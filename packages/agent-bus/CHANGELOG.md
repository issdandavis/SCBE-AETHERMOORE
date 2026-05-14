# Changelog

## 0.3.1

- **Workspace formation command**: adds `scbe-agent-bus workspace new [--root <path>] [--hint <name>] [--json]`, creating the canonical `.aethermoor-bus/workspaces/<workspace-id>/` folder shape and writing a `SCBE_WORKSPACE_READY=1` receipt into `20_receipts/workspace.json`.

## 0.3.0

- **Hosted-credential gate on `send`**: requests with `--dispatch-provider` set to a non-local provider (anything other than `offline`, `local`, `ollama`, `local_only`, empty) now require `SCBE_API_KEY` in the environment. Without a key, `send` prints a hosted-intake notice (intake URL, service-credits URL, Ko-fi top-up URL, fee policy: provider/model cost passed through with 2-5% SCBE coordination fee) and exits with code 2.
- **New `upgrade` command**: prints the hosted-run path — service-credit policy, intake URL, credit top-up — and detects whether `SCBE_API_KEY` is set so the user knows whether hosted dispatch is currently unlocked.
- **Help text updated** to call out the local-first default and link the `upgrade` flow.
- **Documented constants**: `HOSTED_INTAKE_URL` (`https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html`), `SERVICE_CREDITS_URL` (`https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html`), `CREDIT_TOPUP_URL` (`https://ko-fi.com/izdandavis`).

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
