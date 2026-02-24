#!/bin/bash

# Windows 98 USB Preparation Script for Twilight ISOs
# Prepares a USB drive with ISO files for use with virtual CD software in Windows 98

# -e: exit on error, -u: error on unset vars, -o pipefail: catch pipe failures
set -euo pipefail

# ── Color helpers ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

msg()  { echo -e "${GREEN}$*${NC}"; }
warn() { echo -e "${YELLOW}$*${NC}"; }
err()  { echo -e "${RED}ERROR: $*${NC}" >&2; }
die()  { err "$@"; exit 1; }

banner() {
    echo ""
    echo -e "${1}========================================${NC}"
    echo -e "${1}  $2${NC}"
    echo -e "${1}========================================${NC}"
    echo ""
}

# Print a list of ISOs (takes array of paths)
print_iso_list() {
    local prefix="${1:-  - }"
    shift
    for iso in "$@"; do
        echo -e "${prefix}$(basename "$iso") [${iso_sizes[$(basename "$iso")]}]"
    done
}

# ── Cleanup trap ───────────────────────────────────────────────
MOUNT_POINT=""
cleanup() {
    if [[ -n "$MOUNT_POINT" && -d "$MOUNT_POINT" ]]; then
        umount "$MOUNT_POINT" 2>/dev/null || true
        rmdir "$MOUNT_POINT" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Script directory ───────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

banner "${GREEN}" "Windows 98 USB + Virtual CD Setup"

# ── Root check ─────────────────────────────────────────────────
[[ "$EUID" -eq 0 ]] || die "This script must be run as root (use sudo)"

# ── Dependency check ───────────────────────────────────────────
REQUIRED_TOOLS=(mkfs.vfat mount umount parted partprobe dd)
MISSING_TOOLS=()
for tool in "${REQUIRED_TOOLS[@]}"; do
    command -v "$tool" &>/dev/null || MISSING_TOOLS+=("$tool")
done
if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
    die "Missing required tools: ${MISSING_TOOLS[*]}\n  Install with: sudo apt install dosfstools parted"
fi

# ── Scan for ISOs & cache sizes ────────────────────────────────
warn "Scanning for ISO files..."
mapfile -t iso_files < <(find "$SCRIPT_DIR" -maxdepth 1 -name "*.iso" -type f | sort -V)
[[ ${#iso_files[@]} -gt 0 ]] || die "No ISO files found in $SCRIPT_DIR"

# Build associative array of filename → human-readable size (avoids repeated du calls)
declare -A iso_sizes
total_bytes=0
for iso in "${iso_files[@]}"; do
    fname=$(basename "$iso")
    iso_sizes["$fname"]=$(du -h "$iso" | cut -f1)
    total_bytes=$((total_bytes + $(stat -c%s "$iso")))
done

msg "Found ${#iso_files[@]} ISO files:"
echo ""
for i in "${!iso_files[@]}"; do
    fname=$(basename "${iso_files[$i]}")
    printf "  %3d) %-30s [%s]\n" $((i+1)) "$fname" "${iso_sizes[$fname]}"
done

# ── ISO selection ──────────────────────────────────────────────
echo ""
warn "Enter Twilight release numbers (e.g., '28' for Twilight 28 discs,"
warn "  '28 29' for releases 28 & 29, '#28' for list position, or 'all'):"
read -r iso_choice

# Helper: find ISOs matching a Twilight release pattern
find_matching_isos() {
    local pattern="$1"
    local label="$2"
    local found=()
    for iso in "${iso_files[@]}"; do
        [[ "$(basename "$iso")" =~ $pattern ]] && found+=("$iso")
    done
    [[ ${#found[@]} -gt 0 ]] || die "No Twilight $label ISO found"
    printf '%s\n' "${found[@]}"
}

SELECTED_ISOS=()

if [[ "$iso_choice" == "all" ]]; then
    SELECTED_ISOS=("${iso_files[@]}")
else
    for item in $iso_choice; do
        if [[ "$item" =~ ^#([0-9]+)$ ]]; then
            # List position reference
            num="${BASH_REMATCH[1]}"
            (( num >= 1 && num <= ${#iso_files[@]} )) \
                || die "Invalid list position: #$num (must be 1-${#iso_files[@]})"
            SELECTED_ISOS+=("${iso_files[$((num-1))]}")
        elif [[ "$item" =~ ^([0-9]+)([aAbB])?$ ]]; then
            # Twilight release number, optionally with disc letter
            num="${BASH_REMATCH[1]}"
            letter="${BASH_REMATCH[2]:-}"
            suffix="${letter:-[aAbB]?}"
            mapfile -t matches < <(find_matching_isos \
                "[Tt]wilight0*${num}${suffix}\.iso$" "${num}${letter}")
            SELECTED_ISOS+=("${matches[@]}")
        else
            die "Invalid selection: $item\n  Use numbers (28), with letters (28a), or #N for list position"
        fi
    done
fi

[[ ${#SELECTED_ISOS[@]} -gt 0 ]] || die "No ISOs selected"

# ── Calculate total selected size ──────────────────────────────
selected_bytes=0
for iso in "${SELECTED_ISOS[@]}"; do
    selected_bytes=$((selected_bytes + $(stat -c%s "$iso")))
done
selected_human=$(numfmt --to=iec-i --suffix=B "$selected_bytes" 2>/dev/null || echo "${selected_bytes} bytes")

echo ""
msg "Selected ${#SELECTED_ISOS[@]} ISO(s) (${selected_human} total):"
print_iso_list "  ${GREEN}✓${NC} " "${SELECTED_ISOS[@]}"
echo ""

# ── USB device selection ───────────────────────────────────────
warn "Available block devices:"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL | grep -E "disk|part" || true
echo ""
echo -e "${RED}${BOLD}WARNING: ALL DATA ON THE SELECTED DEVICE WILL BE ERASED!${NC}"
warn "Enter the USB device (e.g., sdd — without /dev/ prefix):"
read -r usb_device

USB_DEV="/dev/${usb_device}"
[[ -b "$USB_DEV" ]] || die "Device $USB_DEV does not exist"

# If user gave a partition, find the parent disk (handles sda1, nvme0n1p1, mmcblk0p1)
if [[ "$usb_device" =~ [0-9]$ ]]; then
    warn "You specified a partition. Resolving parent disk..."
    parent=$(lsblk -ndo PKNAME "/dev/$usb_device" 2>/dev/null) \
        || die "Cannot determine parent disk of $usb_device"
    [[ -n "$parent" ]] || die "Cannot determine parent disk of $usb_device"
    usb_device="$parent"
    USB_DEV="/dev/${usb_device}"
    warn "Using parent disk: $USB_DEV"
fi

# ── Check USB capacity ────────────────────────────────────────
usb_bytes=$(blockdev --getsize64 "$USB_DEV" 2>/dev/null || echo 0)
usb_human=$(numfmt --to=iec-i --suffix=B "$usb_bytes" 2>/dev/null || echo "unknown")

if [[ "$usb_bytes" -gt 0 && "$selected_bytes" -gt "$usb_bytes" ]]; then
    die "Selected ISOs (${selected_human}) exceed USB capacity (${usb_human})"
fi

# ── Final confirmation ─────────────────────────────────────────
banner "${RED}" "FINAL CONFIRMATION"
echo -e "ISO Files (${#SELECTED_ISOS[@]}, ${selected_human}):"
print_iso_list "  ${GREEN}" "${SELECTED_ISOS[@]}"
echo -e "USB Device: ${RED}${BOLD}$USB_DEV${NC} ($usb_human)"
echo -e "${RED}ALL DATA ON $USB_DEV WILL BE DESTROYED!${NC}"
echo ""
warn "Type 'YES' to continue (case-sensitive):"
read -r confirmation
[[ "$confirmation" == "YES" ]] || { warn "Operation cancelled."; exit 0; }

# ── Start processing ──────────────────────────────────────────
echo ""
msg "Starting USB preparation..."

# Unmount any mounted partitions
warn "Unmounting any mounted partitions on $USB_DEV..."
for partition in "${USB_DEV}"*; do
    [[ -b "$partition" ]] && umount "$partition" 2>/dev/null || true
done

# Wipe partition table
warn "Wiping partition table..."
dd if=/dev/zero of="$USB_DEV" bs=512 count=2048 status=none

# Create MBR + FAT32 partition
warn "Creating MBR partition table + FAT32 partition..."
parted -s "$USB_DEV" mklabel msdos
parted -s "$USB_DEV" mkpart primary fat32 1MiB 100%

# Wait for kernel to recognise the new partition
partprobe "$USB_DEV" 2>/dev/null || true
# Poll for partition device (up to 5 s) instead of blind sleep
USB_PART=""
for _ in $(seq 1 10); do
    if [[ -b "${USB_DEV}1" ]]; then
        USB_PART="${USB_DEV}1"; break
    elif [[ -b "${USB_DEV}p1" ]]; then
        USB_PART="${USB_DEV}p1"; break
    fi
    sleep 0.5
done
[[ -n "$USB_PART" ]] || die "Cannot find partition after creation"

# Format
warn "Formatting $USB_PART as FAT32..."
mkfs.vfat -F 32 -n "TWILIGHT" "$USB_PART"

# Mount
MOUNT_POINT=$(mktemp -d /tmp/usb_mount.XXXXXX)
warn "Mounting USB at $MOUNT_POINT..."
mount "$USB_PART" "$MOUNT_POINT"

# ── Copy ISO files with progress ──────────────────────────────
warn "Copying ${#SELECTED_ISOS[@]} ISO file(s) to USB..."
copy_count=0
for iso in "${SELECTED_ISOS[@]}"; do
    copy_count=$((copy_count + 1))
    fname=$(basename "$iso")
    echo -e "  [${copy_count}/${#SELECTED_ISOS[@]}] ${fname} (${iso_sizes[$fname]})..."
    # Use rsync for progress if available, else fall back to cp
    if command -v rsync &>/dev/null; then
        rsync --progress --info=progress2 "$iso" "$MOUNT_POINT/" 2>/dev/null \
            || cp "$iso" "$MOUNT_POINT/"
    else
        cp "$iso" "$MOUNT_POINT/"
    fi
done

# Copy Daemon Tools if present
DAEMON_PATH="$SCRIPT_DIR/daemon347.exe"
if [[ -f "$DAEMON_PATH" ]]; then
    warn "Copying Daemon Tools installer..."
    cp "$DAEMON_PATH" "$MOUNT_POINT/"
else
    warn "Note: daemon347.exe not found in script directory"
fi

# ── Create README ──────────────────────────────────────────────
{
    cat <<-HEADER
	Twilight ISO Collection for Windows 98
	======================================

	This USB contains ${#SELECTED_ISOS[@]} Twilight ISO file(s).

	To use these ISOs in Windows 98:
	1. Install Daemon Tools: Run daemon347.exe from this USB
	2. Mount the ISO file you want to use in Daemon Tools
	3. Run menu95.exe or autorun from the mounted virtual CD drive
	4. For multi-disc releases (28a/28b, etc):
	   - Start with disc 'a'
	   - When prompted for disc 2, unmount and mount disc 'b'

	ISO Files on this USB:
	HEADER
    for iso in "${SELECTED_ISOS[@]}"; do
        fname=$(basename "$iso")
        echo "  - $fname [${iso_sizes[$fname]}]"
    done
} > "$MOUNT_POINT/README.TXT"

# ── Sync & unmount (trap handles cleanup on failure) ──────────
warn "Syncing data..."
sync
warn "Unmounting USB..."
umount "$MOUNT_POINT"
rmdir "$MOUNT_POINT"
MOUNT_POINT=""   # clear so trap doesn't double-unmount

# ── Done ───────────────────────────────────────────────────────
banner "${GREEN}" "SUCCESS!"
msg "USB drive prepared successfully!"
echo -e "  ISOs copied: ${BOLD}${#SELECTED_ISOS[@]}${NC} (${selected_human})"
print_iso_list "  - " "${SELECTED_ISOS[@]}"
echo -e "  Device: ${BOLD}$USB_DEV${NC}"
echo ""
warn "Next Steps for Windows 98:"
echo "  1. Plug USB into Windows 98 PC"
echo "  2. Install a virtual CD program (Daemon Tools, Virtual CD, etc.)"
echo "  3. Mount the ISO files from the USB"
echo "  4. Run menu95.exe from the mounted virtual CD"
echo ""
msg "You can now safely remove the USB drive."
