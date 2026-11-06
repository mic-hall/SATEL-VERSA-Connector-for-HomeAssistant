"""Offline VERSA input bitmap interpretation, derived from DLOADX UI code.

Mapping was physically correlated for selected inputs on one VERSA 15.
Other positions/models remain unverified. No transport, credentials or commands.
Caller supplies configured input numbers; absent inputs are never invented.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InputState:
    number: int
    blocked: bool
    violated: bool
    alarm_memory: bool
    armed: bool
    monitoring_delay: bool


def decode_inputs(body: bytes, input_numbers: list[int]) -> tuple[InputState, ...]:
    """Decode body of validated opcode 0x71, including selector 1.

    Caller MUST validate outer record, opcode and inner checksum first.
    Additional bytes after the five bitmaps remain opaque.
    """
    if len(body) < 21 or body[0] != 1:
        raise ValueError("Incomplete or unsupported input state body")
    if any(type(n) is not int or not 1 <= n <= 30 for n in input_numbers):
        raise ValueError("Input numbers must be integers from 1 to 30")
    if len(set(input_numbers)) != len(input_numbers):
        raise ValueError("Duplicate input number")
    result = []
    for number in input_numbers:
        index = number - 1
        values = [bool(body[1 + 4 * group + index // 8] & (1 << (index % 8))) for group in range(5)]
        result.append(InputState(number, *values))
    return tuple(result)
