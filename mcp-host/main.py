import subprocess, json, sys, os

SERVERS = {
    "catalog": ["python", "server.py"],
}

def call_server(proc, payload):
    proc.stdin.write((json.dumps(payload)+"\n").encode())
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)

def main():
    procs = {}
    for name, cmd in SERVERS.items():
        procs[name] = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    # initialize + list tools
    for name, p in procs.items():
        init = call_server(p, {"jsonrpc":"2.0","id":1,"method":"initialize"})
        tools = call_server(p, {"jsonrpc":"2.0","id":2,"method":"listTools"})
        print(f"[{name}] tools: {tools}")

    # demo: low stock
    res = call_server(procs["catalog"], {
        "jsonrpc":"2.0","id":3,"method":"callTool",
        "params":{"name":"catalog.searchLowStock","arguments":{"threshold":5}}
    })
    print("Low stock:", res)

if __name__ == "__main__":
    main()