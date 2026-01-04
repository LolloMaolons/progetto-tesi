#!/usr/bin/env python3
"""
Reset all product prices and stock to base values.
Usage: python scripts/reset-prices.py
"""
import os
import sys
import requests

REST_BASE = os.getenv("REST_BASE_URL", "http://localhost:8080")

BASE_DATA = {
    1: {"price": 1499.0, "stock": 10},
    2: {"price": 29.0, "stock": 200},
    3: {"price": 79.0, "stock": 120},
    4: {"price": 329.0, "stock": 45},
    5: {"price": 119.0, "stock": 80},
    6: {"price": 149.0, "stock": 60},
    7: {"price": 199.0, "stock": 35},
    8: {"price": 129.0, "stock": 150},
    9: {"price": 799.0, "stock": 8},
    10: {"price": 999.0, "stock": 25},
    11: {"price": 899.0, "stock": 55},
    12: {"price": 649.0, "stock": 40},
    13: {"price": 59.0, "stock": 300},
    14: {"price": 179.0, "stock": 70},
    15: {"price": 549.0, "stock": 15},
    16: {"price": 229.0, "stock": 50},
    17: {"price": 249.0, "stock": 90},
    18: {"price": 159.0, "stock": 180},
    19: {"price": 399.0, "stock": 22},
    20: {"price": 299.0, "stock": 65},
}

def reset_all():
    """Reset all products to base values"""
    print(f"Resetting all products to base values...")
    print(f"Using REST API: {REST_BASE}")
    
    for pid, data in BASE_DATA.items():
        try:
            resp = requests.patch(
                f"{REST_BASE}/products/{pid}",
                params={"price": data["price"], "stock": data["stock"]}
            )
            resp.raise_for_status()
            print(f"✓ Product {pid}: price={data['price']}, stock={data['stock']}")
        except Exception as e:
            print(f"✗ Product {pid}: Error - {e}", file=sys.stderr)
    
    print("\nReset complete!")

if __name__ == "__main__":
    reset_all()
