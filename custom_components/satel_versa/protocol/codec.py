"""Experimental VERSA/ETHM codec; profile validated on three local captures."""

from dataclasses import dataclass, field

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

TABLE = bytes.fromhex("030e0f5c4123594f20262e1a2b26204f321c54134745275d4b0a3a1461312c3b")


def derive_key(secret):
    half = bytes(secret)[:12].ljust(12, b" ")
    return half + half


def ecb(key, block, decrypt=False):
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    ctx = cipher.decryptor() if decrypt else cipher.encryptor()
    return ctx.update(block) + ctx.finalize()


def transform(key, data, decrypt=False):
    if len(key) != 24:
        raise ValueError("Expected AES-192 key")
    cv = ecb(key, bytes(16))
    out = bytearray()
    for offset in range(0, len(data), 16):
        block = data[offset : offset + 16]
        if len(block) < 16:
            out.extend(a ^ b for a, b in zip(block, ecb(key, cv)))
        elif decrypt:
            out.extend(a ^ b for a, b in zip(ecb(key, block, True), cv))
            cv = block
        else:
            cv = ecb(key, bytes(a ^ b for a, b in zip(block, cv)))
            out.extend(cv)
    return bytes(out)


def checksum(data):
    value = 0x1510
    for byte in data:
        value = (value + byte) & 0xFFFF
        value = (value >> 1) | ((value & 1) << 15)
    return value


def transform_body(data, nonce, inverse=False):
    out = bytearray()
    state = nonce
    for value in data:
        x, carry, second = (state + 1) & 255, 0, 0
        for step in range(7):
            old = x & 128
            x = ((x << 1) & 255) | bool(carry)
            carry = old
            if step == 1:
                second = x
        state = x ^ second
        key = TABLE[state & 31] ^ (255 if state & 128 else 0)
        mode = (state >> 5) & 3
        if mode == 0:
            value ^= key
        elif mode == 1:
            value += key if inverse else -key
        elif mode == 2:
            value += -key if inverse else key
        elif inverse:
            value ^= key
            value = ((value << 4) | (value >> 4)) & 255
        else:
            value = (((value << 4) | (value >> 4)) & 255) ^ key
        out.append(value & 255)
    return bytes(out)


@dataclass(frozen=True)
class Frame:
    opcode: int
    nonce: int
    body: bytes = field(repr=False)
    consumed: int


def parse_frame(data, offset=0):
    if offset < 0 or len(data) - offset < 3 or data[offset : offset + 2] != b"\x01\x01":
        raise ValueError("Invalid inner header")
    length = data[offset + 2]
    end = offset + 3 + length
    if length < 2 or end + 2 > len(data):
        raise ValueError("Incomplete inner frame")
    if checksum(data[offset + 2 : end]) != int.from_bytes(data[end : end + 2], "big"):
        raise ValueError("Inner checksum mismatch")
    nonce = data[offset + 4]
    return Frame(
        data[offset + 3], nonce, transform_body(data[offset + 5 : end], nonce, True), length + 5
    )


def build_frame(opcode, nonce, body):
    if not 0 <= opcode <= 255 or not 0 <= nonce <= 255 or len(body) > 253:
        raise ValueError("Invalid frame arguments")
    frame = bytes([1, 1, len(body) + 2, opcode, nonce]) + transform_body(body, nonce)
    return frame + checksum(frame[2:]).to_bytes(2, "big")


def request_record(key, token, nonce, opcode, body):
    if not 0 <= token <= 255 or nonce == 0xA1:
        raise ValueError("Invalid token or nonce")
    # Explicitly limited to observed session boundaries, input poll, display query.
    if not (
        (opcode in (0x53, 0x46) and len(body) == 4)
        or (opcode == 0x51 and body == b"\x01")
        or (opcode == 0x4B and body == b"\x67")
    ):
        raise ValueError("Request outside supported profile")
    plain = bytes([token]) + build_frame(opcode, nonce, body)
    return transform(key, plain.ljust(16, b"\xff"))


def server_record_size(first_block):
    if len(first_block) != 16 or first_block[1:4] != b"\x00\x01\x01" or first_block[4] < 2:
        raise ValueError("Unsupported server header")
    return 1 + ((first_block[4] + 6 + 15) // 16) * 16
