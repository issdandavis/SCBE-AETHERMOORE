# Aether Realtime Voice Call Options

Last updated: 2026-03-17

## Goal

Answer the practical question: can Aether/SCBE call Issac on a real phone, and can it support realtime spoken conversation like a voice assistant?

Short answer: yes, but there are two different implementation lanes:

1. browser/app realtime voice
2. phone-number / PSTN calling

They share some logic, but they are not the same product.

## Current local repo state

What already exists in this repo:

- Source voice material lives under `artifacts/voice/`
- Local recording path exists via `scripts/voice_record.py` (referenced by `artifacts/voice/README.md`)
- Emulator/phone preview lane exists via:
  - `scripts/system/hydra_browser_phone_bridge.py`
  - `scripts/system/phone_eye.py`
- Audio-governance experiment lane now exists via:
  - `src/harmonic/voxelRecord.ts`
  - `scripts/audio_gate_spectrum_report.py`

What does not appear to exist yet:

- no active telephony provider integration
- no PSTN/SIP call ingress
- no production realtime voice session server
- no phone-number routing or call control layer

So today the repo has `voice assets + phone preview + audio analysis`, but not a true call stack.

## Option A: Browser or app realtime voice

Best first prototype if the goal is "talk to the system live."

Use a browser or mobile app mic, connect directly to a realtime model, and keep tool logic on the application server.

Why this is the easiest first win:

- lower operational complexity than phone-number telephony
- easier to debug
- keeps the user inside Aether surfaces
- maps directly to the existing AetherBrowse / phone lane direction

Official basis:

- OpenAI recommends WebRTC for browser/mobile realtime clients
- OpenAI supports a sideband server connection for monitoring, tool calls, and instruction updates

## Option B: Real phone number that can call or answer

Best if the goal is "give the system a phone identity."

This requires a telecom layer. The clean shapes are:

- SIP trunk -> OpenAI Realtime SIP
- Twilio Media Streams / ConversationRelay -> your app server
- full-stack telecom provider such as SignalWire or Telnyx

This is more powerful, but it adds:

- phone numbers
- telecom billing
- call routing
- webhooks
- compliance/recording concerns
- latency and failover work

## Recommended architecture order

### Phase 1: Realtime app voice

Build:

- browser/app mic input
- OpenAI Realtime WebRTC session
- server-side tool and policy sideband
- local transcript + event logging
- optional SCBE audio telemetry overlay

Outcome:

- user can talk to Aether in realtime
- easier training and iteration loop
- easiest place to test persona, latency, interruption handling, and tool use

### Phase 2: Phone call lane

Add:

- telecom provider
- inbound/outbound phone number
- SIP or streaming bridge
- call event logging
- safety/consent prompts if recording

Outcome:

- the system can answer or place real phone calls
- same core assistant logic can be reused

## Best provider patterns

### OpenAI Realtime + WebRTC

Best for:

- browser/mobile voice assistant
- low-latency speech-to-speech
- tool-calling with server-side monitoring

Notes:

- strong fit for AetherBrowse / phone-app lane
- not by itself a phone-number solution

### OpenAI Realtime + SIP

Best for:

- direct phone/SIP integration
- keeping the model on the OpenAI realtime side

Notes:

- still needs a SIP trunking provider
- good if you want the shortest "real phone number to realtime model" path

### Twilio Media Streams

Best for:

- maximum control
- custom STT/TTS or custom model routing

Notes:

- you manage more of the stack
- good when you want raw audio and your own orchestration

### Twilio ConversationRelay

Best for:

- faster phone-agent MVP
- Twilio handling STT/TTS/session details while your app handles logic

Notes:

- cleaner than raw streams for many assistants
- useful if you want a phone number quickly without owning every media detail

### SignalWire

Best for:

- telecom-native AI voice stack
- multi-agent call routing
- Python-friendly voice agent flows

Notes:

- attractive if the long-term vision is many agents and call routing
- heavier platform decision than a simple MVP

## What I would do here

### If the goal is "Cortana for me"

Start with:

1. realtime browser/app voice
2. persistent session memory
3. server-side tool lane
4. transcripts + traces
5. later add phone-number calling

This gets the conversation quality right before telecom complexity.

### If the goal is "it has its own phone number"

Start with:

1. Twilio ConversationRelay or OpenAI Realtime SIP
2. one inbound number
3. one simple persona/tool loop
4. no outbound calling until the inbound loop is stable

## Training implications

Realtime conversation training is not the same as normal chat SFT.

You will want to capture:

- turn timing
- interruptions / barge-in
- ASR uncertainty
- tool latency
- hesitation / correction moments
- failed actions and handoff requests

Those are part of the "choice monitoring" lane, not just the content lane.

Good training artifacts:

- transcript
- timestamps
- audio features
- policy events
- tool events
- interruption markers
- final satisfaction or correction label

## SCBE-specific fit

The clean SCBE mapping is:

- realtime mic / phone audio = perception channel
- session state = fused world state
- tool sideband = affordance / execution sense
- policy gate = risk sense
- interrupt + barge-in handling = reflex/recovery loop
- saved traces = unbloomed buds + post-action learning

## MVP recommendation

Build this first:

1. `voice-chat` web route or phone-side panel
2. OpenAI Realtime WebRTC session
3. server-side sideband control
4. transcript/event logger
5. optional `audio_gate_spectrum_report` post-analysis

Do not start with:

- full outbound phone automation
- multi-agent live call routing
- custom telecom stack
- large-scale training before the realtime loop is stable

## Sources

- OpenAI Realtime WebRTC: `https://developers.openai.com/api/docs/guides/realtime-webrtc`
- OpenAI Realtime SIP: `https://developers.openai.com/api/docs/guides/realtime-sip`
- OpenAI server-side controls: `https://developers.openai.com/api/docs/guides/realtime-server-controls`
- Twilio Media Streams: `https://www.twilio.com/docs/voice/media-streams`
- Twilio ConversationRelay: `https://www.twilio.com/docs/voice/twiml/connect/conversationrelay`
- SignalWire AI voice stack: `https://signalwire.com/c/telecom-stack-ai-voice`
