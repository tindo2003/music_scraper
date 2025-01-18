from lyricsgenius import Genius

# Initialize Genius API client
GENIUS_API_TOKEN = "C1WHRGGM7mlHJxwgePDAXzo68_aOPJPEGwCL2qI2jGxq8czQ85g0T1zRk1uw8To9"  # Replace with your Genius API token
genius = Genius(
    access_token=GENIUS_API_TOKEN,
    user_agent="my_laptop",
)


def fetch_lyrics(track_title, artist_name):
    try:
        # Search for the song
        song = genius.search_song(track_title, artist_name)

        if song:
            print(f"Found lyrics for '{track_title}' by '{artist_name}':\n")
            # print(song.lyrics)
            return song.lyrics
        else:
            # print(f"No lyrics found for '{track_title}' by '{artist_name}'.")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
