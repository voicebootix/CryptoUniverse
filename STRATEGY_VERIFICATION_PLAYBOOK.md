# Strategy Verification Playbook

The opportunity discovery feature relies on fourteen trading strategies.  To
confirm that each strategy is operational after a code change or deployment,
run the automated diagnostic helper that ships with this repository.

## Quick start

```bash
python tools/run_strategy_diagnostics.py --user-id admin-audit
```

The command executes every strategy that feeds the opportunity scanner and
prints a table summarizing success/failure details.  A non-zero exit status
indicates that at least one strategy reported an error.

### JSON output

To capture machine-readable evidence for incident reports use:

```bash
python tools/run_strategy_diagnostics.py --json > diagnostics.json
```

## Simulation mode

If you need to validate orchestration logic without calling real market-data
providers (for example, inside continuous integration) append the
`--simulation` flag.  This preserves the execution flow while making it clear
in the report that live pricing was not requested.

```bash
python tools/run_strategy_diagnostics.py --simulation
```

## Continuous integration

The diagnostics runner is covered by `tests/tools/test_strategy_diagnostics.py`.
Running `pytest` locally or in CI verifies the wiring, expected strategy set,
and reporting format.

## Operational checklist

1. Run the diagnostics helper in the target environment.
2. Inspect the output for any ❌ rows and review the accompanying error column.
3. Optionally re-run with `--json` and archive the report for audit trails.
4. Once all strategies return ✅, initiate the standard opportunity discovery
   workflow to ensure the chat layer surfaces the new signals.
