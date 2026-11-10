# KIPP-CI v2 — Intelligent Facilitator

Versi terkini: [v3 TISE Collective Intelligence Laboratory](ci-v3-manual.md).
Perintah versi 2 di bawah tetap tersedia.

Versi 2 menambahkan dukungan fasilitasi ke Forum Observer: indikasi perbedaan
pendapat, ketimpangan partisipasi, integrasi gagasan dengan bukti, rekomendasi
intervensi, dan pelacakan konsensus melalui konfirmasi manusia.

Token `TELEGRAM_BOT_TOKEN_CI`, `peserta.csv`, antrean fasilitator, persetujuan
peserta, database `ci.sqlite3`, serta offset lama tetap digunakan. `.env` dan
daftar peserta tidak diubah oleh pembaruan ini. Entry point tetap `ci.py`.

## Menjalankan

Hentikan proses CI lama dan cadangkan database/offset bersama. Jalankan kembali:

```bash
.venv/bin/python ci.py
```

Tabel versi 2 dibuat secara aditif pada startup; tabel percakapan, asesmen,
antrean fasilitator, dan arsip versi sebelumnya tetap ada. Tidak ada dependensi
baru. Satu proses untuk setiap token/database. Konfigurasi grup dan peran tetap
seperti [panduan observer](ci-manual.md).

Fasilitator perlu membuka chat pribadi bot terlebih dahulu agar dapat menerima
saran. Jika mengelola beberapa grup, pilih grup melalui `/forum ID_GRUP` sebelum
mengelola intervensi. Peserta tetap menggunakan identitas yang sudah terdaftar;
`/setuju` adalah persetujuan pengumpulan data, bukan registrasi ulang.

## Perintah baru

| Perintah | Fungsi dan akses |
|---|---|
| `/partisipasi` | Indikator partisipasi kolektif, tanpa leaderboard individual |
| `/konflik` | Penanda perbedaan pendapat dengan ID bukti |
| `/integrasi M1,M2 TEKS` | Mencatat integrasi gagasan dari 2–8 pesan sumber, sedikitnya dua penulis berbeda |
| `/integrasi` | Melihat 10 integrasi terbaru yang sumbernya masih valid |
| `/usulan TEKS` | Membuat alternatif solusi formal, maksimal 2.000 karakter |
| `/usulan` | Melihat 10 usulan terbaru |
| `/sepakat ID_USULAN` | Fasilitator membuka putaran konfirmasi; belum mengumumkan kesepakatan |
| `/sikap ID_PUTARAN setuju` | Peserta mengonfirmasi penerimaan usulan |
| `/sikap ID_PUTARAN abstain ALASAN` | Mencatat abstain secara eksplisit |
| `/sikap ID_PUTARAN keberatan ALASAN` | Mencatat keberatan yang perlu dibahas |
| `/keberatan` | Melihat hingga 20 keberatan formal pada putaran yang masih terbuka |
| `/konsensus [ID_PUTARAN]` | Melihat status, jumlah sikap, serta jumlah peserta belum merespons |
| `/konfirmasi ID_PUTARAN` | Fasilitator mengonfirmasi hasil setelah seluruh peserta menyatakan setuju |
| `/bukaulang ID_PUTARAN` | Fasilitator membuka putaran baru untuk usulan yang sama; seluruh sikap perlu diisi ulang |
| `/intervensi` | Fasilitator di chat pribadi melihat hingga 5 saran yang menunggu keputusan |
| `/terapkan ID_INTERVENSI [TEKS]` | Fasilitator di chat pribadi menyetujui saran, opsional dengan suntingan, untuk dikirim ke grup |
| `/alternatif ID_INTERVENSI` | Fasilitator di chat pribadi meminta rumusan pertanyaan alternatif |
| `/abaikan ID_INTERVENSI` | Fasilitator di chat pribadi mengabaikan atau membatalkan saran yang belum diposting |

ID ditampilkan sebagai `M` (pesan), `G` (integrasi), `U` (usulan), `R` (putaran),
dan `I` (intervensi). Pada argumen numerik gunakan angkanya saja, kecuali daftar
sumber `/integrasi` yang menerima `M1,M2` maupun `1,2`. Sumber integrasi harus
tersedia di forum yang sama. Jika sumber diedit atau dihapus, integrasi lama
berhenti dihitung sebagai integrasi valid; kirim integrasi baru setelah meninjau
sumber. Sumber adalah bukti rujukan, bukan validasi kebenaran isi sintesis.

