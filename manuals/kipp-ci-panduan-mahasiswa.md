# Panduan Mahasiswa KIPP_ci_bot

**KIPP-CI v3 | TISE Collective Intelligence Laboratory**  
Mata kuliah II2100 - Komunikasi Interpersonal dan Publik (KIPP)  
Edisi 10 November 2026

## Panduan cepat: mulai di sini

1. Buka akun **@KIPP_ci_bot** yang dikonfirmasi dosen. Gunakan akun Telegram yang sama dengan akun yang sudah terdaftar pada bot perkuliahan.
2. Di **chat pribadi bot**, kirim `/start`. Baca pengantar penggunaan data sebelum melanjutkan.
3. Jika bersedia, kirim `/setuju`. Bot mengirim tautan untuk meminta bergabung ke forum.
4. Tekan tautan, lalu pilih **Request to Join / Minta Bergabung**. Tunggu bot menyetujui akun Anda. Mengirim `/setuju` saja belum memasukkan akun ke grup.
5. Di **grup forum**, baca tujuan melalui `/tujuan`, lalu berdiskusi dengan pesan biasa dan fitur Reply.
6. Ikuti putaran kesepakatan yang dibuka fasilitator. Kirim `/sikap NOMOR_PUTARAN setuju`, atau nyatakan abstain/keberatan beserta alasannya.
7. Di **chat pribadi bot**, gunakan `/refleksi` untuk melihat bukti dan umpan balik milik Anda.

**Tidak perlu registrasi ulang di bot CI.** Bot mengenali Telegram ID yang sudah terhubung dengan data peserta kelas. Jika akun belum dikenali, hubungi dosen; jangan mengirim token, kata sandi, atau kode OTP.

## Daftar isi

1. Tujuan dan cara kerja forum
2. Persiapan dan bergabung ke grup
3. Memilih forum dan tempat mengirim perintah
4. Berdiskusi dan mengikuti ringkasan
5. Membuat usulan dan mengintegrasikan gagasan
6. Menyatakan sikap dan membangun konsensus
7. Mengambil giliran fasilitator
8. Tugas mahasiswa saat menjadi fasilitator
9. Mengikuti sesi TAIDA dan survei
10. Membaca refleksi dan meminta tinjauan
11. Memahami indikator CI dan modal sosial
12. Menggunakan dashboard dan Project Charter UAS
13. Persetujuan, privasi, dan penghapusan data
14. Contoh satu alur kegiatan kelas
15. Daftar perintah peserta dan fasilitator
16. Pemecahan masalah dan daftar periksa

## 1. Tujuan dan cara kerja forum

KIPP_ci_bot mendukung pembelajaran **Collective Intelligence (CI)**: menggabungkan pengetahuan dan perspektif untuk memahami masalah, menimbang alternatif, mengambil keputusan yang dapat dipertanggungjawabkan, dan mengorganisasi tindakan bersama.

Misi forum kelas adalah menyusun spesifikasi proyek UAS: aplikasi AI yang membantu fasilitator membangun CI dalam suatu komunitas.

Laboratorium menggunakan pembagian peran TISE:

| Unsur | Peran dalam kegiatan |
|---|---|
| Collective Intelligence (CI) | Peserta saling berbagi, menanggapi, mengintegrasikan gagasan, dan mengonfirmasi keputusan. |
| Natural Intelligence (NI) | Manusia mengamati kenyataan, memahami konteks, berempati, menilai bukti, dan mengambil tanggung jawab. |
| Artificial Intelligence (AI) | Perangkat lunak membantu mengelompokkan kontribusi, menunjukkan indikator, dan menawarkan pertanyaan fasilitasi. |

**Versi saat ini memakai aturan lokal, bukan percakapan generatif dengan LLM.** Bot tidak otomatis menjawab semua pesan seperti chatbot. Sebagian besar percakapan berlangsung antarmahasiswa; bot mengamati, merangkum secara ekstraktif, dan melayani perintah.

Banyak pesan tidak otomatis berarti kontribusi berkualitas. Ringkasan dan indikator bot juga tidak menggantikan penilaian dosen atau konfirmasi peserta.

## 2. Persiapan dan bergabung ke grup

### 2.1 Pastikan akun yang dipakai benar

Gunakan akun Telegram yang sudah Anda daftarkan pada layanan perkuliahan. Mengganti nama tampilan tidak mengganti Telegram ID; memakai akun Telegram lain dapat membuat bot tidak mengenali Anda.

Jika belum terhubung ke data kelas, minta petunjuk dosen. Bila dosen masih menggunakan alur registrasi pada bot perkuliahan lama, jalankan `/reg NIM_ANDA` di **bot lama tersebut**, bukan di KIPP_ci_bot. Jangan mencoba menggunakan NIM orang lain.

### 2.2 Baca pengantar dan beri persetujuan

Di chat pribadi @KIPP_ci_bot:

```text
/start
```

Baca penjelasan pencatatan pesan dan penggunaan data. Jika bersedia:

```text
/setuju
```

Persetujuan ini berkaitan dengan pengamatan dan penggunaan data lokal; bukan pendaftaran mahasiswa baru. Jika belum bersedia, bicarakan alternatif partisipasi dengan dosen. Jangan menganggap persetujuan sebagai kewajiban yang harus dipenuhi tanpa memahami penjelasannya.

### 2.3 Tekan tautan untuk meminta bergabung

Bot mengirim tautan forum. Tekan tautan tersebut, pilih **Minta Bergabung**, lalu tunggu persetujuan bot.

