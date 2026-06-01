import sqlite3
import pandas as pd
import numpy as np
import gspread
import time
import requests
import html
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date


# ตัวแปรสำหรับเช็คว่าวันนี้ส่งแจ้งเตือนไปหรือยัง (ป้องกันการส่งซ้ำ)
last_sent_8am = None
last_sent_14pm = None
first_run_test = True # ✅ ตัวแปรพิเศษสำหรับทดสอบครั้งแรก

# ตั้งค่า Telegram
TELEGRAM_TOKEN = "7874896500:AAHrF5L8peF80F0sOTpxI03DevE-uIjUOac"
TELEGRAM_CHAT_ID = "-4619280584"

# ✅ ป้องกัน FutureWarning ใน Pandas
pd.set_option('future.no_silent_downcasting', True)

# -----------------------------
# 1. CONFIG (ตั้งค่าการเชื่อมต่อ)
# -----------------------------
DB_PATH = r"C:\OnepointofsaleV3\compact.db"
SERVICE_ACCOUNT = r"C:\OnepointofsaleV3\plenary-stacker-349102-29ed19c5921d.json"
SHEET_ID = "1P9pv-cLwFYyUfE-SYzrJolb4xTCkvL_WbaeSNOdquOs"

SLOW_DAYS = 180
DEAD_DAYS = 365

# -----------------------------
# 2. SQL QUERIES (ใช้ชื่อตารางจริงจาก DB คุณ)
# -----------------------------

# --- ดึงข้อมูลสต็อกหลัก ---
STOCK_QUERY = """
SELECT
    P.Barcode, P.Name, P.Qty, P.Left AS [MinStock], P.Cost, P.RetailPrice,
    (P.RetailPrice - P.Cost) AS [ProfitPerUnit], U.Name AS [UnitName], C.Name AS [CategoryName]
FROM Product P
LEFT JOIN ProductUnit U ON P.Unit = U.Id
LEFT JOIN ProductCategory C ON P.Category = C.Id
WHERE P.IsDelete = 0 ORDER BY P.Name;
"""

# --- ดึงข้อมูล Bundle/Set (สต็อกจริงเก็บที่ตัวย่อย) ---
BUNDLE_QUERY = """
SELECT
    pi.Barcode           AS BundleBarcode,
    pi.BarcodeIngredient AS IngBarcode,
    pi.SetPoint          AS QtyPerBundle,
    p_ing.Qty            AS IngQty
FROM ProductIngredient pi
JOIN Product p_ing ON pi.BarcodeIngredient = p_ing.Barcode
WHERE pi.IsDelete = 0
  AND pi.SetPoint > 0
"""

# --- ดึงประวัติการขาย (สำหรับ LastSale 1-6 และ FIFO) ---
SALES_HISTORY_QUERY = """
SELECT OD.Barcode, O.Complete, OD.Qty
FROM OrdersDetail OD
JOIN Orders O ON O.Id = OD.OrderId
ORDER BY OD.Barcode, O.Complete DESC;
"""

# --- ดึงข้อมูลการซื้อ/ใบเสร็จ (ImportProduct + Vendor) ---
PURCHASE_BILL_QUERY = """
SELECT 
    h.[Create] as [วันที่], h.Id as [เลขที่ใบเสร็จ], v.Name as [ชื่อบริษัทผู้ขาย],
    v.TaxId as [เลขผู้เสียภาษี], v.Address as [ที่อยู่บริษัท], p.Barcode, p.Name as [ชื่อสินค้า],
    d.Qty as [จำนวน], d.Cost as [ราคาทุนต่อหน่วย], (d.Qty * d.Cost) as [ยอดรวมสินค้า]
FROM ImportProductDetail d
JOIN ImportProduct h ON d.ImportId = h.Id
JOIN Product p ON d.Barcode = p.Barcode
LEFT JOIN Vendor v ON h.VenderId = v.Id
WHERE d.IsDelete = 0 ORDER BY h.[Create] DESC;
"""

# --- ดึงประวัติการซื้อสำหรับ FIFO ---
PURCHASE_HISTORY_QUERY = """
SELECT 
    p.Barcode, p.Name as [itemname], d.Qty as [purchase_qty], h.[Create] 
    as [purchase_date], h.Id as [bill_no]
FROM ImportProductDetail d
JOIN ImportProduct h ON d.ImportId = h.Id
JOIN Product p ON d.Barcode = p.Barcode
WHERE d.IsDelete = 0 ORDER BY p.Barcode, h.[Create] ASC;
"""

