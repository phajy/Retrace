#!/usr/bin/env python3
"""Content hashes of FITS binary tables: compare data, not file bytes.

FITS headers can carry timestamps and software versions, so two files holding identical data
can differ byte for byte. This tool reads a FITS file back and hashes each column of each binary
table: sha256 of the column's values as a contiguous big-endian array of its own dtype (after
FITS scaling such as TZERO is applied).

Used by the filter and lightcurves stages, which write the hashes to git-tracked
`content_hashes.json` files. Verifiers can recompute them for any file:

    python tools/fits_hashes.py reduction/filter/output/*.fits
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits


def column_hash(values) -> str:
    """sha256 of the values in a canonical (contiguous, big-endian) layout."""
    arr = np.asarray(values)
    arr = np.ascontiguousarray(arr.astype(arr.dtype.newbyteorder(">")))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def file_hashes(path: str | Path) -> dict:
    """{HDU name: {column name: sha256}} for every binary table in the file, in file order."""
    with fits.open(path) as hdul:
        return {hdu.name: {c: column_hash(hdu.data[c]) for c in hdu.columns.names}
                for hdu in hdul if isinstance(hdu, fits.BinTableHDU)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps({Path(p).name: file_hashes(p) for p in sys.argv[1:]}, indent=2))
