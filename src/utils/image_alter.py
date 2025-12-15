"""Image description utility for providing text alternatives to images."""

import json
from pathlib import Path
from typing import Optional


class ImageAlter:
    """Provides text descriptions for local image files."""

    _instance = None
    _json_path: Path = Path(__file__).parent.parent.parent / "assets" / "config" / "image_descriptions.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def get_description(self, image_path: str) -> Optional[str]:
        """
        Get description for a local image file.

        Args:
            image_path: Relative path to the image file

        Returns:
            Description string if available, None otherwise
        """
        # Normalize path to use forward slashes and remove leading slash
        normalized_path = str(Path(image_path)).replace("\\", "/").lstrip("/")

        # Check cache first
        if normalized_path in self._cache:
            return self._cache[normalized_path]

        # Load from JSON file
        self._load_from_json()

        # Return from cache after loading
        return self._cache.get(normalized_path)

    def _load_from_json(self):
        """Load image descriptions from JSON file into cache."""
        if not self._json_path.exists():
            return

        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache = data
        except Exception:
            # Silently ignore errors, cache remains empty or unchanged
            pass


# Singleton instance
image_alter = ImageAlter()
