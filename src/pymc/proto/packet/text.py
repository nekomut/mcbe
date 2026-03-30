"""Text packet - chat messages, tips, popups, etc."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_TEXT
from pymc.proto.pool import Packet, register_bidirectional

# Text types
TEXT_TYPE_RAW = 0
TEXT_TYPE_CHAT = 1
TEXT_TYPE_TRANSLATION = 2
TEXT_TYPE_POPUP = 3
TEXT_TYPE_JUKEBOX_POPUP = 4
TEXT_TYPE_TIP = 5
TEXT_TYPE_SYSTEM = 6
TEXT_TYPE_WHISPER = 7
TEXT_TYPE_ANNOUNCEMENT = 8
TEXT_TYPE_OBJECT_WHISPER = 9
TEXT_TYPE_OBJECT = 10
TEXT_TYPE_OBJECT_ANNOUNCEMENT = 11

# Text category types
TEXT_CATEGORY_MESSAGE_ONLY = 0
TEXT_CATEGORY_AUTHORED_MESSAGE = 1
TEXT_CATEGORY_MESSAGE_WITH_PARAMETERS = 2

_MESSAGE_ONLY_TYPES = {
    TEXT_TYPE_RAW, TEXT_TYPE_TIP, TEXT_TYPE_SYSTEM,
    TEXT_TYPE_OBJECT_WHISPER, TEXT_TYPE_OBJECT_ANNOUNCEMENT, TEXT_TYPE_OBJECT,
}
_AUTHORED_MESSAGE_TYPES = {
    TEXT_TYPE_CHAT, TEXT_TYPE_WHISPER, TEXT_TYPE_ANNOUNCEMENT,
}
_PARAMETERIZED_TYPES = {
    TEXT_TYPE_TRANSLATION, TEXT_TYPE_POPUP, TEXT_TYPE_JUKEBOX_POPUP,
}


@register_bidirectional
@dataclass
class Text(Packet):
    packet_id = ID_TEXT
    needs_translation: bool = False
    text_type: int = 0
    source_name: str = ""
    message: str = ""
    parameters: list[str] = field(default_factory=list)
    xuid: str = ""
    platform_chat_id: str = ""
    filtered_message: str | None = None

    def write(self, w: PacketWriter) -> None:
        w.bool(self.needs_translation)
        # Determine category
        if self.text_type in _MESSAGE_ONLY_TYPES:
            category = TEXT_CATEGORY_MESSAGE_ONLY
        elif self.text_type in _AUTHORED_MESSAGE_TYPES:
            category = TEXT_CATEGORY_AUTHORED_MESSAGE
        else:
            category = TEXT_CATEGORY_MESSAGE_WITH_PARAMETERS
        w.uint8(category)
        w.uint8(self.text_type)

        if self.text_type in _AUTHORED_MESSAGE_TYPES:
            w.string(self.source_name)
            w.string(self.message)
        elif self.text_type in _MESSAGE_ONLY_TYPES:
            w.string(self.message)
        elif self.text_type in _PARAMETERIZED_TYPES:
            w.string(self.message)
            w.write_slice(self.parameters, w.string)

        w.string(self.xuid)
        w.string(self.platform_chat_id)
        w.write_optional(self.filtered_message, w.string)

    @classmethod
    def read(cls, r: PacketReader) -> Text:
        needs_translation = r.bool()
        _category = r.uint8()  # Read but derive from text_type
        text_type = r.uint8()

        source_name = ""
        message = ""
        parameters: list[str] = []

        if text_type in _AUTHORED_MESSAGE_TYPES:
            source_name = r.string()
            message = r.string()
        elif text_type in _MESSAGE_ONLY_TYPES:
            message = r.string()
        elif text_type in _PARAMETERIZED_TYPES:
            message = r.string()
            parameters = r.read_slice(r.string)

        xuid = r.string()
        platform_chat_id = r.string()
        filtered_message = r.read_optional(r.string)

        return cls(
            needs_translation=needs_translation,
            text_type=text_type,
            source_name=source_name,
            message=message,
            parameters=parameters,
            xuid=xuid,
            platform_chat_id=platform_chat_id,
            filtered_message=filtered_message,
        )
