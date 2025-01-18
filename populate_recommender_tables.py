import requests
import time
import os
import django
from datetime import datetime
from fetch_lyrics import fetch_lyrics

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sscape.settings")
django.setup()
from recommender.models import Genre, Artist, Release, Track


def fetch_release_details(mbid, headers):
    """
    Fetch full release details (including recordings and artists)
    for the given release MBID from MusicBrainz.
    """
    url = f"https://musicbrainz.org/ws/2/release/{mbid}"
    params = {"inc": "recordings+artists+genres+release-groups", "fmt": "json"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"Error fetching release details for {mbid}: Status code {response.status_code}"
        )
        return None


def extract_release(data):
    """
    Extract release information from the API response.
    """
    release_group = data.get("release-group", {})

    release = {
        "mbid": data.get("id"),
        "title": data.get("title"),
        "date": data.get("date"),
        "country": data.get("country"),
        "rg_mbid": release_group.get("id"),  # Extract release-group ID
        "genres": data.get("genres", []),
    }
    return release


def extract_artists(data):
    artists = []
    for artist_credit in data.get("artist-credit", []):
        artist_info = artist_credit.get("artist", {})
        artists.append(
            {
                "mbid": artist_info.get("id"),
                "name": artist_info.get("name"),
                # person, group, orchestra, choir, or character
                "type": artist_info.get("type"),
                "genres": artist_info.get("genres", []),
            }
        )
    # print("artists", artists)
    return artists


def extract_tracks(data):
    tracks = []
    for medium in data.get("media", []):
        for track in medium.get("tracks", []):
            recording = track.get("recording", {})
            track_title = recording.get("title")
            artist_name = None  # Default artist name

            # Extract artist name from data if available
            artist_credit = data.get("artist-credit", [])
            if artist_credit and "artist" in artist_credit[0]:
                artist_name = artist_credit[0]["artist"].get("name")

            # Fetch lyrics for the track
            lyrics = None
            if track_title and artist_name:
                lyrics = fetch_lyrics(track_title, artist_name)

            tracks.append(
                {
                    "mbid": track.get("id"),
                    "title": track.get("title"),
                    "length": track.get("length"),
                    "number": track.get("number"),
                    "position": track.get("position"),
                    "recording_id": recording.get("id"),
                    "recording_title": recording.get("title"),
                    "genres": recording.get("genres", []),
                    "lyrics": lyrics,  # Add lyrics to the track dictionary
                }
            )

    return tracks


def save_genres(genres_dict):
    """
    Create or retrieve Genre objects based on IDs and names.

    Args:
        genres_data (list): A list of dictionaries containing genre IDs and names.
                            Example: [{"id": "genre_id_1", "name": "Rock"}]

    Returns:
        list: A list of Genre objects.
    """
    genres = []
    for genre_data in genres_dict:
        genre_id = genre_data.get("id")
        genre_name = genre_data.get("name", "")
        if genre_id:
            genre, _ = Genre.objects.get_or_create(
                mbid=genre_id,
                defaults={
                    "name": genre_name
                },  # Use the provided name if it's a new genre
            )
            # If the genre already exists but doesn't have a name, update it
            if not genre.name and genre_name:
                genre.name = genre_name
                genre.save()

            genres.append(genre)
    return genres


def _format_date(date_str):
    """
    Format a partial date (YYYY or YYYY-MM) to a full date (YYYY-MM-DD).
    If the date is already in YYYY-MM-DD format, return it as is.
    """
    if date_str:
        parts = date_str.split("-")
        if len(parts) == 1:  # Format: YYYY
            return f"{date_str}-01-01"
        elif len(parts) == 2:  # Format: YYYY-MM
            return f"{date_str}-01"
        elif len(parts) == 3:  # Format: YYYY-MM-DD
            return date_str
    return None  # Return None if the date_str is invalid or None


