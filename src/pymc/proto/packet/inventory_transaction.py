"""Packet: InventoryTransaction.

TransactionData is kept as raw bytes because the polymorphic transaction
types (NormalTransactionData, UseItemTransactionData, etc.) and their
sub-structures (InventoryAction, LegacySetItemSlot) have not been ported yet.
The conditional LegacySetItemSlots logic is implemented correctly.
"""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_INVENTORY_TRANSACTION
from pymc.proto.pool import Packet, register_server_packet

INVENTORY_TRANSACTION_TYPE_NORMAL = 0
INVENTORY_TRANSACTION_TYPE_MISMATCH = 1
INVENTORY_TRANSACTION_TYPE_USE_ITEM = 2
INVENTORY_TRANSACTION_TYPE_USE_ITEM_ON_ENTITY = 3
INVENTORY_TRANSACTION_TYPE_RELEASE_ITEM = 4


@register_server_packet
@dataclass
class InventoryTransaction(Packet):
    packet_id = ID_INVENTORY_TRANSACTION
    legacy_request_id: int = 0
    legacy_set_item_slots: bytes = b""
    transaction_data_type: int = 0
    actions: bytes = b""
    transaction_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.legacy_request_id)
        if self.legacy_request_id != 0:
            w.byte_slice(self.legacy_set_item_slots)
        w.varuint32(self.transaction_data_type)
        w.bytes_raw(self.actions)
        w.bytes_raw(self.transaction_data)

    @classmethod
    def read(cls, r: PacketReader) -> InventoryTransaction:
        legacy_request_id = r.varint32()
        legacy_set_item_slots = b""
        if legacy_request_id != 0:
            legacy_set_item_slots = r.byte_slice()
        transaction_data_type = r.varuint32()
        remaining = r.bytes_remaining()
        return cls(
            legacy_request_id=legacy_request_id,
            legacy_set_item_slots=legacy_set_item_slots,
            transaction_data_type=transaction_data_type,
            actions=b"",
            transaction_data=remaining,
        )
