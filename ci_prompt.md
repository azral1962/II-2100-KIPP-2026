# MASTER PROMPT
# KIPP-CI — Collective Intelligence Facilitator
## Python + Telegram Bot + LLM + Streamlit Dashboard

### 1. PERAN AI DEVELOPER

Bertindaklah sebagai senior Python software architect, AI engineer, educational technology researcher, multi-agent systems engineer, dan full-stack developer.

Bangun aplikasi Python lengkap bernama:

**KIPP-CI: Collective Intelligence Facilitator**

Aplikasi ini merupakan laboratorium pembelajaran mata kuliah **II2100 – Komunikasi Interpersonal dan Publik (KIPP)** sekaligus prototipe penerapan paradigma **Triune-Intelligence Smart Engineering (TISE)**.

Sistem harus dapat dijalankan pada laptop Windows, macOS, atau Linux, dan dapat dikembangkan untuk deployment pada server Ubuntu.

Implementasikan aplikasi modular, mudah dipelihara, memiliki dokumentasi, pengujian otomatis, dan antarmuka berbahasa Indonesia.

**Jangan berhenti pada rancangan arsitektur, pseudocode, atau contoh sebagian kode. Buat seluruh source code, konfigurasi, database, prompt AI, dashboard, unit test, serta petunjuk menjalankannya.**

---

## 2. KONSEP DAN FILOSOFI SISTEM

### 2.1 Collective Intelligence

Collective Intelligence (CI) adalah kemampuan suatu komunitas untuk:

1. Mengamati realitas bersama.
2. Menggabungkan pengetahuan, pengalaman, dan perspektif anggotanya.
3. Memahami masalah serta kebutuhan yang berbeda.
4. Membangun kesadaran dan tujuan bersama.
5. Menghasilkan alternatif solusi.
6. Membuat keputusan yang dapat dipertanggungjawabkan.
7. Mengorganisasikan tindakan kolektif.
8. Belajar dari hasil tindakan.
9. Meningkatkan pengetahuan kolektif dan modal sosial.

Kecerdasan kolektif tidak sama dengan banyaknya pesan, keseragaman pendapat, ataupun cepatnya voting.

Sebuah komunitas disebut lebih cerdas apabila kualitas pemahaman, pengambilan keputusan, koordinasi, pembelajaran, dan kapasitas pemecahan masalahnya meningkat.

### 2.2 Paradigma TISE

Gunakan tiga sumber kecerdasan:

- **Collective Intelligence (CI):** pengetahuan, pengalaman, nilai, relasi, kepercayaan, dan kerja sama antaranggota.
- **Natural Intelligence (NI):** kemampuan manusia mengamati, memahami, berempati, menilai, dan mengambil keputusan dalam konteks lingkungan kehidupannya.
- **Artificial Intelligence (AI):** kemampuan LLM dan algoritma untuk mengelompokkan informasi, menyusun ringkasan, mendeteksi perbedaan, menganalisis kontribusi, dan merekomendasikan intervensi.

AI harus menjadi pendukung kecerdasan kolektif, bukan pengganti manusia.

Keputusan normatif, asesmen akademik final, dan legitimasi kesepakatan tetap menjadi tanggung jawab manusia.

### 2.3 Komunikasi sebagai proses pengembangan CI

Sistem harus memperhatikan lima kompetensi:

1. **Awareness:** membangun kesadaran bersama terhadap realitas.
2. **Values:** memahami motivasi, kepentingan, dan nilai kehidupan.
3. **Character:** membangun kepercayaan, empati, integritas, dan tanggung jawab.
4. **Teamwork:** mengintegrasikan kontribusi dalam kerja sama.
5. **Action:** menghasilkan keputusan dan tindakan kolektif yang bernilai.

### 2.4 TAIDA sebagai kerangka fasilitasi

Gunakan TAIDA:

- **Target:** tujuan dan indikator keberhasilan.
- **Attention:** perhatian terhadap masalah.
- **Interest:** eksplorasi perspektif, kebutuhan, dan pengetahuan.
- **Desire:** pembentukan motivasi dan komitmen.
- **Action:** keputusan dan tindakan nyata.

Forum boleh bergerak maju atau kembali ke fase sebelumnya apabila muncul informasi atau keberatan baru.

---

## 3. SKENARIO UTAMA

Aplikasi digunakan dalam satu kelas berisi sekitar 40 mahasiswa.

