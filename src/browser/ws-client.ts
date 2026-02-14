/**
 * @file ws-client.ts
 * @module browser/ws-client
 * @layer Layer 14 (transport)
 * @component Minimal RFC 6455 WebSocket Client
 * @version 1.0.0
 *
 * Zero-dependency WebSocket client built on Node.js `net` and `http` modules.
 * Implements just enough of RFC 6455 for Chrome DevTools Protocol:
 *   - Text frames (opcode 0x1) — all CDP uses JSON
 *   - Close frames (opcode 0x8)
 *   - Ping/Pong (opcode 0x9/0xA)
 *   - Client-side masking (required by spec)
 *   - 7-bit, 16-bit, and 64-bit payload lengths
 *
 * No binary frame support (CDP doesn't need it).
 * No extensions (permessage-deflate etc.).
 */

import { createConnection, Socket } from 'net';
import { createHash, randomBytes } from 'crypto';
import { URL } from 'url';
import { EventEmitter } from 'events';

// =============================================================================
// TYPES
// =============================================================================

export interface WSClientOptions {
  /** Connection timeout in ms (default 10000) */
  connectTimeout?: number;
  /** Maximum payload size in bytes (default 16MB) */
  maxPayloadSize?: number;
}

export type WSReadyState = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';

// =============================================================================
// CONSTANTS
// =============================================================================

const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
const OPCODE_TEXT = 0x1;
const OPCODE_CLOSE = 0x8;
const OPCODE_PING = 0x9;
const OPCODE_PONG = 0xa;
const DEFAULT_MAX_PAYLOAD = 16 * 1024 * 1024; // 16MB

// =============================================================================
// MINIMAL WEBSOCKET CLIENT
// =============================================================================

/**
 * Minimal WebSocket client for CDP communication.
 *
 * Usage:
 * ```ts
 * const ws = new WSClient('ws://127.0.0.1:9222/devtools/page/ABC');
 * await ws.connect();
 * ws.on('message', (data) => console.log(data));
 * ws.send(JSON.stringify({ id: 1, method: 'Page.enable' }));
 * await ws.close();
 * ```
 */
export class WSClient extends EventEmitter {
  private socket: Socket | null = null;
  private readyState: WSReadyState = 'CONNECTING';
  private buffer: Buffer = Buffer.alloc(0);
  private url: URL;
  private options: Required<WSClientOptions>;

  constructor(url: string, options?: WSClientOptions) {
    super();
    this.url = new URL(url);
    this.options = {
      connectTimeout: options?.connectTimeout ?? 10000,
      maxPayloadSize: options?.maxPayloadSize ?? DEFAULT_MAX_PAYLOAD,
    };
  }

  /** Current connection state */
  get state(): WSReadyState {
    return this.readyState;
  }

