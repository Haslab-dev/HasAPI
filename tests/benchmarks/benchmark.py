#!/usr/bin/env python3
"""
HasAPI Benchmark - Compare with Starlette and FastAPI
"""

import asyncio
import subprocess
import sys
import tempfile
import os
import re

sys.path.insert(0, '.')

FRAMEWORKS = [
    ('HasAPI', 8001),
    ('Starlette', 8002),
    ('FastAPI', 8003),
]


def parse_wrk_output(output: str) -> dict:
    result = {'rps': 0, 'avg': 0, 'p50': 0, 'p99': 0, 'errors': 0}
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
                elif val.endswith('s'):
                    result['avg'] = float(val[:-1]) * 1000
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
        elif 'Socket errors' in line or 'Non-2xx' in line:
            nums = re.findall(r'\d+', line)
            result['errors'] = sum(int(n) for n in nums)
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


async def benchmark_framework(framework: str, port: int) -> dict:
    code = get_server_code(framework, port)
    fd, script_path = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as f:
        f.write(code)
    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await asyncio.sleep(3)
        if process.poll() is not None:
            stderr = process.stderr.read().decode()
            return {'error': stderr[:80]}
        url = f'http://127.0.0.1:{port}/'
        subprocess.run(['wrk', '-t', '2', '-c', '10', '-d', '2s', url], capture_output=True)
        result = subprocess.run(
            ['wrk', '-t', '4', '-c', '100', '-d', '10s', '--latency', url],
            capture_output=True, text=True
        )
        return parse_wrk_output(result.stdout + result.stderr)
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
        try:
            os.unlink(script_path)
        except:
            pass


async def main():
    print("\n" + "=" * 65)
    print("  HasAPI Benchmark")
    print("=" * 65)
    print("  Endpoint: GET /")
    print("  Duration: 10s per framework")
    print("  Connections: 100 concurrent")
    print("=" * 65)
    
    results = {}
    for framework, port in FRAMEWORKS:
        print(f"\n  Benchmarking {framework}...")
        results[framework] = await benchmark_framework(framework, port)
        await asyncio.sleep(1)
    
    print("\n" + "=" * 65)
    print("  RESULTS")
    print("=" * 65)
    print(f"  {'Framework':<12} {'RPS':>10} {'Avg(ms)':>8} {'P50(ms)':>8} {'P99(ms)':>8}")
    print("  " + "-" * 61)
    
    valid = [(k, v) for k, v in results.items() if 'error' not in v]
    sorted_results = sorted(valid, key=lambda x: x[1].get('rps', 0), reverse=True)
    winner_rps = sorted_results[0][1].get('rps', 1) if sorted_results else 1
    
    for framework, data in sorted_results:
        ratio = data['rps'] / winner_rps
        badge = "🥇" if ratio == 1 else f"({ratio:.2f}x)"
        print(f"  {framework:<12} {data['rps']:>10,.0f} {data['avg']:>8.2f} {data['p50']:>8.2f} {data['p99']:>8.2f} {badge}")
    
    for framework, data in results.items():
        if 'error' in data:
            print(f"  {framework:<12} ERROR: {data['error'][:50]}")
    
    print("=" * 65)
    
    if sorted_results:
        winner = sorted_results[0]
        print(f"\n  Winner: {winner[0]} with {winner[1]['rps']:,.0f} req/sec")
        for framework, data in sorted_results[1:]:
            if data['rps'] > 0:
                speedup = winner[1]['rps'] / data['rps']
                print(f"  {speedup:.2f}x faster than {framework}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
