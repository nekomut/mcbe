"""Monkey-patches for aiortc to improve compatibility with Minecraft BDS.

Patches applied:
1. Reduce SCTP stream counts from 65535 to 1024 (matches libwebrtc default).
2. Increase max-message-size from 65536 to 262144 (matches libdatachannel).
3. Fix DCEP OPEN ordered flag to match channel configuration (RFC 8832).
4. Reduce stream counts in new RTCSctpTransport instances.
5. Add SCTP chunk logging for diagnostics.
6. Log TURN allocation failures.
7. Discard unauthenticated STUN error responses (RFC 8489 §9.1.4).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_patched = False


def apply():
    """Apply all aiortc patches. Safe to call multiple times."""
    global _patched
    if _patched:
        return
    _patched = True

    import aiortc.rtcsctptransport as sctp

    # 1. Reduce stream counts to match libwebrtc defaults.
    old_max = sctp.MAX_STREAMS
    sctp.MAX_STREAMS = 1024
    logger.info("aiortc patch: MAX_STREAMS %d -> %d", old_max, sctp.MAX_STREAMS)

    # 2. Increase max-message-size to 262144 (matches libdatachannel).
    #    Without this, the server sees max-message-size:65536 in SDP and ABORTs
    #    when trying to send large packets (e.g. StartGame ~222KB).
    old_max_msg = sctp.RTCSctpTransport.getCapabilities().maxMessageSize
    sctp.RTCSctpTransport.getCapabilities = classmethod(
        lambda cls: sctp.RTCSctpCapabilities(maxMessageSize=262144)
    )
    logger.info("aiortc patch: maxMessageSize %d -> %d", old_max_msg, 262144)

    # 3. Fix DCEP OPEN: pass ordered=channel.ordered so SCTP flags match DCEP channel_type.
    #    Without this fix, unordered DataChannels send DCEP OPEN with SCTP ordered flag,
    #    which contradicts channel_type=0x81 (unordered).
    _original_data_channel_flush = sctp.RTCSctpTransport._data_channel_flush

    async def _patched_data_channel_flush(self):
        _original_send = self._send

        async def _send_with_ordered_fix(stream_id, pp_id, user_data, **kwargs):
            if pp_id == sctp.WEBRTC_DCEP and "ordered" not in kwargs:
                channel = self._data_channels.get(stream_id)
                if channel is not None:
                    kwargs["ordered"] = channel.ordered
            return await _original_send(stream_id, pp_id, user_data, **kwargs)

        self._send = _send_with_ordered_fix
        try:
            await _original_data_channel_flush(self)
        finally:
            self._send = _original_send

    sctp.RTCSctpTransport._data_channel_flush = _patched_data_channel_flush

    # 4. Patch __init__ to apply reduced stream counts to new instances.
    _original_transport_init = sctp.RTCSctpTransport.__init__

    def _patched_transport_init(self, transport, port=5000):
        _original_transport_init(self, transport, port)
        self._inbound_streams_max = sctp.MAX_STREAMS
        self._outbound_streams_count = sctp.MAX_STREAMS

    sctp.RTCSctpTransport.__init__ = _patched_transport_init

    # 5. Add SCTP chunk logging for diagnostics.
    _original_receive_chunk = sctp.RTCSctpTransport._receive_chunk

    async def _patched_receive_chunk(self, chunk):
        chunk_name = type(chunk).__name__
        extra = ""
        if isinstance(chunk, (sctp.InitChunk, sctp.InitAckChunk)):
            extra = (
                f" tag={chunk.initiate_tag} rwnd={chunk.advertised_rwnd}"
                f" os={chunk.outbound_streams} mis={chunk.inbound_streams}"
                f" tsn={chunk.initial_tsn}"
            )
        elif isinstance(chunk, sctp.AbortChunk):
            extra = f" params={chunk.params}"

        if isinstance(chunk, sctp.AbortChunk):
            logger.warning("SCTP recv chunk: %s%s", chunk_name, extra)
        else:
            logger.debug("SCTP recv chunk: %s%s", chunk_name, extra)
        await _original_receive_chunk(self, chunk)

    sctp.RTCSctpTransport._receive_chunk = _patched_receive_chunk

    logger.info("aiortc SCTP patches applied")

    # 6. Log TURN allocation failures (aioice silently swallows them).
    import aioice.ice as _ice
    _original_relayed_candidate = _ice.relayed_candidate

    async def _logged_relayed_candidate(*args, **kwargs):
        try:
            return await _original_relayed_candidate(*args, **kwargs)
        except Exception as e:
            turn_server = kwargs.get("turn_server") or (args[2] if len(args) > 2 else "?")
            turn_transport = kwargs.get("turn_transport") or (args[6] if len(args) > 6 else "?")
            logger.warning(
                "TURN allocation failed (server=%s transport=%s): %s: %s",
                turn_server, turn_transport, type(e).__name__, e,
            )
            raise

    _ice.relayed_candidate = _logged_relayed_candidate
    logger.info("aiortc TURN logging patch applied")

    # 7. Discard unauthenticated STUN error responses (RFC 8489 §9.1.4).
    #
    #    Minecraft BDS (libwebrtc) sends a 401 Unauthorized error WITHOUT
    #    MESSAGE-INTEGRITY before sending the real success response for the
    #    same transaction.  Per RFC 8489 §9.1.4, error responses without
    #    MESSAGE-INTEGRITY MUST be discarded.  aioice does not implement
    #    this, causing the transaction to fail prematurely.
    from aioice import stun as _stun
    _original_response_received = _stun.Transaction.response_received

    def _rfc8489_response_received(self, message, addr):
        if message.message_class == _stun.Class.ERROR:
            if "MESSAGE-INTEGRITY" not in message.attributes:
                logger.debug(
                    "discarding unauthenticated STUN error from %s "
                    "(no MESSAGE-INTEGRITY, RFC 8489 §9.1.4): %s",
                    addr,
                    message.attributes.get("ERROR-CODE", "?"),
                )
                return
        _original_response_received(self, message, addr)

    _stun.Transaction.response_received = _rfc8489_response_received

    logger.info("aiortc ICE patches applied")