Bot memeriksa ulang apakah Telegram ID terdaftar dan persetujuan masih aktif. Tautan yang diteruskan kepada akun lain tidak menjamin akun itu akan diterima. Gunakan tautan yang dikirim bot CI; permintaan melalui tautan admin lain mungkin perlu ditinjau admin tersebut.

Jika tautan tidak terlihat atau perlu diminta kembali:

```text
/gabung
```

Tautan memiliki masa berlaku 24 jam sejak dibuat; tautan yang diberikan ulang mungkin masih memakai sisa masa berlaku tautan sebelumnya. Jika kedaluwarsa, minta tautan baru melalui `/gabung`.

Jika bot menyatakan Anda sudah menjadi anggota, buka grup yang sudah ada pada daftar chat Telegram. Jika akses akun dibatasi admin, hubungi dosen; bot tidak membuka blokir secara otomatis.

## 3. Memilih forum dan tempat mengirim perintah

### 3.1 Bedakan chat pribadi dan grup

| Tempat | Kegunaan utama |
|---|---|
| Chat pribadi @KIPP_ci_bot | Persetujuan, tautan bergabung, refleksi, bukti pribadi, permintaan tinjauan, survei, dan saran intervensi saat bertugas. |
| Grup forum kelas | Percakapan bersama, usulan, integrasi gagasan, sikap terhadap usulan, dan pergantian fasilitator yang perlu dilihat kelas. |

Usulan formal, integrasi, dan alasan keberatan **dapat dibaca peserta forum meskipun Anda mengirim perintahnya lewat chat pribadi**. Chat pribadi tidak menjadikan kontribusi formal tersebut rahasia.

### 3.2 Jika ada lebih dari satu forum

Di grup, bot memakai forum tempat Anda mengirim perintah. Di chat pribadi, jika hanya ada satu forum, bot memilihnya secara otomatis. Jika ada beberapa forum, gunakan ID grup yang diberikan dosen atau yang terlihat pada keterangan forum dari bot:

```text
/forum -1001234567890
```

Angka di atas hanya contoh. Gunakan ID forum kelas yang benar, termasuk tanda minus. Pemilihan forum ini membantu bot menentukan forum yang dimaksud; tidak mendaftarkan akun ke grup baru.

### 3.3 Cara menulis perintah

Kirim satu perintah dalam satu pesan. Jangan menyertakan tanda petik atau pagar blok kode saat menyalin contoh. Ganti nomor contoh dengan nomor yang diberikan bot.

Perintah bantuan:

```text
/help
```

`/bantuan` juga tersedia. Jika ada beberapa bot di grup dan diperlukan, gunakan bentuk seperti `/status@KIPP_ci_bot` setelah memastikan username bot dari dosen.

## 4. Berdiskusi dan mengikuti ringkasan

### 4.1 Mulai dari tujuan

Di grup:

```text
/tujuan
/status
```

`/tujuan` menampilkan misi kegiatan. `/status` menampilkan kondisi pengamatan dan data partisipasi yang tersedia, bukan status keanggotaan Telegram Anda. Untuk memeriksa apakah Anda sudah menjadi anggota, gunakan `/gabung` di chat pribadi atau lihat grup pada Telegram.

### 4.2 Gunakan pesan biasa dan Reply

Anda tidak perlu mengawali setiap pendapat dengan perintah. Contoh pesan biasa:

> Saya mengusulkan agar aplikasi menampilkan sumber setiap ringkasan. Alasannya, peserta perlu dapat memeriksa kembali konteks sebelum menyetujui keputusan.

Saat menanggapi orang lain, gunakan tombol **Reply / Balas** pada pesan sumber. Balasan Telegram membantu peserta dan bot mengenali hubungan antarpendapat.

Kontribusi yang membantu antara lain pertanyaan yang memperjelas masalah, alasan, sumber yang dapat diperiksa, pengalaman yang relevan, kritik terhadap gagasan, sintesis, dan rencana tindakan.

Hindari menambah kata kunci hanya untuk mengejar indikator bot. Tulis dengan wajar, relevan, dan bertanggung jawab.

### 4.3 Baca ringkasan

```text
/ringkasan
```

Ringkasan saat ini berupa cuplikan hingga 12 pesan terakhir, dilengkapi pseudonim dan ID bukti. Kutipan dapat terpotong. Baca pesan asli sebelum menilai pendapat atau mengambil keputusan.

Secara default, analisis berkala sekitar 10 menit dan ringkasan sekitar 20 menit. Operator dapat mengubah interval. Ringkasan tidak selalu dikirim bila data tidak berubah; ringkasan awal juga dapat muncul lebih cepat setelah data tersedia.

### 4.4 Kenali pesan yang dapat diamati

Pengamatan membutuhkan akun terdaftar, persetujuan aktif, grup yang dikonfigurasi, akses bot terhadap pesan, dan pengamatan yang tidak dijeda. Teks dan caption dapat dicatat. Isi suara, video, gambar, dan lampiran tidak dianalisis; sertakan uraian tertulis jika bukti Anda berupa media.

Jangan menganggap pesan lama sebelum persetujuan akan diambil ulang. Percakapan pribadi biasa dengan bot tidak menjadi arsip diskusi kelas. Pencatatan grup dapat berlangsung meskipun sesi laboratorium belum dibuka; sesi menentukan periode evaluasi.

## 5. Membuat usulan dan mengintegrasikan gagasan

### 5.1 Daftarkan usulan formal

