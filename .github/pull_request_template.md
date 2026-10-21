### Apa yang berubah

<!-- Satu paragraf. Apa yang sekarang berbeda dari sebelumnya. -->

### Kenapa

<!-- Masalah yang diselesaikan, atau permintaan yang dijawab. Kalau ada issue-nya,
sebut di sini dengan "Closes #123" supaya issue-nya ikut tertutup saat merge. -->

### Jenis perubahan

- [ ] Perbaikan bug
- [ ] Fitur baru
- [ ] Perbaikan tampilan atau pengalaman pakai
- [ ] Refactor, perilaku tidak berubah
- [ ] Performa
- [ ] Dokumentasi
- [ ] Infrastruktur, CI, atau skrip operasional

### Cara saya mengujinya

<!-- Bukan "sudah dites". Tulis yang benar-benar dijalankan, misalnya:
     - `pnpm --filter web check:types` bersih
     - `docker compose -f docker-compose-local.yml exec -T api python -m pytest plane/tests/x.py` lolos
     - dibuka di localhost:4000, dicoba dengan akun staf dan akun admin
   Kalau belum diuji sama sekali, tulis apa adanya. Itu informasi, bukan aib. -->

### Tangkapan layar

<!-- Wajib kalau menyentuh tampilan. Sebelum dan sesudah lebih baik daripada sesudah saja. -->

### Sebelum minta review

- [ ] `pnpm check` hijau di mesin saya, atau saya sebutkan bagian mana yang merah dan kenapa
- [ ] Tidak ada rahasia yang ikut ter-commit: tidak ada `.env`, token, kata sandi, atau kunci di dalam diff
- [ ] Menambah variabel lingkungan baru? `.env.example` yang bersangkutan ikut diperbarui
- [ ] Menyentuh berkas locale? `git status` sudah dicek dan junction `packages/i18n/locales` masih utuh
- [ ] Mengubah perilaku yang sudah didokumentasikan? README atau dokumen di `paradise/` ikut diperbarui

### Yang perlu diperhatikan reviewer

<!-- Bagian yang kamu sendiri paling ragu, keputusan yang sengaja diambil, atau
hal yang sengaja TIDAK dikerjakan di PR ini. Ini yang paling menghemat waktu review. -->
