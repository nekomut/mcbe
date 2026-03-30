"""Packet: ServerBoundDiagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_BOUND_DIAGNOSTICS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerBoundDiagnostics(Packet):
    packet_id = ID_SERVER_BOUND_DIAGNOSTICS
    average_frames_per_second: float = 0.0
    average_server_sim_tick_time: float = 0.0
    average_client_sim_tick_time: float = 0.0
    average_begin_frame_time: float = 0.0
    average_input_time: float = 0.0
    average_render_time: float = 0.0
    average_end_frame_time: float = 0.0
    average_remainder_time_percent: float = 0.0
    average_unaccounted_time_percent: float = 0.0
    memory_category_values: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.float32(self.average_frames_per_second)
        w.float32(self.average_server_sim_tick_time)
        w.float32(self.average_client_sim_tick_time)
        w.float32(self.average_begin_frame_time)
        w.float32(self.average_input_time)
        w.float32(self.average_render_time)
        w.float32(self.average_end_frame_time)
        w.float32(self.average_remainder_time_percent)
        w.float32(self.average_unaccounted_time_percent)
        w.byte_slice(self.memory_category_values)

    @classmethod
    def read(cls, r: PacketReader) -> ServerBoundDiagnostics:
        return cls(
            average_frames_per_second=r.float32(),
            average_server_sim_tick_time=r.float32(),
            average_client_sim_tick_time=r.float32(),
            average_begin_frame_time=r.float32(),
            average_input_time=r.float32(),
            average_render_time=r.float32(),
            average_end_frame_time=r.float32(),
            average_remainder_time_percent=r.float32(),
            average_unaccounted_time_percent=r.float32(),
            memory_category_values=r.byte_slice(),
        )
