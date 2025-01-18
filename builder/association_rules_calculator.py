import os
from collections import defaultdict
from itertools import combinations
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prs_project.settings")

import django

django.setup()

from recommender.models import SeededRecs, MPDPlaylist


def build_association_rules(playlists):
    """
    `playlists` is a dict where:
        - key = playlist_id (or any unique ID)
        - value = list of items (e.g. song IDs) in that playlist

    Example:
        playlists = {
            "playlist_1": ["songA", "songB", "songC"],
            "playlist_2": ["songA", "songD"],
            ...
        }
    """

    rules = calculate_support_confidence(playlists, min_sup=0.01)
    save_rules(rules)


def calculate_support_confidence(transactions, min_sup=0.01):

    N = len(transactions)
    print(N)
    one_itemsets = calculate_itemsets_one(transactions, min_sup)
    print(one_itemsets)
    two_itemsets = calculate_itemsets_two(transactions, one_itemsets)

    rules = calculate_association_rules(one_itemsets, two_itemsets, N)
    print(rules)
    return sorted(rules)


def calculate_itemsets_one(transactions, min_sup=0.01):

    N = len(transactions)

    temp = defaultdict(int)
    one_itemsets = dict()

    for key, items in transactions.items():
        for item in items:
            inx = frozenset({item})
            temp[inx] += 1

    print("temp:")
    print(temp)
    # remove all items that is not supported.
    for key, itemset in temp.items():
        print(f"{key}, {itemset}, {min_sup}, {min_sup * N}")
        if itemset > min_sup * N:
            one_itemsets[key] = itemset

    return one_itemsets


def calculate_itemsets_two(transactions, one_itemsets):
    two_itemsets = defaultdict(int)

    for key, items in transactions.items():
        items = list(set(items))  # remove duplications

        if len(items) > 2:
            for perm in combinations(items, 2):
                if has_support(perm, one_itemsets):
                    two_itemsets[frozenset(perm)] += 1
        elif len(items) == 2:
            if has_support(items, one_itemsets):
                two_itemsets[frozenset(items)] += 1
    return two_itemsets


def calculate_association_rules(one_itemsets, two_itemsets, N):
    timestamp = datetime.now()

    rules = []
    for source, source_freq in one_itemsets.items():
        for key, group_freq in two_itemsets.items():
            if source.issubset(key):
                target = key.difference(source)
                support = group_freq / N
                confidence = group_freq / source_freq
                rules.append(
                    (
                        timestamp,
                        next(iter(source)),
                        next(iter(target)),
                        confidence,
                        support,
                    )
                )
    return rules


def has_support(perm, one_itemsets):
    return frozenset({perm[0]}) in one_itemsets and frozenset({perm[1]}) in one_itemsets


def save_rules(rules):

    for rule in rules:
        SeededRecs(
            created=rule[0],
            source=str(rule[1]),
            target=str(rule[2]),
            support=rule[3],
            confidence=rule[4],
        ).save()


def get_all_playlists_as_transactions():
    transactions = {}
    # Suppose we have a QuerySet of all playlists
    all_playlists = MPDPlaylist.objects.all().prefetch_related("songs")
    for pl in all_playlists:
        song_ids = list(pl.songs.values_list("id", flat=True))
        transactions[pl.id] = song_ids
    return transactions


def main():
    playlists = get_all_playlists_as_transactions()
    build_association_rules(playlists)
