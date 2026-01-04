#!/usr/bin/env python3
"""
Calculate mean and p95 latency from ws-latency.js output.
Usage: python scripts/ws-latency-report.py < ws-latency-output.txt
Or: node misurazioni/ws-latency.js | python scripts/ws-latency-report.py
"""
import sys
import re
import statistics

def parse_latencies(lines):
    """Parse latency values from ws-latency.js output"""
    latencies = []
    for line in lines:
        # Look for lines like "Latency 1: 3.45 ms"
        match = re.search(r'Latency \d+:\s+([\d.]+)\s*ms', line)
        if match:
            latencies.append(float(match.group(1)))
    return latencies

def calculate_stats(latencies):
    """Calculate mean and p95 from latency values"""
    if not latencies:
        return None, None
    
    mean = statistics.mean(latencies)
    p95_idx = int(len(latencies) * 0.95)
    sorted_latencies = sorted(latencies)
    p95 = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
    
    return mean, p95

def main():
    """Read from stdin and calculate statistics"""
    lines = sys.stdin.readlines()
    latencies = parse_latencies(lines)
    
    if not latencies:
        print("No latency data found in input", file=sys.stderr)
        sys.exit(1)
    
    mean, p95 = calculate_stats(latencies)
    
    print(f"\nWebSocket Latency Statistics")
    print(f"=============================")
    print(f"Total measurements: {len(latencies)}")
    print(f"Mean latency:       {mean:.2f} ms")
    print(f"P95 latency:        {p95:.2f} ms")
    print(f"Min latency:        {min(latencies):.2f} ms")
    print(f"Max latency:        {max(latencies):.2f} ms")
    
    if len(latencies) > 1:
        stdev = statistics.stdev(latencies)
        print(f"Std deviation:      {stdev:.2f} ms")

if __name__ == "__main__":
    main()
