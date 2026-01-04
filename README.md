# Architettura ibrida REST + GraphQL + WebSocket + MCP (demo tesi)

Questa demo mostra come integrare i quattro paradigmi descritti nel Capitolo 1:
- **REST** per CRUD e stato autorevole.
- **GraphQL** per viste client-driven e riduzione di over/under-fetching.
- **WebSocket** per notifiche real-time.
- **MCP** per orchestrare un agente (LLM host) che legge dati freschi ed esegue azioni tramite tool dichiarativi.

## Servizi inclusi
- `redis`: pub/sub per gli eventi.
- `api-rest`: FastAPI, stato in-memory (prodotti), pubblica eventi `stock_update` e `price_update`.
- `gateway-graphql`: Apollo Server, compone i dati REST e calcola `lowStock`.
- `ws-events`: Node + ws, inoltra su WebSocket tutto ciò che arriva dal canale Redis `events`.
- `mcp-server-catalog`: server MCP (JSON-RPC stdio) con tool:
  - `catalog.searchLowStock(threshold)`
  - `catalog.applyDiscount(product_id, percent, threshold)` con guard-rail sullo stock.
- `mcp-server-orders`: server MCP (mock) con tool:
  - `orders.notifyPending(product_id)` → pubblica `notify_pending` su Redis/WS.
- `mcp-host`: host MCP (mock LLM) che orchestra i tool sopra (one-shot: esegue e termina).

> Postgres **non è usato** in questa demo: il DB è in-memory. Redis è invece necessario.

## Prerequisiti
- Docker e Docker Compose
- (Opzionale) Node.js per usare `wscat` (`npm install -g wscat`)

## Avvio rapido
```bash
docker compose down -v
docker compose build
docker compose up -d
```

## Test passo-passo

### 1) WebSocket
```bash
wscat -c ws://localhost:7070/ws
```

### 2) REST
```bash
curl.exe http://localhost:8080/products
```

### 3) GraphQL
Vai su `http://localhost:4000/graphql` e lancia:
```graphql
query {
  product(id: 1) { id name price stock lowStock }
  products { id name price stock lowStock }
}
```

### 4) MCP (azione dell’agente, one-shot)
```bash
cd mcp-host
python main.py
```
Logica aggiornata:
- Sconta **tutti** i prodotti sotto soglia (`stock <= 15`) del 10%, solo se non già scontati.
- Se un prodotto non è più low-stock, ripristina il prezzo base.
- Pubblica `price_update`; `notify_pending` resta mock.

### 5) Verifica effetti
- **WebSocket**: vedi `price_update` e `notify_pending`.
- **REST**: `curl.exe http://localhost:8080/products/1`
- **GraphQL**: stessa query di prima → `price` aggiornato e `lowStock` ricalcolato.

### 6) Trigger manuale di eventi / aggiornare stock o prezzo
```powershell
# Esempio: stock=5 e price=1200 sul prodotto 1
$curl = "$env:SystemRoot\System32\curl.exe"
& $curl -s -X PATCH "http://localhost:8080/products/1?stock=5&price=1200"

# Solo stock
& $curl -s -X PATCH "http://localhost:8080/products/1?stock=8"

# Verifica
& $curl -s "http://localhost:8080/products/1"
```

## Architettura logica
- **REST (api-rest)**: stato autorevole (in-memory). Pubblica eventi su Redis.
- **GraphQL (gateway-graphql)**: compone le risorse REST, aggiunge `lowStock`.
- **WebSocket (ws-events)**: sottoscritto a Redis `events`, inoltra ai client.
- **MCP**: orchestration: i server MCP espongono tool; l’host MCP coordina la sequenza (es. low-stock → sconto → notifica). L’host è one-shot: puoi lanciarlo on-demand con `docker compose run --rm mcp-host`.

## Variabili d’ambiente principali
- `REDIS_URL`: default `redis://redis:6379/0` (nei container); `redis://localhost:6379/0` fuori da Docker.
- `REST_BASE_URL`: `http://api-rest:8080` (nei container); `http://localhost:8080` fuori.

