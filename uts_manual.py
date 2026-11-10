"""Local manual UTS gradebook; preserves every revision and never calls an LLM."""
import csv
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from file_lock import exclusive_file_lock
from course_service import build_portfolio_url

COMPONENTS = {'paper': 'Pra-UTS / makalah', '1': 'Sesi 1', '2a': 'Sesi 2a',
              '2b': 'Sesi 2b', '3a': 'Sesi 3a', '3b': 'Sesi 3b'}


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        return list(csv.DictReader(source))


def history(path):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def latest(path):
    return {r['nim']: r for r in history(path)}


def normalize_scores(scores):
    if set(scores) != set(COMPONENTS):
        raise ValueError('Isi tepat enam komponen UTS.')
    result = {}
    for key, value in scores.items():
        if value is None or value == '':
            result[key] = None
            continue
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError('Nilai harus berupa angka 0–100.') from exc
        if not number.is_finite() or not 0 <= number <= 100:
            raise ValueError('Nilai harus berupa angka 0–100.')
        result[key] = str(number)
    return result


def final_score(scores):
    scores = normalize_scores(scores)
    if any(v is None for v in scores.values()):
        return None
    value = Decimal(scores['paper']) * Decimal('.10') + sum(
        Decimal(scores[k]) * Decimal('.18') for k in COMPONENTS if k != 'paper')
    return str(value.quantize(Decimal('.01')))


def save_review(path, *, nim, name, ticket, scores, notes, assessor, final, expected_revision):
    scores = normalize_scores(scores)
    total = final_score(scores)
    if not nim.strip() or not assessor.strip():
        raise ValueError('NIM dan nama dosen wajib diisi.')
    if final and total is None:
        raise ValueError('Lengkapi enam nilai sebelum finalisasi. Nilai kosong bukan nol.')
    path = Path(path)
    with exclusive_file_lock(path):
        records = history(path)
        old = next((r for r in reversed(records) if r['nim'] == nim), None)
        revision = old['revision'] if old else 0
        if revision != expected_revision:
            raise ValueError('Nilai sudah diubah oleh sesi lain. Muat ulang sebelum menyimpan.')
        record = dict(nim=nim, name=name, ticket=ticket, scores=scores, notes=notes,
                      assessor=assessor.strip(), status='FINAL' if final else 'DRAF',
                      total=total, revision=revision + 1,
                      updated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        records.append(record)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                             delete=False) as target:
                temporary = target.name
                json.dump(records, target, ensure_ascii=False, indent=2)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and Path(temporary).exists():
                Path(temporary).unlink()
    return record


def portfolio_links(participant, ticket, input_dir):
    """Prefer actual recorded links; otherwise return explicitly labelled candidates."""
    try:
        index = build_portfolio_url(participant['repo'], 'W08')
    except (ValueError, KeyError):
        return '', {}
    base = index.rsplit('/', 1)[0] + '/UTS/'
    manifest = {}
    if ticket:
        path = Path(input_dir) / f"tiket-{ticket['tiket']}-W08-evidence.json"
        if path.exists():
            try:
                manifest = json.loads(path.read_text())['manifest']
            except (ValueError, KeyError):
                pass
    links = {}
    for key in COMPONENTS:
        url = manifest.get(key, {}).get('url', '')
        parsed = urlsplit(url)
        if parsed.scheme == 'https' and parsed.netloc == urlsplit(index).netloc and url.startswith(base):
            links[key] = [('Buka laporan', url)]
        elif key == 'paper':
            links[key] = [('Buka makalah (alamat perkiraan)', base + 'paper.html')]
        else:
            links[key] = [('Buka laporan dengan NIM (alamat perkiraan)', base + f"hasil_{key}_{participant['NIM']}.html"),
                          ('Buka laporan tanpa NIM (alamat perkiraan)', base + f'hasil_{key}.html')]
    return index, links


def export_csv(records):
    output = io.StringIO()
    fields = ['NIM', 'Nama', 'Tiket', *COMPONENTS, 'Total', 'Status', 'Dosen', 'Revisi', 'Waktu']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for r in records.values():
        writer.writerow(dict(NIM=r['nim'], Nama=r['name'], Tiket=r['ticket'],
                             **{k: v if v is not None else '' for k, v in r['scores'].items()},
                             Total=r['total'] or '', Status=r['status'], Dosen=r['assessor'],
                             Revisi=r['revision'], Waktu=r['updated_at']))
    return '\ufeff' + output.getvalue()


def ai_suggestions(report_dir, ticket, nim):
    """Read only the selected student's validated UTS report; never infer grades."""
    import uts
    if not ticket:
        return {}, 'Pilih tiket UTS untuk melihat usulan AI.'
    if not str(ticket).isdigit():
        return {}, 'Nomor tiket tidak valid.'
    path = Path(report_dir) / f'tiket-{ticket}-W08-uts-v1.json'
    if not path.exists():
        return {}, 'Laporan AI untuk tiket ini belum tersedia.'
    try:
        report = uts.validate_report(json.loads(path.read_text(encoding='utf-8')), str(ticket), str(nim))
        suggestions = {}
        for session, item in report['sessions'].items():
            value = uts.session_score(item['dimensions'])
            suggestions[session] = {
                'score': float(uts.score_text(value)) if value is not None else None,
                'evidence_status': item['evidence_status'],
                'summary': item['summary'],
                'improvement_priority': item['improvement_priority'],
            }
        return suggestions, ''
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {}, f'Laporan AI tidak dapat digunakan: {exc}'
