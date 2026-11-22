# SATEL VERSA connector for Home Assistant

This is a custom integration allowing to read states of inputs of SATEL VERSA alarm systems locally through an **ETHM-1 Plus** expansion card. This custom integration is distributed under the MIT license.

**Beta: 0.1.0-beta.3.** The protocol has been tested with one VERSA 15 +
ETHM-1 Plus installation. Other models/firmware and long-running operation
are not yet validated. This project is independent of SATEL.

## Features

- A `binary_sensor` for each selected input, with stable IDs across IP changes.
- `on` means the input is currently violated; alarm memory is a separate flag
  in the protocol and does not turn the violation entity on.
- One asynchronous session and one shared poll for all inputs (default 1 s).
- Entities become `unavailable` when polling fails. Reconnect uses a bounded
  backoff of 5–60 seconds, returning to normal polling after recovery.
- UI setup, polling options and connection reconfiguration. English and Polish UI.
- Local communication. No arming/disarming, bypass control, output switching
  or alarm configuration writes. No Home Assistant actions/services are exposed.

## Requirements

- Home Assistant **2026.10.1 or newer**.
- A SATEL VERSA alarm board with ETHM-1 Plus and a working DLOADX LAN/WAN connection.
- Network access from Home Assistant to the ETHM DLOADX port (usually 7090).
- The ETHM **DLOADX key**, **DLOADX identifier** and **VERSA identifier** from
  DLOADX communication settings. The program opening PIN is not used.
- Disconnect DLOADX before using the integration. Concurrent programming
  sessions are not supported by this beta.

The integration uses `cryptography`, already required and installed by Home
Assistant Core. It does not download or run DLOADX. The protocol library is
included in `custom_components/satel_versa/protocol` and is independent of HA.

## Installation

### HACS custom repository

1. Open HACS → menu → Custom repositories.
2. Add https://github.com/mic-hall/SATEL-VERSA-Connector-for-HomeAssistant, category **Integration**.
3. Download SATEL VERSA and restart Home Assistant.
4. Add the integration through Devices & services.

This project is prepared for a HACS custom repository; it is not listed in the
HACS default store.

### Manual

1. Download the release `satel_versa-<version>.zip` and extract it into your
   Home Assistant configuration directory. The resulting path must be:
   `config/custom_components/satel_versa/manifest.json`.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → SATEL VERSA**.

Alternatively, copy only `custom_components/satel_versa` from this repository
into `config/custom_components/` and restart Home Assistant.

## Configuration

| Setting | Meaning |
|---|---|
| Host / port | ETHM LAN address and DLOADX TCP port |
| ETHM DLOADX key | 1–12 printable ASCII characters; copied exactly, including any spaces |
| DLOADX identifier | Exactly 8 hexadecimal characters from communication settings |
| VERSA identifier | Exactly 8 hexadecimal characters from communication settings |
| Inputs | Explicit input numbers, e.g. `1-8,10`; supported positions are 1–30 |
| Poll interval | 1–60 seconds; default 1 second |

Choose only inputs actually configured on your panel. A zero in the bitmap
does not prove an input exists. Input 31/32 and automatic input discovery are
not supported. ASCII key validation deliberately excludes ambiguous legacy
Windows encodings in this first release.

Setup performs START, a display query (ETHM only), one input read, an optional
output indicator read and STOP to validate the
settings. It then opens the operational session. The integration never renders
or logs the virtual keypad display.

Entities are called **Input N** (or **Wejście N**). Rename them and assign areas
in Home Assistant. No device class is guessed: a violation may represent motion,
a contact, a fault or a different panel input type.

**Configure** changes the input selection and poll interval. **Reconfigure**
changes the host, port and identifiers/key; enter credentials again. It briefly
stops the running connection while testing the new settings. The panel ID must
remain the same; remove and add the integration to use a different panel.
Identifiers are user-configurable, so changing the panel ID also changes its
HA identity. Preserve it when changing only the network address.

## Availability, stopping and DLOADX

A failed poll makes all entities unavailable until the next successful read.
Old values are not presented as fresh data and are not replaced with `off`.
The coordinator reconnects with increasing delays, capped at 60 seconds.
Normal polls and protocol operations are serialized.

To use DLOADX, disable this integration first. Disable/unload closes the session
and attempts STOP; transport failures may prevent a STOP acknowledgement, but
the socket is still closed. Re-enable the integration after disconnecting DLOADX.

To uninstall, remove its entry from Devices & services, remove
`config/custom_components/satel_versa`, and restart Home Assistant. If installed
through HACS, remove the repository there as well.

## Limitations

- Tested hardware: VERSA 15 + ETHM-1 Plus; no INTEGRA or PERFECTA support claim.
- Reverse-engineered successful-session profile, not an official SATEL protocol
  implementation. Unknown greetings/records fail the operation.
- Some startup notifications can precede input data; a poll handles at most four
  responses under one timeout (5 s for ETHM, 15 s for VERSA Plus LTE). Persistent
  notifications fail the poll.
- Command rejection is not automatically classified as an invalid password.
- No names import, configuration-file import or output control. Alarm panel entities
  are read-only.
- Experimental output indicators report DLOADX colors; physical ON/OFF semantics
  have not been verified.
- A successful read is not a test of the alarm installation or a replacement for
  its independent alarm functions.

## Troubleshooting and privacy

