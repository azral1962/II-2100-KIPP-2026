# KIPP-CI v3 — TISE Collective Intelligence Laboratory

Untuk peserta kelas, gunakan [Panduan Mahasiswa KIPP_ci_bot](kipp-ci-panduan-mahasiswa.md)
atau [PDF siap dibagikan](../output/pdf/kipp-ci-panduan-mahasiswa.pdf).
Panduan di bawah ditujukan terutama bagi dosen/operator.

Versi 3 menambahkan dashboard Streamlit, sesi TAIDA, indikator modal sosial,
evaluasi perkembangan CI, eksperimen multi-agen lokal, dan Project Charter UAS.
Bot Telegram, token `TELEGRAM_BOT_TOKEN_CI`, identitas `peserta.csv`, persetujuan,
antrean fasilitator, intervensi, serta konsensus versi 2 tetap digunakan.

## Jalankan demo lokal

Dashboard default menggunakan **demo sintetik**, bukan database kelas. Setiap
sesi browser memperoleh direktori/database demo terpisah di folder temporer.
Tidak ada pesan dikirim ke Telegram. Pembuatan data dilakukan saat halaman
pertama dibuka, tanpa token atau layanan AI eksternal.

```bash
.venv/bin/python -m pip install -r requirements-ci-dashboard.txt
CI_DASHBOARD_MODE=demo .venv/bin/python -m streamlit run ci_dashboard.py --server.address 127.0.0.1 --server.port 8502
```

Pada PowerShell:

```powershell
$env:CI_DASHBOARD_MODE="demo"
.venv\Scripts\python -m streamlit run ci_dashboard.py --server.address 127.0.0.1 --server.port 8502
```

Buka `http://localhost:8502`. Pilihan peran Dosen/Fasilitator/Mahasiswa pada mode
demo merupakan **peran fiktif untuk demonstrasi**, tidak dapat dipakai untuk
membuka data produksi. Mode demo menggunakan kelompok dan survei sintetis yang
diberi label jelas. Direktori temporer dapat dibersihkan operator setelah demo;
jalankan ulang sesi browser untuk membuat demo baru jika diperlukan.

## Mode kelas dengan autentikasi

Mode `live` tidak menampilkan data sebelum login OIDC dan pemetaan identitas
terverifikasi berhasil. Tidak ada password bersama atau pilihan bebas ID/NIM.

1. Konfigurasikan penyedia OpenID Connect yang digunakan institusi.
2. Salin `ci.secrets.example.toml` ke `.streamlit/secrets.toml`, lalu isi
   `client_id`, `client_secret`, `cookie_secret` acak panjang, metadata provider,
   serta redirect URI yang didaftarkan pada provider.
3. Pada `[ci_users]`, petakan **issuer dan subject** dari provider ke Telegram ID
   yang sudah terdaftar. Format kunci: `ISSUER|SUBJECT`. Email yang diketik
   pengguna tidak dipercaya untuk menentukan identitas atau peran.
4. Pertahankan konfigurasi bot pada `.env`: `CI_CHAT_IDS`, `PESERTA_CSV`,
   `CI_DATABASE`, `CI_FACILITATOR_IDS`, dan `CI_INSTRUCTOR_IDS`.
5. Jalankan dashboard dengan `CI_DASHBOARD_MODE=live`. Untuk deployment publik,
   operator perlu konfigurasi HTTPS, redirect provider, dan akses server yang sesuai.

Contoh:

```bash
CI_DASHBOARD_MODE=live .venv/bin/python -m streamlit run ci_dashboard.py --server.address 127.0.0.1 --server.port 8502
```

Peran ditentukan ulang pada setiap rerun. Fasilitator giliran kehilangan akses
kokpit ketika tugasnya selesai. Mahasiswa hanya melihat asesmen pribadinya;
dosen boleh memilih peserta untuk meninjau bukti. Data kolektif dan percakapan
kelas tersedia bagi peserta yang terdaftar, dengan pseudonim pada explorer.
Tabel kolektif tidak memuat JSON asesmen pribadi, NIM, atau ID Telegram.
Pseudonimisasi bukan anonimisasi penuh karena isi percakapan dapat dikenali.

