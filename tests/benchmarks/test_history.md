## 1
hy4-mac-002@HY4-MAC-002 benchmarks % python simple_benchmark.py
============================================================
📊 RESULTS COMPARISON
============================================================

| Framework | RPS    | Avg Latency (ms) | Success Rate |
|-----------|--------|------------------|--------------|
| HasAPI  |    734 |             1.36 |       100.0% |
| FastAPI   |   2109 |             0.47 |       100.0% |
| Flask     |   1844 |             0.54 |       100.0% |

🥇 Winner: FastAPI with 2109 requests/second
   HasAPI is 0.35x slower than FastAPI
   HasAPI is 0.40x slower than Flask

🧹 Cleaning up...
✅ Done!

## 2

hy4-mac-002@HY4-MAC-002 benchmarks % python simple_benchmark.py
🚀 HasAPI vs FastAPI vs Flask Benchmark
============================================================

Creating test applications...
✅ Test apps created

============================================================
Testing HasAPI
============================================================
Starting HasAPI server...
✅ HasAPI is ready
Running benchmark (5000 requests, 50 concurrent)...
  Successful: 5000/5000
  Failed: 0
  Total time: 2.25s
  Requests/sec: 2226
  Avg latency: 0.45ms

============================================================
Testing FastAPI
============================================================
Starting FastAPI server...
✅ FastAPI is ready
Running benchmark (5000 requests, 50 concurrent)...
  Successful: 5000/5000
  Failed: 0
  Total time: 6.56s
  Requests/sec: 762
  Avg latency: 1.31ms

============================================================
Testing Flask
============================================================
Starting Flask server...
✅ Flask is ready
Running benchmark (5000 requests, 50 concurrent)...
  Successful: 5000/5000
  Failed: 0
  Total time: 2.45s
  Requests/sec: 2040
  Avg latency: 0.49ms

============================================================
📊 RESULTS COMPARISON
============================================================

| Framework | RPS    | Avg Latency (ms) | Success Rate |
|-----------|--------|------------------|--------------|
| HasAPI  |   2226 |             0.45 |       100.0% |
| FastAPI   |    762 |             1.31 |       100.0% |
| Flask     |   2040 |             0.49 |       100.0% |

🥇 Winner: HasAPI with 2226 requests/second
   HasAPI is 2.92x faster than FastAPI
   HasAPI is 1.09x faster than Flask

🧹 Cleaning up...
✅ Done!