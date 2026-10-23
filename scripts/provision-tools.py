#!/usr/bin/env python3
"""Install verified Go/Node archives in GitHub's permanent Actions tool cache.

Run during provisioning or deliberate updates, never as a per-job bootstrap.
Versions are explicit so a prepared environment can be reproduced. Run again
with current stable versions when upgrading. Existing complete installs are reused.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import tarfile
import tempfile
import urllib.request


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def install(cache, tool, version, system, arch):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("use an exact stable release version")
    target = cache / tool / version / arch
    complete = target.with_suffix(".complete")
    if complete.exists() and (target / "bin" / tool).is_file():
        print(f"Reusing {tool} {version} ({system}/{arch})", flush=True)
        return
    if tool == "go":
        machine = {"x64": "amd64", "arm64": "arm64"}[arch]
        filename = f"go{version}.{system}-{machine}.tar.gz"
        releases = json.loads(fetch("https://go.dev/dl/?mode=json&include=all"))
        archive = next(f for release in releases for f in release["files"] if f["filename"] == filename)
        digest, source, folder = archive["sha256"], "https://go.dev/dl/" + filename, "go"
    else:
        node_os = "darwin" if system == "darwin" else "linux"
        folder = f"node-v{version}-{node_os}-{arch}"
        filename = folder + ".tar.gz"
        base = f"https://nodejs.org/dist/v{version}/"
        checksums = fetch(base + "SHASUMS256.txt").decode().splitlines()
        digest = next(line.split()[0] for line in checksums if line.split()[-1] == filename)
        source = base + filename
    print(f"Installing {tool} {version} ({system}/{arch})", flush=True)
    payload = fetch(source)
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"checksum mismatch: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".install-") as work:
        work = Path(work)
        archive = work / "archive.tar.gz"
        archive.write_bytes(payload)
        with tarfile.open(archive) as bundle:
            bundle.extractall(work / "unpack", filter="data")
        staged = work / "unpack" / folder
        (staged / "installation.json").write_text(json.dumps({"url": source, "sha256": digest}) + "\n")
        if target.exists():
            shutil.rmtree(target)
        os.replace(staged, target)
    complete.touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-cache", required=True, type=Path)
    parser.add_argument("--go", action="append", default=[])
    parser.add_argument("--node", action="append", default=[])
    parser.add_argument("--os", choices=["linux", "darwin"], default=platform.system().lower())
    parser.add_argument("--arch", choices=["x64", "arm64"], default={"x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine()))
    args = parser.parse_args()
    if not args.arch or args.os not in ("linux", "darwin"):
        parser.error("unsupported platform")
    if not args.go and not args.node:
        parser.error("specify --go and/or --node versions to provision")
    for tool, versions in [("go", args.go), ("node", args.node)]:
        for version in versions:
            install(args.tool_cache.resolve(), tool, version, args.os, args.arch)


if __name__ == "__main__":
    main()
