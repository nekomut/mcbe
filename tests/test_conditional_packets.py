"""Tests for conditional/branching packet roundtrip serialization."""

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.types import BlockPos, ChunkPos, SubChunkPos, Vec3


def _roundtrip(pk):
    """Encode a packet, decode it, and return the result."""
    w = PacketWriter()
    pk.write(w)
    data = w.data()
    r = PacketReader(data)
    return type(pk).read(r)


# ── MovePlayer ──

class TestMovePlayer:
    def test_roundtrip_normal(self):
        from pymc.proto.packet.move_player import MovePlayer, MOVE_MODE_NORMAL
        pk = MovePlayer(
            entity_runtime_id=42,
            position=Vec3(1.0, 2.0, 3.0),
            pitch=10.0,
            yaw=20.0,
            head_yaw=30.0,
            mode=MOVE_MODE_NORMAL,
            on_ground=True,
            ridden_entity_runtime_id=0,
            tick=100,
        )
        result = _roundtrip(pk)
        assert result.entity_runtime_id == 42
        assert result.mode == MOVE_MODE_NORMAL
        assert result.on_ground is True
        assert result.teleport_cause == 0
        assert result.teleport_source_entity_type == 0
        assert result.tick == 100

    def test_roundtrip_teleport(self):
        from pymc.proto.packet.move_player import MovePlayer, MOVE_MODE_TELEPORT, TELEPORT_CAUSE_COMMAND
        pk = MovePlayer(
            entity_runtime_id=7,
            position=Vec3(100.0, 64.0, 200.0),
            pitch=0.0,
            yaw=90.0,
            head_yaw=90.0,
            mode=MOVE_MODE_TELEPORT,
            on_ground=False,
            ridden_entity_runtime_id=0,
            teleport_cause=TELEPORT_CAUSE_COMMAND,
            teleport_source_entity_type=5,
            tick=200,
        )
        result = _roundtrip(pk)
        assert result.mode == MOVE_MODE_TELEPORT
        assert result.teleport_cause == TELEPORT_CAUSE_COMMAND
        assert result.teleport_source_entity_type == 5
        assert result.tick == 200


# ── LevelChunk ──

class TestLevelChunk:
    def test_roundtrip_basic(self):
        from pymc.proto.packet.level_chunk import LevelChunk
        pk = LevelChunk(
            position=ChunkPos(10, 20),
            dimension=0,
            sub_chunk_count=4,
            cache_enabled=False,
            raw_payload=b"\x01\x02\x03",
        )
        result = _roundtrip(pk)
        assert result.position == ChunkPos(10, 20)
        assert result.sub_chunk_count == 4
        assert result.cache_enabled is False
        assert result.raw_payload == b"\x01\x02\x03"
        assert result.blob_hashes == []

    def test_roundtrip_with_cache(self):
        from pymc.proto.packet.level_chunk import LevelChunk
        pk = LevelChunk(
            position=ChunkPos(5, 15),
            dimension=1,
            sub_chunk_count=2,
            cache_enabled=True,
            blob_hashes=[111, 222, 333],
            raw_payload=b"\xAA\xBB",
        )
        result = _roundtrip(pk)
        assert result.cache_enabled is True
        assert result.blob_hashes == [111, 222, 333]

    def test_roundtrip_limited(self):
        from pymc.proto.packet.level_chunk import LevelChunk, SUB_CHUNK_REQUEST_MODE_LIMITED
        pk = LevelChunk(
            position=ChunkPos(0, 0),
            dimension=0,
            sub_chunk_count=SUB_CHUNK_REQUEST_MODE_LIMITED,
            highest_sub_chunk=16,
            cache_enabled=False,
            raw_payload=b"",
        )
        result = _roundtrip(pk)
        assert result.sub_chunk_count == SUB_CHUNK_REQUEST_MODE_LIMITED
        assert result.highest_sub_chunk == 16


# ── BossEvent ──

