"""Packet: ClientMovementPredictionSync."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_MOVEMENT_PREDICTION_SYNC
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientMovementPredictionSync(Packet):
    packet_id = ID_CLIENT_MOVEMENT_PREDICTION_SYNC
    actor_flags: bytes = b""
    bounding_box_scale: float = 0.0
    bounding_box_width: float = 0.0
    bounding_box_height: float = 0.0
    movement_speed: float = 0.0
    underwater_movement_speed: float = 0.0
    lava_movement_speed: float = 0.0
    jump_strength: float = 0.0
    health: float = 0.0
    hunger: float = 0.0
    entity_unique_id: int = 0
    flying: bool = False

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.actor_flags)
        w.float32(self.bounding_box_scale)
        w.float32(self.bounding_box_width)
        w.float32(self.bounding_box_height)
        w.float32(self.movement_speed)
        w.float32(self.underwater_movement_speed)
        w.float32(self.lava_movement_speed)
        w.float32(self.jump_strength)
        w.float32(self.health)
        w.float32(self.hunger)
        w.varint64(self.entity_unique_id)
        w.bool(self.flying)

    @classmethod
    def read(cls, r: PacketReader) -> ClientMovementPredictionSync:
        return cls(
            actor_flags=r.byte_slice(),
            bounding_box_scale=r.float32(),
            bounding_box_width=r.float32(),
            bounding_box_height=r.float32(),
            movement_speed=r.float32(),
            underwater_movement_speed=r.float32(),
            lava_movement_speed=r.float32(),
            jump_strength=r.float32(),
            health=r.float32(),
            hunger=r.float32(),
            entity_unique_id=r.varint64(),
            flying=r.bool(),
        )
