"""Tests for text formatting module."""

from pymc.text.formatting import (
    BOLD, RED, RESET, clean, colourf, to_ansi,
)


class TestClean:
    def test_removes_colour_codes(self):
        assert clean("§cHello §aWorld") == "Hello World"

    def test_no_codes(self):
        assert clean("Hello World") == "Hello World"

    def test_all_codes(self):
        assert clean("§0§1§2§3§4§5§6§7§8§9§a§b§c§d§e§f§r") == ""

    def test_preserves_non_codes(self):
        assert clean("§zHello") == "§zHello"


class TestToAnsi:
    def test_converts_red(self):
        result = to_ansi("§cHello")
        assert "\x1b[38;5;203m" in result
        assert "Hello" in result

    def test_bold(self):
        result = to_ansi("§lBold")
        assert "\x1b[1m" in result

    def test_reset(self):
        result = to_ansi("§r")
        assert "\x1b[m" in result


class TestColourf:
    def test_simple_tag(self):
        result = colourf("<red>Hello</red>")
        assert RED in result
        assert "Hello" in result

    def test_nested_tags(self):
        result = colourf("<red>Hello <bold>World</bold></red>")
        assert RED in result
        assert BOLD in result
        assert "Hello" in result
        assert "World" in result

    def test_unknown_tag_literal(self):
        result = colourf("<unknown>text</unknown>")
        assert "<unknown>" in result

    def test_no_tags(self):
        result = colourf("plain text")
        assert "plain text" in result


class TestResourceManifest:
    def test_manifest_parse(self):
        from pymc.resource.manifest import Manifest

        json_str = """{
            "format_version": 2,
            "header": {
                "name": "Test Pack",
                "description": "A test",
                "uuid": "abc-123",
                "version": [1, 0, 0],
                "min_engine_version": [1, 21, 0]
            },
            "modules": [
                {"uuid": "mod-1", "type": "resources", "version": [1, 0, 0]}
            ],
            "dependencies": [
                {"uuid": "dep-1", "version": "1.0.0"}
            ]
        }"""
        m = Manifest.parse(json_str)
        assert m.header.name == "Test Pack"
        assert m.header.uuid == "abc-123"
        assert str(m.header.version) == "1.0.0"
        assert len(m.modules) == 1
        assert m.modules[0].type == "resources"
        assert m.has_textures()
        assert not m.has_behaviours()
        assert len(m.dependencies) == 1
        assert str(m.dependencies[0].version) == "1.0.0"

    def test_version_string_format(self):
        from pymc.resource.manifest import Version

        v = Version.from_json("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_version_array_format(self):
        from pymc.resource.manifest import Version

        v = Version.from_json([1, 0, 5])
        assert str(v) == "1.0.5"
