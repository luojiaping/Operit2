# operit-board-esp32

Board profile for ESP32-2432S028 hardware.

This crate owns the board-specific Host API implementations used by
`apps/esp32`. The implemented surfaces are:

- `DeviceIoHost` for the onboard RGB status LEDs
- `RobotFaceHost` for the ILI9341 face display

The crate does not own Operit Core startup, Access pairing, Link packets,
Wi-Fi transport, or the firmware HTTP home page. Those belong to `apps/esp32`.

Display rotation `90` is used for the physical 320x240 landscape panel.

The physical panel receives RGB565 pixels. The remote screen mirror stores
RGB332 (75 KiB at 320x240) and expands colors when streaming a BMP, so remote
previews have reduced color precision without changing panel colors. LVGL uses
one synchronous 10-line RGB565 buffer (6.25 KiB). Full Edge snapshots use a
fallible allocation; if RAM is insufficient, use the streaming `/screen.bmp`
endpoint instead.
