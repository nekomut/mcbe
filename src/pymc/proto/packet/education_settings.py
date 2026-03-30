"""Packet: EducationSettings."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_EDUCATION_SETTINGS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class EducationSettings(Packet):
    packet_id = ID_EDUCATION_SETTINGS
    code_builder_default_uri: str = ""
    code_builder_title: str = ""
    can_resize_code_builder: bool = False
    disable_legacy_title_bar: bool = False
    post_process_filter: str = ""
    screenshot_border_path: str = ""
    can_modify_blocks: bytes = b""
    override_uri: bytes = b""
    has_quiz: bool = False
    external_link_settings: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.code_builder_default_uri)
        w.string(self.code_builder_title)
        w.bool(self.can_resize_code_builder)
        w.bool(self.disable_legacy_title_bar)
        w.string(self.post_process_filter)
        w.string(self.screenshot_border_path)
        w.byte_slice(self.can_modify_blocks)
        w.byte_slice(self.override_uri)
        w.bool(self.has_quiz)
        w.byte_slice(self.external_link_settings)

    @classmethod
    def read(cls, r: PacketReader) -> EducationSettings:
        return cls(
            code_builder_default_uri=r.string(),
            code_builder_title=r.string(),
            can_resize_code_builder=r.bool(),
            disable_legacy_title_bar=r.bool(),
            post_process_filter=r.string(),
            screenshot_border_path=r.string(),
            can_modify_blocks=r.byte_slice(),
            override_uri=r.byte_slice(),
            has_quiz=r.bool(),
            external_link_settings=r.byte_slice(),
        )
