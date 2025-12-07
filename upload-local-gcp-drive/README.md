# Upload ke Google Cloud Storage (GCS)

Skrip `upload-to-gcp.py` melakukan unggah file atau seluruh direktori ke bucket GCS dengan dukungan paralel, pelaporan waktu per file, dan pencatatan ke CSV.

## Prasyarat
- Python 3.9+ (direkomendasikan)
- Paket Python: `google-cloud-storage`
- Kredensial Google Cloud siap digunakan

## Instalasi
```bash
pip install google-cloud-storage
```

## Autentikasi
Pilih salah satu metode berikut:

```bash
# Metode 1: Application Default Credentials (ADC) via gcloud
gcloud auth application-default login

# Metode 2: Service Account Key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

## Cara Pakai
```bash
python3 upload-to-gcp.py \
  <source> <bucket> \
  [--prefix PREFIX] [--workers N] \
  [--timeout-sec S] [--chunk-mb M] [--max-attempts K] \
  [--log PATH]
```

- `source`: path ke file atau direktori lokal yang akan diunggah.
- `bucket`: nama bucket target (tanpa `gs://`).
- `--prefix`: awalan objek di dalam bucket, mis. `backup/`. Jika diisi dan tidak diakhiri `/`, skrip akan menambahkan `/` secara otomatis (`upload-local-gcp-drive/upload-to-gcp.py:115-117`).
- `--workers`: jumlah pekerja paralel (default `4`, kurangi jika jaringan tidak stabil) (`upload-local-gcp-drive/upload-to-gcp.py:93-94,135`).
- `--timeout-sec`: timeout per permintaan/chunk dalam detik (default `900=15m`) (`upload-local-gcp-drive/upload-to-gcp.py:94,59-63`).
- `--chunk-mb`: ukuran chunk resumable dalam MiB (default `8`), coba `8–32` pada jaringan tidak stabil (`upload-local-gcp-drive/upload-to-gcp.py:95,41-43`).
- `--max-attempts`: jumlah percobaan total per file (default `6`) (`upload-local-gcp-drive/upload-to-gcp.py:96,56-84`).
- `--log`: path CSV untuk log. Default: `./logs/gcs_upload_<timestamp>.csv` dan direktori `./logs` akan dibuat otomatis (`upload-local-gcp-drive/upload-to-gcp.py:105-107,121-133`).

### Contoh
```bash
# Unggah satu file ke bucket my-backup tanpa prefix
python3 upload-to-gcp.py ~/data/report.pdf my-backup

# Unggah seluruh direktori dengan prefix dan 8 worker
python3 upload-to-gcp.py ~/data my-backup --prefix backup/ --workers 8

# Unggah direktori dengan kontrol reliabilitas
python3 upload-to-gcp.py ./photos my-backup \
  --prefix archive/ --workers 4 \
  --timeout-sec 1200 --chunk-mb 16 --max-attempts 8 \
  --log /tmp/upload_log.csv
```

## Output & Log
- Terminal akan menampilkan hasil setiap file: `[OK]` atau `[FAIL]` dengan waktu dan throughput (`upload-local-gcp-drive/upload-to-gcp.py:156-158`).
- CSV berisi kolom: `timestamp_local`, `source_path`, `gcs_uri`, `size_bytes`, `duration_sec`, `throughput_MBps` (`upload-local-gcp-drive/upload-to-gcp.py:121-131,153-155`).
- Ringkasan akhir: jumlah sukses/total dan lokasi file log (`upload-local-gcp-drive/upload-to-gcp.py:160`).

## Penamaan Objek di GCS
- Nama objek dibentuk dari `prefix + relative_path` terhadap sumber (`upload-local-gcp-drive/upload-to-gcp.py:35-38`).
- Pemisah path dinormalisasi menjadi `/` agar konsisten di GCS.

## Kinerja
- Naikkan `--workers` untuk mempercepat banyak file kecil. Uji dan sesuaikan agar tidak melampaui batas jaringan atau kuota.
- Jika jaringan tidak stabil, kurangi `--workers` dan naikkan `--chunk-mb` (mis. 16–32 MiB) agar HTTP write lebih besar namun lebih sedikit.
- Unggah menggunakan mekanisme resumable, ukuran chunk dikendalikan oleh `--chunk-mb` (`upload-local-gcp-drive/upload-to-gcp.py:41-43`).