# --- รายงานภาษีขาย (ดึงเฉพาะรายการ VAT OUT และรายละเอียดสมาชิก) ---
SALES_VAT_QUERY = """
SELECT 
    O.Complete as [วันที่], 
    O.BillNo as [เลขที่ใบกำกับภาษี], 
    COALESCE(m.FirstName || ' ' || m.LastName, 'ลูกค้าทั่วไป') as [ชื่อผู้ซื้อ/สมาชิก],
    m.TaxId as [เลขผู้เสียภาษีผู้ซื้อ], 
    m.Address as [ที่อยู่ผู้ซื้อ], 
    p.Name as [รายการสินค้า],
    OD.Qty as [จำนวน], 
    OD.Price as [ราคาต่อหน่วย], 
    (OD.Qty * OD.Price) as [ยอดรวมรวม VAT],
    p.Vat as [เช็คค่าVat] -- เพิ่มมาเพื่อดูว่าใน DB เก็บค่าอะไร (0 หรือ 1)
FROM OrdersDetail OD
JOIN Product p ON OD.Barcode = p.Barcode
JOIN Orders O ON OD.OrderId = O.Id
LEFT JOIN Member m ON O.MemberId = m.Id
WHERE O.IsDelete = 0 
ORDER BY O.Complete DESC 
LIMIT 100; -- ดึงมาดู 100 รายการล่าสุดก่อน
"""

# -----------------------------
# 3. FUNCTIONS (ส่วนคำนวณตรรกะ)
# -----------------------------

def classify_sale_status(last_sale_dt):
    if pd.isna(last_sale_dt) or last_sale_dt == "":
        return None, "NEVER_SOLD"
    try:
        dt = pd.to_datetime(last_sale_dt).date()
        days = (date.today() - dt).days
        if days >= DEAD_DAYS: return days, "DEAD"
        if days >= SLOW_DAYS: return days, "SLOW"
        return days, "ACTIVE"
    except: return None, "ERROR"

def calculate_fifo_aging(df_purchases, df_sales_all, df_stock):
    # เตรียม Barcode ให้สะอาด
    df_purchases['Barcode'] = df_purchases['Barcode'].astype(str).str.strip()
    df_sales_all['Barcode'] = df_sales_all['Barcode'].astype(str).str.strip()
    df_stock['Barcode'] = df_stock['Barcode'].astype(str).str.strip()

    name_map = dict(zip(df_stock['Barcode'], df_stock['Name']))
    sales_dict = df_sales_all.groupby('Barcode')['Qty'].sum().to_dict()
    actual_stock_dict = dict(zip(df_stock['Barcode'], df_stock['Qty']))
    
    results = []
    today = pd.to_datetime('today')
    
    for barcode, current_qty in actual_stock_dict.items():
        if current_qty <= 0: continue
        
        real_name = name_map.get(barcode, "ไม่พบชื่อสินค้า")
        # ดึงบิลซื้อจริง
        p_rows = df_purchases[df_purchases['Barcode'] == barcode].sort_values(by='purchase_date').to_dict('records')
        
        # 1. คำนวณหา "ยอดยกมา" (ถ้ามี)
        total_p_qty = sum(row['purchase_qty'] for row in p_rows)
        total_sales = sales_dict.get(barcode, 0)
        
        # สูตร: ยอดยกมา = (ของที่มีอยู่จริง + ของที่ขายไปแล้ว) - ของที่มีหลักฐานการซื้อ
        opening_balance_qty = max(0, (current_qty + total_sales) - total_p_qty)
        
        # 2. สร้างกองบิลทั้งหมด (เอายอดยกมาวางไว้หน้าสุดเป็นบิลเก่าที่สุด)
        all_bills = []
        if opening_balance_qty > 0:
            all_bills.append({
                'bill_no': 'ยอดยกมา',
                'purchase_date': '2000-01-01', # ตั้งให้เก่ามากๆ
                'purchase_qty': opening_balance_qty,
                'itemname': real_name
            })
        all_bills.extend(p_rows)
        
        # 3. เริ่มกระบวนการ FIFO: หักยอดขายออกจากบิล (เริ่มจากบิลเก่าสุด/ยอดยกมา)
        sold_pool = total_sales
        for bill in all_bills:
            p_qty = bill['purchase_qty']
            # หักยอดขายออกจากบิลนี้
            remaining_in_bill = max(0, p_qty - sold_pool)
            # ปรับปรุงยอดขายที่เหลือให้ไปหักบิลถัดไป
            sold_pool = max(0, sold_pool - p_qty)
            
            if remaining_in_bill > 0:
                # กันเหนียว: ยอดในบิลต้องไม่เกินยอดสต็อกจริง
                # (กรณีมีของหายหรือคีย์ยอดขายไม่ครบ)
                p_date_str = bill['purchase_date']
                
                if p_date_str == "2000-01-01":
                    display_date = "เก่ากว่าประวัติบิล"
                    age_months = 99
                    status = "สินค้ายอดยกมา"
                else:
                    p_date = pd.to_datetime(p_date_str)
                    display_date = p_date.strftime('%Y-%m-%d')
                    age_months = (today - p_date).days // 30
                    # คำนวณสถานะสีตามอายุ
                    status = "GREEN"
                    if age_months >= 12: status = "DEAD (1Y+)"
                    elif age_months >= 10: status = "RED (URGENT)"
                    elif age_months >= 6: status = "YELLOW"
                
                results.append([
                    barcode, real_name, bill['bill_no'], 
                    display_date, remaining_in_bill, age_months, status
                ])

    return pd.DataFrame(results, columns=['Barcode', 'Name', 'BillNo', 'Date', 'Remaining', 'AgeMonths', 'Status'])

