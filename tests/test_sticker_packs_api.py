"""Test sticker packs API endpoint"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


def test_get_sticker_packs():
    """Test that /api/characters/sticker-packs returns available sticker packs"""
    from src.api.main import app
    
    client = TestClient(app)
    response = client.get("/api/characters/sticker-packs")
    
    assert response.status_code == 200
    data = response.json()
    assert "packs" in data
    assert isinstance(data["packs"], list)
    
    # Verify expected packs exist
    packs = data["packs"]
    assert "general" in packs or "rin" in packs or "weirdo" in packs, \
        f"Expected at least one of the known packs, got: {packs}"
    
    # Verify packs are sorted
    assert packs == sorted(packs), "Packs should be sorted alphabetically"


def test_sticker_packs_endpoint_with_nonexistent_directory(monkeypatch, tmp_path):
    """Test that endpoint returns empty list when sticker directory doesn't exist"""
    from src.api.main import app
    import src.api.http_routes as http_routes
    
    # Temporarily change STICKER_BASE_DIR to a non-existent directory
    monkeypatch.setattr(http_routes, "STICKER_BASE_DIR", tmp_path / "nonexistent")
    
    client = TestClient(app)
    response = client.get("/api/characters/sticker-packs")
    
    assert response.status_code == 200
    data = response.json()
    assert data["packs"] == []


def test_sticker_packs_endpoint_ignores_hidden_dirs(monkeypatch, tmp_path):
    """Test that endpoint ignores hidden directories (starting with .)"""
    from src.api.main import app
    import src.api.http_routes as http_routes
    
    # Create test directory structure
    stickers_dir = tmp_path / "stickers"
    stickers_dir.mkdir()
    
    # Create visible and hidden directories
    (stickers_dir / "pack1").mkdir()
    (stickers_dir / "pack2").mkdir()
    (stickers_dir / ".hidden").mkdir()
    
    # Create a file (should be ignored)
    (stickers_dir / "file.txt").touch()
    
    monkeypatch.setattr(http_routes, "STICKER_BASE_DIR", stickers_dir)
    
    client = TestClient(app)
    response = client.get("/api/characters/sticker-packs")
    
    assert response.status_code == 200
    data = response.json()
    packs = data["packs"]
    
    assert len(packs) == 2
    assert "pack1" in packs
    assert "pack2" in packs
    assert ".hidden" not in packs
    assert "file.txt" not in packs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
