"""Packet: CameraInstruction.

Complex sub-structures (CameraInstructionSet, CameraInstructionFade, etc.)
are kept as raw bytes. The Optional pattern is implemented using
read_optional/write_optional.
"""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_INSTRUCTION
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CameraInstruction(Packet):
    packet_id = ID_CAMERA_INSTRUCTION
    set: bytes | None = None
    clear: bool | None = None
    fade: bytes | None = None
    target: bytes | None = None
    remove_target: bool | None = None
    field_of_view: bytes | None = None
    spline: bytes | None = None
    attach_to_entity: int | None = None
    detach_from_entity: bool | None = None

    def write(self, w: PacketWriter) -> None:
        w.write_optional(self.set, w.bytes_raw)
        w.write_optional(self.clear, w.bool)
        w.write_optional(self.fade, w.bytes_raw)
        w.write_optional(self.target, w.bytes_raw)
        w.write_optional(self.remove_target, w.bool)
        w.write_optional(self.field_of_view, w.bytes_raw)
        w.write_optional(self.spline, w.bytes_raw)
        w.write_optional(self.attach_to_entity, w.int64)
        w.write_optional(self.detach_from_entity, w.bool)

    @classmethod
    def read(cls, r: PacketReader) -> CameraInstruction:
        set_ = r.read_optional(r.bytes_remaining)
        clear = r.read_optional(r.bool)
        fade = r.read_optional(r.bytes_remaining)
        target = r.read_optional(r.bytes_remaining)
        remove_target = r.read_optional(r.bool)
        field_of_view = r.read_optional(r.bytes_remaining)
        spline = r.read_optional(r.bytes_remaining)
        attach_to_entity = r.read_optional(r.int64)
        detach_from_entity = r.read_optional(r.bool)
        return cls(
            set=set_,
            clear=clear,
            fade=fade,
            target=target,
            remove_target=remove_target,
            field_of_view=field_of_view,
            spline=spline,
            attach_to_entity=attach_to_entity,
            detach_from_entity=detach_from_entity,
        )
