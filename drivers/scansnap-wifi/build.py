#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later WITH SANE-exception
"""Build the pinned, patched iX1300 module locally; no installation or network.

Linux development build only. Requires installed Python 3.10+, cc, Git, Linux
development headers and libjpeg development files. The portable release path is
upstream's full Autotools build. The optional tests use in-memory protocol replays.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
PIN = "130b69136f1eedff19acb377cb5019e38d865065"
FILES = (
    "backend/scansnap.c", "backend/scansnap-protocol.c",
    "backend/scansnap-protocol.h", "backend/stubs.c", "backend/sane_strstatus.c",
    "sanei/sanei_init_debug.c", "sanei/sanei_constrain_value.c", "sanei/sanei_config.c",
    "testsuite/backend/scansnap/scansnap_protocol_test.c",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="Checkout at the documented commit, with supplied patch applied")
    parser.add_argument("--build", required=True, type=Path,
                        help="New or empty build directory outside the source checkout")
    parser.add_argument("--test", action="store_true", help="Run offline replay tests after building")
    args = parser.parse_args()
    source, build = args.source.resolve(), args.build.resolve()
    if platform.system() != "Linux":
        parser.error("This experimental build recipe supports Linux only.")
    if not source.is_dir():
        parser.error("Source directory does not exist.")
    if source == build or source in build.parents or build in source.parents:
        parser.error("Source and build must be separate directories, not nested.")
    if build.exists() and (not build.is_dir() or any(build.iterdir())):
        parser.error("Build directory must be absent or empty; existing builds are never overwritten.")
    for program in ("cc", "git"):
        if not shutil.which(program):
            parser.error(f"Required installed program is missing: {program}")
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"],
                                     text=True).strip()
    if commit != PIN:
        parser.error(f"Source HEAD must be exactly {PIN}.")
    expected = json.loads((PACKAGE / "source-hashes.json").read_text())
    for relative, checksum in expected.items():
        path = source / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            parser.error(f"Patched source does not match the supplied patch: {relative}")

    build.mkdir(parents=True, exist_ok=True)
    for relative in FILES:
        target = build / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    shutil.copytree(source / "include/sane", build / "include/sane")
    shutil.copytree(source / "testsuite/backend/scansnap/fixtures",
                    build / "testsuite/backend/scansnap/fixtures")
    shutil.copy2(PACKAGE / "session_cleanup_test.c", build / "session_cleanup_test.c")

    private_config = build / "empty-config"
    private_config.mkdir()
    (private_config / "dll.conf").write_text("scansnap\n")
    (private_config / "scansnap.conf").write_text("# No scanner target configured.\n")
    # JSON quoting yields a safe ASCII C string even when the local path has spaces.
    (build / "include/sane/config.h").write_text(
        "/* Explicit configuration for this local Linux development build. */\n"
        "#ifndef PAPERDOCK_STANDALONE_SANE_CONFIG_H\n"
        "#define PAPERDOCK_STANDALONE_SANE_CONFIG_H\n"
        "#define HAVE_UNISTD_H 1\n#define HAVE_SYS_SOCKET_H 1\n"
        "#define HAVE_VSYSLOG 1\n#define HAVE_SIGPROCMASK 1\n#define HAVE_LIBJPEG 1\n"
        f"#define PATH_SANE_CONFIG_DIR {json.dumps(str(private_config), ensure_ascii=True)}\n"
        "#endif\n"
    )
    flags = ["-std=gnu11", "-O2", "-g", "-fPIC", "-Wall", "-Wextra",
             "-Iinclude", "-Ibackend", "-include", "include/sane/config.h"]
    objects = []
    (build / "objects").mkdir()
    for relative in FILES:
        if not relative.endswith(".c") or relative.startswith("testsuite/"):
            continue
        output = Path("objects") / (Path(relative).stem + ".o")
        backend_flag = ["-DBACKEND_NAME=scansnap"] if relative in (
            "backend/scansnap.c", "backend/stubs.c") else []
        subprocess.run(["cc", *flags, *backend_flag, "-c", relative, "-o", str(output)],
                       cwd=build, check=True)
        objects.append(str(output))
    (build / "lib").mkdir()
    subprocess.run(["cc", "-shared", "-Wl,-z,defs", "-Wl,-z,relro,-z,now",
                    "-Wl,-soname,libsane-scansnap.so.1", "-o", "lib/libsane-scansnap.so.1",
                    *objects, "-ljpeg"], cwd=build, check=True)
    (build / "lib/libsane-scansnap.so").symlink_to("libsane-scansnap.so.1")
    subprocess.run(["cc", *flags, "testsuite/backend/scansnap/scansnap_protocol_test.c",
                    "-o", "scansnap_protocol_test"], cwd=build, check=True)
    subprocess.run(["cc", *flags, "-Werror", "session_cleanup_test.c",
                    "-o", "session_cleanup_test"], cwd=build, check=True)
    if args.test:
        environment = os.environ.copy()
        environment["SCANSNAP_FIXTURES"] = str(build / "testsuite/backend/scansnap/fixtures")
        environment["TZ"] = "Europe/Berlin"
        for test in ("scansnap_protocol_test", "session_cleanup_test"):
            subprocess.run([str(build / test)], cwd=build, env=environment, check=True)
    print(f"Built: {build / 'lib/libsane-scansnap.so.1'}")
    print("No installation or scanner/network request was performed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        sys.exit(1)
