# -*- coding: utf-8 -*-
"""
ผู้ช่วยคนทำบัญชี — ThaiNova AutoPaint
- ค้นหารหัสบัญชี (POS barcode/ชื่อ → acc_code)
- ใบอ้างอิง A4 สำหรับคีย์บิลซื้อเข้า AccOffice

Data access แยกเป็นฟังก์ชันต่างหาก — ตอนนี้อ่านจาก CSV ใน repo
อนาคตย้ายไป Google Sheets ได้โดยแก้เฉพาะ load_*() ด้านล่าง
"""
import os
import html as _html
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Accountant_helper")

# ══════════════════════════════════════════════════════════════
# DATA ACCESS LAYER
# ลำดับ: Google Sheets (private, ใช้บน cloud) → CSV ในเครื่อง (fallback)
# ══════════════════════════════════════════════════════════════
def _read_sheet(worksheet: str) -> pd.DataFrame:
    """อ่าน worksheet จาก spreadsheet เดิม — คืน DataFrame string ล้วน"""
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet=worksheet)
    if df is None or df.empty:
        raise ValueError(f"worksheet {worksheet} ว่าง")
    return df.astype(str).replace({"nan": "", "None": "", "<NA>": ""}).fillna("")

@st.cache_data(ttl=600)
def load_mapping() -> pd.DataFrame:
    """mapping สินค้า POS↔AccOffice — pos_barcode/acc_code เป็น string เสมอ"""
    try:
        df = _read_sheet("Product_Mapping")
    except Exception:
        try:
            df = pd.read_csv(os.path.join(_DATA_DIR, "product_mapping.csv"),
                             encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            return pd.DataFrame(columns=["pos_barcode","pos_name","acc_code",
                                         "acc_name","acc_unit","match_source",
                                         "verified","updated"])
    df["pos_barcode"] = df["pos_barcode"].astype(str).str.strip()
    df["pos_barcode"] = df["pos_barcode"].str.replace(r"\.0$", "", regex=True)
    return df

@st.cache_data(ttl=600)
def load_supplier_mapping() -> pd.DataFrame:
    """mapping ผู้ขาย POS → acc_supp_code"""
    try:
        return _read_sheet("Supplier_Mapping")
    except Exception:
        try:
            return pd.read_csv(os.path.join(_DATA_DIR, "supplier_mapping.csv"),
                               encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            return pd.DataFrame(columns=["pos_supplier_name","pos_tax_id",
                                         "acc_supp_code","acc_supp_name",
                                         "acc_tax_id","match_source","verified"])

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def _norm_barcode(v) -> str:
    """แปลง barcode เป็น string สะอาด (ตัด .0 ที่ pandas เติมจากตัวเลข)"""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def search_mapping(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """ค้น contains + case-insensitive จาก ชื่อPOS / ชื่อบัญชี / บาร์โค้ด / รหัสบัญชี"""
    q = query.strip()
    if not q:
        return df
    mask = (
        df["pos_name"].str.contains(q, case=False, na=False, regex=False) |
        df["acc_name"].str.contains(q, case=False, na=False, regex=False) |
        df["pos_barcode"].str.contains(q, case=False, na=False, regex=False) |
        df["acc_code"].str.contains(q, case=False, na=False, regex=False)
    )
    return df[mask]

def enrich_purchase(purchase_df: pd.DataFrame,
                    mapping_df: pd.DataFrame) -> pd.DataFrame:
    """merge บิลซื้อกับ mapping ด้วย barcode — แถวไม่ match ได้ acc_code ว่าง"""
    p = purchase_df.copy()
    p["_bc"] = p["Barcode"].apply(_norm_barcode)
    m = mapping_df[["pos_barcode","acc_code","acc_name","acc_unit"]].copy()
    m = m.drop_duplicates(subset="pos_barcode")
    out = p.merge(m, left_on="_bc", right_on="pos_barcode", how="left")
    for c in ("acc_code","acc_name","acc_unit"):
        out[c] = out[c].fillna("")
    return out

# ══════════════════════════════════════════════════════════════
# TAB 1 — ค้นหารหัสบัญชี
# ══════════════════════════════════════════════════════════════
def render_search_tab():
    mapping = load_mapping()
    if mapping.empty:
        st.warning("⚠️ ไม่พบไฟล์ Accountant_helper/product_mapping.csv")
        return

    q = st.text_input(
        "🔎 ค้นหา", key="ah_q",
        placeholder="พิมพ์ชื่อสินค้า (ไทย/อังกฤษ บางส่วนก็ได้) หรือบาร์โค้ด หรือรหัสบัญชี",
        label_visibility="collapsed")

    res = search_mapping(mapping, q)

    c1, c2 = st.columns(2)
    c1.caption(f"พบ {len(res):,} จาก {len(mapping):,} รายการ")
    verified_only = c2.toggle("เฉพาะที่ยืนยันแล้ว", key="ah_vrf")
    if verified_only:
        res = res[res["verified"] == "yes"]

    if res.empty:
        st.info("ไม่พบสินค้าที่ค้นหา — ลองพิมพ์สั้นลง หรือใช้บาร์โค้ด")
        return

    show = res[["acc_code","acc_name","acc_unit","pos_name","pos_barcode","verified"]].copy()
    show.columns = ["รหัสบัญชี","ชื่อในบัญชี","หน่วย","ชื่อใน POS","บาร์โค้ด","ยืนยัน"]
    st.dataframe(show.head(200), use_container_width=True, hide_index=True,
                 column_config={"ยืนยัน": st.column_config.TextColumn(width="small")})
    if len(res) > 200:
        st.caption("แสดง 200 รายการแรก — พิมพ์ค้นหาเพิ่มเพื่อกรองให้แคบลง")

# ══════════════════════════════════════════════════════════════
# TAB 2 — ใบอ้างอิง A4
# ══════════════════════════════════════════════════════════════
_PRICE_COL_CANDIDATES = ["ราคาทุนต่อหน่วย", "ราคาต่อหน่วย", "ราคา/หน่วย", "UnitPrice", "ราคาทุน"]

def _find_price_col(df: pd.DataFrame):
    for c in _PRICE_COL_CANDIDATES:
        if c in df.columns:
            return c
    return None

def _fiscal_default_range() -> tuple:
    """ค่าเริ่มต้น: 7 วันล่าสุด"""
    today = date.today()
    return (today - timedelta(days=7), today)

def _build_print_html(bills: list, date_from: date, date_to: date) -> str:
    """สร้าง HTML A4 พร้อมฟอนต์ Sarabun + ปุ่มพิมพ์ (ซ่อนตอน print)"""
    e = _html.escape
    bill_blocks = []
    n_bills = len(bills)
    for bi, b in enumerate(bills, 1):
        rows_html = []
        for i, r in enumerate(b["items"], 1):
            unknown = not r["acc_code"]
            cls = ' class="unk"' if unknown else ""
            code = "ไม่รู้รหัส ＿＿＿＿" if unknown else e(r["acc_code"])
            unit = r["acc_unit"] or "—"
            sb = r.get("stock_before")
            if sb is None:
                stock_cell = "—"
            elif sb < 0:
                stock_cell = f'0 <span class="bc">(ขายแล้ว {abs(sb):,.0f})</span>'
            else:
                stock_cell = f"{sb:,.0f}"
            rows_html.append(
                f'<tr{cls}><td>{i}</td>'
                f'<td class="code">{code}</td>'
                f'<td class="pos">{e(r["pos_name"])}<br>'
                f'<span class="bc">{e(r["barcode"])}</span></td>'
                f'<td class="num">{stock_cell}</td>'
                f'<td class="num">{r["qty"]:,.0f}</td>'
                f'<td>{e(unit)}</td>'
                f'<td class="num">{r["price"]:,.2f}</td>'
                f'<td class="num">{r["total"]:,.2f}</td></tr>')
        n_unknown = sum(1 for r in b["items"] if not r["acc_code"])
        unk_note = f" (รอเติมรหัส {n_unknown})" if n_unknown else ""
        supp_code = e(b["supp_code"]) if b["supp_code"] else "＿＿＿＿"
        bill_blocks.append(f"""
<div class="bill">
  <div class="bill-head">
    <div><span class="muted">บิลที่ {bi}/{n_bills}</span>&nbsp;
      <b>{e(b["vendor"])}</b> · เลขบิล <span class="mono">{e(b["invoice"])}</span>
      · {e(b["date_str"])}</div>
    <div>รหัสผู้ขาย: <span class="mono suppcode">{supp_code}</span></div>
  </div>
  <table>
    <thead><tr>
      <th style="width:22px">#</th><th style="width:95px">รหัสบัญชี</th>
      <th>ชื่อสินค้า / บาร์โค้ด</th>
      <th style="width:62px" class="num">สต็อคก่อนรับ*</th>
      <th style="width:52px" class="num">จำนวนรับ</th><th style="width:52px">หน่วย</th>
      <th style="width:62px" class="num">ทุน/หน่วย</th>
      <th style="width:70px" class="num">รวม</th>
    </tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
    <tfoot><tr>
      <td colspan="6"><b>รวมบิลนี้ · {len(b["items"])} รายการ{unk_note}</b></td>
      <td colspan="2" class="num"><b>{b["total"]:,.2f}</b></td>
    </tr></tfoot>
  </table>
  <div class="bill-foot">
    <span>คีย์เข้า AccOffice แล้ว ☐ &nbsp;&nbsp; เลขที่ใบสำคัญ: ＿＿＿＿＿＿＿</span>
    <span>ผู้คีย์: ＿＿＿＿＿＿</span>
  </div>
</div>""")

    grand = sum(b["total"] for b in bills)
    return f"""<!DOCTYPE html>
<html lang="th"><head><meta charset="utf-8">
<title>ใบอ้างอิงคีย์บิลซื้อ {date_from:%d-%m-%Y} ถึง {date_to:%d-%m-%Y}</title>
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ font-family: 'Sarabun', sans-serif; font-size: 13px; color: #1a1a1a;
         background: #fff; padding: 20px; }}
  @page {{ size: A4; margin: 12mm 10mm; }}
  .mono {{ font-family: 'Sarabun', monospace; letter-spacing: .3px; }}
  .muted {{ color: #666; }}
  .doc-head {{ display: flex; justify-content: space-between; align-items: flex-end;
               border-bottom: 2px solid #1a1a1a; padding-bottom: 6px; }}
  .doc-head h1 {{ font-size: 17px; font-weight: 700; }}
  .doc-head .sub {{ font-size: 11.5px; color: #555; }}
  .bill {{ margin-top: 14px; page-break-inside: avoid; }}
  .bill-head {{ display: flex; justify-content: space-between; background: #f0f0ee;
                padding: 6px 10px; font-size: 12.5px; }}
  .suppcode {{ border-bottom: 1px dotted #999; padding: 0 10px; font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 4px; }}
  th {{ border-bottom: 1.5px solid #1a1a1a; text-align: left; padding: 4px; }}
  td {{ border-bottom: .5px solid #ddd; padding: 5px 4px; vertical-align: top; }}
  td.code {{ font-weight: 700; }}
  td.pos {{ color: #555; }}
  .bc {{ font-size: 10.5px; color: #888; }}
  .num {{ text-align: right; }}
  th.num {{ text-align: right; }}
  tr.unk td {{ background: #FAEEDA; color: #7a4a08; }}
  tfoot td {{ border-top: 1.5px solid #1a1a1a; border-bottom: none; font-size: 12.5px; }}
  .bill-foot {{ display: flex; justify-content: space-between; margin-top: 6px;
                font-size: 11.5px; color: #555; }}
  .grand {{ margin-top: 18px; text-align: right; font-size: 14px; font-weight: 700;
            border-top: 2px solid #1a1a1a; padding-top: 8px; }}
  .toolbar {{ position: sticky; top: 0; background: #1a1a1a; color: #fff;
              padding: 10px 16px; margin: -20px -20px 16px; display: flex;
              justify-content: space-between; align-items: center; }}
  .toolbar button {{ font-family: 'Sarabun', sans-serif; font-size: 15px; font-weight: 700;
              background: #C9A84C; color: #1a1a1a; border: none; border-radius: 8px;
              padding: 8px 22px; cursor: pointer; }}
  @media print {{ .toolbar {{ display: none; }} body {{ padding: 0; }} }}
</style></head><body>
<div class="toolbar">
  <span>กด "พิมพ์" แล้วเลือกเครื่องพิมพ์ หรือ Save as PDF</span>
  <button onclick="window.print()">🖨️ พิมพ์ / บันทึก PDF</button>
</div>
<div class="doc-head">
  <div><h1>ใบอ้างอิงคีย์บิลซื้อ — AccOffice</h1>
    <div class="sub">ThaiNova AutoPaint · ช่วงวันที่ {date_from:%d/%m/%Y} – {date_to:%d/%m/%Y}</div></div>
  <div class="sub" style="text-align:right">พิมพ์เมื่อ {datetime.now():%d/%m/%Y %H:%M}<br>ทั้งหมด {n_bills} บิล</div>
</div>
{''.join(bill_blocks)}
<div class="grand">รวมทุกบิล ({n_bills} บิล): {grand:,.2f} บาท</div>
<div style="margin-top:8px;font-size:10.5px;color:#888">
  * สต็อคก่อนรับ = สต็อคปัจจุบัน − ยอดรับเข้าตั้งแต่วันที่บิลถึงวันนี้
  · "(ขายแล้ว N)" = มีการขายอย่างน้อย N ชิ้นหลังวันที่บิล
  · พิมพ์ทันทีหลังรับเข้าเพื่อความแม่นยำสูงสุด — บิลยิ่งเก่าตัวเลขยิ่งคลาดเคลื่อน</div>
</body></html>"""

def render_reference_tab(purchase_df: pd.DataFrame, stock_df: pd.DataFrame = None):
    mapping   = load_mapping()
    suppliers = load_supplier_mapping()

    if purchase_df is None or purchase_df.empty:
        st.info("📭 ยังไม่มีข้อมูลบิลซื้อใน Purchase_Invoices")
        return

    df = purchase_df.copy()
    df["วันที่"] = pd.to_datetime(df["วันที่"].astype(str).str.strip(),
                                   errors="coerce", format="mixed")
    df = df.dropna(subset=["วันที่"])

    # ── สต็อคปัจจุบัน + ประวัติรับเข้าทั้งหมด (ไว้คำนวณสต็อคก่อนรับ) ──
    stock_map = {}
    if stock_df is not None and not stock_df.empty and "Qty" in stock_df.columns:
        for _, sr in stock_df.iterrows():
            stock_map[_norm_barcode(sr.get("Barcode", ""))] = \
                pd.to_numeric(sr.get("Qty"), errors="coerce")
    hist = df[["Barcode", "วันที่", "จำนวน"]].copy()
    hist["_bc"]  = hist["Barcode"].apply(_norm_barcode)
    hist["_qty"] = pd.to_numeric(hist["จำนวน"], errors="coerce").fillna(0)

    def _stock_before(bc: str, bill_dt) -> float | None:
        """สต็อคก่อนรับ = สต็อคปัจจุบัน − ยอดรับเข้าตั้งแต่วันบิลถึงวันนี้"""
        cur = stock_map.get(bc)
        if cur is None or pd.isna(cur):
            return None
        received_since = hist.loc[
            (hist["_bc"] == bc) & (hist["วันที่"] >= bill_dt), "_qty"].sum()
        return float(cur) - float(received_since)

    price_col = _find_price_col(df)
    if price_col is None:
        st.error("❌ ไม่พบคอลัมน์ราคาต่อหน่วยใน Purchase_Invoices "
                 f"(หาจาก: {', '.join(_PRICE_COL_CANDIDATES)})")
        return

    # ── เลือกช่วงวันที่ ────────────────────────────────────────
    d_min = df["วันที่"].min().date()
    d_max = df["วันที่"].max().date()
    def_from, def_to = _fiscal_default_range()
    def_from = max(def_from, d_min)
    def_to   = min(max(def_to, d_min), d_max)

    c1, c2 = st.columns([3, 1])
    with c1:
        rng = st.date_input("📅 ช่วงวันที่บิลซื้อ", value=(def_from, def_to),
                            min_value=d_min, max_value=d_max,
                            format="DD/MM/YYYY", key="ah_rng")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="ah_ref", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not (isinstance(rng, tuple) and len(rng) == 2):
        st.caption("เลือกวันเริ่ม–วันสิ้นสุดให้ครบก่อน")
        return
    date_from, date_to = rng

    sel = df[(df["วันที่"].dt.date >= date_from) & (df["วันที่"].dt.date <= date_to)]
    if sel.empty:
        st.info("ไม่พบบิลซื้อในช่วงวันที่นี้")
        return

    # ── merge mapping + supplier code ─────────────────────────
    enriched = enrich_purchase(sel, mapping)
    supp_map = dict(zip(suppliers["pos_supplier_name"], suppliers["acc_supp_code"]))

    for nc in ("จำนวน", price_col, "ยอดรวมสินค้า"):
        if nc in enriched.columns:
            enriched[nc] = pd.to_numeric(enriched[nc], errors="coerce").fillna(0)

    name_col = "ชื่อสินค้า" if "ชื่อสินค้า" in enriched.columns else "Name"

    bills = []
    grp = enriched.sort_values("วันที่").groupby(
        ["InvoiceNo", "ชื่อบริษัทผู้ขาย"], sort=False)
    for (inv, vendor), g in grp:
        bdate = g["วันที่"].iloc[0]
        items = []
        for _, r in g.iterrows():
            qty   = float(r.get("จำนวน", 0) or 0)
            price = float(r.get(price_col, 0) or 0)
            total = float(r.get("ยอดรวมสินค้า", 0) or 0)
            if not total:
                total = qty * price
            bc = _norm_barcode(r.get("Barcode", ""))
            items.append({
                "acc_code": r["acc_code"], "acc_name": r["acc_name"],
                "acc_unit": r["acc_unit"],
                "pos_name": str(r.get(name_col, "")),
                "barcode":  bc,
                "stock_before": _stock_before(bc, bdate),
                "qty": qty, "price": price, "total": total,
            })
        bills.append({
            "invoice": str(inv), "vendor": str(vendor),
            "date_str": bdate.strftime("%d/%m/%Y"),
            "supp_code": supp_map.get(str(vendor).strip(), ""),
            "items": items,
            "total": sum(i["total"] for i in items),
        })

    # ── สรุปบนจอ ───────────────────────────────────────────────
    n_items   = sum(len(b["items"]) for b in bills)
    n_unknown = sum(1 for b in bills for i in b["items"] if not i["acc_code"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🧾 จำนวนบิล", f"{len(bills):,}")
    m2.metric("📦 รายการสินค้า", f"{n_items:,}")
    m3.metric("⚠️ ไม่รู้รหัส", f"{n_unknown:,}")
    m4.metric("💰 ยอดรวม", f"฿{sum(b['total'] for b in bills):,.0f}")
    if n_unknown:
        st.caption("รายการสีเหลืองในใบพิมพ์ = ไม่พบใน mapping — เติมรหัสด้วยมือ "
                   "หรืออัปเดต product_mapping.csv แล้วกด Refresh")

    # ── แสดงตัวอย่าง + พิมพ์ ──────────────────────────────────
    html_doc = _build_print_html(bills, date_from, date_to)

    st.download_button(
        "📄 ดาวน์โหลดไฟล์พิมพ์ (เปิดแล้วกดพิมพ์ / Save as PDF)",
        data=html_doc.encode("utf-8"),
        file_name=f"ใบอ้างอิงบัญชี_{date_from:%Y%m%d}-{date_to:%Y%m%d}.html",
        mime="text/html", use_container_width=True)

    with st.expander("🖨️ ดูตัวอย่าง + พิมพ์จากหน้านี้", expanded=True):
        st.components.v1.html(html_doc, height=700, scrolling=True)
