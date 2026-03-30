"""Packet: SyncWorldClocks.

Complex sub-structures (SyncWorldClockStateData, WorldClockData,
TimeMarkerData) are kept as raw bytes. The conditional switch on
PayloadType is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SYNC_WORLD_CLOCKS
from pymc.proto.pool import Packet, register_server_packet

CLOCK_PAYLOAD_TYPE_SYNC_STATE = 0
CLOCK_PAYLOAD_TYPE_INITIALIZE_REGISTRY = 1
CLOCK_PAYLOAD_TYPE_ADD_TIME_MARKER = 2
CLOCK_PAYLOAD_TYPE_REMOVE_TIME_MARKER = 3


@register_server_packet
@dataclass
class SyncWorldClocks(Packet):
    packet_id = ID_SYNC_WORLD_CLOCKS
    payload_type: int = 0
    sync_states: bytes = b""
    clocks: bytes = b""
    add_clock_id: int = 0
    add_time_markers: bytes = b""
    remove_clock_id: int = 0
    remove_time_marker_ids: list[int] = field(default_factory=list)

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.payload_type)
        if self.payload_type == CLOCK_PAYLOAD_TYPE_SYNC_STATE:
            w.bytes_raw(self.sync_states)
        elif self.payload_type == CLOCK_PAYLOAD_TYPE_INITIALIZE_REGISTRY:
            w.bytes_raw(self.clocks)
        elif self.payload_type == CLOCK_PAYLOAD_TYPE_ADD_TIME_MARKER:
            w.varuint64(self.add_clock_id)
            w.bytes_raw(self.add_time_markers)
        elif self.payload_type == CLOCK_PAYLOAD_TYPE_REMOVE_TIME_MARKER:
            w.varuint64(self.remove_clock_id)
            w.varuint32(len(self.remove_time_marker_ids))
            for mid in self.remove_time_marker_ids:
                w.varuint64(mid)

    @classmethod
    def read(cls, r: PacketReader) -> SyncWorldClocks:
        payload_type = r.varuint32()
        sync_states = b""
        clocks = b""
        add_clock_id = 0
        add_time_markers = b""
        remove_clock_id = 0
        remove_time_marker_ids: list[int] = []

        if payload_type == CLOCK_PAYLOAD_TYPE_SYNC_STATE:
            sync_states = r.bytes_remaining()
        elif payload_type == CLOCK_PAYLOAD_TYPE_INITIALIZE_REGISTRY:
            clocks = r.bytes_remaining()
        elif payload_type == CLOCK_PAYLOAD_TYPE_ADD_TIME_MARKER:
            add_clock_id = r.varuint64()
            add_time_markers = r.bytes_remaining()
        elif payload_type == CLOCK_PAYLOAD_TYPE_REMOVE_TIME_MARKER:
            remove_clock_id = r.varuint64()
            count = r.varuint32()
            remove_time_marker_ids = [r.varuint64() for _ in range(count)]

        return cls(
            payload_type=payload_type,
            sync_states=sync_states,
            clocks=clocks,
            add_clock_id=add_clock_id,
            add_time_markers=add_time_markers,
            remove_clock_id=remove_clock_id,
            remove_time_marker_ids=remove_time_marker_ids,
        )