# -----------------------------
# 4. MAIN SYNC PROCESS
# -----------------------------
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")
        
def run_sync(client):
    print(f"\n🚀 Sync started at {datetime.now()}")
    conn = sqlite3.connect(DB_PATH)
    ss = client.open_by_key(SHEET_ID)
# --- เพิ่มฟังก์ชัน update_tab ตรงนี้ (จุดที่ 1) ---
    def update_tab(tab_name, data_df):
        try:
            clean_df = data_df.replace([np.inf, -np.inf], np.nan).fillna("")
            for col in clean_df.columns:
                if any(x in str(col).lower() for x in ['date', 'วันที่', 'complete', 'create', 'month']):
                    clean_df[col] = clean_df[col].astype(str).replace(["NaT", "None", "nan"], "")
            
            ws = ss.worksheet(tab_name)
            ws.clear()
            ws.update([clean_df.columns.values.tolist()] + clean_df.values.tolist())
            print(f"✅ Update {tab_name} Success")
        except Exception as e:
            print(f"⚠️ Error {tab_name}: {e}")
    try:
        # ก) สต็อกและประวัติขาย 6 ครั้ง
        df = pd.read_sql_query(STOCK_QUERY, conn)
        df_sales_all = pd.read_sql_query(SALES_HISTORY_QUERY, conn)
        
        df_top6 = df_sales_all.groupby('Barcode').head(6).copy()
        df_top6['Rank'] = df_top6.groupby('Barcode').cumcount() + 1
        df_pivot = df_top6.pivot(index='Barcode', columns='Rank', values='Complete')
        df_pivot.columns = [f"SaleDate{i}" for i in df_pivot.columns]
        df = df.merge(df_pivot, on='Barcode', how='left')

        df["LastSaleDate"] = df["SaleDate1"].fillna("")
        df["DaysSinceLastSale"], df["SaleStatus"] = zip(*df["SaleDate1"].apply(classify_sale_status))
        df["StockStatus"] = [("OUT_OF_STOCK" if q == 0 else "LOW" if q < ms else "OK") for q, ms in zip(df["Qty"], df["MinStock"])]
        df["QtyPositive"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0).clip(lower=0)
        df["StockValueCost"] = df["QtyPositive"] * df["Cost"].fillna(0)
        df["StockValueRetail"] = df["QtyPositive"] * df["RetailPrice"].fillna(0)
        
        # ✅ ย้าย SnapshotTime ไปคอลัมน์แรก พร้อมเวลา Sync
        df["SnapshotTime"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        cols = ["SnapshotTime"] + [c for c in df.columns if c != "SnapshotTime"]
        df = df[cols]

        # ── คำนวณสต็อกจริงสำหรับสินค้า Bundle/Set ──────────────────────
        try:
            df_bundle = pd.read_sql_query(BUNDLE_QUERY, conn)
            if not df_bundle.empty:
                for _, brow in df_bundle.iterrows():
                    bundle_bc = str(brow['BundleBarcode']).strip()
                    qty_per   = float(brow['QtyPerBundle'])
                    ing_qty   = float(brow['IngQty'])
                    if qty_per > 0:
                        real_qty = ing_qty / qty_per
                        mask = df['Barcode'].astype(str).str.strip() == bundle_bc
                        if mask.any():
                            df.loc[mask, 'Qty'] = real_qty
                # ── ตรวจสอบผลลัพธ์ Bundle ──
                print("🔎 ตรวจสอบสต็อก Bundle/Set:")
                for _, brow in df_bundle.iterrows():
                    bc = str(brow['BundleBarcode']).strip()
                    name = df.loc[df['Barcode'].astype(str).str.strip() == bc, 'Name'].values
                    qty  = df.loc[df['Barcode'].astype(str).str.strip() == bc, 'Qty'].values
                    print(f"   Bundle: {bc} | {name} | Qty={qty} (จาก {brow['IngQty']} ÷ {brow['QtyPerBundle']})")
        except Exception as e:
            print(f"[WARN] Bundle stock calculation skipped: {e}")
        # ─────────────────────────────────────────────────────────────────

        # --- เรียกใช้ update_tab สำหรับ Stock (จุดที่ 2) ---
        update_tab("Stock", df)

        # --- ข) รายงานภาษีขาย (Sales VAT Report) ---
        print("📊 กำลังดึงรายงานภาษีขาย (เฉพาะ VAT OUT)...")
        df_vat = pd.read_sql_query(SALES_VAT_QUERY, conn)
        if not df_vat.empty:
            # คำนวณภาษีแยกออกมาให้เห็นชัดเจน
            # สูตร: VAT = ยอดรวม * 7 / 107 | ยอดก่อน VAT = ยอดรวม - VAT
            df_vat['VAT 7%'] = round(df_vat['ยอดรวมรวม VAT'] * 1.07, 2)
            df_vat['Before VAT'] = df_vat['ยอดรวมรวม VAT']
            
            # เพิ่มคอลัมน์ "เดือน" เพื่อให้คุณ Filter ใน Sheets ได้ง่ายขึ้น
            df_vat['Month'] = pd.to_datetime(df_vat['วันที่']).dt.strftime('%Y-%m')
            
            # จัดลำดับคอลัมน์ใหม่ (เอาเดือนไว้หน้าสุดเพื่อให้คุณเช็ครายเดือนได้)
            cols_vat = ['Month'] + [c for c in df_vat.columns if c != 'Month']
            df_vat = df_vat[cols_vat]
        # ส่งข้อมูลไปยังแท็บ 'Sales_VAT_Report'
        update_tab("Sales_VAT_Report", df_vat)
        
        # ค) คำนวณ FIFO
        print("📦 กำลังคำนวณ FIFO Lot Tracking...")
        df_purchases = pd.read_sql_query(PURCHASE_HISTORY_QUERY, conn)
        df_lot = calculate_fifo_aging(df_purchases, df_sales_all, df)
        update_tab("Lot_Tracking", df_lot)

        # ง) อัปเดตใบรับเข้าสินค้า (Purchase_Invoices) ---
        # ✅ เพิ่มส่วนนี้: เพื่อให้หน้า "ใบนำฝากสินค้า" ในเว็บทำงานได้
        print("🧾 กำลังดึงข้อมูลใบรับเข้าสินค้า (Purchase_Invoices)...")
        df_purchase_bills = pd.read_sql_query(PURCHASE_BILL_QUERY, conn)

        # rename ก่อน แล้วค่อยใช้
        df_purchase_bills = df_purchase_bills.rename(columns={'เลขที่ใบเสร็จ': 'InvoiceNo'})
        if 'InvoiceNo' not in df_purchase_bills.columns:
            df_purchase_bills['InvoiceNo'] = df_purchase_bills.index.astype(str)

        update_tab("Purchase_Invoices", df_purchase_bills)

        # จ) ส่งขึ้น Google Sheets
        print("☁️ ส่งข้อมูลขึ้น Cloud...")
    finally:
        conn.close()
        print(f"🏁 รอบการ Sync เสร็จสิ้นที่เวลา {datetime.now().strftime('%H:%M:%S')}")

   # --- ส่วนเช็คเวลาและส่งแจ้งเตือน Telegram (กรองผ่าน Name + Category) ---
    global last_sent_8am, last_sent_14pm, first_run_test
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = date.today()

    is_time_8am = "08:00" <= current_time <= "08:10"
    is_time_2pm = "14:00" <= current_time <= "14:10"

    if (is_time_8am and last_sent_8am != today) or \
       (is_time_2pm and last_sent_14pm != today) or \
       (first_run_test == True): 
        
        # 1. กรองสินค้า LOW/OUT และตัดรายการ xx ออกก่อนเป็นอันดับแรก
        all_low = df[df["StockStatus"].str.strip().isin(["OUT_OF_STOCK", "LOW"])].copy()
        valid_items = all_low[~all_low['Name'].str.strip().str.lower().str.startswith('xx', na=False)]

        # 2. แยกกลุ่มที่ 1: สีพ่นรถยนต์ (หาจากชื่อสินค้า OR ชื่อหมวดหมู่)
        paint_filter = valid_items[
            valid_items['Name'].str.contains('สีพ่น', na=False) | 
            valid_items['CategoryName'].str.contains('สีพ่น', na=False)
        ]

        # 3. แยกกลุ่มที่ 2: สินค้าหลักอื่นๆ (หาจากชื่อสินค้า OR ชื่อหมวดหมู่)
        other_keywords = ["แลคเกอร์", "ทินเนอร์", "สีโป๊ว", "สีรองพื้น"]
        other_pattern = '|'.join(other_keywords)
        
        # ✅ ปรับใหม่: เช็คทั้งใน Name และ CategoryName
        other_filter = valid_items[
            valid_items['Name'].str.contains(other_pattern, na=False) | 
            valid_items['CategoryName'].str.contains(other_pattern, na=False)
        ]

        # ฟังก์ชันช่วยส่งรายงาน (แบ่งข้อความอัตโนมัติ)
        def send_chunked_report(items_df, title):
            if items_df.empty:
                if first_run_test:
                    send_telegram_alert(f"<b>✅ {title}:</b>\nสต็อกยังมีเพียงพอครับ")
                return

            alert_list = []
            for _, row in items_df.iterrows():
                p_name = html.escape(str(row['Name']).strip())
                icon = "❌" if row["StockStatus"] == "OUT_OF_STOCK" else "🟠"
                # แสดงชื่อหน่วยและจำนวนให้ชัดเจน
                alert_list.append(f"{icon} <b>{p_name}</b>\n   คงเหลือ: {row['Qty']} {row['UnitName']}")

            chunk_size = 20
            header_text = f"<b>📦 {title}</b>\nประจำเวลา {current_time}\n\n"
            
            for i in range(0, len(alert_list), chunk_size):
                batch = alert_list[i : i + chunk_size]
                msg = (header_text if i == 0 else "") + "\n".join(batch)
                send_telegram_alert(msg)
                time.sleep(1) # พักเบรกกันโดน Telegram แบน

        # --- สั่งรันการส่งแจ้งเตือนแยกข้อความ ---
        print(f"📊 ตรวจพบสีพ่นรถยนต์: {len(paint_filter)} รายการ | สินค้าหลักอื่นๆ: {len(other_filter)} รายการ")
        
        send_chunked_report(paint_filter, "รายงานหมวด: สีพ่นรถยนต์")
        send_chunked_report(other_filter, "รายงานหมวด: สินค้าหลักอื่นๆ")

        # บันทึกสถานะเพื่อป้องกันการส่งซ้ำในรอบ 5 นาทีถัดไป
        if is_time_8am: last_sent_8am = today
        if is_time_2pm: last_sent_14pm = today
        if first_run_test: first_run_test = False
# -----------------------------
# 5. EXECUTION
# -----------------------------

if __name__ == "__main__":
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT, scope)
    gs_client = gspread.authorize(creds)
    
    # ✅ เพิ่มบรรทัดนี้เพื่อทดสอบส่งข้อความทันทีที่เริ่มโปรแกรม
    print("🧪 กำลังส่งข้อความทดสอบเข้า Telegram...")
    send_telegram_alert("<b>🚀 ระบบแจ้งเตือนสต็อกเริ่มทำงานแล้ว!</b>\nสถานะ: เชื่อมต่อสำเร็จ")
    
    while True:
        try:
            run_sync(gs_client)
        except Exception as e:
            print(f"❌ GLOBAL ERROR: {e}")
        
        print(f"😴 Waiting 5 minutes for next sync...")
        time.sleep(300)

