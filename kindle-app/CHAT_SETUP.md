# Kindle App Polly Chat Setup

## What shipped
- `kindle-app/www/chat.html` is now a real Hugging Face-backed chat surface.
- `kindle-app/www/static/polly-hf-chat.js` exposes a reusable `window.PollyHFChat.mount(...)` API.
- The same files are mirrored into the Android asset lane under `kindle-app/android/app/src/main/assets/public/`.

## Default model routing
- chat default: `issdandavis/scbe-pivot-qwen-0.5b`
- future dedicated model: `issdandavis/polly-chat-qwen-0.5b`
- embeddings only: `issdandavis/phdm-21d-embedding`
- not the default chatbot: `issdandavis/spiralverse-ai-federated-v1`

## Security split
- private local app: storing a Hugging Face token on-device is acceptable
- public website: do not expose raw tokens; use a proxy endpoint instead

## Mounting the widget in other surfaces
```html
<div id="pollySidebar"></div>
<script src="/static/polly-hf-chat.js"></script>
<script>
  window.PollyHFChat.mount(document.getElementById("pollySidebar"), {
    title: "Polly",
    subtitle: "Support and navigation assistant",
    model: "issdandavis/scbe-pivot-qwen-0.5b"
  });
</script>
```

## Feedback loop
The widget stores local thumbs-up / needs-work feedback and can export that history. Use those exports as the next SFT and preference-tuning lane for the dedicated Polly chat model.
