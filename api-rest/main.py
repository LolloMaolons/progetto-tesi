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

DB_PRODUCTS = {
    1: Product(id=1, name="Laptop Pro", price=1499.0, stock=10),
    2: Product(id=2, name="Mouse", price=29.0, stock=200),
}

@app.get("/products", response_model=List[Product])
def list_products():
    return list(DB_PRODUCTS.values())

@app.get("/products/{pid}", response_model=Product)
def get_product(pid: int):
    p = DB_PRODUCTS.get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    return p

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