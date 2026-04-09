"""Sub-chunk parsing for Minecraft Bedrock Edition.

Decodes the palette-based block storage format used in LevelChunk
and SubChunk packets. Only extracts the top-most non-air block at
each (x, z) column for map rendering.
"""

from __future__ import annotations

import logging
import struct
from io import BytesIO

logger = logging.getLogger(__name__)

AIR = "minecraft:air"

# ── FNV-1a 32-bit ──────────────────────────────────────────────

_FNV1A_OFFSET = 0x811C9DC5
_FNV1A_PRIME = 0x01000193
_MASK32 = 0xFFFFFFFF


def _fnv1a_32(data: bytes) -> int:
    """Compute FNV-1a 32-bit hash."""
    h = _FNV1A_OFFSET
    for b in data:
        h = ((h ^ b) * _FNV1A_PRIME) & _MASK32
    return h


# ── NBT type-preserving decode/encode for hash computation ─────
#
# Block network ID hashes are FNV-1a of the block state compound
# serialized with *LittleEndian* NBT (fixed-size int16 string lengths,
# fixed int32/int64).  Sub-chunk palette NBT is *NetworkLittleEndian*
# (varuint32 string lengths, zigzag varint ints).
#
# We need to decode NLE, then re-encode as LE with sorted keys,
# preserving the original tag types (TAG_INT vs TAG_BYTE matters).

_TAG_END = 0
_TAG_BYTE = 1
_TAG_SHORT = 2
_TAG_INT = 3
_TAG_LONG = 4
_TAG_FLOAT = 5
_TAG_DOUBLE = 6
_TAG_BYTE_ARRAY = 7
_TAG_STRING = 8
_TAG_LIST = 9
_TAG_COMPOUND = 10
_TAG_INT_ARRAY = 11
_TAG_LONG_ARRAY = 12


def _nle_read_varuint32(buf: BytesIO) -> int:
    result = 0
    for i in range(0, 35, 7):
        b = buf.read(1)
        if not b:
            raise EOFError
        b = b[0]
        result |= (b & 0x7F) << i
        if (b & 0x80) == 0:
            return result
    raise ValueError("varuint32 overflow")


def _nle_read_zigzag32(buf: BytesIO) -> int:
    ux = 0
    for i in range(0, 35, 7):
        b = buf.read(1)
        if not b:
            raise EOFError
        b = b[0]
        ux |= (b & 0x7F) << i
        if (b & 0x80) == 0:
            x = ux >> 1
            if ux & 1:
                x = ~x
            if x > 0x7FFFFFFF:
                x -= 0x100000000
            return x
    raise ValueError("zigzag32 overflow")


def _nle_read_string(buf: BytesIO) -> str:
    length = _nle_read_varuint32(buf)
    return buf.read(length).decode("utf-8")


def _decode_typed(buf: BytesIO, tag_type: int):
    """Decode a single NBT value preserving its tag type.

    Returns ``(tag_type, value)`` where value depends on tag_type.
    TAG_COMPOUND values are ``dict[str, (int, Any)]``.
    """
    if tag_type == _TAG_BYTE:
        return buf.read(1)[0]
    elif tag_type == _TAG_SHORT:
        return struct.unpack_from("<h", buf.read(2))[0]
    elif tag_type == _TAG_INT:
        return _nle_read_zigzag32(buf)
    elif tag_type == _TAG_LONG:
        # zigzag64
        ux = 0
        for i in range(0, 70, 7):
            b = buf.read(1)[0]
            ux |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                x = ux >> 1
                if ux & 1:
                    x = ~x
                return x
        raise ValueError("zigzag64 overflow")
    elif tag_type == _TAG_FLOAT:
        return struct.unpack_from("<f", buf.read(4))[0]
    elif tag_type == _TAG_DOUBLE:
        return struct.unpack_from("<d", buf.read(8))[0]
    elif tag_type == _TAG_STRING:
        return _nle_read_string(buf)
    elif tag_type == _TAG_COMPOUND:
        fields: dict[str, tuple[int, object]] = {}
        while True:
            child_type = buf.read(1)[0]
            if child_type == _TAG_END:
                break
            name = _nle_read_string(buf)
            fields[name] = (child_type, _decode_typed(buf, child_type))
        return fields
    elif tag_type == _TAG_LIST:
        elem_type = buf.read(1)[0]
        n = _nle_read_zigzag32(buf)
        return (elem_type, [_decode_typed(buf, elem_type) for _ in range(max(0, n))])
    elif tag_type == _TAG_BYTE_ARRAY:
        n = _nle_read_zigzag32(buf)
        return buf.read(n)
    elif tag_type == _TAG_INT_ARRAY:
        n = _nle_read_zigzag32(buf)
        return [_nle_read_zigzag32(buf) for _ in range(n)]
    elif tag_type == _TAG_LONG_ARRAY:
        n = _nle_read_zigzag32(buf)
        vals = []
        for _ in range(n):
            ux = 0
            for i in range(0, 70, 7):
                b = buf.read(1)[0]
                ux |= (b & 0x7F) << i
                if (b & 0x80) == 0:
                    x = ux >> 1
                    if ux & 1:
                        x = ~x
                    vals.append(x)
                    break
        return vals
    else:
        raise ValueError(f"unsupported tag type: {tag_type}")


