"""Packet: ClientBoundAttributeLayerSync.

Complex sub-structures (AttributeLayerData, AttributeLayerSettings, etc.)
are kept as raw bytes. The conditional switch on PayloadType is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_ATTRIBUTE_LAYER_SYNC
from pymc.proto.pool import Packet, register_server_packet

ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_LAYERS = 0
ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_SETTINGS = 1
ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_ENVIRONMENT = 2
ATTRIBUTE_LAYER_PAYLOAD_TYPE_REMOVE_ENVIRONMENT = 3


@register_server_packet
@dataclass
class ClientBoundAttributeLayerSync(Packet):
    packet_id = ID_CLIENT_BOUND_ATTRIBUTE_LAYER_SYNC
    payload_type: int = 0
    layers: bytes = b""
    layer_name: str = ""
    dimension_id: int = 0
    settings: bytes = b""
    environment_attributes: bytes = b""
    remove_attribute_names: list[str] | None = None

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.payload_type)
        if self.payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_LAYERS:
            w.bytes_raw(self.layers)
        elif self.payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_SETTINGS:
            w.string(self.layer_name)
            w.varint32(self.dimension_id)
            w.bytes_raw(self.settings)
        elif self.payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_ENVIRONMENT:
            w.string(self.layer_name)
            w.varint32(self.dimension_id)
            w.bytes_raw(self.environment_attributes)
        elif self.payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_REMOVE_ENVIRONMENT:
            w.string(self.layer_name)
            w.varint32(self.dimension_id)
            names = self.remove_attribute_names or []
            w.varuint32(len(names))
            for name in names:
                w.string(name)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundAttributeLayerSync:
        payload_type = r.varuint32()
        layers = b""
        layer_name = ""
        dimension_id = 0
        settings = b""
        environment_attributes = b""
        remove_attribute_names: list[str] | None = None

        if payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_LAYERS:
            layers = r.bytes_remaining()
        elif payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_SETTINGS:
            layer_name = r.string()
            dimension_id = r.varint32()
            settings = r.bytes_remaining()
        elif payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_UPDATE_ENVIRONMENT:
            layer_name = r.string()
            dimension_id = r.varint32()
            environment_attributes = r.bytes_remaining()
        elif payload_type == ATTRIBUTE_LAYER_PAYLOAD_TYPE_REMOVE_ENVIRONMENT:
            layer_name = r.string()
            dimension_id = r.varint32()
            count = r.varuint32()
            remove_attribute_names = [r.string() for _ in range(count)]

        return cls(
            payload_type=payload_type,
            layers=layers,
            layer_name=layer_name,
            dimension_id=dimension_id,
            settings=settings,
            environment_attributes=environment_attributes,
            remove_attribute_names=remove_attribute_names,
        )
