# Contributing

Use the pinned environment and checks in README.md. Add focused tests for protocol
changes, failure cleanup and HA entity availability. Tests must not contact an
alarm panel or use real credentials. Use documentation IP ranges and synthetic IDs.

Keep transport/protocol changes in `protocol/`, separate from HA platform code.
Do not expand supported commands or infer semantics from packet lengths alone.
Describe the hardware/firmware and validation scope for compatibility changes.

Do not contribute SATEL binaries, extracted files, disassembly, configuration
exports or unredacted captures. This repository distributes the original Python
implementation and synthetic tests only.
