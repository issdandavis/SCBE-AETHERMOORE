/**
 * @file bookmarks.js
 * Simple bookmark store for AetherBrowser (main process).
 * Plain JSON in userData -- bookmarks are not secrets, so no encryption needed.
 */
'use strict';

const { app } = require('electron');
const path = require('path');
const fs = require('fs');

let _items = null; // [{ id, url, title, addedAt }]

function file() {
  return path.join(app.getPath('userData'), 'aether-bookmarks.json');
}

function load() {
  if (_items) return;
  try {
    const data = JSON.parse(fs.readFileSync(file(), 'utf8'));
    _items = Array.isArray(data) ? data : [];
  } catch {
    _items = [];
  }
}

function persist() {
  try { fs.writeFileSync(file(), JSON.stringify(_items, null, 2)); } catch { /* best effort */ }
}

function genId() {
  return 'b_' + Date.now().toString(36) + Math.floor(Math.random() * 1e5).toString(36);
}

function list() {
  load();
  return _items.slice();
}

function add(url, title) {
  load();
  if (!url || !/^https?:/i.test(url)) return false;
  if (_items.some((b) => b.url === url)) return false; // no duplicates
  _items.unshift({ id: genId(), url, title: title || url, addedAt: new Date().toISOString() });
  persist();
  return true;
}

function remove(id) {
  load();
  _items = _items.filter((b) => b.id !== String(id));
  persist();
}

module.exports = { list, add, remove };
