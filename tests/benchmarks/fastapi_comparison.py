"""
HasAPI vs FastAPI Performance Comparison

Benchmark comparison between HasAPI and FastAPI frameworks.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any

# Mock ASGI environment for testing
class MockASGIEnv:
    """Mock ASGI environment for testing"""
    
    def __init__(self):
        self.received = []
        self.sent = []
    
    async def receive(self):
        """Mock receive callable"""
        if not self.received:
            return {"type": "http.request", "body": b"", "more_body": False}
        else:
            return self.received.pop(0)
    
    async def send(self, message):
        """Mock send callable"""
        self.sent.append(message)


def run_benchmark(test_name: str, test_func, iterations: int = 1000) -> Dict[str, Any]:
    """Run a benchmark test"""
    print(f"Running {test_name}...")
    
    times = []
    
    for i in range(iterations):
        start_time = time.perf_counter()
        asyncio.run(test_func())
        end_time = time.perf_counter()
        
        elapsed = (end_time - start_time) * 1000  # Convert to milliseconds
        times.append(elapsed)
        
        if (i + 1) % 100 == 0:
            progress = (i + 1) / iterations * 100
            print(f"Progress: {progress:.0f}%")
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    p95_time = sorted(times)[int(iterations * 0.95)]
    
    result = {
        "test_name": test_name,
        "iterations": iterations,
        "avg_ms": avg_time,
        "min_ms": min_time,
        "max_ms": max_time,
        "median_ms": median_time,
        "p95_ms": p95_time,
        "requests_per_second": 1000 / (avg_time / 1000) if avg_time > 0 else 0
    }
    
    print(f"✅ {test_name} completed")
    print(f"   Average: {avg_time:.2f}ms")
    print(f"   Median: {median_time:.2f}ms")
    print(f"   95th percentile: {p95_time:.2f}ms")
    print(f"   RPS: {result['requests_per_second']:.0f}")
    print()
    
    return result


async def test_hasapi_hello():
    """Test HasAPI hello world"""
    from hasapi import HasAPI, JSONResponse
    
    app = HasAPI()
    
    @app.get("/")
    async def hello(request):
        return JSONResponse({"message": "Hello World"})
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 8000)
    }
    
    env = MockASGIEnv()
    await app(scope, env.receive, env.send)


async def test_fastapi_hello():
    """Test FastAPI hello world"""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    
    @app.get("/")
    async def hello():
        return JSONResponse({"message": "Hello World"})
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
        "root_path": "",
        "http_version": "1.1",
    }
    
    env = MockASGIEnv()
    await app(scope, env.receive, env.send)


async def test_hasapi_json():
    """Test HasAPI JSON response"""
    from hasapi import HasAPI, JSONResponse
    
    app = HasAPI()
    
    @app.get("/data")
    async def get_data(request):
        return JSONResponse({
            "users": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
                {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
            ],
            "total": 3,
            "page": 1
        })
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/data",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 8000)
    }
    
    env = MockASGIEnv()
    await app(scope, env.receive, env.send)


async def test_fastapi_json():
    """Test FastAPI JSON response"""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    
    @app.get("/data")
    async def get_data():
        return JSONResponse({
            "users": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
                {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
            ],
            "total": 3,
            "page": 1
        })
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/data",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
        "root_path": "",
        "http_version": "1.1",
    }
    
    env = MockASGIEnv()
    await app(scope, env.receive, env.send)


def run_comparison():
    """Run comparison benchmarks"""
    print("🚀 HasAPI vs FastAPI Performance Comparison")
    print("=" * 60)
    print()
    
    results = {}
    
    # HasAPI benchmarks
    print("📦 HasAPI Benchmarks")
    print("-" * 60)
    results['hasapi_hello'] = run_benchmark("HasAPI Hello World", test_hasapi_hello, iterations=500)
    results['hasapi_json'] = run_benchmark("HasAPI JSON Response", test_hasapi_json, iterations=500)
    
    # FastAPI benchmarks
    print("📦 FastAPI Benchmarks")
    print("-" * 60)
    results['fastapi_hello'] = run_benchmark("FastAPI Hello World", test_fastapi_hello, iterations=500)
    results['fastapi_json'] = run_benchmark("FastAPI JSON Response", test_fastapi_json, iterations=500)
    
    # Comparison
    print("=" * 60)
    print("📊 Performance Comparison")
    print("=" * 60)
    print()
    
    print("Hello World Endpoint:")
    hasapi_hello_avg = results['hasapi_hello']['avg_ms']
    fastapi_hello_avg = results['fastapi_hello']['avg_ms']
    speedup = fastapi_hello_avg / hasapi_hello_avg if hasapi_hello_avg > 0 else 0
    print(f"  HasAPI: {hasapi_hello_avg:.2f}ms")
    print(f"  FastAPI:  {fastapi_hello_avg:.2f}ms")
    print(f"  Speedup:  {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
    print()
    
    print("JSON Response Endpoint:")
    hasapi_json_avg = results['hasapi_json']['avg_ms']
    fastapi_json_avg = results['fastapi_json']['avg_ms']
    speedup = fastapi_json_avg / hasapi_json_avg if hasapi_json_avg > 0 else 0
    print(f"  HasAPI: {hasapi_json_avg:.2f}ms")
    print(f"  FastAPI:  {fastapi_json_avg:.2f}ms")
    print(f"  Speedup:  {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
    print()
    
    # Overall winner
    hasapi_total = hasapi_hello_avg + hasapi_json_avg
    fastapi_total = fastapi_hello_avg + fastapi_json_avg
    
    print("Overall Performance:")
    print(f"  HasAPI Total: {hasapi_total:.2f}ms")
    print(f"  FastAPI Total:  {fastapi_total:.2f}ms")
    
    if hasapi_total < fastapi_total:
        speedup = fastapi_total / hasapi_total
        print(f"  🏆 HasAPI is {speedup:.2f}x faster overall!")
    else:
        speedup = hasapi_total / fastapi_total
        print(f"  FastAPI is {speedup:.2f}x faster overall")
    
    print()
    return results


if __name__ == "__main__":
    run_comparison()