```text
/usulan Aplikasi harus menampilkan pesan sumber untuk setiap ringkasan diskusi.
```

Bot memberikan nomor usulan, misalnya **U3**. Untuk melihat usulan terbaru:

```text
/usulan
```

Menyimpan usulan tidak berarti kelas menyetujuinya. Fasilitator perlu membuka putaran konfirmasi ketika usulan siap dibahas sebagai calon keputusan. Teks usulan maksimal 2.000 karakter.

### 5.2 Hubungkan gagasan dengan sumber yang jelas

Jika dua peserta menyampaikan gagasan yang dapat digabungkan, tulis integrasi dengan ID pesan yang ditampilkan bot:

```text
/integrasi M12,M18 Gabungkan ringkasan berbukti dengan daftar pertanyaan terbuka agar fasilitator dapat memeriksa konteks dan menindaklanjuti hal yang belum selesai.
```

Syarat integrasi:

- Memakai 2 sampai 8 ID pesan yang berbeda.
- Sumber berasal dari sedikitnya dua penulis berbeda dan berada di forum yang sama.
- Pesan sumber tersedia pada arsip bot.
- Teks integrasi maksimal 2.000 karakter.

Lihat integrasi yang masih memiliki sumber valid:

```text
/integrasi
```

Bot memberi nomor integrasi seperti **G2**. Integrasi adalah sintesis yang diajukan peserta, bukan konsensus otomatis. Jika sumber diedit atau dihapus, integrasi lama dapat tidak lagi dianggap valid; baca sumber terbaru dan kirim integrasi baru bila perlu.

### 5.3 Pahami jenis nomor

| Awalan | Arti | Cara memakai |
|---|---|---|
| M | Pesan/bukti dalam arsip bot | `/bukti 12` untuk M12 milik sendiri; daftar integrasi boleh `M12,M18`. |
| U | Usulan formal | Fasilitator memakai `/sepakat 3` untuk U3. |
| R | Putaran konfirmasi | Peserta memakai `/sikap 4 setuju` untuk R4. |
| G | Integrasi gagasan | Ditampilkan pada daftar integrasi; bukan nomor putaran. |
| I | Saran intervensi | Fasilitator memakai `/terapkan 2` untuk I2. |
| S | Sesi laboratorium | Menentukan periode evaluasi; bot memakai sesi terbaru pada forum terpilih. |
| C | Project Charter | Dokumen berversi; persetujuan dokumen khusus dosen. |

Kecuali daftar sumber `/integrasi`, gunakan **angkanya saja** pada argumen numerik. M12 bukan nomor urut pesan yang Anda hitung sendiri di Telegram. Ambil ID dari keluaran bot, refleksi, atau explorer dashboard yang tersedia.

## 6. Menyatakan sikap dan membangun konsensus

### 6.1 Tunggu putaran dibuka

Fasilitator membuka putaran untuk usulan tertentu. Contoh: U3 dibuka sebagai R4. Baca teks usulan dan alasan peserta lain sebelum memilih sikap.

Lihat statusnya:

```text
/konsensus 4
```

### 6.2 Pilih satu sikap yang mencerminkan pendapat Anda

Jika setuju:

```text
/sikap 4 setuju
```

Jika belum dapat mengambil posisi:

```text
/sikap 4 abstain Saya belum sempat memeriksa contoh data yang menjadi dasar usulan.
```

Jika memiliki keberatan:

```text
/sikap 4 keberatan Perlu aturan agar ringkasan tidak menampilkan asesmen pribadi mahasiswa lain.
```

Alasan wajib untuk abstain dan keberatan, maksimal 2.000 karakter. Nyatakan alasan substantif dan hindari data sensitif. Alasan keberatan formal dapat dibaca melalui:

```text
/keberatan
```

### 6.3 Perbarui sikap setelah berdiskusi

Selama putaran masih `open`, Anda dapat mengirim `/sikap` lagi untuk memperbarui posisi sendiri. Riwayat perubahan disimpan. Jika keberatan sudah terjawab dan Anda benar-benar setuju, nyatakan sendiri:

```text
/sikap 4 setuju
```

Fasilitator tidak dapat mengganti sikap Anda. Jangan menyatakan setuju hanya untuk mempercepat penutupan bila masih ada keberatan yang belum terjawab.

### 6.4 Bagaimana kesepakatan ditetapkan

Metode saat ini memerlukan **semua peserta pada daftar awal putaran menyatakan setuju**, lalu fasilitator menjalankan konfirmasi. Diam bukan persetujuan; abstain juga belum memenuhi metode ini.

| Status | Makna bagi peserta |
|---|---|
| `open` | Putaran masih terbuka; sikap dapat diperbarui. Semua setuju belum otomatis mengubah status. |
| `confirmed` | Fasilitator sudah mengonfirmasi setelah semua peserta menyatakan setuju. |
| `superseded` | Putaran telah digantikan atau tidak lagi menjadi dasar konfirmasi aktif. Jangan mengirim sikap baru ke putaran ini. |

Jika putaran sudah dikonfirmasi tetapi ada informasi baru, hubungi fasilitator untuk membuka putaran baru. Sikap lama tidak otomatis dibawa ke putaran baru. Jika teks usulan berubah, buat usulan baru agar orang tidak dianggap menyetujui teks yang berbeda.

Daftar awal putaran berasal dari data peserta kelas, bukan semata daftar orang yang sedang online. Jika identitas atau daftar peserta berubah, fasilitator mungkin perlu membuka putaran baru.

## 7. Mengambil giliran fasilitator

