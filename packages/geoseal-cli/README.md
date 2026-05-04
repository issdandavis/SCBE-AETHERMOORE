# geoseal-cli

`geoseal-cli` is a lightweight npm alias package that exposes the GeoSeal CLI
commands by forwarding to `scbe-aethermoore`.

## Install

```bash
npm i -g geoseal-cli
```

## Usage

```bash
geoseal --help
scbe-geoseal --help
```

## Why this exists

The primary package is published as `scbe-aethermoore`, but many users search
for `geoseal-cli` on npm. This package provides a discoverable alias while
keeping the real CLI implementation in one place.

## Publish (maintainer)

From `packages/geoseal-cli`:

```bash
npm publish --access public
```
