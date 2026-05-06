import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# -----------------------------
# 0. INITIALIZATION (เตรียมระบบ)
# -----------------------------
st.set_page_config(page_title="AutoPaint Online Platform", layout="wide")

# เก็บสถานะตะกร้าสินค้า
if 'cart' not in st.session_state:
    st.session_state.cart = {}

# เก็บสถานะการล็อคอิน
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = 'guest'

# ฟังก์ชันจัดการตะกร้าสินค้า
def add_to_cart(barcode, name, price, qty):
    if barcode in st.session_state.cart:
        # ถ้ามีของเดิมอยู่แล้ว ให้บวกเพิ่มตามจำนวนที่ระบุ
        st.session_state.cart[barcode]['qty'] += qty
    else:
        # ถ้ายังไม่มี ให้สร้างรายการใหม่ตามจำนวนที่ระบุ
        st.session_state.cart[barcode] = {'name': name, 'price': price, 'qty': qty}
# -----------------------------
# 1. DATA CONNECTION (เชื่อมต่อข้อมูล)
# -----------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

# -----------------------------
# 1. ปรับปรุงการโหลดข้อมูล (Merge ข้อมูลตำแหน่ง)
# -----------------------------
def load_data():
    stock_df = conn.read(worksheet="Stock")
    reorder_df = conn.read(worksheet="Reorder_All")
    shelf_map_df = conn.read(worksheet="Shelf_Map")
    purchase_df = conn.read(worksheet="Purchase_Invoices")
    lot_df = conn.read(worksheet="Lot_Tracking")
    
    # รวม Stock + ShelfMap (เพื่อให้หน้าสต็อกโชว์ที่เก็บด้วย)
    merged_stock = pd.merge(stock_df, shelf_map_df[['Barcode', 'ShelfMap']], on='Barcode', how='left')
    merged_stock['ShelfMap'] = merged_stock['ShelfMap'].fillna("ยังไม่ได้ระบุ")
    
    return merged_stock, reorder_df, shelf_map_df, purchase_df, lot_df
        
    return merged_df, reorder_df
