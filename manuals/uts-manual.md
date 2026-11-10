# Penilaian manual UTS dengan Streamlit

Jalankan dari folder proyek:

```bash
.venv/bin/python -m pip install -r requirements-uts-review.txt
.venv/bin/python -m streamlit run uts_review.py --server.address 127.0.0.1
```

Buka http://localhost:8501. Pilih mahasiswa dan tiket W08, buka indeks portfolio atau tautan tiap komponen, lalu isi nama dosen, nilai 0–100, dan catatan. Tautan berasal dari snapshot evidence tiket bila tersedia. Tautan yang dibuat berdasarkan pola nama berkas ditandai sebagai alamat perkiraan; gunakan indeks W08 jika tautan tersebut tidak tersedia.

Pra-UTS/makalah berbobot 10%; sesi 1, 2a, 2b, 3a, 3b masing-masing 18%. Nilai kosong berarti belum dinilai dan berbeda dengan nol. Simpan draf untuk pekerjaan parsial. Finalisasi hanya tersedia secara valid setelah semua enam nilai dan nama dosen terisi. Total merupakan penjumlahan berbobot skala 0–100.

Penilaian manual disimpan dalam `uts-manual-reviews.json` (opsional: `UTS_MANUAL_FILE` di `.env`). Setiap penyimpanan menambahkan revisi; catatan dan nilai lama tetap tersedia. Rekap menampilkan revisi terbaru per NIM, termasuk status DRAF/FINAL, dan dapat diunduh sebagai CSV. Ketika memilih tiket berbeda untuk mahasiswa yang sama, form memuat nilai manual terakhir mahasiswa tersebut; periksa kembali sebelum menyimpan.

Aplikasi ini tidak memanggil LLM, tidak mengubah `antrian.csv`, `assessment.csv`, atau `uts-assessment.csv`. Status FINAL adalah finalisasi dalam buku nilai manual terpisah. File JSON perlu dicadangkan bersama data nilai lain. Aplikasi ditujukan untuk komputer dosen pada localhost; nama dosen merupakan pencatatan, bukan login/autentikasi.

## Mengadopsi usulan AI

Setiap sesi menampilkan nilai AI /100, status evidence, ringkasan, dan prioritas perbaikan dari laporan tiket yang dipilih. Klik **Adopsi nilai AI** untuk mengisi nilai dosen sesi tersebut. Nilai tetap dapat diedit; gunakan **Simpan draf** atau **Finalisasi nilai manual** untuk menyimpannya. Tombol adopsi tidak menyimpan atau memfinalisasi nilai. BT tidak dapat diadopsi sebagai angka. Pra-UTS tetap dinilai manual oleh dosen. Laporan yang tidak cocok dengan NIM/tiket atau tidak valid tidak digunakan.
