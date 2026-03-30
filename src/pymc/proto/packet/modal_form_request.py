"""Packet: ModalFormRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MODAL_FORM_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ModalFormRequest(Packet):
    packet_id = ID_MODAL_FORM_REQUEST
    form_id: int = 0
    form_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.form_id)
        w.byte_slice(self.form_data)

    @classmethod
    def read(cls, r: PacketReader) -> ModalFormRequest:
        return cls(
            form_id=r.varuint32(),
            form_data=r.byte_slice(),
        )