# -----------------------------
# 2. AUTHENTICATION (ระบบล็อคอิน)
# -----------------------------
def login():
    with st.sidebar:
        st.subheader("🔑 เข้าสู่ระบบจัดการร้าน")
        user = st.text_input("Username", key="login_user")
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            if user == "admin" and pw == "123": # เปลี่ยนรหัสที่นี่
                st.session_state['logged_in'] = True
                st.session_state['role'] = 'admin'
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# -----------------------------
# 3. CUSTOMER VIEW (ส่วนของลูกค้า)
# -----------------------------
def customer_view(stock_df):
    st.title("🎨 AutoPaint Online")
    
    tabs = st.tabs(["🏠 หน้าแรก", "📦 สั่งซื้อสินค้า", "🛒 ตะกร้าของฉัน", "🔍 ค้นหาสีเบอร์", "📍 ติดต่อเรา"])

    with tabs[0]:
        st.header("ยินดีต้อนรับสู่ศูนย์รวมสีพ่นรถยนต์")
        st.write("สั่งของง่าย เช็คสต็อกเรียลไทม์ ส่งด่วนถึงอู่ด้วย Lalamove")
        st.image("https://images.unsplash.com/photo-1593444209167-173f0534241a?q=80&w=1000&auto=format&fit=crop", caption="Professional Automotive Paint")

    with tabs[1]:
        st.header("📦 ค้นหาและเลือกสินค้า")
        
        # 1. ปรับ Default เป็น None (เพื่อให้ขึ้น Choose options ว่างๆ)
        categories = stock_df['CategoryName'].unique() if 'CategoryName' in stock_df.columns else []
        sel_cat = st.multiselect("📂 เลือกหมวดหมู่ที่ต้องการ:", categories, default=None, key="cat_select")
        
        search_q = st.text_input("🔍 พิมพ์ชื่อสินค้า หรือ รุ่นรถยนต์ เพื่อค้นหาด่วน:", key="search_bar")

        # กรองข้อมูล
        filtered_df = stock_df[stock_df['CategoryName'].isin(sel_cat)]
        if search_q:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_q, na=False, case=False)]

        st.divider()

        if not sel_cat and not search_q:
            st.info("💡 กรุณาเลือกหมวดหมู่สินค้า หรือพิมพ์ค้นหาเพื่อดูรายการสินค้า")
        elif filtered_df.empty:
            st.warning("📥 ไม่พบสินค้าที่ตรงกับเงื่อนไข")
        else:
            for i, row in filtered_df.iterrows():
                with st.container():
                    # ปรับเป็น 2 คอลัมน์เพื่อให้ปุ่มบวกลบไม่หายในมือถือ
                    col_text, col_action = st.columns([4, 1])
                    
                    with col_text:
                        st.write(f"**{row['Name']}**")
                        st.write(f"฿{row['RetailPrice']:,.2f}")
                        st.caption(f"หมวดหมู่: {row['CategoryName']}")
                    
                    with col_action:
                        if row['Qty'] > 0:
                            # ช่องใส่จำนวนที่มีปุ่ม + -
                            item_qty = st.number_input(
                                "จำนวน", 
                                min_value=1, 
                                max_value=int(row['Qty']), 
                                value=1, 
                                key=f"qty_{row['Barcode']}",
                                label_visibility="collapsed"
                            )
                            if st.button("➕ เพิ่ม", key=f"btn_{row['Barcode']}", use_container_width=True):
                                add_to_cart(row['Barcode'], row['Name'], row['RetailPrice'], item_qty)
                                st.toast(f"เพิ่ม {row['Name']} จำนวน {item_qty} แล้ว!")
                        else:
                            st.write("❌ สินค้าหมด")
                    st.divider()
        
        # 2. ฟังก์ชันค้นหาด้วยชื่อหรือรุ่นรถ (Keyword Search)
        search_q = st.text_input("🔍 พิมพ์ชื่อสินค้า หรือ รุ่นรถยนต์ เพื่อค้นหาด่วน:")

        # --- Logic การกรองข้อมูล ---
        # กรองตามหมวดหมู่ที่เลือกก่อน
        filtered_df = stock_df[stock_df['CategoryName'].isin(sel_cat)]
        
        # แล้วจึงกรองตามคำค้นหา (ถ้ามีการพิมพ์)
        if search_q:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_q, na=False, case=False)]

        st.divider()

        # 3. แสดงผลลัพธ์
        if filtered_df.empty:
            st.warning("📥 ไม่พบสินค้าที่ตรงกับเงื่อนไขการค้นหา")
        else:
            st.write(f"พบสินค้าทั้งหมด {len(filtered_df)} รายการ")
            
            # แสดงสินค้าเป็นแถวๆ (Row Layout) เพื่อให้กดง่ายในมือถือ
            for i, row in filtered_df.iterrows():
                with st.container():
                    c1, c2, c4 = st.columns([4, 1, 1])
                    with c1:
                        st.write(f"**{row['Name']}**")
                        st.caption(f"หมวดหมู่: {row['CategoryName']}")
                    
                    c2.write(f"฿{row['RetailPrice']:,.2f}")
			
                    if row['Qty'] > 0:
                        if c4.button("➕ เพิ่ม", key=f"add_cat_{row['Barcode']}"):
                            add_to_cart(row['Barcode'], row['Name'], row['RetailPrice'])
                            st.toast(f"เพิ่ม {row['Name']} แล้ว!")
                    else:
                        c4.write("🚫 หมด")
                    st.divider()

    with tabs[2]:
        st.header("🛒 รายการสั่งซื้อของคุณ")
        if not st.session_state.cart:
            st.write("ยังไม่มีสินค้าในตะกร้า")
        else:
            grand_total = 0
            for bc, item in st.session_state.cart.items():
                line_total = item['qty'] * item['price']
                grand_total += line_total
                st.write(f"✅ {item['name']} x {item['qty']} = **{line_total:,.2f} บาท**")
            
            st.divider()
            st.subheader(f"ยอดรวมค่าสินค้า: {grand_total:,.2f} บาท")
            st.info("📍 ขั้นตอนถัดไป: ระบบจะเชื่อมต่อ Lalamove เพื่อคำนวณค่าส่งตามระยะทาง")
            if st.button("ยืนยันออเดอร์ (โอนชำระเงิน)"):
                st.success("บันทึกออเดอร์เรียบร้อย! กรุณารอการยืนยันจากร้านค้า")

    with tabs[3]:
        st.header("🔍 ค้นหาเบอร์สีรถยนต์")
        st.info("อ้างอิงข้อมูลเบอร์สีจากฐานข้อมูล Nippon Paint / เพจเพื่อนบ้าน")
        model = st.text_input("รุ่นรถยนต์", key="color_model")
        color_code = st.text_input("รหัสสี", key="color_code")
        if st.button("ค้นหาข้อมูล", key="btn_color_search"):
            st.write("กำลังดึงข้อมูลเฉดสีที่ใกล้เคียง...")

    with tabs[4]:
        st.header("📍 ติดต่อเรา")
        st.write("ร้านตั้งอยู่ที่: ถนน... จังหวัด...")
        st.markdown('<iframe src="https://www.google.com/maps/embed?..." width="100%" height="450"></iframe>', unsafe_allow_html=True)

