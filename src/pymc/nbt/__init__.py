"""NBT (Named Binary Tag) serialization for Minecraft.

Supports three encoding variants:
- NetworkLittleEndian: varint-based, used for network protocol
- LittleEndian: fixed-size, used for world saves (Bedrock Edition)
- BigEndian: fixed-size, used for Java Edition
"""

from pymc.nbt.codec import decode, encode
from pymc.nbt.encoding import BigEndian, LittleEndian, NetworkLittleEndian

__all__ = [
    "decode",
    "encode",
    "NetworkLittleEndian",
    "LittleEndian",
    "BigEndian",
]
