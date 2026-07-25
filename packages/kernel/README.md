# @scbe/kernel

Private internal TypeScript package for the SCBE-AETHERMOORE math and governance kernel.

## Install

This package is marked `private: true` and is consumed from the SCBE monorepo workspace rather than published as a standalone npm package.

```bash
npm install
```

## Usage

Import kernel modules from `src/index.ts` or from specific source modules during monorepo development:

```ts
import { CONSTANTS } from './src/index';
```

The package contains the hyperbolic geometry, harmonic scaling, Sacred Tongues, audio-axis, post-quantum, and 14-layer pipeline primitives used by the public SCBE package build.

## Quality gate

Run the root package score gate before release work:

```bash
npm run package:quality
```