Check the port, identifiers and ETHM key, network routing, and whether DLOADX
is disconnected. A working DLOADX connection on another computer does not prove
Home Assistant has network access. Review HA logs for connection/update failures.

Download integration diagnostics from the entry menu. Diagnostics contain only
version, configured input count, poll interval and last update success. They omit
host, identifiers, key, input states and display content. Credentials are stored
by Home Assistant in the config entry; protect your HA configuration and backups.
Do not attach DLOADX configuration files, packet captures or credentials to issues.

See [SECURITY.md](SECURITY.md) and [TESTING.md](TESTING.md).

## Experimental VERSA Plus LTE support

The built-in Ethernet profile is detected from the `VERSA` greeting. It uses a
2.5-second START delay, a 15-second default timeout, its own response layout and
skips the unsupported display query. ETHM defaults remain unchanged. No HA
configuration changes are needed. This does not implement cellular LTE transport.
The implementation is based on a supplied working-installation report and tested
with simulated transport; physical VERSA Plus LTE validation remains pending.

## Experimental ETHM output indicator entities

In Configure, enter **ETHM output numbers**, for example `1-4,12`. Leave blank
(the default for existing entries) to disable the extra read. Select only output
positions configured on your panel. The supported selection is 1–12; no output
presence or name discovery is performed. Setup and Reconfigure also accept this
optional field. Output polling is currently restricted to ETHM-1 Plus.

Each selected position creates a `sensor` named **Output N indicator**, attached
to the existing VERSA device. Its states match the DLOADX indicator: `green`,
`red`, `blinking_green_red`. These are enum sensors, not switches or physical
ON/OFF binary sensors. The UI colors and numbering were recovered from DLOADX;
the wire layout was checked against 18 recorded replies with constant data.
Changes of physical outputs and the meaning of the blinking flag remain unverified.

Enabling outputs adds one shared read per polling cycle, regardless of how many
outputs are selected. Input and output operations use the same serialized session.
A failed read makes all entities unavailable until the complete cycle succeeds;
old states are not published as fresh data. Removing a selected output removes
its entity on reload. Raw status bytes are not exposed in entity attributes or
integration diagnostics. No output switching command is implemented.

## Optional ETHM partition entities

In Configure, enter **ETHM partitions**: `1` for A, `2` for B, or `1,2` for both.
The field is also available during setup and Reconfigure. Blank disables the
extra poll and is the default for existing entries. Partition support currently
requires ETHM-1 Plus; the LTE profile rejects this option before START.

Each selected partition adds a **Partition N arm mode** enum sensor with states
`disarmed`, `full`, `night`, `day`, plus separate binary sensors for entry delay,
exit delay, alarm, fire alarm, tamper alarm and warning (silent) alarm. During exit
delay the mode reflects the selected arming mode; check the separate delay flag
before treating it as fully armed. Current alarms are independent of the mode.

Alarm memories and verified alarm/ACPO-blocked flags are separate entities,
disabled by default in the entity registry. Enable them individually if needed.
A remembered fire alarm never activates the current fire alarm sensor. The
ordinary flag is labelled **Alarm**, following DLOADX; classification specifically
as burglary has not been independently established. Alarm control actions are rejected; see the read-only alarm panels below.

One shared selector0 read per cycle updates all selected partitions. A cycle is
published only after every configured read succeeds; failures make entities
unavailable until recovery. Deselected partition entities are removed on reload.
User identifiers from the response are ignored and not exposed in HA.

Arming/disarming of both partitions was correlated with user-reported actions on
one VERSA + ETHM installation. Full mode and exit delay were decoded in the same
recording. Night/day modes, entry delay, alarm flags and memories are mapped from
DLOADX code but lack active hardware examples in our validation capture. The new
client/HA behavior has automated tests, not a live deployment validation.

## Read-only alarm panels

Each selected ETHM partition also creates an `alarm_control_panel` entity named
**Partition N alarm**, on the same VERSA device. Use the existing **ETHM partitions**
field (`1`, `2`, or `1,2`); no new setting, credentials or extra protocol read is
needed. Existing arm mode and binary sensors retain their identities.

The mapping is:

| Partition snapshot | HA alarm state |
|---|---|
| Any current alarm, fire, tamper or warning (silent) alarm | `triggered` |
| Entry delay, without a current alarm | `pending` |
| Exit delay, without a current alarm or entry delay | `arming` |
| Full arming | `armed_away` |
| Night arming | `armed_night` |
| Day arming | `armed_home` |
| Disarmed | `disarmed` |
| Failed poll, missing partition or unload | `unavailable` |

This priority order is deliberate. Current fire/tamper alarms can show
`triggered` even while disarmed. Alarm memories and ACPO flags alone never
trigger the panel. Day-to-home is a presentation convention of this integration.
The individual binary sensors continue to distinguish alarm types and memories.

All synchronous and asynchronous arm/disarm/trigger methods explicitly reject
control. Supported control features are zero. HA may still display a Disarm
control because its alarm domain always exposes disarming; using it returns a
localized read-only error. It does not send a command or change the displayed
state. The integration does not ask for an alarm PIN. Configure the dashboard
for status viewing; the entities remain usable in history and automations.

The state mapping is covered by HA tests, including failed polls and recovery.
Hardware evidence has the same limits as the partition data above: the new HA
alarm layer does not add physical validation of active alarms or other arm modes.
