#!/usr/bin/env bash
# Stage 1 (fetch): import the XMM-Newton EPIC-pn PPS products from HEASARC with
# `dvc import-url`, so each .dvc file records the source URL, the S3 ETag and the
# md5 of what we downloaded. We do NOT store raw data ourselves.
#
# Re-running this script on a fresh clone is not needed: `dvc pull` (from a remote)
# or `dvc update reduction/raw/*/*.dvc` re-fetches from HEASARC and checks hashes.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="https://nasa-heasarc.s3.amazonaws.com/xmm/data/rev0"

# ObsID  exposure-id  (calibrated pn event list + pn flare-background time series)
FILES=(
  "0511580101 PNS001"
  "0511580201 PNS001"
  "0511580201 PNU027"   # short extra exposure; fetched so the include/exclude decision is testable
  "0511580301 PNU002"
  "0511580401 PNU002"
)

for entry in "${FILES[@]}"; do
  read -r obs expo <<<"$entry"
  mkdir -p "reduction/raw/$obs"
  for kind in FBKTSR PIEVLI; do
    f="P${obs}${expo}${kind}0000.FTZ"
    out="reduction/raw/$obs/$f"
    if [[ -f "$out.dvc" ]]; then
      echo "skip (already imported): $out"
      continue
    fi
    echo "importing $f"
    dvc import-url "$BASE/$obs/PPS/$f" "$out"
  done
done
