"""
items/matching.py — "Possible matches" for a report.

For a LOST report we look at open FOUND reports (and vice-versa) that are
close in time, in the same category, and share words in the title / location.
Pure Python scoring over a small candidate set — no external services.
"""
import re
from datetime import timedelta

from django.db.models import Q

from .models import ItemReport

STOP_WORDS = {
    'the', 'and', 'for', 'with', 'near', 'from', 'lost', 'found', 'new', 'old',
    'inside', 'outside', 'floor', 'room', 'block', 'building', 'has', 'have', 'was',
}


def tokens(text):
    """Lower-cased, de-pluralised words (3+ letters) without stop words."""
    out = set()
    for word in re.findall(r'[a-z0-9]+', (text or '').lower()):
        if len(word) < 3 or word in STOP_WORDS:
            continue
        if word.endswith('s') and len(word) > 3:
            word = word[:-1]
        out.add(word)
    return out


def find_matches(item, limit=3, window_days=14):
    """Return up to `limit` open reports of the opposite type that look like `item`."""
    opposite = ItemReport.FOUND if item.report_type == ItemReport.LOST else ItemReport.LOST
    candidates = ItemReport.objects.filter(
        report_type=opposite,
        status=ItemReport.OPEN,
        date__range=(item.date - timedelta(days=window_days), item.date + timedelta(days=window_days)),
    ).exclude(pk=item.pk).exclude(posted_by=item.posted_by).select_related('posted_by')

    if item.category != ItemReport.OTHER:
        candidates = candidates.filter(Q(category=item.category) | Q(category=ItemReport.OTHER))

    my_title, my_loc, my_desc = tokens(item.title), tokens(item.location), tokens(item.description)

    scored = []
    for other in candidates.order_by('-created_at')[:100]:
        title_hits = len(my_title & tokens(other.title))
        loc_hits = len(my_loc & tokens(other.location))
        desc_hits = min(len(my_desc & tokens(other.description)), 3)
        # One generic shared word ("case", "black") is not a match. Need two title
        # words, or a title word plus the same place or two shared description words.
        if not (title_hits >= 2 or (title_hits and (loc_hits or desc_hits >= 2))):
            continue
        same_cat = 1 if other.category == item.category else 0
        gap = abs((other.date - item.date).days)
        score = title_hits * 3 + loc_hits * 2 + desc_hits + same_cat + max(0, 3 - gap // 5)
        other.match_score = score
        scored.append(other)

    scored.sort(key=lambda o: o.match_score, reverse=True)
    return scored[:limit]
