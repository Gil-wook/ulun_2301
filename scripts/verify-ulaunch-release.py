#!/usr/bin/env python3
"""Verify downloaded uLaunch release files without extracting or executing them."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


ZIP_NAME = "uLaunch-23.0.1-dev.zip"
SOURCE_NAME = "uLaunch-23.0.1-dev-source.tar.gz"
BINARIES = {
    "atmosphere/contents/0100000000001000/exefs.nsp": (0, b"PFS0"),
    "ulaunch/bin/uSystem/exefs.nsp": (0, b"PFS0"),
    "ulaunch/bin/uMenu/main": (0, b"NSO0"),
    "ulaunch/bin/uMenu/main.npdm": (0, b"META"),
    "ulaunch/bin/uMenu/romfs.bin": (0, b"\x50\0\0\0\0\0\0\0"),
    "ulaunch/bin/uLoader/applet/main": (0, b"NSO0"),
    "ulaunch/bin/uLoader/applet/main.npdm": (0, b"META"),
    "ulaunch/bin/uLoader/application/main": (0, b"NSO0"),
    "ulaunch/bin/uLoader/application/main.npdm": (0, b"META"),
    "switch/uManager.nro": (16, b"NRO0"),
}
SOURCE_FILES = {
    "source/Makefile",
    "source/LICENSE",
    "source/nx-hbloader.LICENSE.md",
    "source/libs/Atmosphere-libs/LICENSE",
    "source/libs/Plutonium/LICENSE",
    "source/libs/libnx-ext/LICENSE",
    "source/libnx/LICENSE.md",
    "source/libnx/nx/include/switch.h",
    "source/arc/arc.py",
    "source/arc/arc_db_gen.py",
    "sdl-inputs/SDL2-2.28.5.tar.gz",
    "sdl-inputs/SDL2-2.28.5.patch",
    "sdl-inputs/PKGBUILD",
}
SOURCE_FILES.update(
    f"source/projects/{component}/{name}"
    for component in ["uSystem", "uLoader", "uMenu", "uManager"]
    for name in ["Makefile", "source/main.cpp"]
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(name):
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def verify(directory, run_url):
    directory = Path(directory)
    require(
        run_url.startswith("https://github.com/")
        and "/actions/runs/" in run_url,
        "Expected the GitHub Actions run URL",
    )
    sums = {}
    for line in (directory / "SHA256SUMS.txt").read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        filename = filename.removeprefix("*")
        require(filename in {ZIP_NAME, SOURCE_NAME}, "Unexpected checksum filename")
        require(filename not in sums, "Duplicate checksum filename")
        with (directory / filename).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        require(actual == digest, f"Checksum mismatch: {filename}")
        sums[filename] = digest
    require(set(sums) == {ZIP_NAME, SOURCE_NAME}, "Missing release checksum")

    info = (directory / "BUILD-INFO.txt").read_bytes()
    require(run_url.encode() in info, "Build metadata does not match the run")
    require(b"does NOT establish console compatibility" in info, "Missing warning")
    for name in ["sdk-packages.txt", "port-baseline.patch"]:
        require((directory / name).stat().st_size > 0, f"Missing metadata: {name}")

    sizes = {}
    with zipfile.ZipFile(directory / ZIP_NAME) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate ZIP member")
        require(all(safe_name(name) for name in names), "Unsafe ZIP path")
        require(archive.testzip() is None, "ZIP CRC check failed")
        for name, (offset, magic) in BINARIES.items():
            data = archive.read(name)
            require(
                len(data) > offset + len(magic)
                and data[offset:offset + len(magic)] == magic,
                f"Invalid or missing binary: {name}",
            )
            sizes[name] = len(data)
        require(
            archive.read("ulaunch/bin/uSystem/exefs.nsp")
            == archive.read("atmosphere/contents/0100000000001000/exefs.nsp"),
            "The two uSystem copies differ",
        )
        require(archive.read("BUILD-INFO.txt") == info, "ZIP build metadata differs")
        for name in ["LICENSE-uLaunch.txt", "nx-hbloader.LICENSE.md"]:
            require(len(archive.read(name)) > 0, f"Missing license: {name}")

    with tarfile.open(directory / SOURCE_NAME, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        require(len(names) == len(set(names)), "Duplicate source member")
        require(all(safe_name(name) for name in names), "Unsafe source path")
        files = {member.name for member in members if member.isfile() and member.size}
        missing = SOURCE_FILES - files
        require(not missing, f"Incomplete corresponding source: {sorted(missing)}")
        require(
            not any(PurePosixPath(name).suffix in {".o", ".a", ".elf", ".nsp", ".nso", ".nro"} for name in files),
            "Source archive contains generated binaries",
        )
        # Confirm that the corresponding source carries the development version.
        makefile = archive.extractfile("source/Makefile").read().decode()
        micro = [
            line.replace(" ", "").replace("\t", "")
            for line in makefile.splitlines()
            if line.startswith("VERSION_MICRO")
        ]
        require(micro == ["VERSION_MICRO:=6"], "Source version is not 1.2.6")

    return {"run": run_url, "sha256": sums, "binary_sizes": sizes}


if __name__ == "__main__":
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.run_url), indent=2))
