# Generated by Django 5.1.5 on 2025-01-18 16:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("recommender", "0004_release_tags"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="release",
            name="tags",
        ),
    ]