Login dashboard memakai identitas tambahan untuk autentikasi web; tidak
membuat pendaftaran mahasiswa baru atau mengubah `peserta.csv`. Pemetaan akun
OIDC dilakukan operator pada server. Rahasia tidak ditampilkan di dashboard
atau disimpan dalam database CI. `.streamlit/secrets.toml` diabaikan Git.

## Halaman dashboard

1. **Ikhtisar:** tujuan, fase TAIDA, kohort, pesan, keputusan, indeks eksploratif,
   cuplikan percakapan, mulai/tutup sesi bagi fasilitator.
2. **Perkembangan CI:** grafik snapshot, perubahan awal–akhir, cakupan data,
   komponen/bobot, indikator modal sosial, dan agregat survei.
3. **Penjelajah percakapan:** filter pseudonim, kategori kontribusi, tanggal dan
   teks; ID bukti, relasi balasan, serta ekspor CSV percakapan terfilter.
4. **Refleksi dan survei:** bukti kontribusi sendiri, grafik aktivitas, indikator
   rubrik, serta survei sukarela pra/pasca. Dosen memiliki akses tinjauan peserta.
5. **Project Charter UAS:** draf berversi, bagian editorial yang dapat dilengkapi,
   sumber keputusan, persetujuan dosen, serta ekspor Markdown.
6. **Kokpit fasilitator:** perbedaan pendapat, ketimpangan, peserta belum teramati,
   analisis manual, dan menerima/menyunting/mengabaikan intervensi. Kiriman ke
   Telegram tetap dilakukan proses bot; dashboard tidak mengirim langsung.
7. **Simulasi multi-agen:** eksperimen berpasangan berdasarkan seed, perbandingan
   kebijakan, replay langkah, dan ekspor JSON sintetik. Tersedia dalam demo atau
   untuk dosen pada mode kelas; semua eksperimen memakai database terpisah.
8. **Konfigurasi:** bobot indeks per forum dan penetapan kelompok oleh dosen.
   Halaman ini tidak menampilkan token, API key, atau konfigurasi rahasia login.

Navigasi dan pemeriksaan akses dilakukan pada server; menyembunyikan tombol
bukan satu-satunya pembatasan. Layanan asesmen memeriksa pemilik bukti dan peran,
charter memeriksa hak dosen, dan pemetaan kelompok/bobot memerlukan dosen.

## Sesi, fase, dan perintah bot

Mulai ulang `ci.py` untuk menerapkan migrasi aditif tabel `ci_v3_*`. Bot tidak
menjalankan dashboard secara otomatis.

```text
/sesi mulai Laboratorium spesifikasi UAS
/fase Target
/fase Attention
/fase Interest
/fase Desire
/fase Action
/sesi selesai
```

Fase boleh bergerak mundur jika muncul kebutuhan/informasi baru. Sesi adalah
batas evaluasi; percakapan di luar sesi tetap tersimpan oleh observer tetapi
tidak masuk metrik sesi itu. Satu forum mempunyai paling banyak satu sesi aktif.
Awal sesi menyimpan kohort dari `peserta.csv` agar denominator partisipasi jelas.
Setelah sesi ditutup, pesan kemudian tidak menambah hasil sesi tersebut.

| Perintah | Akses dan fungsi |
|---|---|
| `/sesi` | Status sesi terbaru |
| `/sesi mulai JUDUL` | Fasilitator membuka sesi |
| `/sesi selesai` | Fasilitator menutup sesi dan menyimpan snapshot akhir |
| `/fase [NAMA]` | Melihat fase; perubahan khusus fasilitator |
| `/survei pra 4,4,4,4` | Survei pribadi sukarela pra kegiatan |
| `/survei pasca 4,4,4,4` | Survei pribadi sukarela pasca kegiatan |
| `/modal_sosial` | Indikator observasional sesi terbaru |
| `/perkembangan` | Ringkasan indeks, cakupan dan snapshot sesi |
| `/charter` | Charter terbaru beserta status dan sumbernya |
| `/charter buat JUDUL` | Fasilitator membuat draf dari konsensus dikonfirmasi |
| `/charter setujui ID` | Dosen menyetujui dokumen, lewat chat pribadi |
| `/dashboard` | Petunjuk menjalankan dashboard |

