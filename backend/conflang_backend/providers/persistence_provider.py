"""
Persistence Provider interface for backend data access.

Abstracts storage so we can swap JSON → SQLite → Supabase without changing business logic.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import json


class PersistenceProvider(ABC):
    """Interface for data persistence"""

    @abstractmethod
    async def save(self, collection: str, id: str, data: Any) -> None:
        """Save data to storage"""
        pass

    @abstractmethod
    async def load(self, collection: str, id: str) -> Any | None:
        """Load data from storage, or None if not found"""
        pass

    @abstractmethod
    async def query(self, collection: str, filter: dict[str, Any]) -> list[Any]:
        """Query data with filters"""
        pass

    @abstractmethod
    async def delete(self, collection: str, id: str) -> None:
        """Delete data from storage"""
        pass


class JSONPersistenceProvider(PersistenceProvider):
    """
    JSON file-based persistence.

    Storage structure:
        {base_path}/{collection}/{id}.json
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def _get_path(self, collection: str, id: str) -> Path:
        """Get the file path for a collection+id"""
        return self.base_path / collection / f"{id}.json"

    async def save(self, collection: str, id: str, data: Any) -> None:
        """Save data as JSON"""
        path = self._get_path(collection, id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def load(self, collection: str, id: str) -> Any | None:
        """Load JSON data"""
        path = self._get_path(collection, id)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def query(self, collection: str, filter: dict[str, Any]) -> list[Any]:
        """
        Query by loading all files in collection and filtering in memory.

        This is inefficient but acceptable for small datasets.
        A real DB would use indexed queries.
        """
        collection_dir = self.base_path / collection
        if not collection_dir.exists():
            return []

        results = []
        for path in collection_dir.glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Simple filter: check if all filter key-value pairs match
                if all(data.get(k) == v for k, v in filter.items()):
                    results.append(data)

        return results

    async def delete(self, collection: str, id: str) -> None:
        """Delete JSON file"""
        path = self._get_path(collection, id)
        if path.exists():
            path.unlink()
