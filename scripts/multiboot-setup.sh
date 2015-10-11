#!/bin/bash

set -e

SYSLINUX_CFG="syslinux/syslinux.cfg"
REFIND_CFG="System/Library/CoreServices/refind.conf"

function setup_bootloader {
    install_syslinux
    install_refind
    rm -rf distros
}

function install_syslinux {
    rm -rf syslinux
    mkdir syslinux
    cp -R /usr/lib/syslinux/bios/*.c32 syslinux/

    echo "UI menu.c32" >> "$SYSLINUX_CFG"

    echo "Install syslinux:"
    echo "  # dd bs=440 count=1 if=/usr/lib/syslinux/bios/mbr.bin of=/dev/sdX"
    echo "  # extlinux -i -d /<mountpoint>/syslinux"
}

function install_refind {
    rm -rf System
    mkdir -p System/Library/CoreServices
    cp /usr/share/refind/refind_x64.efi System/Library/CoreServices/boot.efi

    echo "timeout 0" >> "$REFIND_CFG"
    echo "textonly true" >> "$REFIND_CFG"
    echo "textmode 1024" >> "$REFIND_CFG"
    echo "scanfor manual" >> "$REFIND_CFG"
}

function setup_iso {
    mount_iso
    set_boot_vars
    copy_boot_files
    configure_syslinux
    configure_refind
    umount_iso
}

function mount_iso {
    umount_iso
    sudo mount "$ISOFILE" /mnt
}

function umount_iso {
    sudo umount /mnt || true
}

function set_boot_vars {
    if [[ "$ISOFILE" == *ubuntu*.iso ]]; then
        set_ubuntu_boot_vars
    elif [[ "$ISOFILE" == *fedora*.iso ]]; then
        set_fedora_boot_vars
    else
        echo "Unsupported ISO! $ISOFILE"
    fi
}

function set_ubuntu_boot_vars {
    version="$(basename "$ISOFILE" | cut -d- -f2)"
    menulabel="Ubuntu $version"
    unpackdir="distros/ubuntu_$(generate_safe_filename "$version")"
    kernel="/mnt/casper/vmlinuz.efi"
    initrd="/mnt/casper/initrd.lz"
    bootparams="boot=casper iso-scan/filename=/${unpackdir}/$(basename "$ISOFILE")"
}

function set_fedora_boot_vars {
    version="$(basename "$ISOFILE" .iso | sed 's/.*x86_64-//')"
    menulabel="Fedora $version"
    unpackdir="distros/fedora_$(generate_safe_filename "$version")"
    kernel="/mnt/isolinux/vmlinuz0"
    initrd="/mnt/isolinux/initrd0.img"
    bootparams="root=live:CDLABEL=$(basename "$ISOFILE" .iso) rootfstype=auto iso-scan/filename=/${unpackdir}/$(basename "$ISOFILE")"
}

function generate_safe_filename {
    echo -n "$1" | tr -c '[:alnum:]\n' '_'
}

function copy_boot_files {
    mkdir -p "${unpackdir}"
    ln "$ISOFILE" "${unpackdir}/"
    cp "$kernel" "$initrd" "${unpackdir}/"
}

function configure_syslinux {
    cat <<EOT >> "$SYSLINUX_CFG"

LABEL $(basename $unpackdir)
MENU LABEL ${menulabel}
LINUX /${unpackdir}/$(basename ${kernel})
INITRD /${unpackdir}/$(basename ${initrd})
APPEND ${bootparams}
EOT
}

function configure_refind {
    cat <<EOT >> "$REFIND_CFG"

menuentry "${menulabel}"
    loader /${unpackdir}/$(basename ${kernel})
    initrd /${unpackdir}/$(basename ${initrd})
    options "${bootparams}"
}
EOT
}

if [ "$1" = "reset" ]; then
    setup_bootloader
elif [[ "$1" == *.iso ]]; then
    ISOFILE="$1"
    setup_iso
else
    echo "Usage: $0 [reset|/path/to/ubuntu.iso]"
fi
