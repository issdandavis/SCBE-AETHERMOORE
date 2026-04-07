# Use Claude Code with Chrome (beta)

> Source: https://code.claude.com/docs/en/chrome

> Connect Claude Code to your Chrome browser to test web apps, debug with console logs, automate form filling, and extract data from web pages.

Claude Code integrates with the Claude in Chrome browser extension to give you browser automation capabilities from the CLI or the VS Code extension. Build your code, then test and debug in the browser without switching contexts.

Claude opens new tabs for browser tasks and shares your browser's login state, so it can access any site you're already signed into. Browser actions run in a visible Chrome window in real time. When Claude encounters a login page or CAPTCHA, it pauses and asks you to handle it manually.

Chrome integration is in beta and currently works with Google Chrome and Microsoft Edge. It is not yet supported on Brave, Arc, or other Chromium-based browsers. WSL (Windows Subsystem for Linux) is also not supported.

## Capabilities

With Chrome connected, you can chain browser actions with coding tasks in a single workflow:

* **Live debugging**: read console errors and DOM state directly, then fix the code that caused them
* **Design verification**: build a UI from a Figma mock, then open it in the browser to verify it matches
* **Web app testing**: test form validation, check for visual regressions, or verify user flows
* **Authenticated web apps**: interact with Google Docs, Gmail, Notion, or any app you're logged into without API connectors
* **Data extraction**: pull structured information from web pages and save it locally
* **Task automation**: automate repetitive browser tasks like data entry, form filling, or multi-site workflows
* **Session recording**: record browser interactions as GIFs to document or share what happened

## Prerequisites

Before using Claude Code with Chrome, you need:

* Google Chrome or Microsoft Edge browser
* Claude in Chrome extension version 1.0.36 or higher
* Claude Code version 2.0.73 or higher
* A direct Anthropic plan (Pro, Max, Team, or Enterprise)

Chrome integration is not available through third-party providers like Amazon Bedrock, Google Cloud Vertex AI, or Microsoft Foundry.

## Get started in the CLI

1. Start Claude Code with the `--chrome` flag:

```bash
claude --chrome
```

You can also enable Chrome from within an existing session by running `/chrome`.

2. Ask Claude to use the browser:

```text
Go to code.claude.com/docs, click on the search box,
type "hooks", and tell me what results appear
```

Run `/chrome` at any time to check the connection status, manage permissions, or reconnect the extension.

### Enable Chrome by default

To avoid passing `--chrome` each session, run `/chrome` and select "Enabled by default".

Enabling Chrome by default in the CLI increases context usage since browser tools are always loaded.

### Manage site permissions

Site-level permissions are inherited from the Chrome extension. Manage permissions in the Chrome extension settings.

## Example workflows

### Test a local web application

```text
I just updated the login form validation. Can you open localhost:3000,
try submitting the form with invalid data, and check if the error
messages appear correctly?
```

### Debug with console logs

```text
Open the dashboard page and check the console for any errors when
the page loads.
```

### Automate form filling

```text
I have a spreadsheet of customer contacts in contacts.csv. For each row,
go to the CRM at crm.example.com, click "Add Contact", and fill in the
name, email, and phone fields.
```

### Draft content in Google Docs

```text
Draft a project update based on the recent commits and add it to my
Google Doc at docs.google.com/document/d/abc123
```

### Extract data from web pages

```text
Go to the product listings page and extract the name, price, and
availability for each item. Save the results as a CSV file.
```

### Run multi-site workflows

```text
Check my calendar for meetings tomorrow, then for each meeting with
an external attendee, look up their company website and add a note
about what they do.
```

### Record a demo GIF

```text
Record a GIF showing how to complete the checkout flow, from adding
an item to the cart through to the confirmation page.
```

## Troubleshooting

### Extension not detected

If Claude Code shows "Chrome extension not detected":

1. Verify the Chrome extension is installed and enabled in `chrome://extensions`
2. Verify Claude Code is up to date by running `claude --version`
3. Check that Chrome is running
4. Run `/chrome` and select "Reconnect extension" to re-establish the connection
5. If the issue persists, restart both Claude Code and Chrome

The first time you enable Chrome integration, Claude Code installs a native messaging host configuration file. Chrome reads this file on startup, so restart Chrome if the extension isn't detected on your first attempt.

Native messaging host file locations:

For Chrome:
* **macOS**: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json`
* **Linux**: `~/.config/google-chrome/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json`
* **Windows**: check `HKCU\Software\Google\Chrome\NativeMessagingHosts\` in the Windows Registry

For Edge:
* **macOS**: `~/Library/Application Support/Microsoft Edge/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json`
* **Linux**: `~/.config/microsoft-edge/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json`
* **Windows**: check `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\` in the Windows Registry

### Browser not responding

1. Check if a modal dialog (alert, confirm, prompt) is blocking the page
2. Ask Claude to create a new tab and try again
3. Restart the Chrome extension by disabling and re-enabling it

### Connection drops during long sessions

The Chrome extension's service worker can go idle during extended sessions. Run `/chrome` and select "Reconnect extension".

### Windows-specific issues

* **Named pipe conflicts (EADDRINUSE)**: restart Claude Code. Close any other sessions using Chrome.
* **Native messaging host errors**: try reinstalling Claude Code to regenerate the host configuration.

### Common error messages

| Error                                | Cause                                            | Fix                                                             |
| ------------------------------------ | ------------------------------------------------ | --------------------------------------------------------------- |
| "Browser extension is not connected" | Native messaging host cannot reach the extension | Restart Chrome and Claude Code, then run `/chrome` to reconnect |
| "Extension not detected"             | Chrome extension is not installed or is disabled | Install or enable the extension in `chrome://extensions`        |
| "No tab available"                   | Claude tried to act before a tab was ready       | Ask Claude to create a new tab and retry                        |
| "Receiving end does not exist"       | Extension service worker went idle               | Run `/chrome` and select "Reconnect extension"                  |

## See also

* [Computer use](/en/computer-use): control native macOS apps when a task can't be done in a browser
* [Use Claude Code in VS Code](/en/vs-code#automate-browser-tasks-with-chrome): browser automation in the VS Code extension
* [CLI reference](/en/cli-reference): command-line flags including `--chrome`