### 7.1 Minta giliran

Di grup forum yang ingin Anda fasilitasi:

```text
/request_fasilitator
```

Bentuk singkat `/request` juga tersedia. Jika belum ada fasilitator mahasiswa aktif, Anda langsung mendapat giliran. Jika sudah ada, Anda masuk antrean sesuai urutan permintaan.

Lihat posisi dan fasilitator aktif:

```text
/antrian_fasilitator
```

### 7.2 Batalkan jika masih menunggu

```text
/unrequest_fasilitator
```

Bentuk singkatnya `/unrequest`. Ini membatalkan permintaan sendiri yang masih menunggu, bukan mengakhiri giliran aktif. Meminta giliran kembali setelah membatalkan menempatkan Anda di urutan terakhir.

### 7.3 Lepaskan peran setelah tugas selesai

```text
/selesai_fasilitator
```

Giliran berpindah otomatis kepada peserta berikutnya. Jika antrean kosong, tidak ada fasilitator mahasiswa aktif sampai peserta berikutnya meminta giliran. Antrean tersimpan meskipun bot restart dan terpisah untuk setiap forum.

Gunakan perintah di grup agar pergantian terlihat oleh kelas. Tidak ada DM tambahan otomatis untuk mengumumkan pergantian; peserta dapat memeriksa antrean. Permintaan berulang tidak menaikkan posisi atau membuat giliran ganda.

## 8. Tugas mahasiswa saat menjadi fasilitator

Peran fasilitator berarti membantu orang berpikir bersama, bukan mengambil alih percakapan atau menentukan persetujuan orang lain. Bacalah tujuan, rangkum dengan adil, undang perspektif yang belum terwakili, dan kembalikan keputusan kepada peserta.

### 8.1 Kelola sesi dan perhatian kelas

Dengan koordinasi dosen, mulai sesi laboratorium bila belum ada:

```text
/sesi mulai Penyusunan spesifikasi proyek UAS
```

Lihat keadaan sesi dan fase:

```text
/sesi
/fase
```

Fasilitator dapat memilih fase TAIDA, misalnya `/fase Interest`. Fase dapat dikembalikan jika muncul informasi atau keberatan baru. Jangan membuka sesi baru jika masih ada sesi aktif.

### 8.2 Minta analisis, lalu baca dengan kritis

```text
/analisis
/laporan
```

Hasil menunjukkan indikator berbasis data yang tersedia. Lebih sedikit pesan belum tentu berarti peserta tidak berpikir atau tidak berkontribusi melalui cara lain. Untuk informasi yang tidak perlu diumumkan kepada kelas, baca laporan lewat chat pribadi.

### 8.3 Kelola saran intervensi di chat pribadi

Buka chat pribadi bot. Jika perlu, pilih forum dengan `/forum ID_GRUP`, kemudian:

```text
/intervensi
```

Jika bot memberi saran I2, pilih tindakan berikut:

```text
/terapkan 2
/terapkan 2 Mari dengarkan dahulu alasan dari dua perspektif sebelum membandingkan alternatif.
/alternatif 2
/abaikan 2
```

Pilih salah satu sesuai kebutuhan, bukan menyalin semua baris sekaligus. `/terapkan` menyetujui saran untuk dikirim ke grup; tambahan teks mengganti pertanyaan yang diusulkan. `/alternatif` meminta rumusan lain, sedangkan `/abaikan` menolak atau membatalkan saran yang belum diposting.

Saran baru dapat dikirim ke chat pribadi fasilitator saat analisis berjalan. Jika Anda belum pernah membuka chat bot, buka dan tekan Start. Bot tidak memaksakan saran ke grup tanpa persetujuan fasilitator. Saran yang buktinya berubah atau tidak lagi relevan dapat menjadi tidak tersedia.

### 8.4 Buka dan konfirmasi calon keputusan

```text
/sepakat 3
```

Perintah tersebut membuka putaran untuk U3, bukan menyatakan bahwa kelas sudah sepakat. Setelah semua peserta menyatakan setuju pada R4, periksa lalu konfirmasikan:

```text
/konsensus 4
/konfirmasi 4
```

Jika perlu konfirmasi ulang untuk usulan yang sama:

```text
/bukaulang 4
```

Perintah ini menghasilkan nomor putaran baru dan semua peserta perlu mengisi sikap lagi. Jangan menebak nomor baru; baca balasan bot.

### 8.5 Jeda, tutup sesi, dan akhiri giliran dengan tepat

Jika perlu menghentikan sementara pengamatan kelas:

```text
/pause
```

Lanjutkan dengan `/resume`. Pesan selama jeda tidak diambil ulang. Gunakan jeda dengan koordinasi peserta dan dosen karena berlaku pada forum tersebut, bukan hanya akun Anda.

Jika kegiatan evaluasi memang berakhir:

```text
/sesi selesai
```

Ini menutup periode evaluasi dan menyimpan snapshot akhir; tidak otomatis menghentikan pencatatan grup. Setelah tugas memfasilitasi selesai:

```text
/selesai_fasilitator
```

**Pergantian fasilitator bukan penutupan sesi.** Jangan menutup sesi jika kelas masih melanjutkan kegiatan yang sama dengan fasilitator berikutnya.

Fasilitator mahasiswa tidak memperoleh hak admin Telegram, tidak boleh melihat asesmen pribadi peserta lain melalui peran giliran, dan tidak dapat memberi koreksi akademik atau menyetujui dokumen sebagai dosen.

## 9. Mengikuti sesi TAIDA dan survei