# -----------------------------
# 4. ADMIN VIEW (ส่วนของเจ้าของร้าน)
# -----------------------------
def admin_view(stock_df, reorder_df, shelf_map_df, purchase_df, lot_df):
    st.title("📊 ระบบบริหารจัดการหลังบ้าน")
    
    # Dashboard สรุปยอด (มูลค่า 1.8 ล้านของคุณพี่)
    col1, col2, col3 = st.columns(3)
    total_value = (stock_df['Qty'] * stock_df['Cost']).sum()
    col1.metric("มูลค่าสต็อกรวม", f"{total_value:,.2f} บาท")
    col2.metric("รายการที่ต้องสั่งเพิ่ม", len(reorder_df))
    col3.metric("สถานะคลังสินค้า", "พร้อมใช้งาน ✅")

    st.divider()

    # แท็บจัดการระบบ
    admin_tabs = st.tabs(["📋 เช็กสต็อก", "🚛 สั่งของ", "📥 ใบรับเข้า (Put-away)", "🔢 ตรวจสอบ Lot", "💰 บริหารการเงิน"])

    with admin_tabs[0]:
        st.subheader("🔍 ตรวจสอบรายการสินค้าและที่เก็บ")
        # ช่องค้นหาด่วนภายในหน้า Admin
        q_admin = st.text_input("ค้นหาชื่อสินค้า/Barcode เพื่อดูที่เก็บ:", key="admin_search")
        
        if q_admin:
            look_up = stock_df[stock_df['Name'].str.contains(q_admin, na=False, case=False) | 
                              stock_df['Barcode'].astype(str).str.contains(q_admin)]
        else:
            look_up = stock_df

        # --- ส่วนที่แก้ไข: เช็คคอลัมน์ก่อนแสดงผล ---
        # กำหนดคอลัมน์พื้นฐานที่ต้องมีแน่ๆ
        cols_to_show = ['Barcode', 'Name', 'Qty', 'ShelfMap']
        
        # เช็คว่าในไฟล์พี่ใช้ชื่อ Supplier ว่าอะไร (เช่น Supplier หรือ SupplierName)
        actual_columns = look_up.columns.tolist()
        if 'SupplierName' in actual_columns:
            cols_to_show.append('SupplierName')
        elif 'Supplier' in actual_columns:
            cols_to_show.append('Supplier')
        elif 'ผู้ผลิต' in actual_columns:
            cols_to_show.append('ผู้ผลิต')

        # แสดงตารางเฉพาะคอลัมน์ที่มีอยู่จริง
        st.dataframe(
            look_up[cols_to_show],
            use_container_width=True,
            hide_index=True
        )

    with admin_tabs[1]:
        st.header("รายการที่ต้องสั่งแยกตาม Supplier")
        if not reorder_df.empty:
            sup_col = next((c for c in ['Supplier', 'SupplierName', 'ผู้ผลิต'] if c in reorder_df.columns), None)
            if sup_col:
                for sup in reorder_df[sup_col].unique():
                    with st.expander(f"📦 Supplier: {sup}"):
                        sup_items = reorder_df[reorder_df[sup_col] == sup][['Name', 'Qty', 'MinStock']]
                        # ใช้ dataframe + hide_index เพื่อลบตัวเลขด้านหน้ากวนใจ
                        st.dataframe(sup_items, use_container_width=True, hide_index=True)
                        if st.button(f"พิมพ์ใบสั่งซื้อ {sup}"):
                           st.write("กำลังเจนฯ PDF ใบสั่งซื้อ...")
            else:
                st.error("ไม่พบคอลัมน์ Supplier")
    
    # --- Tab 3: ใบรับสินค้าเข้า (Put-away) แบบอัปเกรด ---
    with admin_tabs[2]:
        st.subheader("📥 รายการรับเข้าสินค้าและการจัดเก็บ")
        
        if not purchase_df.empty:
            # 1. เตรียมข้อมูลวันที่เพื่อการกรอง
            purchase_df['วันที่'] = pd.to_datetime(purchase_df['วันที่'], errors='coerce')
            
            # สร้างตัวเลือก ปี และ เดือน
            years = sorted([int(y) for y in purchase_df['วันที่'].dt.year.unique() if pd.notna(y)], reverse=True)
            months = range(1, 13)
            month_names = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                           "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

            c1, c2 = st.columns(2)
            sel_year = c1.selectbox("เลือกปี:", years)
            sel_month = c2.selectbox("เลือกเดือน:", months, index=datetime.now().month-1, format_func=lambda x: month_names[x-1])

            # กรองข้อมูลตามวันที่เลือก
            filtered_purchase = purchase_df[
                (purchase_df['วันที่'].dt.year == sel_year) & 
                (purchase_df['วันที่'].dt.month == sel_month)
            ]

            st.divider()

            if filtered_purchase.empty:
                st.info(f"📅 ไม่พบข้อมูลการรับเข้าในเดือน {month_names[sel_month-1]} {sel_year}")
            else:
                # 2. จัดกลุ่มข้อมูลตาม เลขบิล เพื่อแสดงเป็นใบๆ
                # เรียงจากวันที่ล่าสุดขึ้นก่อน
                invoice_groups = filtered_purchase.groupby(['InvoiceNo', 'ชื่อบริษัทผู้ขาย', 'วันที่'])

                for (inv_no, vendor, inv_date), items in invoice_groups:
                    # สร้างหัวข้อ Card ที่รวมข้อมูลสำคัญ
                    date_str = inv_date.strftime('%d/%m/%Y %H:%M')
                    with st.expander(f"📅 {date_str} | 🏢 {vendor} | 📄 บิลเลขที่: {inv_no}"):
                        
                        # นำรายการสินค้าในบิลนี้ไปหาตำแหน่งที่เก็บจาก ShelfMap
                        if 'Barcode' in items.columns:
                            # รวมข้อมูลกับ ShelfMap
                            receipt_with_map = pd.merge(
                                items, 
                                shelf_map_df[['Barcode', 'ShelfMap']], 
                                on='Barcode', 
                                how='left'
                            )
                            receipt_with_map['ShelfMap'] = receipt_with_map['ShelfMap'].fillna("ยังไม่ได้ระบุ")

                            # เลือกคอลัมน์ที่จะโชว์
                            # ตรวจสอบชื่อคอลัมน์จริงในไฟล์พี่ (ชื่อสินค้า/Name, จำนวน/Qty)
                            name_col = next((c for c in ['ชื่อสินค้า', 'Name'] if c in receipt_with_map.columns), 'Name')
                            qty_col = next((c for c in ['จำนวน', 'Qty'] if c in receipt_with_map.columns), 'Qty')
                            
                            display_df = receipt_with_map[[name_col, qty_col, 'ShelfMap']].sort_values(by='ShelfMap')
                            
                            # ปรับชื่อคอลัมน์ให้ดูง่ายในตาราง
                            display_df.columns = ['รายการสินค้า', 'จำนวนที่รับ', 'ตำแหน่งชั้นวาง']
                            
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                            
                            # ปุ่มปริ้นท์แยกตามบิล
                            st.button(f"🖨️ พิมพ์ใบจัดเก็บ (บิล {inv_no})", key=f"print_{inv_no}")
                        else:
                            st.error("❌ ข้อมูลบิลนี้ไม่มี Barcode ทำให้ดึงตำแหน่งที่เก็บไม่ได้")
        else:
            st.warning("⚠️ ไม่พบข้อมูลในแท็บ Purchase_Invoices")

