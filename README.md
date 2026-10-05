# Eleven Radio

AI radio network built on the ElevenLabs ecosystem. Each station has its own music, AI DJ and programming rules. Stations are configuration, not code.

Station #1 has Kip as its DJ. It plays mostly alt, plus some indie, some electronic, some rock, and whatever else is interesting.

- `docs/phase-1-plan.md`: architecture, the Station Controller contract and the build order
- `djs/kip/`: Kip's prompt and aircheck log

## Architecture

```
Kip (ElevenAgents) ──webhook tools──▶ Station Controller ──PlayoutAdapter──▶ AzuraCast (now)
Future app ─────────────────────────▶        (source of truth)           └─▶ Super Hi-Fi (later)
```
