import streamlit as st
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from datetime import datetime

DATA_FILE = "album_data.json"
SPOTIFY_CLIENT_ID = "100456f703694a66b15b1b66201eaec6"
SPOTIFY_CLIENT_SECRET = "d0d598c4de0a495e884a4748192f8b2d"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
def stars(rating: float) -> str:
    full  = int(rating)
    half  = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "⯨" * half + "☆" * empty

@st.cache_resource
def get_spotify_client():
    auth_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
    return spotipy.Spotify(auth_manager=auth_manager)

sp = get_spotify_client()

def search_albums(query: str, limit: int = 8):
    if not query.strip():
        return []
    try:
        results = sp.search(q=query, type="album", limit=limit)
        albums = results.get("albums", {}).get("items", [])
        output = []

        for item in albums:
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            images  = item.get("images", [])
            cover   = images[0]["url"] if images else None
            output.append({
                "spotify_id":   item["id"],
                "album":        item["name"],
                "artist":       artists,
                "year":         (item.get("release_date") or "")[:4],
                "cover":        cover,
                "total_tracks": item.get("total_tracks", ""),
            })
        return output
    except Exception as e:
        st.error(f"Spotify search error: {e}")
        return []
def get_album_details(spotify_id: str):
    try:
        album = sp.album(spotify_id)
        artists = ", ".join(a["name"] for a in album.get("artists", []))
        images  = album.get("images", [])
        cover   = images[0]["url"] if images else None
        return {
            "spotify_id":   album["id"],
            "album":        album["name"],
            "artist":       artists,
            "year":         (album.get("release_date") or "")[:4],
            "cover":        cover,
            "total_tracks": album.get("total_tracks", ""),
        }
    except Exception as e:
        st.error(f"Spotify details error: {e}")
        return None

if "albums"         not in st.session_state: st.session_state.albums = load_data()
if "search_results" not in st.session_state: st.session_state.search_results = []
if "selected_album" not in st.session_state: st.session_state.selected_album = None
if "last_query"     not in st.session_state: st.session_state.last_query = ""

