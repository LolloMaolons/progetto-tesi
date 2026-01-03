from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn, os, json, redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL)

app = FastAPI(title="API REST - Catalog/Orders/Users")

class Product(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category: str | None = None
    description: str | None = None

DB_PRODUCTS = {
    1: Product(id=1, name="Laptop Pro", price=1499.0, stock=10, category="laptop", description='15" performance laptop'),
    2: Product(id=2, name="Mouse", price=29.0, stock=200, category="accessories", description="Wireless ergonomic mouse"),
    3: Product(id=3, name="Keyboard", price=79.0, stock=120, category="accessories", description="Mechanical keyboard"),
    4: Product(id=4, name="Monitor 27\"", price=329.0, stock=45, category="monitor", description='27" QHD IPS monitor'),
    5: Product(id=5, name="Headset", price=119.0, stock=80, category="audio", description="Wireless noise-cancelling headset"),
    6: Product(id=6, name="Webcam 4K", price=149.0, stock=60, category="accessories", description="4K streaming webcam"),
    7: Product(id=7, name="Docking Station", price=199.0, stock=35, category="accessories", description="USB-C docking station"),
    8: Product(id=8, name="SSD 1TB", price=129.0, stock=150, category="storage", description="NVMe 1TB SSD"),
    9: Product(id=9, name="GPU External", price=799.0, stock=8, category="gpu", description="External GPU enclosure"),
    10: Product(id=10, name="Laptop Air", price=999.0, stock=25, category="laptop", description='13" ultrabook'),
    11: Product(id=11, name="Smartphone Plus", price=899.0, stock=55, category="phone", description='6.7" OLED smartphone'),
    12: Product(id=12, name="Tablet Max", price=649.0, stock=40, category="tablet", description='12" tablet with pen'),
    13: Product(id=13, name="Charger 100W", price=59.0, stock=300, category="accessories", description="GaN fast charger"),
    14: Product(id=14, name="Router WiFi 6", price=179.0, stock=70, category="network", description="WiFi 6 tri-band router"),
    15: Product(id=15, name="NAS 4-bay", price=549.0, stock=15, category="storage", description="4-bay NAS with RAID"),
    16: Product(id=16, name="Printer Laser", price=229.0, stock=50, category="printer", description="Duplex laser printer"),
    17: Product(id=17, name="Smartwatch", price=249.0, stock=90, category="wearable", description="Fitness smartwatch"),
    18: Product(id=18, name="Earbuds Pro", price=159.0, stock=180, category="audio", description="ANC true wireless earbuds"),
    19: Product(id=19, name="Projector 1080p", price=399.0, stock=22, category="display", description="Portable 1080p projector"),
    20: Product(id=20, name="Action Cam", price=299.0, stock=65, category="camera", description="4K action camera"),
}

@app.get("/products", response_model=List[Product])
def list_products(limit: int | None = None, category: str | None = None):
    items = list(DB_PRODUCTS.values())
    if category:
        items = [p for p in items if p.category == category]
    if limit:
        items = items[:limit]
    return items

@app.get("/products/{pid}", response_model=Product)
def get_product(pid: int):
    p = DB_PRODUCTS.get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    return p

@app.get("/products/{pid}/recommendations", response_model=List[Product])
def get_recommendations(pid: int, limit: int = 3):
    if pid not in DB_PRODUCTS:
        raise HTTPException(404, "Not found")
    category = DB_PRODUCTS[pid].category
    items = [p for p in DB_PRODUCTS.values() if p.id != pid and p.category == category]
    if len(items) < limit:
        others = [p for p in DB_PRODUCTS.values() if p.id != pid and p not in items]
        items = (items + others)[:limit]
    return items[:limit]

@app.patch("/products/{pid}", response_model=Product)
def update_product(pid: int, stock: int | None = None, price: float | None = None):
    p = DB_PRODUCTS.get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    if stock is not None:
        p.stock = stock
        try:
            r.publish("events", json.dumps({"type": "stock_update", "id": pid, "stock": stock}))
        except Exception as e:
            print("Redis publish stock_update error:", e, flush=True)
    if price is not None:
        p.price = price
        try:
            r.publish("events", json.dumps({"type": "price_update", "id": pid, "price": price}))
        except Exception as e:
            print("Redis publish price_update error:", e, flush=True)
    return p

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)