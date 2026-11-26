import unittest
from datetime import datetime

import pandas as pd

from receiving_helper import build_receiving_print_html, prepare_receiving_bills


class ReceivingPrintTests(unittest.TestCase):
    def test_duplicate_mapping_does_not_multiply_receipt_rows(self):
        receipts = pd.DataFrame([
            {"InvoiceNo": "INV1", "ชื่อบริษัทผู้ขาย": "ผู้ขาย A", "วันที่": "2026-02-07 09:32:57.475699",
             "Barcode": "00123", "ชื่อสินค้า": "สี PYLAC", "จำนวน": 2, "หน่วย": "กระป๋อง"},
            {"InvoiceNo": "INV1", "ชื่อบริษัทผู้ขาย": "ผู้ขาย A", "วันที่": "2026-02-07 09:32:58",
             "Barcode": "00123", "ชื่อสินค้า": "สี PYLAC", "จำนวน": 3, "หน่วย": "กระป๋อง"},
        ])
        mapping = pd.DataFrame({"Barcode": ["00123", "00123", "00123"], "ShelfMap": ["A-01", "A-01", "B-02"]})
        original = receipts.copy(deep=True)
        bills = prepare_receiving_bills(receipts, mapping)
        self.assertEqual(len(bills), 1)
        self.assertEqual(len(bills[0]["items"]), 2)
        self.assertEqual([i["qty"] for i in bills[0]["items"]], ["2", "3"])
        self.assertEqual(bills[0]["items"][0]["shelf"], "A-01 / B-02")
        self.assertEqual(bills[0]["items"][0]["barcode"], "00123")
        pd.testing.assert_frame_equal(receipts, original)

    def test_missing_columns_and_unknown_shelf_are_printable(self):
        bills = prepare_receiving_bills(pd.DataFrame({"Name": ["สินค้าไม่มีรหัส"], "Qty": [1.5]}), pd.DataFrame())
        item = bills[0]["items"][0]
        self.assertTrue(item["missing_shelf"])
        self.assertEqual(item["qty"], "1.5")
        self.assertEqual(item["unit"], "—")
        html = build_receiving_print_html(bills)
        self.assertIn("ยังไม่ได้ระบุ", html)
        self.assertIn('class="unk"', html)

    def test_numeric_barcode_and_empty_mapping(self):
        rows = pd.DataFrame({"Barcode": [123.0, None], "Name": ["A", "B"], "Qty": [0, -2]})
        mapping = pd.DataFrame({"Barcode": ["123", ""], "ShelfMap": ["C-03", "DO NOT MATCH"]})
        items = prepare_receiving_bills(rows, mapping)[0]["items"]
        self.assertEqual(items[0]["shelf"], "C-03")
        self.assertEqual(items[0]["qty"], "0")
        self.assertTrue(items[1]["missing_shelf"])
        self.assertEqual(items[1]["qty"], "-2")

    def test_same_invoice_other_supplier_remains_separate(self):
        rows = pd.DataFrame({"InvoiceNo": ["1", "1"], "ชื่อบริษัทผู้ขาย": ["A", "B"],
                             "วันที่": ["2026-02-26 09:13:47", "2026-02-26 09:13:47.001"], "Name": ["A", "B"]})
        bills = prepare_receiving_bills(rows, None)
        self.assertEqual(len(bills), 2)
        self.assertNotEqual(bills[0]["id"], bills[1]["id"])

    def test_html_escapes_sheet_text_and_preserves_a4_print_rules(self):
        rows = pd.DataFrame({"Name": ['สี <script>alert(1)</script> & "A"'], "Qty": [2]})
        html = build_receiving_print_html(prepare_receiving_bills(rows, None), datetime(2026, 11, 26, 10, 0))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("size: A4 portrait", html)
        self.assertIn("table-header-group", html)
        self.assertIn("window.print()", html)
        self.assertIn("26/11/2026 10:00", html)

    def test_empty_receipts(self):
        self.assertEqual(prepare_receiving_bills(pd.DataFrame(), None), [])


if __name__ == "__main__":
    unittest.main()
