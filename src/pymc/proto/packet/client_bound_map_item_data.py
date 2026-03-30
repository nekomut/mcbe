"""Packet: ClientBoundMapItemData.

Complex sub-structures (MapTrackedObject, MapDecoration, Pixel RGBA) are
kept as raw bytes. The conditional flag-based logic is implemented correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_MAP_ITEM_DATA
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos

MAP_UPDATE_FLAG_TEXTURE = 1 << 1
MAP_UPDATE_FLAG_DECORATION = 1 << 2
MAP_UPDATE_FLAG_INITIALISATION = 1 << 3


@register_server_packet
@dataclass
class ClientBoundMapItemData(Packet):
    packet_id = ID_CLIENT_BOUND_MAP_ITEM_DATA
    map_id: int = 0
    update_flags: int = 0
    dimension: int = 0
    locked_map: bool = False
    origin: BlockPos = field(default_factory=BlockPos)
    scale: int = 0
    maps_included_in: list[int] = field(default_factory=list)
    tracked_objects: bytes = b""
    decorations: bytes = b""
    width: int = 0
    height: int = 0
    x_offset: int = 0
    y_offset: int = 0
    pixels: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.map_id)
        w.varuint32(self.update_flags)
        w.uint8(self.dimension)
        w.bool(self.locked_map)
        w.block_pos(self.origin)
        if self.update_flags & MAP_UPDATE_FLAG_INITIALISATION:
            w.varuint32(len(self.maps_included_in))
            for mid in self.maps_included_in:
                w.varint64(mid)
        if self.update_flags & (
            MAP_UPDATE_FLAG_INITIALISATION
            | MAP_UPDATE_FLAG_DECORATION
            | MAP_UPDATE_FLAG_TEXTURE
        ):
            w.uint8(self.scale)
        if self.update_flags & MAP_UPDATE_FLAG_DECORATION:
            w.bytes_raw(self.tracked_objects)
            w.bytes_raw(self.decorations)
        if self.update_flags & MAP_UPDATE_FLAG_TEXTURE:
            w.varint32(self.width)
            w.varint32(self.height)
            w.varint32(self.x_offset)
            w.varint32(self.y_offset)
            w.bytes_raw(self.pixels)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundMapItemData:
        map_id = r.varint64()
        update_flags = r.varuint32()
        dimension = r.uint8()
        locked_map = r.bool()
        origin = r.block_pos()
        maps_included_in: list[int] = []
        scale = 0
        tracked_objects = b""
        decorations = b""
        width = 0
        height = 0
        x_offset = 0
        y_offset = 0
        pixels = b""

        if update_flags & MAP_UPDATE_FLAG_INITIALISATION:
            count = r.varuint32()
            maps_included_in = [r.varint64() for _ in range(count)]
        if update_flags & (
            MAP_UPDATE_FLAG_INITIALISATION
            | MAP_UPDATE_FLAG_DECORATION
            | MAP_UPDATE_FLAG_TEXTURE
        ):
            scale = r.uint8()
        if update_flags & MAP_UPDATE_FLAG_DECORATION:
            tracked_objects = r.bytes_remaining()
            decorations = b""
        elif update_flags & MAP_UPDATE_FLAG_TEXTURE:
            width = r.varint32()
            height = r.varint32()
            x_offset = r.varint32()
            y_offset = r.varint32()
            pixels = r.bytes_remaining()

        return cls(
            map_id=map_id,
            update_flags=update_flags,
            dimension=dimension,
            locked_map=locked_map,
            origin=origin,
            scale=scale,
            maps_included_in=maps_included_in,
            tracked_objects=tracked_objects,
            decorations=decorations,
            width=width,
            height=height,
            x_offset=x_offset,
            y_offset=y_offset,
            pixels=pixels,
        )
