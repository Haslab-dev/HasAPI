#!/usr/bin/env python3
"""
HasAPI Benchmark V2 - Real-world complex scenarios

Tests:
1. JSON serialization (large response)
2. Path parameters
3. Query parameters
4. POST with JSON body
5. Multiple endpoints
"""

import asyncio
import subprocess
import sys
import tempfile
import os
import re
import json

sys.path.insert(0, '.')

FRAMEWORKS = [
    ('HasAPI', 9001),
    ('Starlette', 9002),
    ('FastAPI', 9003),
]

TESTS = [
    ('Simple GET /', '/'),
    ('JSON response', '/json'),
    ('Path params', '/users/12345'),
    ('Query params', '/search?q=hello&limit=10'),
    ('POST JSON', '/items', 'POST', {'name': 'test', 'price': 99.99, 'tags': ['a', 'b']}),
]


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

ITEMS = [
    {{"id": i, "name": f"Item {{i}}", "price": i * 10.5, "tags": ["tag1", "tag2"]}}
    for i in range(100)
]

@app.get("/")
async def index(request):
    return {{"message": "Hello, World!"}}

@app.get("/json")
async def json_response(request):
    return {{
        "items": ITEMS[:20],
        "total": 100,
        "page": 1,
        "metadata": {{"version": "1.0", "server": "hasapi"}}
    }}

@app.get("/users/{{user_id}}")
async def get_user(request):
    user_id = request.path_params.get("user_id")
    return {{
        "id": user_id,
        "name": f"User {{user_id}}",
        "email": f"user{{user_id}}@example.com",
        "profile": {{"bio": "Hello", "avatar": "https://example.com/avatar.png"}}
    }}

@app.get("/search")
async def search(request):
    q = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", "10"))
    return {{
        "query": q,
        "results": [f"Result {{i}} for {{q}}" for i in range(limit)],
        "total": limit
    }}

@app.post("/items")
async def create_item(request):
    body = await request.json()
    return {{"created": True, "item": body, "id": 12345}}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port={port})
'''


def get_starlette_code(port: int) -> str:
    return f'''
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

ITEMS = [
    {{"id": i, "name": f"Item {{i}}", "price": i * 10.5, "tags": ["tag1", "tag2"]}}
    for i in range(100)
]

async def index(request):
    return JSONResponse({{"message": "Hello, World!"}})

async def json_response(request):
    return JSONResponse({{
        "items": ITEMS[:20],
        "total": 100,
        "page": 1,
        "metadata": {{"version": "1.0", "server": "starlette"}}
    }})

async def get_user(request):
    user_id = request.path_params["user_id"]
    return JSONResponse({{
        "id": user_id,
        "name": f"User {{user_id}}",
        "email": f"user{{user_id}}@example.com",
        "profile": {{"bio": "Hello", "avatar": "https://example.com/avatar.png"}}
    }})

async def search(request):
    q = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", "10"))
    return JSONResponse({{
        "query": q,
        "results": [f"Result {{i}} for {{q}}" for i in range(limit)],
        "total": limit
    }})

async def create_item(request):
    body = await request.json()
    return JSONResponse({{"created": True, "item": body, "id": 12345}})

app = Starlette(routes=[
    Route("/", index),
    Route("/json", json_response),
    Route("/users/{{user_id}}", get_user),
    Route("/search", search),
    Route("/items", create_item, methods=["POST"]),
])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={port}, log_level="error")
'''


def get_fastapi_code(port: int) -> str:
    return f'''
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

ITEMS = [
    {{"id": i, "name": f"Item {{i}}", "price": i * 10.5, "tags": ["tag1", "tag2"]}}
    for i in range(100)
]

class Item(BaseModel):
    name: str
    price: float
    tags: List[str] = []

@app.get("/")
async def index():
    return {{"message": "Hello, World!"}}

@app.get("/json")
async def json_response():
    return {{
        "items": ITEMS[:20],
        "total": 100,
        "page": 1,
        "metadata": {{"version": "1.0", "server": "fastapi"}}
    }}

@app.get("/users/{{user_id}}")
async def get_user(user_id: str):
    return {{
        "id": user_id,
        "name": f"User {{user_id}}",
        "email": f"user{{user_id}}@example.com",
        "profile": {{"bio": "Hello", "avatar": "https://example.com/avatar.png"}}
    }}

@app.get("/search")
async def search(q: str = "", limit: int = 10):
    return {{
        "query": q,
        "results": [f"Result {{i}} for {{q}}" for i in range(limit)],
        "total": limit
    }}

