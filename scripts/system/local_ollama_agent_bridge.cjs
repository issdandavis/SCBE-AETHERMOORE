#!/usr/bin/env node
'use strict';

const http = require('http');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');
const ROUTES = {
  '/api/agent/chat': require(path.join(REPO_ROOT, 'api/agent/chat.js')),
  '/api/agent/health': require(path.join(REPO_ROOT, 'api/agent/health.js')),
  '/api/agent/search': require(path.join(REPO_ROOT, 'api/agent/search.js')),
  '/api/agent/storage': require(path.join(REPO_ROOT, 'api/agent/storage.js')),
};

function configureDefaults(env = process.env) {
  env.AGENT_CHAT_PROVIDER_ORDER = env.AGENT_CHAT_PROVIDER_ORDER || 'ollama,huggingface,offline';
  env.AGENT_OLLAMA_URL = env.AGENT_OLLAMA_URL || env.OLLAMA_URL || 'http://127.0.0.1:11434';
  env.AGENT_OLLAMA_MODEL = env.AGENT_OLLAMA_MODEL || env.OLLAMA_MODEL || 'qwen2.5-coder:1.5b';
  env.AGENT_CHAT_TIMEOUT_MS = env.AGENT_CHAT_TIMEOUT_MS || '45000';
}

function lanAddresses() {
  const rows = [];
  for (const entries of Object.values(os.networkInterfaces())) {
    for (const entry of entries || []) {
      if (entry.family === 'IPv4' && !entry.internal) {
        rows.push(entry.address);
      }
    }
  }
  return rows;
}

function wrapResponse(res) {
  let statusCode = 200;
  return {
    setHeader(name, value) {
      res.setHeader(name, value);
      return this;
    },
    status(code) {
      statusCode = Number(code) || 500;
      return this;
    },
    json(payload) {
      if (!res.headersSent) {
        res.statusCode = statusCode;
      }
      res.end(JSON.stringify(payload));
      return this;
    },
    end(payload) {
      if (!res.headersSent) {
        res.statusCode = statusCode;
      }
      res.end(payload);
      return this;
    },
  };
}

function createBridgeServer() {
  configureDefaults();
  return http.createServer(async (req, res) => {
    const url = new URL(req.url || '/', `http://${req.headers.host || '127.0.0.1'}`);
    const handler = ROUTES[url.pathname];
    if (!handler) {
      res.writeHead(404, { 'content-type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: 'unknown route', route: url.pathname }));
      return;
    }
    try {
      await handler(req, wrapResponse(res));
    } catch (error) {
      if (!res.headersSent) {
        res.writeHead(500, { 'content-type': 'application/json; charset=utf-8' });
      }
      res.end(
        JSON.stringify({
          ok: false,
          error: 'local bridge handler failed',
          error_class: error && error.name ? String(error.name) : 'Error',
        })
      );
    }
  });
}

function main() {
  configureDefaults();
  const host = process.env.LOCAL_AGENT_BRIDGE_HOST || '0.0.0.0';
  const port = Number(process.env.LOCAL_AGENT_BRIDGE_PORT || 8787);
  const server = createBridgeServer();
  server.listen(port, host, () => {
    const address = server.address();
    const boundPort = typeof address === 'object' && address ? address.port : port;
    console.log('Aethermoor local Ollama agent bridge');
    console.log(`  model: ${process.env.AGENT_OLLAMA_MODEL}`);
    console.log(`  ollama: ${process.env.AGENT_OLLAMA_URL}`);
    console.log(`  local: http://127.0.0.1:${boundPort}`);
    for (const ip of lanAddresses()) {
      console.log(`  phone: http://${ip}:${boundPort}`);
    }
    console.log('Set the app Bridge field to the phone URL while on the same Wi-Fi.');
  });
}

if (require.main === module) {
  main();
}

module.exports = {
  configureDefaults,
  createBridgeServer,
  lanAddresses,
};