## Reliabilitas & Retry
- Skrip mengaktifkan retry untuk error transien (timeout/reset koneksi/5xx) menggunakan `google.api_core.retry.Retry` (`upload-local-gcp-drive/upload-to-gcp.py:45-50`).
- Pengendalian reliabilitas melalui CLI:
  - `--timeout-sec`: timeout per permintaan/chunk (bukan total file) (`upload-local-gcp-drive/upload-to-gcp.py:59-63`).
  - `--chunk-mb`: memaksa resumable upload dengan ukuran chunk tertentu (`upload-local-gcp-drive/upload-to-gcp.py:41-43`).
  - `--max-attempts`: total percobaan per file dengan exponential backoff + jitter (`upload-local-gcp-drive/upload-to-gcp.py:56-84`).
- Throughput dihitung berbasis durasi total unggah per file (`upload-local-gcp-drive/upload-to-gcp.py:64-66,72-74`).

## Zona Waktu
- Menggunakan `Asia/Jakarta` via `zoneinfo` bila tersedia; fallback ke UTC+7 jika basis data zona waktu tidak tersedia (`upload-local-gcp-drive/upload-to-gcp.py:9-16`).

## Penjelasan Fungsi
- `iter_files` (`upload-local-gcp-drive/upload-to-gcp.py:17-23`): Menghasilkan iterator semua file dari sumber, mendukung file tunggal atau penelusuran rekursif direktori.
- `upload_one` (`upload-local-gcp-drive/upload-to-gcp.py:25-86`): Mengunggah satu file ke GCS dengan timeout per chunk, ukuran chunk dinamis, `Retry`, dan backoff berjitter; mengembalikan data ringkasan.
- `main` (`upload-local-gcp-drive/upload-to-gcp.py:88-163`): Mengurai argumen CLI, menyiapkan klien GCS, menjalankan unggah paralel dengan parameter reliabilitas, dan menulis log CSV.

## Troubleshooting
- Pastikan kredensial valid dan memiliki akses ke bucket.
- Periksa koneksi jaringan jika banyak `[FAIL]` muncul.
- Pastikan `bucket` sudah dibuat dan nama benar (tanpa `gs://`).
- Gunakan path absolut untuk `source` dan `--log` bila perlu.

---

# Salin dari GCS ke Google Drive (rclone)

Skrip `gcp-to-drive.sh` menyalin objek dari remote GCS ke remote Google Drive menggunakan `rclone`. Skrip ini mendukung parameterisasi concurrency, ukuran chunk Drive, logging, serta opsi dry-run.

## Instalasi Rclone
- macOS: `brew install rclone`
- Linux (Debian/Ubuntu): `sudo apt-get install rclone` atau ikuti panduan resmi di https://rclone.org/install/
- Verifikasi: `rclone version`

## Konfigurasi Rclone
- Buat remote `gcs` (Google Cloud Storage):
  - Jalankan `rclone config` → pilih `n` (new remote) → nama: `gcs` → storage: `Google Cloud Storage`.
  - Gunakan service account: isi `service_account_file` dengan path JSON (`/path/to/key.json`).
  - Isi `project_number` bila diperlukan, sisanya dapat default.
  - Alternatif non-interaktif: `rclone config create gcs gcs service_account_file /path/to/key.json`.
- Buat remote `gdrive` (Google Drive):
  - Jalankan `rclone config` → pilih `n` (new remote) → nama: `gdrive` → storage: `Google Drive`.
  - Scope: `drive` (full access) atau `drive.readonly` sesuai kebutuhan.
  - Auto config: `yes`, login via browser, pilih akun, dan izinkan akses.
  - Jika memakai Shared Drive, set `team_drive` atau aktifkan saat prompt.

## Verifikasi Konfigurasi
- Lihat bucket GCS: `rclone lsd gcs:` atau `rclone ls gcs:<bucket>`
- Lihat folder Drive: `rclone lsd gdrive:`

## Cara Pakai
```bash
bash gcp-to-drive.sh \
  --src "gcs:<bucket>/<path>" \
  --dst "gdrive:<folder>/<path>" \
  [--transfers N] [--checkers N] \
  [--chunk M] [--shared] [--ignore-existing] \
  [--no-progress] [--dry-run] \
  [--log-file PATH] [--log-level LEVEL]
```

- `--src`: remote sumber GCS, mis. `gcs:transit_bucket_ysds/itdel/BPM1`.
- `--dst`: remote tujuan Drive, mis. `gdrive:01_Data Mentah/itdel/bawang_putih/BPM1`.
- `--transfers`: jumlah transfer paralel (default `16`).
- `--checkers`: jumlah proses pemeriksa (default `8`).
- `--chunk`: ukuran chunk Drive, mis. `64M` (default `64M`).
- `--shared`: sertakan file yang dibagikan ke akun (`--drive-shared-with-me`).
- `--ignore-existing`: lewati file yang sudah ada di tujuan (default aktif).
- `--no-progress`: sembunyikan progress.
- `--dry-run`: simulasi tanpa menyalin.
- `--log-file`: tulis log rclone ke file.
- `--log-level`: tingkat log rclone (`INFO`, `ERROR`, `DEBUG`; default `INFO`).

