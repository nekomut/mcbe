"""Resource pack manifest parsing.

Mirrors gophertunnel/minecraft/resource/manifest.go.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Version:
    """Semantic version [major, minor, patch]."""
    major: int = 0
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_json(cls, data) -> Version:
        """Parse version from JSON (can be array [1,0,0] or string "1.0.0")."""
        if isinstance(data, list) and len(data) >= 3:
            return cls(major=data[0], minor=data[1], patch=data[2])
        if isinstance(data, str):
            parts = data.split(".")
            return cls(
                major=int(parts[0]) if len(parts) > 0 else 0,
                minor=int(parts[1]) if len(parts) > 1 else 0,
                patch=int(parts[2]) if len(parts) > 2 else 0,
            )
        return cls()


@dataclass
class Module:
    """A module within a resource pack."""
    uuid: str = ""
    description: str = ""
    type: str = ""  # "resources", "data", "client_data", "world_template"
    version: Version = field(default_factory=Version)

    @classmethod
    def from_json(cls, data: dict) -> Module:
        return cls(
            uuid=data.get("uuid", ""),
            description=data.get("description", ""),
            type=data.get("type", ""),
            version=Version.from_json(data.get("version", [])),
        )


@dataclass
class Dependency:
    """A dependency on another resource pack."""
    uuid: str = ""
    version: Version = field(default_factory=Version)

    @classmethod
    def from_json(cls, data: dict) -> Dependency:
        return cls(
            uuid=data.get("uuid", ""),
            version=Version.from_json(data.get("version", [])),
        )


@dataclass
class Header:
    """Resource pack header."""
    name: str = ""
    description: str = ""
    uuid: str = ""
    version: Version = field(default_factory=Version)
    min_engine_version: Version = field(default_factory=Version)

    @classmethod
    def from_json(cls, data: dict) -> Header:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            uuid=data.get("uuid", ""),
            version=Version.from_json(data.get("version", [])),
            min_engine_version=Version.from_json(data.get("min_engine_version", [])),
        )


@dataclass
class Metadata:
    """Resource pack metadata."""
    authors: list[str] = field(default_factory=list)
    license: str = ""
    url: str = ""

    @classmethod
    def from_json(cls, data: dict) -> Metadata:
        return cls(
            authors=data.get("authors", []),
            license=data.get("license", ""),
            url=data.get("url", ""),
        )


@dataclass
class Manifest:
    """Resource pack manifest (manifest.json)."""
    format_version: int = 2
    header: Header = field(default_factory=Header)
    modules: list[Module] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    metadata: Metadata = field(default_factory=Metadata)

    @classmethod
    def from_json(cls, data: dict) -> Manifest:
        return cls(
            format_version=data.get("format_version", 2),
            header=Header.from_json(data.get("header", {})),
            modules=[Module.from_json(m) for m in data.get("modules", [])],
            dependencies=[Dependency.from_json(d) for d in data.get("dependencies", [])],
            capabilities=data.get("capabilities", []),
            metadata=Metadata.from_json(data.get("metadata", {})),
        )

    @classmethod
    def parse(cls, json_str: str) -> Manifest:
        """Parse a manifest from JSON string."""
        return cls.from_json(json.loads(json_str))

    def has_scripts(self) -> bool:
        return any(m.type == "client_data" for m in self.modules)

    def has_textures(self) -> bool:
        return any(m.type == "resources" for m in self.modules)

    def has_behaviours(self) -> bool:
        return any(m.type == "data" for m in self.modules)

    def has_world_template(self) -> bool:
        return any(m.type == "world_template" for m in self.modules)
