"""Replay sintetik tahap 1; tidak membaca peserta atau token produksi."""
import csv
import random
import time
from pathlib import Path

from ci_observer import Observer


def simulate(path, seed=42):
    path = Path(path)
    roster = path.with_suffix('.participants.csv')
    if path.exists() or roster.exists():
        raise SystemExit('Gunakan path database simulasi baru agar data lama tidak tertimpa.')
    path.parent.mkdir(parents=True, exist_ok=True)
    with roster.open('x', newline='', encoding='utf-8') as output:
        writer = csv.writer(output)
        writer.writerow(['NIM', 'Nama', 'ID', 'repo'])
        for i in range(40):
            writer.writerow([f'SIM{i+1:02d}', f'Peserta Sintetik {i+1}', 1000+i, ''])
    observer = Observer(path, roster, chats={-999}, instructors={1000})
    for i in range(40):
        observer.command(1000+i, {'Nama': f'Sintetik {i+1}'}, {'type': 'private', 'id': 1000+i}, '/setuju', '')
    rng = random.Random(seed)
    phrases = [
        'Saya usul aplikasi merangkum kebutuhan fasilitator.',
        'Bagaimana jika perspektif minoritas belum terdengar?',
        'Saya keberatan: keputusan terlalu cepat, karena belum ada kriteria.',
        'Berdasarkan sumber https://example.org/data-sintetik perlu uji coba.',
        'Terima kasih, mari gabungkan kedua usulan menjadi sintesis.',
        'Bagaimana pendapat peserta yang belum berbicara?',
        'Saya akan menulis kriteria penerimaan untuk uji kelas.',
        'Saya menyadari kita perlu memisahkan ringkasan dari konsensus.'
    ]
    stamp = int(time.time()) + 1
    # Deliberately leave some fictional participants unheard.
    for i in range(64):
        uid = 1000 + rng.randrange(32)
        message = {'message_id': i+1, 'date': stamp+i, 'text': phrases[i % len(phrases)],
                   'chat': {'id': -999, 'type': 'supergroup', 'title': 'SIMULASI SINTETIK'},
                   'from': {'id': uid}}
        if i and i % 3 == 0:
            message['reply_to_message'] = {'message_id': i}
        observer.handle({'update_id': i+1, 'message': message})
    observer.analyze(-999)
    # Exercise integration and an explicit human confirmation flow, entirely local.
    state = observer.facilitator.snapshot(-999)
    first = state['rows'][0]
    second = next(r for r in state['rows'] if r['telegram_id'] != first['telegram_id'])
    chat = {'id':-999,'type':'supergroup'}
    user = {'NIM':'SIM01','Nama':'Peserta Sintetik 1'}
    observer.command(1000,user,chat,'/integrasi',f"{first['id']},{second['id']} Gabungkan kebutuhan fasilitator dan perlindungan perspektif minoritas.")
    observer.command(1000,user,chat,'/usulan','Prototipe lokal dengan bukti, persetujuan manusia, dan uji kelas.')
    observer.command(1000,user,chat,'/sepakat','1')
    observer.command(1001,{'NIM':'SIM02'},chat,'/sikap','1 keberatan Perlu kriteria perlindungan data.')
    for i in range(40):
        observer.command(1000+i,{'NIM':f'SIM{i+1:02d}'},chat,'/sikap','1 setuju')
    before = observer.command(1000,user,chat,'/konsensus','1')
    observer.command(1000,user,chat,'/konfirmasi','1')
    after = observer.command(1000,user,chat,'/konsensus','1')
    return (f'DATA SINTETIK — seed {seed}; 40 peserta fiktif\n' + observer.report(-999, summary=True)
            + '\n\nSIMULASI KONFIRMASI MANUSIA\nSebelum konfirmasi:\n' + before + '\nSetelah konfirmasi:\n' + after)
