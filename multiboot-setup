#!/bin/bash

set -eu

ISO_MNT="/mnt/iso"
PARTITION_LABEL="multiboot"
MULTIBOOT_MNT="/mnt/multiboot"
GRUB_CFG="${MULTIBOOT_MNT}/grub/grub.cfg"
SYSLINUX_VERSION="6.03"
SYSLINUX_URL="https://www.kernel.org/pub/linux/utils/boot/syslinux/syslinux-${SYSLINUX_VERSION}.tar.gz"

function cmd_format {
    if [ -z "${1:-}" ]; then
        echo "Usage: $0 format /dev/sdX"
        exit 1
    fi
    set -x

    sudo -k
    DISK_DEVICE="$1"
    PARTITION_DEVICE="${DISK_DEVICE}1"
    echo -ne 'label: dos\ntype=c, bootable\n' | sudo sfdisk "$DISK_DEVICE"
    sudo mkfs.vfat -n "$PARTITION_LABEL" "$PARTITION_DEVICE"
}

function cmd_bootloader {
    DISK_DEVICE="$(mount|grep /mnt/multiboot|cut -d' ' -f1|sed 's/[0-9]*$//')"
    set -x

    sudo -k
    install_grub_bios
    install_grub_efi
    install_grub_cfg
}

function install_grub_bios {
    sudo grub-install \
        --target=i386-pc \
        --boot-directory="$MULTIBOOT_MNT" \
        "$DISK_DEVICE"
}

function install_grub_efi {
    sudo grub-install \
        --target=x86_64-efi \
        --no-nvram \
        --removable \
        --efi-directory="$MULTIBOOT_MNT" \
        --boot-directory="$MULTIBOOT_MNT" \
        "$DISK_DEVICE"
}

function install_grub_cfg {
    mkdir -p "$(dirname "$GRUB_CFG")"
    cat <<EOT >> "$GRUB_CFG"
insmod all_video
insmod part_msdos
insmod progress
search --set=root --label $PARTITION_LABEL

EOT
}

function cmd_mount {
    set -x

    PARTITION_DEVICE="$(readlink -f /dev/disk/by-label/multiboot)"
    sudo mkdir -p "$MULTIBOOT_MNT"
    while sudo umount "$PARTITION_DEVICE"; do true; done
    sudo mount "$PARTITION_DEVICE" "$MULTIBOOT_MNT" -o "uid=$(whoami)"
}

function cmd_umount {
    set -x

    sudo umount "$MULTIBOOT_MNT"
    sudo rmdir "$MULTIBOOT_MNT"
}

function cmd_add_iso {
    if [ -z "${1:-}" ]; then
        echo "Usage: $0 add_iso /path/to/ubuntu.iso"
        exit 1
    fi
    set -x

    ISO_FILE="$1"

    if [[ "$ISO_FILE" == *ubuntu*.iso ]]; then
        setup_ubuntu
    elif [[ "$ISO_FILE" == *Fedora*.iso ]]; then
        setup_fedora
    elif [[ "$ISO_FILE" == *archlinux*.iso ]]; then
        setup_archlinux
    elif [[ "$ISO_FILE" == *FD12*.zip ]]; then
        setup_freedos
    else
        echo "Unsupported ISO! $ISO_FILE"
    fi
}

function setup_ubuntu {
    local version="$(basename "$ISO_FILE" | cut -d- -f2)"

    copy_iso_data

    cat <<EOT >> "$GRUB_CFG"
menuentry 'Ubuntu $version' {
  loopback loop /$(basename "$ISO_FILE")
  linux (loop)/casper/vmlinuz.efi boot=casper quiet iso-scan/filename=/$(basename "$ISO_FILE")
  initrd (loop)/casper/initrd.lz
}

EOT
}

function setup_fedora {
    local version="$(basename "$ISO_FILE" .iso | sed 's/.*x86_64-\([0-9\.]*\)-.*/\1/')"

    copy_iso_data

    cat <<EOT >> "$GRUB_CFG"
menuentry 'Fedora $version' {
  loopback loop /$(basename "$ISO_FILE")
  linux (loop)/isolinux/vmlinuz root=live:CDLABEL=$(blkid -s LABEL -o value "$ISO_FILE") rd.live.image quiet iso-scan/filename=/$(basename "$ISO_FILE")
  initrd (loop)/isolinux/initrd.img
}

EOT
}

function setup_archlinux {
    local version="$(basename "$ISO_FILE" .iso | sed -e 's/archlinux-//' -e 's/-dual//')"

    copy_iso_data

    cat <<EOT >> "$GRUB_CFG"
menuentry 'Arch Linux $version' {
  loopback loop /$(basename "$ISO_FILE")
  linux (loop)/arch/boot/x86_64/vmlinuz img_label=${PARTITION_LABEL} img_loop=$(basename "$ISO_FILE") archisobasedir=arch earlymodules=loop
  initrd (loop)/arch/boot/x86_64/archiso.img
}

EOT
}

function setup_freedos {
    install_memdisk
    copy_iso_data

    cat <<EOT >> "$GRUB_CFG"
menuentry 'FreeDOS' {
  if [ \${grub_platform} = pc ]; then
    linux16 /memdisk raw
    initrd16 /$(basename "$ISO_FILE")
  else
    echo "FreeDOS only works with BIOS boot."
    sleep 3
  fi
}

EOT
}

function copy_iso_data {
    rsync --size-only --progress "$ISO_FILE" "${MULTIBOOT_MNT}/"
}

function install_memdisk {
    local dest="${MULTIBOOT_MNT}/memdisk"

    if [ -f "$dest" ]; then
        return
    fi

    for maybe in /usr/lib/syslinux/bios/memdisk /usr/lib/syslinux/memdisk; do
        if [ -f "$maybe" ]; then
            cp "$maybe" "$dest"
            return
        fi
    done

    curl --fail "$SYSLINUX_URL" | \
        tar xz --strip-components=3 -C "$MULTIBOOT_MNT" \
            "syslinux-${SYSLINUX_VERSION}/bios/memdisk/memdisk"
}

CMD="cmd_${1:-}"
shift || true

if [ "$(type -t -- "$CMD")" = "function" ]; then
    "${CMD}" "$@"
else
    echo "Usage: $0 [format|mount|bootloader|add_iso|umount]"
    exit 1
fi
