#!/usr/bin/env bash
# Usage: ./run_all.sh [path/to/real/train.csv]   (omit the argument to use the synthetic sample)
set -e; cd "$(dirname "$0")"
[ -z "$1" ] && python python/01_generate_synthetic.py
python python/02_load_db.py ${1:-data/sample_expedia.csv}
python python/03_analysis.py
Rscript r/04_position_model.R || echo "R step skipped (R not installed)"
