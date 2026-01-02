import sys, json, uuid, os, requests

REST_BASE = os.getenv("REST_BASE_URL", "http://api-rest:8080")

def respond(id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": id}
    if error:
        msg["error"] = {"code": -32000, "message": error}
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def handle(req):
    method = req.get("method")
    id_ = req.get("id")
    if method == "initialize":
        return respond(id_, {"capabilities": {"tools": True}})
    if method == "listTools":
        return respond(id_, {
            "tools": [
                {"name": "catalog.searchLowStock", "description": "List products with stock <= threshold", "input_schema": {"threshold": "integer"}}
            ]
        })
    if method == "callTool":
        params = req.get("params", {})
        tool = params.get("name")
        args = params.get("arguments", {})
        if tool == "catalog.searchLowStock":
            threshold = int(args.get("threshold", 5))
            r = requests.get(f"{REST_BASE}/products")
            items = [p for p in r.json() if p["stock"] <= threshold]
            return respond(id_, {"items": items})
        else:
            return respond(id_, error="unknown tool")
    return respond(id_, error="unknown method")

def main():
    for line in sys.stdin:
        line=line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            handle(req)
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc":"2.0","error":{"code":-32000,"message":str(e)}})+"\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()