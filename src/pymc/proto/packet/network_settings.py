"""NetworkSettings packet - server responds with compression settings."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_NETWORK_SETTINGS
from pymc.proto.pool import Packet, register_server_packet

COMPRESSION_FLATE = 0
COMPRESSION_SNAPPY = 1
COMPRESSION_NONE = 0xFFFF


@register_server_packet
@dataclass
class NetworkSettings(Packet):
    packet_id = ID_NETWORK_SETTINGS
    compression_threshold: int = 0
    compression_algorithm: int = 0
    client_throttle: bool = False
    client_throttle_threshold: int = 0
    client_throttle_scalar: float = 0.0

    def write(self, w: PacketWriter) -> None:
        w.uint16(self.compression_threshold)
        w.uint16(self.compression_algorithm)
        w.bool(self.client_throttle)
        w.uint8(self.client_throttle_threshold)
        w.float32(self.client_throttle_scalar)

    @classmethod
    def read(cls, r: PacketReader) -> NetworkSettings:
        return cls(
            compression_threshold=r.uint16(),
            compression_algorithm=r.uint16(),
            client_throttle=r.bool(),
            client_throttle_threshold=r.uint8(),
            client_throttle_scalar=r.float32(),
        )
