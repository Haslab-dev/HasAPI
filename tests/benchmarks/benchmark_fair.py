#!/usr/bin/env python3
"""
HasAPI Fair Benchmark - Same conditions for all frameworks

- Each framework tested separately
- 5 second cooldown between frameworks
- Process fully killed and cleaned up
- Same test repeated 3 times, take average
"""

import asyncio
import subprocess
import sys
import tempfile
import os
import re
import time
import gc

sys.path.insert(0, '.')

FRAMEWORKS = [
    ('HasAPI', 9001),
    ('Starlette', 9002),
    ('FastAPI', 9003),
]

COOLDOWN = 5  # seconds between tests
RUNS = 3  # number of runs per framework


def parse_wrk_output(output: str) -> dict:
    result = {'rps': 0, 'avg': 0, 'p50': 0, 'p99': 0}
    for line in output.split('\n'):
        line = line.strip()
        if 'Requests/sec:' in line:
            result['rps'] = float(line.split(':')[1].strip())
        elif line.startswith('Latency') and 'Distribution' not in line:
            parts = line.split()
            if len(parts) >= 2:
                val = parts[1]
                if val.endswith('us'):
                    result['avg'] = float(val[:-2]) / 1000
                elif val.endswith('ms'):
                    result['avg'] = float(val[:-2])
        elif line.startswith('50%'):
            val = line.split()[1]
            if val.endswith('us'):
                result['p50'] = float(val[:-2]) / 1000
            elif val.endswith('ms'):
                result['p50'] = float(val[:-2])
        elif line.startswith('99%'):
            val = line.split()[1]
            if val.endswith('us'):
                result['p99'] = float(val[:-2]) / 1000
            elif val.endswith('ms'):
                result['p99'] = float(val[:-2])
    return result


def get_hasapi_code(port: int) -> str:
    return f'''
import sys
sys.path.insert(0, '.')
from hasapi import HasAPI
app = HasAPI(docs=False)
@app.get("/")
async def index(request):
    return {{"message": "Hello, World!"}}
if __name__ == "__main__":
    app.run(host="127.0.0.1", port={port})
'''


def get_starlette_code(port: int) -> str:
    return f'''
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
async def index(request):
    return JSONResponse({{"message": "Hello, World!"}})
app = Starlette(routes=[Route("/", index)])
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={port}, log_level="error")
'''


def get_fastapi_code(port: int) -> str:
    return f'''
from fastapi import FastAPI
import uvicorn
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
@app.get("/")
async def index():
    return {{"message": "Hello, World!"}}
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={port}, log_level="error")
'''


def get_server_code(framework: str, port: int) -> str:
    if framework == 'HasAPI':
        return get_hasapi_code(port)
    elif framework == 'Starlette':
        return get_starlette_code(port)
    elif framework == 'FastAPI':
        return get_fastapi_code(port)
    return ''


def cleanup():
    """Force cleanup"""
    gc.collect()
    time.sleep(0.5)


async def single_benchmark(framework: str, port: int, run_num: int) -> dict:
    """Run single benchmark for one framework"""
    code = get_server_code(framework, port)
    fd, script_path = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as f:
        f.write(code)
    
    process = None
    try:
        # Start server
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to be ready
        await asyncio.sleep(2)
        
        if process.poll() is not None:
            stderr = process.stderr.read().decode()
            return {'error': stderr[:80]}
        
        url = f'http://127.0.0.1:{port}/'
        
        # Warmup
        subprocess.run(
            ['wrk', '-t', '2', '-c', '10', '-d', '2s', url],
            capture_output=True
        )
        
        # Actual benchmark
        result = subprocess.run(
            ['wrk', '-t', '4', '-c', '100', '-d', '10s', '--latency', url],
            capture_output=True, text=True
        )
        
        return parse_wrk_output(result.stdout + result.stderr)
        
    finally:
        # Kill process completely
        if process:
            process.terminate()
            try:
                process.wait(timeout=3)
            except:
                process.kill()
                process.wait()
        
        # Remove temp file
        try:
            os.unlink(script_path)
        except:
            pass
        
        # Force cleanup
        cleanup()


async def main():
    print("\n" + "=" * 65)
    print("  HasAPI Fair Benchmark")
    print("=" * 65)
    print(f"  Runs per framework: {RUNS}")
    print(f"  Cooldown between tests: {COOLDOWN}s")
    print("  Duration: 10s per run")
    print("  Connections: 100 concurrent")
    print("=" * 65)
    
    all_results = {f: [] for f, _ in FRAMEWORKS}
    
    for run in range(1, RUNS + 1):
        print(f"\n  === Run {run}/{RUNS} ===")
        
        for framework, port in FRAMEWORKS:
            print(f"\n  [{framework}] Starting benchmark...")
            
            result = await single_benchmark(framework, port, run)
            all_results[framework].append(result)
            
            if 'error' in result:
                print(f"  [{framework}] ERROR: {result['error']}")
            else:
                print(f"  [{framework}] {result['rps']:,.0f} RPS, {result['avg']:.2f}ms avg")
            
            # Cooldown
            print(f"  Cooling down {COOLDOWN}s...")
            await asyncio.sleep(COOLDOWN)
    
    # Calculate averages
    print("\n" + "=" * 65)
    print("  RESULTS (Average of {} runs)".format(RUNS))
    print("=" * 65)
    print(f"  {'Framework':<12} {'Avg RPS':>10} {'Best RPS':>10} {'Avg(ms)':>8} {'P99(ms)':>8}")
    print("  " + "-" * 55)
    
    averages = []
    for framework, _ in FRAMEWORKS:
        results = [r for r in all_results[framework] if 'error' not in r]
        if results:
            avg_rps = sum(r['rps'] for r in results) / len(results)
            best_rps = max(r['rps'] for r in results)
            avg_latency = sum(r['avg'] for r in results) / len(results)
            avg_p99 = sum(r['p99'] for r in results) / len(results)
            averages.append((framework, avg_rps, best_rps, avg_latency, avg_p99))
    
    averages.sort(key=lambda x: x[1], reverse=True)
    winner_rps = averages[0][1] if averages else 1
    
    for framework, avg_rps, best_rps, avg_latency, avg_p99 in averages:
        ratio = avg_rps / winner_rps
        badge = "🥇" if ratio == 1 else f"({ratio:.2f}x)"
        print(f"  {framework:<12} {avg_rps:>10,.0f} {best_rps:>10,.0f} {avg_latency:>8.2f} {avg_p99:>8.2f} {badge}")
    
    print("=" * 65)
    
    if averages:
        winner = averages[0]
        print(f"\n  Winner: {winner[0]} with {winner[1]:,.0f} avg RPS")
        for framework, avg_rps, *_ in averages[1:]:
            if avg_rps > 0:
                speedup = winner[1] / avg_rps
                print(f"  {speedup:.2f}x faster than {framework}")
    
    # Show all runs
    print("\n  Individual runs:")
    for framework, _ in FRAMEWORKS:
        runs = [r.get('rps', 0) for r in all_results[framework] if 'error' not in r]
        if runs:
            print(f"  {framework}: {', '.join(f'{r:,.0f}' for r in runs)}")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())
