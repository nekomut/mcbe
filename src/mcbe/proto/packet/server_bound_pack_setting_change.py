"""Packet: ServerBoundPackSettingChange."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_SERVER_BOUND_PACK_SETTING_CHANGE
from mcbe.proto.pool import Packet, register_client_packet

# Pack setting value type constants.
PACK_SETTING_FLOAT = 0
PACK_SETTING_BOOL = 1
PACK_SETTING_STRING = 2


@register_client_packet
@dataclass
class ServerBoundPackSettingChange(Packet):
    packet_id = ID_SERVER_BOUND_PACK_SETTING_CHANGE
    pack_id: UUID = None
    setting_name: str = ""
    setting_value: object = None

    def __post_init__(self):
        if self.pack_id is None:
            self.pack_id = UUID(int=0)

    def write(self, w: PacketWriter) -> None:
        w.uuid(self.pack_id)
        w.string(self.setting_name)
        if isinstance(self.setting_value, float):
            w.varuint32(PACK_SETTING_FLOAT)
            w.float32(self.setting_value)
        elif isinstance(self.setting_value, bool):
            w.varuint32(PACK_SETTING_BOOL)
            w.bool(self.setting_value)
        elif isinstance(self.setting_value, str):
            w.varuint32(PACK_SETTING_STRING)
            w.string(self.setting_value)
        else:
            w.varuint32(PACK_SETTING_FLOAT)
            w.float32(0.0)

    @classmethod
    def read(cls, r: PacketReader) -> ServerBoundPackSettingChange:
        pack_id = r.uuid()
        setting_name = r.string()
        setting_type = r.varuint32()
        if setting_type == PACK_SETTING_FLOAT:
            setting_value = r.float32()
        elif setting_type == PACK_SETTING_BOOL:
            setting_value = r.bool()
        elif setting_type == PACK_SETTING_STRING:
            setting_value = r.string()
        else:
            setting_value = None
        return cls(
            pack_id=pack_id,
            setting_name=setting_name,
            setting_value=setting_value,
        )
