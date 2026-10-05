# Supplied independent test sources

The original 104 security/load definitions and the retained contract-corrected copy are the same definition set. Four email-malformation expectations were corrected from401to422; original failures are retained in the final case matrix. Copying files or collecting tests is not a new test execution.

Run against a disposable synthetic service only; these tests reset state. After starting Stage4, install pytest and httpx in a virtual environment and use:

```sh
python -m pytest qa/frozen/baseline-adjudicated --target http://127.0.0.1:8080 --case-log cases.jsonl -q
```

`baseline-original` retains the unchanged earlier oracle. `supplemental` and `numeric-original` retain additional frozen probes; some require Playwright and explicit stage-specific flags. Original numeric client limits and resource conditions are documented in the exact product review. Do not infer completion from a collected source file. Executed outcomes are in reports/stage-4/case-matrix-25ade1c.json and the original evidence archive.
