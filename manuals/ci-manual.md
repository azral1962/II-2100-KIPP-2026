# KIPP-CI tahap 1 — Forum Observer

Versi terkini: [v2 Intelligent Facilitator](ci-v2-manual.md). Panduan ini
menjelaskan dasar pencatatan dan antrean fasilitator yang tetap berlaku.

Implementasi bertahap dari `ci_prompt.md`. Tahap ini mengamati percakapan nyata
pada Telegram supergroup: pencatatan pesan/caption, edit dan relasi balasan,
analisis kontribusi lokal, ringkasan ekstraktif, serta refleksi berbukti.
`ci.py` tetap menjadi entry point; `ci_observer.py` menangani database, kontrol
akses dan analisis; `ci_simulator.py` menyediakan replay sintetik.

## Menjalankan bot

Token `TELEGRAM_BOT_TOKEN_CI` dan identitas pada `peserta.csv` tetap digunakan.
Tidak perlu registrasi ulang. Jangan mengganti token atau menjalankan dua proses
polling untuk token yang sama. Hentikan proses CI lama sebelum menjalankan versi ini.
Bot tugas kuliah dengan token berbeda dapat tetap berjalan.

Tambahkan konfigurasi grup dan peran di `.env` tanpa menghapus isinya yang lama:

```dotenv
# Pertahankan TELEGRAM_BOT_TOKEN_CI yang sudah ada.
CI_CHAT_IDS=-1001234567890
CI_FACILITATOR_IDS=123456789
CI_INSTRUCTOR_IDS=987654321
CI_ANALYSIS_SECONDS=600
CI_SUMMARY_SECONDS=1200
CI_RETENTION_DAYS=90
```

Isi ID numerik sebenarnya. Beberapa ID dipisahkan koma. Fasilitator dan dosen
ditetapkan hanya lewat konfigurasi server, bukan klaim melalui chat. Dosen boleh
berada di luar daftar mahasiswa; peserta mahasiswa tetap dibaca dari CSV setiap
pesan. `CI_CHAT_IDS` kosong menonaktifkan pencatatan seluruh grup.

```bash
.venv/bin/python ci.py
```

Python 3.10+ dengan pustaka standar cukup. Tidak ada dependensi baru pada tahap
ini. Transport Telegram yang sudah tersedia di proyek dipakai kembali agar bot
lama tidak berubah. SQL memakai parameter binding dan foreign key; migrasi SQLite
bersifat aditif. Tabel `topics`, `posts`, dan `receipts` versi sebelumnya tetap
tersimpan sebagai arsip. Perintah forum pribadi versi lama diganti oleh perintah
observer; pesan pribadi biasa tidak dikumpulkan sebagai percakapan kelas.

1. Tambahkan bot ke supergroup yang tercantum pada `CI_CHAT_IDS`.
2. Atur akses agar bot menerima percakapan biasa: jadikan bot administrator atau
   nonaktifkan Privacy Mode melalui BotFather. Setelah mengubah Privacy Mode,
   ikuti petunjuk Telegram untuk menerapkannya pada grup (dapat perlu menambahkan
   bot kembali). Pastikan bot dapat mengirim pesan.
3. Mahasiswa membuka chat pribadi dengan bot, menjalankan `/start`, membaca
   penjelasan penggunaan data, lalu `/setuju`. Ini persetujuan pengamatan,
   bukan registrasi ulang.
4. Mulai percakapan biasa di grup. Bot mencatat diam-diam dan tidak menilai setiap
   pesan secara publik. Gunakan balasan Telegram untuk menghubungkan gagasan.
5. Fasilitator memakai `/analisis`, atau menunggu analisis setiap 10 menit dan
   ringkasan setiap 20 menit. Interval mengikuti polling; ringkasan pertama dapat
   dikirim segera ketika ada data, dan hanya diulang ketika sumber berubah.

