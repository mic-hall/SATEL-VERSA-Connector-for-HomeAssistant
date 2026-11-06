import json
import zipfile
from pathlib import Path

import pytest

from tools import build_release


@pytest.mark.parametrize(
    "private_name", [".env", "captures/session.pcap", "config/credentials.json", "research.exe"]
)
def test_release_allowlist_excludes_private_files(tmp_path, monkeypatch, private_name):
    monkeypatch.setattr(build_release, "ROOT", tmp_path)
    private = tmp_path / private_name
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_bytes(b"not-for-release")
    safe = tmp_path / "README.md"
    safe.write_text("Public documentation")
    assert build_release.source_files() == [safe]


def test_archive_reproducible_and_paths_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(build_release, "ROOT", tmp_path)
    path = tmp_path / "custom_components/satel_versa/manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    build_release.write_zip(first, [path])
    build_release.write_zip(second, [path])
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["custom_components/satel_versa/manifest.json"]
        assert archive.testzip() is None


def test_metadata_and_translation_keys_match():
    root = Path(__file__).resolve().parents[1]
    component = root / "custom_components/satel_versa"
    manifest = json.loads((component / "manifest.json").read_text())
    assert manifest["domain"] == "satel_versa"
    assert manifest["version"] == "0.1.0-beta.2"
    assert manifest["iot_class"] == "local_polling"
    assert (component / "brand/icon.png").is_file()
    english = json.loads((component / "strings.json").read_text())

    def keys(value):
        return {k: keys(v) for k, v in value.items()} if isinstance(value, dict) else None

    for language in ["en", "pl"]:
        assert keys(json.loads((component / f"translations/{language}.json").read_text())) == keys(
            english
        )
