#!/usr/bin/env python3
import argparse, csv, os, sys, time, math, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import timezone, timedelta
from google.cloud import storage
from google.api_core.retry import Retry

# ---- Timezone (robust) ----
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Jakarta")
except Exception:
    # Fallback to fixed UTC+7 if tz database missing
    TZ = timezone(timedelta(hours=7))

def iter_files(src: Path):
    if src.is_file():
        yield src
    else:
        for p in src.rglob("*"):
            if p.is_file():
                yield p

def upload_one(
    client,
    bucket_name: str,
    local_path: Path,
    dest_prefix: str,
    source_root: Path,
    write_timeout_sec: float,
    chunk_mb: int,
    max_attempts: int,
):
    bucket = client.bucket(bucket_name)
    rel = local_path.relative_to(source_root) if source_root.is_dir() else local_path.name
    blob_name = f"{dest_prefix}{rel}".replace("\\", "/")
    blob = bucket.blob(blob_name)

    # Force resumable upload and smaller HTTP writes for flaky links
    if chunk_mb and chunk_mb > 0:
        blob.chunk_size = chunk_mb * 1024 * 1024  # bytes

    # Retry transient network errors and 5xx
    retry_policy = Retry(
        initial=1.0,          # first retry after 1s
        maximum=32.0,         # cap backoff between attempts
        multiplier=2.0,       # exponential
        deadline=write_timeout_sec + 60,  # internal deadline per attempt
    )

    start_total = time.perf_counter()
    size_bytes = local_path.stat().st_size
    last_err = None

    for attempt in range(1, max_attempts + 1):
        try:
            # timeout here is per HTTP request/chunk, not whole file
            blob.upload_from_filename(
                str(local_path),
                timeout=write_timeout_sec,
                retry=retry_policy,
            )
            dur = time.perf_counter() - start_total
            mbps = (size_bytes / (1024 * 1024)) / dur if dur > 0 else 0.0
            ts = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
            return {
                "timestamp_local": ts,
                "source_path": str(local_path),
                "gcs_uri": f"gs://{bucket_name}/{blob_name}",
                "size_bytes": size_bytes,
                "duration_sec": round(dur, 3),
                "throughput_MBps": round(mbps, 2),
            }
        except Exception as e:
            last_err = e
            if attempt >= max_attempts:
                raise
            # Exponential backoff with jitter
            base = 2 ** (attempt - 1)
            sleep_s = min(30.0, base) + random.uniform(0, 0.5 * min(30.0, base))
            print(f"[RETRY {attempt}/{max_attempts-1}] {local_path} due to: {e}. Sleeping {sleep_s:.1f}s", file=sys.stderr)
            time.sleep(sleep_s)

    # Should not reach here
    raise last_err

def main():
    ap = argparse.ArgumentParser(description="Upload to GCS with per-file time report (robust timeouts/retries)")
    ap.add_argument("source", help="File or directory to upload")
    ap.add_argument("bucket", help="Target bucket name (without gs://)")
    ap.add_argument("--prefix", default="", help="Object key prefix inside the bucket (e.g., 'backup/')")
    ap.add_argument("--workers", type=int, default=4, help="Parallel upload workers (reduce if link is unstable)")
    ap.add_argument("--timeout-sec", type=float, default=900, help="Per-request (per-chunk) timeout, seconds (default 900=15m)")
    ap.add_argument("--chunk-mb", type=int, default=8, help="Resumable chunk size in MiB (default 8; try 8–32 on flaky links)")
    ap.add_argument("--max-attempts", type=int, default=6, help="Total attempts per file (default 6)")
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

    prefix = args.prefix
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    print(f"Uploading {len(files)} file(s) to gs://{args.bucket}/{prefix} ...")
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp_local",
                "source_path",
                "gcs_uri",
                "size_bytes",
                "duration_sec",
                "throughput_MBps",
            ],
        )
        writer.writeheader()

        successes = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {
                ex.submit(
                    upload_one,
                    client,
                    args.bucket,
                    p,
                    prefix,
                    source,
                    args.timeout_sec,
                    args.chunk_mb,
                    args.max_attempts,
                ): p
                for p in files
            }
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
