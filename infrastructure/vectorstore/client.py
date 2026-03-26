from __future__ import annotations

from typing import Any


class VectorStoreClient:
    def __init__(self, uri: str = 'memory://vectorstore'):
        self.uri = uri
        self._memory: list[dict[str, Any]] = []

    def upsert_documents(self, documents: list[dict[str, Any]]) -> None:
        self._memory.extend(documents)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self._memory[:limit]
