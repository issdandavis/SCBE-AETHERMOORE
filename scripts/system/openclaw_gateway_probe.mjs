#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

function parseArgs(argv) {
  const args = {
    method: 'health',
    params: {},
    url: undefined,
    timeoutMs: 15000,
    clientName: 'cli',
    clientDisplayName: 'SCBE Gateway Probe',
    clientVersion: 'scbe-probe',
    mode: 'probe',
    role: 'operator',
    openclawHome: undefined,
    configPath: undefined,
    deviceAuthPath: undefined,
    devicePath: undefined,
    authDeviceToken: undefined,
    gatewayToken: undefined,
    skipDeviceIdentity: false
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--method') args.method = argv[++i];
    else if (arg === '--params') args.params = JSON.parse(argv[++i] ?? '{}');
    else if (arg === '--url') args.url = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i] ?? 15000);
    else if (arg === '--client-name') args.clientName = argv[++i];
    else if (arg === '--client-version') args.clientVersion = argv[++i];
    else if (arg === '--mode') args.mode = argv[++i];
    else if (arg === '--role') args.role = argv[++i];
    else if (arg === '--openclaw-home') args.openclawHome = argv[++i];
    else if (arg === '--config-path') args.configPath = argv[++i];
    else if (arg === '--device-auth-path') args.deviceAuthPath = argv[++i];
    else if (arg === '--device-path') args.devicePath = argv[++i];
    else if (arg === '--auth-device-token') args.authDeviceToken = argv[++i];
    else if (arg === '--gateway-token') args.gatewayToken = argv[++i];
    else if (arg === '--skip-device-identity') args.skipDeviceIdentity = true;
    else if (arg === '--help' || arg === '-h') args.help = true;
  }

  return args;
}

function printHelp() {
  console.log(`OpenClaw gateway probe

Usage:
  node scripts/system/openclaw_gateway_probe.mjs --method tools.catalog
  node scripts/system/openclaw_gateway_probe.mjs --method tools.invoke --params "{\\"tool\\":\\"scbe_flow_plan\\",\\"args\\":{\\"task\\":\\"smoke test\\"}}"

Defaults:
  - loads gateway URL from ~/.openclaw/openclaw.json
  - loads operator device token from ~/.openclaw/identity/device-auth.json
  - loads paired device identity from ~/.openclaw/identity/device.json
  - override with --auth-device-token / --gateway-token
  - omit signing identity with --skip-device-identity
`);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function resolveOpenClawHome() {
  return path.join(process.env.USERPROFILE ?? process.env.HOME ?? '.', '.openclaw');
}

function resolveMethodScopes(method) {
  if (method === 'health') return ['operator.read'];
  if (method.startsWith('tools.') || method.startsWith('models.') || method.startsWith('gateway.') || method.startsWith('chat.history') || method.startsWith('sessions.list')) {
    return ['operator.read'];
  }
  if (method === 'tools.call' || method === 'tools.invoke' || method.startsWith('chat.send') || method.startsWith('sessions.send')) {
    return ['operator.admin', 'operator.write', 'operator.read'];
  }
  return ['operator.read'];
}

function resolveHttpUrl(wsUrl) {
  if (wsUrl.startsWith('ws://')) return `http://${wsUrl.slice('ws://'.length)}`;
  if (wsUrl.startsWith('wss://')) return `https://${wsUrl.slice('wss://'.length)}`;
  return wsUrl;
}

function normalizeGatewayHttpUrl(rawUrl) {
  const parsed = new URL(resolveHttpUrl(rawUrl));
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`Unsupported gateway protocol: ${parsed.protocol}`);
  }
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(parsed.hostname)) {
    throw new Error(`Unsupported gateway host: ${parsed.hostname}`);
  }
  return parsed.toString().replace(/\/$/, '');
}

async function invokeToolOverHttp({ baseUrl, authToken, timeoutMs, params }) {
  void authToken;
  void params;
  void timeoutMs;
  normalizeGatewayHttpUrl(baseUrl);
  throw new Error('Direct HTTP tool invocation is disabled; use the gateway websocket client path instead.');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }

  const openclawHome = args.openclawHome ?? resolveOpenClawHome();
  const configPath = args.configPath ?? path.join(openclawHome, 'openclaw.json');
  const deviceAuthPath = args.deviceAuthPath ?? path.join(openclawHome, 'identity', 'device-auth.json');
  const devicePath = args.devicePath ?? path.join(openclawHome, 'identity', 'device.json');

  const config = readJson(configPath);
  const needsDeviceAuth = !args.gatewayToken && !args.authDeviceToken;
  const deviceAuth = needsDeviceAuth ? readJson(deviceAuthPath) : null;
  const deviceIdentity = args.skipDeviceIdentity || args.gatewayToken ? undefined : readJson(devicePath);
  const distModulePath = path.join(
    process.env.APPDATA ?? '',
    'npm',
    'node_modules',
    'openclaw',
    'dist',
    'method-scopes-Gjdcdc0s.js'
  );

  const gatewayModule = await import(pathToFileURL(distModulePath).href);
  const GatewayClient = gatewayModule.f;

  const roleToken = args.authDeviceToken ?? deviceAuth?.tokens?.[args.role]?.token;
  if (!roleToken && !args.gatewayToken) {
    throw new Error(`No ${args.role} token found in ${path.join(openclawHome, 'identity', 'device-auth.json')}`);
  }

  const url = args.url ?? `ws://127.0.0.1:${config?.gateway?.port ?? 18789}`;
  const gatewaySharedSecret = typeof config?.gateway?.auth?.token === 'string' && config.gateway.auth.token.trim()
    ? config.gateway.auth.token.trim()
    : typeof config?.gateway?.auth?.password === 'string' && config.gateway.auth.password.trim()
      ? config.gateway.auth.password.trim()
      : undefined;
  const authToken = args.gatewayToken ?? gatewaySharedSecret ?? roleToken;

  if (args.method === 'tools.invoke') {
    const result = await invokeToolOverHttp({
      baseUrl: resolveHttpUrl(url),
      authToken,
      timeoutMs: args.timeoutMs,
      params: args.params
    });
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  const result = await new Promise((resolve, reject) => {
    let settled = false;
    const client = new GatewayClient({
      url,
      authDeviceToken: roleToken,
      authToken: args.gatewayToken,
      deviceIdentity,
      clientName: args.clientName,
      clientDisplayName: args.clientDisplayName,
      clientVersion: args.clientVersion,
      mode: args.mode,
      role: args.role,
      scopes: resolveMethodScopes(args.method),
      requestTimeoutMs: args.timeoutMs,
      onHelloOk: async (hello) => {
        try {
          const response = await client.request(args.method, args.params);
          settled = true;
          await client.stopAndWait({ timeoutMs: 1000 }).catch(() => {});
          resolve({ hello, response });
        } catch (error) {
          settled = true;
          await client.stopAndWait({ timeoutMs: 1000 }).catch(() => {});
          reject(error);
        }
      },
      onConnectError: (error) => {
        if (settled) return;
        settled = true;
        reject(error);
      },
      onClose: (code, reason) => {
        if (settled) return;
        settled = true;
        reject(new Error(`gateway closed (${code}): ${reason}`));
      }
    });

    client.start();
  });

  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  const payload = {
    ok: false,
    error: String(error?.message ?? error)
  };
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
});
