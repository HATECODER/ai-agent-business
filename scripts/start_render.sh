#!/bin/sh
set -eu

python scripts/write_streamlit_secrets.py

exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT:-10000}" \
  --server.headless=true \
  --browser.gatherUsageStats=false