Seluruh mahasiswa bergabung ke sebuah Telegram Supergroup.

Misi kelas:

**Secara kolektif merumuskan dan menyepakati spesifikasi proyek Ujian Akhir Semester, yaitu aplikasi AI yang membantu fasilitator membangun Collective Intelligence dalam suatu komunitas.**

Setiap mahasiswa harus memiliki kesempatan yang setara untuk:

- Menyampaikan pendapat.
- Memberikan alasan dan bukti.
- Mengajukan pertanyaan.
- Mengkritisi gagasan secara konstruktif.
- Mendengarkan dan menanggapi peserta lain.
- Menggabungkan ide.
- Memperbaiki pandangan setelah menerima informasi baru.
- Membantu fasilitasi percakapan.
- Merumuskan kesepakatan dan rencana aksi.

Telegram Bot harus mengamati percakapan dan secara berkala menghasilkan asesmen serta rekomendasi.

Setiap pesan mahasiswa merupakan kandidat bukti kontribusi, tetapi pesan tidak harus dinilai secara publik atau langsung setelah dikirim.

Kelas adalah laboratorium nyata untuk menguji perangkat lunak yang dirancang.

---

## 4. ARSITEKTUR APLIKASI

Gunakan arsitektur berikut:

```text
TELEGRAM SUPERGROUP
       |
       v
Telegram Bot Interface
       |
       v
Message Ingestion Service
       |
       v
Database + Conversation History
       |
       v
AI ANALYSIS ENGINE
       |
       +-- Message Analyzer
       +-- Student Competency Analyzer
       +-- Collective Intelligence Analyzer
       +-- Conflict and Consensus Analyzer
       +-- Social Capital Indicators
       +-- Facilitator Recommendation Engine
       |
       v
Assessment and Feedback Engine
       |
       +-- Personal Feedback
       +-- Facilitator Guidance
       +-- Collective Dashboard
       +-- Instructor Dashboard
       |
       v
Decision and Project Charter Generator
```

Bangun modul yang terpisah dengan antarmuka yang jelas.

### Stack teknologi

- Python 3.12 atau versi stabil kompatibel.
- python-telegram-bot versi stabil yang sesuai.
- FastAPI untuk REST API.
- SQLAlchemy dan Alembic untuk database.
- SQLite untuk pengembangan lokal.
- PostgreSQL sebagai pilihan deployment.
- Pydantic untuk validasi data.
- Streamlit untuk dashboard.
- Plotly untuk grafik interaktif.
- Pandas untuk analisis.
- APScheduler atau mekanisme scheduling yang kompatibel.
- Pytest untuk pengujian.
- httpx untuk akses API.
- dotenv atau konfigurasi environment yang aman.

### Backend AI

Sediakan tiga pilihan:

1. OpenAI-compatible API.
2. Google Gemini API.
3. Ollama lokal.

Gunakan adapter pattern:

```python
class LLMProvider:
    async def generate(self, messages, schema=None):
        ...

class OpenAIProvider(LLMProvider):
    ...

class GeminiProvider(LLMProvider):
    ...

class OllamaProvider(LLMProvider):
    ...
```

Pemilihan model dan provider dilakukan melalui konfigurasi, bukan hardcoded.

Sediakan juga MockLLMProvider agar aplikasi dan pengujian dapat berjalan tanpa API key.

Gunakan structured output dengan validasi Pydantic, penanganan kegagalan parsing, timeout, retry terbatas, dan logging.

---

## 5. MODEL DATA

Rancang database minimal dengan entitas berikut.

### Users

- user_id
- telegram_id
- student_id
- display_name
- role
- consent_status
- created_at

Role meliputi student, facilitator, instructor, dan administrator.

### Forums

- forum_id
- telegram_chat_id
- title
- objective
- status
- active_phase
- created_at

### Messages

- message_id
- telegram_message_id
- forum_id
- user_id
- timestamp
- text
- reply_to_message_id
- telegram_thread_id
- edited_at
- deleted_at
- ingestion_status

### MessageAssessments

- assessment_id
- message_id
- model_name
- rubric_version
- scores
- evidence
- feedback
- confidence
- assessment_timestamp

### CollectiveStates

- state_id
- forum_id
- timestamp
- participation_metrics
- knowledge_metrics
- deliberation_metrics
- consensus_metrics
- social_capital_indicators
- unresolved_issues
- recommendations

### Proposals

