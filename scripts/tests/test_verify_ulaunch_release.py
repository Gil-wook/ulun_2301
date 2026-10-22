import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile


spec = importlib.util.spec_from_file_location(
    "verify_release", Path(__file__).parents[1] / "verify-ulaunch-release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
RUN = "https://github.com/example/build/actions/runs/123"


class ReleaseVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.info = (
            f"Run: {RUN}\nA successful compile does NOT establish console compatibility.\n"
        ).encode()
        (self.directory / "BUILD-INFO.txt").write_bytes(self.info)
        (self.directory / "sdk-packages.txt").write_text("devkitA64 version\n")
        (self.directory / "port-baseline.patch").write_text("development version\n")
        self.binaries = {
            name: b"\0" * offset + magic + b"\0" * 16
            for name, (offset, magic) in release.BINARIES.items()
        }
        self.sources = {name: b"source\n" for name in release.SOURCE_FILES}
        self.sources["source/Makefile"] = b"VERSION_MICRO\t:=\t6\n"
        self.write_archives()

    def write_archives(self):
        with zipfile.ZipFile(self.directory / release.ZIP_NAME, "w") as archive:
            for name, data in self.binaries.items():
                archive.writestr(name, data)
            archive.writestr("BUILD-INFO.txt", self.info)
            archive.writestr("LICENSE-uLaunch.txt", b"GPL-2.0\n")
            archive.writestr("nx-hbloader.LICENSE.md", b"license\n")
        with tarfile.open(self.directory / release.SOURCE_NAME, "w:gz") as archive:
            for name, data in self.sources.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        self.write_checksums()

    def write_checksums(self):
        lines = []
        for name in [release.ZIP_NAME, release.SOURCE_NAME]:
            digest = hashlib.sha256((self.directory / name).read_bytes()).hexdigest()
            lines.append(f"{digest}  {name}\n")
        (self.directory / "SHA256SUMS.txt").write_text("".join(lines))

    def test_complete_release(self):
        result = release.verify(self.directory, RUN)
        self.assertEqual(len(result["binary_sizes"]), 10)

    def test_checksum_tampering(self):
        with (self.directory / release.ZIP_NAME).open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            release.verify(self.directory, RUN)

    def test_missing_component(self):
        del self.binaries["switch/uManager.nro"]
        self.write_archives()
        with self.assertRaises(KeyError):
            release.verify(self.directory, RUN)

    def test_wrong_binary_magic(self):
        self.binaries["switch/uManager.nro"] = b"not an NRO"
        self.write_archives()
        with self.assertRaisesRegex(ValueError, "Invalid or missing binary"):
            release.verify(self.directory, RUN)

    def test_mismatched_run(self):
        with self.assertRaisesRegex(ValueError, "does not match the run"):
            release.verify(self.directory, RUN + "4")

    def test_missing_corresponding_source(self):
        del self.sources["source/libnx/nx/include/switch.h"]
        self.write_archives()
        with self.assertRaisesRegex(ValueError, "Incomplete corresponding source"):
            release.verify(self.directory, RUN)

    def test_unsafe_source_path(self):
        self.sources["../outside"] = b"unsafe"
        self.write_archives()
        with self.assertRaisesRegex(ValueError, "Unsafe source path"):
            release.verify(self.directory, RUN)

    def test_wrong_source_version(self):
        self.sources["source/Makefile"] = b"VERSION_MICRO:=5\n"
        self.write_archives()
        with self.assertRaisesRegex(ValueError, "Source version"):
            release.verify(self.directory, RUN)


if __name__ == "__main__":
    unittest.main()
