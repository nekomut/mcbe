"""Resource pack reading and management.

Mirrors gophertunnel/minecraft/resource/pack.go.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pymc.resource.manifest import Manifest


@dataclass
class Pack:
    """A Minecraft Bedrock Edition resource/behaviour pack."""
    manifest: Manifest = field(default_factory=Manifest)
    content: bytes = b""
    content_key: str = ""
    download_url: str = ""
    _checksum: bytes = b""

    @property
    def name(self) -> str:
        return self.manifest.header.name

    @property
    def uuid(self) -> str:
        return self.manifest.header.uuid

    @property
    def description(self) -> str:
        return self.manifest.header.description

    @property
    def version(self) -> str:
        return str(self.manifest.header.version)

    def has_scripts(self) -> bool:
        return self.manifest.has_scripts()

    def has_textures(self) -> bool:
        return self.manifest.has_textures()

    def has_behaviours(self) -> bool:
        return self.manifest.has_behaviours()

    def checksum(self) -> bytes:
        if not self._checksum and self.content:
            self._checksum = hashlib.sha256(self.content).digest()
        return self._checksum

    def size(self) -> int:
        return len(self.content)

    def data_chunk_count(self, chunk_size: int = 1024 * 1024) -> int:
        """Number of chunks needed to transfer this pack."""
        if chunk_size <= 0:
            return 1
        return (len(self.content) + chunk_size - 1) // chunk_size

    def read_at(self, offset: int, length: int) -> bytes:
        """Read a chunk of pack data at the given offset."""
        return self.content[offset : offset + length]

    def encrypted(self) -> bool:
        return bool(self.content_key)

    @classmethod
    def read_path(cls, path: str | Path) -> Pack:
        """Read a resource pack from a file path (zip or directory)."""
        path = Path(path)

        if path.is_file():
            # Read zip archive.
            content = path.read_bytes()
            manifest = _read_manifest_from_zip(content)
            return cls(manifest=manifest, content=content)

        if path.is_dir():
            # Create zip from directory.
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(path)
                        zf.write(file_path, arcname)
            content = buf.getvalue()
            manifest = _read_manifest_from_zip(content)
            return cls(manifest=manifest, content=content)

        raise FileNotFoundError(f"pack path not found: {path}")

    @classmethod
    def read_bytes(cls, data: bytes) -> Pack:
        """Read a resource pack from zip bytes."""
        manifest = _read_manifest_from_zip(data)
        return cls(manifest=manifest, content=data)


def _read_manifest_from_zip(data: bytes) -> Manifest:
    """Extract and parse manifest.json from a zip archive."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Look for manifest.json (may be at root or in a subdirectory).
        for name in zf.namelist():
            if name.endswith("manifest.json"):
                with zf.open(name) as f:
                    return Manifest.from_json(json.loads(f.read()))
        raise ValueError("manifest.json not found in pack archive")
