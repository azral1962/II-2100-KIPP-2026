# Acuan resmi dosen untuk UTS

## Acuan yang sudah dipasang

65 file `NIM.json` sudah dibentuk dari 325 paket individual versi 2.0 pada repo
`kipp-students`. File individual tetap diabaikan Git. Penugasan, NIM, sesi,
versi dan perbedaan sasaran pasangan sesi diperiksa; hash sumber disimpan.

**Status saat ini: draft.** Descriptor level 1–4 tidak tersedia dalam paket
asli. [RUBRIC-DRAFT.md](RUBRIC-DRAFT.md) dan `rubric-operasional-v1.draft.json`
berisi usulan baru untuk ditinjau dosen. Loader menampilkan BT untuk draf,
termasuk ketika file individual lengkap. Status approved memerlukan nama dan
waktu pengesahan. File acuan lama tanpa field status tetap kompatibel.

Seluruh 65 peserta sudah memiliki lima paket sumber, termasuk NIM **18225111**.
Acuan individual tetap berstatus draft sampai descriptor disahkan dosen.

Setelah descriptor ditetapkan dosen, bentuk acuan approved ke folder baru:

```powershell
python prepare_uts_references.py --packages "C:\github\kipp-students\lk\lk-UTS\peserta" --rubric uts-references/rubric-operasional-v1.draft.json --output uts-references-approved --approved-by "Nama Dosen"
```

Gunakan opsi `--approved-by` hanya setelah pengesahan nyata. Generator tidak
menimpa file yang sudah ada. Set `UTS_REFERENCE_DIR=uts-references-approved`
di `.env`, restart worker/bot, lalu antrekan ulang tiket BT dengan
`python llm.py --retry-uts N`. Nilai makalah dan approval tiket tetap berasal
dari dosen. Makalah tidak dinilai menggunakan descriptor performance ini.

Untuk membentuk draf baru dari paket terbaru, jalankan generator tanpa
`--approved-by` dan pilih folder output baru. Jangan menyalin acuan satu NIM
ke NIM lain atau mengganti target dari paket secara manual.

## Struktur acuan

Simpan `NIM.json` di folder ini (NIM adalah string, termasuk nol di awal).
Berkas JSON individual diabaikan Git. Jangan mengisi descriptor berdasarkan
perkiraan atau mengambil self-assessment mahasiswa sebagai rubrik dosen.

Struktur wajib:

```json
{
  "nim": "07381119",
  "package_version": "2.0",
  "assignments": {
    "1": "Salinan PENUGASAN.md sesi 1 dari paket aktif dosen",
    "2a": "Salinan PENUGASAN.md sesi 2a",
    "2b": "Salinan PENUGASAN.md sesi 2b",
    "3a": "Salinan PENUGASAN.md sesi 3a",
    "3b": "Salinan PENUGASAN.md sesi 3b"
  },
  "descriptors": {
    "objective_context": {"1": "Descriptor resmi", "2": "Descriptor resmi", "3": "Descriptor resmi", "4": "Descriptor resmi"},
    "perception_validation": {"1": "Descriptor resmi", "2": "Descriptor resmi", "3": "Descriptor resmi", "4": "Descriptor resmi"},
    "repertoire_sequence": {"1": "Descriptor resmi", "2": "Descriptor resmi", "3": "Descriptor resmi", "4": "Descriptor resmi"},
    "execution_care_consistency": {"1": "Descriptor resmi", "2": "Descriptor resmi", "3": "Descriptor resmi", "4": "Descriptor resmi"},
    "evaluation_adaptation": {"1": "Descriptor resmi", "2": "Descriptor resmi", "3": "Descriptor resmi", "4": "Descriptor resmi"},
    "reflection_learning": {"1": "Descriptor resmi", "2": "Descriptor resmi", "3": "Descriptor resmi", "4": "Descriptor resmi"}
  }
}
```

Contoh di atas adalah struktur, bukan rubrik siap pakai. Ganti seluruh placeholder
dengan acuan resmi. Tanpa file, worker membuat inventaris evidence dan BT tanpa
memanggil model. File ada tetapi rusak/tidak lengkap menghasilkan GAGAL agar
operator memperbaikinya. Jika belum ada descriptor resmi, jangan membuatnya dari
enam fokus pemeriksaan dalam template; fokus tersebut bukan descriptor level 1–4.

Periksa NIM, versi, sasaran aktif dan perbedaan target 2a/2b serta 3a/3b sebelum
menyediakan acuan. Simpan teks paket sebagai instruksi dosen; profil simulator
bukan evidence kinerja mahasiswa. Referensi, snapshot evidence dan hasil individual
bersifat lokal dan tidak perlu dipublikasikan dalam repo.
