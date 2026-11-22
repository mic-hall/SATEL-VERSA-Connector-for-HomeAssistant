# Changelog

## 0.1.0-beta.3 — 2026-11-22

- Add read-only alarm_control_panel entities for selected ETHM partitions,
  sharing the existing snapshots and preserving existing sensor identities.
- Map current alarms, entry/exit delays and arm modes with explicit priority;
  exclude memories and ACPO-only flags from triggered state.
- Reject all sync/async alarm controls and report a localized read-only error.

- Add optional ETHM partition selection (1=A, 2=B) and shared selector0 polling.
- Expose partition arm mode and independent delay/current alarm binary sensors.
- Keep alarm memory and ACPO entities separate and disabled by default.
- Preserve existing input/output entities and opt out legacy entries by default.
- Correlate arming/disarming with a recording; document static-only validation
  of other modes and alarm flags. No arming/disarming commands are added.

- Add opt-in ETHM output indicator sensors for positions 1–12, with green, red
  and blinking green/red states matching DLOADX. Physical ON/OFF is unverified.
- Add output selection to setup/reconfiguration/options, serialized read-only
  selector9 polling, unavailable/recovery handling and output entity cleanup.
- Leave output polling disabled for existing entries; reject LTE output polling.

- Detect the VERSA Plus LTE built-in Ethernet profile from its greeting.
- Use its response layout, 2.5-second START delay and 15-second default timeout;
  skip the unsupported display query for this profile only.
- Preserve ETHM defaults and validate checksums and panel identity for both profiles.
- Correct the configuration schema import to voluptuous.
- Add simulated LTE lifecycle, reconnect and rejection tests. Hardware validation
  of this implementation on VERSA Plus LTE remains pending.

## 0.1.0-beta.2

- Lower the tested minimum to Home Assistant 2026.10.1.
- Test both HA 2026.10.1 and 2026.10.4 in CI using matching pinned test harnesses.
- Update HACS compatibility metadata and installation documentation.

## 0.1.0-beta.1

Initial beta for VERSA input states over ETHM-1 Plus.

- UI configuration and reconfiguration; explicit input selection and poll interval.
- One binary sensor per configured input; no inferred motion/door class.
- Shared asynchronous connection, input polling and bounded reconnect backoff.
- Unavailable entities after a failed poll; STOP and socket cleanup on unload.
- English and Polish UI, diagnostics that omit credentials and input states.
- Protocol, simulated transport and Home Assistant integration tests.

Validated protocol with VERSA 15 + ETHM-1 Plus. Support for other models and
firmware, DLOADX coexistence and long-running reliability remain unverified.
