# Eleven Radio on Live365 (interim playout)

Live365 is a stopgap. It gets the station on air, licensed, while Super Hi-Fi comes together. The AzuraCast plan is parked, not deleted.

Docs re-checked 2026-10-05.

## Plan

**Broadcast 1, Ad Control: $89/mo** (or $890/yr). The $65 "With Ads" plan forces 4 min/hr of Live365 network ads; Ad Control lets you switch them off.

- **1,500 listening hours/mo** included, then $0.07/hr. 1,500 hours is about 2 listeners around the clock, which is fine for a demo.
- **50 GB storage.** Our 65 tracks use well under 1 GB.
- **Licensing covers the US, Canada and Mexico.** Listeners elsewhere are geo-blocked.
- Source: help.live365.com, "Live365 2026 Pricing & Feature Update".

## What Live365 does and doesn't do vs. our programming rules

| Our rule (`programming.yaml`) | Live365 | Status |
|---|---|---|
| P1 / N1 / G1 categories | Track Categories. A track can have several categories; use one music-only tag per category. | ✅ |
| Category turnover | ClockWheel: a repeating pattern of category slots | ✅ approximated |
| Least-recently-played rotation | "Oldest Track" selection algorithm | ✅ |
| Artist / album / title separation | AutoDJ Separation Rules: same artist / album / title / track "within" | ✅ |
| DMCA performance complement | Built-in checker | ✅ |
| Energy, year, texture, vocal, BPM separation | Not available | ❌ comes back with Super Hi-Fi |
| Controller-picked songs | No API to queue songs | ❌ not needed for now |
| Requests | Banked by the controller; the payoff comes when the song plays naturally | ✅ |

## Setup steps (you, in the Live365 dashboard)

1. **Create the station** "Eleven Radio" on Broadcast 1 Ad Control. Turn network ads OFF.
2. **Create 3 categories:** `P1`, `N1`, `G1`.
3. **Upload the 65 tracks** from `stations/eleven-alt/buy-list.md`. Assign each track's category during upload, or in bulk afterwards with "Change categories".
   - The category for each song is in `library.csv`.
   - Leave store-bought tags alone. Licensing depends on correct Artist / Title / Album.
4. **Set the separation rules.** These are starting values.
   - Same track / title within: **40 min**
   - Same artist within: **25 min**
   - Same album within: **25 min**
   - Why so short: a P1 song comes back every ~46 min. A separation rule longer than that blocks P1 itself, and artists like Tame Impala, Steve Lacy, Dominic Fike and Jungle have a P1 song *and* a G1 song.
5. **Build the ClockWheel.** 9 slots, every slot set to "Oldest Track":

   ```
   1 P1   2 G1   3 P1   4 G1   5 P1   6 N1   7 P1   8 G1   9 P1
   ```

   One loop is ~33 min. That gives:

   | Category | Each song repeats every | Target |
   |---|---|---|
   | P1 | ~46 min | ~50 min |
   | N1 | ~2.8 hr | ~3 hr |
   | G1 | ~9.7 hr | 10–12 hr |

   P1 never plays twice in a row, and N1 sits between two powers.
6. **Schedule the ClockWheel** as a recurring event: 24 hrs, every day, "Flexible".
   - Live365 fills recurring events 12–24 hrs ahead, so the first one may not start right away.
7. **Get two URLs.** Go to Listen → Embeds and copy:
   - the **stream URL**, `https://streaming.live365.com/<id>`
   - the **station ID**

   Send both to me. Neither is a secret.

## How Kip will know what's playing

Live365 has **no official broadcaster API**. Kip's Station Controller will read:
- **Primary:** the station's public metadata, the same feed Live365's own "Last Played" widget uses. It's undocumented, so it could change without notice.
- **Fallback:** the ICY metadata embedded in the stream itself.

Both are read-only and public. I'll test both against the live station before writing the adapter.

What works on Live365:
- `get_current_song`
- `get_previous_song`

- `request_song`. Requests are **banked**, not queued (see `phase-1-plan.md`), so no queue API is needed.
