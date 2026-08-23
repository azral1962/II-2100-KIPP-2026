# Student Course Services II2100

Bot Telegram untuk interaksi mahasiswa yang terdaftar dengan instruktur.

Dokumentasi Quarto tersedia di [`KIPP-2026/user-guide.qmd`](KIPP-2026/user-guide.qmd)
untuk mahasiswa dan [`KIPP-2026/technical-reference.qmd`](KIPP-2026/technical-reference.qmd)
untuk operator/pengembang. Render dengan `quarto render KIPP-2026 --to html`.

## Fitur saat ini

- `/start` menampilkan petunjuk registrasi.
- `/reg NIM` memvalidasi NIM terhadap `peserta.csv`, mengambil Telegram user ID
  dari pengirim, dan menyimpannya ke kolom `ID`.
- `/repo URL` memvalidasi URL repo GitHub beserta `README.md`, lalu menyimpan
  atau mengganti kolom `repo` milik Telegram ID yang sudah terdaftar.
- `/status` menampilkan status registrasi dan memeriksa apakah kolom `repo`
  berisi URL repo GitHub yang valid.
- `/skor AXX` mengambil nilai `A01` sampai `A15` dari `assessment.csv`. Nilai
  kosong meminta mahasiswa mengerjakan tugas, nilai di bawah `3.0` berstatus
  `revisi`, dan nilai minimal `3.0` berstatus `tercapai`.
- `/submit WXX` memeriksa halaman portfolio `W01` sampai `W15` pada GitHub
  Pages. Halaman yang valid dimasukkan ke `antrian.csv` dengan tiket berurutan
  dan status `ANTRI`. Submission aktif untuk mahasiswa dan minggu yang sama
  memakai kembali tiket lama agar tidak duplikat.
- `/antrian` menampilkan lima submission terbaru beserta statusnya.
- `/hasil WXX` menampilkan total rubrik, ringkasan, dan prioritas perbaikan dari
  hasil assessment terbaru untuk minggu tersebut.
- `/llm TICKET` menampilkan hasil LLM untuk nomor tiket tertentu. Bot hanya
  menampilkan tiket yang dimiliki mahasiswa yang sedang login.
- Registrasi tidak dapat mengambil alih NIM yang sudah terhubung atau memakai
  satu akun Telegram untuk dua NIM.

Repo dinyatakan valid hanya jika URL memakai format
`https://github.com/pemilik/repo`, repo dapat dibaca melalui GitHub, dan baris
pertama `README.md` pada branch default tepat seperti berikut:

```markdown
# Portfolio Mahasiswa KIPP-2026
```

## Menjalankan bot

Proyek ini hanya membutuhkan Python 3.10 atau yang lebih baru dan tidak memakai
dependensi eksternal.

Masukkan token dari BotFather ke file `.env`:

```dotenv
TELEGRAM_BOT_TOKEN_KIPP=token-dari-BotFather

# Opsional untuk repo privat atau batas API GitHub yang lebih tinggi
GITHUB_TOKEN=token-github
```

File `.env` sudah diabaikan oleh Git agar token tidak ikut ter-commit. Setelah
token diisi, jalankan:

```powershell
python app.py
```

Secara default bot membaca `peserta.csv`. Lokasi file dan durasi long polling
juga dapat ditambahkan ke `.env`:

```dotenv
PESERTA_CSV=C:\path\ke\peserta.csv
ASSESSMENT_CSV=C:\path\ke\assessment.csv
ANTRIAN_CSV=C:\path\ke\antrian.csv
TELEGRAM_POLL_TIMEOUT=30
TELEGRAM_OFFSET_FILE=telegram-offset.txt
```

Offset update Telegram disimpan secara atomik sehingga restart bot tidak
mengulang update yang sudah selesai. Semua path relatif dibaca dari folder
proyek, bukan dari current working directory terminal.

Jangan simpan token bot di source code atau commit Git.

Tekan `Ctrl+C` pada terminal untuk menghentikan bot dengan aman.

## Menjalankan worker assessment LLM