Survei memakai urutan **persepsi trust, rasa didengar, rasa aman mengemukakan
pendapat, kesediaan bekerja sama**, masing-masing 1–5. Ini instrumen eksploratif
sukarela, bukan tes psikologis tervalidasi. Memerlukan persetujuan penggunaan data.
Rata-rata hanya ditampilkan setelah minimal **5** responden per tahap; perubahan
pra–pasca memakai peserta berpasangan yang sama dan juga minimal 5 pasangan.
Nilai survei individu tidak muncul pada tabel dosen atau laporan kolektif.

## Rumus dan batasan indeks CI

Indeks **bukan ukuran ilmiah yang tervalidasi, bukan nilai akademik, dan bukan
pengukuran kualitas manusia**. Komponen 0–1 yang digunakan:

| Komponen | Definisi operasional | Bobot awal |
|---|---|---:|
| participation | Mahasiswa dengan pesan / jumlah kohort sesi | 20% |
| balance | Entropi distribusi pesan mahasiswa / log(jumlah kohort) | 15% |
| knowledge | min(1, (pesan dengan tautan/penanda alasan + 2 × integrasi bersumber valid) / seluruh pesan sesi) | 20% |
| deliberation | min(1, jumlah balasan lintas penulis dengan sumber tersedia / seluruh pesan sesi) | 15% |
| action | Putaran dikonfirmasi / seluruh putaran nonsuperseded yang dimulai dalam sesi | 15% |
| reciprocity | Pasangan penulis yang saling membalas / pasangan dengan sedikitnya satu arah balasan | 15% |

Skor = `100 × Σ(bobot × nilai tersedia) / Σ(bobot komponen tersedia)`.
Cakupan = jumlah bobot yang komponen datanya tersedia. Komponen tidak tersedia
bernilai `null`, bukan otomatis nol. Indeks tidak diterbitkan sebelum ada minimal
6 pesan mahasiswa. Denominator `knowledge` dan `deliberation` mencakup pesan staf
juga; ini indikator proses keseluruhan, bukan atribusi prestasi mahasiswa.
Tautan dan penanda alasan belum memvalidasi kebenaran informasi. Integrasi
hanya dihitung jika semua pesan sumber tersedia dalam sesi dan revisinya cocok.

Snapshot bersifat kumulatif sejak awal sesi, bukan jendela dengan volume sama.
Snapshot disimpan saat bot menganalisis sesi aktif, saat diminta fasilitator,
dan saat sesi ditutup. Data tidak berubah tidak menghasilkan snapshot baru.
Snapshot menyimpan komponen, bobot, sumber, dan keterbatasan; sumber yang diedit
atau hilang ditandai tidak lagi valid dan dikeluarkan dari grafik.

Perubahan awal–akhir hanya **deskriptif**. Perubahan bobot, komposisi kohort,
pemetaan kelompok, volume dan jenis aktivitas dapat menjelaskan selisih indeks.
Dashboard tidak menyatakan intervensi menyebabkan pertumbuhan CI. Replay
menggunakan teks/revisi yang saat ini tersimpan; tidak merekonstruksi isi pesan
sebelum edit historis. Data sintetik tidak memiliki masalah edit historis itu.

## Modal sosial observasional

- **Bonding:** jumlah balasan antar mahasiswa dengan kelompok eksplisit sama.
- **Bridging:** jumlah balasan antar mahasiswa dengan kelompok eksplisit berbeda.
- **Linking:** jumlah balasan dua arah mana pun antara mahasiswa dan staf/dosen
  konfigurasi. Ini relasi percakapan teramati, bukan akses kekuasaan atau trust.
