import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import requests, hmac, hashlib, time, json, io, base64, os

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

st.set_page_config(page_title="ThaiNova AutoPaint", page_icon="🎨",
                   layout="wide", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Sarabun:wght@300;400;500;600&display=swap');

:root {
  --red:#E8192C; --red-dark:#B5101F; --red-dim:#3a0a0e;
  --bg:#0a0a0a; --surface:#141414; --surface2:#1e1e1e; --surface3:#252525;
  --border:#2a2a2a; --border-red:rgba(232,25,44,0.3);
  --text:#f0f0f0; --muted:#888; --muted2:#555; --gold:#C9A84C;
  --green:#4ade80; --green-dim:rgba(74,222,128,0.1);
}
html,body,[class*="css"]{font-family:'Sarabun',sans-serif!important;}
.stApp{background:var(--bg)!important;color:var(--text)!important;}
#MainMenu,footer,header{visibility:hidden;}
section[data-testid="stSidebar"]{display:none!important;}
.block-container{padding:0!important;max-width:100%!important;}

/* ── Topnav ── */
.topnav{background:var(--surface);border-bottom:1px solid var(--border);
  padding:0 20px;height:54px;display:flex;align-items:center;
  justify-content:space-between;position:sticky;top:0;z-index:200;}
.brand{font-family:'Barlow Condensed',sans-serif;font-weight:900;
  font-size:20px;letter-spacing:2px;}
.brand span{color:var(--red);}
.nav-right{display:flex;align-items:center;gap:10px;}
.sync-pill{font-size:10px;color:var(--green);background:var(--green-dim);
  border:1px solid rgba(74,222,128,.2);padding:3px 9px;border-radius:12px;}
.cart-chip{background:var(--red-dim);border:1px solid var(--border-red);
  color:var(--red);padding:4px 12px;border-radius:20px;font-size:12px;
  font-weight:700;cursor:pointer;font-family:'Sarabun',sans-serif;}

/* ── Page nav buttons ── */
.stButton>button{
  background:var(--surface2)!important;color:var(--muted)!important;
  border:1px solid var(--border)!important;border-radius:8px!important;
  font-family:'Sarabun',sans-serif!important;font-size:12px!important;
  font-weight:500!important;padding:6px 4px!important;transition:all .2s!important;}
.stButton>button:hover{background:var(--surface3)!important;color:var(--text)!important;
  border-color:var(--border-red)!important;}
.stButton>button[kind="primary"]{
  background:var(--red)!important;color:#fff!important;
  border-color:var(--red)!important;}
.stButton>button[kind="primary"]:hover{background:var(--red-dark)!important;}

/* ── Back button ── */
.back-btn>button{background:transparent!important;color:var(--muted)!important;
  border:none!important;font-size:13px!important;}
.back-btn>button:hover{color:var(--text)!important;background:transparent!important;}

/* ── Hero ── */
.hero-card{background:linear-gradient(135deg,#1a0408 0%,#0f0f0f 60%,#1a0a00 100%);
  border:1px solid var(--border-red);border-radius:12px;padding:24px;
  margin-bottom:16px;position:relative;overflow:hidden;}
.hero-card::before{content:'';position:absolute;top:-30px;right:-30px;
  width:160px;height:160px;
  background:radial-gradient(circle,rgba(232,25,44,.12) 0%,transparent 70%);}
.hero-tag{font-size:10px;letter-spacing:3px;color:var(--red);
  text-transform:uppercase;margin-bottom:6px;}
.hero-title{font-family:'Barlow Condensed',sans-serif;font-size:38px;
  font-weight:900;line-height:1;letter-spacing:1px;margin-bottom:8px;}
.hero-title em{color:var(--red);font-style:normal;}
.hero-sub{font-size:12px;color:var(--muted);margin-bottom:16px;line-height:1.6;}
.hero-stats{display:flex;gap:24px;padding-top:14px;border-top:1px solid var(--border);
  flex-wrap:wrap;}
.hstat-num{font-family:'Barlow Condensed',sans-serif;font-size:26px;
  font-weight:700;color:var(--red);}
.hstat-lbl{font-size:10px;color:var(--muted);}

/* ── Section title ── */
.sec-title{font-family:'Barlow Condensed',sans-serif;font-size:16px;
  font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;}
.sec-title::before{content:'';display:inline-block;width:3px;height:14px;
  background:var(--red);border-radius:2px;margin-right:8px;vertical-align:middle;}

/* ── Product grid (2-col) ── */
.pcg-card{background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:12px;margin-bottom:4px;transition:border-color .2s;}
.pcg-card:hover{border-color:var(--border-red);}
.pcg-swatch{width:40px;height:40px;border-radius:8px;border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:8px;}
.pcg-name{font-size:12px;font-weight:600;color:var(--text);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px;}
.pcg-brand{font-size:10px;color:var(--muted);margin-bottom:6px;}
.pcg-price{font-family:'Barlow Condensed',sans-serif;font-size:22px;
  font-weight:700;color:var(--text);margin-bottom:2px;}
.dot-ok{color:var(--green);}.dot-low{color:var(--gold);}.dot-out{color:var(--red);}

/* ── Cart page ── */
.cart-item-row{background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:12px 14px;margin-bottom:8px;
  display:flex;align-items:center;gap:12px;}
.ci-icon{width:42px;height:42px;background:var(--surface2);border-radius:8px;
  display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
.ci-name{font-size:13px;font-weight:600;flex:1;}
.ci-price{font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:700;}
.cart-total-box{background:var(--surface);border:1px solid var(--border-red);
  border-radius:10px;padding:14px 18px;margin:12px 0;}
.ct-row{display:flex;justify-content:space-between;font-size:13px;padding:4px 0;}
.ct-total{font-family:'Barlow Condensed',sans-serif;font-size:26px;
  font-weight:700;color:var(--red);}

/* ── Checkout wizard ── */
.wizard{display:flex;align-items:center;margin:16px 0 20px;}
.wstep{display:flex;flex-direction:column;align-items:center;gap:4px;}
.wnum{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:12px;font-weight:700;}
.wnum.done{background:var(--green);color:#000;}
.wnum.active{background:var(--red);color:#fff;
  box-shadow:0 0 0 3px rgba(232,25,44,.2);}
.wnum.idle{background:var(--surface2);color:var(--muted);border:1px solid var(--border);}
.wlabel{font-size:9px;color:var(--muted);letter-spacing:.5px;}
.wlabel.active{color:var(--red);}
.wline{flex:1;height:2px;background:var(--border);margin:0 4px 14px;}
.wline.done{background:var(--green);}

/* ── Checkout form sections ── */
.co-section{background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:18px;margin-bottom:12px;}
.co-section-title{font-size:11px;color:var(--muted);letter-spacing:.8px;
  text-transform:uppercase;margin-bottom:14px;font-weight:600;}
.delivery-opt{background:var(--surface2);border:1.5px solid var(--border);
  border-radius:10px;padding:12px 14px;margin-bottom:8px;cursor:pointer;
  display:flex;align-items:center;gap:12px;transition:all .2s;}
.delivery-opt.sel{border-color:var(--red);background:var(--red-dim);}

/* ── Vehicle option ── */
.v-opt{background:var(--surface2);border:1.5px solid var(--border);
  border-radius:10px;padding:10px 12px;margin-bottom:6px;cursor:pointer;
  display:flex;align-items:center;gap:10px;transition:all .2s;}
.v-opt.sel{border-color:var(--red);background:var(--red-dim);}
.v-icon{font-size:22px;flex-shrink:0;}
.v-name{font-size:12px;font-weight:600;}
.v-detail{font-size:10px;color:var(--muted);}
.v-price{font-family:'Barlow Condensed',sans-serif;font-size:18px;
  font-weight:700;margin-left:auto;text-align:right;}
.v-eta{font-size:9px;color:var(--muted);}

/* ── Payment options ── */
.pay-opt{background:var(--surface2);border:1.5px solid var(--border);
  border-radius:10px;padding:14px;margin-bottom:8px;cursor:pointer;
  transition:all .2s;}
.pay-opt.sel{border-color:var(--green);background:rgba(74,222,128,.05);}

/* ── Order summary ── */
.sum-card{background:var(--surface2);border:1px solid var(--border);
  border-radius:10px;padding:14px;margin-bottom:12px;}
.sum-row{display:flex;justify-content:space-between;font-size:12px;
  padding:5px 0;border-bottom:1px solid var(--border);}
.sum-row:last-child{border-bottom:none;padding-top:8px;font-weight:700;font-size:14px;}
.sum-row:last-child span:last-child{color:var(--red);}

/* ── Confirmed page ── */
.confirm-wrap{text-align:center;padding:40px 20px 30px;}
.confirm-icon{font-size:60px;margin-bottom:12px;}
.confirm-title{font-family:'Barlow Condensed',sans-serif;font-size:30px;
  font-weight:900;letter-spacing:1px;margin-bottom:4px;}
.confirm-sub{font-size:13px;color:var(--muted);margin-bottom:20px;}
.order-num-box{background:var(--red-dim);border:1px solid var(--border-red);
  border-radius:10px;padding:12px 20px;display:inline-block;margin-bottom:20px;}
.order-num-label{font-size:10px;color:var(--red);letter-spacing:1px;
  text-transform:uppercase;}
.order-num-val{font-family:'Barlow Condensed',sans-serif;font-size:28px;
  font-weight:900;color:var(--text);}
.qr-box{background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:16px;text-align:center;margin-bottom:12px;}

/* ── Contact ── */
.contact-card{background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:16px 18px;margin-bottom:10px;}
.contact-row{display:flex;align-items:center;gap:12px;
  padding:10px 0;border-bottom:1px solid var(--border);}
.contact-row:last-child{border-bottom:none;padding-bottom:0;}
.contact-icon{width:36px;height:36px;background:var(--red-dim);
  border:1px solid var(--border-red);border-radius:8px;
  display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;}
.call-btn{margin-left:auto;background:var(--surface2);border:1px solid var(--border);
  color:var(--text);padding:5px 12px;border-radius:6px;font-size:11px;
  cursor:pointer;text-decoration:none;font-family:'Sarabun',sans-serif;}
.hours-row{display:flex;justify-content:space-between;font-size:13px;
  padding:7px 0;border-bottom:1px solid var(--border);}
.hours-row:last-child{border-bottom:none;}

/* ── Admin ── */
.pill{display:inline-block;padding:2px 8px;border-radius:12px;font-size:9px;font-weight:700;}
.pill-ok{background:rgba(74,222,128,.1);color:var(--green);border:1px solid rgba(74,222,128,.2);}
.pill-low{background:rgba(201,168,76,.12);color:var(--gold);border:1px solid rgba(201,168,76,.2);}
.pill-out{background:rgba(232,25,44,.12);color:var(--red);border:1px solid rgba(232,25,44,.2);}

/* ── Lalamove delivery page ── */
.lala-card{background:var(--surface);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;margin-bottom:14px;}
.lala-head{padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:10px;}
.lala-logo{width:36px;height:36px;background:#FF6600;border-radius:8px;
  display:flex;align-items:center;justify-content:center;
  font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:900;color:#fff;}
.lala-body{padding:18px;}
.addr-box{background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.2);
  border-radius:8px;padding:10px 12px;font-size:12px;line-height:1.5;}

/* ── Streamlit overrides ── */
[data-testid="stMetricValue"]{color:var(--red)!important;
  font-family:'Barlow Condensed',sans-serif!important;font-size:1.8rem!important;}
[data-testid="stMetricLabel"]{color:var(--muted)!important;font-size:.72rem!important;}
[data-testid="metric-container"]{background:var(--surface)!important;
  border:1px solid var(--border)!important;border-radius:10px!important;}
.stTextInput>div>div>input,.stNumberInput>div>div>input{
  background:var(--surface2)!important;border:1px solid var(--border)!important;
  color:var(--text)!important;border-radius:8px!important;
  font-family:'Sarabun',sans-serif!important;}
.stTextInput>div>div>input:focus{border-color:var(--border-red)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--surface)!important;
  border-radius:10px!important;border:1px solid var(--border)!important;padding:4px!important;}
.stTabs [data-baseweb="tab"]{color:var(--muted)!important;border-radius:8px!important;
  font-family:'Sarabun',sans-serif!important;}
.stTabs [aria-selected="true"]{background:var(--red)!important;color:#fff!important;}
.stDataFrame{border:1px solid var(--border)!important;border-radius:10px!important;}
.streamlit-expanderHeader{background:var(--surface2)!important;
  border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}
.streamlit-expanderContent{background:var(--surface)!important;border-color:var(--border)!important;}
hr{border-color:var(--border)!important;}
.stSelectbox>div>div{background:var(--surface2)!important;
  border-color:var(--border)!important;color:var(--text)!important;}
.stRadio label{color:var(--text)!important;font-family:'Sarabun',sans-serif!important;}
div[data-testid="stContainer"]{background:transparent;}
.stAlert{border-radius:10px!important;}
p{margin:0;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════
_defaults = {
    'cart': {}, 'logged_in': False, 'role': 'guest', 'page': 'home',
    'checkout_step': 1,
    'cust_name': '', 'cust_phone': '',
    'delivery_method': 'lalamove',
    'checkout_addr': '', 'checkout_lat': None, 'checkout_lng': None,
    'checkout_vehicle': 'MOTORCYCLE',
    'checkout_quote_id': None, 'checkout_quote_price': None, 'checkout_quote_dist': None,
    'lala_pay_type': 'sender',
    'payment_method': 'promptpay',
    'order_id': None, 'order_lala_id': None, 'order_share_link': None,
    'dest_lat': None, 'dest_lng': None, 'dest_addr': '',
    'quotation_id': None, 'sel_vehicle': 'MOTORCYCLE',
    'quoted_price': '', 'quoted_dist': '', 'quoted_vehicle': '',
    'sel_cat': 'ทั้งหมด',
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def load_data():
    stock_df     = conn.read(worksheet="Stock")
    reorder_df   = conn.read(worksheet="Reorder_All")
    shelf_map_df = conn.read(worksheet="Shelf_Map")
    purchase_df  = conn.read(worksheet="Purchase_Invoices")
    lot_df       = conn.read(worksheet="Lot_Tracking")
    merged = pd.merge(stock_df, shelf_map_df[['Barcode','ShelfMap']], on='Barcode', how='left')
    merged['ShelfMap'] = merged['ShelfMap'].fillna("ยังไม่ได้ระบุ")
    return merged, reorder_df, shelf_map_df, purchase_df, lot_df

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
STORE_LAT = "13.8468093"
STORE_LNG  = "100.7982969"

VEHICLES = {
    "MOTORCYCLE": {"label":"🛵 Motorbike",    "price":79,  "eta":"30-45 นาที", "detail":"≤ 20 kg · สีขนาดเล็ก"},
    "CAR":        {"label":"🚗 Sedan/Eco Car","price":149, "eta":"45-60 นาที", "detail":"≤ 50 kg · หลายกระป๋อง"},
    "VAN":        {"label":"🚐 Van/Truck",    "price":249, "eta":"60-90 นาที", "detail":"≤ 500 kg · ล็อตใหญ่"},
}

# -- Cart --
def add_to_cart(barcode, name, price, qty, max_stock):
    cur = st.session_state.cart.get(barcode, {}).get('qty', 0)
    nq  = cur + qty
    if nq > max_stock:
        st.toast(f"⚠️ มีเพียง {max_stock} ชิ้น"); return
    st.session_state.cart[barcode] = {'name': name, 'price': price, 'qty': nq, 'max': max_stock}
    st.toast(f"✅ เพิ่ม {name[:20]} แล้ว!")

def remove_from_cart(barcode):
    st.session_state.cart.pop(barcode, None)

def cart_total():
    return sum(i['price'] * i['qty'] for i in st.session_state.cart.values())

def cart_count():
    return sum(i['qty'] for i in st.session_state.cart.values())

# -- PromptPay QR --
def _crc16(data: str) -> str:
    crc = 0xFFFF
    for b in data.encode('ascii'):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
        crc &= 0xFFFF
    return format(crc, '04X')

def promptpay_payload(phone: str, amount: float) -> str:
    ph = ''.join(c for c in phone if c.isdigit())
    if ph.startswith('0') and len(ph) == 10:
        ph = '0066' + ph[1:]
    elif ph.startswith('66') and len(ph) == 11:
        ph = '00' + ph
    ph = ph.zfill(13)[:13]
    guid = "A000000677010111"
    acc  = f"00{len(guid):02d}{guid}0113{ph}"   # 20 + 17 = 37 chars
    p = f"000201010211{len(acc):02d}{acc}5303764"
    if amount > 0:
        a = f"{amount:.2f}"
        p += f"54{len(a):02d}{a}"
    name = "ThaiNova AP"
    p += f"5802TH59{len(name):02d}{name}6304"
    return p + _crc16(p)

def gen_qr_b64(phone: str, amount: float):
    if not HAS_QR: return None
    try:
        payload = promptpay_payload(phone, amount)
        img = qrcode.make(payload)
        buf = io.BytesIO(); img.save(buf, 'PNG')
        return base64.b64encode(buf.getvalue()).decode()
    except: return None

# -- Lalamove --
def _lala_sign(key, secret, method, path, body=""):
    ts  = str(int(time.time() * 1000))
    raw = f"{ts}\r\n{method}\r\n{path}\r\n\r\n{body}"
    sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return {"Content-Type":"application/json","Market":"TH","Accept":"application/json",
            "Authorization": f"hmac {key}:{ts}:{sig}"}

def get_quotation(dlat, dlng, service, lkey, lsecret):
    path = "/v3/quotations"
    body = json.dumps({"data":{"serviceType":service,"language":"th_TH","stops":[
        {"coordinates":{"lat":STORE_LAT,"lng":STORE_LNG},"address":"ThaiNova AutoPaint"},
        {"coordinates":{"lat":str(dlat),"lng":str(dlng)},"address":"ปลายทาง"}
    ]}},separators=(',',':'))
    try:
        r = requests.post("https://rest.sandbox.lalamove.com"+path,
                          headers=_lala_sign(lkey,lsecret,"POST",path,body),
                          data=body.encode(), timeout=10)
        d = r.json()
        if r.status_code in [200,201]:
            data  = d.get("data", d)
            dist  = int(data.get("distance",{}).get("value", 0))
            stops = data.get("stops", [])
            # ดึง stopId จริงจาก quotation response — ต้องใช้ตอน create order
            stop_sender    = stops[0].get("stopId","1") if len(stops) > 0 else "1"
            stop_recipient = stops[1].get("stopId","2") if len(stops) > 1 else "2"
            return {"ok":True,
                    "quotation_id":  data.get("quotationId",""),
                    "price":         data.get("priceBreakdown",{}).get("total","-"),
                    "distance":      f"{dist/1000:.1f} km",
                    "stop_sender":   stop_sender,
                    "stop_recipient":stop_recipient}
        return {"ok":False,"error":d}
    except Exception as e:
        return {"ok":False,"error":str(e)}

def create_lala_order(quote_id, stop_sender, stop_recipient, cname, cphone, lkey, lsecret, is_pod=False):
    """สร้าง Lalamove order ด้วย quotationId และ stopId จริงจาก get_quotation()
    Endpoint: https://rest.sandbox.lalamove.com (Sandbox)
    """
    path = "/v3/orders"
    body_dict = {"data":{
        "quotationId": quote_id,
        "sender":    {"stopId": stop_sender,    "name":"ThaiNova AutoPaint","phone":"+66870799199"},
        "recipients":[{"stopId": stop_recipient, "name":cname, "phone":cphone,
                       "remarks":"สีพ่นรถยนต์ ThaiNova"}],
        "isPODEnabled": is_pod,
    }}
    body = json.dumps(body_dict, separators=(',',':'))
    headers = _lala_sign(lkey, lsecret, "POST", path, body)
    try:
        r = requests.post("https://rest.sandbox.lalamove.com"+path,
                          headers=headers, data=body.encode(), timeout=10)
        d = r.json()
        debug = {
            "endpoint":     "https://rest.sandbox.lalamove.com" + path,
            "status_code":  r.status_code,
            "request_body": body_dict,   # ไม่มี api_secret ใน body
            "response":     d,
        }
        if r.status_code in [200, 201]:
            od = d.get("data", d)
            return {"ok":True,  "order_id":od.get("orderId",""),
                    "share_link":od.get("shareLink",""), "debug":debug}
        return {"ok":False, "error":d, "debug":debug}
    except Exception as e:
        return {"ok":False, "error":str(e), "debug":None}

def geocode(addr, mkey=""):
    # Google Maps (ถ้ามี API key)
    if mkey:
        try:
            r = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
                params={"address":addr,"key":mkey,"language":"th","region":"th"},timeout=5)
            d = r.json()
            if d["status"]=="OK":
                loc = d["results"][0]["geometry"]["location"]
                return loc["lat"],loc["lng"],d["results"][0]["formatted_address"]
        except: pass
    # Nominatim fallback (ฟรี ไม่ต้องใช้ API key)
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q":addr+" ประเทศไทย","format":"json","limit":1,"countrycodes":"th"},
            headers={"User-Agent":"ThaiNovaApp/1.0"},timeout=6)
        d = r.json()
        if d:
            return float(d[0]["lat"]),float(d[0]["lon"]),d[0]["display_name"]
    except: pass
    return None,None,None

def gen_order_id():
    return "TN" + datetime.now().strftime("%y%m%d%H%M%S")

def try_save_order(order_data: dict):
    try:
        try:
            orders_df = conn.read(worksheet="Orders")
        except:
            orders_df = pd.DataFrame()
        new_row = pd.DataFrame([order_data])
        updated  = pd.concat([orders_df, new_row], ignore_index=True)
        conn.update(worksheet="Orders", data=updated)
    except: pass

# -- Nav helpers --
def go(page):
    st.session_state.page = page
    st.rerun()

def get_secrets():
    try:
        lk = st.secrets["lalamove"]["api_key"]
        ls = st.secrets["lalamove"]["api_secret"]
        mk = st.secrets["google"]["maps_key"]
        pp = st.secrets.get("store",{}).get("promptpay_phone","0627377700")
        return lk, ls, mk, pp, True
    except:
        return "","","","0627377700",False

# ══════════════════════════════════════════════════════════════
# NAVIGATION
# ══════════════════════════════════════════════════════════════
def render_nav(show_cart=True):
    cc = cart_count()
    cart_html = (
        f'<span class="cart-chip" title="ตะกร้า">🛒 {cc} รายการ · ฿{cart_total():,.0f}</span>'
        if (show_cart and cc > 0) else
        ('<span style="font-size:12px;color:var(--muted)">🛒 ว่าง</span>' if show_cart else '')
    )
    role_badge = '<span style="font-size:11px;color:var(--red);font-weight:700">⚙ Admin</span>' if st.session_state.logged_in else ''
    st.markdown(
        f'<div class="topnav">'
        f'<div class="brand">THAI<span>NOVA</span>'
        f'<span style="color:var(--muted);font-size:12px;font-weight:400;letter-spacing:0;margin-left:6px">AutoPaint</span>'
        f'</div>'
        f'<div class="nav-right">'
        f'<span class="sync-pill">🟢 Live · 5 min</span>'
        f'{role_badge}'
        f'{cart_html}'
        f'</div></div>',
        unsafe_allow_html=True
    )

def render_page_nav(current):
    nav_items = [
        ("home","🏠","หน้าแรก"),("shop","📦","สินค้า"),
        ("delivery","🚚","จัดส่ง"),("colors","🎨","เบอร์สี"),("contact","📍","ติดต่อ"),
    ]
    cols = st.columns(len(nav_items) + (1 if cart_count() > 0 else 0))
    for i,(key,icon,label) in enumerate(nav_items):
        with cols[i]:
            is_active = current == key
            if st.button(f"{icon} {label}", key=f"nav_{key}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                go(key)
    if cart_count() > 0:
        with cols[len(nav_items)]:
            if st.button(f"🛒 {cart_count()}", key="nav_cart", use_container_width=True,
                         type="primary"):
                go('cart')

# ══════════════════════════════════════════════════════════════
# PAGES — CUSTOMER
# ══════════════════════════════════════════════════════════════

def page_home(stock_df):
    st.markdown("""
    <div class="hero-card">
      <div class="hero-tag">ศูนย์รวมสีพ่นรถยนต์ครบวงจร</div>
      <div class="hero-title">สีพ่น<em>คุณภาพ</em><br>ส่งถึงอู่</div>
      <div class="hero-sub">สต็อกเรียลไทม์จาก POS · จัดส่ง Lalamove ภายใน 2 ชั่วโมง<br>Nippon · TOA · Cromax · Standox</div>
      <div class="hero-stats">
        <div><div class="hstat-num">1,200+</div><div class="hstat-lbl">รายการสินค้า</div></div>
        <div><div class="hstat-num">2 ชม.</div><div class="hstat-lbl">จัดส่งเร็ว</div></div>
        <div><div class="hstat-num">98%</div><div class="hstat-lbl">ความพึงพอใจ</div></div>
        <div><div class="hstat-num">Live</div><div class="hstat-lbl">อัปเดต 5 นาที</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    in_stock = len(stock_df[stock_df.get('Qty', pd.Series(dtype=int)) > 0]) if 'Qty' in stock_df.columns else len(stock_df)
    low_stock = len(stock_df[(stock_df.get('Qty',pd.Series(dtype=int))>0) & (stock_df.get('Qty',pd.Series(dtype=int))<=5)]) if 'Qty' in stock_df.columns else 0
    c1.metric("สินค้าพร้อมขาย", f"{in_stock:,} รายการ")
    c2.metric("เหลือน้อย", f"{low_stock} รายการ", delta="ควรสั่งเพิ่ม" if low_stock>0 else None)
    c3.metric("ซิงค์ล่าสุด", datetime.now().strftime("%H:%M"))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-title">สินค้าแนะนำ</div>', unsafe_allow_html=True)

    featured = stock_df[stock_df.get('Qty', pd.Series(dtype=int)) > 5].head(6) if 'Qty' in stock_df.columns else stock_df.head(6)
    cols = st.columns(3)
    for i, (_, row) in enumerate(featured.iterrows()):
        with cols[i % 3]:
            price = float(row.get('RetailPrice', 0))
            st.markdown(f"""
            <div class="pcg-card">
              <div class="pcg-swatch">🎨</div>
              <div class="pcg-name">{row.get('Name','')}</div>
              <div class="pcg-brand">{row.get('CategoryName','')}</div>
              <div class="pcg-price">฿{price:,.0f}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("+ เพิ่มตะกร้า", key=f"fea_{row['Barcode']}", use_container_width=True):
                add_to_cart(row['Barcode'], row['Name'], price, 1, int(row.get('Qty',1)))
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""<div class="co-section" style="text-align:center">
        <div style="font-size:28px;margin-bottom:8px">🚚</div>
        <div style="font-size:13px;font-weight:600;margin-bottom:4px">จัดส่งด่วน</div>
        <div style="font-size:11px;color:var(--muted)">Lalamove ภายใน 2 ชม.<br>ครอบคลุมทั้ง กทม.</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""<div class="co-section" style="text-align:center">
        <div style="font-size:28px;margin-bottom:8px">📊</div>
        <div style="font-size:13px;font-weight:600;margin-bottom:4px">สต็อกเรียลไทม์</div>
        <div style="font-size:11px;color:var(--muted)">ข้อมูลตรงจาก POS<br>อัปเดตทุก 5 นาที</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown("""<div class="co-section" style="text-align:center">
        <div style="font-size:28px;margin-bottom:8px">✅</div>
        <div style="font-size:13px;font-weight:600;margin-bottom:4px">สินค้าคุณภาพ</div>
        <div style="font-size:11px;color:var(--muted)">นำเข้าตรง ถูกลิขสิทธิ์<br>มีใบรับรองทุกล็อต</div>
        </div>""", unsafe_allow_html=True)


def page_shop(stock_df):
    st.markdown('<div class="sec-title">สินค้าทั้งหมด</div>', unsafe_allow_html=True)
    cats = list(stock_df['CategoryName'].dropna().unique()) if 'CategoryName' in stock_df.columns else []
    all_cats = ["ทั้งหมด"] + cats

    # Category chips — หลายแถว, 6 ปุ่มต่อแถว
    COLS_PER_ROW = 6
    for row_start in range(0, len(all_cats), COLS_PER_ROW):
        row_cats = all_cats[row_start : row_start + COLS_PER_ROW]
        chip_cols = st.columns(len(row_cats))
        for i, cat in enumerate(row_cats):
            is_active = (st.session_state.sel_cat == cat)
            if chip_cols[i].button(
                ("🔴 " if is_active else "") + cat,
                key=f"chip_{cat}", use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.sel_cat = cat
                st.rerun()

    search = st.text_input("", placeholder="🔍 ค้นหาสินค้า, เบอร์สี, ยี่ห้อ...",
                           label_visibility="collapsed", key="shop_search")

    # Sort
    sort_col, count_col = st.columns([2,1])
    sort_by = sort_col.selectbox("เรียงตาม:", ["ชื่อ", "ราคา ↑", "ราคา ↓", "สต็อก ↓"],
                                  label_visibility="collapsed", key="sort_by")

    filtered = stock_df.copy()
    if st.session_state.sel_cat != "ทั้งหมด":
        filtered = filtered[filtered['CategoryName'] == st.session_state.sel_cat]
    if search:
        mask = filtered['Name'].str.contains(search, na=False, case=False)
        if 'Barcode' in filtered.columns:
            mask |= filtered['Barcode'].astype(str).str.contains(search, na=False)
        filtered = filtered[mask]

    if sort_by == "ราคา ↑" and 'RetailPrice' in filtered.columns:
        filtered = filtered.sort_values('RetailPrice')
    elif sort_by == "ราคา ↓" and 'RetailPrice' in filtered.columns:
        filtered = filtered.sort_values('RetailPrice', ascending=False)
    elif sort_by == "สต็อก ↓" and 'Qty' in filtered.columns:
        filtered = filtered.sort_values('Qty', ascending=False)
    else:
        filtered = filtered.sort_values('Name') if 'Name' in filtered.columns else filtered

    count_col.markdown(
        f'<div style="text-align:right;font-size:11px;color:var(--muted);padding-top:6px">'
        f'พบ {len(filtered):,} รายการ</div>', unsafe_allow_html=True
    )

    # 2-column product grid
    cols = st.columns(2, gap="small")
    for i, (_, row) in enumerate(filtered.head(80).iterrows()):
        stock = int(row.get('Qty', 0))
        price = float(row.get('RetailPrice', 0))
        barcode = str(row.get('Barcode',''))
        name    = str(row.get('Name',''))
        brand   = str(row.get('CategoryName',''))

        if stock > 5:   avail_html = '<span style="font-size:10px"><span class="dot-ok">●</span> มีสินค้า</span>'
        elif stock > 0: avail_html = f'<span style="font-size:10px"><span class="dot-low">●</span> เหลือ {stock}</span>'
        else:           avail_html = '<span style="font-size:10px"><span class="dot-out">●</span> หมด</span>'

        with cols[i % 2]:
            st.markdown(f"""
            <div class="pcg-card">
              <div class="pcg-swatch">🎨</div>
              <div class="pcg-name" title="{name}">{name}</div>
              <div class="pcg-brand">{brand}</div>
              <div class="pcg-price">฿{price:,.0f}</div>
              {avail_html}
            </div>""", unsafe_allow_html=True)

            if stock > 0:
                qa, qb = st.columns([1,1])
                qty = qa.number_input("", min_value=1, max_value=stock, value=1,
                                      key=f"q_{barcode}", label_visibility="collapsed")
                if qb.button("🛒 เพิ่ม", key=f"a_{barcode}", use_container_width=True):
                    add_to_cart(barcode, name, price, qty, stock)
                    st.rerun()
            else:
                st.markdown('<div style="height:36px;display:flex;align-items:center;'
                            'font-size:11px;color:var(--muted2)">ไม่สามารถสั่งได้</div>',
                            unsafe_allow_html=True)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


def page_cart():
    render_nav(show_cart=False)
    st.markdown("<div style='padding:16px 20px'>", unsafe_allow_html=True)

    # Back button
    bc = st.columns([1,5])
    with bc[0]:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← ช้อปต่อ", key="back_shop"):
            go('shop')
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-title">ตะกร้าสินค้า</div>', unsafe_allow_html=True)

    cart = st.session_state.cart
    if not cart:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
          <div style="font-size:48px;margin-bottom:12px">🛒</div>
          <div style="font-size:14px;color:var(--muted)">ตะกร้าว่างเปล่า</div>
          <div style="font-size:11px;color:var(--muted2);margin-top:4px">เพิ่มสินค้าจากหน้าร้านค้า</div>
        </div>""", unsafe_allow_html=True)
        if st.button("ไปหน้าสินค้า →", use_container_width=True, type="primary"):
            go('shop')
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Cart items
    for barcode, item in list(cart.items()):
        st.markdown(f"""
        <div class="cart-item-row">
          <div class="ci-icon">🎨</div>
          <div style="flex:1">
            <div class="ci-name">{item['name']}</div>
            <div style="font-size:10px;color:var(--muted)">฿{item['price']:,.0f} × {item['qty']} = ฿{item['price']*item['qty']:,.0f}</div>
          </div>
        </div>""", unsafe_allow_html=True)
        ca, cb, cc = st.columns([2,1,1])
        new_qty = ca.number_input("จำนวน", min_value=1, max_value=item['max'], value=item['qty'],
                                   key=f"cq_{barcode}", label_visibility="collapsed")
        if new_qty != item['qty']:
            st.session_state.cart[barcode]['qty'] = new_qty
            st.rerun()
        if cb.button("ลบ", key=f"rm_{barcode}", use_container_width=True):
            remove_from_cart(barcode); st.rerun()

    # Summary
    total = cart_total()
    n     = cart_count()
    st.markdown(f"""
    <div class="cart-total-box">
      <div class="ct-row"><span style="color:var(--muted)">จำนวนสินค้า</span><span>{n} ชิ้น</span></div>
      <div class="ct-row"><span style="color:var(--muted)">ค่าสินค้า</span><span>฿{total:,.0f}</span></div>
      <div class="ct-row" style="margin-top:6px;padding-top:8px;border-top:1px solid var(--border)">
        <span style="font-weight:700">ยอดรวม (ยังไม่รวมส่ง)</span>
        <span class="ct-total">฿{total:,.0f}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    col_clear, col_order = st.columns([1,2])
    if col_clear.button("🗑 ล้างตะกร้า", use_container_width=True):
        st.session_state.cart = {}; st.rerun()
    if col_order.button("✅ สั่งซื้อ / จัดส่ง →", use_container_width=True, type="primary"):
        go('delivery')

    st.markdown("</div>", unsafe_allow_html=True)


def _checkout_map_html(center_lat, center_lng):
    return f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0a;font-family:'Sarabun',sans-serif}}
.mapwrap{{position:relative;border:1px solid #2a2a2a;border-radius:9px;overflow:hidden}}
#map{{width:100%;height:230px}}
.mpin{{position:absolute;top:50%;left:50%;transform:translate(-50%,-100%);z-index:1000;
  pointer-events:none;filter:drop-shadow(0 2px 4px rgba(0,0,0,.7))}}
.msrow{{position:absolute;top:6px;left:6px;right:6px;z-index:1000;display:flex;gap:5px}}
.msinp{{flex:1;background:rgba(14,14,14,.96);border:1px solid #2a2a2a;color:#f0f0f0;
  padding:7px 9px;border-radius:6px;font-size:11px;outline:none}}
.msbtn{{background:#E8192C;border:none;color:#fff;padding:7px 9px;border-radius:6px;
  font-size:11px;cursor:pointer;font-weight:700}}
.mgps{{position:absolute;bottom:38px;right:6px;z-index:1000;background:rgba(14,14,14,.96);
  border:1px solid #2a2a2a;color:#f0f0f0;padding:5px 8px;border-radius:6px;font-size:10px;cursor:pointer}}
.mconfirm{{width:100%;background:#E8192C;border:none;color:#fff;padding:9px;
  font-size:12px;font-weight:700;cursor:pointer;letter-spacing:.3px}}
.result{{display:none;background:#141414;border:1px solid rgba(74,222,128,.3);
  border-radius:7px;padding:10px 12px;margin-top:6px}}
.result-note{{font-size:10px;color:#4ade80;font-weight:700;margin-bottom:4px}}
.result-addr{{font-size:11px;color:#f0f0f0;line-height:1.5}}
.result-coords{{font-size:9px;color:#888;font-family:monospace;margin-top:3px}}
.copy-btn{{margin-top:6px;background:#252525;border:1px solid #333;color:#aaa;
  padding:4px 10px;border-radius:5px;font-size:10px;cursor:pointer;font-family:'Sarabun',sans-serif}}
.hint{{font-size:10px;color:#555;padding:7px 0 0;text-align:center}}
</style></head><body>
<div class="mapwrap">
  <div id="map"></div>
  <div class="mpin">
    <svg width="22" height="28" viewBox="0 0 32 40" fill="none">
      <path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 24 16 24s16-12 16-24C32 7.16 24.84 0 16 0z" fill="#E8192C"/>
      <circle cx="16" cy="16" r="6" fill="white"/>
    </svg>
  </div>
  <div class="msrow">
    <input class="msinp" id="msearch" placeholder="🔍 ค้นหาที่อยู่..." onkeydown="if(event.key==='Enter')doSearch()">
    <button class="msbtn" onclick="doSearch()">ค้นหา</button>
  </div>
  <button class="mgps" onclick="doGPS()">📡 GPS</button>
  <button class="mconfirm" onclick="confirmPin()">📍 ยืนยันตำแหน่งนี้ — คัดลอกที่อยู่ไปกรอกด้านล่าง</button>
</div>
<div class="result" id="result">
  <div class="result-note">📍 ตำแหน่งที่เลือก</div>
  <div class="result-addr" id="result-addr"></div>
  <div class="result-coords" id="result-coords"></div>
  <button class="copy-btn" onclick="copyAddr()">📋 คัดลอกที่อยู่</button>
</div>
<div class="hint">ลากแผนที่เพื่อย้ายหมุด · กด GPS เพื่อใช้ตำแหน่งปัจจุบัน</div>
<script>
let map, curLat={center_lat}, curLng={center_lng};
let lastAddr = '';
document.addEventListener('DOMContentLoaded',()=>{{
  map=L.map('map',{{zoomControl:false,attributionControl:false}}).setView([curLat,curLng],14);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{maxZoom:19}}).addTo(map);
  L.control.zoom({{position:'bottomleft'}}).addTo(map);
  map.on('move',()=>{{const c=map.getCenter();curLat=+c.lat.toFixed(6);curLng=+c.lng.toFixed(6);}});
}});
function doSearch(){{
  const q=document.getElementById('msearch').value.trim();
  if(!q)return;
  fetch('https://nominatim.openstreetmap.org/search?q='+encodeURIComponent(q+' ไทย')+'&format=json&limit=1&countrycodes=th',
    {{headers:{{'User-Agent':'ThaiNova/1.0'}}}})
  .then(r=>r.json()).then(d=>{{
    if(d.length){{map.setView([+d[0].lat,+d[0].lon],16);}}
    else alert('ไม่พบที่อยู่ ลองพิมพ์ให้ละเอียดขึ้น');
  }}).catch(()=>{{}});
}}
function doGPS(){{
  if(!navigator.geolocation){{alert('Browser ไม่รองรับ GPS');return;}}
  navigator.geolocation.getCurrentPosition(
    p=>{{map.setView([p.coords.latitude,p.coords.longitude],17);}},
    ()=>alert('ไม่สามารถดึง GPS ได้ กรุณาอนุญาต GPS ในเบราว์เซอร์')
  );
}}
function confirmPin(){{
  fetch('https://nominatim.openstreetmap.org/reverse?lat='+curLat+'&lon='+curLng+'&format=json&accept-language=th',
    {{headers:{{'User-Agent':'ThaiNova/1.0'}}}})
  .then(r=>r.json()).then(d=>showResult(d.display_name||curLat+','+curLng))
  .catch(()=>showResult(curLat+','+curLng));
}}
function showResult(addr){{
  lastAddr=addr;
  const el=document.getElementById('result');
  el.style.display='block';
  document.getElementById('result-addr').textContent=addr;
  document.getElementById('result-coords').textContent='พิกัด: '+curLat.toFixed(5)+', '+curLng.toFixed(5);
}}
function copyAddr(){{
  if(navigator.clipboard){{
    navigator.clipboard.writeText(lastAddr).then(()=>alert('✅ คัดลอกแล้ว! วางในช่องที่อยู่จัดส่งด้านล่าง'));
  }}else{{
    const t=document.createElement('textarea');t.value=lastAddr;
    document.body.appendChild(t);t.select();document.execCommand('copy');
    document.body.removeChild(t);alert('✅ คัดลอกแล้ว!');
  }}
}}
</script></body></html>"""

def _wizard_html(step):
    def wn(n):
        if n < step:  return "done", "✓", ""
        if n == step: return "active", str(n), "active"
        return "idle", str(n), ""
    def wd(n): return "done" if n < step else ""
    c1,n1,l1 = wn(1); c2,n2,l2 = wn(2); _,_,_ = wn(3)
    return f"""
    <div class="wizard">
      <div class="wstep"><div class="wnum {c1}">{n1}</div><div class="wlabel {l1}">ข้อมูลส่ง</div></div>
      <div class="wline {wd(1)}"></div>
      <div class="wstep"><div class="wnum {c2}">{n2}</div><div class="wlabel {l2}">ชำระเงิน</div></div>
    </div>"""


def page_checkout():
    lk, ls, mk, pp_phone, keys_ok = get_secrets()
    render_nav(show_cart=False)
    st.markdown("<div style='padding:16px 20px'>", unsafe_allow_html=True)

    bc = st.columns([1,5])
    with bc[0]:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← กลับ", key="co_back"):
            if st.session_state.checkout_step == 1: go('cart')
            else: st.session_state.checkout_step -= 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-title">สั่งซื้อสินค้า</div>', unsafe_allow_html=True)
    st.markdown(_wizard_html(st.session_state.checkout_step), unsafe_allow_html=True)

    # ── STEP 1: ข้อมูลส่ง ──────────────────────────────────
    if st.session_state.checkout_step == 1:

        # Cart summary (mini)
        st.markdown('<div class="sum-card">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">สินค้าในออเดอร์</div>', unsafe_allow_html=True)
        for bc_key, item in st.session_state.cart.items():
            st.markdown(
                f'<div class="sum-row"><span>{item["name"][:28]} ×{item["qty"]}</span>'
                f'<span>฿{item["price"]*item["qty"]:,.0f}</span></div>',
                unsafe_allow_html=True
            )
        st.markdown(
            f'<div class="sum-row"><span style="font-weight:700">รวม</span>'
            f'<span>฿{cart_total():,.0f}</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Customer info
        st.markdown('<div class="co-section">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">ข้อมูลผู้รับ</div>', unsafe_allow_html=True)
        name  = st.text_input("ชื่อ-นามสกุล / ชื่ออู่ *", value=st.session_state.cust_name,
                               key="co_name", placeholder="เช่น อู่ซ่อมรถ ลาดพร้าว")
        phone = st.text_input("เบอร์โทร *", value=st.session_state.cust_phone,
                               key="co_phone", placeholder="0XX-XXX-XXXX")
        st.markdown('</div>', unsafe_allow_html=True)

        # Delivery method
        st.markdown('<div class="co-section">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">วิธีรับสินค้า</div>', unsafe_allow_html=True)
        method = st.radio("",["🚚 จัดส่ง Lalamove","🏪 รับที่ร้าน"],
                           index=0 if st.session_state.delivery_method=="lalamove" else 1,
                           key="co_method", horizontal=True, label_visibility="collapsed")
        is_lala = "Lalamove" in method

        if is_lala:
            import streamlit.components.v1 as components
            # — MAP —
            clat = st.session_state.checkout_lat or 13.8468093
            clng = st.session_state.checkout_lng or 100.7982969
            components.html(_checkout_map_html(clat, clng), height=340, scrolling=False)

            st.markdown("""<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.15);
            border-radius:8px;padding:8px 12px;font-size:11px;color:#4ade80;margin-bottom:8px">
            💡 <strong>วิธีใช้:</strong> ค้นหาหรือกด GPS บนแผนที่ → กด "ยืนยันตำแหน่ง" → คัดลอกที่อยู่ → วางในช่องด้านล่าง
            </div>""", unsafe_allow_html=True)

            # — Address input + search —
            addr_txt = st.text_input("📍 ที่อยู่จัดส่ง *",
                value=st.session_state.checkout_addr or "",
                key="co_addr",
                placeholder="วางที่อยู่จากแผนที่ หรือพิมพ์เอง เช่น อู่ซ่อมรถ ลาดพร้าว 71 กรุงเทพฯ")

            if st.button("🔍 ค้นหาและยืนยันที่อยู่", use_container_width=True, key="co_geocode",
                         disabled=not addr_txt):
                with st.spinner("กำลังค้นหา..."):
                    lat, lng, fmt = geocode(addr_txt, mk)
                if lat:
                    st.session_state.checkout_lat   = lat
                    st.session_state.checkout_lng   = lng
                    st.session_state.checkout_addr  = fmt
                    st.session_state.checkout_quote_id = None
                    st.rerun()
                else:
                    st.error("❌ ไม่พบที่อยู่ ลองพิมพ์ให้ละเอียดขึ้น เช่น เพิ่มชื่อแขวง/เขต")

            if st.session_state.checkout_lat:
                st.markdown(f"""<div class="addr-box">
                  <span style="color:var(--green)">✓ ยืนยันแล้ว:</span> {st.session_state.checkout_addr}<br>
                  <span style="font-size:10px;color:var(--muted);font-family:monospace">
                  {st.session_state.checkout_lat:.5f}, {st.session_state.checkout_lng:.5f}</span>
                </div>""", unsafe_allow_html=True)

                # — Vehicle selection —
                st.markdown('<div style="margin-top:14px;font-size:11px;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;margin-bottom:8px">🚗 เลือกยานพาหนะ</div>', unsafe_allow_html=True)
                veh_choice = st.radio("", list(VEHICLES.keys()),
                    format_func=lambda k: f"{VEHICLES[k]['label']} — ฿{VEHICLES[k]['price']} ({VEHICLES[k]['detail']})",
                    index=list(VEHICLES.keys()).index(st.session_state.checkout_vehicle),
                    key="co_veh", label_visibility="collapsed")

                # — Who pays shipping —
                st.markdown('<div style="margin-top:14px;font-size:11px;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;margin-bottom:8px">💳 ผู้ชำระค่าจัดส่ง</div>', unsafe_allow_html=True)
                lala_pay_opts = [
                    "🏪 ร้านค้าชำระ (ThaiNova จ่ายค่าส่งให้ Lalamove)",
                    "💵 ลูกค้าชำระ — Driver เก็บเงินสดที่ปลายทาง (POD)",
                    "🏦 ลูกค้าชำระ — โอนเงินค่าส่งให้ร้านก่อนจัดส่ง",
                ]
                pay_type_idx = {"sender":0,"recipient_cash":1,"recipient_transfer":2}.get(
                    st.session_state.lala_pay_type, 0)
                lala_pay = st.radio("", lala_pay_opts,
                    index=pay_type_idx, key="co_lala_pay", label_visibility="collapsed")
                lala_pay_key = ["sender","recipient_cash","recipient_transfer"][lala_pay_opts.index(lala_pay)]

                if lala_pay_key == "recipient_cash":
                    st.markdown("""<div style="background:rgba(201,168,76,.08);border:1px solid rgba(201,168,76,.25);
                    border-radius:7px;padding:8px 12px;font-size:11px;color:#C9A84C">
                    ⚠️ Driver จะเก็บค่าจัดส่งจากผู้รับเป็นเงินสด (POD) ลูกค้าชำระค่าส่งตอนรับของ
                    </div>""", unsafe_allow_html=True)
                elif lala_pay_key == "recipient_transfer":
                    st.markdown(f"""<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.2);
                    border-radius:7px;padding:8px 12px;font-size:11px;color:#4ade80">
                    📲 ลูกค้าต้องโอนค่าจัดส่งให้ร้านก่อนจัดส่ง<br>
                    <span style="color:var(--muted)">PromptPay: 062-737-7700 (นายปัญญธร ชัยพิศุทธิ์)</span>
                    </div>""", unsafe_allow_html=True)

                if keys_ok:
                    if st.button("💰 ขอราคาจาก Lalamove", use_container_width=True, key="co_getprice"):
                        with st.spinner("กำลังคำนวณ..."):
                            q = get_quotation(st.session_state.checkout_lat,
                                              st.session_state.checkout_lng, veh_choice, lk, ls)
                        if q["ok"]:
                            st.session_state.checkout_quote_id    = q["quotation_id"]
                            st.session_state.checkout_quote_price = q["price"]
                            st.session_state.checkout_quote_dist  = q["distance"]
                            st.session_state.checkout_vehicle     = veh_choice
                            st.session_state.lala_pay_type        = lala_pay_key
                            st.rerun()
                        else:
                            st.error(f"❌ {q['error']}")
                else:
                    st.session_state.checkout_vehicle = veh_choice
                    st.session_state.lala_pay_type    = lala_pay_key

                if st.session_state.checkout_quote_id and st.session_state.checkout_vehicle == veh_choice:
                    st.success(
                        f"✅ ค่าส่ง: **฿{st.session_state.checkout_quote_price}** · "
                        f"ระยะทาง: {st.session_state.checkout_quote_dist}"
                    )
        else:
            st.markdown("""<div class="addr-box">
              <span style="color:var(--green)">📍</span> รับที่ร้าน ThaiNova AutoPaint<br>
              <span style="font-size:11px;color:var(--muted)">ฟรีค่าจัดส่ง · เปิด จ-ศ 08:00-18:00</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Validate & proceed
        can_proceed = bool(name and phone)
        if is_lala: can_proceed = can_proceed and bool(st.session_state.checkout_lat)

        if st.button("ต่อไป: ชำระเงิน →", use_container_width=True, type="primary",
                     key="co_step2", disabled=not can_proceed):
            st.session_state.cust_name       = name
            st.session_state.cust_phone      = phone
            st.session_state.delivery_method = "lalamove" if is_lala else "pickup"
            if is_lala and 'lala_pay_key' in dir():
                st.session_state.lala_pay_type = lala_pay_key
            st.session_state.checkout_step  = 2
            st.rerun()

        if not can_proceed:
            missing = []
            if not name:  missing.append("ชื่อ")
            if not phone: missing.append("เบอร์โทร")
            if is_lala and not st.session_state.checkout_lat: missing.append("ที่อยู่จัดส่ง")
            st.caption(f"⚠️ กรุณากรอก: {', '.join(missing)}")

    # ── STEP 2: ชำระเงิน ───────────────────────────────────
    elif st.session_state.checkout_step == 2:
        is_lala    = st.session_state.delivery_method == "lalamove"
        cart_amt   = cart_total()
        delivery_fee = st.session_state.checkout_quote_price or (VEHICLES[st.session_state.checkout_vehicle]["price"] if is_lala else 0)
        try: delivery_fee_num = float(delivery_fee)
        except: delivery_fee_num = 0.0
        total_amt  = cart_amt + delivery_fee_num

        # Order summary
        st.markdown('<div class="sum-card">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">สรุปออเดอร์</div>', unsafe_allow_html=True)
        for _, item in st.session_state.cart.items():
            st.markdown(
                f'<div class="sum-row"><span>{item["name"][:28]} ×{item["qty"]}</span>'
                f'<span>฿{item["price"]*item["qty"]:,.0f}</span></div>',
                unsafe_allow_html=True
            )
        if is_lala:
            vname = VEHICLES[st.session_state.checkout_vehicle]['label']
            price_note = "จริง ✓" if st.session_state.checkout_quote_id else "ประมาณ"
            st.markdown(
                f'<div class="sum-row"><span>ค่าจัดส่ง {vname} ({price_note})</span>'
                f'<span>฿{delivery_fee_num:,.0f}</span></div>',
                unsafe_allow_html=True
            )
        st.markdown(
            f'<div class="sum-row"><span>ยอดรวมทั้งหมด</span><span>฿{total_amt:,.0f}</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # — Lalamove payment recap (if recipient pays transfer) —
        lala_pay_t = st.session_state.get("lala_pay_type","sender")
        if is_lala and lala_pay_t == "recipient_transfer":
            st.markdown(f"""<div style="background:rgba(201,168,76,.08);border:1px solid rgba(201,168,76,.3);
            border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#C9A84C">
            ⚠️ <strong>ค่าจัดส่ง ฿{delivery_fee_num:,.0f}</strong> — กรุณาโอนค่าส่งให้ร้านก่อนจัดส่ง<br>
            <span style="font-size:11px">PromptPay: <strong>062-737-7700</strong> (นายปัญญธร ชัยพิศุทธิ์)</span>
            </div>""", unsafe_allow_html=True)
        elif is_lala and lala_pay_t == "recipient_cash":
            st.markdown("""<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.2);
            border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#4ade80">
            ✅ Driver จะเก็บค่าจัดส่งเป็นเงินสดที่ปลายทาง (POD) — ลูกค้าชำระตอนรับของ
            </div>""", unsafe_allow_html=True)

        # — Product payment method —
        st.markdown('<div class="co-section">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">ชำระเงินค่าสินค้า</div>', unsafe_allow_html=True)
        pay_opts = ["📱 PromptPay / QR Code", "🏦 โอนเงินเข้าบัญชีธนาคาร"]
        pay_choice = st.radio("", pay_opts, key="co_pay", label_visibility="collapsed")

        STORE_PP_PHONE = "0627377700"
        STORE_BANK     = "กสิกรไทย (KBank)"
        STORE_ACCOUNT  = "129-1-89092-6"
        STORE_NAME     = "นายปัญญธร ชัยพิศุทธิ์"

        if "PromptPay" in pay_choice:
            st.session_state.payment_method = "promptpay"
            qr_b64 = gen_qr_b64(STORE_PP_PHONE, total_amt)
            if qr_b64:
                st.markdown(f"""
                <div class="qr-box">
                  <div style="font-size:12px;font-weight:600;margin-bottom:6px">สแกน QR ชำระเงิน</div>
                  <div style="font-size:22px;font-weight:700;color:var(--red);font-family:'Barlow Condensed',sans-serif;margin-bottom:8px">
                    ฿{total_amt:,.0f}</div>
                  <img src="data:image/png;base64,{qr_b64}"
                       style="width:200px;border-radius:10px;border:3px solid #2a2a2a;margin-bottom:10px">
                  <div style="font-size:12px;font-weight:600">PromptPay: {STORE_PP_PHONE}</div>
                  <div style="font-size:11px;color:var(--muted)">{STORE_NAME}</div>
                  <div style="font-size:10px;color:var(--muted2);margin-top:6px">
                    หลังโอนกรุณาแนบสลิปทาง LINE หรือ โทร 062-737-7700</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="co-section">
                <div style="font-size:13px;font-weight:700;margin-bottom:4px">📱 PromptPay</div>
                <div style="font-size:22px;font-weight:700;color:var(--red);font-family:'Barlow Condensed',sans-serif">
                  {STORE_PP_PHONE}</div>
                <div style="font-size:12px;color:var(--muted)">{STORE_NAME}</div>
                <div style="font-size:14px;font-weight:700;margin-top:8px">ยอด: ฿{total_amt:,.0f}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.session_state.payment_method = "transfer"
            st.markdown(f"""
            <div style="background:var(--surface2);border:1px solid var(--border);
                 border-radius:10px;padding:16px;text-align:center">
              <div style="font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">
                โอนเงินเข้าบัญชี</div>
              <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px">
                🏦 {STORE_BANK}</div>
              <div style="font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:700;
                   color:var(--red);letter-spacing:1px;margin:6px 0">{STORE_ACCOUNT}</div>
              <div style="font-size:13px;font-weight:600">{STORE_NAME}</div>
              <div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border);
                   font-size:14px;font-weight:700">
                ยอดโอน: <span style="color:var(--red)">฿{total_amt:,.0f}</span></div>
              <div style="font-size:10px;color:var(--muted);margin-top:6px">
                หลังโอนกรุณาแนบสลิปทาง LINE หรือ โทร 062-737-7700</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Customer info recap
        st.markdown(f"""
        <div class="co-section">
          <div class="co-section-title">ข้อมูลส่งสินค้า</div>
          <div style="font-size:13px;font-weight:600">{st.session_state.cust_name}</div>
          <div style="font-size:12px;color:var(--muted)">{st.session_state.cust_phone}</div>
          <div style="font-size:12px;color:var(--muted);margin-top:4px">
            {st.session_state.checkout_addr if is_lala else "รับที่ร้าน"}
          </div>
        </div>""", unsafe_allow_html=True)

        # Confirm button
        if st.button("🎉 ยืนยันคำสั่งซื้อ", use_container_width=True, type="primary", key="co_confirm"):
            order_id = gen_order_id()
            lala_order_id = ""
            share_link    = ""

            # Create Lalamove order
            is_pod = st.session_state.get("lala_pay_type","sender") == "recipient_cash"
            if is_lala and st.session_state.checkout_quote_id and keys_ok:
                with st.spinner("กำลังสร้าง Lalamove order..."):
                    lo = create_lala_order(
                        st.session_state.checkout_quote_id,
                        st.session_state.get("checkout_stop_sender",    "1"),
                        st.session_state.get("checkout_stop_recipient", "2"),
                        st.session_state.cust_name, st.session_state.cust_phone,
                        lk, ls, is_pod=is_pod
                    )
                if lo.get("debug"):
                    with st.expander("🔍 Lalamove Debug Response", expanded=not lo["ok"]):
                        st.json(lo["debug"])
                if lo["ok"]:
                    lala_order_id = lo["order_id"]
                    share_link    = lo["share_link"]
                else:
                    st.error(f"❌ Lalamove create order ล้มเหลว: {lo['error']}")

            # Save order
            try_save_order({
                "OrderID":       order_id,
                "DateTime":      datetime.now().isoformat(),
                "CustomerName":  st.session_state.cust_name,
                "CustomerPhone": st.session_state.cust_phone,
                "Items":         json.dumps({k:v for k,v in st.session_state.cart.items()}, ensure_ascii=False),
                "CartTotal":     cart_amt,
                "DeliveryMethod":st.session_state.delivery_method,
                "DeliveryAddr":  st.session_state.checkout_addr,
                "Vehicle":       st.session_state.checkout_vehicle if is_lala else "",
                "DeliveryFee":   delivery_fee_num,
                "PaymentMethod": st.session_state.payment_method,
                "TotalAmount":   total_amt,
                "LalamoveID":    lala_order_id,
                "Status":        "pending",
            })

            st.session_state.order_id        = order_id
            st.session_state.order_lala_id   = lala_order_id
            st.session_state.order_share_link= share_link
            st.session_state.cart = {}
            st.session_state.checkout_step = 1
            go('confirmed')

    st.markdown("</div>", unsafe_allow_html=True)


def page_confirmed():
    render_nav(show_cart=False)
    oid   = st.session_state.order_id or "TN------"
    lid   = st.session_state.order_lala_id
    link  = st.session_state.order_share_link

    st.markdown(f"""
    <div class="confirm-wrap">
      <div class="confirm-icon">🎉</div>
      <div class="confirm-title">สั่งซื้อสำเร็จ!</div>
      <div class="confirm-sub">ขอบคุณที่ใช้บริการ ThaiNova AutoPaint</div>
      <div class="order-num-box">
        <div class="order-num-label">หมายเลขออเดอร์</div>
        <div class="order-num-val">{oid}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if lid:
        st.success(f"✅ Lalamove Order ID: **{lid}**")
    if link:
        st.link_button("📍 ติดตาม Driver", link, use_container_width=True)

    st.markdown("""
    <div style="background:var(--surface);border:1px solid var(--border);
         border-radius:10px;padding:16px;margin:12px 20px;text-align:center">
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">
        ต้องการสอบถาม?</div>
      <div style="font-weight:600">📞 087-079-9199 / 062-737-7700</div>
    </div>""", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🏠 กลับหน้าแรก", use_container_width=True):
            go('home')
    with col_b:
        if st.button("📦 สั่งซื้ออีกครั้ง", use_container_width=True, type="primary"):
            go('shop')


def _shared_js():
    """Shared vehicle/schedule/confirm JS สำหรับ delivery iframe.
    Visual-only — ไม่มี postMessage (Streamlit sandbox บล็อกทั้งหมด)
    พิกัดถึง Python ผ่าน text_input + ปุ่ม ยืนยันที่อยู่ ด้านล่าง"""
    return """
function setConfirmed(addr,lat,lng){
  confirmed=true;
  document.getElementById('map-wrap').style.display='none';
  document.getElementById('con-card').style.display='flex';
  const sh=addr.length>50?addr.substring(0,50)+'...':addr;
  document.getElementById('con-name').textContent=sh;
  document.getElementById('con-coords').textContent=(lat.toFixed?lat.toFixed(5):lat)+', '+(lng.toFixed?lng.toFixed(5):lng);
  document.getElementById('sum-dest').textContent=sh;
  toast('✅ ปักหมุดแล้ว! กำลังส่งที่อยู่ไปยังฟอร์ม...');
  try{
    var p=new URLSearchParams(window.parent.location.search);
    p.set('_dlat',lat.toFixed?lat.toFixed(6):String(lat));
    p.set('_dlng',lng.toFixed?lng.toFixed(6):String(lng));
    p.set('_daddr',addr);
    window.parent.history.replaceState(null,'',window.parent.location.pathname+'?'+p.toString());
    window.parent.dispatchEvent(new PopStateEvent('popstate',{bubbles:true}));
  }catch(e){}
}
function changeAddr(){
  confirmed=false;
  document.getElementById('map-wrap').style.display='block';
  document.getElementById('con-card').style.display='none';
}
function selectV(k,el){
  ['MOTORCYCLE','CAR','VAN'].forEach(v=>{
    const c=document.getElementById('v-'+v),n=document.getElementById('vn-'+v);
    if(c){c.classList.remove('sel');n.classList.remove('sel');n.textContent=n.textContent.replace('  ✓','');}
  });
  el.classList.add('sel');
  const n=document.getElementById('vn-'+k);n.classList.add('sel');n.textContent+='  ✓';
  document.getElementById('sum-v').textContent=VN[k];
  document.getElementById('sum-price').textContent='฿'+VP[k];
  document.getElementById('sum-price').style.color='var(--gd)';
  document.getElementById('pnote').textContent='(ประมาณ)';
  document.getElementById('pnote').style.color='var(--gd)';
}
function selectSched(s){
  document.getElementById('sched-now').classList.toggle('sel',s==='now');
  document.getElementById('sched-later').classList.toggle('sel',s==='later');
}"""


def page_delivery():
    lk, ls, mk, pp_phone, keys_ok = get_secrets()
    import streamlit.components.v1 as components

    # ── รับพิกัด+ที่อยู่จากแผนที่ผ่าน query params ──────────────────
    _qp = st.query_params
    if "_dlat" in _qp and "_dlng" in _qp:
        try:
            st.session_state.checkout_lat      = float(_qp["_dlat"])
            st.session_state.checkout_lng      = float(_qp["_dlng"])
            st.session_state.checkout_addr     = _qp.get("_daddr", "")
            st.session_state.checkout_quote_id    = None
            st.session_state.show_map_delivery = False   # ซ่อนแผนที่, แสดงกล่องที่อยู่
        except (ValueError, KeyError):
            pass
        st.query_params.clear()
        st.rerun()

    from_cart = bool(st.session_state.cart)

    # unified state keys
    dest_lat  = st.session_state.checkout_lat
    dest_lng  = st.session_state.checkout_lng
    dest_addr = st.session_state.checkout_addr or ""
    sel_v     = st.session_state.checkout_vehicle
    q_id      = st.session_state.checkout_quote_id
    q_price   = str(st.session_state.checkout_quote_price or "")
    q_dist    = str(st.session_state.checkout_quote_dist or "")

    is_confirmed = dest_lat is not None
    has_quote    = bool(q_id) and st.session_state.checkout_vehicle == sel_v

    price_map   = {"MOTORCYCLE":"79","CAR":"149","VAN":"249"}
    disp_price  = q_price if has_quote else price_map.get(sel_v, "79")
    price_color = "#4ade80" if has_quote else "#C9A84C"
    price_note  = "ราคาจริง ✓" if has_quote else "ประมาณ"

    addr_esc   = dest_addr.replace('"','').replace('\n',' ')
    addr_short = addr_esc[:50]+"..." if len(addr_esc)>50 else addr_esc

    def sc(n):
        if n==1: return "done"
        if n==2: return "done" if is_confirmed else "active"
        if n==3: return "active" if is_confirmed and not q_id else ("done" if q_id else "idle")
        if n==4: return "active" if q_id else "idle"
        return "idle"
    def sl(n):
        if n==1: return "done"
        if n==2: return "done" if is_confirmed else ""
        if n==3: return "done" if q_id else ""
        return ""
    def snum(n):
        if n==1: return "✓"
        if n==2: return "✓" if is_confirmed else "2"
        return str(n)
    def vrow(key, icon, name, detail, price, eta):
        sel_cls = "sel" if sel_v==key else ""
        chk = "  ✓" if sel_v==key else ""
        return (f'<div class="v-card {sel_cls}" onclick="selectV(\'{key}\',this)" id="v-{key}">'
                f'<div class="v-icon">{icon}</div>'
                f'<div><div class="v-name {"sel" if sel_v==key else ""}" id="vn-{key}">{name}{chk}</div>'
                f'<div class="v-detail">{detail}</div></div>'
                f'<div><div class="v-price">฿{price}</div><div class="v-eta">{eta}</div></div></div>')
    def sbtn(key, icon, label):
        sel_sched = st.session_state.get("sel_sched","now")
        cls = "sel" if sel_sched==key else ""
        return f'<button class="sched-btn {cls}" id="sched-{key}" onclick="selectSched(\'{key}\')">{icon} {label}</button>'

    sum_dest  = addr_short if dest_addr else "— ยังไม่ได้เลือก"
    sum_vname = {"MOTORCYCLE":"🛵 Motorbike","CAR":"🚗 Sedan","VAN":"🚐 Van"}.get(sel_v,"")
    map_lat   = dest_lat if dest_lat else 13.8468093
    map_lng   = dest_lng if dest_lng else 100.7982969

    use_google = bool(mk)

    # ── Google Maps JS (when API key available) ──────────────────
    if use_google:
        shared = _shared_js()
        map_js = f"""
<script>
let map,curLat={map_lat},curLng={map_lng},confirmed={str(is_confirmed).lower()};
const VP={{MOTORCYCLE:79,CAR:149,VAN:249}};
const VN={{MOTORCYCLE:'🛵 Motorbike',CAR:'🚗 Sedan/Eco Car',VAN:'🚐 Van/Truck'}};
const DARK=[
  {{elementType:"geometry",stylers:[{{color:"#141414"}}]}},
  {{elementType:"labels.icon",stylers:[{{visibility:"off"}}]}},
  {{elementType:"labels.text.fill",stylers:[{{color:"#888"}}]}},
  {{elementType:"labels.text.stroke",stylers:[{{color:"#141414"}}]}},
  {{featureType:"administrative",elementType:"geometry",stylers:[{{color:"#555"}}]}},
  {{featureType:"administrative.locality",elementType:"labels.text.fill",stylers:[{{color:"#aaa"}}]}},
  {{featureType:"road",elementType:"geometry.fill",stylers:[{{color:"#2a2a2a"}}]}},
  {{featureType:"road",elementType:"labels.text.fill",stylers:[{{color:"#777"}}]}},
  {{featureType:"road.arterial",elementType:"geometry",stylers:[{{color:"#333"}}]}},
  {{featureType:"road.highway",elementType:"geometry",stylers:[{{color:"#3c3c3c"}}]}},
  {{featureType:"road.local",elementType:"labels.text.fill",stylers:[{{color:"#555"}}]}},
  {{featureType:"transit",elementType:"labels.text.fill",stylers:[{{color:"#555"}}]}},
  {{featureType:"water",elementType:"geometry",stylers:[{{color:"#000"}}]}},
  {{featureType:"poi",elementType:"geometry",stylers:[{{color:"#1a1a1a"}}]}},
  {{featureType:"poi",elementType:"labels.text.fill",stylers:[{{color:"#555"}}]}},
];
function toast(m,d=2500){{const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),d);}}
function initMap(){{
  map=new google.maps.Map(document.getElementById('map'),{{
    center:{{lat:curLat,lng:curLng}},zoom:14,
    disableDefaultUI:true,zoomControl:true,zoomControlOptions:{{position:google.maps.ControlPosition.LEFT_BOTTOM}},
    styles:DARK
  }});
  const input=document.getElementById('map-search');
  const sb=new google.maps.places.SearchBox(input);
  sb.addListener('places_changed',()=>{{
    const p=sb.getPlaces();
    if(!p||!p.length)return;
    const pl=p[0];if(!pl.geometry||!pl.geometry.location)return;
    curLat=+pl.geometry.location.lat().toFixed(6);
    curLng=+pl.geometry.location.lng().toFixed(6);
    map.setCenter(pl.geometry.location);map.setZoom(16);
    toast('📍 '+pl.name);
  }});
  map.addListener('center_changed',()=>{{
    const c=map.getCenter();
    curLat=+c.lat().toFixed(6);curLng=+c.lng().toFixed(6);
  }});
}}
function useGPS(){{
  if(!navigator.geolocation){{toast('Browser ไม่รองรับ GPS');return;}}
  toast('กำลังดึง GPS...');
  navigator.geolocation.getCurrentPosition(
    p=>{{curLat=+p.coords.latitude.toFixed(6);curLng=+p.coords.longitude.toFixed(6);
      map.setCenter({{lat:curLat,lng:curLng}});map.setZoom(16);toast('✅ ได้ตำแหน่งแล้ว!');}},
    ()=>toast('ไม่สามารถดึง GPS ได้ กรุณาอนุญาตใน Browser')
  );
}}
function confirmLoc(){{
  toast('กำลังระบุที่อยู่...');
  const gc=new google.maps.Geocoder();
  gc.geocode({{location:{{lat:curLat,lng:curLng}},language:'th'}},(res,status)=>{{
    setConfirmed((status==='OK'&&res[0])?res[0].formatted_address:curLat+','+curLng,curLat,curLng);
  }});
}}
{shared}
</script>
<script async src="https://maps.googleapis.com/maps/api/js?key={mk}&libraries=places&language=th&callback=initMap"></script>"""
        map_body = f"""
<div class="mapwrap" id="map-wrap" {'style="display:none"' if is_confirmed else ''}>
  <div id="map" style="width:100%;height:210px"></div>
  <div class="mpin"><svg width="26" height="34" viewBox="0 0 32 40" fill="none"><path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 24 16 24s16-12 16-24C32 7.16 24.84 0 16 0z" fill="#E8192C"/><circle cx="16" cy="16" r="6" fill="white"/></svg></div>
  <div class="msrow">
    <input class="msinp" id="map-search" placeholder="🔍 ค้นหา (Google Maps)..." type="text">
  </div>
  <button class="mgps" onclick="useGPS()">📡 GPS</button>
  <button class="mconfirm" onclick="confirmLoc()">✓ ยืนยันตำแหน่งนี้</button>
</div>"""
    else:
        # ── Leaflet + Nominatim fallback ──────────────────────────
        map_js = f"""
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
let map,curLat={map_lat},curLng={map_lng},confirmed={str(is_confirmed).lower()};
const VP={{MOTORCYCLE:79,CAR:149,VAN:249}};
const VN={{MOTORCYCLE:'🛵 Motorbike',CAR:'🚗 Sedan/Eco Car',VAN:'🚐 Van/Truck'}};
function toast(m,d=2500){{const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),d);}}
document.addEventListener('DOMContentLoaded',()=>{{
  map=L.map('map',{{zoomControl:false,attributionControl:false}}).setView([curLat,curLng],14);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{maxZoom:19}}).addTo(map);
  L.control.zoom({{position:'bottomleft'}}).addTo(map);
  map.on('move',()=>{{const c=map.getCenter();curLat=+c.lat.toFixed(6);curLng=+c.lng.toFixed(6);}});
}});
function searchAddr(){{
  const q=document.getElementById('map-search').value.trim();if(!q)return;toast('กำลังค้นหา...');
  fetch('https://nominatim.openstreetmap.org/search?q='+encodeURIComponent(q+' ไทย')+'&format=json&limit=1&countrycodes=th',{{headers:{{'User-Agent':'ThaiNova/1.0'}}}})
  .then(r=>r.json()).then(d=>{{if(d.length){{curLat=+d[0].lat;curLng=+d[0].lon;map.setView([curLat,curLng],16);toast('📍 พบตำแหน่ง!');}}else toast('ไม่พบ ลองพิมพ์ใหม่');}}).catch(()=>toast('เกิดข้อผิดพลาด'));
}}
function useGPS(){{
  if(!navigator.geolocation){{toast('Browser ไม่รองรับ GPS');return;}}toast('กำลังดึง GPS...');
  navigator.geolocation.getCurrentPosition(p=>{{curLat=+p.coords.latitude.toFixed(6);curLng=+p.coords.longitude.toFixed(6);map.setView([curLat,curLng],16);toast('✅ ได้ตำแหน่งแล้ว!');}},()=>toast('ไม่สามารถดึง GPS'));
}}
function confirmLoc(){{
  toast('กำลังระบุที่อยู่...');
  fetch('https://nominatim.openstreetmap.org/reverse?lat='+curLat+'&lon='+curLng+'&format=json',{{headers:{{'User-Agent':'ThaiNova/1.0'}}}})
  .then(r=>r.json()).then(d=>setConfirmed(d.display_name||curLat+','+curLng,curLat,curLng)).catch(()=>setConfirmed(curLat+','+curLng,curLat,curLng));
}}
{_shared_js()}
</script>"""
        map_body = f"""
<div class="mapwrap" id="map-wrap" {'style="display:none"' if is_confirmed else ''}>
  <div id="map" style="width:100%;height:210px"></div>
  <div class="mpin"><svg width="26" height="34" viewBox="0 0 32 40" fill="none"><path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 24 16 24s16-12 16-24C32 7.16 24.84 0 16 0z" fill="#E8192C"/><circle cx="16" cy="16" r="6" fill="white"/></svg></div>
  <div class="msrow">
    <input class="msinp" id="map-search" placeholder="ค้นหาที่อยู่..." onkeydown="if(event.key==='Enter')searchAddr()">
    <button class="msbtn" onclick="searchAddr()">ค้นหา</button>
  </div>
  <button class="mgps" onclick="useGPS()">📡 GPS</button>
  <button class="mconfirm" onclick="confirmLoc()">✓ ยืนยันตำแหน่งนี้</button>
</div>"""

    leaflet_css = '' if use_google else '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
{leaflet_css}
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600&family=Barlow+Condensed:wght@700;900&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--red:#E8192C;--rdim:#3a0a0e;--bg:#0a0a0a;--s1:#141414;--s2:#1e1e1e;--bor:#2a2a2a;--brd:rgba(232,25,44,.3);--tx:#f0f0f0;--mu:#888;--gr:#4ade80;--gd:#C9A84C}}
body{{background:var(--bg);color:var(--tx);font-family:'Sarabun',sans-serif;padding:10px}}
h1{{font-family:'Barlow Condensed',sans-serif;font-size:22px;font-weight:900;letter-spacing:1px;text-align:center;margin-bottom:2px}}
h1 span{{color:var(--red)}}.sub{{font-size:10px;color:var(--mu);text-align:center;margin-bottom:14px}}
.stepper{{display:flex;align-items:center;margin-bottom:16px}}
.si{{display:flex;flex-direction:column;align-items:center;gap:3px;flex:1}}
.sc{{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700}}
.sc.done{{background:var(--gr);color:#000}}.sc.active{{background:var(--red);color:#fff;box-shadow:0 0 0 3px rgba(232,25,44,.2)}}
.sc.idle{{background:var(--s2);color:var(--mu);border:1px solid var(--bor)}}
.sl{{font-size:9px;color:var(--mu);text-align:center}}.sl.active{{color:var(--red)}}
.sline{{flex:1;height:2px;background:var(--bor);margin:0 3px;margin-bottom:14px}}.sline.done{{background:var(--gr)}}
.ocard{{background:var(--s1);border:1px solid var(--bor);border-radius:9px;padding:9px 11px;margin-bottom:9px;display:flex;align-items:center;gap:7px}}
.odot{{width:8px;height:8px;border-radius:50%;background:var(--gr);flex-shrink:0}}
.oname{{font-size:11px;font-weight:600}}.oaddr{{font-size:10px;color:var(--mu)}}
.obadge{{margin-left:auto;background:rgba(74,222,128,.1);color:var(--gr);border:1px solid rgba(74,222,128,.2);padding:2px 6px;border-radius:9px;font-size:9px;font-weight:700}}
.mapwrap{{border-radius:9px;overflow:hidden;margin-bottom:9px;border:1px solid var(--bor);position:relative}}
.mpin{{position:absolute;top:50%;left:50%;transform:translate(-50%,-100%);z-index:1000;pointer-events:none;filter:drop-shadow(0 2px 4px rgba(0,0,0,.7))}}
.msrow{{position:absolute;top:7px;left:7px;right:7px;z-index:1000;display:flex;gap:5px}}
.msinp{{flex:1;background:rgba(20,20,20,.95);border:1px solid var(--bor);color:var(--tx);padding:6px 9px;border-radius:6px;font-size:11px;font-family:'Sarabun',sans-serif;outline:none}}
.msbtn{{background:var(--red);border:none;color:#fff;padding:6px 9px;border-radius:6px;font-size:11px;cursor:pointer;font-family:'Sarabun',sans-serif;font-weight:600}}
.mgps{{position:absolute;bottom:40px;right:7px;z-index:1000;background:rgba(20,20,20,.95);border:1px solid var(--bor);color:var(--tx);padding:6px 8px;border-radius:6px;font-size:10px;cursor:pointer;font-family:'Sarabun',sans-serif}}
.mconfirm{{width:100%;background:var(--red);border:none;color:#fff;padding:9px;font-family:'Sarabun',sans-serif;font-size:12px;font-weight:700;cursor:pointer}}
.concard{{background:var(--s1);border:1px solid rgba(74,222,128,.3);border-radius:9px;padding:9px 11px;margin-bottom:9px;display:flex;align-items:flex-start;gap:7px}}
.ddot{{width:8px;height:8px;border-radius:50%;background:var(--red);flex-shrink:0;margin-top:2px}}
.cname{{font-size:11px;font-weight:600;line-height:1.4}}.ccoords{{font-size:9px;color:var(--mu);font-family:monospace}}
.chbtn{{margin-left:auto;background:var(--s2);border:1px solid var(--bor);color:var(--mu);padding:3px 7px;border-radius:5px;font-size:9px;cursor:pointer;font-family:'Sarabun',sans-serif}}
.slbl{{font-size:9px;color:var(--mu);letter-spacing:.5px;text-transform:uppercase;margin:10px 0 6px}}
.vgrid{{display:flex;flex-direction:column;gap:6px;margin-bottom:10px}}
.v-card{{background:var(--s1);border:1.5px solid var(--bor);border-radius:8px;padding:9px 11px;cursor:pointer;display:flex;align-items:center;gap:9px;transition:all .2s}}
.v-card.sel{{border-color:var(--red);background:var(--rdim)}}
.v-icon{{font-size:22px;flex-shrink:0}}.v-name{{font-size:11px;font-weight:600}}.v-name.sel{{color:var(--red)}}
.v-detail{{font-size:10px;color:var(--mu);margin-top:1px}}
.v-price{{font-family:'Barlow Condensed',sans-serif;font-size:17px;font-weight:700;text-align:right;margin-left:auto}}
.v-eta{{font-size:9px;color:var(--mu);text-align:right}}
.sgrid{{display:flex;gap:6px;margin-bottom:10px}}
.sched-btn{{flex:1;background:var(--s1);border:1.5px solid var(--bor);color:var(--mu);padding:8px 5px;border-radius:8px;font-family:'Sarabun',sans-serif;font-size:10px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:4px}}
.sched-btn.sel{{border-color:var(--red);background:var(--rdim);color:var(--red)}}
.sumcard{{background:var(--s1);border:1px solid var(--bor);border-radius:9px;padding:11px;margin-bottom:9px}}
.sumtitle{{font-size:9px;color:var(--mu);letter-spacing:.5px;text-transform:uppercase;margin-bottom:7px}}
.sumrow{{display:flex;justify-content:space-between;align-items:center;font-size:10px;padding:5px 0;border-bottom:1px solid var(--bor)}}
.sumrow:last-child{{border-bottom:none;padding-top:7px;font-size:13px;font-weight:700}}
.sumlbl{{color:var(--mu)}}.sumval{{text-align:right;max-width:58%;font-size:10px}}
.sumprice{{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700}}
.cbtn{{width:100%;border:none;color:#fff;padding:11px;border-radius:8px;font-family:'Sarabun',sans-serif;font-size:12px;font-weight:700;cursor:pointer;margin-bottom:6px;display:flex;align-items:center;justify-content:center;gap:6px;transition:all .2s}}
.cbtn:disabled{{opacity:.5;cursor:not-allowed}}
.map-tag{{position:absolute;top:7px;right:7px;z-index:1000;background:rgba(20,20,20,.9);border:1px solid var(--bor);color:var(--mu);padding:3px 7px;border-radius:5px;font-size:9px}}
.toast{{position:fixed;top:10px;left:50%;transform:translateX(-50%);background:var(--s1);border:1px solid var(--brd);color:var(--tx);padding:6px 12px;border-radius:7px;font-size:10px;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none;max-width:90%;text-align:center}}
.toast.show{{opacity:1}}
</style></head><body>
<div class="toast" id="toast"></div>
<h1>จัดส่ง<span>Lalamove</span></h1>
<div class="sub">{'🗺️ Google Maps' if use_google else 'ลากแผนที่เพื่อปักหมุด'} · ส่งถึงหน้าอู่ภายใน 2 ชั่วโมง</div>
<div class="stepper">
  <div class="si"><div class="sc done">✓</div><div class="sl">ต้นทาง</div></div>
  <div class="sline done"></div>
  <div class="si"><div class="sc {sc(2)}">{snum(2)}</div><div class="sl {'active' if sc(2)=='active' else ''}">ปลายทาง</div></div>
  <div class="sline {sl(2)}"></div>
  <div class="si"><div class="sc {sc(3)}">3</div><div class="sl {'active' if sc(3)=='active' else ''}">ยานพาหนะ</div></div>
  <div class="sline {sl(3)}"></div>
  <div class="si"><div class="sc {sc(4)}">4</div><div class="sl {'active' if sc(4)=='active' else ''}">ยืนยัน</div></div>
</div>
<div class="ocard"><div class="odot"></div><div><div class="oname">ThaiNova AutoPaint</div><div class="oaddr">13.8468, 100.7983 · คู้ขวา กรุงเทพฯ</div></div><span class="obadge">ต้นทาง</span></div>
{map_body}
<div class="concard" id="con-card" {'style="display:none"' if not is_confirmed else ''}>
  <div class="ddot"></div>
  <div style="flex:1"><div class="cname" id="con-name">{addr_short}</div>
  <div class="ccoords" id="con-coords">{dest_lat or ''}, {dest_lng or ''}</div></div>
  <button class="chbtn" onclick="changeAddr()">เปลี่ยน</button>
</div>
<div class="slbl">เลือกยานพาหนะ</div>
<div class="vgrid">
  {vrow("MOTORCYCLE","🛵","Motorbike","≤ 20 kg · สีขนาดเล็ก","79","30-45 นาที")}
  {vrow("CAR","🚗","Sedan / Eco Car","≤ 50 kg · หลายกระป๋อง","149","45-60 นาที")}
  {vrow("VAN","🚐","Van / Truck","≤ 500 kg · ล็อตใหญ่","249","60-90 นาที")}
</div>
<div class="slbl">เวลาจัดส่ง</div>
<div class="sgrid">
  {sbtn("now","⚡","ส่งเดี๋ยวนี้")}
  {sbtn("later","📅","นัดล่วงหน้า")}
</div>
<div class="sumcard">
  <div class="sumtitle">สรุปคำสั่งส่ง</div>
  <div class="sumrow"><span class="sumlbl">ปลายทาง</span><span class="sumval" id="sum-dest">{sum_dest}</span></div>
  <div class="sumrow"><span class="sumlbl">ยานพาหนะ</span><span class="sumval" id="sum-v">{sum_vname}</span></div>
  <div class="sumrow"><span class="sumlbl">ระยะทาง</span><span class="sumval" id="sum-dist">{q_dist if q_dist else "—"}</span></div>
  <div class="sumrow">
    <span>ค่าจัดส่ง <span id="pnote" style="font-size:9px;color:{price_color}">({price_note})</span></span>
    <span class="sumprice" id="sum-price" style="color:{price_color}">฿{disp_price}</span>
  </div>
</div>
{map_js}
</body></html>"""

    render_nav(show_cart=False)
    st.markdown("<div style='padding:16px 20px'>", unsafe_allow_html=True)

    bc = st.columns([1,5])
    with bc[0]:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← กลับ", key="del_back"):
            go('cart' if from_cart else 'home')
        st.markdown('</div>', unsafe_allow_html=True)

    title = "สั่งซื้อ + จัดส่ง" if from_cart else "จัดส่ง Lalamove"
    st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)

    # ── Cart summary (from_cart mode) ──────────────────────────
    if from_cart:
        st.markdown('<div class="sum-card">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">สินค้าในออเดอร์</div>', unsafe_allow_html=True)
        for _, item in st.session_state.cart.items():
            st.markdown(
                f'<div class="sum-row"><span>{item["name"][:28]} ×{item["qty"]}</span>'
                f'<span>฿{item["price"]*item["qty"]:,.0f}</span></div>',
                unsafe_allow_html=True
            )
        st.markdown(
            f'<div class="sum-row"><span style="font-weight:700">รวมค่าสินค้า</span>'
            f'<span>฿{cart_total():,.0f}</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Big delivery iframe / กล่องที่อยู่ ──────────────────────
    _show_map = st.session_state.get("show_map_delivery", False)

    if dest_lat and not _show_map:
        # ✅ มีพิกัดแล้ว — แสดงกล่องที่อยู่ + ปุ่มเปลี่ยน/รีเซ็ต
        st.markdown(
            f'<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.25);'
            f'border-radius:10px;padding:12px 16px;margin-bottom:8px">'
            f'<div style="font-size:11px;color:#4ade80;font-weight:700;margin-bottom:4px">'
            f'📍 ที่อยู่ที่เลือกแล้ว</div>'
            f'<div style="font-size:13px;font-weight:600;line-height:1.4">{dest_addr}</div>'
            f'<div style="font-size:10px;color:var(--muted);font-family:monospace;margin-top:4px">'
            f'{dest_lat:.5f}, {dest_lng:.5f}</div>'
            f'</div>', unsafe_allow_html=True)
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            if st.button("🗺️ เปลี่ยนตำแหน่ง", key="del_show_map", use_container_width=True):
                st.session_state.show_map_delivery = True
                st.rerun()
        with _mc2:
            if st.button("🔄 รีเซ็ตที่อยู่", key="del_reset_addr", use_container_width=True):
                st.session_state.checkout_lat         = None
                st.session_state.checkout_lng         = None
                st.session_state.checkout_addr        = ""
                st.session_state.checkout_quote_id    = None
                st.session_state.checkout_quote_price = None
                st.session_state.checkout_quote_dist  = None
                st.session_state.show_map_delivery    = False
                st.rerun()
    else:
        # 🗺️ ยังไม่มีพิกัด หรือกด "เปลี่ยนตำแหน่ง" — แสดงแผนที่
        components.html(html, height=420, scrolling=False)

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # STREAMLIT CHECKOUT — Single-pass, one calculate button
    # ══════════════════════════════════════════════════════════════

    # ── ขั้นตอนที่ 1: ยืนยันที่อยู่ปลายทาง ─────────────────────
    st.markdown(
        '<div style="background:rgba(232,25,44,.05);border:1px solid rgba(232,25,44,.15);'
        'border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:var(--muted)">'
        '📍 ปักหมุดบนแผนที่ด้านบน หรือพิมพ์ที่อยู่ปลายทางในช่องด้านล่าง '
        'จากนั้นเลือกยานพาหนะ แล้วกด <strong>"💰 คำนวณราคาจัดส่ง"</strong> ได้เลย'
        '</div>', unsafe_allow_html=True)

    addr_txt = dest_addr or st.session_state.get("checkout_addr", "")

    if dest_lat:
        st.markdown(
            f'<div class="addr-box">'
            f'<span style="color:#4ade80;font-weight:700">✓ ที่อยู่:</span> {dest_addr}<br>'
            f'<span style="font-size:10px;color:var(--muted);font-family:monospace">'
            f'{dest_lat:.5f}, {dest_lng:.5f}</span></div>',
            unsafe_allow_html=True)

    # ── ขั้นตอนที่ 2: เลือกยานพาหนะ ────────────────────────────
    st.markdown(
        '<div style="font-size:11px;color:var(--muted);letter-spacing:.5px;'
        'text-transform:uppercase;margin:14px 0 6px">🚗 เลือกยานพาหนะ</div>',
        unsafe_allow_html=True)
    veh_sel = st.selectbox("", list(VEHICLES.keys()),
        format_func=lambda k: f"{VEHICLES[k]['label']}  ·  ฿{VEHICLES[k]['price']}  ·  {VEHICLES[k]['eta']}",
        index=list(VEHICLES.keys()).index(st.session_state.checkout_vehicle),
        key="del_veh_sel", label_visibility="collapsed")

    # ── ขั้นตอนที่ 3: ผู้ชำระค่าจัดส่ง ─────────────────────────
    st.markdown(
        '<div style="font-size:11px;color:var(--muted);letter-spacing:.5px;'
        'text-transform:uppercase;margin:14px 0 6px">💳 ผู้ชำระค่าจัดส่ง</div>',
        unsafe_allow_html=True)
    lala_pay_opts = [
        "🏪 ร้านค้าชำระ (ThaiNova จ่ายค่าส่งให้ Lalamove)",
        "💵 ลูกค้าชำระ — Driver เก็บเงินสดที่ปลายทาง (POD)",
        "🏦 ลูกค้าชำระ — โอนเงินค่าส่งให้ร้านก่อนจัดส่ง",
    ]
    pay_type_idx = {"sender":0,"recipient_cash":1,"recipient_transfer":2}.get(
        st.session_state.lala_pay_type, 0)
    lala_pay = st.radio("", lala_pay_opts,
        index=pay_type_idx, key="del_lala_pay", label_visibility="collapsed")
    lala_pay_key = ["sender","recipient_cash","recipient_transfer"][lala_pay_opts.index(lala_pay)]
    st.session_state.lala_pay_type = lala_pay_key

    if lala_pay_key == "recipient_cash":
        st.markdown(
            '<div style="background:rgba(201,168,76,.08);border:1px solid rgba(201,168,76,.25);'
            'border-radius:7px;padding:8px 12px;font-size:11px;color:#C9A84C;margin-bottom:4px">'
            '⚠️ Driver จะเก็บค่าจัดส่งจากผู้รับเป็นเงินสด (POD)</div>',
            unsafe_allow_html=True)
    elif lala_pay_key == "recipient_transfer":
        st.markdown(
            '<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.2);'
            'border-radius:7px;padding:8px 12px;font-size:11px;color:#4ade80;margin-bottom:4px">'
            '📲 ลูกค้าโอนค่าจัดส่งให้ร้านก่อน — PromptPay: <strong>062-737-7700</strong></div>',
            unsafe_allow_html=True)

    # ── ขั้นตอนที่ 4: ข้อมูลผู้รับ (from_cart เท่านั้น) ────────
    cust_name  = ""
    cust_phone = ""
    if from_cart:
        st.markdown('<div class="co-section" style="margin-top:14px">', unsafe_allow_html=True)
        st.markdown('<div class="co-section-title">👤 ข้อมูลผู้รับ</div>', unsafe_allow_html=True)
        cust_name  = st.text_input("ชื่อ-นามสกุล / ชื่ออู่ *",
            value=st.session_state.cust_name, key="del_name",
            placeholder="เช่น อู่ซ่อมรถ ลาดพร้าว")
        cust_phone = st.text_input("เบอร์โทร *",
            value=st.session_state.cust_phone, key="del_phone",
            placeholder="0XX-XXX-XXXX")
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # ปุ่มคำนวณราคาเพียงปุ่มเดียว — validate ครบ → call API → fallback
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    if st.button("💰 คำนวณราคาจัดส่ง", key="del_calc",
                 type="primary", use_container_width=True):
        # ── Step 1: resolve พิกัดปลายทาง ──────────────────────────
        _lat, _lng = dest_lat, dest_lng
        if _lat:
            # มีพิกัดจากแผนที่แล้ว — ถ้า addr ว่างให้ reverse geocode เติมให้
            if not dest_addr:
                with st.spinner("🔍 กำลังดึงชื่อที่อยู่..."):
                    _, _, _rfmt = geocode(f"{_lat},{_lng}", mk)
                if _rfmt:
                    st.session_state.checkout_addr = _rfmt
        elif addr_txt:
            # ไม่มีพิกัด แต่มีข้อความ → geocode
            with st.spinner("🔍 กำลังค้นหาที่อยู่..."):
                _lat, _lng, _fmt = geocode(addr_txt, mk)
            if _lat:
                st.session_state.checkout_lat      = _lat
                st.session_state.checkout_lng      = _lng
                st.session_state.checkout_addr     = _fmt
                st.session_state.checkout_quote_id = None
            else:
                st.error("❌ ไม่พบที่อยู่นี้ กรุณาพิมพ์ให้ละเอียดขึ้น เช่น ถนน แขวง เขต จังหวัด")
                st.stop()
        else:
            # ไม่มีทั้งพิกัดและข้อความ
            st.error("❌ กรุณาปักหมุดบนแผนที่ หรือกรอกที่อยู่ปลายทาง")
            st.stop()

        # ── Step 2: validate fields อื่น ────────────────────────
        missing = []
        if from_cart and not cust_name:
            missing.append("ชื่อ-นามสกุลผู้รับ")
        if from_cart and not cust_phone:
            missing.append("เบอร์โทรผู้รับ")

        if missing:
            st.error("❌ ข้อมูลยังไม่ครบ กรุณากรอก:\n" +
                     "\n".join(f"  • {m}" for m in missing))
        elif keys_ok:
            with st.spinner("🚀 กำลังคำนวณราคาจัดส่ง..."):
                q = get_quotation(_lat, _lng, veh_sel, lk, ls)
            if q["ok"]:
                st.session_state.checkout_quote_id       = q["quotation_id"]
                st.session_state.checkout_quote_price    = q["price"]
                st.session_state.checkout_quote_dist     = q["distance"]
                st.session_state.checkout_vehicle        = veh_sel
                st.session_state.checkout_stop_sender    = q["stop_sender"]
                st.session_state.checkout_stop_recipient = q["stop_recipient"]
                st.rerun()
            else:
                fallback = str(VEHICLES[veh_sel]["price"])
                st.warning(f"⚠️ Lalamove API: {q['error']}\n\n"
                           f"ใช้ราคาประมาณ ฿{fallback} แทน")
                st.session_state.checkout_quote_id    = "estimate"
                st.session_state.checkout_quote_price = fallback
                st.session_state.checkout_quote_dist  = ""
                st.session_state.checkout_vehicle     = veh_sel
                st.rerun()
        else:
            # ไม่มี Lalamove API key — fallback ทันที
            fallback = str(VEHICLES[veh_sel]["price"])
            st.session_state.checkout_quote_id    = "estimate"
            st.session_state.checkout_quote_price = fallback
            st.session_state.checkout_quote_dist  = ""
            st.session_state.checkout_vehicle     = veh_sel
            st.rerun()

    if not keys_ok and not has_quote:
        st.caption("ℹ️ ไม่มี Lalamove API key — จะใช้ราคาประมาณ")

    # ══════════════════════════════════════════════════════════════
    # แสดงผลราคา + checkout (หลังคำนวณสำเร็จ)
    # ══════════════════════════════════════════════════════════════
    if has_quote:
        is_estimate = st.session_state.checkout_quote_id == "estimate"
        pc  = "#C9A84C" if is_estimate else "#4ade80"
        pb  = "rgba(201,168,76,.08)" if is_estimate else "rgba(74,222,128,.08)"
        pb2 = "rgba(201,168,76,.3)"  if is_estimate else "rgba(74,222,128,.3)"
        p_icon = "⚠️" if is_estimate else "✅"
        p_note = "ราคาประมาณ" if is_estimate else "ราคาจริง Lalamove ✓"
        dist_line = (f'<div style="font-size:11px;color:var(--muted)">📏 ระยะทาง: {q_dist}</div>'
                     if q_dist and not is_estimate else "")

        st.markdown(
            f'<div style="background:{pb};border:1px solid {pb2};'
            f'border-radius:10px;padding:14px 18px;margin:8px 0">'
            f'<div style="font-size:11px;color:{pc};margin-bottom:4px">'
            f'{p_icon} ค่าจัดส่ง ({VEHICLES[st.session_state.checkout_vehicle]["label"]}) — {p_note}</div>'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:42px;'
            f'font-weight:700;color:{pc};line-height:1">฿{q_price}</div>'
            f'{dist_line}</div>', unsafe_allow_html=True)

        if from_cart:
            STORE_PP_PHONE = "0627377700"
            STORE_BANK     = "กสิกรไทย (KBank)"
            STORE_ACCOUNT  = "129-1-89092-6"
            STORE_NAME     = "นายปัญญธร ชัยพิศุทธิ์"

            cart_amt = cart_total()
            try:    delivery_fee_num = float(st.session_state.checkout_quote_price)
            except: delivery_fee_num = float(VEHICLES[veh_sel]["price"])
            total_amt = cart_amt + delivery_fee_num

            if lala_pay_key == "recipient_transfer":
                st.markdown(
                    f'<div style="background:rgba(201,168,76,.08);border:1px solid rgba(201,168,76,.3);'
                    f'border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#C9A84C">'
                    f'⚠️ <strong>ค่าจัดส่ง ฿{delivery_fee_num:,.0f}</strong> — กรุณาโอนค่าส่งก่อนจัดส่ง<br>'
                    f'PromptPay: <strong>062-737-7700</strong></div>', unsafe_allow_html=True)
            elif lala_pay_key == "recipient_cash":
                st.markdown(
                    '<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.2);'
                    'border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#4ade80">'
                    '✅ Driver เก็บค่าจัดส่งเป็นเงินสดที่ปลายทาง (POD)</div>', unsafe_allow_html=True)

            # สรุปออเดอร์
            st.markdown('<div class="sum-card">', unsafe_allow_html=True)
            st.markdown('<div class="co-section-title">สรุปออเดอร์</div>', unsafe_allow_html=True)
            for _, item in st.session_state.cart.items():
                st.markdown(
                    f'<div class="sum-row"><span>{item["name"][:28]} ×{item["qty"]}</span>'
                    f'<span>฿{item["price"]*item["qty"]:,.0f}</span></div>',
                    unsafe_allow_html=True)
            pnote2 = "ราคาประมาณ" if is_estimate else "จริง ✓"
            st.markdown(
                f'<div class="sum-row"><span>ค่าจัดส่ง {VEHICLES[st.session_state.checkout_vehicle]["label"]} ({pnote2})</span>'
                f'<span>฿{delivery_fee_num:,.0f}</span></div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="sum-row"><span>ยอดรวมทั้งหมด</span>'
                f'<span>฿{total_amt:,.0f}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # วิธีชำระเงินค่าสินค้า
            st.markdown('<div class="co-section">', unsafe_allow_html=True)
            st.markdown('<div class="co-section-title">ชำระเงินค่าสินค้า</div>', unsafe_allow_html=True)
            pay_opts   = ["📱 PromptPay / QR Code", "🏦 โอนเงินเข้าบัญชีธนาคาร"]
            pay_choice = st.radio("", pay_opts, key="del_pay", label_visibility="collapsed")

            if "PromptPay" in pay_choice:
                st.session_state.payment_method = "promptpay"
                script_dir = os.path.dirname(os.path.abspath(__file__))
                kbank_path = next(
                    (os.path.join(script_dir, f) for f in ("kbank_qr.png","kbank_qr.jpg","kbank_qr.jpeg")
                     if os.path.exists(os.path.join(script_dir, f))), "")
                if kbank_path:
                    with open(kbank_path,"rb") as f: kbank_b64 = base64.b64encode(f.read()).decode()
                    ext = "jpeg" if kbank_path.endswith((".jpg",".jpeg")) else "png"
                    st.markdown(f"""<div class="qr-box">
                      <div style="font-size:12px;font-weight:600;margin-bottom:8px">สแกน QR ชำระค่าสินค้า</div>
                      <img src="data:image/{ext};base64,{kbank_b64}"
                           style="width:220px;border-radius:10px;border:3px solid #2a2a2a;margin-bottom:10px">
                      <div style="font-size:13px;font-weight:700;color:var(--red);margin-bottom:6px">
                        ยอดสินค้า ฿{cart_amt:,.0f}</div>
                      <div style="font-size:12px;font-weight:600">PromptPay: {STORE_PP_PHONE}</div>
                      <div style="font-size:11px;color:var(--muted)">{STORE_NAME}</div>
                      <div style="font-size:10px;color:var(--muted2);margin-top:6px">
                        หลังโอนแนบสลิปทาง LINE หรือ โทร 062-737-7700</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    qr_b64 = gen_qr_b64(STORE_PP_PHONE, cart_amt)
                    if qr_b64:
                        st.markdown(f"""<div class="qr-box">
                          <div style="font-size:12px;font-weight:600;margin-bottom:6px">สแกน QR ชำระเงิน</div>
                          <div style="font-size:22px;font-weight:700;color:var(--red);
                               font-family:'Barlow Condensed',sans-serif;margin-bottom:8px">
                            ฿{cart_amt:,.0f}</div>
                          <img src="data:image/png;base64,{qr_b64}"
                               style="width:200px;border-radius:10px;border:3px solid #2a2a2a;margin-bottom:10px">
                          <div style="font-size:12px;font-weight:600">PromptPay: {STORE_PP_PHONE}</div>
                          <div style="font-size:11px;color:var(--muted)">{STORE_NAME}</div>
                        </div>""", unsafe_allow_html=True)
            else:
                st.session_state.payment_method = "transfer"
                st.markdown(f"""<div style="background:var(--surface2);border:1px solid var(--border);
                     border-radius:10px;padding:16px;text-align:center">
                  <div style="font-size:10px;color:var(--muted);letter-spacing:1px;
                       text-transform:uppercase;margin-bottom:10px">โอนเงินเข้าบัญชี</div>
                  <div style="font-size:14px;font-weight:700;margin-bottom:4px">🏦 {STORE_BANK}</div>
                  <div style="font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:700;
                       color:var(--red);letter-spacing:1px;margin:6px 0">{STORE_ACCOUNT}</div>
                  <div style="font-size:13px;font-weight:600">{STORE_NAME}</div>
                  <div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border);
                       font-size:14px;font-weight:700">
                    ยอดโอน: <span style="color:var(--red)">฿{cart_amt:,.0f}</span></div>
                  <div style="font-size:10px;color:var(--muted);margin-top:6px">
                    หลังโอนแนบสลิปทาง LINE หรือ โทร 062-737-7700</div>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            can_confirm = bool(cust_name and cust_phone and dest_lat)
            if not can_confirm:
                miss2 = [x for x,v in [("ชื่อ",cust_name),("เบอร์โทร",cust_phone),("ที่อยู่",dest_lat)] if not v]
                st.caption(f"⚠️ กรุณากรอก: {', '.join(miss2)}")

            if st.button("🎉 ยืนยันคำสั่งซื้อ", use_container_width=True, type="primary",
                         key="del_confirm", disabled=not can_confirm):
                order_id = gen_order_id(); lala_order_id = ""; share_link = ""
                is_pod   = lala_pay_key == "recipient_cash"
                real_quote = st.session_state.checkout_quote_id not in (None, "estimate")
                if real_quote and keys_ok:
                    with st.spinner("กำลังสร้าง Lalamove order..."):
                        lo = create_lala_order(
                            st.session_state.checkout_quote_id,
                            st.session_state.get("checkout_stop_sender",    "1"),
                            st.session_state.get("checkout_stop_recipient", "2"),
                            cust_name, cust_phone, lk, ls, is_pod=is_pod)
                    if lo.get("debug"):
                        with st.expander("🔍 Lalamove Debug Response", expanded=not lo["ok"]):
                            st.json(lo["debug"])
                    if lo["ok"]:
                        lala_order_id = lo["order_id"]; share_link = lo["share_link"]
                    else:
                        st.error(f"❌ Lalamove create order ล้มเหลว:\n{lo['error']}")
                        st.stop()
                try_save_order({
                    "OrderID": order_id, "DateTime": datetime.now().isoformat(),
                    "CustomerName": cust_name, "CustomerPhone": cust_phone,
                    "Items": json.dumps({ck:cv for ck,cv in st.session_state.cart.items()},
                                        ensure_ascii=False),
                    "CartTotal": cart_amt, "DeliveryMethod": "lalamove",
                    "DeliveryAddr": dest_addr, "Vehicle": veh_sel,
                    "DeliveryFee": delivery_fee_num,
                    "PaymentMethod": st.session_state.payment_method,
                    "TotalAmount": total_amt, "LalamoveID": lala_order_id, "Status": "pending",
                })
                st.session_state.cust_name        = cust_name
                st.session_state.cust_phone       = cust_phone
                st.session_state.order_id         = order_id
                st.session_state.order_lala_id    = lala_order_id
                st.session_state.order_share_link = share_link
                st.session_state.cart             = {}
                go('confirmed')

        else:
            # Standalone (ไม่มีตะกร้า) — ส่ง order ไป Lalamove ตรงๆ
            if st.session_state.checkout_quote_id not in (None, "estimate"):
                st.markdown("---")
                r1, r2 = st.columns(2)
                rn = r1.text_input("ชื่ออู่ / ผู้รับ", key="del_rn")
                rp = r2.text_input("เบอร์โทร (+66...)", key="del_rp")
                if st.button("✅ ส่ง Order ไป Lalamove", use_container_width=True, key="del_co"):
                    if rn and rp and keys_ok:
                        with st.spinner("กำลังสร้าง Order..."):
                            lo = create_lala_order(
                                st.session_state.checkout_quote_id,
                                st.session_state.get("checkout_stop_sender",    "1"),
                                st.session_state.get("checkout_stop_recipient", "2"),
                                rn, rp, lk, ls)
                        if lo.get("debug"):
                            with st.expander("🔍 Lalamove Debug Response", expanded=not lo["ok"]):
                                st.json(lo["debug"])
                        if lo["ok"]:
                            st.success(f"🎉 Order สำเร็จ! ID: {lo['order_id']}")
                            if lo["share_link"]: st.link_button("📍 ติดตาม Driver", lo["share_link"])
                            st.session_state.checkout_quote_id = None
                        else:
                            st.error(f"❌ Lalamove: {lo['error']}")
                    else:
                        st.error("กรุณากรอกชื่อและเบอร์โทร")

    st.markdown("</div>", unsafe_allow_html=True)


def page_colors():
    st.markdown('<div class="sec-title">ค้นหาเบอร์สีรถ</div>', unsafe_allow_html=True)
    brands = ["Toyota","Honda","Isuzu","Nissan","Mitsubishi","Ford","Mazda","Suzuki","Subaru","Chevrolet","BMW","Mercedes-Benz"]
    c1,c2 = st.columns(2)
    brand = c1.selectbox("ยี่ห้อรถ:", ["-- เลือก --"] + brands)
    code  = c2.text_input("รหัสสี (ถ้ารู้):", placeholder="เช่น 1F7, 040")

    if brand != "-- เลือก --" or code:
        st.markdown("""<div class="co-section">
        <div class="co-section-title">วิธีค้นหาเบอร์สีรถ</div>
        <div style="font-size:12px;color:var(--muted);line-height:1.8">
          1. ดูที่สติ๊กเกอร์ข้อมูลรถ (มักอยู่บนกรอบประตู หรือฝากระโปรงหน้า)<br>
          2. แจ้งรหัสสีให้ทีมงาน เพื่อเช็คสต็อกที่ถูกต้อง<br>
          3. โทรสอบถามได้ที่ <strong>087-079-9199</strong>
        </div>
        </div>""", unsafe_allow_html=True)
        st.info(f"🔍 ค้นหาสี **{brand}** {'รหัส: ' + code if code else ''}\n\n"
                f"กรุณาโทรสอบถาม: **087-079-9199** หรือ LINE: @thainova\n\n"
                f"ทีมงานพร้อมช่วยหาสีให้ตรงกับรถคุณ")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-title">ยี่ห้อสีที่มีในร้าน</div>', unsafe_allow_html=True)
    brands_avail = [
        ("🔴 Nippon Paint","สีกาก็อต, ด้านสีเทา, เงิน"),
        ("🟡 TOA","สีพ่น 2K, 1K ครบไลน์"),
        ("🔵 Cromax (Axalta)","สีพ่นรถยนต์ระดับพรีเมียม"),
        ("🟢 Standox","สีมาตรฐานโรงงาน OEM"),
        ("⚪ Sikkens","สียุโรป คุณภาพสูง"),
    ]
    for name, detail in brands_avail:
        st.markdown(f"""<div style="background:var(--surface);border:1px solid var(--border);
        border-radius:8px;padding:10px 14px;margin-bottom:6px;display:flex;
        justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:13px">{name}</span>
        <span style="font-size:11px;color:var(--muted)">{detail}</span>
        </div>""", unsafe_allow_html=True)


def page_contact():
    st.markdown('<div class="sec-title">ติดต่อเรา</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="border-radius:12px;overflow:hidden;border:1px solid var(--border);margin-bottom:12px">
      <iframe src="https://maps.google.com/maps?q=13.8468093,100.7982969&z=16&output=embed&hl=th"
        width="100%" height="240" style="border:0;display:block" allowfullscreen loading="lazy"></iframe>
    </div>""", unsafe_allow_html=True)

    col_map, col_line = st.columns(2)
    with col_map:
        st.link_button("🗺️ เปิด Google Maps", "https://maps.app.goo.gl/S6Esp74JNYGCHQbz8",
                       use_container_width=True)
    with col_line:
        st.link_button("💬 LINE @ThaiNova", "https://line.me/R/ti/p/@thainova",
                       use_container_width=True)

    st.markdown("""
    <div class="contact-card">
      <div style="font-size:10px;color:var(--muted);letter-spacing:.5px;font-weight:600;margin-bottom:8px;text-transform:uppercase">ช่องทางติดต่อ</div>
      <div class="contact-row">
        <div class="contact-icon">📞</div>
        <div><div style="font-size:10px;color:var(--muted)">โทรศัพท์ 1</div>
          <div style="font-size:15px;font-weight:600">087-079-9199</div></div>
        <a href="tel:0870799199" class="call-btn">โทร</a>
      </div>
      <div class="contact-row">
        <div class="contact-icon">📞</div>
        <div><div style="font-size:10px;color:var(--muted)">โทรศัพท์ 2</div>
          <div style="font-size:15px;font-weight:600">062-737-7700</div></div>
        <a href="tel:0627377700" class="call-btn">โทร</a>
      </div>
    </div>
    <div class="contact-card">
      <div style="font-size:10px;color:var(--muted);letter-spacing:.5px;font-weight:600;margin-bottom:8px;text-transform:uppercase">เวลาทำการ</div>
      <div class="hours-row"><span style="color:var(--muted)">จันทร์ – ศุกร์</span>
        <span>08:00 – 18:00 <span style="color:#4ade80;font-size:10px;font-weight:700">● เปิด</span></span></div>
      <div class="hours-row"><span style="color:var(--muted)">เสาร์</span><span>08:00 – 17:00</span></div>
      <div class="hours-row"><span style="color:var(--muted)">อาทิตย์</span>
        <span style="color:var(--red)">ปิด</span></div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════
def admin_view(stock_df, reorder_df, shelf_map_df, purchase_df, lot_df):
    render_nav(show_cart=False)
    st.markdown("<div style='padding:16px 20px'>", unsafe_allow_html=True)
    c1,c2 = st.columns([5,1])
    c1.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;font-weight:700;padding:6px 0">⚙️ Admin Dashboard</div>', unsafe_allow_html=True)
    if c2.button("ออกจากระบบ"):
        st.session_state.logged_in = False; st.session_state.role = 'guest'; st.rerun()

    st.markdown(f'<span class="sync-pill">🟢 Sync อัตโนมัติทุก 5 นาที · {datetime.now().strftime("%H:%M:%S")}</span><br><br>',
                unsafe_allow_html=True)

    total_val = (stock_df['Qty'] * stock_df['Cost']).sum() if 'Cost' in stock_df.columns else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("มูลค่าสต็อก", f"฿{total_val/1e6:.2f}M" if total_val>0 else "—")
    c2.metric("สต็อกต่ำ/หมด", len(reorder_df) if not reorder_df.empty else 0)
    c3.metric("รายการทั้งหมด", f"{len(stock_df):,}")
    c4.metric("Sync ล่าสุด", datetime.now().strftime("%H:%M"))
    st.divider()

    atabs = st.tabs(["📋 สต็อก","🚛 สั่งของ","📥 รับเข้า","🔢 Lot","💰 การเงิน","📦 Orders"])

    with atabs[0]:
        q = st.text_input("🔍 ค้นหา / Barcode:", key="aq")
        df = stock_df[
            stock_df['Name'].str.contains(q, na=False, case=False) |
            stock_df['Barcode'].astype(str).str.contains(q, na=False)
        ] if q else stock_df
        cols = [c for c in ['Barcode','Name','Qty','ShelfMap'] if c in df.columns]
        for sc in ['SupplierName','Supplier','ผู้ผลิต']:
            if sc in df.columns: cols.append(sc); break
        st.dataframe(df[cols], use_container_width=True, hide_index=True)

    with atabs[1]:
        if not reorder_df.empty:
            sc = next((c for c in ['Supplier','SupplierName','ผู้ผลิต'] if c in reorder_df.columns), None)
            if sc:
                for sup in reorder_df[sc].unique():
                    with st.expander(f"📦 {sup}"):
                        items = reorder_df[reorder_df[sc]==sup]
                        show  = [c for c in ['Name','Qty','MinStock'] if c in items.columns]
                        st.dataframe(items[show], use_container_width=True, hide_index=True)
                        st.button(f"🖨️ พิมพ์ใบสั่งซื้อ {sup}", key=f"po_{sup}")

    with atabs[2]:
        if not purchase_df.empty:
            purchase_df['วันที่'] = pd.to_datetime(purchase_df['วันที่'], errors='coerce')
            years = sorted([int(y) for y in purchase_df['วันที่'].dt.year.dropna().unique()], reverse=True)
            mn = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
            c1,c2 = st.columns(2)
            yr = c1.selectbox("ปี:", years)
            mo = c2.selectbox("เดือน:", range(1,13), index=datetime.now().month-1,
                              format_func=lambda x: mn[x-1])
            filt = purchase_df[(purchase_df['วันที่'].dt.year==yr) & (purchase_df['วันที่'].dt.month==mo)]
            if filt.empty: st.info("ไม่พบข้อมูลในช่วงเวลานี้")
            else:
                for (inv,vendor,date),items in filt.groupby(['InvoiceNo','ชื่อบริษัทผู้ขาย','วันที่']):
                    with st.expander(f"📄 {date.strftime('%d/%m/%Y')} · {vendor} · {inv}"):
                        if 'Barcode' in items.columns:
                            mg = pd.merge(items, shelf_map_df[['Barcode','ShelfMap']], on='Barcode', how='left')
                            mg['ShelfMap'] = mg['ShelfMap'].fillna("ยังไม่ได้ระบุ")
                            nc = next((c for c in ['ชื่อสินค้า','Name'] if c in mg.columns), None)
                            qc = next((c for c in ['จำนวน','Qty'] if c in mg.columns), None)
                            if nc and qc:
                                d2 = mg[[nc,qc,'ShelfMap']].copy()
                                d2.columns = ['สินค้า','จำนวน','ที่วาง']
                                st.dataframe(d2, use_container_width=True, hide_index=True)
                        st.button(f"🖨️ พิมพ์", key=f"p_{inv}")

    with atabs[3]:
        if not lot_df.empty:
            ql = st.text_input("ค้นหา:", key="lq")
            dl = lot_df[
                lot_df['Name'].str.contains(ql, na=False, case=False) |
                lot_df['Barcode'].astype(str).str.contains(ql, na=False)
            ] if ql else lot_df
            cm = {k:v for k,v in {'Name':'ชื่อสินค้า','BillNo':'เลขบิล','Date':'วันรับ',
                                   'Remaining':'คงเหลือ','AgeMonths':'อายุ(ด.)','Status':'สถานะ'}.items()
                  if k in dl.columns}
            st.dataframe(dl[list(cm.keys())].rename(columns=cm), use_container_width=True, hide_index=True)

    with atabs[4]:
        if not purchase_df.empty and 'ยอดรวมสินค้า' in purchase_df.columns:
            purchase_df['วันที่'] = pd.to_datetime(purchase_df['วันที่'], errors='coerce')
            yf  = sorted([int(y) for y in purchase_df['วันที่'].dt.year.dropna().unique()], reverse=True)
            mnf = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
            f1,f2 = st.columns(2)
            yrf = f1.selectbox("ปี:", yf, key="fy")
            mof = f2.selectbox("เดือน:", range(1,13), index=datetime.now().month-1,
                               format_func=lambda x: mnf[x-1], key="fm")
            fd = purchase_df[(purchase_df['วันที่'].dt.year==yrf) & (purchase_df['วันที่'].dt.month==mof)]
            if not fd.empty:
                st.metric("ยอดซื้อรวม", f"฿{fd['ยอดรวมสินค้า'].sum():,.0f}")
                ss = fd.groupby('ชื่อบริษัทผู้ขาย')['ยอดรวมสินค้า'].sum().reset_index()
                ss.columns = ['ผู้ขาย','ยอดรวม(฿)']
                st.dataframe(ss.sort_values('ยอดรวม(฿)', ascending=False),
                             use_container_width=True, hide_index=True)

    with atabs[5]:
        st.markdown('<div class="co-section-title">ออเดอร์จากลูกค้าออนไลน์</div>', unsafe_allow_html=True)
        try:
            orders_df = conn.read(worksheet="Orders")
            if not orders_df.empty:
                display_cols = [c for c in ['OrderID','DateTime','CustomerName','CustomerPhone',
                                             'TotalAmount','DeliveryMethod','Status'] if c in orders_df.columns]
                st.dataframe(orders_df[display_cols].sort_values('DateTime', ascending=False) if 'DateTime' in orders_df.columns else orders_df[display_cols],
                             use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีออเดอร์")
        except:
            st.info("💡 สร้างแท็บ **Orders** ใน Google Sheets เพื่อบันทึกออเดอร์อัตโนมัติ\n\n"
                    "คอลัมน์: OrderID, DateTime, CustomerName, CustomerPhone, Items, CartTotal, "
                    "DeliveryMethod, DeliveryAddr, Vehicle, DeliveryFee, PaymentMethod, TotalAmount, LalamoveID, Status")

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# CUSTOMER VIEW
# ══════════════════════════════════════════════════════════════
def customer_view(stock_df):
    page = st.session_state.page

    # Full-page checkout experiences (no nav tabs)
    from_cart = bool(st.session_state.cart)
    if page in ('cart', 'checkout', 'confirmed') or (page == 'delivery' and from_cart):
        if page == 'cart':       page_cart()
        elif page == 'checkout': page_checkout()
        elif page == 'confirmed':page_confirmed()
        elif page == 'delivery': page_delivery()
        return

    # Normal pages with nav
    render_nav()

    # Admin login (collapsed by default)
    with st.expander("🔑 Admin Login", expanded=False):
        u = st.text_input("Username", key="lu")
        p = st.text_input("Password", type="password", key="lp")
        if st.button("เข้าสู่ระบบ", key="login_btn"):
            au = st.secrets.get("admin",{}).get("username","admin")
            ap = st.secrets.get("admin",{}).get("password","1234")
            if u==au and p==ap:
                st.session_state.logged_in=True; st.session_state.role='admin'; st.rerun()
            else: st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    st.markdown("<div style='padding:8px 16px'>", unsafe_allow_html=True)
    render_page_nav(page)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='padding:0 16px 16px'>", unsafe_allow_html=True)

    if page == 'home':      page_home(stock_df)
    elif page == 'shop':    page_shop(stock_df)
    elif page == 'delivery':page_delivery()
    elif page == 'colors':  page_colors()
    elif page == 'contact': page_contact()
    else: page_home(stock_df)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
try:
    stock_df, reorder_df, shelf_map_df, purchase_df, lot_df = load_data()
    if st.session_state.role == 'admin':
        admin_view(stock_df, reorder_df, shelf_map_df, purchase_df, lot_df)
    else:
        customer_view(stock_df)
except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาด: {e}")
    st.info("ตรวจสอบ secrets.toml และชื่อแท็บ: Stock, Reorder_All, Shelf_Map, Purchase_Invoices, Lot_Tracking")