`llm.py` membaca setiap baris `antrian.csv` yang berstatus `ANTRI`, mengambil
teks halaman portfolio dari kolom `url`, memilih prompt minggu yang sesuai dari
`llm-assessment-prompts.md`, lalu mengirim assessment ke endpoint chat
completions milik llama.cpp. Konfigurasi default mengarah ke
`http://100.110.236.59:8088`.

Tambahkan konfigurasi berikut ke `.env` bila perlu:

```dotenv
LLM_SERVER_URL=http://100.110.236.59:8088

# Opsional; bila kosong, worker mengambil ID pertama dari GET /v1/models
LLM_MODEL=
LLM_REQUEST_TIMEOUT=300
LLM_ENABLE_THINKING=false
LLM_QUEUE_POLL_SECONDS=10
LLM_LEASE_SECONDS=900
LLM_INPUT_DIR=assessment-inputs
LLM_REPORT_DIR=assessment-results

# Aman sebagai default: nilai resmi menunggu persetujuan dosen
LLM_AUTO_APPROVE=false
```

`LLM_ENABLE_THINKING=false` direkomendasikan untuk assessment terstruktur.
Model reasoning seperti Qwen dapat memakai seluruh `LLM_MAX_TOKENS` untuk
`reasoning_content` dan berhenti sebelum menghasilkan jawaban final. Thinking
dapat diaktifkan kembali dengan nilai `true` bila token output dinaikkan.

Jalankan worker terus-menerus pada terminal terpisah:

```powershell
python llm.py
```

Untuk memproses snapshot antrian satu kali, misalnya dari scheduler:

```powershell
python llm.py --once
```

Untuk menguji koneksi dan respons model tanpa membaca atau mengubah
`antrian.csv`:

```powershell
python llm.py --test
```

Prompt tes bawaan meminta model menjawab `LLAMA_CPP_OK`. Prompt lain dapat
diberikan langsung:

```powershell
python llm.py --test "Jelaskan 2 + 2 dalam satu kalimat"
```

Sebelum memanggil llama.cpp, worker membuat dua file TXT untuk setiap tiket di
`assessment-inputs/`: `tiket-<nomor>-<minggu>-prompts.txt` berisi prompt sistem
dan prompt minggu terpilih, sedangkan `tiket-<nomor>-<minggu>-portfolio.txt`
berisi teks hasil ekstraksi halaman portfolio. Isi kedua file itulah yang dibaca
dan dimasukkan ke request `/v1/chat/completions`. TXT dipakai karena endpoint
API llama.cpp tidak menyediakan kontrak upload TXT/PDF yang stabil seperti Web
UI-nya.

Worker meminta JSON terstruktur dan memvalidasi kelima dimensi rubrik, jumlah
total, tingkat, status evidence, serta konsistensi keputusan. Hasil ringkas
ditulis ke `antrian.csv`; laporan manusiawi beserta JSON sumber disimpan di
`assessment-results/`. Setelah berhasil, status default menjadi
`MENUNGGU PERSETUJUAN` dan `assessment.csv` belum berubah.

Assessor perlu membaca laporan lalu menyetujui tiket secara eksplisit:

```powershell
python llm.py --approve 7
```

Persetujuan memetakan total rubrik ke nilai resmi: `5-8` menjadi `1`, `9-12`
menjadi `2`, `13-16` menjadi `3`, dan `17-20` menjadi `4`; keputusan
`PERLU REVISI` dibatasi maksimal `2`. `BELUM DAPAT DINILAI` tidak menghapus
nilai lama. Mode lama yang langsung menulis nilai tersedia secara sadar dengan
`LLM_AUTO_APPROVE=true`, tetapi tidak direkomendasikan untuk penilaian resmi.

Worker mengklaim tiket secara atomik dengan status `PROSES`. Lease yang lebih
lama dari `LLM_LEASE_SECONDS` dapat diambil worker lain setelah crash. Laporan
yang sudah tersimpan digunakan ulang agar retry tidak meminta hasil model baru.
Error permanen diberi status `GAGAL`; error jaringan/server dikembalikan ke
`ANTRI` untuk dicoba lagi.

Tekan `Ctrl+C` pada terminal worker untuk menghentikannya dengan aman.

## Pengujian

```powershell
python -m unittest discover -s tests -v
```
