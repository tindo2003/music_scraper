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
    artist_type = models.CharField(max_length=50, null=True, blank=True)  # e.g., person, group, orchestra
    genres = models.ManyToManyField(Genre, related_name="artists", blank=True)

    def __str__(self):
        return self.name

class Release(models.Model):
    """Represents a music release."""
    mbid = models.CharField(max_length=36, unique=True, primary_key=True)  # Primary key
    rg_mbid = models.CharField(max_length=36, unique=True, null=True, blank=True)  # Release group MBID
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
    number = models.CharField(max_length=10, null=True, blank=True)  # Track number as string
    position = models.IntegerField(null=True, blank=True)  # Track position in the release
    recording_id = models.CharField(max_length=36, null=True, blank=True)
    recording_title = models.CharField(max_length=255, null=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name="tracks", blank=True)
    release = models.ForeignKey(Release, related_name="tracks", on_delete=models.CASCADE)
    lyrics = models.TextField(null=True, blank=True)  # Store lyrics as a text field

    def __str__(self):
        return self.title
