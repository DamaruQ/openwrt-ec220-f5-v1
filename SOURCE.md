# Source and build notes

## Base

- OpenWrt 25.12.5
- revision `r33051-f5dae5ece4`
- target `ramips/mt76x8`
- kernel `6.12.94`

Official OpenWrt release source/tag:

- https://github.com/openwrt/openwrt/releases/tag/v25.12.5
- https://downloads.openwrt.org/releases/25.12.5/targets/ramips/mt76x8/

## Current release build status

The public v1.0 firmware is a **validated device-specific repack**, not yet a fully upstream-native OpenWrt target image.

The starting hardware support is closely related to Archer C50 v6, but the EC220-F5 v1 has a different native boot/flash layout. The release therefore keeps the tested OpenWrt 25.12.5 kernel/userspace base and applies EC220-specific changes:

- native identity `tplink,ec220-f5-v1`
- native EC220 flash layout
- 40 MHz SPI NOR clock
- EC220 ROM/radio NVMEM offsets
- EC220 board.d network/LED defaults
- EC220-specific sysupgrade validation and fixed kernel/rootfs partition writer

The final binary was then validated on the router through an actual sysupgrade cycle.

## Device tree source

`device/mt7628an_tplink_ec220-f5-v1.dts` is a clean DTS representation of the DT embedded in the tested FINAL firmware.

During release preparation it was compiled with the OpenWrt 25.12.5 kernel-tree `dtc`; the decompiled result was semantically/diff identical to the DTB extracted from the validated FINAL kernel.

## Userspace changes

Exact unified diffs against OpenWrt 25.12.5 ImageBuilder sources are in:

- `device/rootfs-diff/01_leds.patch`
- `device/rootfs-diff/02_network.patch`
- `device/rootfs-diff/platform.sh.patch`

## Reference build implementation

`reference/FINAL_BUILD.py` is the reference script used for the validated FINAL image assembly. It is included for auditability and accepts input locations through these environment variables:

- `EC220_BUILD_WORK`
- `EC220_RC2`
- `EC220_STOCK_TFTP`
- `EC220_ROOTFS`
- `OPENWRT_IMAGEBUILDER`
- `OPENWRT_FWTOOL`

The script documents the final repack process, but it is **not** presented as a one-command public build system: it expects the validated intermediate image, stock recovery template, prepared SquashFS and OpenWrt host `fwtool` as inputs.

A future upstream-quality implementation should move the EC220 image wrapper/header generation into the OpenWrt image build system and add a proper `mt76x8.mk` profile so releases can be built from a clean source tree without binary transplant/repack steps.