st.markdown("""
<div class="app-header">
    <h1>🎵 Album Ranker</h1>
    <p>Search any album via Spotify, rate it, build your collection.</p>
</div>
""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### 🔎 Search Albums")
    query = st.text_input("Search by album or artist", placeholder="e.g. Blonde Frank Ocean")

    if query and query != st.session_state.last_query:
        with st.spinner("Searching Spotify…"):
            st.session_state.search_results = search_albums(query)
            st.session_state.last_query = query
            st.session_state.selected_album = None

    if st.session_state.search_results:
        st.markdown("**Select an album:**")
        for res in st.session_state.search_results:
            label = f"{res['album']} · {res['artist']} ({res['year'] or '?'})"
            if st.button(label, key=f"pick_{res['spotify_id']}"):
                with st.spinner("Loading album details…"):
                    details = get_album_details(res["spotify_id"])
                    st.session_state.selected_album = {**res, **details}
                st.rerun()
    elif query and st.session_state.last_query == query:
        st.caption("No results found.")

    st.divider()

    sel = st.session_state.selected_album

    if sel:
        if sel.get("cover"):
            st.image(sel["cover"], width=80)
        st.markdown(f"**{sel['album']}**  \n{sel['artist']} · {sel['year']}")
        if sel.get("genres"):
            st.caption(sel["genres"])
        if sel.get("total_tracks"):
            st.caption(f"{sel['total_tracks']} tracks")
        st.markdown("### ✏️ Your Rating")
    else:
        st.markdown("### ✏️ Rate an Album")
        st.caption("Search above and select an album, or fill in manually.")

    with st.form("add_album_form", clear_on_submit=True):
        album_name  = st.text_input("Album Title *", value=sel["album"]           if sel else "")
        artist_name = st.text_input("Artist *",       value=sel["artist"]          if sel else "")
        year        = st.text_input("Year",            value=sel["year"]            if sel else "")
        genre       = st.text_input("Genre",           value=sel.get("genres", "") if sel else "")
        rating      = st.slider("Your Rating ★", 0.5, 5.0, 4.0, step=0.5)
        notes       = st.text_area("Notes", placeholder="What do you love about it?", height=70)
        submitted   = st.form_submit_button("Add to Collection")

    if submitted:
        if album_name.strip() and artist_name.strip():
            entry = {
                "id":           datetime.now().isoformat(),
                "spotify_id":   sel["spotify_id"]        if sel else "",
                "album":        album_name.strip(),
                "artist":       artist_name.strip(),
                "year":         year.strip(),
                "genre":        genre.strip(),
                "rating":       rating,
                "notes":        notes.strip(),
                "cover":        sel["cover"]             if sel else None,
                "popularity":   sel.get("popularity", 0) if sel else 0,
                "label":        sel.get("label", "")     if sel else "",
                "total_tracks": sel.get("total_tracks", "") if sel else "",
            }
            st.session_state.albums.append(entry)
            save_data(st.session_state.albums)
            st.session_state.selected_album = None
            st.session_state.search_results = []
            st.session_state.last_query = ""
            st.success(f"Added **{album_name}**!")
            st.rerun()
        else:
            st.error("Album title and artist are required.")

    st.divider()
    st.markdown("### 🗂 Filter & Sort")
    sort_by      = st.selectbox("Sort by", ["Rating (High→Low)", "Rating (Low→High)", "Artist A–Z", "Recently Added"])
    filter_genre = st.text_input("Filter by Genre", placeholder="e.g. Jazz")

# ── Main — Collection ─────────────────────────────────────────────────────────
albums = list(st.session_state.albums)

if filter_genre.strip():
    albums = [a for a in albums if filter_genre.lower() in a.get("genre", "").lower()]

if sort_by == "Rating (High→Low)":
    albums = sorted(albums, key=lambda x: x["rating"], reverse=True)
elif sort_by == "Rating (Low→High)":
    albums = sorted(albums, key=lambda x: x["rating"])
elif sort_by == "Artist A–Z":
    albums = sorted(albums, key=lambda x: x["artist"].lower())

# Stats bar
if st.session_state.albums:
    all_ratings = [a["rating"] for a in st.session_state.albums]
    avg = sum(all_ratings) / len(all_ratings)
    top = max(st.session_state.albums, key=lambda x: x["rating"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Albums Rated", len(st.session_state.albums))
    c2.metric("Average Rating", f"{avg:.1f} / 5.0")
    c3.metric("Top Album", f"{top['album']} ({top['rating']}★)")
    st.divider()

# Album cards
if not albums:
    st.markdown(
        "<div style='text-align:center;color:#555;padding:4rem 0;font-size:1.1rem'>"
        "No albums yet — search and add one in the sidebar!</div>",
        unsafe_allow_html=True,
    )
else:
    cols = st.columns(2)
    for i, album in enumerate(albums):
        with cols[i % 2]:
            star_str   = stars(album["rating"])
            badge_html = f'<span class="badge">{album["genre"]}</span>' if album.get("genre") else ""
            year_str   = f" · {album['year']}" if album.get("year") else ""
            art_html   = (
                f'<img class="album-art" src="{album["cover"]}" alt="cover">'
                if album.get("cover")
                else '<div class="album-art-placeholder">🎵</div>'
            )
            notes_html = (
                f"<div style='color:#aaa;font-size:0.82rem;margin-top:0.5rem;font-style:italic'>"
                f"{album['notes']}</div>"
                if album.get("notes") else ""
            )
            pop = album.get("popularity", 0)
            pop_html = (
                f'<div style="font-size:0.75rem;color:#555;margin-top:4px">Spotify popularity: {pop}/100</div>'
                f'<div class="popularity-bar"><div class="popularity-fill" style="width:{pop}%"></div></div>'
                if pop else ""
            )
            tracks_html = (
                f'<div style="font-size:0.75rem;color:#555;margin-top:3px">'
                f'{album["total_tracks"]} tracks · {album["label"]}</div>'
                if album.get("total_tracks") else ""
            )

            st.markdown(f"""
            <div class="album-card">
                {art_html}
                <div class="album-info">
                    <div class="album-title">{album['album']}{badge_html}</div>
                    <div class="album-meta">{album['artist']}{year_str}</div>
                    <div class="star-display" title="{album['rating']} / 5">
                        {star_str} <span style="font-size:0.83rem;color:#888">{album['rating']}/5</span>
                    </div>
                    {pop_html}
                    {tracks_html}
                    {notes_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🗑 Remove", key=f"del_{album['id']}"):
                st.session_state.albums = [a for a in st.session_state.albums if a["id"] != album["id"]]
                save_data(st.session_state.albums)
                st.rerun()