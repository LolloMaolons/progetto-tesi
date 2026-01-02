import subprocess, json, os, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SERVERS = {
    "catalog": ["python", str((BASE_DIR.parent / "mcp-server-catalog" / "server.py").resolve())],
    "orders":  ["python", str((BASE_DIR.parent / "mcp-server-orders" / "server.py").resolve())],
}

REST_BASE_URL = os.getenv("REST_BASE_URL", "http://localhost:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def call_server(proc, payload):
    proc.stdin.write((json.dumps(payload)+"\n").encode())
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("Server process returned no data")
    return json.loads(line)

def main():
    procs = {}
    env = os.environ.copy()
    env["REST_BASE_URL"] = REST_BASE_URL
    env["REDIS_URL"] = REDIS_URL
    for name, cmd in SERVERS.items():
        procs[name] = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)

    # init + list tools
    for name, p in procs.items():
        print(f"[{name}] init:", call_server(p, {"jsonrpc":"2.0","id":1,"method":"initialize"}))
        print(f"[{name}] tools:", call_server(p, {"jsonrpc":"2.0","id":2,"method":"listTools"}))

    # low stock
    low = call_server(procs["catalog"], {
        "jsonrpc":"2.0","id":3,"method":"callTool",
        "params":{"name":"catalog.searchLowStock","arguments":{"threshold":15}}
    })
    print("low stock:", low)

    items = low.get("result", {}).get("items", []) if isinstance(low, dict) else []
    if not items:
        print("Nessun prodotto low-stock: salto sconto e notify.")
        return

    pid = items[0]["id"]
    # apply discount 10% su primo low-stock
    print("discount:", call_server(procs["catalog"], {
        "jsonrpc":"2.0","id":4,"method":"callTool",
        "params":{"name":"catalog.applyDiscount","arguments":{"product_id":pid,"percent":10,"threshold":15}}
    }))

    # notify pending orders per quel prodotto
    print("notify:", call_server(procs["orders"], {
        "jsonrpc":"2.0","id":5,"method":"callTool",
        "params":{"name":"orders.notifyPending","arguments":{"product_id":pid}}
    }))

if __name__ == "__main__":
    main()