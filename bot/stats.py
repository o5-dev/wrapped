class Chatter:
    def __init__(self, id, name, avatar_key):
        self.id = id
        self.name = name
        self.avatar_key = avatar_key


class Tally:
    def __init__(self):
        self.total = 0
        self.message_counts = {}
        self.chatters = {}
        self.emoji_counts = {}

    def add(self, author_id, name, avatar_key, reactions=()):
        self.total += 1
        self.message_counts[author_id] = self.message_counts.get(author_id, 0) + 1
        if author_id not in self.chatters:
            self.chatters[author_id] = Chatter(author_id, name, avatar_key)
        for key, count in reactions:
            self.emoji_counts[key] = self.emoji_counts.get(key, 0) + count

    def top_chatter(self):
        best_id = None
        for author_id, count in self.message_counts.items():
            if best_id is None:
                best_id = author_id
            elif count > self.message_counts[best_id]:
                best_id = author_id
            elif count == self.message_counts[best_id] and author_id < best_id:
                best_id = author_id
        if best_id is None:
            return None
        return self.chatters[best_id], self.message_counts[best_id]

    def favorite_emoji(self):
        best = None
        for key, count in self.emoji_counts.items():
            if best is None or count > self.emoji_counts[best]:
                best = key
        return best
