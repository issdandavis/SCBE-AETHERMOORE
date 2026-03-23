# Troubleshooting

## `DevToolsActivePort file doesn't exist`

- Use `--debugger-address 127.0.0.1:9222` instead of launching with `--profile-dir`.
- Start Chrome first with `--remote-debugging-port=9222`.

## `cannot connect to chrome at 127.0.0.1:9222`

- Restart Chrome with the remote debugging flag.
- Re-run the script after Chrome is fully open.

## No products matched

- Open `https://app.gumroad.com/products` in the attached Chrome session.
- Update `--targets` names to match visible Gumroad product names.

## Product skipped (no filename match)

- Rename image files to include product words (example: `worldforge.png`, `hydra-protocol.jpg`).
- Re-run with `--dry-run` to verify matches before upload.
