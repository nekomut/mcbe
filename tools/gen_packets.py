#!/usr/bin/env python3
"""Generate Python packet dataclasses from Go gophertunnel packet source files.

Usage:
    python tools/gen_packets.py [--go-dir PATH] [--out-dir PATH] [--dry-run]

Reads Go packet files, parses struct definitions and Marshal methods,
and generates Python dataclasses with read()/write() methods.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Already ported manually — skip these.
SKIP_FILES = {
    "login.go",
    "play_status.go",
    "server_to_client_handshake.go",
    "client_to_server_handshake.go",
    "disconnect.go",
    "resource_pack_info.go",
    "resource_pack_stack.go",
    "resource_pack_client_response.go",
    "request_network_settings.go",
    "network_settings.go",
    "text.go",
    "set_local_player_as_initialised.go",
    "request_chunk_radius.go",
    "chunk_radius_updated.go",
    # Utility/non-packet files
    "pool.go",
    "id.go",
    "encoder.go",
    "decoder.go",
    "header.go",
    "encryption.go",
    "doc.go",
}

# Go type → (python_type, reader_method, writer_method, default_value)
TYPE_MAP: dict[str, tuple[str, str, str, str]] = {
    "uint8": ("int", "r.uint8()", "w.uint8", "0"),
    "byte": ("int", "r.uint8()", "w.uint8", "0"),
    "int8": ("int", "r.int8()", "w.int8", "0"),
    "uint16": ("int", "r.uint16()", "w.uint16", "0"),
    "int16": ("int", "r.int16()", "w.int16", "0"),
    "uint32": ("int", "r.varuint32()", "w.varuint32", "0"),
    "int32": ("int", "r.varint32()", "w.varint32", "0"),
    "uint64": ("int", "r.varuint64()", "w.varuint64", "0"),
    "int64": ("int", "r.varint64()", "w.varint64", "0"),
    "float32": ("float", "r.float32()", "w.float32", "0.0"),
    "float64": ("float", "r.float64()", "w.float64", "0.0"),
    "bool": ("bool", "r.bool()", "w.bool", "False"),
    "string": ("str", "r.string()", "w.string", '""'),
    "uuid.UUID": ("UUID", "r.uuid()", "w.uuid", "field(default_factory=lambda: UUID(int=0))"),
    "mgl32.Vec3": ("Vec3", "r.vec3()", "w.vec3", "field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))"),
    "mgl32.Vec2": ("Vec2", "r.vec2()", "w.vec2", "field(default_factory=lambda: Vec2(0.0, 0.0))"),
    "protocol.BlockPos": ("BlockPos", "r.block_pos()", "w.block_pos", "field(default_factory=lambda: BlockPos(0, 0, 0))"),
    "protocol.ChunkPos": ("ChunkPos", "r.chunk_pos()", "w.chunk_pos", "field(default_factory=lambda: ChunkPos(0, 0))"),
    "protocol.SubChunkPos": ("SubChunkPos", "r.sub_chunk_pos()", "w.sub_chunk_pos", "field(default_factory=lambda: SubChunkPos(0, 0, 0))"),
    "[]byte": ("bytes", "r.byte_slice()", "w.byte_slice", 'b""'),
}

# IO method name → (reader_call, writer_call)
# For cases where the Go Marshal uses a named IO method that differs from the type.
IO_METHOD_MAP: dict[str, tuple[str, str]] = {
    "Uint8": ("r.uint8()", "w.uint8"),
    "Int8": ("r.int8()", "w.int8"),
    "Uint16": ("r.uint16()", "w.uint16"),
    "Int16": ("r.int16()", "w.int16"),
    "Uint32": ("r.uint32()", "w.uint32"),
    "Int32": ("r.int32()", "w.int32"),
    "Uint64": ("r.uint64()", "w.uint64"),
    "Int64": ("r.int64()", "w.int64"),
    "Varuint32": ("r.varuint32()", "w.varuint32"),
    "Varint32": ("r.varint32()", "w.varint32"),
    "Varuint64": ("r.varuint64()", "w.varuint64"),
    "Varint64": ("r.varint64()", "w.varint64"),
    "Float32": ("r.float32()", "w.float32"),
    "Float64": ("r.float64()", "w.float64"),
    "Bool": ("r.bool()", "w.bool"),
    "String": ("r.string()", "w.string"),
    "StringUTF": ("r.string_utf()", "w.string_utf"),
    "UUID": ("r.uuid()", "w.uuid"),
    "Vec3": ("r.vec3()", "w.vec3"),
    "Vec2": ("r.vec2()", "w.vec2"),
    "BlockPos": ("r.block_pos()", "w.block_pos"),
    "ChunkPos": ("r.chunk_pos()", "w.chunk_pos"),
    "SubChunkPos": ("r.sub_chunk_pos()", "w.sub_chunk_pos"),
    "ByteSlice": ("r.byte_slice()", "w.byte_slice"),
    "Bytes": ("r.bytes_remaining()", "w.bytes_raw"),
    "BEInt32": ("r.be_int32()", "w.be_int32"),
    "ByteFloat": ("r.byte_float()", "w.byte_float"),
    "NBT": ("r.nbt()", "w.nbt"),
    "NBTList": ("r.nbt()", "w.nbt"),
}

# Python type for IO methods.
IO_METHOD_PYTYPE: dict[str, str] = {
    "Uint8": "int", "Int8": "int", "Uint16": "int", "Int16": "int",
    "Uint32": "int", "Int32": "int", "Uint64": "int", "Int64": "int",
    "Varuint32": "int", "Varint32": "int", "Varuint64": "int", "Varint64": "int",
    "Float32": "float", "Float64": "float", "Bool": "bool", "String": "str",
    "StringUTF": "str", "UUID": "UUID", "Vec3": "Vec3", "Vec2": "Vec2",
    "BlockPos": "BlockPos", "ChunkPos": "ChunkPos", "SubChunkPos": "SubChunkPos",
    "ByteSlice": "bytes", "Bytes": "bytes", "BEInt32": "int",
    "ByteFloat": "float", "NBT": "dict", "NBTList": "dict",
}

IO_METHOD_DEFAULT: dict[str, str] = {
    "Uint8": "0", "Int8": "0", "Uint16": "0", "Int16": "0",
    "Uint32": "0", "Int32": "0", "Uint64": "0", "Int64": "0",
    "Varuint32": "0", "Varint32": "0", "Varuint64": "0", "Varint64": "0",
    "Float32": "0.0", "Float64": "0.0", "Bool": "False", "String": '""',
    "StringUTF": '""', "ByteSlice": 'b""', "Bytes": 'b""', "BEInt32": "0",
    "ByteFloat": "0.0", "NBT": "field(default_factory=dict)",
    "NBTList": "field(default_factory=dict)",
}


@dataclass
class GoField:
    """A field from a Go struct."""
    name: str  # Go name (PascalCase)
    go_type: str
    io_method: str = ""  # IO method used in Marshal


@dataclass
class GoPacket:
    """A parsed Go packet definition."""
    name: str  # Go struct name
    file_name: str
    fields: list[GoField] = field(default_factory=list)
    has_conditional: bool = False  # Has switch/if in Marshal
    marshal_body: str = ""


def go_to_snake(name: str) -> str:
    """Convert PascalCase/camelCase to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def parse_go_file(filepath: Path) -> GoPacket | None:
    """Parse a Go packet file and extract struct + Marshal info."""
    content = filepath.read_text()

    # Find the main struct.
    struct_match = re.search(
        r"type\s+(\w+)\s+struct\s*\{([^}]*)\}", content, re.DOTALL
    )
    if not struct_match:
        return None

    name = struct_match.group(1)
    struct_body = struct_match.group(2)

    # Check if it has an ID method (is a packet).
    if not re.search(r"func\s+\(\*?" + name + r"\)\s+ID\(\)", content):
        return None

    # Parse fields.
    fields: list[GoField] = []
    for line in struct_body.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("_"):
            continue

        # Handle grouped fields: "Pitch, Yaw, HeadYaw float32"
        parts = re.match(r"([\w,\s]+?)\s+([\w.\[\]]+)(?:\s+.*)?$", line)
        if not parts:
            continue

        field_names = [n.strip() for n in parts.group(1).split(",")]
        go_type = parts.group(2).strip()

        for fn in field_names:
            if fn and fn[0].isupper():  # Only exported fields
                fields.append(GoField(name=fn, go_type=go_type))

    # Find Marshal method.
    marshal_match = re.search(
        r"func\s+\(pk\s+\*" + name + r"\)\s+Marshal\(io\s+protocol\.IO\)\s*\{",
        content,
    )

    has_conditional = False
    marshal_body = ""
    if marshal_match:
        # Extract marshal body by counting braces.
        start = marshal_match.end()
        depth = 1
        i = start
        while i < len(content) and depth > 0:
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1
        marshal_body = content[start : i - 1].strip()

        # Check for conditionals.
        has_conditional = bool(
            re.search(r"\bswitch\b|\bif\b.*\{", marshal_body)
        )

        # Extract IO method calls for each field.
        for f in fields:
            # Look for io.MethodName(&pk.FieldName) pattern.
            pat = re.search(
                r"io\.(\w+)\(&pk\." + f.name + r"(?:\)|,)",
                marshal_body,
            )
            if pat:
                f.io_method = pat.group(1)

    return GoPacket(
        name=name,
        file_name=filepath.stem,
        fields=fields,
        has_conditional=has_conditional,
        marshal_body=marshal_body,
    )