TAIDA membantu kelas menata perhatian dan tindakan:

| Fase | Pertanyaan panduan |
|---|---|
| Target | Apa tujuan dan indikator keberhasilan kita? |
| Attention | Kenyataan atau masalah apa yang perlu diperhatikan? |
| Interest | Perspektif, kebutuhan, dan pengetahuan siapa yang perlu dipahami? |
| Desire | Komitmen apa yang ingin dibangun bersama? |
| Action | Apa keputusan dan tindakan nyata berikutnya? |

Survei sukarela dilakukan di chat pribadi saat dosen/fasilitator telah membuka sesi. Urutan empat angka adalah **trust, rasa didengar, rasa aman menyampaikan pendapat, dan kesediaan bekerja sama**, masing-masing 1 sampai 5.

Contoh pra kegiatan:

```text
/survei pra 3,4,3,4
```

Contoh pasca kegiatan:

```text
/survei pasca 4,4,4,5
```

Gunakan penilaian yang jujur, bukan angka yang dianggap menyenangkan dosen. Angka contoh bukan jawaban yang disarankan. Respons berikutnya pada tahap yang sama memperbarui respons Anda pada sesi tersebut.

Agregat baru ditampilkan setelah sedikitnya 5 responden. Perubahan pra-pasca memakai sedikitnya 5 pasangan peserta yang sama. Survei ini merupakan persepsi diri yang eksploratif, bukan tes psikologis tervalidasi atau nilai mata kuliah.

## 10. Membaca refleksi dan meminta tinjauan

### 10.1 Lihat bukti sendiri

Di chat pribadi:

```text
/refleksi
```

`/profil` tersedia sebagai alternatif untuk keluaran yang sama. Bot menampilkan kontribusi, kategori, indikator yang teramati, serta saran perbaikan.

Untuk memeriksa M12 milik Anda:

```text
/bukti 12
```

Bila kode sumber teknis/JSON ditampilkan, fokus pada teks bukti, kategori kontribusi, penjelasan, dan saran. Anda tidak perlu mengubah JSON. Mahasiswa biasa hanya dapat meminta bukti milik sendiri melalui perintah ini.

### 10.2 Pahami rubrik tanpa mengejar kata kunci

```text
/rubrik
```

Enam dimensi adalah relevansi terhadap tujuan, kontribusi pengetahuan, empati/penghargaan, integrasi pengetahuan, fasilitasi/inklusi, dan orientasi keputusan/tindakan.

Pada versi aturan lokal saat ini, penanda awal dapat menghasilkan skor 2/4 dengan keyakinan rendah. Dimensi yang belum terlihat dapat bernilai `null` atau `not_observed`; itu **bukan otomatis nilai nol atau kinerja buruk**. Bot tidak menghitung nilai akademik resmi dari rata-rata pesan.

Tidak semua pesan perlu menunjukkan keenam dimensi. Pertanyaan singkat yang tepat dapat membantu diskusi tanpa memuat seluruh unsur rubrik sekaligus.

### 10.3 Minta dosen meninjau jika perlu

```text
/tinjau 12 Mohon periksa konteks balasan saya; pesan ini menggabungkan kebutuhan dari dua usulan sebelumnya.
```

Gunakan ID bukti milik sendiri dan alasan yang jelas. Catatan tersimpan untuk tinjauan dosen. Permintaan belum otomatis mengubah penilaian dan belum mengirim notifikasi khusus kepada dosen; beri tahu dosen lewat prosedur kelas jika perlu tindak lanjut segera. Penilaian akademik final tetap menjadi tanggung jawab dosen.

## 11. Memahami indikator CI dan modal sosial

Perintah yang dapat dibaca peserta:

```text
/partisipasi
/konflik
/modal_sosial
/perkembangan
```

- `/partisipasi` menunjukkan indikator volume dan pemerataan kontribusi, bukan peringkat kemampuan.
- `/konflik` menunjukkan penanda perbedaan pendapat beserta bukti. Kata seperti “namun” dapat ikut terdeteksi; ini bukan diagnosis konflik pribadi atau emosi.
- `/modal_sosial` menunjukkan relasi balasan yang teramati: dalam kelompok (bonding), lintas kelompok (bridging), mahasiswa-staf (linking), dan timbal balik.
- `/perkembangan` menunjukkan indeks proses eksploratif, cakupan komponen, serta snapshot sesi yang tersedia.

Bonding/bridging memerlukan pemetaan kelompok oleh dosen. Data tidak tersedia tidak sama dengan nol. Trust psikologis tidak disimpulkan langsung dari jaringan balasan.

Indikator fasilitasi versi 2 memakai hingga 200 pesan forum terakhir, sedangkan evaluasi laboratorium memakai periode sesi. Angkanya dapat berbeda karena ruang lingkupnya berbeda.

**Indeks CI belum tervalidasi sebagai ukuran ilmiah dan bukan nilai akademik.** Perubahan indeks tidak membuktikan bahwa satu intervensi menyebabkan peningkatan kualitas kelas. Jangan menambah pesan berulang untuk menaikkan angka.

## 12. Menggunakan dashboard dan Project Charter UAS

### 12.1 Dashboard

Jika dosen menyediakan dashboard kelas, buka alamat yang dibagikan dosen dan login dengan akun institusi yang telah dipetakan. Anda tidak perlu menginstal Python atau menjalankan server sendiri.

