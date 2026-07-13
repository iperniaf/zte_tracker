# Release Notes
## v2.0.20
### Added

- Support for the ZTE F8748 (DIGI Portugal) router model.
- Expose WAN traffic counters for F8748 routers, including Rx/Tx bytes, packets, and error counts.

### Fixed

- Restore previously known offline devices after Home Assistant restarts, including setups with new-device registration disabled.
- Remove the Home Assistant deprecation warning caused by importing `ScannerEntity` from the deprecated module path.
- Address code review follow-ups from issue #68, including safer sensor attributes handling, clearer reboot error reporting, one-time service registration, and safer debug logging.

