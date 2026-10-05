# Eleven Radio — Phase 1 Plan

Status: **proposal, awaiting review.** No infrastructure has been created.
Docs verified 2026-10-05 against the AzuraCast source (OpenAPI 0.23.8) and the ElevenLabs Agents docs.

## Goal

One cloud-hosted station that streams continuously, plus a Station Controller that Kip queries through ElevenAgents. Phase 1 is done when the 13-step demo in the brief works end to end:
what's playing → request → it plays → Kip knows it played.

## Blocking issue: music rights

This has to be settled before real catalog tracks go on a public stream.

- **ElevenMusic app terms.** Other users' catalog and playlist tracks may only be used *inside* the app. You cannot download or stream them outside it. Songs you create yourself are a different case and *can* be used externally.
- **Eleven Music model terms.** Every self-serve plan excludes **radio**. Only the Enterprise tier removes that exclusion.
- **Music Marketplace (ElevenCreative).** Tracks there come with a purchasable license and a download. I couldn't confirm whether any license tier covers radio or broadcast.

Plan: keep building. Engineering runs on a **private, password-protected stream** with a handful of placeholder files (test tones or audio you own). Those files are scaffolding only and never stand in for the station's library. Meanwhile, you check Marketplace licensing and/or get written confirmation from ElevenLabs. Nothing about the architecture depends on which source we end up with.

## Repo structure

```
controller/            Station Controller (Python + FastAPI). Built in Step 9; not yet.
  app/
    api.py             HTTP routes: the contract below
    service.py         station logic: request rules, matching, state
    models.py          Track, Play, RequestResult
    playout/
      base.py          PlayoutAdapter interface
      azuracast.py     AzuraCast implementation
  tests/
stations/
  eleven-alt/station.yaml   name, DJ, playout binding, request rules
djs/
  kip/
    prompt.md          personality prompt (baseline, versioned)
    rules.md           behavioral rules distilled from airchecks
    airchecks.md       aircheck log
agents/                ElevenLabs CLI config-as-code (agents.json, tool configs)
infra/                 Caddyfile, compose file, provisioning runbook
scripts/               music loader (AzuraCast upload API), aircheck pull
docs/
```

Stations and DJs are data. Code lives only in `controller/`. Station #2 should need a new `stations/x/`, a new `djs/y/`, and an AzuraCast station, with no new code.

## Station Controller contract

Kip and the future app only ever see this. Responses are small and written for a DJ, never raw AzuraCast JSON.

```
GET  /v1/stations/{station}/now-playing   → Play + elapsed/remaining          (Phase 1)
GET  /v1/stations/{station}/previous      → last Play                          (Phase 2)
GET  /v1/stations/{station}/next          → artist teaser only, never a title  (Phase 2)
GET  /v1/stations/{station}/queue         → internal/admin only                (Phase 2)
POST /v1/stations/{station}/requests      {title, artist?} → RequestResult     (Phase 3)
```

```
Track         { id, title, artist, album?, duration_s, art_url? }
Play          { track, started_at, source: "rotation" | "request" }
RequestResult { status: "scheduled" | "already_scheduled" | "played_recently"
                      | "not_in_library" | "ambiguous",
                track?, songs_ahead?, eta_s?, candidates? }
```

Everything below the contract goes through a single interface:

```
PlayoutAdapter
  now_playing() -> Play
  history(n) -> list[Play]
  upcoming() -> list[Play]
  library() -> list[Track]
  enqueue(track_id) -> position
  skip()                              # Phase 4
```

`AzuraCastAdapter` is the first implementation. A future `SuperHiFiAdapter` would be the second. The routes, Kip's tools and the app stay the same.

## Licensing constraints on the contract

Under the US statutory webcast license (17 USC 114), the station can't announce a specific title before it plays. It may say that an artist will be featured at some unspecified time. Titles are shown "during, but not before" the song plays.

- **Listener-facing "next".** It returns an artist teaser at most ("more Phoenix later"). It never returns a title.
- **The queue.** Admin-only.
- **Request confirmations.** "I'll get that one on" is fine. "That's next" is not. The cap on requested songs per hour is set in `programming.yaml`.

## Scheduler (decision)

AzuraCast's AutoDJ can't do category turnover plus separation rules (energy, year, texture, vocal, BPM, album/artist compliance).

- **Who picks the songs.** The Station Controller picks every song. It applies the categories and rules in `stations/eleven-alt/programming.yaml`, then pushes its pick into AzuraCast's queue 1–2 songs ahead.
- **Fallback.** AzuraCast's own rotation stays on underneath. If the controller dies, the music keeps playing.
- **Requests.** They go through the same picker as an extra candidate, so separation and compliance still apply.
- **To verify in Step 8:** how controller-inserted items interact with AzuraCast's own AutoDJ queue fill.

