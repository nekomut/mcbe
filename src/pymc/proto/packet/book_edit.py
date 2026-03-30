"""Packet: BookEdit."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_BOOK_EDIT
from pymc.proto.pool import Packet, register_server_packet

BOOK_ACTION_REPLACE_PAGE = 0
BOOK_ACTION_ADD_PAGE = 1
BOOK_ACTION_DELETE_PAGE = 2
BOOK_ACTION_SWAP_PAGES = 3
BOOK_ACTION_SIGN = 4


@register_server_packet
@dataclass
class BookEdit(Packet):
    packet_id = ID_BOOK_EDIT
    inventory_slot: int = 0
    action_type: int = 0
    page_number: int = 0
    secondary_page_number: int = 0
    text: str = ""
    photo_name: str = ""
    title: str = ""
    author: str = ""
    xuid: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.inventory_slot)
        w.varuint32(self.action_type)
        if self.action_type in (BOOK_ACTION_REPLACE_PAGE, BOOK_ACTION_ADD_PAGE):
            w.varint32(self.page_number)
            w.string(self.text)
            w.string(self.photo_name)
        elif self.action_type == BOOK_ACTION_DELETE_PAGE:
            w.varint32(self.page_number)
        elif self.action_type == BOOK_ACTION_SWAP_PAGES:
            w.varint32(self.page_number)
            w.varint32(self.secondary_page_number)
        elif self.action_type == BOOK_ACTION_SIGN:
            w.string(self.title)
            w.string(self.author)
            w.string(self.xuid)

    @classmethod
    def read(cls, r: PacketReader) -> BookEdit:
        inventory_slot = r.varint32()
        action_type = r.varuint32()
        page_number = 0
        secondary_page_number = 0
        text = ""
        photo_name = ""
        title = ""
        author = ""
        xuid = ""
        if action_type in (BOOK_ACTION_REPLACE_PAGE, BOOK_ACTION_ADD_PAGE):
            page_number = r.varint32()
            text = r.string()
            photo_name = r.string()
        elif action_type == BOOK_ACTION_DELETE_PAGE:
            page_number = r.varint32()
        elif action_type == BOOK_ACTION_SWAP_PAGES:
            page_number = r.varint32()
            secondary_page_number = r.varint32()
        elif action_type == BOOK_ACTION_SIGN:
            title = r.string()
            author = r.string()
            xuid = r.string()
        return cls(
            inventory_slot=inventory_slot,
            action_type=action_type,
            page_number=page_number,
            secondary_page_number=secondary_page_number,
            text=text,
            photo_name=photo_name,
            title=title,
            author=author,
            xuid=xuid,
        )