- proposal_id
- forum_id
- title
- description
- proposer_id
- supporting_arguments
- objections
- status

### Agreements

- agreement_id
- forum_id
- proposal_id
- decision_method
- confirmation_status
- participant_responses
- unresolved_objections
- decision_timestamp

### Interventions

- intervention_id
- forum_id
- trigger
- recommendation
- facilitator_decision
- posted_message_id
- timestamp

### ProjectCharters

- charter_id
- forum_id
- version
- title
- requirements
- acceptance_criteria
- work_packages
- approved_by
- created_at

Tambahkan audit logs, consent records, dan configuration tables jika diperlukan.

Implementasikan foreign keys, indexes, migrations, dan mekanisme deduplikasi Telegram update.

---

## 6. TELEGRAM BOT

Implementasikan perintah berikut.

### Perintah peserta

`/start` — registrasi dan pengantar.

`/help` — daftar perintah.

`/tujuan` — tujuan forum dan target pembelajaran.

`/status` — status diskusi.

`/usulan` — daftar alternatif solusi.

`/keberatan` — keberatan yang belum terselesaikan.

`/refleksi` — asesmen pribadi.

`/profil` — ringkasan perkembangan kompetensi.

### Perintah fasilitator

`/analisis` — menganalisis percakapan terbaru.

`/ringkasan` — menghasilkan ringkasan netral.

`/intervensi` — memperoleh saran intervensi.

`/fase` — melihat atau mengubah fase diskusi berdasarkan izin.

`/sepakat` — memulai proses konfirmasi keputusan.

`/poll` — membuat pemungutan suara ketika diperlukan.

### Perintah dosen

`/dashboard` — tautan dashboard.

`/laporan` — laporan kemajuan kelas.

`/rubrik` — menampilkan rubrik asesmen.

`/charter` — menghasilkan rancangan proyek UAS.

`/export` — mengekspor data sesuai kewenangan.

`/pause` dan `/resume` — menghentikan atau melanjutkan pengumpulan serta analisis data forum.

Pastikan perintah menggunakan pemeriksaan role dan authorization.

Gunakan Telegram inline keyboards jika sesuai.

Perhatikan Telegram Privacy Mode, permissions, forum topics, dan penanganan pesan yang diedit.

Jangan mengklaim dapat membaca pesan sebelum bot memperoleh akses atau pesan yang memang tidak tersedia melalui Telegram Bot API.

---

## 7. MESSAGE ANALYSIS ENGINE

AI menganalisis setiap pesan dalam konteks percakapan.

### 7.1 Klasifikasi speech act

Klasifikasikan kontribusi sebagai satu atau beberapa kategori:

- Information.
- Question.
- Proposal.
- Argument.
- Evidence.
- Clarification.
- Agreement.
- Disagreement.
- Constructive Criticism.
- Reframing.
- Integration.
- Synthesis.
- Facilitation.
- Decision.
- Commitment.
- Reflection.
- Off-topic.

### 7.2 Rubrik pesan

Gunakan skala 0–4 dan bobot:

| Dimensi | Bobot |
|---|---:|
| Relevance to Goal | 15% |
| Knowledge Contribution | 20% |
| Empathy and Respect | 15% |
| Knowledge Integration | 20% |
| Facilitation and Inclusion | 15% |
| Decision and Action Orientation | 15% |

Skor adalah indikator berbasis bukti, bukan pengukuran langsung kualitas manusia.

Untuk setiap dimensi hasilkan:

- Score.
- Explanation.
- Evidence message IDs.
- Improvement recommendation.
- Confidence.

Tidak semua pesan harus memperlihatkan semua dimensi.

Bedakan `not_observed`, `not_applicable`, dan `poor_performance` agar penilaian tidak menghukum pesan yang memang berfungsi terbatas.

Lakukan asesmen kontribusi mahasiswa secara longitudinal, bukan hanya dari rata-rata skor pesan.

### 7.3 Format keluaran

Gunakan JSON terstruktur seperti:

```json
{
  "message_id": 123,
  "speech_acts": ["proposal", "synthesis"],
  "scores": {
    "relevance": 4,
    "knowledge": 3,
    "empathy": 4,
    "integration": 4,
    "facilitation": 3,
    "action": 3
  },
  "evidence_message_ids": [120, 121],
  "feedback": "Pesan mengintegrasikan dua usulan.",
  "improvement": "Tambahkan indikator uji keberhasilan.",
  "confidence": 0.83
}
```

