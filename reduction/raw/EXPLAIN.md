# Stage 1 — fetch (raw data imports)

**What:** the EPIC-pn calibrated event lists (`PIEVLI`) and pn flare-background time series
(`FBKTSR`) from the XMM-Newton Processing Pipeline Subsystem (PPS) products for the four
2008 orbits of 1H 0707–495, plus the short extra exposure in orbit 2 (`PNU027`).

**How:** `reduction/fetch_imports.sh` runs `dvc import-url` from the HEASARC S3 mirror
(`https://nasa-heasarc.s3.amazonaws.com/xmm/data/rev0/<ObsID>/PPS/<file>`, anonymous).
Each `*.dvc` file records the source URL, the S3 ETag and size at import time, and the md5 of
the downloaded file. We don't store the raw data. `dvc update <file>.dvc` re-fetches it and
reports if HEASARC's copy has changed.

**Why these files:** they are the starting point of reduction v0 (no SAS needed). The PPS lists
were processed by ESA with SAS 18.0.0 (header `SASVERS = xmmsas_20190401_1820-18.0.0`), *not*
the SAS 8.0.0 used by Fabian et al. 2009 (assumption M-01 in `docs/assumptions.md`).

| ObsID | Exposure | Event list (bytes) | Header DATE-OBS → DATE-END | Mode / filter |
|---|---|---|---|---|
| 0511580101 | PNS001 | 212,214,929 | 2008-01-29T18:57 → 2008-01-31T04:43 | PrimeLargeWindow / Medium |
| 0511580201 | PNS001 | 206,032,824 | 2008-01-31 → 2008-02-02 | PrimeLargeWindow / Medium |
| 0511580201 | PNU027 | 26,542,231 | 2008-02-02T01:39 → 02:34 (3.3 ks) | PrimeLargeWindow / Medium |
| 0511580301 | PNU002 | 226,362,026 | 2008-02-02 → 2008-02-04 | PrimeLargeWindow / Medium |
| 0511580401 | PNU002 | 244,785,334 | 2008-02-04 → 2008-02-06 | PrimeLargeWindow / Medium |

**Checks run (2026-11-19):**
* The file sizes from a fresh S3 listing match the sizes in `docs/pilot-1h0707-lags.md`
  (212, 206, 26.5, 226, 245 MB) and the sizes recorded in the `.dvc` files.
* `dvc status` reported the data and pipelines up to date after import.
* Header keywords (OBJECT = 1H0707-495, INSTRUME = EPN, SUBMODE = PrimeLargeWindow) were inspected for
  0511580101 PNS001 and 0511580201 PNU027.
