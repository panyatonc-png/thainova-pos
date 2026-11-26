"""ใบรับเข้า / จัดสินค้าขึ้นชั้น: เอกสาร A4 สำหรับพิมพ์หรือ Save as PDF."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html import escape
import re

import pandas as pd


def _text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _barcode(value):
    # Sheets บางครั้งอ่าน Barcode ตัวเลขเป็น float; เก็บเลขศูนย์นำหน้าของ string ไว้
    text = _text(value)
    return re.sub(r"^(\d+)\.0+$", r"\1", text)


def prepare_receiving_bills(receipts, shelf_map):
    """จับคู่ชั้นด้วย Barcode โดยไม่เพิ่ม/ตัดแถวหรือเปลี่ยนจำนวนรับเข้า."""
    if receipts is None or receipts.empty:
        return []
    df = receipts.copy()
    date_values = df["วันที่"] if "วันที่" in df else pd.Series("", index=df.index)
    df["_receipt_date"] = pd.to_datetime(
        date_values.astype(str).str.strip(), errors="coerce", format="mixed"
    ).dt.strftime("%Y-%m-%d").fillna("")
    for col in ("InvoiceNo", "ชื่อบริษัทผู้ขาย"):
        df[col] = df[col].map(_text) if col in df else ""

    shelves = {}
    if shelf_map is not None and {"Barcode", "ShelfMap"}.issubset(shelf_map.columns):
        for bc, location in shelf_map[["Barcode", "ShelfMap"]].itertuples(index=False, name=None):
            bc, location = _barcode(bc), _text(location)
            if bc and location:
                locations = shelves.setdefault(bc, [])
                if location not in locations:
                    locations.append(location)

    bills = []
    # รวมแถวบิลเดียวกันในวันเดียวกัน แม้เวลารับเข้าต่างกันระดับ microseconds
    groups = df.sort_values("_receipt_date", ascending=False, kind="stable").groupby(
        ["InvoiceNo", "ชื่อบริษัทผู้ขาย", "_receipt_date"], sort=False, dropna=False
    )
    for (invoice, vendor, date_iso), group in groups:
        items = []
        for _, row in group.iterrows():
            bc = _barcode(row.get("Barcode"))
            name = next((_text(row.get(c)) for c in ("ชื่อสินค้า", "Name") if _text(row.get(c))), "ไม่ระบุชื่อสินค้า")
            quantity = next((_text(row.get(c)) for c in ("จำนวน", "Qty") if _text(row.get(c))), "—")
            unit = next((_text(row.get(c)) for c in ("หน่วย", "หน่วยนับ", "Unit", "UnitName") if _text(row.get(c))), "—")
            location = " / ".join(shelves.get(bc, []))
            items.append({"name": name, "barcode": bc, "qty": quantity,
                          "unit": unit, "shelf": location or "ยังไม่ได้ระบุ",
                          "missing_shelf": not location})
        identity = "\x1f".join((invoice, vendor, date_iso))
        bills.append({
            "id": sha256(identity.encode("utf-8")).hexdigest()[:16],
            "invoice": invoice or "ไม่ระบุเลขบิล", "vendor": vendor or "ไม่ระบุผู้ขาย",
            "date_iso": date_iso,
            "date_str": datetime.strptime(date_iso, "%Y-%m-%d").strftime("%d/%m/%Y") if date_iso else "ไม่ระบุวันที่",
            "items": items,
        })
    return bills


def build_receiving_print_html(bills, printed_at=None):
    """รูปแบบ A4/Sarabun/toolbar แบบใบอ้างอิงบัญชี พร้อมช่องตรวจจัดสินค้า."""
    printed_at = printed_at or datetime.now(timezone(timedelta(hours=7)))
    blocks = []
    for number, bill in enumerate(bills, 1):
        rows = []
        for index, item in enumerate(bill["items"], 1):
            cls = ' class="unk"' if item["missing_shelf"] else ""
            rows.append(
                f'<tr{cls}><td class="center">{index}</td>'
                f'<td>{escape(item["name"])}<br><span class="bc">{escape(item["barcode"] or "ไม่มีบาร์โค้ด")}</span></td>'
                f'<td class="num">{escape(item["qty"])}</td><td class="center">{escape(item["unit"])}</td>'
                f'<td class="shelf">{escape(item["shelf"])}</td>'
                '<td class="center"><span class="check" aria-label="ช่องตรวจจัดเสร็จ"></span></td></tr>'
            )
        missing = sum(item["missing_shelf"] for item in bill["items"])
        note = f" · ยังไม่ระบุที่วาง {missing} รายการ" if missing else ""
        blocks.append(f"""