Model harus dapat menjelaskan alasan penilaian menggunakan bukti yang benar-benar tersedia.

---

## 8. COLLECTIVE INTELLIGENCE ENGINE

Implementasikan indikator proses berikut.

### Participation

- Jumlah peserta aktif.
- Proporsi peserta aktif.
- Distribusi kontribusi.
- Konsentrasi partisipasi.
- Jumlah peserta yang belum mendapat kesempatan menyampaikan gagasan.
- Keberagaman peserta yang gagasannya ditanggapi.

### Knowledge Development

- Jumlah gagasan unik.
- Jumlah klarifikasi substantif.
- Jumlah kontribusi berbukti.
- Jumlah sintesis gagasan.
- Jumlah asumsi yang berhasil diuji.
- Jumlah koreksi informasi.
- Pengetahuan baru yang terdokumentasi.

### Deliberation Quality

- Pertimbangan berbagai kepentingan.
- Kualitas argumentasi.
- Kritik konstruktif.
- Pengakuan ketidakpastian.
- Integrasi perspektif minoritas.
- Perbaikan alternatif setelah keberatan.

### Consensus and Decision

- Jumlah alternatif.
- Kejelasan kriteria keputusan.
- Keberatan yang terselesaikan.
- Keberatan yang tetap terbuka.
- Tingkat konfirmasi penerimaan keputusan.
- Kejelasan rencana tindakan.

### Social Capital

Bedakan:

- Bonding social capital.
- Bridging social capital.
- Linking social capital.

Gunakan indikator observasional seperti kerja sama lintas kelompok dan respons timbal balik.

Jangan menyimpulkan tingkat kepercayaan psikologis secara langsung dari teks.

Tambahkan survei singkat sebelum dan sesudah simulasi untuk mengukur persepsi trust, rasa didengar, psychological safety, dan kesediaan bekerja sama.

### Collective Intelligence Index

Bangun indeks eksploratif berbobot yang dapat dikonfigurasi.

Tampilkan komponen, bobot, metode perhitungan, keterbatasan, serta status validasinya.

Jangan mengklaim bahwa indeks eksploratif tersebut merupakan ukuran CI yang telah tervalidasi secara ilmiah.

---

## 9. FACILITATOR AGENT

Bangun AI agent yang menganalisis kondisi forum dan memberikan rekomendasi kepada fasilitator manusia.

Trigger meliputi:

1. Dominasi peserta tertentu.
2. Banyak peserta belum berkontribusi.
3. Diskusi berulang.
4. Konflik yang tidak berkembang.
5. Ketidakjelasan masalah.
6. Tidak ada kriteria keputusan.
7. Terlalu cepat mencapai kesepakatan.
8. Keberatan minoritas diabaikan.
9. Kurangnya bukti.
10. Pembahasan keluar dari tujuan.

Setiap rekomendasi memuat:

```json
{
  "trigger": "low_participation",
  "diagnosis": "Beberapa perspektif belum terdengar.",
  "recommended_question": "Siapa yang melihat persoalan ini secara berbeda?",
  "expected_effect": "Increase inclusiveness",
  "priority": "medium"
}
```

Secara default intervensi dikirim secara pribadi kepada fasilitator.

Fasilitator dapat memilih:

- Post to Forum.
- Modify.
- Ignore.
- Request Alternative.

Bot tidak boleh memaksakan keputusan atau mengumumkan konsensus tanpa konfirmasi manusia.

---

## 10. SCHEDULER ANALISIS

Implementasikan analisis berkala.

Konfigurasi default:

- 40 mahasiswa.
- Durasi kegiatan 110 menit.
- Analisis setiap 10 menit.
- Ringkasan kelas setiap 20 menit.
- Umpan balik personal setelah sejumlah kontribusi substantif atau pada akhir fase.
- Laporan final saat sesi ditutup.

Analisis juga dapat dipicu manual melalui `/analisis`.

Hindari analisis ulang pesan yang tidak berubah.

Implementasikan incremental processing, caching, rate limiting, dan pengendalian biaya penggunaan LLM.

---

## 11. STREAMLIT DASHBOARD

Buat antarmuka modern, profesional, responsif, dan seluruhnya berbahasa Indonesia.

### Halaman 1 — Overview

Tampilkan:

- Tujuan forum.
- Fase TAIDA aktif.
- Jumlah peserta.
- Partisipasi.
- Ringkasan masalah.
- Alternatif solusi.
- Status kesepakatan.

