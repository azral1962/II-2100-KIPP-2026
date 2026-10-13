# Assessment UTS W08

W08 menggantikan tugas mingguan ke-8. W01–W07 dan W09–W15 tetap memakai
assessment lima dimensi /20 dan nilai resmi 1–4. UTS memiliki makalah (10%)
serta lima sesi 1, 2a, 2b, 3a, 3b (masing-masing 18%). Tiap sesi dinilai pada
enam dimensi resmi. Acuan struktur/bobot berasal dari `azral1962/kipp-students`
commit `d2d06c45aaf71773336900b9c885ace71d7df7e4`.

## Mahasiswa

1. Isi `portfolio/week-08.qmd`, `portfolio/UTS/paper.qmd`, dan kelima laporan.
2. Gunakan nama laporan sesuai PENUGASAN.md. Bila memakai `hasil_2a_NIM.qmd`,
   perbarui tautan indeks W08 agar mengarah ke laporan itu.
3. Render/publikasikan GitHub Pages. Worker membaca indeks dan enam halaman HTML
   tertaut, termasuk transkrip, refleksi dan uji ulang; bukan hanya ringkasan indeks.
4. Jalankan `/submit W08`, `/llm TICKET`, lalu `/hasil W08`.
5. `/skor A08` menampilkan nilai UTS resmi /100 setelah moderasi. Sebelum itu,
   nilai final belum tersedia. Ambang pencapaian UTS menunggu ketetapan dosen.

Nama berkas yang diterima: `paper.html`, `hasil_1.html`, `hasil_2a.html`,
`hasil_2b.html`, `hasil_3a.html`, `hasil_3b.html` atau varian `hasil_SESI_NIM.html`.
Tautan harus berada di `portfolio/UTS/` pada repo Pages mahasiswa terdaftar.
Tautan contoh, `_Old`, NIM lain dan URL di luar repo tidak dipilih. Dua kandidat
berbeda untuk sesi sama dianggap ambigu dan indeks harus diperbaiki.

## Operator dan dosen

Siapkan acuan individual seperti [uts-references/README.md](uts-references/README.md).
Rubrik makalah belum tersedia pada sumber; masukkan nilai makalah yang sudah
ditetapkan dosen. AI tidak mengarang nilai makalah atau descriptor level resmi.

Konfigurasi opsional di `.env`:

```dotenv
UTS_REFERENCE_DIR=uts-references
UTS_ASSESSMENT_CSV=uts-assessment.csv
```

Path relatif dihitung dari folder proyek pada bot/CLI. Untuk penggunaan library,
berikan `uts_reference_dir`, `uts_assessment_path` dan loader UTS secara eksplisit.

Worker memproses sesi satu per satu; transkrip yang melebihi
`LLM_MAX_EVIDENCE_CHARS` per sesi diberi BT tanpa pemotongan. Tingkatkan batas
hanya sesuai kapasitas model. Halaman 404/410 dilaporkan tidak tersedia; error
jaringan atau server sementara mengembalikan tiket ke ANTRI. Template kosong,
evidence parsial, acuan belum tersedia dan skor BT tidak menghasilkan nilai final.

Snapshot indeks, makalah, laporan dan acuan disimpan lokal di
`assessment-inputs/tiket-N-W08-evidence.json`. Request model per sesi juga disimpan.
Hasil memakai `assessment-results/tiket-N-W08-uts-v1.json` dan `.md`; hasil W08
lama tanpa suffix tidak digunakan. Cache mencocokkan hash evidence, acuan, prompt
dan schema setelah mengambil ulang halaman. Hasil UTS selalu menunggu persetujuan,
termasuk ketika `LLM_AUTO_APPROVE=true`.

Dosen membaca JSON/Markdown dan membandingkan skor dengan snapshot/acuan. Koreksi
skor, evidence, alasan atau status evidence pada JSON sebelum persetujuan bila
perlu, lalu catat alasan moderasi pada `reason`. Field kontrak, manifest dan hash
input harus tetap sesuai sumber. Receipt menyimpan hash seluruh laporan yang
disetujui sehingga revisi sesudah approval tidak diam-diam mengubah nilai resmi.
Markdown adalah tampilan usulan AI awal; JSON yang dibaca approval menjadi sumber
hasil yang dimoderasi.

```powershell
python llm.py --approve 7 --paper-score 80 --assessor "Nama Dosen"
```

Approval memerlukan makalah tersedia dan semua sesi sah. Nilai sesi dihitung
ulang dari enam skor: `jumlah /24 ×100`. Nilai final = `0,10×M + 0,18×jumlah lima
sesi`; tidak ada pembobotan ulang atau penggantian BT dengan nol. Perhitungan
memakai Decimal tanpa pembulatan antara; tampilan final dua desimal. Makalah 80
dan semua sesi 75 menghasilkan 75,50. Rata-rata kasus 2/3 hanya ringkasan.

Hasil resmi disimpan di `uts-assessment.csv`, terpisah dari `assessment.csv`,
dengan NIM sebagai teks, tiket, nilai komponen, nama assessor, waktu dan hash
laporan. Approval identik dapat diulang tanpa duplikasi. Tiket yang sudah resmi
tidak dapat dinilai ulang; submission revisi memakai tiket baru. Nilai resmi lama
tetap tersedia sambil revisi menunggu moderasi. `/skor A08` membaca receipt dengan
nomor tiket terbesar milik mahasiswa, bukan self-score atau usulan AI.

Jika acuan/evidence diperbaiki setelah BT, atau tiket W08 lama masih menunggu
persetujuan, antrekan ulang melalui operator:

```powershell
python llm.py --retry-uts 7
python llm.py --once
```

Retry hanya menerima W08 berstatus MENUNGGU PERSETUJUAN atau GAGAL. Mahasiswa
juga dapat menjalankan `/llm 7` setelah operator mengantrekan ulang. Untuk
submission aktif, `/submit W08` tetap menggunakan tiket yang ada agar tidak
menduplikasi pekerjaan.

## Migrasi data lama

A08 dipertahankan sebagai data historis, tidak ditimpa nilai UTS /100. TOTAL
yang dihitung ulang hanya menjumlahkan tugas mingguan aktif, mengecualikan A08.
Sebelum mengoperasikan versi baru, hentikan bot/worker lama dan migrasikan TOTAL
CSV aktual secara eksplisit:

```powershell
python uts.py --migrate-weekly assessment.csv
```

Perintah membuat `assessment.csv.before-uts.bak` sekali, mempertahankan A08,
lalu menghitung ulang TOTAL. Jika memakai `ASSESSMENT_CSV` kustom, berikan path
aktual. Migration tidak dijalankan otomatis saat startup. Nilai final mata kuliah
tidak dihitung: bobot UTS terhadap komponen mata kuliah lain belum diberikan.

## Validasi

```powershell
python -m unittest discover -s tests -v
```

Tes UTS memakai peserta, descriptor dan respons model dummy. Uji operasional
server LLM dengan paket dummy di lingkungan operator sebelum penilaian resmi.
Patch tidak menjalankan bot, memanggil model nyata atau memigrasikan CSV produksi.