## Benchmark REST vs GraphQL (ibrido)
- Query: `query/query_1.json` (semplice) e `query/query_2.json` (composita).
- Script: `misurazioni/run-bench.ps1`
- Output grezzi: `misurazioni/rest_simple.txt`, `gql_simple.txt`, `rest_complex.txt`, `gql_complex.txt`.

Esecuzione:
```powershell
cd progetto-tesi
powershell -ExecutionPolicy Bypass -File misurazioni/run-bench.ps1
```
Risultati esempio (locale):
- **Caso semplice (1 risorsa)**  
  - REST: mean ~3,9 ms, p95 ~4,4 ms; 114 B  
  - GraphQL: mean ~7,7 ms, p95 ~8,6 ms; 92 B  
  → REST vince sulle call atomiche.
- **Caso complesso (4 call REST vs 1 GQL)**  
  - REST: mean ~23,0 ms, p95 ~38,0 ms; 1370 B  
  - GraphQL: mean ~13,8 ms, p95 ~19,6 ms; 1037 B  
  → GraphQL vince su viste composte: meno round-trip, latenza migliore, meno byte se selezioni i campi.

Conclusione: usa REST per operazioni semplici; GraphQL per viste composte/multiple risorse.

## Latenza WebSocket (publish→receive) vs polling REST
- Script WS: `misurazioni/ws-latency.js`  
  Esecuzione:
  ```powershell
  $env:RUNS="20"; $env:WS_URL="ws://localhost:7070/ws"; $env:REST_BASE="http://localhost:8080"
  node misurazioni/ws-latency.js
  ```
  Tipico: mean ~3–5 ms, p95 ~3–7 ms, eventi persi: 0.
- Polling REST: `misurazioni/polling-rest.ps1` (interval=50 ms)  
  Tipico: mean ~41–47 ms, p95 ~39–69 ms con outlier warm-up.
  → WS molto più rapido; polling più frequente riduce latenza ma aumenta carico.

## MCP – freschezza e azione (log tempi, sconto e reset)
Esecuzione:
```powershell
cd mcp-host
$env:REST_BASE_URL="http://localhost:8080"
python main.py
```
Esempio run (storico):
- `searchLowStock`: ~12–14 ms (3 item)
- `applyDiscount`: ~12–16 ms su prodotti low-stock (salta se già scontati)
- `notifyPending`: ~0 ms
- Totale pipeline: ~25–30 ms
- Stato finale coerente: REST/GraphQL riflettono prezzo e lowStock aggiornati; evento WS `price_update` emesso.
- Se un prodotto non è più low-stock, il prezzo viene riportato al base price.

## Estensioni possibili
- Persistenza (Postgres con SQLAlchemy/psycopg in `api-rest`).
- Autenticazione JWT e rate limiting su REST/GraphQL/WS.
- Nuovi tool MCP (es. `orders.updateStatus`) e audit logging strutturato.

## Security Features (New)

### JWT Authentication
La demo supporta autenticazione JWT opzionale per REST, GraphQL e WebSocket. Di default l'autenticazione è **disabilitata**.

#### Abilitare l'autenticazione
Imposta la variabile d'ambiente `JWT_SECRET`:
```bash
export JWT_SECRET="your-secret-key-here"
docker compose up -d
```

#### Generare un token JWT
```python
import jwt
import datetime

payload = {
    "sub": "user123",
    "role": "admin",  # or "viewer"
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
}
token = jwt.encode(payload, "your-secret-key-here", algorithm="HS256")
print(token)
```

#### Usare il token
**REST:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/products
```

**GraphQL:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ products { id name } }"}' \
  http://localhost:4000/graphql
```

**WebSocket:**
```bash
wscat -c "ws://localhost:7070/ws?token=YOUR_TOKEN"
```

#### Ruoli
- **admin**: accesso completo (read + write)
- **viewer**: solo lettura (le PATCH richiedono admin)

