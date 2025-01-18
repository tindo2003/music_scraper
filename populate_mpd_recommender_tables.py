import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sscape.settings")
django.setup()
from django.db import transaction
from recommender.models import MPDTrack, MPDPlaylist


def import_mpd_files(mpd_folder):
    """
    Parse all the JSON files in mpd_folder and import them into MPDPlaylist and MPDTrack models.
    Each playlist and track is created only once, and the M2M relationship is recorded.
    """

    # 1) Fetch existing track URIs (in case you rerun the import)
    known_tracks = set(MPDTrack.objects.values_list("track_uri", flat=True))

    # We'll store new tracks in a dict (uri -> MPDTrack object) so we don't duplicate
    track_buffer = {}
    # We'll store new playlists in a list
    playlist_buffer = []

    # We'll remember which tracks go in which playlist (pid -> list of uris)
    playlist_songs_map = {}

    # Get all JSON files in the folder
    json_files = [f for f in os.listdir(mpd_folder) if f.endswith(".json")]
    json_files.sort()

    print(f"Found {len(json_files)} JSON files in {mpd_folder}.")

    for filename in json_files:
        filepath = os.path.join(mpd_folder, filename)
        print(f"Parsing {filepath} ...")

        with open(filepath, "r") as f:
            data = json.load(f)

        # Each file has a 'playlists' list
        for pl_data in data["playlists"]:
            pid = pl_data["pid"]
            name = pl_data.get("name", "")
            description = pl_data.get("description", "")
            num_tracks = pl_data.get("num_tracks", 0)
            num_albums = pl_data.get("num_albums", 0)
            num_followers = pl_data.get("num_followers", 0)

            # Create a playlist object (not yet saved)
            playlist_obj = MPDPlaylist(
                pid=pid,
                name=name,
                description=description,
                num_tracks=num_tracks,
                num_albums=num_albums,
                num_followers=num_followers,
            )
            playlist_buffer.append(playlist_obj)

            # For each track in that playlist
            track_uris_for_playlist = []
            for t in pl_data["tracks"]:
                uri = t["track_uri"]
                if uri not in known_tracks:
                    # It's a brand-new track
                    known_tracks.add(uri)
                    track_buffer[uri] = MPDTrack(
                        track_uri=uri,
                        track_name=t.get("track_name", ""),
                        artist_name=t.get("artist_name", ""),
                        album_name=t.get("album_name", ""),
                        duration_ms=t.get("duration_ms", 0),
                    )
                track_uris_for_playlist.append(uri)

            # Record the track URIs for this playlist
            playlist_songs_map[pid] = track_uris_for_playlist

    # 2) Now bulk create all unique tracks
    print(f"Creating {len(track_buffer)} MPDTrack entries...")
    with transaction.atomic():
        MPDTrack.objects.bulk_create(track_buffer.values(), ignore_conflicts=True)

    # 3) Bulk create all playlists
    print(f"Creating {len(playlist_buffer)} MPDPlaylist entries...")
    with transaction.atomic():
        MPDPlaylist.objects.bulk_create(playlist_buffer, ignore_conflicts=True)

    # 4) Build the many-to-many relationships
    #    We need the actual primary keys from the database for both playlist and track.
    print("Linking playlists and tracks (many-to-many)...")
    # a) Get the new track IDs
    track_ids = dict(MPDTrack.objects.values_list("track_uri", "pk"))
    # b) Get the new playlist IDs
    playlist_ids = dict(MPDPlaylist.objects.values_list("pid", "pk"))

    # c) We'll use the 'through' model for the ManyToManyField
    through_model = MPDPlaylist.songs.through
    through_buffer = []

    for pid, uris in playlist_songs_map.items():
        playlist_pk = playlist_ids[pid]
        for uri in uris:
            track_pk = track_ids[uri]
            through_buffer.append(
                through_model(mpdplaylist_id=playlist_pk, mpdtrack_id=track_pk)
            )

    # Finally, bulk create those M2M rows
    print(f"Creating {len(through_buffer)} playlist->track relationships...")
    with transaction.atomic():
        through_model.objects.bulk_create(through_buffer, ignore_conflicts=True)

    print("Import complete!")


if __name__ == "__main__":
    folder_path = "hello"
    import_mpd_files(folder_path)