Kemampuan menerima pesan mengikuti [Telegram Bot FAQ](https://core.telegram.org/bots/faq#what-messages-will-my-bot-get)
dan [Telegram Bot API](https://core.telegram.org/bots/api#getupdates). Bot tidak
mengambil riwayat grup sebelum memperoleh akses. Pesan dari akun bot, pengirim
anonim/channel, grup di luar allowlist, peserta tidak dikenal, atau peserta yang
belum setuju diabaikan. Pesan lama yang mendahului persetujuan tidak diambil ulang.
Foto/dokumen hanya dicatat caption-nya; tidak ada download atau transkripsi media.
Bot menerima `edited_message`. Penghapusan pesan biasa tidak tersedia sebagai
notifikasi umum Telegram Bot API; hapus lokal melalui `/hapusdata` atau retensi.

## Perintah tahap 1

| Perintah | Akses dan fungsi |
|---|---|
| `/start`, `/help`, `/bantuan` | Pengantar dan penjelasan data |
| `/setuju`, `/tarik`, `/hapusdata` | Chat pribadi; persetujuan, penarikan, atau hapus data observer sendiri |
| `/tujuan` | Misi spesifikasi aplikasi AI untuk UAS |
| `/forum ID_GRUP` | Pilih salah satu forum yang diizinkan untuk perintah pribadi |
| `/status` | Status pencatatan dan jumlah kontribusi kelas |
| `/request_fasilitator` atau `/request` | Mahasiswa meminta giliran fasilitator |
| `/unrequest_fasilitator` atau `/unrequest` | Membatalkan permintaan yang masih menunggu |
| `/selesai_fasilitator` | Fasilitator aktif melepas peran dan meneruskan giliran |
| `/antrian_fasilitator` | Melihat nama fasilitator aktif dan urutan tunggu |
| `/ringkasan` | Kutipan ekstraktif hingga 12 pesan terakhir dengan ID bukti |
| `/refleksi`, `/profil` | Chat pribadi; riwayat sendiri dan indikator enam dimensi |
| `/rubrik` | Bobot, skala, dan batasan rubrik |
| `/bukti ID_PESAN` | Chat pribadi; rincian bukti dan asesmen sendiri, atau seluruh bukti bagi staf |
| `/tinjauan` | Dosen di chat pribadi; hingga 20 catatan tinjauan terbaru |
| `/tinjau ID_PESAN ALASAN` | Chat pribadi; minta dosen meninjau bukti milik sendiri |
| `/analisis`, `/laporan` | Fasilitator/dosen; analisis incremental dan laporan kolektif |
| `/pause`, `/resume` | Fasilitator/dosen; jeda/lanjut pencatatan serta analisis baru |
| `/koreksi ID_PESAN CATATAN` | Dosen di chat pribadi; catatan koreksi bersama asesmen asli |

ID pada `/tinjau` dan `/koreksi` adalah angka setelah M pada laporan (M12 → 12),
bukan nomor pesan Telegram. Laporan kolektif tidak menampilkan nilai individual.
Daftar NIM yang belum teramati hanya muncul pada `/laporan` atau `/analisis`
melalui chat pribadi staf. Permintaan tinjauan dan koreksi tersimpan di database
`ci_reviews`, dapat dibaca dosen melalui `/tinjauan`; belum ada notifikasi otomatis kepada dosen.
Koreksi tidak menimpa indikator asli dan tidak menetapkan nilai akademik.
Saat dijeda, ringkasan data lama dan penghapusan tetap tersedia; pengumpulan,
analisis terjadwal, serta refleksi baru dihentikan.

## Giliran fasilitator mahasiswa

Antrean terpisah untuk setiap forum. Mahasiswa yang tercatat di `peserta.csv`
dapat mengajukan diri tanpa perubahan konfigurasi atau registrasi ulang. Jika
belum ada fasilitator mahasiswa aktif, pemohon pertama langsung mendapat giliran.
Pemohon berikutnya menunggu sesuai urutan permintaan (FIFO). Permintaan berulang
tidak menggandakan antrean atau mengubah posisi. Semua perintah ini tanpa argumen,
dan hanya mengubah giliran pemilik akun sendiri.

```text
Ani:  /request_fasilitator
Budi: /request_fasilitator
Cici: /request_fasilitator
Budi: /unrequest_fasilitator
Ani:  /selesai_fasilitator
```

Ani langsung aktif, Budi membatalkan permintaan, kemudian Cici otomatis menjadi
fasilitator ketika Ani selesai. Peserta yang selesai boleh meminta giliran lagi
dan ditempatkan pada urutan terakhir. `/unrequest_fasilitator` tidak mengakhiri
giliran yang sudah aktif; gunakan `/selesai_fasilitator` untuk itu. Balasan bot
menampilkan fasilitator aktif dan antrean setelah perubahan. Tidak ada DM atau
pengumuman tambahan otomatis; gunakan perintah di grup agar pergantian terlihat
oleh seluruh kelas, atau periksa `/antrian_fasilitator`.

Fasilitator mahasiswa aktif dapat menjalankan `/analisis`, `/laporan`, `/pause`
dan `/resume` hanya pada forum tempat ia bertugas. Hak itu dicabut setelah
giliran selesai. Peran ini tidak memberikan akses ke bukti/asesmen pribadi
mahasiswa lain, `/tinjauan`, atau `/koreksi`. Hak dosen dan fasilitator tetap dari
konfigurasi server berlaku terpisah; menyelesaikan giliran mahasiswa tidak mencabut
hak yang ditetapkan lewat `CI_FACILITATOR_IDS` atau `CI_INSTRUCTOR_IDS`.

Di chat pribadi, pilih forum lewat `/forum ID_GRUP` jika ada beberapa forum.
Perintah antrean tetap tersedia ketika pengamatan dijeda. Antrean dan giliran
aktif tersimpan di SQLite dan tetap berlaku setelah restart. Mahasiswa yang
tidak lagi terhubung pada daftar peserta dikeluarkan dari giliran/antrean saat
pemeriksaan berikutnya, lalu peserta berikutnya dipromosikan. `/hapusdata` juga
menghapus riwayat antrean milik sendiri dan melepas giliran aktif. Riwayat selesai
atau batal mengikuti retensi; giliran aktif dan permintaan menunggu tetap
tersimpan sampai diselesaikan/dibatalkan. Fitur ini tidak mengubah hak admin
Telegram; peran fasilitator hanya berlaku di aplikasi CI.

## Metode analisis dan batasan

Provider tahap 1 adalah `LocalAnalyzer` (`local-rules-v1`), baseline deterministik
untuk demo tanpa API key. Pesan diperlakukan sebagai data, tidak dijalankan sebagai
instruksi. Tidak ada pengiriman teks ke layanan AI eksternal. Analisis mengamati
penanda pertanyaan, usulan, tautan, alasan, perbedaan pendapat, sintesis, fasilitasi,
komitmen dan refleksi. Balasan hanya menjadi bukti integrasi jika pesan induknya
benar-benar tersedia pada forum yang sama.

Enam dimensi mengikuti prompt: relevansi 15%, kontribusi pengetahuan 20%, empati
15%, integrasi 20%, fasilitasi 15%, dan orientasi tindakan 15%. Setiap dimensi
menyimpan skor, status, alasan, ID bukti, rekomendasi, dan confidence. Penanda awal
menghasilkan skor 2/4 dengan confidence rendah 0,35; dimensi lain bernilai `null`
dengan `not_observed`, termasuk relevansi semantik yang membutuhkan tinjauan
manusia. `not_applicable` dan `poor_performance` tidak otomatis disimpulkan.
Tidak ada total berbobot, rata-rata nilai pesan, peringkat publik, kesimpulan
kepribadian, atau klaim validitas ilmiah.

Ringkasan berupa kutipan berpseudonim, bukan sintesis semantik LLM. Kutipan
memungkinkan peserta tetap dikenali dari isinya; pseudonim bukan anonimitas penuh.
Bot tidak menganggap pernyataan setuju sebagai konsensus kelas. Jumlah peserta
aktif dan belum teramati dihitung dari data yang tersimpan, bukan ukuran kualitas
CI atau bukti bahwa peserta lain tidak berpartisipasi. Riwayat longitudinal
tersedia secara deskriptif; inferensi perkembangan kompetensi belum dilakukan.

Analisis tersimpan per pesan dan revisi. Pesan yang tidak berubah memakai cache.
Edit menghapus cache konteks forum agar bukti lama tidak dipakai. Pengiriman ulang
update tidak menggandakan pesan. Offset tetap terpisah dari bot kuliah; respons
Telegram masih dapat terkirim ulang jika proses berhenti setelah mengirim tetapi
sebelum offset disimpan. Jalankan satu instance observer untuk database/token ini.

## Simulasi lokal

```bash
python3 ci.py --simulate --database /tmp/ci-demo.sqlite3 --seed 42
```

Gunakan path baru. Simulasi membuat database dan CSV peserta fiktif terpisah,
40 mahasiswa, 64 kontribusi dengan sebagian peserta belum terdengar, usulan,
keberatan, bukti, balasan, sintesis, serta rencana tindakan. Seluruh keluaran
berlabel sintetik; seed yang sama menghasilkan percakapan yang sama. Simulasi
tidak membaca token atau peserta produksi dan menolak menimpa berkas lama.

## Penyimpanan dan retensi

Database default tetap `ci.sqlite3` dan offset `ci-offset.txt`. Opsi yang tetap
berlaku: `PESERTA_CSV`, `CI_DATABASE`, `CI_OFFSET_FILE`, `CI_POLL_TIMEOUT`.
Semua path relatif terhadap folder proyek. Cadangkan database dan offset bersama
saat bot berhenti sebelum berpindah versi atau komputer.

`/tarik` menghentikan pengumpulan berikutnya. `/hapusdata` menarik persetujuan
serta menghapus pesan observer, asesmen, dan catatan tinjauan terkait peserta;
cache lintas pesan juga dihapus agar tidak menyisakan bukti terhapus. Arsip
forum pribadi versi lama dan backup yang dikelola operator tidak termasuk dalam
penghapusan ini. Operator perlu mengelolanya secara terpisah.
Retensi otomatis default 90 hari diterapkan pada pesan dan audit observer saat
polling. Persetujuan dan ID deduplikasi dipertahankan untuk kontrol pengumpulan;
operator dapat menghapus seluruh database jika menutup layanan. Cadangan lama
harus mengikuti kebijakan retensi operator juga.

## Pengembangan berikutnya

Versi 2 telah menambahkan deteksi proses, intervensi dengan persetujuan manusia,
dan konfirmasi konsensus; lihat [panduan v2](ci-v2-manual.md). Adapter LLM
semantik, dashboard berbasis database, project charter, API, dan deployment
merupakan pengembangan lanjutan.

```bash
python3 -m unittest discover -s tests -p 'test_ci*.py' -v
```
