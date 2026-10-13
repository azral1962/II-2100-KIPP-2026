"""Build UTS references from trusted course ZIPs and a lecturer-adopted rubric."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SESSIONS = ("1", "2a", "2b", "3a", "3b")
DIMENSIONS = {"objective_context", "perception_validation", "repertoire_sequence",
              "execution_care_consistency", "evaluation_adaptation", "reflection_learning"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(source: Path, rubric: dict, output: Path, approved_by: str | None = None) -> dict:
    descriptors = rubric["descriptors"]
    if set(descriptors) != DIMENSIONS:
        raise ValueError("Rubrik harus memuat tepat enam dimensi UTS.")
    for levels in descriptors.values():
        if set(levels) != {"1", "2", "3", "4"} or any(not isinstance(v, str) or not v.strip() for v in levels.values()):
            raise ValueError("Descriptor level 1-4 tidak lengkap.")
    inventory = {}
    for path in sorted(source.rglob('*.zip')):
        match = re.fullmatch(r'kasus_(1|2a|2b|3a|3b)_([0-9]+)\.zip', path.name)
        if not match:
            continue
        session, nim = match.groups()
        if session in inventory.setdefault(nim, {}):
            raise ValueError(f"Paket duplikat: {nim}/{session}")
        inventory[nim][session] = path
    if not inventory:
        raise ValueError("Tidak ada paket UTS individual ditemukan.")
    prepared = {}
    versions = set()
    targets = {}
    for nim, packages in inventory.items():
        if set(packages) != set(SESSIONS):
            raise ValueError(f"Lima sesi tidak lengkap untuk {nim}.")
        assignments, provenance, local_versions, local_targets = {}, {}, set(), {}
        for session in SESSIONS:
            path = packages[session]
            with zipfile.ZipFile(path) as archive:
                brief_bytes = archive.read("PENUGASAN.md")
                prompt_bytes = archive.read("prompt_umum.md")
            brief = brief_bytes.decode("utf-8-sig")
            prompt = prompt_bytes.decode("utf-8-sig")
            source_nim = re.search(r'^- NIM:\s*([0-9]+)\s*$', brief, re.M)
            source_session = re.search(r'^- Sesi:\s*(1|2a|2b|3a|3b);', brief, re.M)
            version = re.search(r'versi paket individual:\s*([^\r\n]+)', brief, re.I)
            target = re.search(r'^- Komunikan:\s*(.+)$', brief, re.M)
            if (not source_nim or source_nim.group(1) != nim or not source_session
                    or source_session.group(1) != session or not version or not target):
                raise ValueError(f"Identitas/sesi/versi/sasaran paket tidak cocok: {path.name}")
            local_versions.add(version.group(1).strip())
            local_targets[session] = target.group(1).strip()
            assignments[session] = brief.strip() + "\n\n## Prompt umum paket aktif\n\n" + prompt.strip()
            provenance[session] = {"zip": path.name, "zip_sha256": sha(path.read_bytes()),
                "assignment_sha256": sha(brief_bytes), "common_prompt_sha256": sha(prompt_bytes)}
        if len(local_versions) != 1:
            raise ValueError(f"Versi paket berbeda antar sesi untuk {nim}.")
        if local_targets["2a"] == local_targets["2b"] or local_targets["3a"] == local_targets["3b"]:
            raise ValueError(f"Target pasangan sesi tidak berbeda untuk {nim}.")
        version = next(iter(local_versions))
        versions.add(version)
        prepared[nim] = {"nim": nim, "package_version": version,
            "approval_status": "approved" if approved_by else "draft",
            "approved_by": approved_by or None,
            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds") if approved_by else None,
            "rubric_version": rubric["rubric_version"].removesuffix("-draft") if approved_by else rubric["rubric_version"],
            "rubric_origin": rubric["basis"], "rubric_sha256": sha(json.dumps(rubric, sort_keys=True, ensure_ascii=False).encode()),
            "descriptors": descriptors, "assignments": assignments, "rubric_rules": rubric.get("rules", []),
            "provenance": provenance}
        targets[nim] = local_targets
    # Validate all packages before writing any references. Existing files are not overwritten.
    output.mkdir(parents=True, exist_ok=True)
    if any((output / f"{nim}.json").exists() for nim in prepared):
        raise ValueError("Folder output sudah berisi acuan; pilih folder baru agar tidak menimpa moderasi.")
    for nim, data in prepared.items():
        (output / f"{nim}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"students": len(prepared), "packages": len(prepared) * 5,
            "package_versions": sorted(versions), "approval_status": "approved" if approved_by else "draft",
            "output": str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path, required=True, help="Folder lk/lk-UTS/peserta dari repo dosen")
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approved-by", help="Isi hanya setelah dosen mengesahkan descriptor baru")
    args = parser.parse_args()
    if args.approved_by is not None and not args.approved_by.strip():
        parser.error("Nama dosen pengesah tidak boleh kosong.")
    rubric = json.loads(args.rubric.read_text(encoding="utf-8-sig"))
    print(json.dumps(build(args.packages, rubric, args.output, args.approved_by), ensure_ascii=False))


if __name__ == "__main__":
    main()
