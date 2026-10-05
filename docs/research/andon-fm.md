# Andon FM: infrastructure teardown (2026-10-05)

Andon Labs runs four stations, each with a different LLM as its AI DJ (Claude, GPT, Gemini, Grok). Their blog post says almost nothing about infrastructure. Everything below comes from their public page (andonlabs.com/radio) and from Live365's public endpoints for their stations.

## What they run

| Layer | What they use |
|---|---|
| Distribution, licensing, CDN | **Live365.** All 4 stations, at `streaming.live365.com/a46431` and similar URLs |
| Playout | **Their own system, sent into Live365 as a 24/7 live source.** For all 4: `live_dj_on: true`, `auto_dj_on: false`, `active_mount: live`. Live365's AutoDJ is off. |
| DJ voice (TTS) | One per station: ElevenLabs `eleven_v3_conversational` (Claude station), OpenAI `gpt-4o-mini-tts`, Google Gemini TTS, Grok TTS |
| Agent | A shared in-house agent setup, the same one they use for their vending machine and cafe experiments |
| Audio and image storage | Tigris, an S3-compatible object store (signed MP3 URLs) |
| Programming | Hour-long themed blocks, named and described on the public page ("Funk Factory", "90s Alternative") |
| Social | One X account per station, with replies shown on the dashboard |
| Website | SvelteKit page with Plausible analytics, a Live365 stream player per station, and live stats |

Scale (Claude station, 14 days): 520 listeners, about 2,500 listening hours (~5,300/mo), ~64 min average session, 91% music / 9% talk.

## What it means for us

1. **Live365 is validated.** A comparable AI-radio project runs on it.
2. **Live365 accepts our own playout as a 24/7 live source and still covers licensing.** That makes this upgrade path real:
   - our own playout pushes live into Live365
   - Kip's voice breaks, banked calls and our full separation rules all go on air
   - no wait for Super Hi-Fi
   - The cost: we run a playout box again (Liquidsoap/AzuraCast on a small server).
   - Still to verify: what Live365 does when the live source drops (AutoDJ fallback?).
3. **Now-playing works.** Tested against their live stations:
   - `GET https://api.live365.com/station/{id}` returns:
     - `current-track` (title, artist, art, start)
     - `last-played` (8 tracks, with start/end/duration)
     - listener count and live/AutoDJ status
   - The ICY `StreamTitle` in the stream itself is `Artist - Title`, which works as a fallback.
   - Both are unofficial but public. This is what Kip's `get_current_song` / `get_previous_song` will read.
4. **Budget for listening hours.** A modestly popular AI station ran ~5,300 hrs/mo. Broadcast 1 includes 1,500; overage at $0.07/hr would be ~$270. Broadcast 3 (7,000 hrs) costs $219 with ads, more with Ad Control. Watch it after launch.
5. **The voice stack matches ours.** ElevenLabs v3 conversational TTS is what they use for voiced breaks.
