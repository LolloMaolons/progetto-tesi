# Testing Guide for Security and Observability Features

This guide describes how to test all the new security and observability features added to the demo.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for testing scripts)
- Node.js (for WebSocket consumer)
- `curl` and `jq` (optional, for manual testing)

## Quick Start

```bash
# Build and start all services
docker compose down -v
docker compose build
docker compose up -d redis api-rest gateway-graphql ws-events

# Wait for services to be healthy
docker compose ps
```

## 1. Testing REST API Security

### Without Authentication (Default)
```bash
# All endpoints work without auth when JWT_SECRET is not set
curl http://localhost:8080/products | jq .
curl http://localhost:8080/products/1 | jq .
curl -X PATCH "http://localhost:8080/products/1?stock=20" | jq .
```

### With JWT Authentication
```bash
# Start services with JWT_SECRET
export JWT_SECRET="my-secret-key"
docker compose up -d api-rest

# Generate a token (using Python)
python3 <<EOF
import jwt
import datetime
payload = {
    "sub": "admin-user",
    "role": "admin",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
}
token = jwt.encode(payload, "my-secret-key", algorithm="HS256")
print(f"Token: {token}")
EOF

# Use the token
export TOKEN="<token-from-above>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/products | jq .

# Test admin vs viewer roles
# Admin token can PATCH
curl -H "Authorization: Bearer $TOKEN" \
  -X PATCH "http://localhost:8080/products/1?stock=25" | jq .

# Viewer token (generate with role: "viewer") cannot PATCH
# Should return 403 Forbidden
```

## 2. Testing Rate Limiting

### REST API Rate Limiting
```bash
# Set a low rate limit for testing
export RATE_LIMIT="5/minute"
docker compose up -d api-rest

# Send multiple requests rapidly
for i in {1..10}; do
  curl -w "\nStatus: %{http_code}\n" http://localhost:8080/products/1
  sleep 1
done

# After 5 requests, should see 429 Too Many Requests
```

### GraphQL Rate Limiting
```bash
export RATE_LIMIT_PER_MIN="5"
docker compose up -d gateway-graphql

# Send multiple GraphQL queries
for i in {1..10}; do
  curl -X POST http://localhost:4000/graphql \
    -H "Content-Type: application/json" \
    -d '{"query":"{ products { id name } }"}'
  sleep 1
done
```

## 3. Testing GraphQL Security Features

### Depth Limiting
```bash
# Set a low depth limit
export GRAPHQL_DEPTH_LIMIT="2"
docker compose up -d gateway-graphql

# This deep query should be rejected
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ products { id name recommendations { id name recommendations { id } } } }"
  }'
```

### Introspection Toggle
```bash
# Disable introspection
export INTROSPECTION_ENABLED="false"
docker compose up -d gateway-graphql

# Introspection query should fail
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { types { name } } }"}'
```

## 4. Testing WebSocket Security

### Origin Check
```bash
export WS_ALLOWED_ORIGINS="http://localhost:3000,http://myapp.com"
docker compose up -d ws-events

# Connect with wscat (will be rejected if origin doesn't match)
wscat -c ws://localhost:7070/ws -H "Origin: http://badorigin.com"

# Connect with allowed origin (should work)
wscat -c ws://localhost:7070/ws -H "Origin: http://localhost:3000"
```

### JWT Authentication for WebSocket
```bash
# Start with JWT_SECRET
export JWT_SECRET="my-secret-key"
docker compose up -d ws-events

# Generate token and connect
export TOKEN="<your-jwt-token>"
wscat -c "ws://localhost:7070/ws?token=$TOKEN"

# Or use the consumer script
JWT_TOKEN="$TOKEN" node scripts/ws-events-consumer.js
```

### Message Rate Limiting
```bash
# Set low message rate limit
export WS_MESSAGE_RATE_LIMIT="2"
docker compose up -d ws-events

# Connect and send multiple messages rapidly
# After 2 messages per second, will receive rate limit error
```

## 5. Testing Observability Features

### Structured Logging
```bash
# View JSON logs from any service
docker compose logs api-rest --tail=20

# Logs should be in JSON format with request_id and trace_id
# Example:
# {"asctime": "2024-01-04...", "request_id": "123", "trace_id": "123", ...}
```

### Request ID Propagation
```bash
# Send request with custom trace ID
curl -H "X-Trace-ID: my-trace-123" http://localhost:8080/products/1

# Check logs - should show trace_id: my-trace-123
docker compose logs api-rest --tail=5
```

### Prometheus Metrics
```bash
# REST API metrics
curl http://localhost:8080/metrics

# GraphQL metrics
curl http://localhost:9090/metrics

# Look for custom metrics:
# - api_rest_requests_total
# - api_rest_request_duration_seconds
# - graphql_requests_total
# - graphql_request_duration_seconds
# - ws_connections_total
# - ws_messages_total
```

