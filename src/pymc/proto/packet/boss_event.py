"""Packet: BossEvent."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_BOSS_EVENT
from pymc.proto.pool import Packet, register_server_packet

BOSS_EVENT_SHOW = 0
BOSS_EVENT_REGISTER_PLAYER = 1
BOSS_EVENT_HIDE = 2
BOSS_EVENT_UNREGISTER_PLAYER = 3
BOSS_EVENT_HEALTH_PERCENTAGE = 4
BOSS_EVENT_TITLE = 5
BOSS_EVENT_APPEARANCE_PROPERTIES = 6
BOSS_EVENT_TEXTURE = 7
BOSS_EVENT_REQUEST = 8

BOSS_EVENT_COLOUR_GREY = 0
BOSS_EVENT_COLOUR_BLUE = 1
BOSS_EVENT_COLOUR_RED = 2
BOSS_EVENT_COLOUR_GREEN = 3
BOSS_EVENT_COLOUR_YELLOW = 4
BOSS_EVENT_COLOUR_PURPLE = 5
BOSS_EVENT_COLOUR_WHITE = 6


@register_server_packet
@dataclass
class BossEvent(Packet):
    packet_id = ID_BOSS_EVENT
    boss_entity_unique_id: int = 0
    event_type: int = 0
    player_unique_id: int = 0
    boss_bar_title: str = ""
    filtered_boss_bar_title: str = ""
    health_percentage: float = 0.0
    screen_darkening: int = 0
    colour: int = 0
    overlay: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.boss_entity_unique_id)
        w.varuint32(self.event_type)
        if self.event_type == BOSS_EVENT_SHOW:
            w.string(self.boss_bar_title)
            w.string(self.filtered_boss_bar_title)
            w.float32(self.health_percentage)
            w.uint16(self.screen_darkening)
            w.varuint32(self.colour)
            w.varuint32(self.overlay)
        elif self.event_type in (
            BOSS_EVENT_REGISTER_PLAYER,
            BOSS_EVENT_UNREGISTER_PLAYER,
            BOSS_EVENT_REQUEST,
        ):
            w.varint64(self.player_unique_id)
        elif self.event_type == BOSS_EVENT_HIDE:
            pass
        elif self.event_type == BOSS_EVENT_HEALTH_PERCENTAGE:
            w.float32(self.health_percentage)
        elif self.event_type == BOSS_EVENT_TITLE:
            w.string(self.boss_bar_title)
            w.string(self.filtered_boss_bar_title)
        elif self.event_type == BOSS_EVENT_APPEARANCE_PROPERTIES:
            w.uint16(self.screen_darkening)
            w.varuint32(self.colour)
            w.varuint32(self.overlay)
        elif self.event_type == BOSS_EVENT_TEXTURE:
            w.varuint32(self.colour)
            w.varuint32(self.overlay)

    @classmethod
    def read(cls, r: PacketReader) -> BossEvent:
        boss_entity_unique_id = r.varint64()
        event_type = r.varuint32()
        player_unique_id = 0
        boss_bar_title = ""
        filtered_boss_bar_title = ""
        health_percentage = 0.0
        screen_darkening = 0
        colour = 0
        overlay = 0

        if event_type == BOSS_EVENT_SHOW:
            boss_bar_title = r.string()
            filtered_boss_bar_title = r.string()
            health_percentage = r.float32()
            screen_darkening = r.uint16()
            colour = r.varuint32()
            overlay = r.varuint32()
        elif event_type in (
            BOSS_EVENT_REGISTER_PLAYER,
            BOSS_EVENT_UNREGISTER_PLAYER,
            BOSS_EVENT_REQUEST,
        ):
            player_unique_id = r.varint64()
        elif event_type == BOSS_EVENT_HIDE:
            pass
        elif event_type == BOSS_EVENT_HEALTH_PERCENTAGE:
            health_percentage = r.float32()
        elif event_type == BOSS_EVENT_TITLE:
            boss_bar_title = r.string()
            filtered_boss_bar_title = r.string()
        elif event_type == BOSS_EVENT_APPEARANCE_PROPERTIES:
            screen_darkening = r.uint16()
            colour = r.varuint32()
            overlay = r.varuint32()
        elif event_type == BOSS_EVENT_TEXTURE:
            colour = r.varuint32()
            overlay = r.varuint32()

        return cls(
            boss_entity_unique_id=boss_entity_unique_id,
            event_type=event_type,
            player_unique_id=player_unique_id,
            boss_bar_title=boss_bar_title,
            filtered_boss_bar_title=filtered_boss_bar_title,
            health_percentage=health_percentage,
            screen_darkening=screen_darkening,
            colour=colour,
            overlay=overlay,
        )