Perintah `/dashboard` saat ini menampilkan petunjuk teknis menjalankan aplikasi, **bukan otomatis tautan dashboard kelas yang sudah dipublikasikan**. Mintalah alamat layanan kelas kepada dosen/operator.

Halaman yang relevan untuk mahasiswa mencakup ikhtisar, perkembangan CI, penjelajah percakapan, refleksi dan survei, serta Project Charter. Akses halaman tambahan mengikuti peran. Asesmen pribadi peserta lain tidak tersedia bagi mahasiswa melalui dashboard.

Jika layar bertuliskan **DEMO SINTETIK**, itu data contoh, bukan data percakapan dan nilai Anda. Pilihan peran pada demo tidak memberi hak atas data kelas yang nyata.

### 12.2 Project Charter UAS

```text
/charter
```

Charter menyatukan tujuan dan kebutuhan proyek dengan rujukan keputusan yang telah dikonfirmasi. Bagian editorial, seperti kriteria penerimaan dan rencana pekerjaan, dapat masih berupa rancangan dan diberi label tersendiri.

Jika sedang menjadi fasilitator dan sesi memiliki keputusan dikonfirmasi:

```text
/charter buat Aplikasi AI Fasilitator Collective Intelligence
```

Lengkapi draf bersama kelas melalui dashboard bila akses tersedia. Setiap penyimpanan membuat versi baru. Persetujuan dokumen sebagai dosen dilakukan oleh dosen, bukan fasilitator mahasiswa.

Status dokumen `draft` berarti rancangan, `approved` berarti persetujuan dokumen oleh dosen tercatat, dan `stale` berarti sumber konsensus tidak lagi valid. Dokumen stale tidak boleh dianggap sebagai keputusan aktif. Ekspor saat ini berupa Markdown.

Persetujuan dokumen oleh dosen tidak otomatis menjadikan seluruh tambahan editorial sebagai konsensus kelas. Kebutuhan baru yang hendak dinyatakan sebagai keputusan bersama tetap perlu dibahas dan dikonfirmasi.

## 13. Persetujuan, privasi, dan penghapusan data

### 13.1 Data yang dicatat

Untuk pesan yang memenuhi syarat pengamatan, bot dapat menyimpan teks/caption, identitas peserta yang terhubung, waktu, ID pesan, relasi balasan, topik Telegram, dan edit pesan yang diterima. Bot juga menyimpan kontribusi formal, sikap, antrean fasilitator, serta data laboratorium sesuai fitur yang Anda gunakan.

Ringkasan publik memakai pseudonim, tetapi isi pesan masih mungkin dikenali. Jangan mengirim kata sandi, token, OTP, data identitas sensitif, atau informasi pribadi orang lain yang tidak perlu untuk pembelajaran.

### 13.2 Tarik persetujuan

Di chat pribadi:

```text
/tarik
```

Ini menghentikan pencatatan berikutnya yang mensyaratkan persetujuan. Data yang sudah tersimpan tidak otomatis dihapus. Anda tidak otomatis keluar dari grup; keluarlah melalui Telegram bila memang ingin meninggalkan grup.

Jika kemudian bersedia kembali, baca pengantar dan gunakan `/setuju`. Pesan yang dikirim saat persetujuan tidak aktif tidak diambil ulang.

### 13.3 Hapus data melalui bot

```text
/hapusdata
```

Perintah ini menarik persetujuan dan menghapus data pengamatan serta data turunan terkait sesuai implementasi, termasuk bukti/asesmen, usulan atau integrasi milik sendiri, sikap, survei, dan riwayat antrean. Jika Anda sedang memfasilitasi, peran giliran dilepas dan peserta berikutnya dapat dipromosikan.

Penghapusan dapat membuat putaran keputusan atau charter yang kehilangan bukti tidak lagi berlaku, dan snapshot turunan dapat ikut dihapus. Bicarakan dampak pada dokumentasi kelas dengan dosen bila diperlukan.

Perintah ini **tidak** menghapus identitas dasar Anda dari daftar peserta kelas, tidak menghapus pesan asli Telegram, tidak menghapus kutipan yang ditulis orang lain, dan tidak menghapus berkas yang sudah diunduh atau backup operator secara otomatis. Terdapat pula catatan kontrol/operasional yang mengikuti kebijakan retensi; jangan menafsirkan perintah ini sebagai penghapusan setiap jejak di semua sistem.

Menghapus pesan di Telegram tidak otomatis menghapus salinan lokal bot. Jika perlu penghapusan tertentu yang belum tercakup, hubungi dosen/operator. Retensi default data operasional tertentu adalah 90 hari, tetapi kebijakan kelas dapat dikonfigurasi berbeda.

## 14. Contoh satu alur kegiatan kelas

Nomor berikut hanya ilustrasi. Dalam praktik, ikuti nomor dari balasan bot.

**Sebelum kegiatan, chat pribadi:**

```text
/start
/setuju
```

Tekan tautan dan pilih Minta Bergabung.

**Di grup:**

```text
/tujuan
/request_fasilitator
/antrian_fasilitator
```

Jika mendapat giliran, koordinasikan sesi dengan dosen:

```text
/sesi mulai Spesifikasi aplikasi AI fasilitator
/fase Attention
```

Peserta berdiskusi dengan pesan biasa dan Reply, kemudian mencatat usulan:

```text
/usulan Ringkasan harus mencantumkan pesan sumber agar konteks dapat diperiksa.
```

Jika bot memberikan U3, fasilitator menjalankan `/sepakat 3`. Misalnya bot membuka R4, peserta mengirim:

```text
/sikap 4 setuju
```

