// Real Electron preload contracts. Hidden windows, isolated temporary profile,
// fixed IPC fixtures, and no network or Python backend.
const { app, BrowserWindow, WebContentsView, ipcMain } = require('electron');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const desktop = path.resolve(__dirname, '..');
const repo = path.resolve(desktop, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'aether-preload-smoke-'));
const profile = path.join(temp, 'profile');
fs.mkdirSync(profile);
app.setPath('userData', profile);
app.disableHardwareAcceleration();
const html = path.join(temp, 'fixture.html');
fs.writeFileSync(
  html,
  '<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'"><title>Local preload check</title><h1>Ready</h1>'
);
// Browser helpers are ESM even though the repository's Node package is CJS.
// Copy them unchanged into a temporary ESM package for the API selection checks.
const modules = path.join(temp, 'modules');
fs.mkdirSync(modules);
fs.writeFileSync(path.join(modules, 'package.json'), '{"type":"module"}');
for (const name of ['browser-api.js', 'storage.js', 'dom-reader.js']) {
  fs.copyFileSync(path.join(repo, 'src/extension/lib', name), path.join(modules, name));
}
const timer = setTimeout(() => {
  console.error('Preload smoke timed out');
  app.exit(1);
}, 30000);

app
  .whenReady()
  .then(async () => {
    const load = (name) => import(pathToFileURL(path.join(modules, name)).href);
    const { getBrowserApi } = await load('browser-api.js');
    const { loadSettings, saveSettings } = await load('storage.js');
    const { readActivePage, getOpenTabs, captureVisibleTab } = await load('dom-reader.js');
    let saved;
    globalThis.chrome = {
      tabs: {
        query: async () => [{ id: 7, title: 'Fixture' }],
        sendMessage: (_id, _message, callback) => callback({ text: 'Fixture page' }),
      },
      runtime: {
        lastError: null,
        sendMessage: (message, callback) =>
          callback(
            message.action === 'getOpenTabs'
              ? { ok: true, tabs: [{ id: 7 }] }
              : { ok: true, dataUrl: 'data:image/png;base64,fixture' }
          ),
      },
      storage: {
        local: {
          get: (_key, callback) => callback({ aetherbrowser_settings: { port: 8123 } }),
          set: (value, callback) => {
            saved = value;
            callback();
          },
        },
      },
    };
    assert.equal(getBrowserApi(), globalThis.chrome);
    assert.equal((await loadSettings()).port, 8123);
    await saveSettings({ port: 8124 });
    assert.equal(saved.aetherbrowser_settings.port, 8124);
    assert.deepEqual(await readActivePage(), { text: 'Fixture page' });
    assert.deepEqual(await getOpenTabs(), [{ id: 7 }]);
    assert.equal(await captureVisibleTab(), 'data:image/png;base64,fixture');
    globalThis.aetherChrome = {
      storage: {
        local: {
          get: (_key, callback) => callback({ aetherbrowser_settings: { port: 8125 } }),
        },
      },
    };
    assert.equal((await loadSettings()).port, 8125);
    delete globalThis.aetherChrome;
    delete globalThis.chrome;
    assert.throws(getBrowserApi, /API is unavailable/);

    ipcMain.handle('chrome-tabs-query', () => [{ id: 7, title: 'Fixture' }]);
    const win = new BrowserWindow({ show: false, width: 800, height: 600 });
    assert.equal(win.isVisible(), false);
    const checked = [];
    for (const [file, expression] of [
      ['preload-addressbar.js', 'typeof window.addressBarBridge?.navigate === "function"'],
      ['preload-browser.js', 'typeof window.aetherBridge?.readPage === "function"'],
      ['preload-sidepanel.js', 'typeof window.aetherChrome?.tabs.query === "function"'],
    ]) {
      const view = new WebContentsView({
        webPreferences: {
          preload: path.join(desktop, 'electron', file),
          contextIsolation: true,
          nodeIntegration: false,
          sandbox: true,
        },
      });
      const errors = [];
      view.webContents.on('preload-error', (_event, _preload, error) => errors.push(String(error)));
      win.contentView.addChildView(view);
      view.setBounds({ x: 0, y: 0, width: 400, height: 300 });
      await view.webContents.loadFile(html);
      assert.deepEqual(errors, [], file);
      assert.equal(await view.webContents.executeJavaScript(expression), true, file);
      assert.equal(await view.webContents.executeJavaScript('typeof require'), 'undefined');
      if (file === 'preload-sidepanel.js') {
        assert.equal(await view.webContents.executeJavaScript('typeof window.chrome'), 'object');
        assert.equal(
          await view.webContents.executeJavaScript('window.chrome === window.aetherChrome'),
          false
        );
        assert.deepEqual(
          await view.webContents.executeJavaScript('window.aetherChrome.tabs.query({})'),
          [{ id: 7, title: 'Fixture' }]
        );
        assert.equal(
          await view.webContents.executeJavaScript(`new Promise(resolve => {
        window.aetherChrome.storage.local.set({ smoke: 17 }, () => {
          window.aetherChrome.storage.local.get('smoke', result => resolve(result.smoke));
        });
      })`),
          17
        );
      }
      checked.push(file);
      win.contentView.removeChildView(view);
      view.webContents.close();
    }
    console.log(
      JSON.stringify({
        passed: true,
        electron: process.versions.electron,
        checked,
        nativeApiFallback: true,
        desktopApiSelection: true,
        storageRoundtrip: true,
        sandbox: true,
      })
    );
    clearTimeout(timer);
    win.destroy();
    app.quit();
  })
  .catch((error) => {
    console.error(error);
    clearTimeout(timer);
    app.exit(1);
  });
