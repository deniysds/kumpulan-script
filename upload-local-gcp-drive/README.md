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
python3 upload-to-gcp.py <source> <bucket> [--prefix PREFIX] [--workers N] [--log PATH]
```

- `source`: path ke file atau direktori lokal yang akan diunggah.
- `bucket`: nama bucket target (tanpa `gs://`).
- `--prefix`: awalan objek di dalam bucket, mis. `backup/`. Jika diisi dan tidak diakhiri `/`, skrip akan menambahkan `/` secara otomatis (`upload-local-gcp-drive/upload-to-gcp.py:98-102`).
- `--workers`: jumlah pekerja paralel (default `4`) (`upload-local-gcp-drive/upload-to-gcp.py:79,109`).
- `--log`: path CSV untuk log. Default: `./logs/gcs_upload_<timestamp>.csv` dan direktori `./logs` akan dibuat otomatis (`upload-local-gcp-drive/upload-to-gcp.py:88-91,104-107`).

### Contoh
```bash
# Unggah satu file ke bucket my-backup tanpa prefix
python3 upload-to-gcp.py ~/data/report.pdf my-backup

# Unggah seluruh direktori dengan prefix dan 8 worker
python3 upload-to-gcp.py ~/data my-backup --prefix backup/ --workers 8

# Unggah direktori dan simpan log ke lokasi khusus
python3 upload-to-gcp.py ./photos my-backup --prefix archive/ --log /tmp/upload_log.csv
```

## Output & Log
- Terminal akan menampilkan hasil setiap file: `[OK]` atau `[FAIL]` dengan waktu dan throughput (`upload-local-gcp-drive/upload-to-gcp.py:117-119`).
- CSV berisi kolom: `timestamp_local`, `source_path`, `gcs_uri`, `size_bytes`, `duration_sec`, `throughput_MBps` (`upload-local-gcp-drive/upload-to-gcp.py:105-107,114-116`).
- Ringkasan akhir: jumlah sukses/total dan lokasi file log (`upload-local-gcp-drive/upload-to-gcp.py:121`).

## Penamaan Objek di GCS
- Nama objek dibentuk dari `prefix + relative_path` terhadap sumber (`upload-local-gcp-drive/upload-to-gcp.py:26-31`).
- Pemisah path dinormalisasi menjadi `/` agar konsisten di GCS.

## Kinerja
- Naikkan `--workers` untuk mempercepat banyak file kecil. Uji dan sesuaikan agar tidak melampaui batas jaringan atau kuota.
- Unggah menggunakan mekanisme resumable dari `google-cloud-storage`. Ukuran chunk dipaksa ke `8 MiB` untuk stabilitas jaringan, dapat disesuaikan via konstanta `CHUNK_SIZE` (`upload-local-gcp-drive/upload-to-gcp.py:31`).

## Reliabilitas & Retry
- Skrip mengaktifkan retry untuk error transien (timeout/reset koneksi) menggunakan `google.api_core.retry.Retry` (`upload-local-gcp-drive/upload-to-gcp.py:33-35`).
- Konstanta penyetelan:
  - `WRITE_TIMEOUT_SEC = 900`: timeout per permintaan/chunk (bukan total file) (`upload-local-gcp-drive/upload-to-gcp.py:21`).
  - `CHUNK_SIZE = 8 * 1024 * 1024`: ukuran chunk 8 MiB untuk jaringan tidak stabil (`upload-local-gcp-drive/upload-to-gcp.py:22,31`).
  - `MAX_ATTEMPTS = 6`: percobaan maksimum per file (`upload-local-gcp-drive/upload-to-gcp.py:23,41-64`).
  - `BASE_BACKOFF = 2.0`: exponential backoff dengan jitter (`upload-local-gcp-drive/upload-to-gcp.py:24,66-69`).
- Throughput dihitung berbasis durasi total unggah per file (`upload-local-gcp-drive/upload-to-gcp.py:50-60`).

## Penjelasan Fungsi
- `iter_files` (`upload-local-gcp-drive/upload-to-gcp.py:12-18`): Menghasilkan iterator semua file dari sumber, mendukung file tunggal atau penelusuran rekursif direktori.
- `upload_one` (`upload-local-gcp-drive/upload-to-gcp.py:26-73`): Mengunggah satu file ke GCS dengan retry, timeout per chunk, dan kalkulasi throughput, lalu mengembalikan data ringkasan.
- `main` (`upload-local-gcp-drive/upload-to-gcp.py:74-124`): Mengurai argumen CLI, menyiapkan klien GCS, menjalankan unggah paralel, dan menulis log CSV.

## Troubleshooting
- Pastikan kredensial valid dan memiliki akses ke bucket.
- Periksa koneksi jaringan jika banyak `[FAIL]` muncul.
- Pastikan `bucket` sudah dibuat dan nama benar (tanpa `gs://`).
- Gunakan path absolut untuk `source` dan `--log` bila perlu.