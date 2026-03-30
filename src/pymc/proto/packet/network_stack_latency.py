"""Packet: NetworkStackLatency."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_NETWORK_STACK_LATENCY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class NetworkStackLatency(Packet):
    packet_id = ID_NETWORK_STACK_LATENCY
    timestamp: int = 0
    needs_response: bool = False

    def write(self, w: PacketWriter) -> None:
        w.int64(self.timestamp)
        w.bool(self.needs_response)

    @classmethod
    def read(cls, r: PacketReader) -> NetworkStackLatency:
        return cls(
            timestamp=r.int64(),
            needs_response=r.bool(),
        )
