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

## Troubleshooting
- Nessun evento in WS: verifica `api-rest` pubblica su Redis e `ws-events` è up.
- MCP (host) esce subito: è one-shot; lancialo con `docker compose run --rm mcp-host` quando `api-rest` è pronto.
- MCP non risponde: controlla `REST_BASE_URL` e `REDIS_URL`; dipendenze `requests`/`redis`.
- Guard-rail: `catalog.applyDiscount` rifiuta se `stock > threshold`. L’host salta lo sconto se già applicato e ripristina il prezzo base se non è più low-stock.