class TestBossEvent:
    def test_roundtrip_show(self):
        from pymc.proto.packet.boss_event import BossEvent, BOSS_EVENT_SHOW
        pk = BossEvent(
            boss_entity_unique_id=1,
            event_type=BOSS_EVENT_SHOW,
            boss_bar_title="Ender Dragon",
            filtered_boss_bar_title="Ender Dragon",
            health_percentage=0.75,
            screen_darkening=1,
            colour=2,
            overlay=0,
        )
        result = _roundtrip(pk)
        assert result.event_type == BOSS_EVENT_SHOW
        assert result.boss_bar_title == "Ender Dragon"
        assert abs(result.health_percentage - 0.75) < 0.001
        assert result.colour == 2

    def test_roundtrip_hide(self):
        from pymc.proto.packet.boss_event import BossEvent, BOSS_EVENT_HIDE
        pk = BossEvent(boss_entity_unique_id=1, event_type=BOSS_EVENT_HIDE)
        result = _roundtrip(pk)
        assert result.event_type == BOSS_EVENT_HIDE

    def test_roundtrip_register_player(self):
        from pymc.proto.packet.boss_event import BossEvent, BOSS_EVENT_REGISTER_PLAYER
        pk = BossEvent(
            boss_entity_unique_id=1,
            event_type=BOSS_EVENT_REGISTER_PLAYER,
            player_unique_id=42,
        )
        result = _roundtrip(pk)
        assert result.event_type == BOSS_EVENT_REGISTER_PLAYER
        assert result.player_unique_id == 42

    def test_roundtrip_health_percentage(self):
        from pymc.proto.packet.boss_event import BossEvent, BOSS_EVENT_HEALTH_PERCENTAGE
        pk = BossEvent(
            boss_entity_unique_id=1,
            event_type=BOSS_EVENT_HEALTH_PERCENTAGE,
            health_percentage=0.5,
        )
        result = _roundtrip(pk)
        assert abs(result.health_percentage - 0.5) < 0.001

    def test_roundtrip_title(self):
        from pymc.proto.packet.boss_event import BossEvent, BOSS_EVENT_TITLE
        pk = BossEvent(
            boss_entity_unique_id=1,
            event_type=BOSS_EVENT_TITLE,
            boss_bar_title="Wither",
            filtered_boss_bar_title="Wither",
        )
        result = _roundtrip(pk)
        assert result.boss_bar_title == "Wither"

    def test_roundtrip_texture(self):
        from pymc.proto.packet.boss_event import BossEvent, BOSS_EVENT_TEXTURE
        pk = BossEvent(
            boss_entity_unique_id=1,
            event_type=BOSS_EVENT_TEXTURE,
            colour=3,
            overlay=1,
        )
        result = _roundtrip(pk)
        assert result.colour == 3
        assert result.overlay == 1


# ── BookEdit ──

class TestBookEdit:
    def test_roundtrip_replace_page(self):
        from pymc.proto.packet.book_edit import BookEdit, BOOK_ACTION_REPLACE_PAGE
        pk = BookEdit(
            inventory_slot=0,
            action_type=BOOK_ACTION_REPLACE_PAGE,
            page_number=3,
            text="Hello world",
            photo_name="photo1",
        )
        result = _roundtrip(pk)
        assert result.action_type == BOOK_ACTION_REPLACE_PAGE
        assert result.page_number == 3
        assert result.text == "Hello world"
        assert result.photo_name == "photo1"

    def test_roundtrip_delete_page(self):
        from pymc.proto.packet.book_edit import BookEdit, BOOK_ACTION_DELETE_PAGE
        pk = BookEdit(inventory_slot=1, action_type=BOOK_ACTION_DELETE_PAGE, page_number=5)
        result = _roundtrip(pk)
        assert result.page_number == 5

    def test_roundtrip_swap_pages(self):
        from pymc.proto.packet.book_edit import BookEdit, BOOK_ACTION_SWAP_PAGES
        pk = BookEdit(
            inventory_slot=0,
            action_type=BOOK_ACTION_SWAP_PAGES,
            page_number=2,
            secondary_page_number=7,
        )
        result = _roundtrip(pk)
        assert result.page_number == 2
        assert result.secondary_page_number == 7

    def test_roundtrip_sign(self):
        from pymc.proto.packet.book_edit import BookEdit, BOOK_ACTION_SIGN
        pk = BookEdit(
            inventory_slot=0,
            action_type=BOOK_ACTION_SIGN,
            title="My Book",
            author="Steve",
            xuid="12345",
        )
        result = _roundtrip(pk)
        assert result.title == "My Book"
        assert result.author == "Steve"
        assert result.xuid == "12345"


