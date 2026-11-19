## What this changes

## Results and issues affected
<!-- e.g. "Changes R1 (baseline lags). Refs the check-request issue it answers." -->

## Checklist
- [ ] `dvc repro` has been run, `dvc.lock` is committed and `dvc status` is clean
- [ ] Every new analysis choice has an assumption ID in `docs/assumptions.md` and `params.yaml`
- [ ] The `EXPLAIN.md` of each changed stage says what changed, why, and which checks were run
- [ ] Nothing was tuned to match the published values
- [ ] Failed attempts are recorded in `docs/LOG.md`
- [ ] The score sheet changes only for checks that were actually run, and names them
