"""NBT encode/decode implementation.

Works with Python dicts (TAG_Compound), lists (TAG_List), and primitive types.
No reflection needed — Python's dynamic typing handles tag type inference.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from pymc.nbt.encoding import Encoding, NetworkLittleEndian

# Tag type constants
TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


def encode(
    value: Any,
    encoding: Encoding | None = None,
    name: str = "",
) -> bytes:
    """Encode a Python value to NBT bytes.

    Args:
        value: The value to encode. Typically a dict (compound tag).
        encoding: NBT encoding variant. Defaults to NetworkLittleEndian.
        name: Root tag name (usually empty for network NBT).

    Returns:
        Encoded NBT bytes.
    """
    if encoding is None:
        encoding = NetworkLittleEndian
    buf = BytesIO()
    tag_type = _infer_tag_type(value)
    buf.write(bytes([tag_type]))
    encoding.write_string(buf, name)
    _write_payload(buf, encoding, tag_type, value)
    return buf.getvalue()


def decode(
    data: bytes,
    encoding: Encoding | None = None,
    allow_zero: bool = True,
) -> dict[str, Any]:
    """Decode NBT bytes to a Python dict.

    Args:
        data: Raw NBT bytes.
        encoding: NBT encoding variant. Defaults to NetworkLittleEndian.
        allow_zero: If True, a leading TAG_End byte returns an empty dict.

    Returns:
        Decoded compound tag as a dict.
    """
    if encoding is None:
        encoding = NetworkLittleEndian
    buf = BytesIO(data)
    return _decode_root(buf, encoding, allow_zero)


def _decode_root(
    buf: BytesIO, encoding: Encoding, allow_zero: bool
) -> dict[str, Any]:
    tag_type_byte = buf.read(1)
    if len(tag_type_byte) == 0:
        if allow_zero:
            return {}
        raise EOFError("empty NBT data")

    tag_type = tag_type_byte[0]
    if tag_type == TAG_END:
        if allow_zero:
            return {}
        raise ValueError("unexpected TAG_End at root")

    _name = encoding.read_string(buf)
    return _read_payload(buf, encoding, tag_type)


# ── Decoding ──


def _read_payload(buf: BytesIO, enc: Encoding, tag_type: int) -> Any:
    if tag_type == TAG_BYTE:
        b = buf.read(1)
        if len(b) == 0:
            raise EOFError("unexpected end reading TAG_Byte")
        return b[0]
    elif tag_type == TAG_SHORT:
        return enc.read_int16(buf)
    elif tag_type == TAG_INT:
        return enc.read_int32(buf)
    elif tag_type == TAG_LONG:
        return enc.read_int64(buf)
    elif tag_type == TAG_FLOAT:
        return enc.read_float32(buf)
    elif tag_type == TAG_DOUBLE:
        return enc.read_float64(buf)
    elif tag_type == TAG_BYTE_ARRAY:
        length = enc.read_int32(buf)
        return buf.read(length)
    elif tag_type == TAG_STRING:
        return enc.read_string(buf)
    elif tag_type == TAG_LIST:
        return _read_list(buf, enc)
    elif tag_type == TAG_COMPOUND:
        return _read_compound(buf, enc)
    elif tag_type == TAG_INT_ARRAY:
        return enc.read_int32_slice(buf)
    elif tag_type == TAG_LONG_ARRAY:
        return enc.read_int64_slice(buf)
    else:
        raise ValueError(f"unknown tag type: {tag_type}")


def _read_compound(buf: BytesIO, enc: Encoding) -> dict[str, Any]:
    result: dict[str, Any] = {}
    while True:
        tag_type_byte = buf.read(1)
        if len(tag_type_byte) == 0:
            raise EOFError("unexpected end reading compound")
        tag_type = tag_type_byte[0]
        if tag_type == TAG_END:
            break
        name = enc.read_string(buf)
        result[name] = _read_payload(buf, enc, tag_type)
    return result


def _read_list(buf: BytesIO, enc: Encoding) -> list[Any]:
    element_type_byte = buf.read(1)
    if len(element_type_byte) == 0:
        raise EOFError("unexpected end reading list type")
    element_type = element_type_byte[0]
    length = enc.read_int32(buf)
    if length <= 0:
        return []
    return [_read_payload(buf, enc, element_type) for _ in range(length)]


# ── Encoding ──


def _infer_tag_type(value: Any) -> int:
    if isinstance(value, bool):
        return TAG_BYTE
    elif isinstance(value, int):
        if 0 <= value <= 127:
            return TAG_BYTE
        elif -32768 <= value <= 32767:
            return TAG_SHORT
        elif -2147483648 <= value <= 2147483647:
            return TAG_INT
        else:
            return TAG_LONG
    elif isinstance(value, float):
        return TAG_FLOAT
    elif isinstance(value, str):
        return TAG_STRING
    elif isinstance(value, (bytes, bytearray)):
        return TAG_BYTE_ARRAY
    elif isinstance(value, dict):
        return TAG_COMPOUND
    elif isinstance(value, list):
        return TAG_LIST
    else:
        raise TypeError(f"cannot infer NBT tag type for {type(value)}")


def _write_payload(buf: BytesIO, enc: Encoding, tag_type: int, value: Any) -> None:
    if tag_type == TAG_BYTE:
        v = int(value) & 0xFF
        buf.write(bytes([v]))
    elif tag_type == TAG_SHORT:
        enc.write_int16(buf, value)
    elif tag_type == TAG_INT:
        enc.write_int32(buf, value)
    elif tag_type == TAG_LONG:
        enc.write_int64(buf, value)
    elif tag_type == TAG_FLOAT:
        enc.write_float32(buf, value)
    elif tag_type == TAG_DOUBLE:
        enc.write_float64(buf, value)
    elif tag_type == TAG_BYTE_ARRAY:
        enc.write_int32(buf, len(value))
        buf.write(value)
    elif tag_type == TAG_STRING:
        enc.write_string(buf, value)
    elif tag_type == TAG_LIST:
        _write_list(buf, enc, value)
    elif tag_type == TAG_COMPOUND:
        _write_compound(buf, enc, value)
    elif tag_type == TAG_INT_ARRAY:
        enc.write_int32(buf, len(value))
        for item in value:
            enc.write_int32(buf, item)
    elif tag_type == TAG_LONG_ARRAY:
        enc.write_int32(buf, len(value))
        for item in value:
            enc.write_int64(buf, item)
    else:
        raise ValueError(f"unknown tag type: {tag_type}")


def _write_compound(buf: BytesIO, enc: Encoding, d: dict[str, Any]) -> None:
    for key, value in d.items():
        tag_type = _infer_tag_type(value)
        buf.write(bytes([tag_type]))
        enc.write_string(buf, key)
        _write_payload(buf, enc, tag_type, value)
    buf.write(bytes([TAG_END]))


def _write_list(buf: BytesIO, enc: Encoding, items: list[Any]) -> None:
    if len(items) == 0:
        buf.write(bytes([TAG_END]))
        enc.write_int32(buf, 0)
        return
    element_type = _infer_tag_type(items[0])
    buf.write(bytes([element_type]))
    enc.write_int32(buf, len(items))
    for item in items:
        _write_payload(buf, enc, element_type, item)
