"""Tests for packet encryption/decryption."""

import os

from cryptography.hazmat.primitives.asymmetric import ec

from pymc.proto.encryption import (
    PacketDecrypt,
    PacketEncrypt,
    compute_shared_secret,
    derive_key,
)


class TestEncryptDecrypt:
    def test_roundtrip(self):
        key = os.urandom(32)
        enc = PacketEncrypt(key)
        dec = PacketDecrypt(key)

        original = bytearray(b"\xfe\x01\x02\x03\x04\x05")
        data = bytearray(original)
        enc.encrypt(data)

        # Header byte should be unchanged
        assert data[0] == 0xFE
        # Data should be longer (8-byte checksum appended)
        assert len(data) == len(original) + 8

        # Decrypt (pass data[1:] as decoder receives without header)
        payload = dec.decrypt_and_verify(bytes(data[1:]))
        assert payload == bytes(original[1:])

    def test_multiple_packets(self):
        key = os.urandom(32)
        enc = PacketEncrypt(key)
        dec = PacketDecrypt(key)

        for i in range(10):
            original = bytearray(b"\xfe") + bytearray(os.urandom(20))
            data = bytearray(original)
            enc.encrypt(data)

            payload = dec.decrypt_and_verify(bytes(data[1:]))
            assert payload == bytes(original[1:])

    def test_tampered_checksum_raises(self):
        key = os.urandom(32)
        enc = PacketEncrypt(key)
        dec = PacketDecrypt(key)

        data = bytearray(b"\xfe\x01\x02\x03")
        enc.encrypt(data)

        # Tamper with last byte (checksum)
        tampered = bytearray(data[1:])
        tampered[-1] ^= 0xFF
        try:
            dec.decrypt_and_verify(bytes(tampered))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "invalid checksum" in str(e)

    def test_counter_mismatch_raises(self):
        key = os.urandom(32)
        enc = PacketEncrypt(key)
        dec = PacketDecrypt(key)

        data1 = bytearray(b"\xfe\x01")
        data2 = bytearray(b"\xfe\x02")
        enc.encrypt(data1)
        enc.encrypt(data2)

        # Skip first packet, try to decrypt second → counter mismatch
        try:
            dec.decrypt_and_verify(bytes(data2[1:]))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_short_data_raises(self):
        key = os.urandom(32)
        dec = PacketDecrypt(key)
        try:
            dec.decrypt_and_verify(b"\x01\x02\x03")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "at least 8 bytes" in str(e)

    def test_invalid_key_length(self):
        try:
            PacketEncrypt(b"\x00" * 16)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            PacketDecrypt(b"\x00" * 16)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestDeriveKey:
    def test_deterministic(self):
        salt = b"\x01" * 16
        secret = b"\x02" * 48
        k1 = derive_key(salt, secret)
        k2 = derive_key(salt, secret)
        assert k1 == k2
        assert len(k1) == 32

    def test_different_salt(self):
        secret = b"\x02" * 48
        k1 = derive_key(b"\x01" * 16, secret)
        k2 = derive_key(b"\x03" * 16, secret)
        assert k1 != k2


class TestComputeSharedSecret:
    def test_ecdh_symmetric(self):
        key_a = ec.generate_private_key(ec.SECP384R1())
        key_b = ec.generate_private_key(ec.SECP384R1())

        secret_ab = compute_shared_secret(key_a, key_b.public_key())
        secret_ba = compute_shared_secret(key_b, key_a.public_key())
        assert secret_ab == secret_ba
        assert len(secret_ab) == 48

    def test_full_handshake_flow(self):
        """Simulate complete key exchange and encrypted communication."""
        key_server = ec.generate_private_key(ec.SECP384R1())
        key_client = ec.generate_private_key(ec.SECP384R1())
        salt = os.urandom(16)

        secret_s = compute_shared_secret(key_server, key_client.public_key())
        secret_c = compute_shared_secret(key_client, key_server.public_key())

        key_s = derive_key(salt, secret_s)
        key_c = derive_key(salt, secret_c)
        assert key_s == key_c

        # Server encrypts, client decrypts
        enc = PacketEncrypt(key_s)
        dec = PacketDecrypt(key_c)

        original = bytearray(b"\xfe\x01\x02\x03")
        data = bytearray(original)
        enc.encrypt(data)
        payload = dec.decrypt_and_verify(bytes(data[1:]))
        assert payload == bytes(original[1:])
