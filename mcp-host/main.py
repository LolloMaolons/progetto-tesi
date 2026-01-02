import subprocess, json, os, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SERVERS = {
    # Path assoluto al server catalog
    "catalog": ["python", str((BASE_DIR.parent / "mcp-server-catalog" / "server.py").resolve())]
}

REST_BASE_URL = os.getenv("REST_BASE_URL", "http://localhost:8080")

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
    for name, cmd in SERVERS.items():
        procs[name] = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    init = call_server(procs["catalog"], {"jsonrpc":"2.0","id":1,"method":"initialize"})
    tools = call_server(procs["catalog"], {"jsonrpc":"2.0","id":2,"method":"listTools"})
    print("init:", init)
    print("tools:", tools)
    res = call_server(procs["catalog"], {
    "jsonrpc":"2.0","id":3,"method":"callTool",
    "params":{"name":"catalog.searchLowStock","arguments":{"threshold":15}}
    })
    print("low stock:", res)

if __name__ == "__main__":
    main()