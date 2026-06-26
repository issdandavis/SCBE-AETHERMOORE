/**
 * @file vault.js
 * @module desktop/electron/vault
 *
 * AetherBrowser's secure password vault (main process only).
 *
 * SECURITY MODEL:
 *  - Credentials are encrypted with Electron `safeStorage`, which on Windows uses
 *    DPAPI (a key tied to the logged-in Windows account) -- the SAME mechanism
 *    Chrome/Edge use for their local password stores. The encrypted blob lives in
 *    the per-user `userData` folder. A copy of the file off the disk is unreadable.
 *  - We NEVER write plaintext. If OS encryption is unavailable, saving is refused.
 *  - Passwords are never logged. `list()` deliberately omits password fields.
 *  - The caller (main.js) derives the origin for autofill from the sender frame's
 *    real URL -- never from a value the web page supplies -- so one site can never
 *    read another site's saved password.
 */

'use strict';

const { app, safeStorage } = require('electron');
const path = require('path');
const fs = require('fs');

let _entries = [];   // [{ id, origin, username, password, savedAt, updatedAt }]
let _never = [];     // [origin]  -- sites the user chose "never save" for
let _loaded = false;

function vaultPath() {
  // Resolved lazily so it is only read after the app is ready.
  return path.join(app.getPath('userData'), 'aether-vault.bin');
}

function encryptionAvailable() {
  try {
    return safeStorage.isEncryptionAvailable();
  } catch {
    return false;
  }
}

function load() {
  if (_loaded) return;
  _loaded = true;
  try {
    const file = vaultPath();
    if (fs.existsSync(file)) {
      const buf = fs.readFileSync(file);
      const json = safeStorage.decryptString(buf);
      const data = JSON.parse(json);
      _entries = Array.isArray(data.entries) ? data.entries : [];
      _never = Array.isArray(data.never) ? data.never : [];
    }
  } catch {
    // Corrupt, or encrypted under a different Windows account -> start clean,
    // never crash the browser over the vault.
    _entries = [];
    _never = [];
  }
}

function persist() {
  if (!encryptionAvailable()) return false; // refuse to ever store plaintext
  try {
    const json = JSON.stringify({ entries: _entries, never: _never });
    const buf = safeStorage.encryptString(json);
    fs.writeFileSync(vaultPath(), buf);
    return true;
  } catch {
    return false;
  }
}

function genId() {
  return 'c_' + Date.now().toString(36) + '_' + Math.floor(Math.random() * 1e9).toString(36);
}

function normalizeOrigin(value) {
  if (!value) return null;
  const v = String(value).trim();
  try {
    return new URL(v).origin;
  } catch {
    try {
      return new URL('https://' + v.replace(/^\/+/, '')).origin;
    } catch {
      return null;
    }
  }
}

/** Credentials saved for an exact origin (includes passwords -- for same-origin autofill only). */
function getForOrigin(origin) {
  load();
  const o = normalizeOrigin(origin);
  if (!o) return [];
  return _entries
    .filter((e) => e.origin === o)
    .map((e) => ({ id: e.id, username: e.username, password: e.password }));
}

function isNever(origin) {
  load();
  const o = normalizeOrigin(origin);
  return o ? _never.includes(o) : false;
}

function addNever(origin) {
  load();
  const o = normalizeOrigin(origin);
  if (!o) return;
  if (!_never.includes(o)) _never.push(o);
  // Drop any stored creds for a site the user no longer wants remembered.
  _entries = _entries.filter((e) => e.origin !== o);
  persist();
}

/** Insert or update one credential. Returns { created|updated|unchanged }. */
function upsert({ origin, username, password }) {
  load();
  const o = normalizeOrigin(origin);
  if (!o || !password) return { ok: false };
  const user = String(username || '');
  const existing = _entries.find((e) => e.origin === o && e.username === user);
  const now = new Date().toISOString();
  if (existing) {
    if (existing.password === password) return { ok: true, unchanged: true };
    existing.password = password;
    existing.updatedAt = now;
    persist();
    return { ok: true, updated: true };
  }
  _entries.push({ id: genId(), origin: o, username: user, password, savedAt: now, updatedAt: now });
  persist();
  return { ok: true, created: true };
}

/** Safe listing for the management UI -- NO passwords are included. */
function list() {
  load();
  return _entries
    .map((e) => ({ id: e.id, origin: e.origin, username: e.username, savedAt: e.savedAt, updatedAt: e.updatedAt }))
    .sort((a, b) => (a.origin < b.origin ? -1 : a.origin > b.origin ? 1 : 0));
}

function remove(id) {
  load();
  const before = _entries.length;
  _entries = _entries.filter((e) => e.id !== String(id));
  if (_entries.length !== before) persist();
  return { ok: true };
}

function count() {
  load();
  return _entries.length;
}

/** Bulk import from a parsed export (Google / Proton Pass). Returns how many were stored. */
function importMany(records) {
  load();
  let imported = 0;
  for (const r of records || []) {
    const origin = normalizeOrigin(r.url || r.origin);
    const password = r.password ? String(r.password) : '';
    if (!origin || !password) continue;
    const username = String(r.username || r.email || '');
    const res = upsert({ origin, username, password });
    if (res.ok && !res.unchanged) imported++;
  }
  return imported;
}

module.exports = {
  encryptionAvailable,
  getForOrigin,
  isNever,
  addNever,
  upsert,
  list,
  remove,
  count,
  importMany,
  normalizeOrigin,
};
