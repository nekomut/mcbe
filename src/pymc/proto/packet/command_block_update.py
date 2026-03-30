"""Packet: CommandBlockUpdate."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_COMMAND_BLOCK_UPDATE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos

COMMAND_BLOCK_IMPULSE = 0
COMMAND_BLOCK_REPEATING = 1
COMMAND_BLOCK_CHAIN = 2


@register_server_packet
@dataclass
class CommandBlockUpdate(Packet):
    packet_id = ID_COMMAND_BLOCK_UPDATE
    block: bool = False
    position: BlockPos = field(default_factory=BlockPos)
    mode: int = 0
    needs_redstone: bool = False
    conditional: bool = False
    minecart_entity_runtime_id: int = 0
    command: str = ""
    last_output: str = ""
    name: str = ""
    filtered_name: str = ""
    should_track_output: bool = False
    tick_delay: int = 0
    execute_on_first_tick: bool = False

    def write(self, w: PacketWriter) -> None:
        w.bool(self.block)
        if self.block:
            w.block_pos(self.position)
            w.varuint32(self.mode)
            w.bool(self.needs_redstone)
            w.bool(self.conditional)
        else:
            w.varuint64(self.minecart_entity_runtime_id)
        w.string(self.command)
        w.string(self.last_output)
        w.string(self.name)
        w.string(self.filtered_name)
        w.bool(self.should_track_output)
        w.uint32(self.tick_delay)
        w.bool(self.execute_on_first_tick)

    @classmethod
    def read(cls, r: PacketReader) -> CommandBlockUpdate:
        is_block = r.bool()
        position = BlockPos()
        mode = 0
        needs_redstone = False
        conditional = False
        minecart_entity_runtime_id = 0
        if is_block:
            position = r.block_pos()
            mode = r.varuint32()
            needs_redstone = r.bool()
            conditional = r.bool()
        else:
            minecart_entity_runtime_id = r.varuint64()
        command = r.string()
        last_output = r.string()
        name = r.string()
        filtered_name = r.string()
        should_track_output = r.bool()
        tick_delay = r.uint32()
        execute_on_first_tick = r.bool()
        return cls(
            block=is_block,
            position=position,
            mode=mode,
            needs_redstone=needs_redstone,
            conditional=conditional,
            minecart_entity_runtime_id=minecart_entity_runtime_id,
            command=command,
            last_output=last_output,
            name=name,
            filtered_name=filtered_name,
            should_track_output=should_track_output,
            tick_delay=tick_delay,
            execute_on_first_tick=execute_on_first_tick,
        )
