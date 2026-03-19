/**
 * @file ws-client.js
 * @module extension/lib/ws-client
 *
 * WebSocket client with exponential backoff reconnection.
 */

const DEFAULT_URL = 'ws://127.0.0.1:8002/ws';
const MAX_BACKOFF_MS = 30_000;

export class WsClient {
  constructor(opts) {
    this.url = opts.url || DEFAULT_URL;
    this.onMessage = opts.onMessage;
    this.onConnectionChange = opts.onConnectionChange || (() => {});
    this._ws = null;
    this._connected = false;
    this._backoff = 1000;
    this._seq = 0;
    this._shouldReconnect = true;
  }

  connect() {
    this._shouldReconnect = true;
    this._tryConnect();
  }

  _tryConnect() {
    if (this._ws) return;
    try {
      this._ws = new WebSocket(this.url);
    } catch {
      this._scheduleReconnect();
      return;
    }

    this._ws.onopen = () => {
      this._connected = true;
      this._backoff = 1000;
      this.onConnectionChange(true);
    };

    this._ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.onMessage(msg);
      } catch { /* ignore malformed */ }
    };

    this._ws.onclose = () => {
      this._connected = false;
      this._ws = null;
      this.onConnectionChange(false);
      if (this._shouldReconnect) {
        this._scheduleReconnect();
      }
    };

    this._ws.onerror = () => {};
  }

  _scheduleReconnect() {
    const jitter = Math.random() * 500;
    setTimeout(() => this._tryConnect(), this._backoff + jitter);
    this._backoff = Math.min(this._backoff * 2, MAX_BACKOFF_MS);
  }

  send(type, payload = {}) {
    if (!this._connected || !this._ws) return false;
    this._seq++;
    const msg = {
      type,
      agent: 'user',
      payload,
      ts: new Date().toISOString(),
      seq: this._seq,
    };
    this._ws.send(JSON.stringify(msg));
    return true;
  }

  sendCommand(text, routing = null) {
    return this.send('command', {
      text,
      ...(routing ? { routing } : {}),
    });
  }

  sendPageContext(payload, routing = null) {
    return this.send('page_context', {
      ...payload,
      ...(routing ? { routing } : {}),
    });
  }

  sendZoneResponse(requestSeq, decision) { return this.send('zone_response', { request_seq: requestSeq, decision }); }

  disconnect() {
    this._shouldReconnect = false;
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }

  get connected() { return this._connected; }
}
