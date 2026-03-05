/**
 * Copies AetherCode PWA assets into the Capacitor www/ directory
 * and patches the API base URL for the Kindle build.
 */
const fs = require('fs');
const path = require('path');

const WWW = path.resolve(__dirname, '../www');
const SOURCE_CANDIDATES = [
  path.resolve(__dirname, '../../public'),
  path.resolve(__dirname, '../../src/aethercode'),
  WWW,
];

// API endpoint override for packaged builds.
// If unset, app uses same-origin API.
const API_BASE = process.env.AETHERCODE_API_BASE || '';

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function copyFile(src, dest) {
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  console.log(`  copied: ${path.relative(WWW, dest)}`);
}

function patchAppHtml(content) {
  // Optionally replace same-origin API with explicit API base.
  // Original: const API = window.location.origin;
  // Patched (optional): const API = '<AETHERCODE_API_BASE>';
  if (API_BASE) {
    content = content.replace(
      /const API\s*=\s*window\.location\.origin;/,
      `const API = '${API_BASE}';`
    );
  }

  // Add runtime bridge helpers before closing </head>.
  // Keep this bundle self-contained (no third-party CDN dependencies).
  const capScript = `<script>
  // Capacitor bridge — detect native vs web
  window.isKindleApp = typeof window.Capacitor !== 'undefined';

  // Handle offline state
  window.addEventListener('offline', () => {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (dot) dot.className = 'dot off';
    if (txt) txt.textContent = 'Offline';
  });
  window.addEventListener('online', () => {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (dot) dot.className = 'dot on';
    if (txt) txt.textContent = 'Online';
    // Re-check health
    if (typeof checkHealth === 'function') checkHealth();
  });
</script>`;

  content = content.replace('</head>', `${capScript}\n</head>`);

  // Update service worker path for Capacitor
  content = content.replace(
    "navigator.serviceWorker.register('/sw.js')",
    "navigator.serviceWorker.register('./sw.js')"
  );

  // Fix manifest path
  content = content.replace(
    'href="/manifest.json"',
    'href="./manifest.json"'
  );

  return content;
}

function patchManifest(content) {
  const manifest = JSON.parse(content);
  // Fix icon paths for Capacitor
  manifest.start_url = './index.html';
  manifest.scope = './';
  if (manifest.icons) {
    manifest.icons = manifest.icons.map(icon => ({
      ...icon,
      src: icon.src.replace(/^\//, './')
    }));
  }
  if (manifest.shortcuts) {
    manifest.shortcuts = manifest.shortcuts.map(s => ({
      ...s,
      url: s.url.replace(/^\//, './')
    }));
  }
  return JSON.stringify(manifest, null, 2);
}

function patchServiceWorker(content) {
  // Fix cache paths for Capacitor (no leading slashes)
  content = content.replace(
    /["']\/([^"']+)["']/g,
    (match, p) => `"./${p}"`
  );
  content = content.replace('"/"', '"./index.html"');
  return content;
}

function resolveSourceRoot() {
  for (const root of SOURCE_CANDIDATES) {
    const hasManifest = fs.existsSync(path.join(root, 'manifest.json'));
    const hasSw = fs.existsSync(path.join(root, 'sw.js'));
    const hasMainHtml =
      fs.existsSync(path.join(root, 'arena.html')) ||
      fs.existsSync(path.join(root, 'app.html')) ||
      fs.existsSync(path.join(root, 'index.html'));
    if (hasManifest && hasSw && hasMainHtml) {
      return root;
    }
  }
  throw new Error(
    `No valid PWA source root found. Checked: ${SOURCE_CANDIDATES.join(', ')}`
  );
}

// ---- Main ----
console.log('Copying AetherCode PWA assets to kindle-app/www/...');
ensureDir(WWW);
ensureDir(path.join(WWW, 'static', 'icons'));
const SRC = resolveSourceRoot();
const sourceLabel = path.relative(path.resolve(__dirname, '..'), SRC) || '.';
console.log(`  source: ${sourceLabel}`);

// 1. Copy and patch arena.html → index.html (arena.html is the primary app)
const appSource = fs.existsSync(path.join(SRC, 'arena.html'))
  ? path.join(SRC, 'arena.html')
  : fs.existsSync(path.join(SRC, 'app.html'))
    ? path.join(SRC, 'app.html')
    : path.join(SRC, 'index.html');
const appHtml = fs.readFileSync(appSource, 'utf8');
fs.writeFileSync(path.join(WWW, 'index.html'), patchAppHtml(appHtml));
if (API_BASE) {
  console.log(`  patched: index.html (from ${path.basename(appSource)}, API base → ${API_BASE})`);
} else {
  console.log(`  patched: index.html (from ${path.basename(appSource)}, API base → same-origin)`);
}

// 2. Copy and patch manifest.json
const manifest = fs.readFileSync(path.join(SRC, 'manifest.json'), 'utf8');
fs.writeFileSync(path.join(WWW, 'manifest.json'), patchManifest(manifest));
console.log('  patched: manifest.json (paths → relative)');

// 3. Copy and patch service worker
const sw = fs.readFileSync(path.join(SRC, 'sw.js'), 'utf8');
fs.writeFileSync(path.join(WWW, 'sw.js'), patchServiceWorker(sw));
console.log('  patched: sw.js (paths → relative)');

// 4. Copy arena.html if it exists
const arenaPath = path.join(SRC, 'arena.html');
if (fs.existsSync(arenaPath) && path.resolve(arenaPath) !== path.resolve(path.join(WWW, 'arena.html'))) {
  copyFile(arenaPath, path.join(WWW, 'arena.html'));
}

// 5. Copy icons
const iconDir = path.join(SRC, 'static', 'icons');
if (fs.existsSync(iconDir)) {
  for (const file of fs.readdirSync(iconDir)) {
    const sourceIcon = path.join(iconDir, file);
    const destIcon = path.join(WWW, 'static', 'icons', file);
    if (path.resolve(sourceIcon) !== path.resolve(destIcon)) {
      copyFile(sourceIcon, destIcon);
    }
  }
} else {
  console.log('  warn: no icons found at src/aethercode/static/icons/');
  console.log('  generating placeholder icons...');
  // Generate minimal SVG icons as placeholders
  const svgIcon = (size) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect width="${size}" height="${size}" rx="${size * 0.17}" fill="#070b12"/>
  <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" fill="#17c6cf" font-family="sans-serif" font-size="${size * 0.45}" font-weight="800">A</text>
</svg>`;
  fs.writeFileSync(path.join(WWW, 'static', 'icons', 'icon-192.svg'), svgIcon(192));
  fs.writeFileSync(path.join(WWW, 'static', 'icons', 'icon-512.svg'), svgIcon(512));
}

console.log('\nDone! Assets ready in kindle-app/www/');
console.log('Next: npm install && npx cap add android && npx cap sync');
