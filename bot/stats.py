"""Counting. No discord imports and no message text: only counters, so it is easy to test
and nothing about what people wrote is ever kept."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Chatter:
    id: int
    name: str
    avatar_key: str | None   # the user's own avatar hash, None = default avatar


class Tally:
    def __init__(self) -> None:
        self.total = 0
        self._by_author: Counter[int] = Counter()
        self._chatters: dict[int, Chatter] = {}
        self._emoji: Counter[str] = Counter()

    def add(
        self,
        author_id: int,
        name: str,
        avatar_key: str | None,
        reactions: Iterable[tuple[str, int]] = (),
    ) -> None:
        """One human message. reactions = (emoji key, how many people reacted) pairs."""
        self.total += 1
        self._by_author[author_id] += 1
        # messages arrive newest first, so the first name we see is the current one
        self._chatters.setdefault(author_id, Chatter(author_id, name, avatar_key))
        for key, count in reactions:
            self._emoji[key] += count

    def top_chatter(self) -> tuple[Chatter, int] | None:
        """(chatter, their message count). Ties go to the lower user id so the result is stable."""
        if not self._by_author:
            return None
        author_id, n = max(self._by_author.items(), key=lambda kv: (kv[1], -kv[0]))
        return self._chatters[author_id], n

    def favorite_emoji(self) -> str | None:
        """Most-used reaction, as cardlink.emoji_field() writes it. None if nobody reacted."""
        top = self._emoji.most_common(1)
        return top[0][0] if top else None
