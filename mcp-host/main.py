import time
import requests
import os

REST_BASE = os.getenv("REST_BASE_URL", "http://localhost:8080")
THRESHOLD = 15
DISCOUNT = 10.0

BASE_PRICES = {
    1: 1499.0,
    2: 29.0,
    3: 79.0,
    4: 329.0,
    5: 119.0,
    6: 149.0,
    7: 199.0,
    8: 129.0,
    9: 799.0,
    10: 999.0,
    11: 899.0,
    12: 649.0,
    13: 59.0,
    14: 179.0,
    15: 549.0,
    16: 229.0,
    17: 249.0,
    18: 159.0,
    19: 399.0,
    20: 299.0,
}

def now_ms():
    return int(time.time() * 1000)

def log(msg):
    print(f"[{now_ms()}] {msg}", flush=True)

def fetch_all():
    resp = requests.get(f"{REST_BASE}/products")
    resp.raise_for_status()
    return resp.json()

def patch_price(pid, price):
    r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": price})
    r.raise_for_status()
    return r.json()

def run():
    t0 = time.time()
    items = fetch_all()
    dt_fetch = (time.time() - t0) * 1000
    log(f"Fetched {len(items)} products in {dt_fetch:.2f} ms")

    total_ops = 0
    for p in items:
        pid = p["id"]
        stock = p["stock"]
        cur_price = p["price"]
        base_price = BASE_PRICES.get(pid, cur_price)
        target_price = round(base_price * (1 - DISCOUNT / 100), 2)

        if stock <= THRESHOLD:
            if cur_price > target_price:
                patch_price(pid, target_price)
                log(f"applyDiscount pid={pid} stock={stock} price {cur_price} -> {target_price}")
                total_ops += 1
            else:
                log(f"skipDiscount (already discounted) pid={pid} stock={stock} price={cur_price} target={target_price}")
        else:
            if cur_price < base_price:
                patch_price(pid, base_price)
                log(f"resetPrice pid={pid} stock={stock} price {cur_price} -> {base_price}")
                total_ops += 1
            else:
                log(f"noChange pid={pid} stock={stock} price={cur_price}")

    log(f"Ops executed: {total_ops}")

if __name__ == "__main__":
    run()