# --- Tab 4: ตรวจสอบ Lot (FIFO Lot Tracking) ---
    with admin_tabs[3]:
        st.subheader("🔢 ตรวจสอบอายุสินค้าราย Lot (รายบิลรับเข้า)")
        st.caption("ระบบจะแสดงเฉพาะสินค้าที่มีประวัติการซื้อเข้า เพื่อคำนวณอายุตามจริง")
        
        if not lot_df.empty:
            # 1. ส่วนการค้นหา
            search_lot = st.text_input("🔍 ค้นชื่อสินค้า หรือ Barcode เพื่อดู Lot:", key="search_lot_input")
            
            display_lot = lot_df.copy()
            if search_lot:
                display_lot = display_lot[
                    display_lot['Name'].str.contains(search_lot, na=False, case=False) | 
                    display_lot['Barcode'].astype(str).str.contains(search_lot)
                ]

            # 2. ปรับแต่งการแสดงผลตาราง
            # เรียงลำดับตามวันที่ (จากเก่าไปใหม่) เพื่อให้พี่เห็นตัวที่ควรระบายออกก่อน
            display_lot = display_lot.sort_values(by=['Barcode', 'Date'])

            # เปลี่ยนชื่อคอลัมน์ให้พี่อ่านง่ายขึ้น
            column_mapping = {
                'Name': 'ชื่อสินค้า',
                'BillNo': 'เลขที่บิล',
                'Date': 'วันที่รับเข้า',
                'Remaining': 'จำนวนคงเหลือใน Lot',
                'AgeMonths': 'อายุ (เดือน)',
                'Status': 'สถานะอายุ'
            }
            
            # กรองเอาเฉพาะคอลัมน์ที่พี่อยากเห็น
            final_df = display_lot[list(column_mapping.keys())].rename(columns=column_mapping)

            # 3. แสดงผลตารางพร้อมสีสถานะ
            st.dataframe(
                final_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "จำนวนคงเหลือใน Lot": st.column_config.NumberColumn(format="%d ชิ้น"),
                    "อายุ (เดือน)": st.column_config.NumberColumn(format="%d เดือน"),
                    "สถานะอายุ": st.column_config.TextColumn(help="GREEN: ปกติ, YELLOW: เริ่มเก่า, RED: ต้องรีบขาย")
                }
            )
            
            st.info("💡 สินค้าตัวเดียวกันอาจมีหลายบรรทัด หมายถึงสินค้าที่เหลือค้างสต็อกมาจากหลายบิลรับเข้าครับ")
        else:
            st.warning("⚠️ ไม่พบข้อมูล Lot Tracking กรุณาตรวจสอบแท็บ Lot_Tracking ใน Google Sheets")

