"""Offline session evidence gate. No transport and no claim of authentication.

Input must already pass cryptographic framing and inner checksum validation.
Unknown identity metadata is retained but never treated as permissions.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from .inputs import decode_inputs


def identifier_bytes(value: str) -> bytes:
    if (
        not isinstance(value, str)
        or len(value) != 8
        or any(c not in "0123456789abcdefABCDEF" for c in value)
    ):
        raise ValueError("Identifier must contain exactly eight hex characters")
    return bytes.fromhex(value)


@dataclass(frozen=True)
class IdentityReply:
    panel_id: bytes
    metadata: bytes


@dataclass(frozen=True)
class OnlineDisplayReply:
    status: int
    display_bytes: bytes = field(repr=False)


def parse_online_display(opcode: int, body: bytes) -> OnlineDisplayReply:
    """Observed 6b/73 profile routed to DLOADX's 32-position display renderer.

    Status semantics/character encoding are not yet fully established.
    Control bytes below 0x20 can occur; do not interpret as plain UTF-8.
    This reply is not proof of authentication or fresh input data.
    """
    if opcode != 0x6B or len(body) != 34 or body[0] != 0x73:
        raise ValueError("Unsupported online display reply")
    return OnlineDisplayReply(body[1], bytes(body[2:34]))


def parse_identity(opcode: int, body: bytes, expected_panel_id: bytes) -> IdentityReply:
    if opcode not in (0x73, 0x66) or len(body) != 13 or len(expected_panel_id) != 4:
        raise ValueError("Unsupported identity reply profile")
    if body[:4] != expected_panel_id:
        raise ValueError("Unexpected panel identity")
    return IdentityReply(bytes(body[:4]), bytes(body[4:]))


class Phase(Enum):
    DISCONNECTED = auto()
    WAIT_IDENTITY = auto()
    IDENTIFIED = auto()
    READ_CONFIRMED = auto()
    FAILED = auto()


class CommandRejected(ValueError):
    """Observed native receiver error branches; not a login-specific verdict."""

    def __init__(self, opcode):
        self.opcode = opcode
        super().__init__({0x62: "Invalid command", 0x64: "Command unavailable"}[opcode])


class SessionEvidence:
    """Local policy: matching identity alone never publishes input states.

    This is a testable boundary for a future client, not DLOADX's complete FSM.
    A session must be explicitly reset after disconnect or any rejected reply.
    """

    def __init__(self, panel_id: bytes, input_numbers: list[int]):
        if len(panel_id) != 4:
            raise ValueError("Invalid panel identifier")
        decode_inputs(bytes([1]) + bytes(20), input_numbers)
        self.panel_id = bytes(panel_id)
        self.input_numbers = list(input_numbers)
        self.phase = Phase.DISCONNECTED
        self.inputs = None

    def begin(self):
        if self.phase != Phase.DISCONNECTED:
            raise ValueError("Session must be disconnected before starting")
        self.phase = Phase.WAIT_IDENTITY

    def receive(self, opcode: int, body: bytes):
        try:
            if opcode in (0x62, 0x64):
                raise CommandRejected(opcode)
            if opcode == 0x73 and self.phase == Phase.WAIT_IDENTITY:
                reply = parse_identity(opcode, body, self.panel_id)
                self.phase = Phase.IDENTIFIED
                return reply
            if opcode == 0x6B and self.phase in (Phase.IDENTIFIED, Phase.READ_CONFIRMED):
                return parse_online_display(opcode, body)
            if opcode == 0x71 and self.phase in (Phase.IDENTIFIED, Phase.READ_CONFIRMED):
                states = decode_inputs(body, self.input_numbers)
                self.inputs = states
                self.phase = Phase.READ_CONFIRMED
                return states
            raise ValueError("Unexpected reply for evidence gate")
        except ValueError:
            self.inputs = None
            self.phase = Phase.FAILED
            raise

    def disconnect(self):
        self.inputs = None
        self.phase = Phase.DISCONNECTED
