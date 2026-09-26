# Recovery / return to stock

The EC220-F5 v1 bootloader TFTP recovery path remained functional throughout testing.

## TFTP parameters validated on the test unit

- PC / TFTP server: `192.168.0.66`
- Router TFTP client: `192.168.0.2`
- Requested filename: `tp_recovery.bin`
- Ethernet connection: PC directly to a LAN port
- Trigger: power off -> hold RESET -> power on while holding RESET -> release after transfer begins

## Stock recovery image

A TP-Link stock recovery binary is **not redistributed in this package**.

The tested OEM source file was:

`EC220-F5(US1)v1_3.16.0_0.9.1_up_boot(220713)_2022-07-13_09.11.41.bin`

For that file, the EC220 bootloader-compatible TFTP recovery image is the OEM binary with the first `0x200` bytes removed.

The tested result has:

- size: `8126464` bytes (`0x7C0000`)
- SHA256: `d95860cda001c4dbc483800dfb07c8c3e3ff939642237b3b57d88c3181fa8629`

Use `tools/make_stock_recovery.py` to create it from a legally obtained OEM firmware file.

If the resulting checksum differs, do not assume it is equivalent to the tested stock recovery image.

## Important

Do not use a raw full-flash dump from another router as a recovery image. The last flash regions contain per-device MAC/calibration data.
