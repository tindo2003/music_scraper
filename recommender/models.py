from django.db import models
from django.contrib.postgres.fields import ArrayField

# Create your models here.


class Genre(models.Model):
    """Represents a music genre."""

    mbid = models.CharField(max_length=36, unique=True, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Artist(models.Model):
    """Represents an artist."""

    mbid = models.CharField(max_length=36, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    artist_type = models.CharField(
        max_length=50, null=True, blank=True
    )  # e.g., person, group, orchestra
    genres = models.ManyToManyField(Genre, related_name="artists", blank=True)

    def __str__(self):
        return self.name


class Release(models.Model):
    """Represents a music release."""

    mbid = models.CharField(max_length=36, unique=True, primary_key=True)  # Primary key
    rg_mbid = models.CharField(
        max_length=36, unique=True, null=True, blank=True
    )  # Release group MBID
    title = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name="releases", blank=True)
    artists = models.ManyToManyField(Artist, related_name="releases")

    def __str__(self):
        return self.title


class Track(models.Model):
    """Represents a track in a release."""

    mbid = models.CharField(max_length=36, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    length = models.IntegerField(null=True, blank=True)  # length in milliseconds
    number = models.CharField(
        max_length=10, null=True, blank=True
    )  # Track number as string
    position = models.IntegerField(
        null=True, blank=True
    )  # Track position in the release
    recording_id = models.CharField(max_length=36, null=True, blank=True)
    recording_title = models.CharField(max_length=255, null=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name="tracks", blank=True)
    release = models.ForeignKey(
        Release, related_name="tracks", on_delete=models.CASCADE
    )
    lyrics = models.TextField(null=True, blank=True)  # Store lyrics as a text field

    def __str__(self):
        return self.title


class MPDTrack(models.Model):
    """
    Represents a unique track from the MPD dataset.
    We'll use the track_uri (e.g., "spotify:track:...") as the primary key.
    """

    track_uri = models.CharField(max_length=200, primary_key=True)
    track_name = models.CharField(max_length=500, blank=True)
    artist_name = models.CharField(max_length=500, blank=True)
    album_name = models.CharField(max_length=500, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    # add other fields you care about, like track_id if needed

    def __str__(self):
        return f"{self.track_uri} | {self.track_name}"


class MPDPlaylist(models.Model):

    pid = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    num_tracks = models.PositiveIntegerField(default=0)
    num_albums = models.PositiveIntegerField(default=0)
    num_followers = models.PositiveIntegerField(default=0)
    # and so on...

    # We'll store track references (their URIs, which are PKs in MPDTrack)
    songs = models.ManyToManyField(MPDTrack)

    def __str__(self):
        return f"PID={self.pid} | {self.name}"


class SeededRecs(models.Model):
    created = models.DateTimeField()
    source = models.CharField(max_length=16)
    target = models.CharField(max_length=16)
    support = models.DecimalField(max_digits=10, decimal_places=8)
    confidence = models.DecimalField(max_digits=10, decimal_places=8)
    type = models.CharField(max_length=8)

    class Meta:
        db_table = "seeded_recs"

    def __str__(self):
        return "[({} => {}) s = {}, c= {}]".format(
            self.source, self.target, self.support, self.confidence
        )
