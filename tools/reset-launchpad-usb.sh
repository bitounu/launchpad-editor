#!/usr/bin/env bash

set -euo pipefail

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  cat <<'EOF'
Usage: ./scripts/reset-launchpad-usb.sh [midi-device]

Soft-resets a USB-connected Novation Launchpad by unbinding and rebinding
its parent USB device through sysfs.

Arguments:
  midi-device   ALSA rawmidi node name, default: midiC3D0

Examples:
  ./scripts/reset-launchpad-usb.sh
  ./scripts/reset-launchpad-usb.sh midiC3D1
EOF
  exit 0
fi

midi_device="${1:-midiC3D0}"
sysfs_path="/sys/class/sound/${midi_device}/device"

if [[ ! -e "$sysfs_path" ]]; then
  echo "error: ${sysfs_path} does not exist" >&2
  exit 1
fi

resolved_path="$(readlink -f "$sysfs_path")"
usb_id="$(grep -oE '[0-9]+-[0-9]+(\.[0-9]+)?' <<<"$resolved_path" | head -n1 || true)"

if [[ -z "$usb_id" ]]; then
  echo "error: could not determine USB device id from ${resolved_path}" >&2
  exit 1
fi

unbind="/sys/bus/usb/drivers/usb/unbind"
bind="/sys/bus/usb/drivers/usb/bind"

echo "Resetting USB device ${usb_id} for ${midi_device}"
echo "$usb_id" | sudo tee "$unbind" >/dev/null
sleep 1
echo "$usb_id" | sudo tee "$bind" >/dev/null
sleep 1

echo
echo "Current MIDI ports:"
amidi -l