def _le_write_string(buf: BytesIO, s: str) -> None:
    encoded = s.encode("utf-8")
    buf.write(struct.pack("<H", len(encoded)))
    buf.write(encoded)


def _le_encode_typed(buf: BytesIO, tag_type: int, value) -> None:
    """Encode a typed NBT value to LittleEndian format."""
    if tag_type == _TAG_BYTE:
        buf.write(bytes([value & 0xFF]))
    elif tag_type == _TAG_SHORT:
        buf.write(struct.pack("<h", value))
    elif tag_type == _TAG_INT:
        buf.write(struct.pack("<i", value))
    elif tag_type == _TAG_LONG:
        buf.write(struct.pack("<q", value))
    elif tag_type == _TAG_FLOAT:
        buf.write(struct.pack("<f", value))
    elif tag_type == _TAG_DOUBLE:
        buf.write(struct.pack("<d", value))
    elif tag_type == _TAG_STRING:
        _le_write_string(buf, value)
    elif tag_type == _TAG_COMPOUND:
        for key in sorted(value.keys()):
            child_type, child_val = value[key]
            buf.write(bytes([child_type]))
            _le_write_string(buf, key)
            _le_encode_typed(buf, child_type, child_val)
        buf.write(bytes([_TAG_END]))
    elif tag_type == _TAG_LIST:
        elem_type, items = value
        buf.write(bytes([elem_type]))
        buf.write(struct.pack("<i", len(items)))
        for item in items:
            _le_encode_typed(buf, elem_type, item)
    elif tag_type == _TAG_BYTE_ARRAY:
        buf.write(struct.pack("<i", len(value)))
        buf.write(value)
    elif tag_type == _TAG_INT_ARRAY:
        buf.write(struct.pack("<i", len(value)))
        for v in value:
            buf.write(struct.pack("<i", v))
    elif tag_type == _TAG_LONG_ARRAY:
        buf.write(struct.pack("<i", len(value)))
        for v in value:
            buf.write(struct.pack("<q", v))


def _block_state_to_le_bytes(fields: dict[str, tuple[int, object]]) -> bytes:
    """Encode a typed compound to LittleEndian NBT bytes (root compound)."""
    buf = BytesIO()
    buf.write(bytes([_TAG_COMPOUND]))
    buf.write(b"\x00\x00")  # root name = "" (uint16 LE)
    for key in sorted(fields.keys()):
        child_type, child_val = fields[key]
        buf.write(bytes([child_type]))
        _le_write_string(buf, key)
        _le_encode_typed(buf, child_type, child_val)
    buf.write(bytes([_TAG_END]))
    return buf.getvalue()


def compute_block_hash(name: str, states: dict | None = None) -> int:
    """Compute FNV-1a 32-bit block network ID hash.

    Uses smart type inference for state properties:
    - ``str`` values → TAG_STRING
    - ``int`` values with key ending in ``_bit`` → TAG_BYTE
    - other ``int`` values → TAG_INT

    This matches the server's hash computation (LittleEndian NBT,
    sorted keys).
    """
    states_fields: dict[str, tuple[int, object]] = {}
    if states:
        for key, value in states.items():
            if isinstance(value, str):
                states_fields[key] = (_TAG_STRING, value)
            elif isinstance(value, int):
                if key.endswith("_bit"):
                    states_fields[key] = (_TAG_BYTE, value)
                else:
                    states_fields[key] = (_TAG_INT, value)
            elif isinstance(value, float):
                states_fields[key] = (_TAG_FLOAT, value)
            else:
                states_fields[key] = (_TAG_BYTE, int(value))

    fields: dict[str, tuple[int, object]] = {
        "name": (_TAG_STRING, name),
        "states": (_TAG_COMPOUND, states_fields),
    }
    le_bytes = _block_state_to_le_bytes(fields)
    return _fnv1a_32(le_bytes)


