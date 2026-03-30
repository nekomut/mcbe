"""NBT encoding variants for different byte orderings and varint formats."""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from io import BytesIO


class Encoding(ABC):
    """Base class for NBT encoding variants."""

    @abstractmethod
    def read_int16(self, buf: BytesIO) -> int: ...
    @abstractmethod
    def read_int32(self, buf: BytesIO) -> int: ...
    @abstractmethod
    def read_int64(self, buf: BytesIO) -> int: ...
    @abstractmethod
    def read_float32(self, buf: BytesIO) -> float: ...
    @abstractmethod
    def read_float64(self, buf: BytesIO) -> float: ...
    @abstractmethod
    def read_string(self, buf: BytesIO) -> str: ...
    @abstractmethod
    def read_int32_slice(self, buf: BytesIO) -> list[int]: ...
    @abstractmethod
    def read_int64_slice(self, buf: BytesIO) -> list[int]: ...

    @abstractmethod
    def write_int16(self, buf: BytesIO, v: int) -> None: ...
    @abstractmethod
    def write_int32(self, buf: BytesIO, v: int) -> None: ...
    @abstractmethod
    def write_int64(self, buf: BytesIO, v: int) -> None: ...
    @abstractmethod
    def write_float32(self, buf: BytesIO, v: float) -> None: ...
    @abstractmethod
    def write_float64(self, buf: BytesIO, v: float) -> None: ...
    @abstractmethod
    def write_string(self, buf: BytesIO, v: str) -> None: ...


class _LittleEndian(Encoding):
    """Fixed-size little-endian NBT encoding (used for world saves)."""

    def read_int16(self, buf: BytesIO) -> int:
        return struct.unpack("<h", buf.read(2))[0]

    def read_int32(self, buf: BytesIO) -> int:
        return struct.unpack("<i", buf.read(4))[0]

    def read_int64(self, buf: BytesIO) -> int:
        return struct.unpack("<q", buf.read(8))[0]

    def read_float32(self, buf: BytesIO) -> float:
        return struct.unpack("<f", buf.read(4))[0]

    def read_float64(self, buf: BytesIO) -> float:
        return struct.unpack("<d", buf.read(8))[0]

    def read_string(self, buf: BytesIO) -> str:
        length = struct.unpack("<H", buf.read(2))[0]
        return buf.read(length).decode("utf-8")

    def read_int32_slice(self, buf: BytesIO) -> list[int]:
        n = self.read_int32(buf)
        return [self.read_int32(buf) for _ in range(n)]

    def read_int64_slice(self, buf: BytesIO) -> list[int]:
        n = self.read_int32(buf)
        return [self.read_int64(buf) for _ in range(n)]

    def write_int16(self, buf: BytesIO, v: int) -> None:
        buf.write(struct.pack("<h", v))

    def write_int32(self, buf: BytesIO, v: int) -> None:
        buf.write(struct.pack("<i", v))

    def write_int64(self, buf: BytesIO, v: int) -> None:
        buf.write(struct.pack("<q", v))

    def write_float32(self, buf: BytesIO, v: float) -> None:
        buf.write(struct.pack("<f", v))

    def write_float64(self, buf: BytesIO, v: float) -> None:
        buf.write(struct.pack("<d", v))

    def write_string(self, buf: BytesIO, v: str) -> None:
        encoded = v.encode("utf-8")
        buf.write(struct.pack("<H", len(encoded)))
        buf.write(encoded)


