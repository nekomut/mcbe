"""Packet: PurchaseReceipt."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PURCHASE_RECEIPT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PurchaseReceipt(Packet):
    packet_id = ID_PURCHASE_RECEIPT
    receipts: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.receipts)

    @classmethod
    def read(cls, r: PacketReader) -> PurchaseReceipt:
        return cls(
            receipts=r.byte_slice(),
        )
