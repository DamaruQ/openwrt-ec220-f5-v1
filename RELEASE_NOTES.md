# v1.0.1 — OpenWrt 25.12.5 FINAL

First hardware-validated public release for TP-Link EC220-F5 v1.

## Highlights

- Native `tplink,ec220-f5-v1` board identity
- OpenWrt 25.12.5 / kernel 6.12.94
- SPI NOR raised from inherited 10 MHz to tested 40 MHz
- Native EC220 flash layout
- Correct ROM MAC and radio EEPROM locations
- LAN/WAN defaults
- 2.4 GHz + 5 GHz radio initialization
- TFTP recovery/install image
- Native EC220 sysupgrade image
- Real sysupgrade cycle tested successfully

## Boot-time investigation

The inherited 10 MHz SPI setting was a major I/O bottleneck. Raising it to 40 MHz reduced an uncached ~5.56 MiB MTD read from about 5.43 s to about 1.70 s on the tested unit and substantially shortened boot time.

## Known limitations

See `README.md` / `README_RU.md`.

## Disclaimer / support policy

This build was made primarily for the maintainer's own EC220-F5 V1 and is published AS IS, without warranty. Flashing is at the user's own risk. Compatibility with other hardware samples, revisions, ISP variants, or BOM changes is not guaranteed. No ongoing support, bug-fix schedule, future updates, or adaptation to other models/revisions is promised.

**v1.0.1 is a documentation/release-packaging update only. The firmware binaries are unchanged from the hardware-validated v1.0 build.**