### Halaman 2 — Collective Intelligence

Tampilkan:

- Tren partisipasi.
- Pertumbuhan gagasan.
- Integrasi pengetahuan.
- Kualitas deliberasi.
- Status keputusan.
- Indikator modal sosial.
- Perbandingan awal dan akhir.

### Halaman 3 — Conversation Explorer

Tampilkan:

- Riwayat pesan.
- Filter mahasiswa.
- Filter speech act.
- Filter periode.
- Hubungan antara pesan dan usulan.
- Evidence untuk asesmen.

### Halaman 4 — Student Assessment

Untuk dosen dan mahasiswa yang berwenang.

Tampilkan:

- Profil kompetensi.
- Grafik perkembangan.
- Kontribusi penting.
- Kekuatan komunikasi.
- Saran perbaikan.
- Refleksi diri.

Mahasiswa hanya dapat mengakses asesmen pribadinya.

### Halaman 5 — Facilitator Cockpit

Tampilkan:

- Kondisi percakapan.
- Hambatan.
- Peserta yang belum terdengar.
- Keberatan terbuka.
- Rekomendasi AI.
- Tombol menerima, menyunting, atau menolak intervensi.

### Halaman 6 — Project Charter

Tampilkan hasil kesepakatan kelas:

- Problem statement.
- Target users.
- Functional requirements.
- Non-functional requirements.
- AI features.
- Data model.
- Acceptance criteria.
- Work packages.
- Implementation roadmap.

Tambahkan ekspor Markdown dan PDF jika dependensi tersedia.

### Halaman 7 — Configuration

Tampilkan pengaturan:

- LLM provider.
- Model.
- Interval analisis.
- Rubrik.
- Bobot.
- Kebijakan privasi.
- Session management.

Simpan rahasia API hanya pada server; jangan menampilkannya pada dashboard.

---

## 12. MODE SIMULASI TANPA TELEGRAM

Ini adalah fitur wajib.

Sediakan **Simulation Mode** yang berjalan sepenuhnya lokal.

Buat generator percakapan sintetik dengan:

- 40 mahasiswa fiktif.
- Beberapa profil gaya komunikasi.
- Fasilitator.
- Berbagai usulan.
- Konflik kepentingan.
- Kritik.
- Sintesis.
- Kesepakatan.

Data sintetik harus diberi label jelas.

Simulation Mode harus memungkinkan pengguna:

1. Menjalankan replay percakapan.
2. Menjalankan AI analyzer.
3. Melihat perkembangan CI.
4. Menguji trigger intervensi.
5. Menghasilkan laporan.
6. Membandingkan intervensi yang berbeda.

Sediakan seed sehingga simulasi reproducible.

Jangan menggunakan profil karakter fiktif sebagai dasar untuk menyimpulkan kepribadian mahasiswa nyata.

---

## 13. ASPEK KEAMANAN DAN ETIKA

Karena aplikasi digunakan untuk asesmen mahasiswa:

- Wajib ada persetujuan peserta yang diinformasikan.
- Terapkan role-based access control.
- Pisahkan feedback individual dan laporan kolektif.
- Jangan membuat leaderboard publik nilai mahasiswa.
- Gunakan pseudonimisasi bila memungkinkan.
- Sediakan kebijakan retensi dan penghapusan data.
- Jangan mengirim data sensitif kepada LLM tanpa perlindungan.
- Perlakukan isi pesan Telegram sebagai data tidak tepercaya, termasuk terhadap prompt injection.
- Lakukan logging tanpa membocorkan token atau API key.
- Berikan mekanisme koreksi asesmen oleh dosen.
- Berikan kesempatan mahasiswa meninjau bukti dan meminta peninjauan ulang.
- Nilai akademik final harus ditetapkan oleh dosen.

AI harus menghindari prasangka berdasarkan panjang pesan, dominasi bahasa, kecepatan respons, atau ciri pribadi peserta.

---

## 14. STRUKTUR PROYEK

Gunakan struktur yang kurang lebih seperti berikut:

```text
kipp-ci/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── migrations/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── telegram/
│   ├── api/
│   ├── services/
│   ├── agents/
│   │   ├── message_analyzer.py
│   │   ├── collective_analyzer.py
│   │   ├── facilitator_agent.py
│   │   └── assessment_agent.py
│   ├── llm/
│   ├── prompts/
│   ├── analytics/
│   ├── security/
│   └── scheduler/
├── dashboard/
│   ├── Home.py
│   ├── pages/
│   └── components/
├── simulator/
│   ├── generator.py
│   ├── scenarios.py
│   └── replay.py
├── tests/
└── docs/
```

