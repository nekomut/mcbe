"""Packet encryption/decryption using AES-256-CTR with SHA-256 checksums.

Mirrors gophertunnel/minecraft/protocol/packet/encryption.go.

Flow (matching Go):
  Encoder: encrypt(full_batch) → encrypts bytes[1:], appends checksum before encrypting
  Decoder: receives data[1:] (header stripped), decrypt_and_verify() → decrypts, verifies, strips checksum
"""

from __future__ import annotations

import hashlib
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class PacketEncrypt:
    """Handles packet encryption with integrity checksums (encoder side)."""

    def __init__(self, key_bytes: bytes) -> None:
        if len(key_bytes) != 32:
            raise ValueError(f"key must be 32 bytes, got {len(key_bytes)}")
        self._key_bytes = key_bytes
        self._counter: int = 0

        # AES-256-CTR: IV = first 12 bytes of key + [0, 0, 0, 2]
        iv = key_bytes[:12] + b"\x00\x00\x00\x02"
        cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(iv))
        self._stream = cipher.encryptor()

    def encrypt(self, data: bytearray) -> bytearray:
        """Encrypt batch data. Byte 0 is NOT encrypted; bytes 1+ are.

        Appends 8-byte checksum before encrypting.
        """
        counter_bytes = struct.pack("<Q", self._counter)
        self._counter += 1

        # Checksum over plaintext: SHA256(counter || data[1:] || key)[:8]
        h = hashlib.sha256()
        h.update(counter_bytes)
        h.update(data[1:])
        h.update(self._key_bytes)
        checksum = h.digest()[:8]

        data.extend(checksum)

        # Encrypt bytes 1+ (payload + checksum), skip header byte
        encrypted = self._stream.update(bytes(data[1:]))
        data[1:] = encrypted
        return data


class PacketDecrypt:
    """Handles packet decryption with integrity verification (decoder side)."""

    def __init__(self, key_bytes: bytes) -> None:
        if len(key_bytes) != 32:
            raise ValueError(f"key must be 32 bytes, got {len(key_bytes)}")
        self._key_bytes = key_bytes
        self._counter: int = 0

        iv = key_bytes[:12] + b"\x00\x00\x00\x02"
        cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(iv))
        self._stream = cipher.encryptor()  # CTR is symmetric

    def decrypt_and_verify(self, data: bytes) -> bytes:
        """Decrypt data (without header byte) and verify checksum.

        Returns decrypted payload with checksum stripped.
        Raises ValueError if checksum is invalid.
        """
        # Decrypt
        decrypted = bytearray(self._stream.update(data))

        # Verify checksum
        if len(decrypted) < 8:
            raise ValueError(
                f"encrypted packet must be at least 8 bytes, got {len(decrypted)}"
            )
        received_sum = bytes(decrypted[-8:])
        payload = bytes(decrypted[:-8])

        counter_bytes = struct.pack("<Q", self._counter)
        self._counter += 1

        h = hashlib.sha256()
        h.update(counter_bytes)
        h.update(payload)
        h.update(self._key_bytes)
        expected_sum = h.digest()[:8]

        if received_sum != expected_sum:
            raise ValueError(
                f"invalid checksum for packet {self._counter - 1}: "
                f"expected {expected_sum.hex()}, got {received_sum.hex()}"
            )

        return payload


def derive_key(salt: bytes, shared_secret: bytes) -> bytes:
    """Derive 32-byte encryption key: SHA256(salt || sharedSecret)."""
    return hashlib.sha256(salt + shared_secret).digest()


def compute_shared_secret(private_key, peer_public_key) -> bytes:
    """Compute ECDH shared secret using P-384 keys. Returns 48 bytes."""
    from cryptography.hazmat.primitives.asymmetric import ec

    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    return shared_key.rjust(48, b"\x00")
