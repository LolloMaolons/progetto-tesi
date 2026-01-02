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
- `mcp-host`: host MCP (mock LLM) che orchestra i tool sopra.

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
In un terminale:
```bash
wscat -c ws://localhost:7070/ws
```
Dovresti vedere `welcome`.

### 2) REST
In un altro terminale:
```bash
curl.exe http://localhost:8080/products
```
Vedi i prodotti e i prezzi correnti.

### 3) GraphQL
Vai su `http://localhost:4000/graphql` e lancia:
```graphql
query {
  product(id: 1) { id name price stock lowStock }
  products { id name price stock lowStock }
}
```

### 4) MCP (azione dell’agente)
In un altro terminale:
```bash
cd mcp-host
python main.py
```
Cosa fa:
- `catalog.searchLowStock(threshold=15)` → trova i prodotti sotto soglia.
- Se esistono low-stock, `catalog.applyDiscount` applica -10% (con controllo sullo stock) e pubblica `price_update`.
- `orders.notifyPending` pubblica `notify_pending`.

### 5) Verifica effetti
- **WebSocket**: nella sessione `wscat` dovresti vedere `price_update` e `notify_pending`.
- **REST**: `curl.exe http://localhost:8080/products/1` mostra il nuovo prezzo.
- **GraphQL**: la stessa query di prima mostra `price` aggiornato e `lowStock` ricalcolato.

### 6) Trigger manuale di eventi
```bash
curl.exe -X PATCH "http://localhost:8080/products/1?stock=5&price=1200"
```
Vedrai in WS: `stock_update` e `price_update`.

## Architettura logica
- **REST (api-rest)**: stato autorevole (in-memory). Pubblica eventi su Redis.
- **GraphQL (gateway-graphql)**: compone le risorse REST, aggiunge il campo `lowStock`.
- **WebSocket (ws-events)**: sottoscritto a Redis `events`, inoltra ai client.
- **MCP**: agent orchestration. I server MCP espongono tool che accedono/aggiornano i sistemi. L’host MCP coordina la sequenza (es. low-stock → sconto → notifica).

## Variabili d’ambiente principali
- `REDIS_URL`: di default `redis://redis:6379/0` nei container; `redis://localhost:6379/0` se lanci MCP host/server fuori da Docker.
- `REST_BASE_URL`: `http://api-rest:8080` nei container; `http://localhost:8080` se lanci fuori da Docker.

## Estensioni possibili
- Persistere su Postgres (integrare SQLAlchemy/psycopg in `api-rest`).
- Aggiungere autenticazione (JWT) e rate limiting su REST/GraphQL/WS.
- Aggiungere altri tool MCP (es. `orders.updateStatus`) e audit logging strutturato.

## Troubleshooting
- Nessun evento in WS: verifica che `api-rest` pubblichi sul canale `events` e che `ws-events` sia partito (log docker).
- MCP non risponde: assicurati di impostare `REST_BASE_URL` e `REDIS_URL` corretti se lanci fuori da Docker; verifica di avere `requests`/`redis` installati nelle immagini/ambiente.
- Threshold/guard-rail: `catalog.applyDiscount` rifiuta lo sconto se `stock > threshold`. L’host salta lo sconto se non ci sono low-stock.