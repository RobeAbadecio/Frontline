#!/usr/bin/env python3
"""Export the JASS members from every map archive in War3.mpq.

Warcraft III stores maps as MPQ members, and each map is itself an MPQ archive.
The exporter therefore uses mpqtool for both archive levels instead of parsing
either MPQ format here.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


def run_mpqtool(mpqtool: Path, archive: Path, command: str, path: str = "") -> str:
    """Run an mpqtool query and return its text output, retaining diagnostics."""
    args = [str(mpqtool), "-mpq", str(archive), command]
    if path:
        args.append(path)
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"mpqtool {' '.join(args[2:])} failed: {detail}")
    return result.stdout


def list_children(mpqtool: Path, archive: Path, path: str = "") -> list[str]:
    """List direct children of an MPQ path, stripping mpqtool's directory marker."""
    result = []
    for line in run_mpqtool(mpqtool, archive, "ls", path).splitlines():
        line = line.strip().replace("\\", "/")
        if line:
            result.append(line.removesuffix("/"))
    return result


def walk_files(mpqtool: Path, archive: Path, path: str = "") -> list[str]:
    """Recursively enumerate files below an MPQ path using ls queries."""
    files = []
    for child in list_children(mpqtool, archive, path):
        child_path = f"{path}/{child}" if path else child
        # A file returns an empty listing; a directory returns its children.
        # MPQ directory entries are not required to exist explicitly, so this
        # query is the reliable distinction available through mpqtool.
        children = list_children(mpqtool, archive, child_path)
        if children:
            files.extend(walk_files(mpqtool, archive, child_path))
        else:
            files.append(child_path)
    return files


def dump_file(mpqtool: Path, archive: Path, member: str, destination: Path) -> None:
    """Write one MPQ member to disk and fail visibly if extraction fails."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    args = [str(mpqtool), "-mpq", str(archive), "cat", member]
    with destination.open("wb") as output:
        result = subprocess.run(args, stdout=output, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip() or "unknown error"
        raise RuntimeError(f"mpqtool {' '.join(args[2:])} failed: {detail}")


def safe_member_path(member: str) -> PurePosixPath:
    """Reject archive names that could escape the requested output directory."""
    path = PurePosixPath(member)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"unsafe JASS member path: {member}")
    return path


def export_map(mpqtool: Path, map_archive: Path, output_dir: Path, map_name: str) -> int:
    """Extract all .j members from one nested map archive."""
    scripts = [name for name in walk_files(mpqtool, map_archive) if name.lower().endswith(".j")]
    map_dir = output_dir / Path(map_name).with_suffix("")
    for script in scripts:
        member = safe_member_path(script)
        destination = map_dir.joinpath(*member.parts)
        dump_file(mpqtool, map_archive, script, destination)
        print(f"  {map_name}: {script} -> {destination}")
    if not scripts:
        print(f"warning: {map_name} contains no JASS scripts", file=sys.stderr)
    return len(scripts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mpq", type=Path, default=Path("data/Warcraft III/War3.mpq"))
    parser.add_argument("--mpqtool", type=Path, default=Path("build/bin/mpqtool"))
    parser.add_argument("--output", type=Path, default=Path("data/maps"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.mpq.is_file():
        print(f"error: MPQ not found: {args.mpq}", file=sys.stderr)
        return 1
    if not args.mpqtool.is_file():
        print(f"error: mpqtool not found: {args.mpqtool}", file=sys.stderr)
        return 1

    try:
        map_members = [name for name in walk_files(args.mpqtool, args.mpq, "Maps")
                       if name.lower().endswith((".w3m", ".w3x"))]
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if not map_members:
        print(f"error: no map archives found under Maps in {args.mpq}", file=sys.stderr)
        return 1

    total = 0
    failures = 0
    for map_member in map_members:
        map_name = str(Path(map_member).with_suffix("").relative_to("Maps"))
        try:
            with tempfile.NamedTemporaryFile(prefix="wc3-map-", suffix=".mpq") as nested:
                dump_file(args.mpqtool, args.mpq, map_member, Path(nested.name))
                total += export_map(args.mpqtool, Path(nested.name), args.output, map_name)
        except (OSError, RuntimeError) as error:
            print(f"error: {map_member}: {error}", file=sys.stderr)
            failures += 1

    print(f"exported {total} JASS script(s) from {len(map_members)} map(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