class _NetworkLittleEndian(_LittleEndian):
    """Variable-size integer (varint) little-endian NBT encoding (used for network)."""

    def read_int32(self, buf: BytesIO) -> int:
        ux = 0
        for i in range(0, 35, 7):
            b = buf.read(1)
            if len(b) == 0:
                raise EOFError("unexpected end of data reading varint32")
            b = b[0]
            ux |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                x = ux >> 1
                if ux & 1:
                    x = ~x
                # Convert to signed 32-bit
                if x > 0x7FFFFFFF:
                    x -= 0x100000000
                return x
        raise ValueError("varint32 overflows")

    def read_int64(self, buf: BytesIO) -> int:
        ux = 0
        for i in range(0, 70, 7):
            b = buf.read(1)
            if len(b) == 0:
                raise EOFError("unexpected end of data reading varint64")
            b = b[0]
            ux |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                x = ux >> 1
                if ux & 1:
                    x = ~x
                return x
        raise ValueError("varint64 overflows")

    def read_string(self, buf: BytesIO) -> str:
        length = self._read_varuint32(buf)
        if length > 0x7FFF:
            raise ValueError("string too long")
        return buf.read(length).decode("utf-8")

    def read_int32_slice(self, buf: BytesIO) -> list[int]:
        n = self.read_int32(buf)
        return [self.read_int32(buf) for _ in range(n)]

    def read_int64_slice(self, buf: BytesIO) -> list[int]:
        n = self.read_int32(buf)
        return [self.read_int64(buf) for _ in range(n)]

    def write_int32(self, buf: BytesIO, v: int) -> None:
        # Zigzag encode
        ux = (v << 1) ^ (v >> 31)
        ux &= 0xFFFFFFFF
        while ux >= 0x80:
            buf.write(bytes([(ux & 0x7F) | 0x80]))
            ux >>= 7
        buf.write(bytes([ux]))

    def write_int64(self, buf: BytesIO, v: int) -> None:
        ux = (v << 1) ^ (v >> 63)
        ux &= 0xFFFFFFFFFFFFFFFF
        while ux >= 0x80:
            buf.write(bytes([(ux & 0x7F) | 0x80]))
            ux >>= 7
        buf.write(bytes([ux]))

    def write_string(self, buf: BytesIO, v: str) -> None:
        encoded = v.encode("utf-8")
        if len(encoded) > 0x7FFF:
            raise ValueError("string too long")
        self._write_varuint32(buf, len(encoded))
        buf.write(encoded)

    @staticmethod
    def _read_varuint32(buf: BytesIO) -> int:
        result = 0
        for i in range(0, 35, 7):
            b = buf.read(1)
            if len(b) == 0:
                raise EOFError("unexpected end of data reading varuint32")
            b = b[0]
            result |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                return result
        raise ValueError("varuint32 overflows")

    @staticmethod
    def _write_varuint32(buf: BytesIO, v: int) -> None:
        v &= 0xFFFFFFFF
        while v >= 0x80:
            buf.write(bytes([(v & 0x7F) | 0x80]))
            v >>= 7
        buf.write(bytes([v]))


class _BigEndian(Encoding):
    """Fixed-size big-endian NBT encoding (used for Java Edition)."""

    def read_int16(self, buf: BytesIO) -> int:
        return struct.unpack(">h", buf.read(2))[0]

    def read_int32(self, buf: BytesIO) -> int:
        return struct.unpack(">i", buf.read(4))[0]

    def read_int64(self, buf: BytesIO) -> int:
        return struct.unpack(">q", buf.read(8))[0]

    def read_float32(self, buf: BytesIO) -> float:
        return struct.unpack(">f", buf.read(4))[0]

    def read_float64(self, buf: BytesIO) -> float:
        return struct.unpack(">d", buf.read(8))[0]

    def read_string(self, buf: BytesIO) -> str:
        length = struct.unpack(">H", buf.read(2))[0]
        return buf.read(length).decode("utf-8")

    def read_int32_slice(self, buf: BytesIO) -> list[int]:
        n = self.read_int32(buf)
        return [self.read_int32(buf) for _ in range(n)]

    def read_int64_slice(self, buf: BytesIO) -> list[int]:
        n = self.read_int32(buf)
        return [self.read_int64(buf) for _ in range(n)]

    def write_int16(self, buf: BytesIO, v: int) -> None:
        buf.write(struct.pack(">h", v))

    def write_int32(self, buf: BytesIO, v: int) -> None:
        buf.write(struct.pack(">i", v))

    def write_int64(self, buf: BytesIO, v: int) -> None:
        buf.write(struct.pack(">q", v))

    def write_float32(self, buf: BytesIO, v: float) -> None:
        buf.write(struct.pack(">f", v))

    def write_float64(self, buf: BytesIO, v: float) -> None:
        buf.write(struct.pack(">d", v))

    def write_string(self, buf: BytesIO, v: str) -> None:
        encoded = v.encode("utf-8")
        buf.write(struct.pack(">H", len(encoded)))
        buf.write(encoded)


# Singleton instances
NetworkLittleEndian = _NetworkLittleEndian()
LittleEndian = _LittleEndian()
BigEndian = _BigEndian()