# ── CommandBlockUpdate ──

class TestCommandBlockUpdate:
    def test_roundtrip_block(self):
        from pymc.proto.packet.command_block_update import CommandBlockUpdate, COMMAND_BLOCK_REPEATING
        pk = CommandBlockUpdate(
            block=True,
            position=BlockPos(10, 64, 20),
            mode=COMMAND_BLOCK_REPEATING,
            needs_redstone=True,
            conditional=False,
            command="say hello",
            last_output="hello",
            name="test_block",
            filtered_name="test_block",
            should_track_output=True,
            tick_delay=10,
            execute_on_first_tick=True,
        )
        result = _roundtrip(pk)
        assert result.block is True
        assert result.position == BlockPos(10, 64, 20)
        assert result.mode == COMMAND_BLOCK_REPEATING
        assert result.command == "say hello"

    def test_roundtrip_minecart(self):
        from pymc.proto.packet.command_block_update import CommandBlockUpdate
        pk = CommandBlockUpdate(
            block=False,
            minecart_entity_runtime_id=999,
            command="tp @s 0 64 0",
            last_output="",
            name="cart_cmd",
            filtered_name="",
            should_track_output=False,
            tick_delay=0,
            execute_on_first_tick=False,
        )
        result = _roundtrip(pk)
        assert result.block is False
        assert result.minecart_entity_runtime_id == 999
        assert result.command == "tp @s 0 64 0"


# ── PlayerLocation ──

class TestPlayerLocation:
    def test_roundtrip_coordinates(self):
        from pymc.proto.packet.player_location import PlayerLocation, PLAYER_LOCATION_TYPE_COORDINATES
        pk = PlayerLocation(
            type=PLAYER_LOCATION_TYPE_COORDINATES,
            entity_unique_id=42,
            position=Vec3(10.0, 64.0, 20.0),
        )
        result = _roundtrip(pk)
        assert result.type == PLAYER_LOCATION_TYPE_COORDINATES
        assert abs(result.position.x - 10.0) < 0.001

    def test_roundtrip_hide(self):
        from pymc.proto.packet.player_location import PlayerLocation, PLAYER_LOCATION_TYPE_HIDE
        pk = PlayerLocation(type=PLAYER_LOCATION_TYPE_HIDE, entity_unique_id=7)
        result = _roundtrip(pk)
        assert result.type == PLAYER_LOCATION_TYPE_HIDE
        assert result.position == Vec3(0.0, 0.0, 0.0)


# ── PlayerUpdateEntityOverrides ──

class TestPlayerUpdateEntityOverrides:
    def test_roundtrip_int(self):
        from pymc.proto.packet.player_update_entity_overrides import (
            PlayerUpdateEntityOverrides, PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_INT,
        )
        pk = PlayerUpdateEntityOverrides(
            entity_unique_id=1,
            property_index=5,
            type=PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_INT,
            int_value=42,
        )
        result = _roundtrip(pk)
        assert result.int_value == 42
        assert result.float_value == 0.0

    def test_roundtrip_float(self):
        from pymc.proto.packet.player_update_entity_overrides import (
            PlayerUpdateEntityOverrides, PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_FLOAT,
        )
        pk = PlayerUpdateEntityOverrides(
            entity_unique_id=1,
            property_index=3,
            type=PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_FLOAT,
            float_value=3.14,
        )
        result = _roundtrip(pk)
        assert abs(result.float_value - 3.14) < 0.01
        assert result.int_value == 0

    def test_roundtrip_clear_all(self):
        from pymc.proto.packet.player_update_entity_overrides import (
            PlayerUpdateEntityOverrides, PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_CLEAR_ALL,
        )
        pk = PlayerUpdateEntityOverrides(
            entity_unique_id=1,
            property_index=0,
            type=PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_CLEAR_ALL,
        )
        result = _roundtrip(pk)
        assert result.type == PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_CLEAR_ALL


# ── PlayerVideoCapture ──

