import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_spotify_track(url):
    """
    Extract track info from a Spotify track URL.
    Returns dict with 'title', 'artist', 'duration', 'search_query'.
    """
    # Extract track ID from URL (e.g., https://open.spotify.com/track/123abc)
    track_id = url.split('/')[-1].split('?')[0]
    try:
        track = sp.track(track_id)
    except Exception as e:
        print(f"[Spotify] Error: {e}")
        return None

    title = track['name']
    artist = track['artists'][0]['name']
    duration = track['duration_ms'] // 1000  # convert ms to seconds
    # Build a search query for YouTube
    search_query = f"{title} {artist} audio"
    return {
        "title": title,
        "artist": artist,
        "duration": duration,
        "search_query": search_query
    }

def get_spotify_playlist(url):
    playlist_id = url.split('/')[-1].split('?')[0]
    results = sp.playlist_tracks(playlist_id)
    tracks = []
    for item in results['items']:
        track = item['track']
        tracks.append({
            "title": track['name'],
            "artist": track['artists'][0]['name'],
            "duration": track['duration_ms'] // 1000,
            "search_query": f"{track['name']} {track['artists'][0]['name']} audio"
        })
    return tracks