Peserta yang keberatan memberikan alasan; kelas mendiskusikan dan peserta dapat memperbarui sikap sendiri. Setelah semua benar-benar setuju, fasilitator menjalankan:

```text
/konsensus 4
/konfirmasi 4
```

Di akhir kegiatan, lakukan survei dan refleksi di chat pribadi:

```text
/survei pasca 4,4,3,4
/refleksi
```

Jika sesi memang berakhir, fasilitator menutup sesi, kemudian melepas peran:

```text
/sesi selesai
/selesai_fasilitator
```

Jika hanya berganti fasilitator dan sesi masih berlanjut, cukup `/selesai_fasilitator` tanpa menutup sesi.

## 15. Daftar perintah peserta dan fasilitator

### 15.1 Perintah seluruh peserta

| Perintah | Tempat yang disarankan | Fungsi |
|---|---|---|
| `/start`, `/help`, `/bantuan` | Pribadi | Pengantar dan daftar perintah. |
| `/setuju` | Pribadi, wajib | Persetujuan penggunaan data dan pengiriman tautan bergabung. |
| `/gabung` | Pribadi, wajib | Meminta kembali tautan bergabung. |
| `/forum ID_GRUP` | Pribadi, wajib | Memilih forum untuk perintah pribadi. |
| `/tujuan`, `/status` | Grup | Membaca misi dan kondisi pengamatan. |
| `/ringkasan` | Grup | Cuplikan pesan terbaru. |
| `/usulan [TEKS]` | Grup | Melihat atau membuat usulan formal. |
| `/integrasi [M1,M2 TEKS]` | Grup | Melihat atau mencatat integrasi bersumber. |
| `/sikap ID setuju` | Grup | Mengonfirmasi sikap sendiri pada putaran terbuka. |
| `/sikap ID abstain ALASAN` | Grup | Menyatakan abstain dengan alasan. |
| `/sikap ID keberatan ALASAN` | Grup | Menyatakan keberatan dengan alasan. |
| `/konsensus [ID]`, `/keberatan` | Grup | Memeriksa status putaran dan keberatan formal. |
| `/request_fasilitator`, `/request` | Grup | Meminta giliran fasilitator. |
| `/unrequest_fasilitator`, `/unrequest` | Grup | Membatalkan permintaan yang masih menunggu. |
| `/antrian_fasilitator` | Grup | Melihat giliran dan antrean. |
| `/refleksi`, `/profil` | Pribadi, wajib | Membaca bukti dan umpan balik sendiri. |
| `/bukti ID` | Pribadi, wajib | Melihat rincian bukti milik sendiri. |
| `/tinjau ID ALASAN` | Pribadi, wajib | Meminta tinjauan dosen terhadap bukti sendiri. |
| `/rubrik` | Pribadi atau grup | Membaca dimensi dan batasan rubrik. |
| `/partisipasi`, `/konflik` | Grup | Membaca indikator kolektif berbukti. |
| `/sesi`, `/fase` | Grup | Melihat sesi terbaru dan fase TAIDA. |
| `/survei pra ANGKA,ANGKA,ANGKA,ANGKA` | Pribadi, wajib | Survei diri pra kegiatan; ganti ANGKA dengan 1-5. |
| `/survei pasca ANGKA,ANGKA,ANGKA,ANGKA` | Pribadi, wajib | Survei diri pasca kegiatan. |
| `/modal_sosial`, `/perkembangan` | Grup | Membaca indikator sesi laboratorium. |
| `/charter` | Grup | Membaca Project Charter terbaru. |
| `/dashboard` | Pribadi | Petunjuk dashboard; minta URL kelas kepada dosen. |
| `/tarik`, `/hapusdata` | Pribadi, wajib | Menarik persetujuan atau meminta penghapusan sesuai cakupan fitur. |

Tanda kurung siku pada tabel berarti bagian opsional; jangan ketik tanda kurungnya. Istilah ID pada `/sikap` adalah nomor putaran R, sedangkan ID pada `/bukti` dan `/tinjau` adalah nomor pesan M.

### 15.2 Tambahan saat menjadi fasilitator aktif

| Perintah | Tempat | Fungsi |
|---|---|---|
| `/analisis`, `/laporan` | Grup atau pribadi | Memicu analisis dan membaca laporan. |
| `/intervensi` | Pribadi, wajib | Membaca saran yang belum diputuskan. |
| `/terapkan ID [TEKS]` | Pribadi, wajib | Menyetujui saran, dengan suntingan opsional. |
| `/alternatif ID`, `/abaikan ID` | Pribadi, wajib | Meminta rumusan lain atau membatalkan saran. |
| `/sepakat ID_USULAN` | Grup | Membuka putaran konfirmasi untuk usulan U. |
| `/konfirmasi ID_PUTARAN` | Grup | Mengesahkan hasil setelah semua peserta setuju. |
| `/bukaulang ID_PUTARAN` | Grup | Memulai putaran baru untuk usulan yang sama. |
| `/sesi mulai JUDUL` | Grup | Memulai sesi setelah koordinasi kelas. |
| `/fase NAMA` | Grup | Mengubah fase TAIDA pada sesi aktif. |
| `/sesi selesai` | Grup | Menutup periode evaluasi, bukan menutup grup. |
| `/pause`, `/resume` | Grup atau pribadi | Menjeda/melanjutkan pengamatan dan analisis forum. |
| `/charter buat JUDUL` | Grup atau pribadi | Membuat draf dari keputusan yang dikonfirmasi. |
| `/selesai_fasilitator` | Grup | Melepaskan peran giliran dan melanjutkan antrean. |

