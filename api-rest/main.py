from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="API REST - Catalog/Orders/Users")

class Product(BaseModel):
    id: int
    name: str
    price: float
    stock: int

# In-memory stub (poi Postgres)
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
def update_stock(pid: int, stock: int):
    p = DB_PRODUCTS.get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    p.stock = stock
    # TODO: publish event to Redis
    return p

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)