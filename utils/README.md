# Sempl-it Stress Test Utilities

This directory contains Python utilities used to test the performance and concurrency behavior of the Sempl-it backend. The scripts target a backend running locally at `http://localhost:30010` and use `httpx` for HTTP requests.

## Requirements

- Python 3.10+
- `httpx`
- Sempl-it backend running on port `30010`

Install the dependency with:

```bash
pip install httpx
```

CSV-based tests use `sempl_it_test_texts.csv` by default. The CSV must contain a `testo` column, and input texts must not exceed 4,000 characters.

## Tests

### `simplify_stress_test.py`

Sends multiple simultaneous requests to the Simplify endpoint using the same built-in test document for every request. It reports successes, failures, total execution time, and minimum, maximum, and average duration.

```bash
python simplify_stress_test.py 10
```

The argument is the number of simultaneous requests.

### `simplify_stress_test_csv.py`

Sends simultaneous Simplify requests using different documents from a CSV file. It supports up to 100 requests and validates all selected inputs before starting.

The script writes the nine simplification-step outputs, HTTP status, and duration back to the CSV.

```bash
python simplify_stress_test_csv.py 100
```

Custom dataset:

```bash
python simplify_stress_test_csv.py 100 --csv path/to/dataset.csv
```

**Note:** this test modifies the CSV by adding or updating result columns.

### `analyze_stress_test.py`

Sends multiple simultaneous requests to the Analyze endpoint using the same built-in document for every request. It reports successes, failures, total time, and minimum, maximum, and average duration.

```bash
python analyze_stress_test.py 10
```

### `compare_stress_test.py`

Sends multiple simultaneous requests to the Compare endpoint using the same built-in pair of reference and simplified texts. It reports successes, failures, total time, and minimum, maximum, and average duration.

```bash
python compare_stress_test.py 10
```

### `realistic_mixed_traffic_csv.py`

Simulates a more realistic mixed workload across Simplify, Analyze, and Compare.

Requests arrive at random intervals instead of starting simultaneously. The operation type and CSV input rows are selected randomly; Compare uses two distinct rows. The CSV is **read-only** and is not modified.

The output includes the request mix, individual start/end times, peak concurrent requests, total session duration, arrival statistics, per-function timings, and failures.

```bash
python realistic_mixed_traffic_csv.py 20
```

For a reproducible run:

```bash
python realistic_mixed_traffic_csv.py 20 --seed 1
```

Custom arrival interval:

```bash
python realistic_mixed_traffic_csv.py 20 --min-interval 1 --max-interval 60 --seed 1
```

Custom dataset:

```bash
python realistic_mixed_traffic_csv.py 20 --csv path/to/dataset.csv --seed 1
```

The positional argument is the **total number of operations across all three functions**. The exact Simplify/Analyze/Compare mix is randomly generated.

## Which test should I use?

Use the individual stress tests to deliberately create simultaneous load on a specific endpoint. Use `simplify_stress_test_csv.py` to stress Simplify with heterogeneous documents.

Use `realistic_mixed_traffic_csv.py` to observe the backend under mixed, intermittent traffic that is closer to normal application usage rather than a worst-case simultaneous burst.

## Notes

All scripts use a request timeout of 1,200 seconds so long-running performance tests can complete.

These utilities are intended for controlled performance testing. High-concurrency tests should only be run against environments where generating the requested load is appropriate.
