"""Look up each library track in the US iTunes Store and print the best match.

Usage: python3 scripts/find_store_links.py stations/eleven-alt/library.csv > out.json
Prefers the original studio version (no remix/live/instrumental/sped-up),
the explicit version when both exist, and not a Various Artists compilation.
"""
import csv, json, re, sys, time, urllib.parse, urllib.request

BAD = re.compile(r"\b(remix|live|instrumental|acoustic|sped up|slowed|karaoke|demo|edit|version|mix|carwash|dick's den|a cappella|cover|session|extended|spanish)\b", re.I)

def norm(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"\(feat\.[^)]*\)|\[feat\.[^\]]*\]", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)

def search(artist, title):
    base_title = re.sub(r"\(feat.*", "", title)
    q = urllib.parse.urlencode({"term": f"{artist} {base_title}", "entity": "song",
                                "country": "us", "explicit": "Yes", "limit": 50})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"https://itunes.apple.com/search?{q}", timeout=20) as r:
                return json.load(r)["results"]
        except Exception:
            time.sleep(2 ** attempt)
    return []

def pick(row, results):
    want_t, want_a = norm(row["title"]), norm(row["artist"])
    cands = []
    for r in results:
        if want_a not in norm(r.get("artistName", "")): continue
        name = r.get("trackName", "")
        extra = BAD.search(name) and not BAD.search(row["title"])
        if norm(name) != want_t and not (norm(name).startswith(want_t) and not extra): continue
        if extra: continue
        if r.get("collectionArtistName", "").lower() == "various artists": continue
        if r.get("trackPrice", -1) <= 0: continue
        cands.append(r)
    cands.sort(key=lambda r: (r.get("trackExplicitness") != "explicit", r.get("releaseDate", "")))
    return cands[0] if cands else None

# Original studio album for tracks where plain search finds the wrong version
# (remix single, live session, early EP) or misses explicit-only tracks.
ALBUM_HINTS = {
    "Dracula": "Deadbeat", "End of Beginning": "DECIDE", "oh yeah?": "Oh yeah?",
    "Tiny Bikini": "Cartoon Darkness", "Kids": "Oracular Spectacular", "Arabella": "AM",
    "Daft Punk Is Playing at My House": "LCD Soundsystem", "No One Noticed": "Submarine",
    "The Less I Know the Better": "Currents", "Bad Habit": "Gemini Rights",
    "An Honest Mistake": "The Bravery", "Girlfriend (feat. Dâm-Funk)": "Chris",
    "Photo ID": "I'm Allergic To Dogs!", "10% (feat. Kali Uchis)": "BUBBA",
    "Best Friend (feat. NERVO, The Knocks & ALISA UENO)": "Treehouse",
}

def get(params, path="search"):
    q = urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"https://itunes.apple.com/{path}?{q}", timeout=20) as r:
                return json.load(r)["results"]
        except Exception:
            time.sleep(2 ** attempt)
    return []

def from_album(row, album):
    """Album lookups list explicit tracks that song search hides."""
    want_a = norm(row["artist"])
    # Search hides explicit albums, but lookup-by-artist returns them.
    artists = [a for a in get({"term": row["artist"], "entity": "musicArtist", "country": "us", "limit": 5})
               if norm(a.get("artistName", "")) == want_a]
    albums = []
    for art in artists[:2]:
        albums += [a for a in get({"id": art["artistId"], "entity": "album", "country": "us", "limit": 200}, "lookup")
                   if a.get("wrapperType") == "collection" and norm(a["collectionName"]).startswith(norm(album))]
    albums.sort(key=lambda a: (a.get("collectionExplicitness") != "explicit", "deluxe" in a["collectionName"].lower(),
                               len(a["collectionName"])))
    for a in albums:
        tracks = get({"id": a["collectionId"], "entity": "song", "country": "us"}, "lookup")
        for t in tracks:
            if t.get("wrapperType") == "track" and norm(t["trackName"]).startswith(norm(row["title"])) \
                    and not (BAD.search(t["trackName"]) and not BAD.search(row["title"])) and t.get("trackPrice", -1) > 0:
                return t
    return None

rows = list(csv.DictReader(open(sys.argv[1])))
out = []
for i, row in enumerate(rows, 1):
    hint = ALBUM_HINTS.get(row["title"])
    m = from_album(row, hint) if hint else pick(row, search(row["artist"], row["title"]))
    out.append({"n": i, "category": row["category"], "artist": row["artist"], "title": row["title"],
                "store_title": m and m["trackName"], "store_artist": m and m["artistName"],
                "album": m and m["collectionName"], "explicit": m and m["trackExplicitness"],
                "price": m and m["trackPrice"], "url": m and m["trackViewUrl"].replace("&uo=4", "")})
    time.sleep(0.4)
json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
