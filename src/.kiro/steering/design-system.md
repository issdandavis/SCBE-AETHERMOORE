# Design System Rules for Figma Integration

This document provides guidance for integrating Figma designs into the SCBE Production Pack codebase.

## Project Overview

SCBE is primarily a cryptographic/mathematical backend system with:

- **TypeScript**: Cryptographic envelope, metrics, rollout, self-healing modules
- **Python**: Mathematical core (14-layer hyperbolic geometry pipeline)
- **HTML/CSS**: Demo UI using Tailwind CSS

## Styling Approach

### Primary: Tailwind CSS

The project uses Tailwind CSS via CDN for demo/UI components:

```html
<script src="https://cdn.tailwindcss.com"></script>
```

### Custom CSS Patterns

Custom animations and effects are defined inline:

```css
/* Glass morphism effect */
.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

/* Gradient backgrounds */
.gradient-bg {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

/* Glow effects */
.glow {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
}
.glow-green {
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.5);
}
.glow-red {
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
}
```

## Color Palette

| Purpose         | Tailwind Class | Hex     |
| --------------- | -------------- | ------- |
| Primary Blue    | `blue-600`     | #2563eb |
| Success Green   | `green-500`    | #22c55e |
| Warning Yellow  | `yellow-400`   | #facc15 |
| Danger Red      | `red-500`      | #ef4444 |
| Purple Accent   | `purple-500`   | #a855f7 |
| Background Dark | Custom         | #1a1a2e |
| Text Primary    | `white`        | #ffffff |
| Text Secondary  | `gray-300`     | #d1d5db |
| Text Muted      | `gray-400`     | #9ca3af |

## Component Patterns

### Cards/Sections

```html
<section class="glass rounded-2xl p-8 mb-8 border border-white/10">
  <!-- content -->
</section>
```

### Status Indicators

```html
<!-- Safe/Success -->
<div class="p-4 bg-green-500/20 rounded-xl border border-green-500/30">
  <!-- Warning -->
  <div class="p-4 bg-yellow-500/20 rounded-xl border border-yellow-500/30">
    <!-- Danger/Error -->
    <div class="p-4 bg-red-500/20 rounded-xl border border-red-500/30"></div>
  </div>
</div>
```

### Buttons

```html
<button class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition">Action</button>
```

### Metrics Display

```html
<div class="font-mono text-sm">
  <span class="text-blue-400">value</span>
</div>
```

## Typography

- **Headings**: `font-bold` with size classes (`text-2xl`, `text-4xl`)
- **Body**: Default Tailwind sans-serif
- **Code/Metrics**: `font-mono` for technical values

## Layout Patterns

- Container: `container mx-auto px-4 max-w-6xl`
- Grid: `grid md:grid-cols-2 gap-8`
- Spacing: Consistent `mb-8`, `p-8`, `gap-4`

## Figma Integration Guidelines

When converting Figma designs to code:

1. **Use existing Tailwind utilities** - Don't create custom CSS unless necessary
2. **Match the glass morphism aesthetic** - Use `.glass` class for card backgrounds
3. **Maintain dark theme** - Background should use gradient-bg or dark colors
4. **Use opacity variants** - `bg-color-500/20` for subtle backgrounds
5. **Preserve glow effects** - Apply `.glow-*` classes for emphasis
6. **Keep responsive** - Use `md:` breakpoint for two-column layouts

## Asset Management

- **Icons**: Emoji-based (🔐, 🌐, ✅, etc.) - no icon library
- **Images**: Canvas-based visualizations (Poincaré ball demo)
- **No external assets** - Self-contained HTML demos

## File Locations

- Demo UI: `src/lambda/demo.html`
- TypeScript components: `src/crypto/`, `src/metrics/`, `src/rollout/`
- No dedicated component library exists

## When Adding New UI

1. Follow the existing Tailwind + glass morphism pattern
2. Use the established color palette
3. Maintain dark theme consistency
4. Keep demos self-contained (single HTML file with inline styles/scripts)