def save_release(data):
    """
    Save release data to the database.
    """
    # Format the date properly
    raw_date = data.get("date")
    formatted_date = _format_date(raw_date)

    try:
        # Validate the date format (ensure it's correct for DateField)
        if formatted_date:
            datetime.strptime(formatted_date, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format: {raw_date}. Skipping release.")
        return None

    genres = save_genres(data.get("genres", []))
    release, created = Release.objects.update_or_create(
        mbid=data["mbid"],
        defaults={
            "rg_mbid": data.get("rg_mbid"),
            "title": data["title"],
            "date": formatted_date,
        },
    )
    if created:
        release.genres.set(genres)
    return release


def save_artists(data):
    """
    Save artist data to the database.
    """
    artists = []
    for artist_data in data:
        genres = save_genres(artist_data.get("genres", []))
        artist, created = Artist.objects.update_or_create(
            mbid=artist_data["mbid"],
            defaults={
                "name": artist_data["name"],
                "artist_type": artist_data.get("type"),
            },
        )
        if created:
            artist.genres.set(genres)
        artists.append(artist)
    return artists


def save_tracks(data, release):
    """
    Save track data to the database.
    """
    for track_data in data:
        genres = save_genres(track_data.get("genres", []))
        track, created = Track.objects.update_or_create(
            mbid=track_data["mbid"],
            defaults={
                "title": track_data["title"],
                "length": track_data.get("length"),
                "number": track_data.get("number"),
                "position": track_data.get("position"),
                "recording_id": track_data.get("recording_id"),
                "recording_title": track_data.get("recording_title"),
                "lyrics": track_data.get("lyrics"),
                "release": release,
            },
        )
        if created:
            track.genres.set(genres)


def process_and_save(details):
    """
    Process the details of a release and save it to the database.
    """
    release_data = extract_release(details)
    release = save_release(release_data)

    # If the release could not be saved, stop processing further
    if not release:
        print(
            f"Skipping processing for release due to invalid data: {details.get('id')}"
        )
        return

    artist_data = extract_artists(details)
    artists = save_artists(artist_data)
    release.artists.set(artists)

    track_data = extract_tracks(details)
    save_tracks(track_data, release)


def import_musicbrainz_data(start_year: int, end_year: int):
    """
    Fetches and processes MusicBrainz release data in batches,
    saving directly to the DB without storing all releases in memory.
    """
    print(f"Scraping songs from {start_year} to {end_year}")
    query = (
        f"country:XW "
        f'AND format:"Digital Media" '
        f"AND mediums:1 "
        f"AND status:official "
        f"AND date:[{start_year} TO {end_year}] "
        f"AND primarytype:(Album OR Single)"
    )

    headers = {"User-Agent": "Soundscape (upenn.edu; tindo@sas.upenn.edu)"}

    base_search_url = "https://musicbrainz.org/ws/2/release/"
    limit = 100
    offset = 0

    while True:
        print(f"Fetching releases with offset {offset}...")
        params = {"query": query, "fmt": "json", "limit": limit, "offset": offset}

        try:
            response = requests.get(base_search_url, headers=headers, params=params)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            data = response.json()
            releases = data.get("releases", [])
            if not releases:
                print("No more releases found. Stopping.")
                break

            for release in releases:
                release_mbid = release.get("id")
                if release_mbid:
                    try:
                        details = fetch_release_details(release_mbid, headers)
                        if details:
                            process_and_save(details)
                        time.sleep(2)
                    except Exception as e:
                        print(
                            f"An error occurred while processing release {release_mbid}: {e}"
                        )

            offset += limit
            time.sleep(2)
        except Exception as e:
            print(f"An error occurred while fetching releases at offset {offset}: {e}")
            offset += limit  # Skip this batch and try the next one
            time.sleep(2)

    print("Import finished.")


def delete_db():
    """
    Deletes all data from the database for the models Genre, Artist, Release, and Track.
    """
    print("Truncating database...")

    track_count = Track.objects.all().count()
    release_count = Release.objects.all().count()
    artist_count = Artist.objects.all().count()
    genre_count = Genre.objects.all().count()

    if track_count > 0:
        Track.objects.all().delete()
        print(f"Deleted {track_count} tracks.")

    if release_count > 0:
        Release.objects.all().delete()
        print(f"Deleted {release_count} releases.")

    if artist_count > 0:
        Artist.objects.all().delete()
        print(f"Deleted {artist_count} artists.")

    if genre_count > 0:
        Genre.objects.all().delete()
        print(f"Deleted {genre_count} genres.")

    print("Finished truncating database.")


if __name__ == "__main__":
    print("Starting populate_recommender_tables")
    delete_db()
    import_musicbrainz_data(1970, 2024)