@app.post("/items")
async def create_item(item: Item):
    return {{"created": True, "item": item.dict(), "id": 12345}}

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


async def run_wrk(url: str, method: str = 'GET', body: dict = None) -> dict:
    # Warmup
    if method == 'GET':
        subprocess.run(['wrk', '-t', '2', '-c', '10', '-d', '1s', url], capture_output=True)
        result = subprocess.run(
            ['wrk', '-t', '4', '-c', '100', '-d', '5s', '--latency', url],
            capture_output=True, text=True
        )
    else:
        # POST with lua script
        lua_script = f'''
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = '{json.dumps(body)}'
'''
        fd, lua_path = tempfile.mkstemp(suffix='.lua')
        with os.fdopen(fd, 'w') as f:
            f.write(lua_script)
        
        subprocess.run(['wrk', '-t', '2', '-c', '10', '-d', '1s', '-s', lua_path, url], capture_output=True)
        result = subprocess.run(
            ['wrk', '-t', '4', '-c', '100', '-d', '5s', '--latency', '-s', lua_path, url],
            capture_output=True, text=True
        )
        os.unlink(lua_path)
    
    return parse_wrk_output(result.stdout + result.stderr)


async def benchmark_framework(framework: str, port: int) -> dict:
    code = get_server_code(framework, port)
    fd, script_path = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as f:
        f.write(code)
    
    process = None
    results = {}
    
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
        
        base_url = f'http://127.0.0.1:{port}'
        
        for test_name, path, *rest in TESTS:
            method = rest[0] if rest else 'GET'
            body = rest[1] if len(rest) > 1 else None
            url = base_url + path
            
            result = await run_wrk(url, method, body)
            results[test_name] = result
        
        # Calculate average
        total_rps = sum(r['rps'] for r in results.values())
        results['_total'] = total_rps
        
        return results
        
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
    print("\n" + "=" * 70)
    print("  HasAPI Benchmark V2 - Real World Scenarios")
    print("=" * 70)
    print("  Tests: Simple GET, JSON response, Path params, Query params, POST")
    print("  Duration: 5s per test")
    print("  Connections: 100 concurrent")
    print("=" * 70)
    
    all_results = {}
    
    for framework, port in FRAMEWORKS:
        print(f"\n  Benchmarking {framework}...")
        all_results[framework] = await benchmark_framework(framework, port)
        await asyncio.sleep(1)
    
    # Print results per test
    print("\n" + "=" * 70)
    print("  RESULTS BY TEST")
    print("=" * 70)
    
    for test_name, *_ in TESTS:
        print(f"\n  {test_name}:")
        print(f"  {'Framework':<12} {'RPS':>10} {'Avg(ms)':>8} {'P99(ms)':>8}")
        print("  " + "-" * 45)
        
        test_results = []
        for framework in ['HasAPI', 'Starlette', 'FastAPI']:
            if 'error' not in all_results[framework]:
                data = all_results[framework].get(test_name, {})
                test_results.append((framework, data))
        
        test_results.sort(key=lambda x: x[1].get('rps', 0), reverse=True)
        winner_rps = test_results[0][1].get('rps', 1) if test_results else 1
        
        for framework, data in test_results:
            ratio = data.get('rps', 0) / winner_rps if winner_rps else 0
            badge = "🥇" if ratio == 1 else f"({ratio:.2f}x)"
            print(f"  {framework:<12} {data.get('rps', 0):>10,.0f} {data.get('avg', 0):>8.2f} {data.get('p99', 0):>8.2f} {badge}")
    
    # Print total
    print("\n" + "=" * 70)
    print("  TOTAL (Sum of all tests)")
    print("=" * 70)
    print(f"  {'Framework':<12} {'Total RPS':>12}")
    print("  " + "-" * 30)
    
    totals = []
    for framework in ['HasAPI', 'Starlette', 'FastAPI']:
        if 'error' not in all_results[framework]:
            total = all_results[framework].get('_total', 0)
            totals.append((framework, total))
    
    totals.sort(key=lambda x: x[1], reverse=True)
    winner_total = totals[0][1] if totals else 1
    
    for framework, total in totals:
        ratio = total / winner_total if winner_total else 0
        badge = "🥇" if ratio == 1 else f"({ratio:.2f}x)"
        print(f"  {framework:<12} {total:>12,.0f} {badge}")
    
    print("=" * 70)
    
    if totals:
        winner = totals[0]
        print(f"\n  Winner: {winner[0]}")
        for framework, total in totals[1:]:
            if total > 0:
                speedup = winner[1] / total
                print(f"  {speedup:.2f}x faster than {framework}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
