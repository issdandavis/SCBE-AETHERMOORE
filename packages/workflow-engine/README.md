# @scbe/workflow-engine

Private internal TypeScript package for Aether Desktop governed operation contracts and workflow specification tools.

## Install

This package is marked `private: true` and is consumed from the SCBE monorepo workspace rather than published as a standalone npm package.

```bash
npm install
```

## Usage

Use the package to validate workflow specifications and preview governed operation requests:

```ts
import { preview, validate } from './src/index';
```

The exported types define operation requests, decisions, audit records, workflow steps, and workflow specs for local governed desktop automation.

## Quality gate

Run the root package score gate before release work:

```bash
npm run package:quality
```