Perintah koreksi asesmen `/koreksi`, daftar tinjauan `/tinjauan`, persetujuan dokumen `/charter setujui`, dan pengaturan tertentu pada dashboard adalah kewenangan dosen. Hak konfigurasi staf yang ditetapkan dosen terpisah dari peran giliran mahasiswa.

Perintah lama seperti `/topik`, `/ide`, `/tanya`, `/balas`, `/sintesis`, `/baca`, dan `/ringkas` bukan alur aktif bot versi ini. Gunakan pesan biasa dan Reply, `/usulan`, `/integrasi`, serta `/ringkasan`.

## 16. Pemecahan masalah dan daftar periksa

| Masalah | Yang dapat Anda lakukan |
|---|---|
| Akun belum terhubung | Pastikan akun Telegram sama dengan akun terdaftar. Hubungi dosen atau ikuti registrasi bot lama sesuai instruksi dosen. |
| Setelah `/setuju` belum masuk grup | Buka tautan, tekan Minta Bergabung, dan tunggu persetujuan. Gunakan `/gabung` bila tautan tidak muncul. |
| Tautan belum tersedia atau permintaan belum disetujui | Minta operator memeriksa konfigurasi grup, izin admin bot, dan apakah bot sedang berjalan. Persetujuan Anda dapat tetap tersimpan. |
| Bot menyebut akses akun dibatasi | Hubungi dosen/admin grup. Jangan mencoba mengakali pembatasan dengan akun lain. |
| Bot meminta memilih forum | Kirim `/forum ID_GRUP` di chat pribadi, menggunakan ID yang benar dari dosen. |
| Pesan belum muncul dalam analisis | Periksa persetujuan, forum, dan status jeda. Tunggu interval analisis atau minta fasilitator memicu `/analisis`. Pesan sebelum persetujuan tidak diambil ulang. |
| Grup sepi dari respons bot | Bot tidak menjawab setiap pesan biasa. Coba `/help`; pastikan koneksi dan hubungi fasilitator bila tetap tidak ada respons. |
| Perintah ditolak karena peran | Anda belum menjadi fasilitator aktif atau tindakan khusus dosen. Periksa `/antrian_fasilitator`. |
| `/unrequest` tidak melepas tugas | Jika sudah aktif, gunakan `/selesai_fasilitator`; `/unrequest` hanya membatalkan antrean. |
| ID pesan/usulan/putaran tidak ditemukan | Periksa forum dan jenis ID. Gunakan nomor dari balasan bot, bukan nomor yang diperkirakan. |
| Sumber integrasi tidak valid | Pastikan 2-8 pesan tersedia pada forum yang sama dan sedikitnya dua penulis. Sumber yang berubah perlu ditinjau ulang. |
| Tidak dapat mengirim sikap | Pastikan persetujuan aktif, nomor putaran benar, identitas cocok dengan daftar awal putaran, dan statusnya masih `open`. |
| Konsensus belum dikonfirmasi | Masih ada peserta belum merespons, abstain, atau keberatan; atau fasilitator belum menjalankan `/konfirmasi`. |
| Belum ada sesi atau charter | Minta fasilitator membuka sesi. Charter memerlukan keputusan yang telah dikonfirmasi pada sesi tersebut. |
| Skor atau kategori terasa tidak tepat | Baca bukti dan konteks melalui chat pribadi; kirim `/tinjau ID ALASAN`. Indikator aturan lokal bisa keliru. |
| Dashboard tidak bisa dibuka | Minta URL kelas dan pemetaan akun login kepada dosen/operator. Pesan `/dashboard` belum otomatis memberikan URL publik. |
| Angka pada dashboard berbeda dari `/status` | Bandingkan forum, sesi, periode data, jendela indikator, dan apakah dashboard yang dibuka adalah demo sintetik. |

### Daftar periksa peserta

- [ ] Saya memakai akun Telegram yang benar dan telah membaca pengantar penggunaan data.
- [ ] Saya telah mengambil keputusan persetujuan secara sadar; bila bersedia, saya mengirim `/setuju` di chat pribadi.
- [ ] Saya telah menekan tautan dan benar-benar bergabung ke grup yang benar.
- [ ] Saya membaca tujuan dan menggunakan Reply untuk menjaga konteks.
- [ ] Saya menyampaikan alasan/bukti yang relevan tanpa mengejar jumlah pesan atau kata kunci.
- [ ] Saya mengisi sikap pada putaran yang benar dan menyampaikan keberatan secara konstruktif.
- [ ] Saya menggunakan refleksi sebagai bantuan belajar, bukan menganggapnya nilai akhir.
- [ ] Jika menjadi fasilitator, saya memberi ruang peserta lain dan melepaskan giliran saat selesai.
- [ ] Saya tidak membagikan rahasia atau data pribadi yang tidak diperlukan.

**Jika tetap mengalami kendala**, sampaikan kepada dosen/fasilitator: perintah yang dikirim, forum yang dimaksud, waktu kejadian, dan pesan kesalahan. Hindari meneruskan token, OTP, kata sandi, atau asesmen pribadi peserta lain.

---

Panduan ini mengikuti fungsi KIPP-CI v3 yang tersedia pada kode proyek saat edisi disusun. Nama akun bot dan alamat grup/dashboard yang berlaku tetap mengikuti pengumuman dosen. Contoh ID dan percakapan bersifat ilustratif, bukan data peserta nyata.