### Contoh
```bash
# Menyalin dari GCS ke Drive dengan setting default
bash gcp-to-drive.sh \
  --src "gcs:transit_bucket_ysds/itdel/BPM1" \
  --dst "gdrive:01_Data Mentah/itdel/bawang_putih/BPM1" \
  --shared --transfers 16 --checkers 8 --chunk 64M

# Dry-run untuk verifikasi
bash gcp-to-drive.sh \
  --src "gcs:my-bucket/data" \
  --dst "gdrive:Backup/data" \
  --dry-run --log-level INFO

# Dengan log file
bash gcp-to-drive.sh \
  --src "gcs:my-bucket/data" \
  --dst "gdrive:Backup/data" \
  --log-file /tmp/rclone_copy.log --log-level DEBUG
```

## Catatan
- Pastikan remote `gcs` dan `gdrive` telah dikonfigurasi dengan kredensial yang valid.
- Pada folder Drive yang dibagikan, aktifkan `--shared` agar file muncul.
- Sesuaikan `--transfers` dan `--checkers` sesuai bandwidth/koneksi.
- Ukuran `--chunk` lebih besar dapat membantu throughput, namun bergantung pada kondisi jaringan.

---

# Rotasi Service Account untuk Rclone (gcp-to-drive-sa.sh)

Skrip `gcp-to-drive-sa.sh` menyalin data dari GCS ke Google Drive menggunakan `rclone` dengan mekanisme rotasi Service Account (SA). Skrip akan berganti ke file kredensial SA berikutnya ketika mencapai batas transfer atau kuota.

## Kebutuhan
- `rclone` telah terpasang dan remote `gcs` serta `gdrive_sa` sudah dikonfigurasi.
  - `gcs`: gunakan service account file JSON sesuai proyek GCS.
  - `gdrive_sa`: remote Google Drive yang relevan (bisa Shared Drive). Pastikan akun SA memiliki akses ke Drive/Shared Drive.
- Direktori berisi banyak file JSON service account, mis. `/home/daeng_deni/sa`.
- Hak akses yang memadai pada bucket GCS sumber dan folder Drive tujuan.

## Konfigurasi yang Perlu Disesuaikan
- Buka `gcp-to-drive-sa.sh` dan sesuaikan variabel berikut:
  - `SADIR`: direktori berisi file `*.json` service account.
  - `SRC`: sumber, contoh `gcs:transit_bucket_ysds/bawang_putih_prima_UGM`.
  - `DST`: tujuan, contoh `gdrive_sa:01_Data Mentah/ugm/prima/bawang_putih`.
  - `LIMIT`: batas transfer per SA, mis. `350G` (atur sesuai kebijakan; Anda dapat menaikkan/menurunkan sesuai kebutuhan).

## Cara Penggunaan
```bash
bash gcp-to-drive-sa.sh
```

- Skrip akan mengiterasi semua file JSON di `SADIR`.
- Pada setiap iterasi, `GOOGLE_APPLICATION_CREDENTIALS` akan diarahkan ke file SA aktif.
- Ketika batas tercapai atau error kuota terjadi, skrip akan tidur beberapa detik lalu beralih ke SA berikutnya.

## Opsi Rclone yang Digunakan
- `--transfers=1`, `--checkers=1`: menjaga beban rendah agar tidak cepat kena limit.
- `--drive-chunk-size=64M`, `--fast-list`, `--drive-shared-with-me`, `--ignore-existing`.
- `--max-transfer <LIMIT>`, `--drive-stop-on-upload-limit`, `--bwlimit 200M`, `--verbose`, `--progress`.

## Penanganan Exit Code (Rotasi SA)
- `0`: selesai tanpa error → keluar.
- `8`: `--max-transfer` tercapai → ganti SA.
- `9`: upload limit terlampaui → ganti SA.
- `3` atau `4`: rate limit (403) → ganti SA.
- `7`: `userRateLimitExceeded (403)` → ganti SA.
- Lainnya: hentikan dengan pesan “Unhandled error”.

## Tips
- Tempatkan banyak SA di `SADIR` untuk dataset besar.
- Pastikan tiap SA diberi akses ke folder Drive tujuan (shared atau Team Drive).
- Sesuaikan `LIMIT` agar sesuai kebijakan kuota harian Drive per SA.