<section class="bill">
  <table>
    <colgroup><col style="width:5%"><col style="width:43%"><col style="width:10%">
      <col style="width:10%"><col style="width:24%"><col style="width:8%"></colgroup>
    <thead>
      <tr><th colspan="6" class="bill-head"><span class="muted">บิลที่ {number}/{len(bills)}</span>
        · <b>{escape(bill['vendor'])}</b> · เลขบิล {escape(bill['invoice'])} · {escape(bill['date_str'])}</th></tr>
      <tr><th class="center">#</th><th>สินค้า / บาร์โค้ด</th><th class="num">จำนวนรับ</th>
        <th class="center">หน่วย</th><th>ที่อยู่สินค้า / ชั้นวาง</th><th class="center">จัดแล้ว</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
    <tfoot><tr><td colspan="6"><b>รวมบิลนี้ {len(bill['items'])} รายการ{note}</b></td></tr></tfoot>
  </table>
  <div class="bill-foot"><span>ผู้จัดสินค้า: ____________________</span>
    <span>ผู้ตรวจ: ____________________</span><span>วันที่: ______________</span></div>
</section>""")
    item_count = sum(len(b["items"]) for b in bills)
    missing_count = sum(i["missing_shelf"] for b in bills for i in b["items"])
    dates = sorted(b["date_iso"] for b in bills if b["date_iso"])
    date_label = ""
    if dates:
        first = datetime.strptime(dates[0], "%Y-%m-%d").strftime("%d/%m/%Y")
        last = datetime.strptime(dates[-1], "%Y-%m-%d").strftime("%d/%m/%Y")
        date_label = f" · วันที่รับเข้า {first}" + (f" ถึง {last}" if last != first else "")
    return f"""<!DOCTYPE html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ใบรับเข้าและจัดสินค้าขึ้นชั้น - ThaiNova AutoPaint</title>
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ font-family: 'Sarabun', Tahoma, sans-serif; font-size: 13px; color: #1a1a1a;
    background: #fff; padding: 20px; }}
  @page {{ size: A4 portrait; margin: 12mm 10mm; }}
  .paper {{ max-width: 190mm; margin: auto; }}
  .doc-head {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between;
    align-items: flex-end; border-bottom: 2px solid #1a1a1a; padding-bottom: 6px; }}
  h1 {{ font-size: 17px; font-weight: 700; }}
  .sub {{ font-size: 11.5px; color: #555; }}
  .muted {{ color: #666; }}
  .bill {{ margin-top: 14px; }}
  table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 11.5px; }}
  thead {{ display: table-header-group; }}
  tfoot {{ display: table-row-group; }}
  tr {{ break-inside: avoid; page-break-inside: avoid; }}
  th {{ border-bottom: 1.5px solid #1a1a1a; text-align: left; padding: 5px 4px; }}
  td {{ border-bottom: .5px solid #ddd; padding: 6px 4px; vertical-align: top; }}
  td, th {{ overflow-wrap: anywhere; }}
  .bill-head {{ background: #f0f0ee; padding: 7px 10px; font-size: 12.5px; }}
  .bc {{ font-size: 10.5px; color: #777; }}
  .num {{ text-align: right; }} .center {{ text-align: center; }}
  .shelf {{ font-weight: 700; }}
  .unk td {{ background: #FAEEDA; }}
  .check {{ display: inline-block; width: 13px; height: 13px; border: 1px solid #444; margin-top: 2px; }}
  tfoot td {{ border-top: 1.5px solid #1a1a1a; border-bottom: none; }}
  .bill-foot {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px;
    margin-top: 7px; font-size: 11px; color: #555; break-inside: avoid; }}
  .grand {{ margin-top: 18px; text-align: right; font-size: 14px; font-weight: 700;
    border-top: 2px solid #1a1a1a; padding-top: 8px; }}
  .note {{ margin-top: 8px; font-size: 10.5px; color: #666; }}
  .toolbar {{ position: sticky; top: 0; background: #1a1a1a; color: #fff;
    padding: 10px 16px; margin: -20px -20px 16px; display: flex; flex-wrap: wrap;
    gap: 8px; justify-content: space-between; align-items: center; }}
  .toolbar button {{ font-family: inherit; font-size: 15px; font-weight: 700;
    background: #C9A84C; color: #1a1a1a; border: none; border-radius: 8px;
    padding: 8px 22px; cursor: pointer; }}
  @media print {{ .toolbar {{ display: none; }} body {{ padding: 0; }}
    .paper {{ max-width: none; }} * {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }} }}
</style></head><body>
<div class="toolbar"><span>กด "พิมพ์" แล้วเลือกเครื่องพิมพ์ หรือ Save as PDF</span>
  <button onclick="printDocument()">🖨️ พิมพ์ / บันทึก PDF</button></div>
<main class="paper">
  <header class="doc-head"><div><h1>ใบรับเข้าและจัดสินค้าขึ้นชั้น</h1>
    <div class="sub">ThaiNova AutoPaint{date_label}</div></div>
    <div class="sub">พิมพ์เมื่อ {printed_at:%d/%m/%Y %H:%M} (เวลาไทย)<br>ทั้งหมด {len(bills)} บิล</div></header>
  {''.join(blocks)}
  <div class="grand">รวม {len(bills)} บิล · {item_count} รายการ</div>
  <div class="note">ตำแหน่งชั้นวางอ้างอิง Shelf_Map ณ เวลาสร้างใบพิมพ์ · ช่องจัดแล้วสำหรับตรวจงานหน้างาน<br>
    แถวสีเหลือง = ยังไม่ได้ระบุตำแหน่ง ({missing_count} รายการ) โปรดตรวจสอบก่อนนำขึ้นชั้น</div>
</main>
<script>async function printDocument() {{ if (document.fonts) await document.fonts.ready; window.print(); }}</script>
</body></html>"""


def _render_print_controls(bills, key):
    import streamlit as st
    html_doc = build_receiving_print_html(bills)
    name = bills[0]["date_iso"].replace("-", "") or "undated"
    st.download_button(
        "📄 ดาวน์โหลดไฟล์พิมพ์ (เปิดแล้วกดพิมพ์ / Save as PDF)",
        data=html_doc.encode("utf-8"), file_name=f"ใบจัดสินค้ารับเข้า_{name}_{key}.html",
        mime="text/html", use_container_width=True, key=f"receiving_download_{key}")
    with st.expander("🖨️ ดูตัวอย่าง + พิมพ์จากหน้านี้", expanded=True):
        st.components.v1.html(html_doc, height=700, scrolling=True)


def render_receiving_documents(receipts, shelf_map):
    """รายการบิลในเดือนที่เลือก และการพิมพ์รวม/แยกบิลเฉพาะหน้ารับเข้า."""
    import streamlit as st
    bills = prepare_receiving_bills(receipts, shelf_map)
    if not bills:
        st.info("ไม่พบรายการรับเข้าในช่วงเวลานี้")
        return
    labels = {b["id"]: f"{b['date_str']} · {b['vendor']} · {b['invoice']}" for b in bills}
    selection_key = sha256("|".join(labels).encode()).hexdigest()[:12]
    st.markdown("**🖨️ ใบรับเข้าและจัดสินค้าขึ้นชั้น (A4)**")
    chosen = st.multiselect(
        "เลือกบิลสำหรับพิมพ์รวม", options=list(labels), default=list(labels),
        format_func=labels.get, key=f"receiving_bills_{selection_key}")
    selected = [b for b in bills if b["id"] in chosen]
    if selected:
        c1, c2, c3 = st.columns(3)
        c1.metric("🧾 บิลที่เลือก", len(selected))
        c2.metric("📦 รายการรับเข้า", sum(len(b["items"]) for b in selected))
        c3.metric("⚠️ ยังไม่ระบุที่วาง", sum(i["missing_shelf"] for b in selected for i in b["items"]))
    # เก็บเฉพาะลายเซ็นเอกสาร ไม่เก็บ HTML เก่าข้ามข้อมูลหรือข้ามเดือน
    fingerprint = sha256(repr(selected).encode()).hexdigest()
    if st.button("🖨️ เตรียมพิมพ์บิลที่เลือก / PDF", key="receiving_prepare_all",
                 type="primary", use_container_width=True, disabled=not selected):
        st.session_state["receiving_prepared"] = fingerprint
    if selected and st.session_state.get("receiving_prepared") == fingerprint:
        _render_print_controls(selected, f"all_{fingerprint[:12]}")

    st.caption("พิมพ์แยกบิลได้ด้านล่าง · ในหน้าพิมพ์เลือก Save as PDF เพื่อบันทึกเป็นไฟล์ PDF")
    for bill in bills:
        with st.expander(f"📄 {labels[bill['id']]}"):
            st.dataframe(pd.DataFrame([
                {"สินค้า": i["name"], "บาร์โค้ด": i["barcode"], "จำนวน": i["qty"],
                 "หน่วย": i["unit"], "ที่วาง": i["shelf"]} for i in bill["items"]
            ]), use_container_width=True, hide_index=True)
            bill_fingerprint = sha256(repr(bill).encode()).hexdigest()
            if st.button("🖨️ พิมพ์บิลนี้ / PDF", key=f"receiving_print_{bill['id']}"):
                st.session_state["receiving_single_prepared"] = bill_fingerprint
            if st.session_state.get("receiving_single_prepared") == bill_fingerprint:
                _render_print_controls([bill], bill["id"])