  /**
   * Connect to the WebSocket server.
   * Performs the HTTP upgrade handshake, then switches to frame protocol.
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const port = parseInt(this.url.port || '80', 10);
      const host = this.url.hostname;

      // Generate Sec-WebSocket-Key
      const key = randomBytes(16).toString('base64');
      const expectedAccept = createHash('sha1')
        .update(key + GUID)
        .digest('base64');

      // Connect TCP
      const socket = createConnection({ host, port }, () => {
        // Send HTTP upgrade request
        const path = this.url.pathname + this.url.search;
        const request = [
          `GET ${path} HTTP/1.1`,
          `Host: ${host}:${port}`,
          'Upgrade: websocket',
          'Connection: Upgrade',
          `Sec-WebSocket-Key: ${key}`,
          'Sec-WebSocket-Version: 13',
          '',
          '',
        ].join('\r\n');

        socket.write(request);
      });

      // Connection timeout
      const timeout = setTimeout(() => {
        socket.destroy();
        reject(new Error(`WebSocket connection timed out after ${this.options.connectTimeout}ms`));
      }, this.options.connectTimeout);

      // Track whether we've completed the handshake
      let handshakeComplete = false;
      let handshakeBuffer = '';

      const onData = (chunk: Buffer) => {
        if (!handshakeComplete) {
          // Accumulate handshake response
          handshakeBuffer += chunk.toString('utf8');

          const headerEnd = handshakeBuffer.indexOf('\r\n\r\n');
          if (headerEnd === -1) return; // Need more data

          clearTimeout(timeout);

          // Parse response
          const headers = handshakeBuffer.slice(0, headerEnd);
          const statusLine = headers.split('\r\n')[0];

          if (!statusLine.includes('101')) {
            socket.destroy();
            reject(new Error(`WebSocket upgrade failed: ${statusLine}`));
            return;
          }

          // Verify Sec-WebSocket-Accept
          const acceptMatch = headers.match(/Sec-WebSocket-Accept:\s*(.+)/i);
          if (!acceptMatch || acceptMatch[1].trim() !== expectedAccept) {
            socket.destroy();
            reject(new Error('WebSocket accept key mismatch'));
            return;
          }

          handshakeComplete = true;
          this.socket = socket;
          this.readyState = 'OPEN';

          // Any remaining data after handshake is frame data
          const remaining = handshakeBuffer.slice(headerEnd + 4);
          if (remaining.length > 0) {
            this.buffer = Buffer.from(remaining, 'utf8');
            this.processBuffer();
          }

          // Switch to frame processing
          socket.removeListener('data', onData);
          socket.on('data', (data: Buffer) => {
            this.buffer = Buffer.concat([this.buffer, data]);
            this.processBuffer();
          });

          this.emit('open');
          resolve();
        }
      };

      socket.on('data', onData);

      socket.on('error', (err) => {
        clearTimeout(timeout);
        this.readyState = 'CLOSED';
        if (!handshakeComplete) {
          reject(err);
        } else {
          this.emit('error', err);
        }
      });

      socket.on('close', () => {
        clearTimeout(timeout);
        this.readyState = 'CLOSED';
        this.emit('close');
      });
    });
  }

  /**
   * Send a text message.
   */
  send(data: string): void {
    if (this.readyState !== 'OPEN' || !this.socket) {
      throw new Error('WebSocket is not open');
    }
    const frame = this.encodeFrame(OPCODE_TEXT, Buffer.from(data, 'utf8'));
    this.socket.write(frame);
  }

  /**
   * Close the WebSocket connection gracefully.
   */
  close(code: number = 1000, reason: string = ''): Promise<void> {
    return new Promise((resolve) => {
      if (this.readyState === 'CLOSED' || this.readyState === 'CLOSING') {
        resolve();
        return;
      }

      this.readyState = 'CLOSING';

      if (this.socket) {
        // Send close frame
        const payload = Buffer.alloc(2 + Buffer.byteLength(reason, 'utf8'));
        payload.writeUInt16BE(code, 0);
        if (reason) payload.write(reason, 2, 'utf8');
        const frame = this.encodeFrame(OPCODE_CLOSE, payload);
        this.socket.write(frame);

        // Force close after 5 seconds
        const forceClose = setTimeout(() => {
          this.destroy();
          resolve();
        }, 5000);

        this.once('close', () => {
          clearTimeout(forceClose);
          resolve();
        });
      } else {
        this.readyState = 'CLOSED';
        resolve();
      }
    });
  }

