from saf_mcp import __version__
from saf_mcp.security import SAFSecurityError, resolve_dataset_path
from saf_mcp.server import mcp


def test_imports() -> None:
    assert __version__ == "0.3.0"
    assert mcp is not None


def test_path_traversal_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    try:
        resolve_dataset_path("../secret.sav")
    except SAFSecurityError as exc:
        assert "Path traversal blocked" in str(exc)
    else:
        raise AssertionError("Expected path traversal to be blocked.")
