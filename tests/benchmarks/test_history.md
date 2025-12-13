# HasAPI Benchmark History

## Latest Results (Pure Python)

```
🚀 HasAPI Benchmark
======================================================================
   Endpoint: GET /
   Duration: 10s per framework
   Connections: 100 concurrent
======================================================================

Framework             RPS   Avg (ms)   P50 (ms)   P99 (ms)
----------------------------------------------------------------------
HasAPI             80,816       1.22       1.02       2.10 🥇
FastAPI            21,801       4.95       4.49      21.75 (0.27x)
======================================================================

🏆 Winner: HasAPI with 80,816 req/sec
   3.71x faster than FastAPI
```

## Previous Experiments

### Native Engine Tests (Bun IPC - Deprecated)

```
Framework                RPS   Avg (ms)   P50 (ms)   P99 (ms)   Errors
--------------------------------------------------------------------------------
HasAPI (python)       80,926       1.22       1.01       2.10        0 
HasAPI (native-v3)    65,849       1.49       1.40       2.52        0 (0.81x)
HasAPI (native-v2)    56,757       1.53       1.17       5.11        0 (0.70x)
```

**Conclusion:** Native Bun IPC adds overhead. Pure Python (uvloop + httptools) is faster.

### Gateway Tests (Bun Proxy - Deprecated)

```
Test                                  RPS   Avg (ms)   P99 (ms)   Errors
----------------------------------------------------------------------
Python Direct (8000)               78,705       1.28       2.53        0
Python + Gateway (8080)            13,925      12.51      71.23    35349
Gateway Static /health            103,541       0.87       1.66       10
```

**Conclusion:** Gateway adds 82% overhead for proxied requests. Only useful for static routes.

### Pure Bun Tests (No Python - Not a Python Framework)

```
Framework                RPS   Avg (ms)   P50 (ms)   P99 (ms)   Errors
--------------------------------------------------------------------------------
HasAPI (pure-bun)    106,963       0.93       0.90       1.79  1080443 
HasAPI (python)       82,325       1.27       0.96       2.02        0
```

**Conclusion:** Pure Bun is fastest but has errors and loses Python compatibility.

## Final Architecture Decision

**Use pure Python engine (uvloop + httptools + orjson)**

- 80k+ RPS
- Full pip compatibility
- No IPC overhead
- Production ready

Bun experiments removed. Focus on Python performance.

(venv) hy4-mac-002@HY4-MAC-002 quickapi-py % source venv/bin/activate && python tests/benchmarks/benchmark.py

=================================================================
  HasAPI Benchmark
=================================================================
  Endpoint: GET /
  Duration: 10s per framework
  Connections: 100 concurrent
=================================================================

  Benchmarking HasAPI...

  Benchmarking Starlette...

  Benchmarking FastAPI...

=================================================================
  RESULTS
=================================================================
  Framework           RPS  Avg(ms)  P50(ms)  P99(ms)
  -------------------------------------------------------------
  HasAPI           80,647     1.23     1.06     2.16 🥇
  Starlette        35,314     3.23     2.71    20.49 (0.44x)
  FastAPI          17,173     7.40     4.83    49.71 (0.21x)
=================================================================

  Winner: HasAPI with 80,647 req/sec
  2.28x faster than Starlette
  4.70x faster than FastAPI
