from datetime import datetime, timezone


class LogStore:
    def __init__(self, max_entries: int = 500):
        self.entries: list[dict] = []
        self.max_entries = max_entries
        self._counter = 0

    def add(self, message: str, level: str = "info", category: str = "system"):
        self._counter += 1
        entry = {
            "id": self._counter,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "category": category,
            "message": message,
        }
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_since(self, last_id: int) -> list[dict]:
        return [e for e in self.entries if e["id"] > last_id]

    def clear(self):
        self.entries.clear()


log_store = LogStore()