- **Reciprocity:** pasangan penulis yang memiliki balasan kedua arah.

Balasan diri sendiri tidak dihitung. Kedua pesan harus tersedia pada sesi yang
sama. Kelompok tidak ditebak dari bahasa, pergaulan, atau profil; dosen
menetapkannya melalui Konfigurasi. Balasan dengan kelompok belum diketahui
memiliki penghitung dan cakupan sendiri; bonding/bridging `null` jika pemetaan
belum tersedia. Survei persepsi ditampilkan terpisah dari indikator jaringan.
Fasilitator mahasiswa giliran bukan otomatis staf untuk indikator linking.

## Simulasi multi-agen lokal

```bash
python3 ci.py --simulate --database /tmp/ci-v3-demo.sqlite3 --seed 42 --policy inclusive --steps 120
```

Gunakan path baru. Kebijakan yang tersedia:

- `none`: kesempatan bicara terkonsentrasi pada 8 agen awal.
- `inclusive`: giliran bergilir pada 40 agen.
- `bridge`: giliran antar kelompok dan preferensi balasan lintas kelompok.

Setiap agen memiliki state kontribusi, kebutuhan kelompok yang telah teramati,
dan gaya kontribusi fiktif. Agen mengamati riwayat, memilih balasan, serta
menghasilkan pesan menurut fase dan kebijakan. Model ini **agen berbasis aturan**,
bukan subproses LLM atau manusia sintetis yang dianggap setara mahasiswa nyata.
Ada 40 agen, 4 kelompok dan fase TAIDA selama jam logis 110 menit. Seed yang sama
dan kebijakan yang sama mereproduksi event percakapan yang sama. Waktu absolut
run dapat berbeda, sehingga kesamaan diuji pada event dan state, bukan timestamp.

Asumsi penerimaan usulan: kebutuhan kelompok harus pernah terwakili dalam
percakapan. Karena itu kebijakan `none` dapat menyisakan keberatan, sedangkan
kebijakan yang memberi ruang kelompok lain dapat mencapai konfirmasi. Hasil
tersebut mengikuti asumsi model, **bukan bukti bahwa kebijakan itu pasti unggul
di kelas nyata**. Semua keputusan/survei/charter pada simulasi diberi label
sintetik; baseline yang tidak mencapai konfirmasi tidak dibuatkan charter.

## Project Charter UAS

Draf membutuhkan sedikitnya satu putaran konsensus yang telah dikonfirmasi pada
sesi tersebut. Isi kebutuhan fungsional disalin persis dari usulan yang disepakati,
dengan ID R/U sebagai sumber. Bagian berikut dapat disunting fasilitator:

- Rumusan masalah dan pengguna sasaran.
- Kebutuhan nonfungsional, fitur AI, dan model data.
- Kriteria penerimaan, paket pekerjaan, dan roadmap implementasi.

Bagian editorial diberi label rancangan, bukan otomatis kesepakatan kelas.
Dokumen juga menjelaskan pembagian peran CI, NI, dan AI. Setiap penyimpanan
membuat versi baru dengan pemeriksaan versi untuk mencegah penimpaan suntingan.
Dosen dapat menyetujui dokumen; persetujuan editorial tersebut tidak menggantikan
konfirmasi peserta jika bagian baru ingin dinyatakan sebagai konsensus.

Jika putaran sumber dibuka ulang atau tidak lagi dikonfirmasi, charter menjadi
`stale`, ekspornya diberi peringatan, dan tidak dapat disetujui sebelum versi baru
disusun dari sumber valid. Format ekspor versi ini **Markdown**; PDF belum
diterapkan. Tidak ada kebutuhan atau legitimasi keputusan yang dikarang oleh LLM.

## Penyimpanan, retensi dan pemeriksaan

Database SQLite diperluas secara aditif. Tabel versi 1/2 tetap ada. Sesi, kohort,
kelompok, survei, snapshot, bobot, dan charter disimpan pada `ci_v3_*`; eksperimen
sintetik memakai database/CSV tersendiri. Bot tetap memerlukan satu proses per
token; dashboard menggunakan koneksi SQLite singkat dan transaksi untuk perubahan.

