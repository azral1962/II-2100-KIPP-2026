# Student Course Services II2100

Bot Telegram untuk interaksi mahasiswa yang terdaftar dengan instruktur.

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
  dan status `ANTRI`.
- Registrasi tidak dapat mengambil alih NIM yang sudah terhubung atau memakai
  satu akun Telegram untuk dua NIM.

Repo dinyatakan valid hanya jika URL memakai format
`https://github.com/pemilik/repo`, repo dapat dibaca melalui GitHub, dan baris
pertama `README.md` pada branch default tepat seperti berikut:

```markdown
# Portfolio Mahasiswa KIPP-2
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
```

Jangan simpan token bot di source code atau commit Git.

## Pengujian

```powershell
python -m unittest discover -s tests -v
```