Sikap peserta bisa diperbarui selama putaran masih `open`. Riwayat sikap disimpan
agar perubahan dari keberatan menjadi setuju dapat ditelusuri; fasilitator tidak
dapat mengganti sikap peserta lain. Usulan, integrasi, dan alasan keberatan
formal dapat dibaca anggota forum melalui bot, termasuk jika dikirim lewat chat
pribadi. Umpan balik asesmen individual tetap bersifat pribadi.

## Contoh penggunaan kelas

```text
Mahasiswa:  /request_fasilitator
Mahasiswa:  /usulan Aplikasi perlu memisahkan ringkasan dan konfirmasi keputusan.
Fasilitator: /sepakat 1
Ani:        /sikap 1 setuju
Budi:       /sikap 1 keberatan Perlu memastikan seluruh peserta dapat meninjau bukti.
Fasilitator: /keberatan
```

Diskusikan keberatan dengan pesan dan Reply Telegram. Seseorang dapat merujuk
dua gagasan dengan `/integrasi M12,M18 TEKS`. Hanya Budi yang dapat memperbarui
sikapnya sendiri. Jika teks usulan perlu berubah, buat `/usulan TEKS_BARU` dan
mulai putaran untuk usulan baru; tidak menimpa isi usulan yang sedang dikonfirmasi.

```text
Budi:       /sikap 1 setuju
Fasilitator: /konsensus 1
Fasilitator: /konfirmasi 1
```

`/konfirmasi` ditolak selama masih ada peserta belum merespons, abstain, atau
keberatan. Bot tidak menganggap diam, banyaknya pesan setuju, atau mayoritas
sebagai konsensus. Jika seluruh peserta sudah setuju, status masih `open` sampai
fasilitator secara eksplisit menjalankan `/konfirmasi`.

## Metode konsensus

Metode versi ini adalah **persetujuan eksplisit seluruh peserta pada awal
putaran, kemudian konfirmasi fasilitator**. Snapshot berisi seluruh NIM dan
pemetaan ID Telegram dari `peserta.csv`, termasuk mahasiswa yang belum bergabung
ke grup atau belum mempunyai ID Telegram. Konsekuensinya, mereka tetap tercatat
sebagai belum merespons dan dapat menghambat konfirmasi; data kelas perlu benar.
Bot tidak mengklaim daftar CSV sebagai daftar anggota Telegram yang diverifikasi.

Jika daftar peserta atau pemetaan ID berubah selama putaran, `/konfirmasi`
meminta `/bukaulang`. Putaran baru mereset konfirmasi seluruh peserta tanpa
menghapus riwayat putaran lama. Putaran `confirmed` adalah catatan keputusan
historis dengan peserta saat itu, bukan klaim persetujuan anggota baru.

`/bukaulang` mengubah putaran sebelumnya menjadi `superseded`; bot tidak membawa
sikap lama ke putaran baru. Keputusan yang sudah dikonfirmasi tidak dapat diubah
dengan `/sikap` sampai putaran baru dibuka. Metode mayoritas dan voting anonim
belum diterapkan. Hak memulai/mengonfirmasi putaran mengikuti fasilitator aktif
pada forum tersebut atau staf/dosen yang dikonfigurasi.

## Deteksi dan rekomendasi

Mesin lokal `ci_facilitator.py` memakai hingga **200 pesan terakhir** per forum.
Pengukuran ini berbeda dari hitungan seluruh arsip pada `/status`.

- **Ketimpangan:** setelah sedikitnya 6 pesan mahasiswa, periksa proporsi peserta
  teramati di bawah 60% dan porsi pesan satu kontributor di atas 45%.
- **Perbedaan pendapat:** penanda bahasa seperti “tidak setuju”, “keberatan”,
  “namun”, dan “tetapi”; ditampilkan dengan ID bukti. Perbedaan pendapat bukan
  diagnosis konflik interpersonal atau kondisi emosional.
- **Integrasi:** balasan lintas penulis dengan penanda sintesis merupakan
  kandidat; `/integrasi` mencatat hubungan eksplisit dengan sumber. Mesin
  menyarankan integrasi jika ada usulan dan balasan lintas peserta namun belum
  ada kandidat sintesis/integrasi eksplisit yang valid.
