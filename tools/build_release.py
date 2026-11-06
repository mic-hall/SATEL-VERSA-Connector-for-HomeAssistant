#!/usr/bin/env python3
"""Build deterministic, allowlisted archives. No Git state or credentials needed."""

import json
import re
import zipfile
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {
    ".github/CODEOWNERS",
    ".gitignore",
    "README.md",
    "README.pl.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "TESTING.md",
    "PUBLISHING.md",
    "hacs.json",
    "pyproject.toml",
    "requirements-dev.txt",
}
BRAND_FILES = {
    "custom_components/satel_versa/brand/icon.png",
    "custom_components/satel_versa/brand/icon@2x.png",
}
PREFIXES = ("custom_components/satel_versa/", "tests/", "tools/", ".github/")
SUFFIXES = {".py", ".json", ".md", ".yml", ".yaml", ".toml", ".txt"}


def source_files() -> list[Path]:
    """No arbitrary files, symlinks, binary artifacts or research data."""
    files = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        name = relative.as_posix()
        if any(
            part.startswith(".") and part not in (".github", ".gitignore")
            for part in relative.parts
        ):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlinks cannot be distributed: {name}")
        if "__pycache__" in relative.parts or "dist" in relative.parts or not path.is_file():
            continue
        if (
            name in TOP_FILES
            or name in BRAND_FILES
            or (name.startswith(PREFIXES) and path.suffix in SUFFIXES)
        ):
            if path.stat().st_size > 256_000:
                raise ValueError(f"Unexpected large file: {name}")
            if name in BRAND_FILES:
                files.append(path)
                continue
            text = path.read_text()
            markers = ("/" + "Users" + "/", "/" + "Volumes" + "/", "PRIVATE" + " KEY-----")
            if any(marker in text for marker in markers):
                raise ValueError(f"Private data marker: {name}")
            files.append(path)
    return files


def write_zip(target: Path, files: list[Path], prefix: str = "") -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = prefix + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def main() -> None:
    manifest = json.loads((ROOT / "custom_components/satel_versa/manifest.json").read_text())
    version = manifest["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-z0-9.]+)?", version):
        raise ValueError("Invalid version")
    files = source_files()
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    outputs = [
        output / f"satel_versa-{version}.zip",
        output / f"satel-versa-bridge-{version}-source.zip",
    ]
    write_zip(
        outputs[0], [p for p in files if p.relative_to(ROOT).as_posix().startswith(PREFIXES[0])]
    )
    write_zip(outputs[1], files, prefix="satel-versa-bridge/")
    hashes = "".join(f"{sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in outputs)
    (output / "SHA256SUMS").write_text(hashes)
    print(hashes, end="")


if __name__ == "__main__":
    main()
