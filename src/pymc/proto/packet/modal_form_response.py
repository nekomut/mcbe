"""Packet: ModalFormResponse."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MODAL_FORM_RESPONSE
from pymc.proto.pool import Packet, register_server_packet

MODAL_FORM_CANCEL_REASON_USER_CLOSED = 0
MODAL_FORM_CANCEL_REASON_USER_BUSY = 1


@register_server_packet
@dataclass
class ModalFormResponse(Packet):
    packet_id = ID_MODAL_FORM_RESPONSE
    form_id: int = 0
    response_data: bytes | None = None
    cancel_reason: int | None = None

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.form_id)
        w.write_optional(self.response_data, w.byte_slice)
        w.write_optional(self.cancel_reason, w.uint8)

    @classmethod
    def read(cls, r: PacketReader) -> ModalFormResponse:
        form_id = r.varuint32()
        response_data = r.read_optional(r.byte_slice)
        cancel_reason = r.read_optional(r.uint8)
        return cls(
            form_id=form_id,
            response_data=response_data,
            cancel_reason=cancel_reason,
        )
