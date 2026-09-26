#!/bin/sh
set -e

echo '=== BOARD ==='
cat /tmp/sysinfo/board_name
ubus call system board

echo '=== SPI ==='
hexdump -C /sys/firmware/devicetree/base/palmbus@10000000/spi@b00/flash@0/spi-max-frequency

echo '=== MTD ==='
cat /proc/mtd

echo '=== LAN ==='
ubus call network.interface.lan status

echo '=== WAN ==='
ubus call network.interface.wan status

echo '=== WIFI PHY ==='
iw phy | grep -E 'Wiphy|Band [12]'

echo '=== MT76 ==='
dmesg | grep -Ei 'mt76|mt7615|mt7663|firmware' | tail -50