def compute_block_hash_typed(
    name: str,
    states_typed: dict[str, tuple[int, object]] | None = None,
) -> int:
    """Compute FNV-1a 32-bit block network ID hash from type-preserving NBT.

    Unlike :func:`compute_block_hash`, this function uses exact tag types
    from the wire (no heuristic inference), producing hashes that match
    the server's computation.
    """
    fields: dict[str, tuple[int, object]] = {
        "name": (_TAG_STRING, name),
        "states": (_TAG_COMPOUND, states_typed or {}),
    }
    return _fnv1a_32(_block_state_to_le_bytes(fields))


# ── Canonical block state registry ───────────────────────────────

def _get_canonical_path() -> str:
    """Return the path to canonical_block_states.nbt shipped with the package."""
    import os
    return os.path.join(os.path.dirname(__file__), "data", "canonical_block_states.nbt")


def load_canonical_block_hashes() -> dict[int, str]:
    """Load canonical block states and return a hash→block-name table.

    Reads ``canonical_block_states.nbt`` (NLE NBT format from pmmp/BedrockData),
    computes FNV-1a 32-bit hashes over LE NBT for each ``{name, states}`` pair
    (excluding the ``version`` field), and returns the mapping.
    """
    path = _get_canonical_path()
    with open(path, "rb") as f:
        data = f.read()

    buf = BytesIO(data)
    table: dict[int, str] = {}

    while True:
        tag_byte = buf.read(1)
        if not tag_byte or tag_byte[0] != _TAG_COMPOUND:
            break
        _nle_read_string(buf)  # root name (always empty)
        fields = _decode_typed(buf, _TAG_COMPOUND)

        name_entry = fields.get("name")
        states_entry = fields.get("states")
        if not name_entry or name_entry[0] != _TAG_STRING:
            continue

        name: str = name_entry[1]
        states = states_entry[1] if states_entry and states_entry[0] == _TAG_COMPOUND else {}

        if name == "minecraft:unknown":
            table[0xFFFFFFFE] = name
            continue

        hash_fields: dict[str, tuple[int, object]] = {
            "name": (_TAG_STRING, name),
            "states": (_TAG_COMPOUND, states),
        }
        h = _fnv1a_32(_block_state_to_le_bytes(hash_fields))
        table[h] = name

    logger.info("loaded %d canonical block state hashes", len(table))
    return table


# ── Varint / block storage ─────────────────────────────────────


def _read_varint32(data: bytes, offset: int) -> tuple[int, int]:
    """Read a varint32 from *data* at *offset*. Returns (value, new_offset)."""
    result = 0
    for i in range(0, 35, 7):
        if offset >= len(data):
            raise EOFError("unexpected end of data reading varint32")
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << i
        if (b & 0x80) == 0:
            return result & 0xFFFFFFFF, offset
    raise ValueError("varint32 overflows 5 bytes")


def _zigzag_decode(v: int) -> int:
    """Decode a zigzag-encoded varint to a signed int32, then mask to uint32."""
    return ((v >> 1) ^ -(v & 1)) & 0xFFFFFFFF


