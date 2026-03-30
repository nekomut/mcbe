"""Tests for handshake/login packet roundtrip serialization."""

from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.pool import decode_packet, encode_packet, server_pool

from pymc.proto.packet.request_network_settings import RequestNetworkSettings
from pymc.proto.packet.network_settings import NetworkSettings
from pymc.proto.packet.login import Login
from pymc.proto.packet.play_status import PlayStatus, STATUS_LOGIN_SUCCESS, STATUS_PLAYER_SPAWN
from pymc.proto.packet.handshake import ServerToClientHandshake, ClientToServerHandshake
from pymc.proto.packet.disconnect import Disconnect
from pymc.proto.packet.resource_packs import (
    ResourcePacksInfo, ResourcePackStack, ResourcePackClientResponse,
    TexturePackInfo, StackResourcePack, ExperimentData,
    PACK_RESPONSE_COMPLETED, PACK_RESPONSE_ALL_PACKS_DOWNLOADED,
)
from pymc.proto.packet.text import (
    Text, TEXT_TYPE_CHAT, TEXT_TYPE_RAW, TEXT_TYPE_TRANSLATION, TEXT_TYPE_TIP,
)
from pymc.proto.packet.set_local_player_as_initialised import SetLocalPlayerAsInitialised
from pymc.proto.packet.request_chunk_radius import RequestChunkRadius
from pymc.proto.packet.chunk_radius_updated import ChunkRadiusUpdated


def _roundtrip(pk):
    """Encode a packet, decode it, and return the result."""
    w = PacketWriter()
    pk.write(w)
    data = w.data()
    r = PacketReader(data)
    return type(pk).read(r)


class TestRequestNetworkSettings:
    def test_roundtrip(self):
        pk = RequestNetworkSettings(client_protocol=729)
        result = _roundtrip(pk)
        assert result.client_protocol == 729


class TestNetworkSettings:
    def test_roundtrip(self):
        pk = NetworkSettings(
            compression_threshold=256,
            compression_algorithm=1,
            client_throttle=True,
            client_throttle_threshold=10,
            client_throttle_scalar=0.5,
        )
        result = _roundtrip(pk)
        assert result.compression_threshold == 256
        assert result.compression_algorithm == 1
        assert result.client_throttle is True
        assert result.client_throttle_threshold == 10
        assert abs(result.client_throttle_scalar - 0.5) < 1e-6


class TestLogin:
    def test_roundtrip(self):
        pk = Login(client_protocol=729, connection_request=b"\x01\x02\x03\x04")
        result = _roundtrip(pk)
        assert result.client_protocol == 729
        assert result.connection_request == b"\x01\x02\x03\x04"


class TestPlayStatus:
    def test_roundtrip_success(self):
        pk = PlayStatus(status=STATUS_LOGIN_SUCCESS)
        result = _roundtrip(pk)
        assert result.status == STATUS_LOGIN_SUCCESS

    def test_roundtrip_spawn(self):
        pk = PlayStatus(status=STATUS_PLAYER_SPAWN)
        result = _roundtrip(pk)
        assert result.status == STATUS_PLAYER_SPAWN


class TestServerToClientHandshake:
    def test_roundtrip(self):
        jwt_data = b'{"alg":"ES384","x5u":"..."}'
        pk = ServerToClientHandshake(jwt=jwt_data)
        result = _roundtrip(pk)
        assert result.jwt == jwt_data


class TestClientToServerHandshake:
    def test_roundtrip(self):
        pk = ClientToServerHandshake()
        result = _roundtrip(pk)
        assert isinstance(result, ClientToServerHandshake)


class TestDisconnect:
    def test_roundtrip_with_message(self):
        pk = Disconnect(
            reason=1,
            hide_disconnection_screen=False,
            message="Kicked",
            filtered_message="***",
        )
        result = _roundtrip(pk)
        assert result.reason == 1
        assert result.hide_disconnection_screen is False
        assert result.message == "Kicked"
        assert result.filtered_message == "***"

    def test_roundtrip_hidden(self):
        pk = Disconnect(reason=2, hide_disconnection_screen=True)
        result = _roundtrip(pk)
        assert result.reason == 2
        assert result.hide_disconnection_screen is True
        assert result.message == ""
        assert result.filtered_message == ""


class TestResourcePacksInfo:
    def test_roundtrip_empty(self):
        pk = ResourcePacksInfo(texture_pack_required=True, has_scripts=True)
        result = _roundtrip(pk)
        assert result.texture_pack_required is True
        assert result.has_scripts is True
        assert result.texture_packs == []

    def test_roundtrip_with_packs(self):
        info = TexturePackInfo(
            uuid="abc-123",
            version="1.0.0",
            size=1024,
            content_key="key",
            sub_pack_name="sub",
            content_identity="id",
            has_scripts=True,
            addon_pack=False,
            rtx_enabled=True,
        )
        pk = ResourcePacksInfo(
            texture_pack_required=True,
            has_addons=True,
            has_scripts=False,
            force_disable_vibrant_visuals=True,
            world_template_uuid=UUID("12345678-1234-5678-1234-567812345678"),
            world_template_version="1.0.0",
            texture_packs=[info],
        )
        result = _roundtrip(pk)
        assert result.texture_pack_required is True
        assert result.has_addons is True
        assert result.force_disable_vibrant_visuals is True
        assert len(result.texture_packs) == 1
        ti = result.texture_packs[0]
        assert ti.uuid == "abc-123"
        assert ti.size == 1024
        assert ti.has_scripts is True
        assert ti.rtx_enabled is True


