"""Tests for image_alter utility."""

import json
import tempfile
from pathlib import Path
from src.utils.image_alter import ImageAlter


class TestImageAlter:
    """Tests for ImageAlter class."""

    def setup_method(self):
        """Create a temporary JSON file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_json = Path(self.temp_dir) / "test_image_alter.json"
        
        # Create test data
        self.test_data = {
            "data/stickers/general/limao_yongyu/01.gif": "礼貌用语表情包",
            "data/stickers/rin/kending_haode/01.png": "好的，表示肯定",
            "data/avatars/user.png": "用户头像"
        }
        
        with open(self.temp_json, "w", encoding="utf-8") as f:
            json.dump(self.test_data, f, ensure_ascii=False)
        
        # Override the JSON path for testing
        ImageAlter._json_path = self.temp_json
        ImageAlter._cache = {}

    def test_get_description_existing(self):
        """Test getting description for an existing image."""
        alter = ImageAlter()
        desc = alter.get_description("data/stickers/general/limao_yongyu/01.gif")
        assert desc == "礼貌用语表情包"

    def test_get_description_nonexistent(self):
        """Test getting description for a non-existent image."""
        alter = ImageAlter()
        desc = alter.get_description("data/stickers/nonexistent/test.png")
        assert desc is None

    def test_path_normalization(self):
        """Test that paths are normalized correctly."""
        alter = ImageAlter()
        
        # Test with leading slash
        desc1 = alter.get_description("/data/stickers/general/limao_yongyu/01.gif")
        assert desc1 == "礼貌用语表情包"
        
        # Test with backslashes
        desc2 = alter.get_description("data\\stickers\\rin\\kending_haode\\01.png")
        assert desc2 == "好的，表示肯定"

    def test_singleton_pattern(self):
        """Test that ImageAlter is a singleton."""
        alter1 = ImageAlter()
        alter2 = ImageAlter()
        assert alter1 is alter2

    def test_cache_behavior(self):
        """Test that cache is used after first load."""
        alter = ImageAlter()
        
        # First call loads from JSON
        desc1 = alter.get_description("data/avatars/user.png")
        assert desc1 == "用户头像"
        
        # Modify JSON file
        new_data = {"data/avatars/user.png": "新的描述"}
        with open(self.temp_json, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False)
        
        # Cache should still return old value
        desc2 = alter.get_description("data/avatars/user.png")
        assert desc2 == "用户头像"
        
        # Clear cache and reload
        alter._cache = {}
        desc3 = alter.get_description("data/avatars/user.png")
        assert desc3 == "新的描述"

    def test_malformed_json_handling(self):
        """Test that malformed JSON doesn't crash the utility."""
        # Write malformed JSON
        with open(self.temp_json, "w") as f:
            f.write("{ invalid json }")
        
        alter = ImageAlter()
        alter._cache = {}  # Clear cache
        
        # Should return None without crashing
        desc = alter.get_description("data/stickers/test.png")
        assert desc is None

    def test_missing_json_file(self):
        """Test behavior when JSON file doesn't exist."""
        ImageAlter._json_path = Path(self.temp_dir) / "nonexistent.json"
        alter = ImageAlter()
        alter._cache = {}  # Clear cache
        
        # Should return None without crashing
        desc = alter.get_description("data/stickers/test.png")
        assert desc is None
