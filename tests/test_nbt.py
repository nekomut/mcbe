"""Tests for NBT encode/decode round-trip correctness."""

from pymc.nbt import BigEndian, LittleEndian, NetworkLittleEndian, decode, encode


class TestNetworkLittleEndian:
    def test_empty_compound(self):
        data = encode({})
        result = decode(data)
        assert result == {}

    def test_byte(self):
        data = encode({"val": 42})
        result = decode(data)
        assert result["val"] == 42

    def test_string(self):
        data = encode({"name": "hello"})
        result = decode(data)
        assert result["name"] == "hello"

    def test_nested_compound(self):
        original = {"outer": {"inner": 123}}
        data = encode(original)
        result = decode(data)
        assert result["outer"]["inner"] == 123

    def test_list_of_ints(self):
        original = {"values": [10, 20, 30]}
        data = encode(original)
        result = decode(data)
        assert result["values"] == [10, 20, 30]

    def test_list_of_strings(self):
        original = {"names": ["alice", "bob"]}
        data = encode(original)
        result = decode(data)
        assert result["names"] == ["alice", "bob"]

    def test_empty_list(self):
        original = {"items": []}
        data = encode(original)
        result = decode(data)
        assert result["items"] == []

    def test_byte_array(self):
        original = {"data": b"\x01\x02\x03"}
        data = encode(original)
        result = decode(data)
        assert result["data"] == b"\x01\x02\x03"

    def test_float(self):
        original = {"x": 3.14}
        data = encode(original)
        result = decode(data)
        assert abs(result["x"] - 3.14) < 1e-5

    def test_bool(self):
        original = {"flag": True}
        data = encode(original)
        result = decode(data)
        assert result["flag"] == 1  # NBT stores bools as bytes

    def test_mixed_compound(self):
        original = {
            "name": "test",
            "x": 100,
            "nested": {"a": 1, "b": "two"},
            "list": [10, 20],
        }
        data = encode(original)
        result = decode(data)
        assert result["name"] == "test"
        assert result["x"] == 100
        assert result["nested"]["a"] == 1
        assert result["nested"]["b"] == "two"
        assert result["list"] == [10, 20]

    def test_allow_zero(self):
        result = decode(b"\x00", allow_zero=True)
        assert result == {}

    def test_large_int(self):
        original = {"big": 2147483647}
        data = encode(original)
        result = decode(data)
        assert result["big"] == 2147483647

    def test_long(self):
        original = {"huge": 9999999999}
        data = encode(original)
        result = decode(data)
        assert result["huge"] == 9999999999

    def test_negative_int(self):
        original = {"neg": -100}
        data = encode(original)
        result = decode(data)
        assert result["neg"] == -100


class TestLittleEndian:
    def test_roundtrip(self):
        original = {"name": "world", "value": 42}
        data = encode(original, encoding=LittleEndian)
        result = decode(data, encoding=LittleEndian)
        assert result["name"] == "world"
        assert result["value"] == 42

    def test_nested(self):
        original = {"pos": {"x": 1, "y": 2, "z": 3}}
        data = encode(original, encoding=LittleEndian)
        result = decode(data, encoding=LittleEndian)
        assert result["pos"] == {"x": 1, "y": 2, "z": 3}


class TestBigEndian:
    def test_roundtrip(self):
        original = {"hello": "world", "num": 12345}
        data = encode(original, encoding=BigEndian)
        result = decode(data, encoding=BigEndian)
        assert result["hello"] == "world"
        assert result["num"] == 12345

    def test_list(self):
        original = {"items": [1, 2, 3]}
        data = encode(original, encoding=BigEndian)
        result = decode(data, encoding=BigEndian)
        assert result["items"] == [1, 2, 3]
