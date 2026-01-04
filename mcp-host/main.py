import time
import requests
import os
import math

REST_BASE = os.getenv("REST_BASE_URL", "http://localhost:8080")
PRODUCT_ID = 1
THRESHOLD = 15
DISCOUNT = 10.0
EPS = 0.01 

def now_ms():
    return int(time.time() * 1000)

def log(msg):
    print(f"[{now_ms()}] {msg}", flush=True)

def search_low_stock():
    t0 = time.time()
    resp = requests.get(f"{REST_BASE}/products")
    resp.raise_for_status()
    items = resp.json()
    low = [p for p in items if p["stock"] <= THRESHOLD]
    dt = (time.time() - t0) * 1000
    log(f"searchLowStock: {len(low)} items, dt={dt:.2f} ms")
    return low, dt

def apply_discount(pid, percent):
    t0 = time.time()
    r = requests.get(f"{REST_BASE}/products/{pid}")
    r.raise_for_status()
    cur = r.json()

    target_price = round(cur["price"] * (1 - percent / 100), 2)

    if math.isclose(cur["price"], target_price, abs_tol=EPS):
        dt = (time.time() - t0) * 1000
        log(f"applyDiscount skipped (already discounted) pid={pid} price={cur['price']} dt={dt:.2f} ms")
        return dt, cur["price"]

    r2 = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": target_price})
    r2.raise_for_status()
    dt = (time.time() - t0) * 1000
    log(f"applyDiscount pid={pid} percent={percent}% new_price={target_price} dt={dt:.2f} ms")
    return dt, target_price

def notify_pending(pid):
    t0 = time.time()
    dt = (time.time() - t0) * 1000
    log(f"notifyPending pid={pid} dt={dt:.2f} ms")
    return dt

if __name__ == "__main__":
    low, dt_search = search_low_stock()
    if not low:
        log("No low-stock items; exit.")
        exit(0)

    target = low[0]["id"]
    dt_disc, new_price = apply_discount(target, DISCOUNT)
    dt_notify = notify_pending(target)

    check = requests.get(f"{REST_BASE}/products/{target}").json()
    log(f"State after actions: id={target} price={check['price']} stock={check['stock']}")
    total = dt_search + dt_disc + dt_notify
    log(f"Total pipeline time={total:.2f} ms")