Silakan sesuaikan bila ada alasan arsitektural yang lebih baik, tetapi pertahankan modularitas.

---

## 15. ACCEPTANCE TESTS

Aplikasi dianggap berhasil apabila:

1. Dapat dimulai tanpa Telegram menggunakan Simulation Mode.
2. Dapat menghubungkan bot ke Telegram menggunakan token yang valid.
3. Mampu menyimpan pesan grup yang memang dapat diakses bot.
4. Tidak menggandakan pesan ketika update Telegram dikirim ulang.
5. Dapat menganalisis pesan dengan konteks.
6. Menghasilkan skor, penjelasan, dan evidence.
7. Menampilkan status CI secara berkala.
8. Mengidentifikasi peserta yang belum berkontribusi.
9. Menyarankan intervensi yang relevan.
10. Tidak mengumumkan kesepakatan sebelum dikonfirmasi.
11. Menghasilkan Project Charter dari keputusan forum.
12. Menyajikan dashboard yang benar-benar menggunakan database.
13. Mampu mengekspor laporan.
14. Memiliki pengujian otomatis yang lulus.
15. Dapat berjalan tanpa API berbayar melalui MockLLMProvider.
16. Mencegah pengguna melihat asesmen pribadi orang lain tanpa izin.
17. Memulihkan proses dari gangguan LLM atau Telegram tanpa kehilangan konsistensi data.

---

## 16. LANGKAH IMPLEMENTASI YANG HARUS DILAKUKAN

Kerjakan secara sistematis:

**Tahap A — Foundation**

- Buat struktur direktori.
- Konfigurasi.
- Database.
- Model data.
- Migrasi.
- Unit tests dasar.

**Tahap B — Telegram**

- Registrasi peserta.
- Pengambilan pesan.
- Penyimpanan.
- Role management.
- Commands.

**Tahap C — AI Analytics**

- LLM adapters.
- Prompt templates.
- Message analysis.
- Aggregation.
- Collective state computation.

**Tahap D — Facilitator Agent**

- Trigger detection.
- Recommendation engine.
- Human approval workflow.

**Tahap E — Dashboard**

- Seluruh halaman Streamlit.
- Visualisasi.
- Laporan.
- Kontrol akses.

**Tahap F — Simulator**

- Generator data.
- Replay.
- Skenario konflik dan konsensus.
- Analisis hasil simulasi.

**Tahap G — Integration & Testing**

- Integrasi semua modul.
- Pengujian end-to-end.
- Penanganan error.
- Dokumentasi.
- Contoh konfigurasi.

Pada setiap tahap, hasilkan kode nyata, bukan placeholder.

Jika lingkungan coding mendukung terminal dan filesystem, buat file secara langsung, jalankan pengujian, lalu perbaiki error sampai sistem dapat dijalankan.

Jika lingkungan tidak menyediakan eksekusi, berikan isi semua file yang diperlukan tanpa menyatakan bahwa pengujian sudah berhasil.

---

## 17. OUTPUT AKHIR

Hasilkan:

1. Source code Python lengkap.
2. Telegram Bot yang operasional.
3. AI Analysis Engine.
4. Facilitator Agent.
5. Assessment Engine.
6. Collective Intelligence Dashboard.
7. Simulation Mode.
8. Database beserta migrasi.
9. Prompt AI terpisah dan mudah dikembangkan.
10. Unit dan integration tests.
11. README berbahasa Indonesia.
12. Contoh `.env`.
13. Docker deployment.
14. Panduan demonstrasi untuk kelas II2100.
15. Penjelasan keterbatasan pengukuran Collective Intelligence.

### Kriteria keberhasilan tertinggi

Aplikasi harus membantu komunitas:

**From Conversation → Shared Understanding → Collective Intelligence → Collective Decision → Collective Action → Social Capital Growth.**

Aplikasi tidak hanya merangkum percakapan, tetapi memampukan fasilitator manusia untuk mengembangkan kecerdasan kolektif secara bertanggung jawab.

Mulailah dengan menjelaskan arsitektur final secara ringkas, lalu segera implementasikan aplikasi dalam source code yang dapat dijalankan.
