# Changelog

## 0.2.2

- Restore the Node package source, TypeScript config, and generated `dist/`
  build path so fresh npm installs expose working API and CLI entrypoints.
- Keep the local-first server, terminal UI, send, and health commands
  self-contained for downloader smoke tests.

## 0.1.1

- Restore package source files on the release branch.
- Update TypeScript build settings for the current TypeScript 6 toolchain.

## 0.1.0

- Initial typed Node wrapper for the SCBE agent-bus pipe runner.