def _parse_block_storage(
    data: bytes, offset: int,
    hash_table: dict[int, str] | None = None,
) -> tuple[list[int], int, list[str] | None]:
    """Parse one block storage layer.

    Returns ``(palette_indices[4096], new_offset, local_palette_or_None)``.

    When *hash_table* is provided:
    - ``is_runtime=1``: hashes are resolved via the table and returned as
      a local palette (indices remain unchanged).
    - ``is_runtime=0``: each NBT entry is transcoded to LittleEndian,
      hashed, and learned into *hash_table* (mutated in place).
    """
    if offset >= len(data):
        raise EOFError("no storage header")
    header = data[offset]
    offset += 1
    bits_per_block = header >> 1
    is_runtime = header & 1

    if bits_per_block > 16:
        logger.warning(
            "invalid bpb=%d (header=0x%02x) at offset=%d datalen=%d — skipping",
            bits_per_block, header, offset, len(data),
        )
        raise ValueError(f"invalid bits_per_block={bits_per_block}")

    if bits_per_block == 0:
        # Single-block shortcut: palette has exactly 1 entry.
        if is_runtime:
            palette_size, offset = _read_varint32(data, offset)
            if palette_size >= 1:
                single_id, offset = _read_varint32(data, offset)
                for _ in range(palette_size - 1):
                    _, offset = _read_varint32(data, offset)
            else:
                single_id = 0
            if hash_table is not None:
                # Palette values are zigzag-encoded signed int32 hashes.
                name = hash_table.get(_zigzag_decode(single_id), AIR)
                return [0] * 4096, offset, [name]
            return [single_id] * 4096, offset, None
        else:
            # NBT palette with 1 entry.
            palette_size, offset = _read_varint32(data, offset)
            name = AIR
            for i in range(palette_size):
                n, offset = _read_nbt_block(data, offset, hash_table)
                if i == 0:
                    name = n
            return [0] * 4096, offset, [name]

    blocks_per_word = 32 // bits_per_block
    num_words = -(-4096 // blocks_per_word)  # ceil division
    mask = (1 << bits_per_block) - 1

    # Batch-read uint32 words.
    end = offset + num_words * 4
    if end > len(data):
        raise EOFError(f"not enough data for {num_words} words at offset {offset}")
    words = struct.unpack_from(f"<{num_words}I", data, offset)
    offset = end

    # Unpack palette indices from packed words.
    indices = [0] * 4096
    idx = 0
    for word in words:
        for j in range(blocks_per_word):
            if idx >= 4096:
                break
            indices[idx] = (word >> (j * bits_per_block)) & mask
            idx += 1

    # Read palette.
    palette_size, offset = _read_varint32(data, offset)

    if is_runtime:
        palette = [0] * palette_size
        for i in range(palette_size):
            try:
                palette[i], offset = _read_varint32(data, offset)
            except (EOFError, IndexError):
                break
        if hash_table is not None:
            # Palette values are zigzag-encoded signed int32 hashes.
            local_palette = [hash_table.get(_zigzag_decode(rid), AIR) for rid in palette]
            return indices, offset, local_palette
        # Map indices to runtime IDs.
        runtime_ids = [
            palette[i] if i < palette_size else 0
            for i in indices
        ]
        return runtime_ids, offset, None
    else:
        # NBT palette: each entry is a compound with "name" and "states".
        local_palette: list[str] = []
        for _ in range(palette_size):
            name, offset = _read_nbt_block(data, offset, hash_table)
            local_palette.append(name)
        return indices, offset, local_palette


def _read_nbt_block(
    data: bytes, offset: int,
    hash_table: dict[int, str] | None = None,
) -> tuple[str, int]:
    """Read a single NBT block state entry and return (block_name, new_offset).

    When *hash_table* is provided, also computes the LittleEndian FNV-1a hash
    and learns the mapping (mutates *hash_table* in place).
    """
    try:
        buf = BytesIO(data[offset:])
        # Read root compound header.
        root_type = buf.read(1)[0]
        if root_type != _TAG_COMPOUND:
            return AIR, offset + 1
        _root_name = _nle_read_string(buf)
        # Decode compound fields with type preservation.
        fields = _decode_typed(buf, _TAG_COMPOUND)
        consumed = buf.tell()
        new_offset = offset + consumed

        # Extract block name.
        name_entry = fields.get("name")
        if name_entry and name_entry[0] == _TAG_STRING:
            name = name_entry[1]
        else:
            name = AIR

        # Learn hash.
        if hash_table is not None and name != AIR:
            try:
                le_bytes = _block_state_to_le_bytes(fields)
                h = _fnv1a_32(le_bytes)
                hash_table[h] = name
            except Exception:
                pass

        return name, new_offset
    except Exception as e:
        logger.debug("_read_nbt_block error at offset %d: %s", offset, e)
        # Fallback: try legacy codec for robustness.
        try:
            from mcbe.nbt.codec import _decode_root
            from mcbe.nbt.encoding import NetworkLittleEndian
            buf2 = BytesIO(data[offset:])
            tag = _decode_root(buf2, NetworkLittleEndian, allow_zero=False)
            consumed = buf2.tell()
            name = tag.get("name", AIR) if isinstance(tag, dict) else AIR
            return name, offset + consumed
        except Exception:
            return AIR, offset + 1


def parse_sub_chunk(
    data: bytes, offset: int = 0,
    hash_table: dict[int, str] | None = None,
) -> tuple[list[int], int, list[str] | None] | None:
    """Parse a single versioned sub-chunk (layer 0 only).

    Returns ``(ids[4096], bytes_consumed, local_palette_or_None)`` or
    ``None`` on failure.  When *local_palette* is not ``None``, the ids
    are indices into it (NBT palette mode).  Otherwise they are runtime IDs.
    """
    if offset >= len(data):
        return None

    version = data[offset]
    offset += 1

    if version == 1:
        try:
            ids, offset, lp = _parse_block_storage(data, offset, hash_table)
            return ids, offset, lp
        except Exception:
            return None

    if version in (8, 9):
        storage_count = 1
        if version == 9:
            if offset + 1 >= len(data):
                return None
            storage_count = data[offset]
            offset += 1
            # Version 9 includes an absolute Y index byte.
            offset += 1

        if storage_count < 1:
            return None

        try:
            ids, offset, lp = _parse_block_storage(data, offset, hash_table)
        except Exception as e:
            logger.debug("block_storage error: v=%d sc=%d off=%d len=%d: %s",
                         version, storage_count, offset, len(data), e)
            return None

        # Skip remaining layers (waterlog, etc.).
        for _ in range(storage_count - 1):
            try:
                _, offset, _ = _parse_block_storage(data, offset)
            except Exception:
                break

        return ids, offset, lp

    logger.debug("unknown sub-chunk version %d at offset %d", version, offset - 1)
    return None


def parse_level_chunk_top_blocks(
    raw_payload: bytes,
    sub_chunk_count: int,
    block_palette: list[str],
    hash_table: dict[int, str] | None = None,
) -> list[str] | None:
    """Parse a LevelChunk raw_payload and return the top-block map.

    Args:
        raw_payload: The raw chunk payload containing sub-chunk storages.
        sub_chunk_count: Number of sub-chunks in the payload.
        block_palette: The block palette from StartGame (index = runtime ID).
            May be empty when ``use_block_network_id_hashes`` is true (each
            sub-chunk carries its own NBT palette in that case).
        hash_table: Optional FNV-1a hash → block name mapping for resolving
            runtime IDs when ``use_block_network_id_hashes`` is true.

    Returns:
        A list of 256 block names in ``x * 16 + z`` order, or ``None`` on failure.
    """
    if sub_chunk_count <= 0 or not raw_payload:
        return None

    # Parse all sub-chunks.
    sub_chunks: dict[int, tuple[list[int], list[str] | None]] = {}
    offset = 0
    for y_idx in range(sub_chunk_count):
        result = parse_sub_chunk(raw_payload, offset, hash_table)
        if result is None:
            break
        ids, offset, lp = result
        sub_chunks[y_idx] = (ids, lp)

    if not sub_chunks:
        return None

    return _extract_top_blocks(sub_chunks, block_palette, hash_table)


def _extract_top_blocks(
    sub_chunks: dict[int, tuple[list[int], list[str] | None]],
    block_palette: list[str],
    hash_table: dict[int, str] | None = None,
) -> list[str]:
    """Find the topmost non-air block at each (x, z) column.

    Args:
        sub_chunks: Mapping of Y index to ``(ids[4096], local_palette_or_None)``.
        block_palette: Global block palette for name resolution (used when
            *local_palette* is ``None``).
        hash_table: Optional FNV-1a hash → block name mapping.  When provided
            and *local_palette* is ``None``, IDs are treated as hashes and
            looked up in this table instead of the global palette.

    Returns:
        List of 256 block names in ``x * 16 + z`` order.
    """
    global_len = len(block_palette)
    use_hash = hash_table is not None and global_len == 0
    top_blocks = [AIR] * 256
    found = [False] * 256

    for y_idx in sorted(sub_chunks.keys(), reverse=True):
        storage, local_palette = sub_chunks[y_idx]
        if local_palette is not None:
            pal = local_palette
            pal_len = len(pal)
            for x in range(16):
                for z in range(16):
                    col = x * 16 + z
                    if found[col]:
                        continue
                    for y in range(15, -1, -1):
                        rid = storage[(x << 8) | (z << 4) | y]
                        name = pal[rid] if rid < pal_len else AIR
                        if name != AIR:
                            top_blocks[col] = name
                            found[col] = True
                            break
        elif use_hash:
            ht = hash_table
            for x in range(16):
                for z in range(16):
                    col = x * 16 + z
                    if found[col]:
                        continue
                    for y in range(15, -1, -1):
                        h = storage[(x << 8) | (z << 4) | y]
                        name = ht.get(h, AIR)
                        if name != AIR:
                            top_blocks[col] = name
                            found[col] = True
                            break
        else:
            pal = block_palette
            pal_len = global_len
            for x in range(16):
                for z in range(16):
                    col = x * 16 + z
                    if found[col]:
                        continue
                    for y in range(15, -1, -1):
                        rid = storage[(x << 8) | (z << 4) | y]
                        name = pal[rid] if rid < pal_len else AIR
                        if name != AIR:
                            top_blocks[col] = name
                            found[col] = True
                            break

        if all(found):
            break

    return top_blocks


# SubChunk entry result codes.
_SC_RESULT_SUCCESS = 1
_SC_RESULT_SUCCESS_ALL_AIR = 6

# HeightMap type constants (v944+: swapped from gophertunnel).
_HEIGHTMAP_TOO_HIGH = 0
_HEIGHTMAP_HAS_DATA = 1
_HEIGHTMAP_TOO_LOW = 2


def parse_sub_chunk_entries(
    data: bytes,
    cache_enabled: bool,
    hash_table: dict[int, str] | None = None,
) -> list[tuple[tuple[int, int, int], list[int] | None, list[str] | None, int]]:
    """Parse SubChunk packet entries.

    Args:
        data: The raw ``sub_chunk_entries`` bytes from a SubChunk packet.
        cache_enabled: Whether blob caching is enabled.
        hash_table: Optional FNV-1a hash table (mutated to learn new hashes
            from NBT palette entries).

    Returns:
        List of ``((offset_x, offset_y, offset_z), ids_or_None, local_palette_or_None, result_code)``.
    """
    if len(data) < 4:
        return []

    count = struct.unpack_from("<I", data, 0)[0]
    offset = 4

    results: list[tuple[tuple[int, int, int], list[int] | None, list[str] | None, int]] = []

    for entry_i in range(count):
        if offset + 4 > len(data):
            break

        ox = struct.unpack_from("b", data, offset)[0]
        oy = struct.unpack_from("b", data, offset + 1)[0]
        oz = struct.unpack_from("b", data, offset + 2)[0]
        result_code = data[offset + 3]
        offset += 4

        ids: list[int] | None = None
        lp: list[str] | None = None

        # Raw payload: varuint32 length + data.
        # Present on success; absent for all-air when caching.
        has_payload = False
        if not cache_enabled:
            has_payload = True
        elif result_code != _SC_RESULT_SUCCESS_ALL_AIR:
            has_payload = True

        if has_payload:
            data_len, offset = _read_varint32(data, offset)
            sub_data = data[offset:offset + data_len]
            offset += data_len

            if result_code == _SC_RESULT_SUCCESS:
                parsed = parse_sub_chunk(sub_data, hash_table=hash_table)
                if parsed is not None:
                    ids = parsed[0]
                    lp = parsed[2]

        # HeightMapType (uint8) + optional 256-byte heightmap.
        # 0 = TooHigh, 1 = HasData (256 bytes follow), 2 = TooLow.
        if offset < len(data):
            hm_type = data[offset]
            offset += 1
            if hm_type == _HEIGHTMAP_HAS_DATA:
                offset += 256

        # RenderHeightMapType (uint8) + optional 256-byte heightmap.
        if offset < len(data):
            rhm_type = data[offset]
            offset += 1
            if rhm_type == _HEIGHTMAP_HAS_DATA:
                offset += 256

        # Blob hash (uint64 LE) — only when caching enabled.
        if cache_enabled and offset + 8 <= len(data):
            offset += 8

        results.append(((ox, oy, oz), ids, lp, result_code))

    return results
