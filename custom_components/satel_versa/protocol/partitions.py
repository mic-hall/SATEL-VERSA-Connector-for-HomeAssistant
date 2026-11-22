"""Read-only VERSA partition flags reconstructed from DLOADX's status renderer.

Scope: VERSA + ETHM; no network or command builder. Arming/disarming was
correlated with user-reported actions on one panel. Full mode and exit delay
were decoded from that capture. Other modes and alarm flags have static UI
evidence only, without active alarm examples in the validation recording.
"""

from dataclasses import dataclass
from enum import Enum


class ArmMode(Enum):
    DISARMED = "disarmed"
    FULL = "full"
    NIGHT = "night"
    DAY = "day"


@dataclass(frozen=True)
class PartitionState:
    number: int
    arm_mode: ArmMode
    exit_delay: bool
    entry_delay: bool
    verified_alarm: bool
    acpo_blocked: bool
    tamper_alarm_memory: bool
    silent_alarm_memory: bool
    alarm_memory: bool
    fire_alarm_memory: bool
    tamper_alarm: bool
    warning_alarm: bool
    alarm: bool
    fire_alarm: bool


def decode_partitions(
    opcode: int, body: bytes, partition_numbers: list[int]
) -> tuple[PartitionState, ...]:
    """Read validated 71/00 body, including selector0, without exposing user IDs.

    Caller must validate decryption, framing and checksum first. The generic
    'alarm' flag follows the literal UI label; its exact classification as
    burglary vs other alarm types needs further evidence. Uninterpreted status
    bits and the remaining body fields do not become inferred HA states.
    """
    if opcode != 0x71 or len(body) != 16 or body[0] != 0:
        raise ValueError("Unsupported partition state reply profile")
    if any(type(number) is not int or number not in (1, 2) for number in partition_numbers):
        raise ValueError("Partition numbers must be integers 1 or 2")
    if len(set(partition_numbers)) != len(partition_numbers):
        raise ValueError("Duplicate partition number")
    modes = (ArmMode.DISARMED, ArmMode.FULL, ArmMode.NIGHT, ArmMode.DAY)
    result = []
    for number in partition_numbers:
        status, alarms = body[number], body[number + 4]
        mode = modes[status & 3]
        result.append(
            PartitionState(
                number=number,
                arm_mode=mode,
                exit_delay=mode is not ArmMode.DISARMED and not bool(status & 4),
                entry_delay=bool(status & 8),
                verified_alarm=bool(status & 16),
                acpo_blocked=bool(status & 32),
                tamper_alarm_memory=bool(alarms & 1),
                silent_alarm_memory=bool(alarms & 2),
                alarm_memory=bool(alarms & 4),
                fire_alarm_memory=bool(alarms & 8),
                tamper_alarm=bool(alarms & 16),
                warning_alarm=bool(alarms & 32),
                alarm=bool(alarms & 64),
                fire_alarm=bool(alarms & 128),
            )
        )
    return tuple(result)