class TestResourcePackStack:
    def test_roundtrip(self):
        pk = ResourcePackStack(
            texture_pack_required=True,
            texture_packs=[StackResourcePack(uuid="u1", version="1.0", sub_pack_name="s")],
            base_game_version="1.21.0",
            experiments=[ExperimentData(name="exp1", enabled=True)],
            experiments_previously_toggled=True,
            include_editor_packs=False,
        )
        result = _roundtrip(pk)
        assert result.texture_pack_required is True
        assert len(result.texture_packs) == 1
        assert result.texture_packs[0].uuid == "u1"
        assert result.base_game_version == "1.21.0"
        assert len(result.experiments) == 1
        assert result.experiments[0].name == "exp1"
        assert result.experiments[0].enabled is True
        assert result.experiments_previously_toggled is True


class TestResourcePackClientResponse:
    def test_roundtrip(self):
        pk = ResourcePackClientResponse(
            response=PACK_RESPONSE_COMPLETED,
            packs_to_download=["pack1", "pack2"],
        )
        result = _roundtrip(pk)
        assert result.response == PACK_RESPONSE_COMPLETED
        assert result.packs_to_download == ["pack1", "pack2"]

    def test_roundtrip_empty(self):
        pk = ResourcePackClientResponse(response=PACK_RESPONSE_ALL_PACKS_DOWNLOADED)
        result = _roundtrip(pk)
        assert result.response == PACK_RESPONSE_ALL_PACKS_DOWNLOADED
        assert result.packs_to_download == []


class TestText:
    def test_chat_roundtrip(self):
        pk = Text(
            text_type=TEXT_TYPE_CHAT,
            needs_translation=False,
            source_name="Player1",
            message="Hello world",
            xuid="12345",
            platform_chat_id="",
        )
        result = _roundtrip(pk)
        assert result.text_type == TEXT_TYPE_CHAT
        assert result.source_name == "Player1"
        assert result.message == "Hello world"
        assert result.xuid == "12345"

    def test_raw_roundtrip(self):
        pk = Text(
            text_type=TEXT_TYPE_RAW,
            message="Raw message",
            xuid="",
            platform_chat_id="",
        )
        result = _roundtrip(pk)
        assert result.text_type == TEXT_TYPE_RAW
        assert result.message == "Raw message"
        assert result.source_name == ""

    def test_translation_roundtrip(self):
        pk = Text(
            text_type=TEXT_TYPE_TRANSLATION,
            needs_translation=True,
            message="chat.type.text",
            parameters=["Player1", "Hello"],
            xuid="",
            platform_chat_id="",
        )
        result = _roundtrip(pk)
        assert result.text_type == TEXT_TYPE_TRANSLATION
        assert result.needs_translation is True
        assert result.message == "chat.type.text"
        assert result.parameters == ["Player1", "Hello"]

    def test_tip_roundtrip(self):
        pk = Text(
            text_type=TEXT_TYPE_TIP,
            message="Tip message",
            xuid="",
            platform_chat_id="",
        )
        result = _roundtrip(pk)
        assert result.text_type == TEXT_TYPE_TIP
        assert result.message == "Tip message"

    def test_filtered_message(self):
        pk = Text(
            text_type=TEXT_TYPE_CHAT,
            source_name="P",
            message="bad word",
            xuid="",
            platform_chat_id="",
            filtered_message="*** word",
        )
        result = _roundtrip(pk)
        assert result.filtered_message == "*** word"

    def test_no_filtered_message(self):
        pk = Text(
            text_type=TEXT_TYPE_RAW,
            message="clean",
            xuid="",
            platform_chat_id="",
            filtered_message=None,
        )
        result = _roundtrip(pk)
        assert result.filtered_message is None


class TestSetLocalPlayerAsInitialised:
    def test_roundtrip(self):
        pk = SetLocalPlayerAsInitialised(entity_runtime_id=42)
        result = _roundtrip(pk)
        assert result.entity_runtime_id == 42

    def test_large_id(self):
        pk = SetLocalPlayerAsInitialised(entity_runtime_id=2**48)
        result = _roundtrip(pk)
        assert result.entity_runtime_id == 2**48


class TestRequestChunkRadius:
    def test_roundtrip(self):
        pk = RequestChunkRadius(chunk_radius=16, max_chunk_radius=32)
        result = _roundtrip(pk)
        assert result.chunk_radius == 16
        assert result.max_chunk_radius == 32

    def test_negative_radius(self):
        pk = RequestChunkRadius(chunk_radius=-1, max_chunk_radius=0)
        result = _roundtrip(pk)
        assert result.chunk_radius == -1


class TestChunkRadiusUpdated:
    def test_roundtrip(self):
        pk = ChunkRadiusUpdated(chunk_radius=12)
        result = _roundtrip(pk)
        assert result.chunk_radius == 12
