import WebSocket, { WebSocketServer } from 'ws';
import { createClient } from 'redis';

const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379/0";
const wss = new WebSocketServer({ port: 7070 });

(async () => {
  const sub = createClient({ url: REDIS_URL });
  await sub.connect();
  await sub.subscribe('events', (message) => {
    // broadcast to all clients
    wss.clients.forEach(c => {
      if (c.readyState === WebSocket.OPEN) c.send(message);
    });
  });
  console.log("WS server listening on 7070, subscribed to 'events'");
})();

wss.on('connection', (ws) => {
  ws.send(JSON.stringify({ type: "welcome", ts: Date.now() }));
});