def generate_python(packet: GoPacket, id_constant: str) -> str:
    """Generate Python source code for a packet."""
    snake_name = go_to_snake(packet.name)
    module_name = snake_name

    # Collect imports needed.
    needs_field = False
    needs_uuid = False
    needs_types: set[str] = set()

    # Generate field definitions and read/write lines.
    field_defs: list[str] = []
    write_lines: list[str] = []
    read_args: list[str] = []

    for f in packet.fields:
        py_name = go_to_snake(f.name)
        io_method = f.io_method

        if io_method and io_method in IO_METHOD_MAP:
            reader, writer = IO_METHOD_MAP[io_method]
            py_type = IO_METHOD_PYTYPE.get(io_method, "int")
            default = IO_METHOD_DEFAULT.get(io_method, "0")
        elif f.go_type in TYPE_MAP:
            py_type, reader, writer, default = TYPE_MAP[f.go_type]
        else:
            # Unsupported type — use bytes placeholder.
            py_type = "bytes"
            reader = "r.byte_slice()"
            writer = "w.byte_slice"
            default = 'b""'

        # Check for special types.
        if py_type == "UUID":
            needs_uuid = True
        if "field(" in default:
            needs_field = True
        if py_type in ("Vec3", "Vec2", "BlockPos", "ChunkPos", "SubChunkPos"):
            needs_types.add(py_type)
            needs_field = True

        field_defs.append(f"    {py_name}: {py_type} = {default}")

        # Writer: w.method(self.field)
        write_lines.append(f"        {writer}(self.{py_name})")

        # Reader: field=r.method()
        read_args.append(f"            {py_name}={reader},")

    # Build imports.
    imports = ["from __future__ import annotations\n"]
    imports.append("from dataclasses import dataclass")
    if needs_field:
        imports[-1] = "from dataclasses import dataclass, field"
    if needs_uuid:
        imports.append("from uuid import UUID")
    imports.append("")
    imports.append("from pymc.proto.io import PacketReader, PacketWriter")
    imports.append(f"from pymc.proto.packet import {id_constant}")

    # Determine registration decorator.
    # Default to server_packet; can be adjusted manually.
    reg_import = "register_server_packet"
    reg_decorator = "@register_server_packet"
    imports.append(f"from pymc.proto.pool import Packet, {reg_import}")

    if needs_types:
        type_list = ", ".join(sorted(needs_types))
        imports.append(f"from pymc.proto.types import {type_list}")

    # Build class.
    lines = [
        f'"""Packet: {packet.name}."""',
        "",
        *imports,
        "",
    ]

    if packet.has_conditional:
        lines.append(f"# NOTE: This packet has conditional fields in Go.")
        lines.append(f"# Manual review required for correct implementation.")
        lines.append("")

    lines.extend([
        "",
        reg_decorator,
        "@dataclass",
        f"class {packet.name}(Packet):",
        f"    packet_id = {id_constant}",
    ])

    if not field_defs:
        lines.append("    pass")
    else:
        lines.extend(field_defs)

    lines.append("")

    # Write method.
    lines.append("    def write(self, w: PacketWriter) -> None:")
    if write_lines:
        lines.extend(write_lines)
    else:
        lines.append("        pass")

    lines.append("")

    # Read method.
    lines.append("    @classmethod")
    lines.append(f"    def read(cls, r: PacketReader) -> {packet.name}:")
    if read_args:
        lines.append("        return cls(")
        lines.extend(read_args)
        lines.append("        )")
    else:
        lines.append("        return cls()")

    lines.append("")
    return "\n".join(lines)