- **Keberatan formal:** berasal dari `/sikap ... keberatan`, bukan ditebak dari
  percakapan. Keberatan terbuka tidak dapat dihapus oleh fasilitator dengan
  menyatakan “sudah selesai”; pemiliknya perlu memperbarui sikap sendiri.

Saran berupa diagnosis kondisi, bukti konteks, dan pertanyaan fasilitasi. Confidence
berlabel rendah karena metode berbasis aturan. Tidak ada inferensi kepribadian,
ukuran trust psikologis, penilaian berdasarkan panjang pesan, atau indeks CI yang
diklaim tervalidasi. Volume pesan hanya petunjuk proses; data yang tidak teramati
bukan bukti mahasiswa tidak berpartisipasi.

Ini implementasi operasional **berbasis aturan lokal**, bukan analisis semantik
LLM. Rekomendasi dan alternatif pertanyaan dibuat dari kondisi terdeteksi dan
template yang dapat diperiksa di source. Tidak ada API key baru atau data yang
dikirim ke layanan AI eksternal. Adapter LLM generatif tetap pengembangan lanjutan.

## Alur intervensi dan penjadwalan

Analisis berkala tetap default 10 menit; ringkasan kolektif 20 menit. `/analisis`
dan `/intervensi` juga dapat memicu deteksi. Saran baru dikirim lewat chat pribadi
ke fasilitator giliran aktif dan staf/dosen konfigurasi. Antrean fasilitator tetap
berfungsi dan peran diperiksa pada setiap tindakan.

Saran **tidak otomatis diposting ke grup**. Fasilitator memilih `/terapkan`,
menambahkan teks suntingan, meminta `/alternatif`, atau `/abaikan`. Saran yang
sudah disetujui disimpan sebagai antrean kirim, lalu dikirim pada siklus polling
berikutnya. Gangguan DM satu fasilitator tidak menghalangi pengiriman kepada
penerima lain. Fasilitator yang belum membuka chat pribadi perlu menekan Start.

Satu saran menunggu keputusan per jenis pemicu/forum, deduplikasi konteks, dan
cooldown default 20 menit mengurangi pengiriman berulang. Saran yang bukti
sumbernya berubah/hilang atau pemicunya tidak lagi berlaku menjadi `stale` dan
tidak diposting, termasuk setelah sebelumnya disetujui. Saat dijeda, pengiriman
saran maupun intervensi yang disetujui ikut ditahan. Telegram tidak menyediakan
transaksi bersama database lokal: jika proses berhenti setelah mengirim tetapi
sebelum menandai sukses, pesan dapat terkirim lagi setelah restart.

Opsi `.env` tambahan:

```dotenv
CI_PARTICIPATION_MIN_MESSAGES=6
CI_DOMINANCE_SHARE=0.45
CI_ACTIVE_RATIO=0.60
CI_INTERVENTION_COOLDOWN_SECONDS=1200
```

## Data, penghapusan, dan pengujian

Usulan, putaran, snapshot peserta, sikap dan riwayatnya, integrasi beserta sumber,
saran, keputusan fasilitator, serta catatan pengiriman tersimpan dalam tabel
`ci_v2_*`. Mutasi dan receipt update Telegram disimpan dalam transaksi yang sama
agar retry tidak menggandakan usulan, putaran, atau sikap.

`/hapusdata` menghapus usulan/integrasi yang ditulis peserta, menghapus bukti
sikapnya, dan membuat putaran yang kehilangan bukti manusia menjadi
`superseded`. Intervensi bersumber pesan yang dihapus tidak lagi boleh dikirim.
Catatan kiriman di Telegram, pesan orang lain yang mengutip peserta, dan backup
operator tidak dihapus otomatis. Retensi yang sudah dikonfigurasi berlaku juga
untuk usulan/putarannya, integrasi dan intervensi. Antrean fasilitator tetap
mengikuti aturan versi sebelumnya.

```bash
python3 -m unittest discover -s tests -p 'test_ci*.py' -v
python3 ci.py --simulate --database /tmp/ci-v2-demo.sqlite3 --seed 42
```

Simulasi memakai 40 peserta fiktif dan 64 pesan, menguji integrasi bersumber,
keberatan yang diubah pemiliknya, serta status sebelum/sesudah konfirmasi
fasilitator. Gunakan path baru; database produksi tidak dibaca atau diubah.
Semua hasil simulasi berlabel sintetik.