### Health Checks
```bash
# REST API health
curl http://localhost:8080/health | jq .

# Check Docker health status
docker compose ps
# Should show "healthy" status for api-rest and redis
```

## 6. Testing PostgreSQL Persistence (Optional)

```bash
# Start with Postgres
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d

# Check Postgres is running
docker compose -f docker-compose.yml -f docker-compose.postgres.yml ps

# Verify data persists
curl -X PATCH "http://localhost:8080/products/1?stock=99&price=1999"
docker compose -f docker-compose.yml -f docker-compose.postgres.yml restart api-rest
curl http://localhost:8080/products/1 | jq .
# Stock should still be 99, price 1999
```

## 7. Testing Utility Scripts

### Reset Prices Script
```bash
# Change some prices
curl -X PATCH "http://localhost:8080/products/1?price=9999"
curl -X PATCH "http://localhost:8080/products/2?stock=1"

# Reset to base values
python scripts/reset-prices.py

# Verify reset
curl http://localhost:8080/products/1 | jq .
# Should be back to original price and stock
```

### MCP Host One-Shot
```bash
# Set some products to low stock
curl -X PATCH "http://localhost:8080/products/1?stock=5"
curl -X PATCH "http://localhost:8080/products/9?stock=3"

# Run MCP host
./scripts/run-mcp-once.sh

# Check prices were discounted
curl http://localhost:8080/products/1 | jq .price
# Should be 10% less than base price
```

### WebSocket Events Consumer
```bash
# Terminal 1: Start consumer
node scripts/ws-events-consumer.js

# Terminal 2: Trigger events
curl -X PATCH "http://localhost:8080/products/1?stock=10"

# Terminal 1 should show the stock_update event
```

### WebSocket Latency Report
```bash
# Run latency test and analyze
node misurazioni/ws-latency.js | tee /tmp/ws-output.txt | python scripts/ws-latency-report.py

# Or save and analyze separately
node misurazioni/ws-latency.js > /tmp/ws-output.txt
python scripts/ws-latency-report.py < /tmp/ws-output.txt
```

### Security Test Suite
```bash
# Run automated tests
python scripts/test-security.py

# Tests verify:
# - API works without auth (default)
# - Metrics endpoint accessible
# - Health checks pass
```

## 8. Load Testing (Optional)

### Apache Bench (ab)
```bash
# Install ab
sudo apt-get install apache2-utils

# Test REST API
ab -n 1000 -c 10 http://localhost:8080/products

# Test with rate limiting
export RATE_LIMIT="50/minute"
docker compose up -d api-rest
ab -n 100 -c 10 http://localhost:8080/products
# Should see rate limit errors after ~50 requests
```

### Artillery (Node.js load testing)
```bash
npm install -g artillery

# Create test config
cat > artillery-test.yml <<EOF
config:
  target: "http://localhost:8080"
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - flow:
      - get:
          url: "/products"
EOF

# Run test
artillery run artillery-test.yml
```

## Expected Results

### Security
- ✅ Without JWT_SECRET: All endpoints accessible
- ✅ With JWT_SECRET: Requires Bearer token
- ✅ Admin role: Full access
- ✅ Viewer role: Read-only access (PATCH returns 403)
- ✅ Rate limiting: Returns 429 after limit exceeded
- ✅ GraphQL depth limit: Rejects deep queries
- ✅ WebSocket: Enforces origin check, JWT, and message rate limits

### Observability
- ✅ All logs in JSON format
- ✅ request_id and trace_id in every log entry
- ✅ Custom trace IDs propagated across services
- ✅ Prometheus metrics exposed and updating
- ✅ Health checks return correct status

### Developer Experience
- ✅ Scripts execute successfully
- ✅ Reset script restores base values
- ✅ MCP host applies discounts correctly
- ✅ WS consumer shows events in real-time
- ✅ Latency report calculates mean and p95

## Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs <service-name>

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Health checks failing
```bash
# Check if curl is available in container
docker compose exec api-rest curl http://localhost:8080/health

# If not, rebuild with updated Dockerfile
```

### Metrics not updating
```bash
# Send some requests first
for i in {1..10}; do curl http://localhost:8080/products; done

# Then check metrics
curl http://localhost:8080/metrics | grep api_rest
```

### JWT tokens not working
```bash
# Verify JWT_SECRET is set
docker compose exec api-rest env | grep JWT_SECRET

# Check token is valid and not expired
python3 -c "import jwt; print(jwt.decode('YOUR_TOKEN', 'YOUR_SECRET', algorithms=['HS256']))"
```
