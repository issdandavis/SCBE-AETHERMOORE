# Design System Rules for Figma Integration

## Project Overview

This is the SCBE (Spectral Context-Bound Encryption) project - a security framework with both TypeScript and Python components. The project includes a demo UI built with Tailwind CSS.

## Frameworks & Libraries

- **Languages**: TypeScript, Python, JavaScript
- **UI Framework**: Vanilla HTML/JS with Tailwind CSS (CDN)
- **Build System**: TypeScript compiler (tsc), Vitest for testing
- **Node Version**: 18.0.0+

## Styling Approach

### Tailwind CSS
The project uses Tailwind CSS via CDN for the demo UI (`src/lambda/demo.html`).

**Custom Styles Pattern:**
```css
/* Custom animations */
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Utility classes */
.animate-pulse-slow { animation: pulse 2s ease-in-out infinite; }
.animate-spin-slow { animation: spin 3s linear infinite; }
.glass { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); }
.gradient-bg { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.glow { box-shadow: 0 0 20px rgba(59, 130, 246, 0.5); }
.glow-green { box-shadow: 0 0 20px rgba(34, 197, 94, 0.5); }
.glow-red { box-shadow: 0 0 20px rgba(239, 68, 68, 0.5); }
```

### Color Palette
- **Primary Background**: Dark gradient (`#1a1a2e` → `#16213e` → `#0f3460`)
- **Text**: White (`text-white`), Gray variants (`text-gray-300`, `text-gray-400`)
- **Accent Colors**:
  - Blue: `bg-blue-600`, `text-blue-400` (primary actions)
  - Green: `bg-green-500`, `text-green-400` (success/safe states)
  - Red: `bg-red-500`, `text-red-400` (danger/critical states)
  - Yellow: `bg-yellow-500`, `text-yellow-400` (warnings)
  - Purple: `bg-purple-500`, `text-purple-400` (special features)

### Component Patterns

**Glass Card:**
```html
<section class="glass rounded-2xl p-8 mb-8 border border-white/10">
  <!-- content -->
</section>
```

**Status Badge:**
```html
<div class="inline-block px-4 py-1 bg-blue-600 rounded-full text-sm">
  Badge Text
</div>
```

**Button:**
```html
<button class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition">
  Button Text
</button>
```

**Metric Card:**
```html
<div class="text-center p-4 bg-green-500/20 rounded-xl">
  <div class="text-3xl font-bold text-green-400">Value</div>
  <div class="text-sm text-gray-400">Label</div>
</div>
```

## Project Structure

```
src/
├── crypto/          # TypeScript cryptographic modules
├── lambda/          # AWS Lambda demo (HTML/JS)
├── metrics/         # Telemetry TypeScript modules
├── rollout/         # Deployment utilities
├── selfHealing/     # Self-healing orchestration
├── symphonic_cipher/ # Python cipher implementation
└── physics_sim/     # Python physics simulation
```

## Figma Integration Guidelines

When converting Figma designs to code:

1. **Use Tailwind utilities** - Match the existing Tailwind patterns
2. **Maintain dark theme** - Use the gradient background and glass effects
3. **Follow color semantics** - Green=safe, Red=danger, Yellow=warning, Blue=info
4. **Use rounded corners** - `rounded-lg`, `rounded-xl`, `rounded-2xl`
5. **Apply glass effect** for cards - `glass` class with `border border-white/10`
6. **Responsive design** - Use `md:` breakpoint for tablet/desktop layouts

## Asset Management

- Images stored alongside HTML files
- No CDN configuration (local assets)
- PNG format for screenshots and diagrams