# --- Tab 4: บริหารการเงินร้านค้า ---
    with admin_tabs[4]:
        st.subheader("💰 สรุปยอดสั่งซื้อรายเดือน (Accounts Payable)")
        
        if not purchase_df.empty:
            # เตรียมข้อมูลวันที่ให้เป็นรูปแบบ Datetime
            purchase_df['วันที่'] = pd.to_datetime(purchase_df['วันที่'], errors='coerce')
            
            # กรองปีและเดือน (ดึงเฉพาะปีที่มีข้อมูลจริง)
            years_fin = sorted([int(y) for y in purchase_df['วันที่'].dt.year.unique() if pd.notna(y)], reverse=True)
            month_names = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                           "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

            cf1, cf2 = st.columns(2)
            sel_year_fin = cf1.selectbox("เลือกปี (การเงิน):", years_fin, key="fin_year")
            sel_month_fin = cf2.selectbox("เลือกเดือน (การเงิน):", range(1, 13), 
                                          index=datetime.now().month-1, 
                                          format_func=lambda x: month_names[x-1], 
                                          key="fin_month")

            # กรองข้อมูลตามเดือน/ปีที่เลือก
            df_monthly_fin = purchase_df[
                (purchase_df['วันที่'].dt.year == sel_year_fin) & 
                (purchase_df['วันที่'].dt.month == sel_month_fin)
            ]

            if not df_monthly_fin.empty:
                # --- ส่วนสรุปยอด Metric ---
                total_monthly_buy = df_monthly_fin['ยอดรวมสินค้า'].sum()
                st.metric(f"ยอดซื้อรวมประจำเดือน {month_names[sel_month_fin-1]}", f"{total_monthly_buy:,.2f} บาท")

                st.divider()

                # --- สรุปแยกตาม Supplier ---
                st.write("### 🏢 สรุปยอดแยกตามผู้ขาย (Supplier Summary)")
                
                # รวมยอดเงินแยกตามบริษัทผู้ขาย
                supplier_summary = df_monthly_fin.groupby('ชื่อบริษัทผู้ขาย')['ยอดรวมสินค้า'].sum().reset_index()
                supplier_summary.columns = ['ชื่อบริษัทผู้ขาย', 'ยอดสั่งซื้อรวม (บาท)']
                
                # เรียงลำดับจากยอดเงินมากไปน้อย
                supplier_summary = supplier_summary.sort_values(by='ยอดสั่งซื้อรวม (บาท)', ascending=False)
                
                # แสดงผลตารางสรุป
                st.dataframe(
                    supplier_summary, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "ยอดสั่งซื้อรวม (บาท)": st.column_config.NumberColumn(format="฿ %,.2f")
                    }
                )

                # --- รายละเอียดบิลรายใบ ---
                with st.expander("🔍 ดูรายละเอียดบิลรายใบของเดือนนี้"):
                    bill_detail = df_monthly_fin.groupby(['InvoiceNo', 'ชื่อบริษัทผู้ขาย', 'วันที่'])['ยอดรวมสินค้า'].sum().reset_index()
                    bill_detail.columns = ['เลขที่บิล', 'บริษัทผู้ขาย', 'วันที่รับเข้า', 'ยอดรวมสุทธิ']
                    
                    # ปรับรูปแบบวันที่ให้ดูง่ายในตาราง
                    bill_detail['วันที่รับเข้า'] = bill_detail['วันที่รับเข้า'].dt.strftime('%d/%m/%Y')
                    
                    st.dataframe(
                        bill_detail, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "ยอดรวมสุทธิ": st.column_config.NumberColumn(format="%,.2f")
                        }
                    )
                    
            else:
                st.info(f"📅 ยังไม่มีข้อมูลการซื้อในเดือน {month_names[sel_month_fin-1]} ปี {sel_year_fin}")
        else:
            st.warning("⚠️ ไม่พบข้อมูลบิลรับเข้าในระบบ")
# -----------------------------
# 5. MAIN LOGIC (ส่วนประมวลผลหลัก)
# -----------------------------
try:
    # เตรียมตะกร้ารับข้อมูลให้ครบ 5 ใบ ตามที่ load_data ส่งออกมา
    stock_df, reorder_df, shelf_map_df, purchase_df, lot_df = load_data()
    
    if st.session_state['role'] == 'admin':
        if st.sidebar.button("Log out"):
            st.session_state['role'] = 'guest'
            st.rerun()
        
        # ส่งข้อมูลทั้ง 5 อย่างเข้าไปในหน้า Admin
        admin_view(stock_df, reorder_df, shelf_map_df, purchase_df, lot_df)
    else:
        login()
        # หน้าลูกค้าใช้แค่ stock_df เหมือนเดิมครับ
        customer_view(stock_df)
        
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
    st.info("ตรวจสอบว่าคุณได้แชร์ Sheets ให้ Service Account และตั้งชื่อแท็บว่า Stock, Reorder_All, Shelf_Map, Purchase_Invoices, Lot_Tracking เรียบร้อยแล้ว")