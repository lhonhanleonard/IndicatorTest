"""News sentiment via CryptoPanic public RSS + VADER (free, no API key)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@dataclass
class Headline:
    title: str
    published: datetime
    sentiment: float


class NewsFeed:
    def __init__(self, rss_url: str, keywords: list[str] | None = None):
        self.rss_url = rss_url
        self.keywords = [k.lower() for k in (keywords or [])]
        self._vader = SentimentIntensityAnalyzer()

    def fetch(self, lookback_minutes: int = 60) -> list[Headline]:
        feed = feedparser.parse(self.rss_url)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        out: list[Headline] = []
        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            if self.keywords and not any(k in title.lower() for k in self.keywords):
                continue
            published = self._parse_time(entry)
            if published < cutoff:
                continue
            score = self._vader.polarity_scores(title)["compound"]
            out.append(Headline(title=title, published=published, sentiment=score))
        return out

    @staticmethod
    def _parse_time(entry) -> datetime:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc)


def aggregate_sentiment(headlines: list[Headline]) -> float:
    """Average VADER compound score in [-1, +1]. 0 if no headlines."""
    if not headlines:
        return 0.0
    return sum(h.sentiment for h in headlines) / len(headlines)