class TestPlayerVideoCapture:
    def test_roundtrip_stop(self):
        from pymc.proto.packet.player_video_capture import (
            PlayerVideoCapture, PLAYER_VIDEO_CAPTURE_ACTION_STOP,
        )
        pk = PlayerVideoCapture(action=PLAYER_VIDEO_CAPTURE_ACTION_STOP)
        result = _roundtrip(pk)
        assert result.action == PLAYER_VIDEO_CAPTURE_ACTION_STOP
        assert result.frame_rate == 0
        assert result.file_prefix == ""

    def test_roundtrip_start(self):
        from pymc.proto.packet.player_video_capture import (
            PlayerVideoCapture, PLAYER_VIDEO_CAPTURE_ACTION_START,
        )
        pk = PlayerVideoCapture(
            action=PLAYER_VIDEO_CAPTURE_ACTION_START,
            frame_rate=30,
            file_prefix="capture_",
        )
        result = _roundtrip(pk)
        assert result.frame_rate == 30
        assert result.file_prefix == "capture_"


# ── ClientBoundDebugRenderer ──

class TestClientBoundDebugRenderer:
    def test_roundtrip_clear(self):
        from pymc.proto.packet.client_bound_debug_renderer import (
            ClientBoundDebugRenderer, CLIENT_BOUND_DEBUG_RENDERER_CLEAR,
        )
        pk = ClientBoundDebugRenderer(type=CLIENT_BOUND_DEBUG_RENDERER_CLEAR)
        result = _roundtrip(pk)
        assert result.type == CLIENT_BOUND_DEBUG_RENDERER_CLEAR

    def test_roundtrip_add_cube(self):
        from pymc.proto.packet.client_bound_debug_renderer import (
            ClientBoundDebugRenderer, CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE,
        )
        pk = ClientBoundDebugRenderer(
            type=CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE,
            text="debug marker",
            position=Vec3(1.0, 2.0, 3.0),
            red=1.0,
            green=0.5,
            blue=0.0,
            alpha=1.0,
            duration=5000,
        )
        result = _roundtrip(pk)
        assert result.type == CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE
        assert result.text == "debug marker"
        assert result.duration == 5000
        assert abs(result.green - 0.5) < 0.001


# ── Animate ──

class TestAnimate:
    def test_roundtrip_no_swing_source(self):
        from pymc.proto.packet.animate import Animate, ANIMATE_ACTION_SWING_ARM
        pk = Animate(
            action_type=ANIMATE_ACTION_SWING_ARM,
            entity_runtime_id=5,
            data=0.0,
            swing_source=0,
        )
        result = _roundtrip(pk)
        assert result.action_type == ANIMATE_ACTION_SWING_ARM
        assert result.swing_source == 0

    def test_roundtrip_with_swing_source(self):
        from pymc.proto.packet.animate import Animate, ANIMATE_ACTION_SWING_ARM, ANIMATE_SWING_SOURCE_ATTACK
        pk = Animate(
            action_type=ANIMATE_ACTION_SWING_ARM,
            entity_runtime_id=5,
            data=0.0,
            swing_source=ANIMATE_SWING_SOURCE_ATTACK,
        )
        result = _roundtrip(pk)
        assert result.swing_source == ANIMATE_SWING_SOURCE_ATTACK


# ── MoveActorDelta ──