### Rate Limiting
Rate limiting configurabile per proteggere da abusi.

**Configurazione (env vars):**
- `RATE_LIMIT`: limite per REST (default: `100/minute`)
- `RATE_LIMIT_PER_MIN`: limite per GraphQL (default: `100`)
- `WS_MESSAGE_RATE_LIMIT`: messaggi WS per secondo per connessione (default: `10`)

**Esempio:**
```bash
export RATE_LIMIT="50/minute"
export RATE_LIMIT_PER_MIN="50"
docker compose up -d
```

Se si supera il limite:
- REST/GraphQL: HTTP 429 "Rate limit exceeded"
- WebSocket: messaggio di errore nella connessione

### GraphQL Security
**Depth Limit:**
Previene query troppo profonde (protezione contro query nesting attack).
```bash
export GRAPHQL_DEPTH_LIMIT="5"  # default: 10
```

**Introspection:**
Disabilitare introspection in produzione:
```bash
export INTROSPECTION_ENABLED="false"  # default: true
```

### WebSocket Security
- **Origin check**: configura origini consentite con `WS_ALLOWED_ORIGINS` (default: `*`)
- **Max payload**: `WS_MAX_PAYLOAD` (default: 1MB)
- **Message rate limiting**: limita messaggi in ingresso per connessione
- **JWT validation**: opzionale via query param `?token=...`

**Esempio:**
```bash
export WS_ALLOWED_ORIGINS="http://localhost:3000,https://myapp.com"
export WS_MAX_PAYLOAD="524288"  # 512KB
docker compose up -d
```

## Observability (New)

### Structured Logging
Tutti i servizi usano logging strutturato JSON con request ID e trace ID propagation.

**Esempio log (api-rest):**
```json
{
  "asctime": "2024-01-04T10:30:15.123Z",
  "name": "api-rest",
  "levelname": "INFO",
  "message": "Request completed",
  "request_id": "1234567890",
  "trace_id": "1234567890",
  "method": "GET",
  "path": "/products",
  "status": 200,
  "duration_ms": 12.34
}
```

**Propagazione trace ID:**
I client possono inviare header `X-Request-ID` e `X-Trace-ID` per tracciare richieste cross-service.

### Prometheus Metrics
Metriche esposte per monitoraggio e alerting.

**Endpoints:**
- REST API: `http://localhost:8080/metrics`
- GraphQL: `http://localhost:9090/metrics`

**Metriche disponibili:**
- `api_rest_requests_total`: contatore richieste REST (labels: method, endpoint, status)
- `api_rest_request_duration_seconds`: istogramma latenza REST (labels: method, endpoint)
- `api_rest_errors_total`: contatore errori REST (labels: endpoint)
- `graphql_requests_total`: contatore richieste GraphQL (labels: operation, status)
- `graphql_request_duration_seconds`: istogramma latenza GraphQL (labels: operation)
- `graphql_errors_total`: contatore errori GraphQL (labels: operation)
- `ws_connections_total`: contatore connessioni WebSocket
- `ws_messages_total`: contatore messaggi WS (labels: type)
- `ws_errors_total`: contatore errori WS (labels: type)

**Esempio query Prometheus:**
```promql
# P95 latency REST
histogram_quantile(0.95, rate(api_rest_request_duration_seconds_bucket[5m]))

# Error rate GraphQL
rate(graphql_errors_total[5m])

# WS message throughput
rate(ws_messages_total[1m])
```

### Health Checks
- REST API: `http://localhost:8080/health`
- Docker healthchecks configurati per orchestrazione robusta

## Optional PostgreSQL Persistence

Di default la demo usa database in-memory. Per persistenza Postgres:

### Setup
```bash
# Avvia con Postgres
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d

# Solo servizi core (senza mcp-host)
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d redis postgres api-rest gateway-graphql ws-events
```

### Schema
Lo schema SQL è in `postgres/init.sql` e viene eseguito automaticamente all'avvio.

