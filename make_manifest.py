#!/usr/bin/env python3
"""Rebuild sounds/manifest.txt from sounds/ and check the rules the device relies on."""
import datetime, pathlib, re, sys, zlib

ROOT = pathlib.Path(__file__).resolve().parent / "sounds"
MAN = ROOT / "manifest.txt"
MAX_FILES = 254
EXT = {".mp3", ".wav"}


def die(msg):
    sys.exit("ERROR: " + msg)


def collect():
    files, skipped = [], []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p == MAN:
            continue
        rel = p.relative_to(ROOT).as_posix()
        m = re.fullmatch(r"(\d\d)/(\d\d\d)\.(mp3|wav)", rel)
        if not m:
            skipped.append(rel)
            continue
        d, n = int(m[1]), int(m[2])
        if not (1 <= d <= 99 and 1 <= n <= 255):
            die(f"{rel}: folder must be 01..99, number 001..255")
        files.append((d, n, rel, p.read_bytes()))
    files.sort()
    seen = {}
    for d, n, rel, _ in files:
        if (d, n) in seen:
            die(f"{rel} and {seen[(d, n)]}: same folder/number twice")
        seen[(d, n)] = rel
    if not files:
        die("no sound files in sounds/")
    if len(files) > MAX_FILES:
        die(f"{len(files)} files, the device holds at most {MAX_FILES}")
    return files, skipped


def next_ver():
    today = datetime.date.today().isoformat()
    n = 1
    if MAN.exists():
        m = re.search(rb"^ver (\d{4}-\d\d-\d\d)-(\d+)$", MAN.read_bytes(), re.M)
        if m and m[1].decode() == today:
            n = int(m[2]) + 1
    return f"{today}-{n}"


def build(files, ver):
    lines = ["SVTSET 1", f"ver {ver}"]
    lines += [f"{rel} {len(b)} {zlib.crc32(b) & 0xFFFFFFFF:08x}" for _, _, rel, b in files]
    body = ("\n".join(lines) + "\n").encode("ascii")
    return body + f"end {len(files)} {zlib.crc32(body) & 0xFFFFFFFF:08x}\n".encode("ascii")


def main():
    files, skipped = collect()
    old = MAN.read_bytes() if MAN.exists() else None
    # keep ver when nothing changed, so a rerun does not make the devices re-check
    if old:
        m = re.search(rb"^ver (\S+)$", old, re.M)
        if m and build(files, m[1].decode()) == old:
            print("manifest unchanged")
            report(files, skipped)
            return
    MAN.write_bytes(build(files, next_ver()))
    print("manifest written:", MAN)
    report(files, skipped)


def report(files, skipped):
    total = sum(len(b) for *_, b in files)
    print(f"files: {len(files)}, total: {total} bytes ({total / 1048576:.2f} MiB)")
    for s in skipped:
        print("skipped (not DD/NNN.mp3|wav):", s)


if __name__ == "__main__":
    main()