def get_id_constant(go_name: str) -> str:
    """Convert Go packet name to ID constant name."""
    return "ID_" + go_to_snake(go_name).upper()


def main():
    parser = argparse.ArgumentParser(description="Generate Python packets from Go source")
    parser.add_argument(
        "--go-dir",
        default="/Users/11084486/Documents/mc/gophertunnel/minecraft/protocol/packet",
        help="Go packet source directory",
    )
    parser.add_argument(
        "--out-dir",
        default="/Users/11084486/Documents/mc/pymc/src/pymc/proto/packet",
        help="Python output directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    go_dir = Path(args.go_dir)
    out_dir = Path(args.out_dir)

    if not go_dir.is_dir():
        print(f"Error: Go directory not found: {go_dir}", file=sys.stderr)
        sys.exit(1)

    # Read existing packet ID constants.
    init_file = out_dir / "__init__.py"
    id_constants: set[str] = set()
    if init_file.exists():
        for line in init_file.read_text().split("\n"):
            m = re.match(r"(ID_\w+)\s*=", line)
            if m:
                id_constants.add(m.group(1))

    # Get existing Python packet files.
    existing_py = {f.stem for f in out_dir.glob("*.py") if f.stem != "__init__"}

    stats = {"generated": 0, "skipped_exists": 0, "skipped_manual": 0,
             "conditional": 0, "failed": 0}

    for go_file in sorted(go_dir.glob("*.go")):
        if go_file.name in SKIP_FILES:
            stats["skipped_manual"] += 1
            continue

        if go_file.name.endswith("_test.go"):
            continue

        packet = parse_go_file(go_file)
        if packet is None:
            continue

        py_filename = go_to_snake(packet.name)

        # Skip if already exists.
        if py_filename in existing_py:
            stats["skipped_exists"] += 1
            if args.verbose:
                print(f"  skip (exists): {py_filename}.py")
            continue

        # Check if ID constant exists.
        id_const = get_id_constant(packet.name)
        if id_const not in id_constants:
            if args.verbose:
                print(f"  skip (no ID): {packet.name} → {id_const}")
            stats["failed"] += 1
            continue

        # Generate Python code.
        try:
            code = generate_python(packet, id_const)
        except Exception as e:
            print(f"  error: {packet.name}: {e}", file=sys.stderr)
            stats["failed"] += 1
            continue

        if packet.has_conditional:
            stats["conditional"] += 1

        out_path = out_dir / f"{py_filename}.py"
        if args.dry_run:
            print(f"  would generate: {out_path.name} ({len(packet.fields)} fields)"
                  f"{' [CONDITIONAL]' if packet.has_conditional else ''}")
        else:
            out_path.write_text(code)
            if args.verbose:
                print(f"  generated: {out_path.name} ({len(packet.fields)} fields)"
                      f"{' [CONDITIONAL]' if packet.has_conditional else ''}")

        stats["generated"] += 1

    print(f"\nResults:")
    print(f"  Generated: {stats['generated']}")
    print(f"  Skipped (manual): {stats['skipped_manual']}")
    print(f"  Skipped (exists): {stats['skipped_exists']}")
    print(f"  Conditional (needs review): {stats['conditional']}")
    print(f"  Failed/no ID: {stats['failed']}")


if __name__ == "__main__":
    main()
