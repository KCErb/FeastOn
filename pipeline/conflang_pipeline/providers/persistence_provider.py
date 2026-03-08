"""
Persistence Provider interface for saving/loading pipeline data.

The pipeline implementation uses JSON files on disk.
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
    async def exists(self, collection: str, id: str) -> bool:
        """Check if data exists"""
        pass

    @abstractmethod
    async def delete(self, collection: str, id: str) -> None:
        """Delete data from storage"""
        pass


class JSONPersistenceProvider(PersistenceProvider):
    """
    JSON file-based persistence for the pipeline.

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

    async def exists(self, collection: str, id: str) -> bool:
        """Check if JSON file exists"""
        return self._get_path(collection, id).exists()

    async def delete(self, collection: str, id: str) -> None:
        """Delete JSON file"""
        path = self._get_path(collection, id)
        if path.exists():
            path.unlink()