`/hapusdata` menghapus survei, snapshot turunan, serta charter yang kehilangan
bukti konsensus terkait peserta. Kebijakan retensi bot juga diterapkan pada
sesi yang telah ditutup, survei, snapshot dan charter. Sesi aktif dipertahankan
sampai ditutup; operator sebaiknya menutup sesi selesai. Retensi berjalan melalui
polling bot. Cadangan dan berkas unduhan yang sudah diekspor dikelola operator.

```bash
python3 -m unittest discover -s tests -p 'test_ci*.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_ci_dashboard.py' -v
```

Pengujian dashboard memakai Streamlit AppTest tanpa server/browser, mencakup
seluruh halaman, peran mahasiswa, login yang belum dikonfigurasi, dan pemetaan
issuer/subject. Uji layanan mencakup jaringan balasan, data hilang, bobot, survei,
privasi asesmen, sumber/versi charter, penghapusan, serta reproduksibilitas simulasi.
Uji login nyata membutuhkan konfigurasi provider institusi; pengujian lokal tidak
mengklaim telah menguji kredensial OIDC atau koneksi Telegram produksi.

## Bergabung otomatis setelah persetujuan

Setelah mahasiswa mengirim `/setuju` melalui chat pribadi, bot memberikan tautan
**Request to Join / Minta Bergabung** untuk grup pada `CI_CHAT_IDS`. Mahasiswa
menekan tautan dan meminta bergabung; bot kemudian menyetujui permintaan bila
Telegram ID masih terdaftar di `peserta.csv` dan persetujuannya masih aktif.
Telegram tetap memerlukan tindakan peserta menekan tautan; bot tidak menambahkan
akun ke grup tanpa tindakan tersebut.

Persiapan operator:

1. Tambahkan bot CI ke grup yang sudah ada dan tercantum pada `CI_CHAT_IDS`.
2. Jadikan bot administrator dengan hak **Invite Users / Mengundang Pengguna**
   (`can_invite_users`). Bot membuat tautan permintaan bergabung miliknya sendiri.
3. Mulai ulang `ci.py` agar menerima update `chat_join_request`.
4. Mahasiswa membuka bot memakai akun terdaftar, lalu `/start` dan `/setuju`.

`/gabung` di chat pribadi meminta kembali tautan tanpa mengubah persetujuan.
Bot memberi tahu jika peserta sudah menjadi anggota. Akun yang dibatasi admin
(`kicked`) tidak dibuka blokirnya. Jika hak bot belum cukup, persetujuan peserta
tetap tersimpan; perbaiki izin lalu minta peserta memakai `/gabung`.

Tautan dibuat dengan masa berlaku 24 jam dan dipakai ulang selama masih valid.
Tautan dapat diteruskan, tetapi bot menolak permintaan melalui tautannya sendiri
jika akun pemohon tidak terdaftar atau belum/tidak lagi menyetujui penggunaan data.
Permintaan melalui tautan milik admin lain dibiarkan untuk ditinjau admin tersebut.
Persetujuan dicek lagi saat permintaan masuk, sehingga `/tarik` sebelum bergabung
mencegah persetujuan otomatis. `/tarik` atau `/hapusdata` tidak mengeluarkan
anggota yang sudah berada di grup; peserta dapat keluar melalui Telegram.

Catatan tautan dan hasil pemrosesan update disimpan lokal untuk menghindari
pembuatan tautan atau persetujuan berulang saat retry. Pengiriman pesan respons
masih mungkin berulang setelah gangguan jaringan. Fitur ini hanya menghubungkan
peserta yang ada; tidak menulis ulang identitas atau token.

Kontrak API: [createChatInviteLink](https://core.telegram.org/bots/api#createchatinvitelink)
dan [approveChatJoinRequest](https://core.telegram.org/bots/api#approvechatjoinrequest).
