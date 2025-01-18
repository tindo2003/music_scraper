import requests
import time
import os
import django
from datetime import datetime
from fetch_lyrics import fetch_lyrics

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sscape.settings")
django.setup()
from recommender.models import Genre, Artist, Release, Track


# Assume we have these genres in the database
rock = Genre.objects.create(mbid="1", name="Rock")
pop = Genre.objects.create(mbid="2", name="Pop")
jazz = Genre.objects.create(mbid="3", name="Jazz")

# New release data
release = Release.objects.create(mbid="123", title="Greatest Hits")

# Assign genres to the release
release.genres.set([rock, pop])  # Only Rock and Pop are related
