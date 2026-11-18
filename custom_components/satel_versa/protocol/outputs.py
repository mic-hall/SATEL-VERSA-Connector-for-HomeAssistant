"""Read-only VERSA + ETHM output indicator decoding.

Layout checked against 18 recorded ETHM replies. Indicator colors follow the
DLOADX UI; physical ON/OFF and the meaning of other flags remain unverified.
No network, command builder, credentials, or automatic execution.
"""

from dataclasses import dataclass, field
from enum import Enum


class Indicator(Enum):
    GREEN = "green"
    RED = "red"
    BLINKING_GREEN_RED = "blinking_green_red"


@dataclass(frozen=True)
class OutputIndicator:
    number: int
    indicator: Indicator
    raw_flags: int = field(repr=False)


def decode_output_indicators(
    opcode: int, body: bytes, output_numbers: list[int]
) -> tuple[OutputIndicator, ...]:
    """Decode the statically inferred 71/09 layout, including its selector.

    Caller must first validate decryption, framing and checksum. The November 18
    capture has exactly 15 payload bytes after selector 9.
    Reject other lengths until separately verified. Bytes 0..2 of the payload
    and other flag bits remain opaque. The native receiver copies 16 bytes,
    but this does not establish an extra byte on the wire.
    Blink has priority over steady red, as in Timer1Timer at 0x329772.
    Colors must not be treated as measured voltage or physical on/off states.
    """
    if opcode != 0x71 or len(body) != 16 or body[0] != 9:
        raise ValueError("Unsupported output indicator reply profile")
    if any(type(number) is not int or not 1 <= number <= 12 for number in output_numbers):
        raise ValueError("Output numbers must be integers from 1 to 12")
    if len(set(output_numbers)) != len(output_numbers):
        raise ValueError("Duplicate output number")
    result = []
    for number in output_numbers:
        flags = body[number + 3]
        if flags & 0x10:
            indicator = Indicator.BLINKING_GREEN_RED
        elif flags & 0x80:
            indicator = Indicator.RED
        else:
            indicator = Indicator.GREEN
        result.append(OutputIndicator(number, indicator, flags))
    return tuple(result)
