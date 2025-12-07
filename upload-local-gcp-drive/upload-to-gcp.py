#!/usr/bin/env python3
import argparse, csv, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
from google.cloud import storage

TZ = ZoneInfo("Asia/Jakarta")

def iter_files(src: Path):
    if src.is_file():
        yield src
    else:
        for p in src.rglob("*"):
            if p.is_file():
                yield p

def upload_one(client, bucket_name, local_path: Path, dest_prefix: str, source_root: Path):
    bucket = client.bucket(bucket_name)
    rel = local_path.relative_to(source_root) if source_root.is_dir() else local_path.name
    blob_name = f"{dest_prefix}{rel}".replace("\\", "/")
    blob = bucket.blob(blob_name)

    # Use resumable upload; adjust chunk size if desired (e.g., 8*1024*1024)
    # blob.chunk_size = 8 * 1024 * 1024

    start = time.perf_counter()
    blob.upload_from_filename(str(local_path))
    dur = time.perf_counter() - start
    size_bytes = local_path.stat().st_size
    mbps = (size_bytes / (1024 * 1024)) / dur if dur > 0 else 0.0
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time()))
    return {
        "timestamp_local": ts,
        "source_path": str(local_path),
        "gcs_uri": f"gs://{bucket_name}/{blob_name}",
        "size_bytes": size_bytes,
        "duration_sec": round(dur, 3),
        "throughput_MBps": round(mbps, 2),
    }

def main():
    ap = argparse.ArgumentParser(description="Upload to GCS with per-file time report")
    ap.add_argument("source", help="File or directory to upload")
    ap.add_argument("bucket", help="Target bucket name (without gs://)")
    ap.add_argument("--prefix", default="", help="Object key prefix inside the bucket (e.g., 'backup/')")
    ap.add_argument("--workers", type=int, default=4, help="Parallel upload workers")
    ap.add_argument("--log", default=None, help="CSV log path (default: ./logs/gcs_upload_<timestamp>.csv)")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        sys.exit(1)

    ts_name = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    log_dir = Path("./logs"); log_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log) if args.log else log_dir / f"gcs_upload_{ts_name}.csv"

    client = storage.Client()
    files = list(iter_files(source))
    if not files:
        print("No files to upload.")
        return

    # Ensure prefix ends with / if provided and not already
    prefix = args.prefix
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    print(f"Uploading {len(files)} file(s) to gs://{args.bucket}/{prefix} ...")
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp_local","source_path","gcs_uri","size_bytes","duration_sec","throughput_MBps"])
        writer.writeheader()

        successes = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(upload_one, client, args.bucket, p, prefix, source): p for p in files}
            for fut in as_completed(futs):
                p = futs[fut]
                try:
                    row = fut.result()
                    writer.writerow(row)
                    successes += 1
                    print(f"[OK] {p} -> {row['gcs_uri']} ({row['duration_sec']}s, {row['throughput_MBps']} MB/s)")
                except Exception as e:
                    print(f"[FAIL] {p}: {e}", file=sys.stderr)

    print(f"Done. Success: {successes}/{len(files)}. Log: {log_path}")

if __name__ == "__main__":
    main()