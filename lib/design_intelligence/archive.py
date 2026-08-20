"""Static ZIP inspection. Never execute members."""

from __future__ import annotations

import hashlib
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class ArchiveError(ValueError):
    pass


@dataclass
class ArchiveIssue:
    code: str
    path: str
    detail: str = ""


@dataclass
class ArchiveInspection:
    path: Path
    sha256: str
    logical_name: str
    family: str | None
    top_level: str | None
    members: int
    files: int
    issues: list[ArchiveIssue] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.issues)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_name(path: Path) -> str:
    name = path.name
    name = re.sub(r"\(\d+\)(?=\.zip$)", "", name, flags=re.IGNORECASE)
    return name


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode) if mode else False


def _posix_name(name: str) -> str:
    return name.replace("\\", "/")


def _unsafe_name(name: str) -> str | None:
    posix = _posix_name(name)
    if posix.startswith("/") or re.match(r"^[A-Za-z]:/", posix):
        return "absolute"
    parts = Path(posix).parts
    if ".." in parts or posix.startswith("../") or "/../" in posix:
        return "traversal"
    return None


def detect_family(names: Iterable[str], taxonomy: dict[str, Any]) -> tuple[str | None, str | None]:
    tops: set[str] = set()
    for name in names:
        posix = _posix_name(name).strip("/")
        if not posix:
            continue
        tops.add(posix.split("/", 1)[0])
    families = taxonomy.get("archive_families") or {}
    hits = [top for top in tops if top in families]
    if len(hits) == 1:
        return families[hits[0]], hits[0]
    return None, next(iter(sorted(tops)), None)


def inspect_archive(path: Path, policy: dict[str, Any], taxonomy: dict[str, Any]) -> ArchiveInspection:
    if not path.is_file():
        raise ArchiveError(f"missing archive: {path}")
    digest = sha256_file(path)
    zip_policy = policy.get("zip") or {}
    max_members = int(zip_policy.get("max_members") or 20000)
    max_member = int(zip_policy.get("max_member_uncompressed") or 50 * 1024 * 1024)
    max_total = int(zip_policy.get("max_total_uncompressed") or 2 * 1024 * 1024 * 1024)
    max_ratio = float(zip_policy.get("max_compression_ratio") or 200)

    issues: list[ArchiveIssue] = []
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        return ArchiveInspection(
            path=path,
            sha256=digest,
            logical_name=logical_name(path),
            family=None,
            top_level=None,
            members=0,
            files=0,
            issues=[ArchiveIssue("invalid_zip", "", str(exc))],
        )

    with archive:
        infos = archive.infolist()
        if len(infos) > max_members:
            issues.append(ArchiveIssue("member_count", "", str(len(infos))))
        total = 0
        files = 0
        names = [info.filename for info in infos]
        for info in infos:
            posix = _posix_name(info.filename)
            unsafe = _unsafe_name(posix)
            if unsafe:
                issues.append(ArchiveIssue(unsafe, posix))
            if info.flag_bits & 0x1:
                issues.append(ArchiveIssue("encrypted", posix))
            if _is_symlink(info):
                issues.append(ArchiveIssue("symlink", posix))
            if info.is_dir():
                continue
            files += 1
            total += int(info.file_size)
            if info.file_size > max_member:
                issues.append(ArchiveIssue("member_too_large", posix, str(info.file_size)))
            if info.compress_size and info.file_size / max(info.compress_size, 1) > max_ratio:
                issues.append(ArchiveIssue("compression_ratio", posix))
        if total > max_total:
            issues.append(ArchiveIssue("total_uncompressed", "", str(total)))
        family, top = detect_family(names, taxonomy)
        if family is None:
            issues.append(ArchiveIssue("UNSUPPORTED_ARCHIVE_FAMILY", top or "", "unknown top-level family"))

    return ArchiveInspection(
        path=path,
        sha256=digest,
        logical_name=logical_name(path),
        family=family,
        top_level=top,
        members=len(infos),
        files=files,
        issues=issues,
    )


def open_zip(path: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(path)


def read_member(archive: zipfile.ZipFile, name: str, policy: dict[str, Any]) -> bytes:
    posix = _posix_name(name)
    unsafe = _unsafe_name(posix)
    if unsafe:
        raise ArchiveError(f"{unsafe}: {posix}")
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise ArchiveError(f"missing member: {name}") from exc
    if info.flag_bits & 0x1:
        raise ArchiveError(f"encrypted: {posix}")
    if _is_symlink(info):
        raise ArchiveError(f"symlink: {posix}")
    limit = int((policy.get("zip") or {}).get("max_read_bytes") or 1024 * 1024)
    if info.file_size > limit:
        raise ArchiveError(f"member_too_large_to_read: {posix}")
    data = archive.read(name)
    if len(data) > limit:
        raise ArchiveError(f"member_too_large_to_read: {posix}")
    return data


def member_names(archive: zipfile.ZipFile) -> list[str]:
    return [_posix_name(name) for name in archive.namelist()]


def children(names: Iterable[str], prefix: str) -> list[str]:
    root = prefix.rstrip("/") + "/"
    found: set[str] = set()
    for name in names:
        posix = _posix_name(name)
        if not posix.startswith(root):
            continue
        rest = posix[len(root) :]
        if not rest:
            continue
        child = rest.split("/", 1)[0]
        if child:
            found.add(child)
    return sorted(found)


def has_file(names: Iterable[str], path: str) -> bool:
    posix = _posix_name(path)
    return posix in {_posix_name(name) for name in names}