## How AzuraCast fits underneath (verified)

| Need | AzuraCast mechanism |
|---|---|
| Current, previous, next | `GET /api/nowplaying/{station}`, public. Returns `now_playing`, `song_history`, `playing_next` and `is_request` |
| Queue | `GET /api/station/{id}/queue` (API key). Holds about 3 items ahead, set by `autodj_queue_length` |
| Song changes | Generic web hook on `song_changed` POSTs the full now-playing object to the controller |
| Requests | **Not AzuraCast's native request system.** Its requests wait a random 0–10 min and then queue behind ~3 songs, which is too vague for "I'll get that one on." The controller does the matching, dedup and artist separation itself, then inserts the song via `PUT /api/station/{id}/files/batch` with `do=queue`. That lands it in the next unsent slot, typically 1–2 songs out. |
| "Kip knows it played" | The controller records each request, and the song-change webhook marks it played |
| Skip / play now | `backend/skip` and `files/batch` `do=immediate` exist; held for Phase 4 |
| Music loading | `POST /api/station/{id}/files` plus playlist assignment, scripted |

Auth: AzuraCast API keys inherit their user's full permissions, so the controller gets a dedicated user limited to this station's View, Broadcasting, Media and Reports permissions.

Gap: AzuraCast has no reorder or insert-at-position endpoint. That's acceptable for Phase 1.

## Kip ↔ controller

- Use ElevenAgents **webhook (server) tools**, not MCP. There are only a few endpoints, no approval prompts, and timeouts can be set per tool.
- The station id is a constant in each tool. The tool's bearer token is stored as a workspace secret.
- Tools: `get_current_song` first, then `get_previous_song`, `get_next_song` and `request_song`.
- Kip's prompt and tools are versioned in `agents/` with the official `elevenlabs` CLI, so changes are pushed from git rather than edited in the dashboard.
- Airchecks: pull transcripts with `GET /v1/convai/conversations/{id}`, which includes tool calls, and log the notes in `djs/kip/airchecks.md`.

## Deployment

One DigitalOcean droplet, Ubuntu LTS, **4 GB / 2 vCPU (about $24/mo)**. AzuraCast's minimum is 2 GB, but 2 GB is flaky.

- AzuraCast runs from the official `docker.sh` installer. Skip the 1-click image: it's stale (0.17.x) and has had install failures.
- The controller runs as one container on the same box.
- Caddy terminates TLS:
  - `radio.<domain>` goes to AzuraCast, including the stream.
  - `api.<domain>` goes to the controller.
- The station keeps running with your MacBook off. The Mac is only for admin.
- No Kubernetes, no queue broker, no separate database server. The controller uses SQLite for request records.

## Build order (each step has a test gate)

| # | Step | Gate |
|---|---|---|
| 1 | Plan (this doc) | You approve |
| 2 | Repo scaffold, Kip prompt in git | Committed |
| 3 | Droplet, domain, Caddy | `https://radio.<domain>` resolves |
| 4–5 | AzuraCast installed, station created | Admin UI is up and the station is configured |
| 6 | Load placeholder audio (real tracks once rights are settled) | Files are in a playlist |
| 7 | Stream | Plays in VLC or a browser for 1 hr unattended |
| 8 | Probe the API live | Confirm the table above against our instance |
| 9 | Controller with `now-playing` + AzuraCast adapter | Unit tests, plus a live `curl` that matches the stream |
| 10 | `get_current_song` webhook tool | Tool test in the ElevenLabs dashboard |
| 11 | Connect Kip | "What's playing?" is answered correctly |
| 12 | Aircheck | Notes logged |
| 13 | Phase 2 (previous/next), then Phase 3 (requests) | The full 13-step demo |

## Deliberately not building yet

The website or app, other stations, social features, skip/queue controls, user accounts, Super Hi-Fi, CI/CD beyond a test run, monitoring beyond AzuraCast's own, and multiple servers.

## What I need from you

1. **Music rights.** Pursue Marketplace licensing or written confirmation from ElevenLabs. Until then, OK to proceed on a private placeholder stream?
2. **Hosting.** A DigitalOcean account (or another provider) and a domain you control.
3. **Station id.** I've assumed `eleven-alt` with the display name "Eleven Radio". Confirm or rename.
4. **Secrets.** Keep API keys out of chat. They go in environment variables on the droplet and in ElevenLabs workspace secrets.