class TestMoveActorDelta:
    def test_roundtrip_full(self):
        from pymc.proto.packet.move_actor_delta import (
            MoveActorDelta,
            MOVE_ACTOR_DELTA_FLAG_HAS_X,
            MOVE_ACTOR_DELTA_FLAG_HAS_Y,
            MOVE_ACTOR_DELTA_FLAG_HAS_Z,
            MOVE_ACTOR_DELTA_FLAG_HAS_ROT_X,
            MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Y,
        )
        flags = (
            MOVE_ACTOR_DELTA_FLAG_HAS_X
            | MOVE_ACTOR_DELTA_FLAG_HAS_Y
            | MOVE_ACTOR_DELTA_FLAG_HAS_Z
            | MOVE_ACTOR_DELTA_FLAG_HAS_ROT_X
            | MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Y
        )
        pk = MoveActorDelta(
            entity_runtime_id=10,
            flags=flags,
            position=Vec3(1.0, 2.0, 3.0),
            rotation=Vec3(45.0, 90.0, 0.0),
        )
        result = _roundtrip(pk)
        assert abs(result.position.x - 1.0) < 0.001
        assert abs(result.position.y - 2.0) < 0.001
        assert abs(result.position.z - 3.0) < 0.001
        # byte_float has limited precision (360/256 resolution)
        assert abs(result.rotation.x - 45.0) < 2.0
        assert abs(result.rotation.y - 90.0) < 2.0
        assert result.rotation.z == 0.0

    def test_roundtrip_partial(self):
        from pymc.proto.packet.move_actor_delta import (
            MoveActorDelta, MOVE_ACTOR_DELTA_FLAG_HAS_X,
        )
        pk = MoveActorDelta(
            entity_runtime_id=10,
            flags=MOVE_ACTOR_DELTA_FLAG_HAS_X,
            position=Vec3(5.0, 0.0, 0.0),
        )
        result = _roundtrip(pk)
        assert abs(result.position.x - 5.0) < 0.001
        assert result.position.y == 0.0
        assert result.position.z == 0.0


# ── ModalFormResponse ──

class TestModalFormResponse:
    def test_roundtrip_with_response(self):
        from pymc.proto.packet.modal_form_response import ModalFormResponse
        pk = ModalFormResponse(
            form_id=1,
            response_data=b'{"0":1}',
            cancel_reason=None,
        )
        result = _roundtrip(pk)
        assert result.form_id == 1
        assert result.response_data == b'{"0":1}'
        assert result.cancel_reason is None

    def test_roundtrip_cancelled(self):
        from pymc.proto.packet.modal_form_response import (
            ModalFormResponse, MODAL_FORM_CANCEL_REASON_USER_CLOSED,
        )
        pk = ModalFormResponse(
            form_id=2,
            response_data=None,
            cancel_reason=MODAL_FORM_CANCEL_REASON_USER_CLOSED,
        )
        result = _roundtrip(pk)
        assert result.response_data is None
        assert result.cancel_reason == MODAL_FORM_CANCEL_REASON_USER_CLOSED


# ── SyncWorldClocks ──

class TestSyncWorldClocks:
    def test_roundtrip_remove_time_marker(self):
        from pymc.proto.packet.sync_world_clocks import (
            SyncWorldClocks, CLOCK_PAYLOAD_TYPE_REMOVE_TIME_MARKER,
        )
        pk = SyncWorldClocks(
            payload_type=CLOCK_PAYLOAD_TYPE_REMOVE_TIME_MARKER,
            remove_clock_id=42,
            remove_time_marker_ids=[1, 2, 3],
        )
        result = _roundtrip(pk)
        assert result.payload_type == CLOCK_PAYLOAD_TYPE_REMOVE_TIME_MARKER
        assert result.remove_clock_id == 42
        assert result.remove_time_marker_ids == [1, 2, 3]


# ── ClientBoundAttributeLayerSync ──

class TestClientBoundAttributeLayerSync:
    def test_roundtrip_remove_environment(self):
        from pymc.proto.packet.client_bound_attribute_layer_sync import (
            ClientBoundAttributeLayerSync,
            ATTRIBUTE_LAYER_PAYLOAD_TYPE_REMOVE_ENVIRONMENT,
        )
        pk = ClientBoundAttributeLayerSync(
            payload_type=ATTRIBUTE_LAYER_PAYLOAD_TYPE_REMOVE_ENVIRONMENT,
            layer_name="test_layer",
            dimension_id=0,
            remove_attribute_names=["attr1", "attr2"],
        )
        result = _roundtrip(pk)
        assert result.layer_name == "test_layer"
        assert result.dimension_id == 0
        assert result.remove_attribute_names == ["attr1", "attr2"]


# ── CameraInstruction ──

class TestCameraInstruction:
    def test_roundtrip_basic(self):
        from pymc.proto.packet.camera_instruction import CameraInstruction
        pk = CameraInstruction(
            clear=True,
            attach_to_entity=42,
            detach_from_entity=None,
        )
        result = _roundtrip(pk)
        assert result.clear is True
        assert result.attach_to_entity == 42
        assert result.detach_from_entity is None
