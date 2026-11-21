# Environment

Captured 2026-11-21T12:21:47Z UTC.

* macOS `sw_vers`: 26.7.3 (build 25G342)
* Kernel reported during setup: Darwin 25.6.0, arm64
* Architecture: arm64
* Python: 3.15.2
* DVC: 3.67.1

Independent virtual environment:

```text
astropy==8.0.3
astropy-iers-data==0.2026.11.16.0.37.44
contourpy==1.4.0
cycler==0.12.1
fonttools==4.68.0
kiwisolver==1.5.1
matplotlib==3.11.2
numpy==2.5.5
packaging==26.3
pillow==13.0.0
pyerfa==2.0.1.5
pyparsing==3.3.3
python-dateutil==4.0.0
PyYAML==6.0.4
scipy==1.18.1
stingray==2.3.2
tzdata==2026.6
```

The first sandboxed `pip freeze` failed because pip tried to scan a HEASoft
Python directory outside the sandbox. Repeating only the inventory command
outside the sandbox succeeded.
