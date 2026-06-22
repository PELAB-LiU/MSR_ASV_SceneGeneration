"""Create a small bundled sample from main_measurements.pkl.gz for kick-the-tires."""

from __future__ import annotations

import gzip
import pickle
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "MODELS26_measurements" / "main_measurements.pkl.gz"
OUT_DIR = REPO_ROOT / "artifact_sample_data"
MAX_RECORDS = 40


def main() -> int:
    if not SRC.is_file():
        print(f"Source not found: {SRC}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(SRC, "rb") as handle:
        eval_datas = pickle.load(handle)
    sample = eval_datas[:MAX_RECORDS]
    out_pkl = OUT_DIR / "main_measurements.pkl.gz"
    with gzip.open(out_pkl, "wb") as handle:
        pickle.dump(sample, handle, protocol=pickle.HIGHEST_PROTOCOL)
    summary_src = REPO_ROOT / "MODELS26_measurements" / "measurement_result_summary"
    summary_dst = OUT_DIR / "measurement_result_summary"
    if summary_src.is_dir():
        if summary_dst.exists():
            shutil.rmtree(summary_dst)
        shutil.copytree(summary_src, summary_dst)
    print(f"Wrote {len(sample)} records to {out_pkl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
