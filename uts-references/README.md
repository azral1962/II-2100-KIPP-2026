# Acuan resmi dosen untuk UTS

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
