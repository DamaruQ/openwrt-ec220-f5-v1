# TP-Link EC220-F5 v1 hardware notes

## Tested unit

- Label: EC220-F5, Version 1.0
- PCB: `2050501467`
- SoC: MediaTek MT7628AN, 580 MHz
- RAM: 64 MiB
- SPI NOR: EON EN25QH64, JEDEC `1c7017`, 8 MiB
- 5 GHz PCIe device: MediaTek MT7663 (`14c3:7663`)
- Ethernet: 100 Mbit/s

## Flash layout

```text
0x000000-0x01FFFF  boot      0x020000
0x020000-0x22FFFF  kernel    0x210000
0x230000-0x7BFFFF  rootfs    0x590000
0x7C0000-0x7CFFFF  config    0x010000
0x7D0000-0x7DFFFF  rom       0x010000
0x7E0000-0x7EFFFF  romfile   0x010000
0x7F0000-0x7FFFFF  radio     0x010000
```

## NVMEM

- base MAC: `rom + 0xF100`, 6 bytes
- 2.4 GHz EEPROM: `radio + 0x0000`, `0x400` bytes
- 5 GHz EEPROM: `radio + 0x8000`, `0x4DA8` bytes

## TFTP bootloader behavior observed

```text
tftp 0x81000000 tp_recovery.bin
erase tplink 0x20000 0x7a0000
cp.b 0x81020000 0x20000 0x7a0000
```

This is why the TFTP file is `0x7C0000` bytes: the first `0x20000` bytes are not copied to flash, while the following `0x7A0000` bytes map to flash `0x020000..0x7BFFFF`.