  /**
   * Destroy the connection immediately without close handshake.
   */
  destroy(): void {
    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
    }
    this.readyState = 'CLOSED';
    this.buffer = Buffer.alloc(0);
  }

  // ===========================================================================
  // FRAME ENCODING (client → server: always masked)
  // ===========================================================================

  private encodeFrame(opcode: number, payload: Buffer): Buffer {
    const mask = randomBytes(4);
    const len = payload.length;

    let headerLen: number;
    let header: Buffer;

    if (len < 126) {
      headerLen = 2 + 4; // 2 header + 4 mask
      header = Buffer.alloc(headerLen);
      header[0] = 0x80 | opcode; // FIN + opcode
      header[1] = 0x80 | len; // MASK + length
      mask.copy(header, 2);
    } else if (len < 65536) {
      headerLen = 2 + 2 + 4; // 2 header + 2 ext len + 4 mask
      header = Buffer.alloc(headerLen);
      header[0] = 0x80 | opcode;
      header[1] = 0x80 | 126;
      header.writeUInt16BE(len, 2);
      mask.copy(header, 4);
    } else {
      headerLen = 2 + 8 + 4; // 2 header + 8 ext len + 4 mask
      header = Buffer.alloc(headerLen);
      header[0] = 0x80 | opcode;
      header[1] = 0x80 | 127;
      // Write 64-bit length (JS safe integer range)
      header.writeUInt32BE(Math.floor(len / 0x100000000), 2);
      header.writeUInt32BE(len % 0x100000000, 6);
      mask.copy(header, 10);
    }

    // Mask payload
    const masked = Buffer.alloc(len);
    for (let i = 0; i < len; i++) {
      masked[i] = payload[i] ^ mask[i & 3];
    }

    return Buffer.concat([header, masked]);
  }

  // ===========================================================================
  // FRAME DECODING (server → client: never masked)
  // ===========================================================================

  private processBuffer(): void {
    while (this.buffer.length >= 2) {
      const firstByte = this.buffer[0];
      const secondByte = this.buffer[1];

      const fin = (firstByte & 0x80) !== 0;
      const opcode = firstByte & 0x0f;
      const masked = (secondByte & 0x80) !== 0;
      let payloadLen = secondByte & 0x7f;

      let offset = 2;

      // Extended payload length
      if (payloadLen === 126) {
        if (this.buffer.length < 4) return; // Need more data
        payloadLen = this.buffer.readUInt16BE(2);
        offset = 4;
      } else if (payloadLen === 127) {
        if (this.buffer.length < 10) return;
        const hi = this.buffer.readUInt32BE(2);
        const lo = this.buffer.readUInt32BE(6);
        payloadLen = hi * 0x100000000 + lo;
        offset = 10;
      }

      // Payload size guard
      if (payloadLen > this.options.maxPayloadSize) {
        this.emit('error', new Error(`Payload too large: ${payloadLen} bytes`));
        this.destroy();
        return;
      }

      // Masking key (server should not mask, but handle it anyway)
      let maskKey: Buffer | null = null;
      if (masked) {
        if (this.buffer.length < offset + 4) return;
        maskKey = this.buffer.slice(offset, offset + 4);
        offset += 4;
      }

      // Check if we have the full payload
      if (this.buffer.length < offset + payloadLen) return;

      // Extract payload
      let payload = this.buffer.slice(offset, offset + payloadLen);

      // Unmask if needed
      if (maskKey) {
        for (let i = 0; i < payload.length; i++) {
          payload[i] = payload[i] ^ maskKey[i & 3];
        }
      }

      // Consume from buffer
      this.buffer = this.buffer.slice(offset + payloadLen);

      // Handle frame (we only support FIN frames — no fragmentation needed for CDP)
      if (!fin) {
        // CDP doesn't use fragmented frames, skip
        continue;
      }

      this.handleFrame(opcode, payload);
    }
  }

  private handleFrame(opcode: number, payload: Buffer): void {
    switch (opcode) {
      case OPCODE_TEXT:
        this.emit('message', payload.toString('utf8'));
        break;

      case OPCODE_CLOSE: {
        const code = payload.length >= 2 ? payload.readUInt16BE(0) : 1005;
        const reason = payload.length > 2 ? payload.slice(2).toString('utf8') : '';

        if (this.readyState === 'OPEN') {
          // Echo close frame back
          this.readyState = 'CLOSING';
          const response = Buffer.alloc(2);
          response.writeUInt16BE(code, 0);
          if (this.socket) {
            this.socket.write(this.encodeFrame(OPCODE_CLOSE, response));
            this.socket.end();
          }
        }

        this.readyState = 'CLOSED';
        this.emit('close', code, reason);
        break;
      }

      case OPCODE_PING:
        // Reply with pong
        if (this.socket && this.readyState === 'OPEN') {
          this.socket.write(this.encodeFrame(OPCODE_PONG, payload));
        }
        break;

      case OPCODE_PONG:
        // Ignore pong
        break;

      default:
        // Unknown opcode — ignore
        break;
    }
  }
}
