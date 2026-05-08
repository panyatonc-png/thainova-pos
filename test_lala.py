import requests, hmac, hashlib, time, json, toml

s = toml.load('.streamlit/secrets.toml')
LALA_KEY    = s['lalamove']['api_key']
LALA_SECRET = s['lalamove']['api_secret']
GMAPS_KEY   = s['google']['maps_key']
CRLF        = "\r\n"

# ── Test 1: Google Geocoding ──────────────────────
print("=" * 45)
print("TEST 1: Google Geocoding")
print("=" * 45)
r = requests.get(
    "https://maps.googleapis.com/maps/api/geocode/json",
    params={"address":"ลาดพร้าว 87 กรุงเทพ", "key":GMAPS_KEY, "language":"th"},
    timeout=5
)
d = r.json()
if d["status"] == "OK":
    loc = d["results"][0]["geometry"]["location"]
    dest_lat = str(loc["lat"])
    dest_lng = str(loc["lng"])
    print(f"✅ {d['results'][0]['formatted_address']}")
    print(f"   lat={dest_lat}, lng={dest_lng}")
else:
    print(f"❌ {d['status']}: {d.get('error_message','')}")
    dest_lat, dest_lng = "13.8021", "100.6098"

# ── Test 2: Lalamove Quotation ────────────────────
print()
print("=" * 45)
print("TEST 2: Lalamove Quotation")
print("=" * 45)
path = "/v3/quotations"
body = json.dumps({"data": {
    "serviceType": "MOTORCYCLE",
    "language": "th_TH",
    "stops": [
        {"coordinates": {"lat": "13.756330", "lng": "100.501762"},
         "address": "ThaiNova AutoPaint Bangkok"},
        {"coordinates": {"lat": dest_lat, "lng": dest_lng},
         "address": "ลาดพร้าว 87 กรุงเทพ"}
    ]
}}, separators=(',', ':'))

ts  = str(int(time.time() * 1000))
raw = ts + CRLF + "POST" + CRLF + path + CRLF + CRLF + body
sig = hmac.new(LALA_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()

r2 = requests.post(
    "https://rest.sandbox.lalamove.com" + path,
    headers={"Content-Type": "application/json",
             "Authorization": f"hmac {LALA_KEY}:{ts}:{sig}",
             "Market": "TH", "Accept": "application/json"},
    data=body.encode(), timeout=10
)
d2 = r2.json()
if r2.status_code in [200, 201]:
    data = d2["data"]
    qid  = data["quotationId"]
    price = data["priceBreakdown"]["total"]
    dist  = int(data["distance"]["value"]) / 1000
    print(f"✅ quotationId : {qid}")
    print(f"   ราคา        : {price} THB")
    print(f"   ระยะทาง     : {dist:.1f} km")
    print(f"   หมดอายุ     : {data['expiresAt']}")

    # ── Test 3: Create Order ──────────────────────
    print()
    print("=" * 45)
    print("TEST 3: Create Order (Sandbox)")
    print("=" * 45)
    path2 = "/v3/orders"
    body2 = json.dumps({"data": {
        "quotationId": qid,
        "sender": {
            "stopId":  data["stops"][0]["stopId"],
            "name":    "ThaiNova AutoPaint",
            "phone":   "+66870799199"
        },
        "recipients": [{
            "stopId":  data["stops"][1]["stopId"],
            "name":    "อู่ทดสอบ",
            "phone":   "+66890000000",
            "remarks": "ทดสอบระบบ ThaiNova"
        }],
        "isPODEnabled": False
    }}, separators=(',', ':'))

    ts2  = str(int(time.time() * 1000))
    raw2 = ts2 + CRLF + "POST" + CRLF + path2 + CRLF + CRLF + body2
    sig2 = hmac.new(LALA_SECRET.encode(), raw2.encode(), hashlib.sha256).hexdigest()

    r3 = requests.post(
        "https://rest.sandbox.lalamove.com" + path2,
        headers={"Content-Type": "application/json",
                 "Authorization": f"hmac {LALA_KEY}:{ts2}:{sig2}",
                 "Market": "TH", "Accept": "application/json"},
        data=body2.encode(), timeout=10
    )
    d3 = r3.json()
    if r3.status_code in [200, 201]:
        od = d3["data"]
        print(f"✅ orderId   : {od.get('orderId','')}")
        print(f"   shareLink : {od.get('shareLink','')}")
        print(f"   status    : {od.get('status','')}")
    else:
        print(f"❌ HTTP {r3.status_code}")
        print(json.dumps(d3, ensure_ascii=False, indent=2))
else:
    print(f"❌ HTTP {r2.status_code}")
    print(json.dumps(d2, ensure_ascii=False, indent=2))

print()
print("=" * 45)
print("เสร็จ!")
EOF