**Tabella `products`:**
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    stock INTEGER NOT NULL,
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Configurazione
Il file `docker-compose.postgres.yml` imposta:
- `DATABASE_URL`: connection string per Postgres
- `USE_POSTGRES=true`: flag per abilitare Postgres in api-rest

**Connessione locale (fuori Docker):**
```bash
export DATABASE_URL="postgresql://catalog_user:catalog_pass@localhost:5432/catalog"
export USE_POSTGRES="true"
python api-rest/main.py
```

## Utility Scripts (New)

### Reset Prices and Stock
Ripristina tutti i prodotti ai valori base.
```bash
python scripts/reset-prices.py

# O con custom REST_BASE_URL
REST_BASE_URL=http://localhost:8080 python scripts/reset-prices.py
```

### Run MCP Host Once
Esegue il MCP host in modalità one-shot (senza Docker).
```bash
./scripts/run-mcp-once.sh

# O con env vars custom
REST_BASE_URL=http://localhost:8080 REDIS_URL=redis://localhost:6379/0 ./scripts/run-mcp-once.sh
```

### WebSocket Events Consumer
Semplice consumer per visualizzare eventi WebSocket in tempo reale.
```bash
# Senza autenticazione
node scripts/ws-events-consumer.js

# Con JWT token
JWT_TOKEN="your-token" node scripts/ws-events-consumer.js

# Custom WS URL
node scripts/ws-events-consumer.js ws://localhost:7070/ws
```

Alternative: usa `wscat` (npm install -g wscat)
```bash
wscat -c ws://localhost:7070/ws
```

### WebSocket Latency Report
Calcola mean e P95 latency da output di `ws-latency.js`.
```bash
# Redirect output to report
node misurazioni/ws-latency.js > /tmp/ws-output.txt
python scripts/ws-latency-report.py < /tmp/ws-output.txt

# O piped
node misurazioni/ws-latency.js | python scripts/ws-latency-report.py
```

Output:
```
WebSocket Latency Statistics
=============================
Total measurements: 20
Mean latency:       4.23 ms
P95 latency:        6.15 ms
Min latency:        2.10 ms
Max latency:        8.45 ms
Std deviation:      1.82 ms
```

## Environment Variables Reference

### Global
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)
- `REST_BASE_URL`: REST API base URL (default: `http://localhost:8080`)

### Security (api-rest, gateway-graphql, ws-events)
- `JWT_SECRET`: JWT signing secret (no default; if unset, auth is disabled)
- `JWT_ALGORITHM`: JWT algorithm (default: `HS256`)
- `RATE_LIMIT`: REST rate limit (default: `100/minute`)
- `RATE_LIMIT_PER_MIN`: GraphQL rate limit (default: `100`)
- `WS_MESSAGE_RATE_LIMIT`: WebSocket messages per second (default: `10`)
- `WS_ALLOWED_ORIGINS`: Comma-separated allowed origins (default: `*`)
- `WS_MAX_PAYLOAD`: Max WebSocket payload in bytes (default: `1048576` = 1MB)

### GraphQL
- `LOW_STOCK_THRESHOLD`: Threshold for lowStock field (default: `10`)
- `GRAPHQL_DEPTH_LIMIT`: Max query depth (default: `10`)
- `INTROSPECTION_ENABLED`: Enable introspection (default: `true`)

### PostgreSQL (optional)
- `DATABASE_URL`: PostgreSQL connection string
- `USE_POSTGRES`: Enable Postgres (default: `false` / in-memory)

## Troubleshooting
- Nessun evento in WS: verifica `api-rest` pubblica su Redis e `ws-events` è up.
- MCP (host) esce subito: è one-shot; lancialo con `docker compose run --rm mcp-host` quando `api-rest` è pronto.
- MCP non risponde: controlla `REST_BASE_URL` e `REDIS_URL`; dipendenze `requests`/`redis`.
- Guard-rail: `catalog.applyDiscount` rifiuta se `stock > threshold`. L’host salta lo sconto se già applicato e ripristina il prezzo base se non è più low-stock.