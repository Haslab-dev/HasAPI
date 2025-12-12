"""
Simple benchmark comparing HasAPI, FastAPI, and Flask
"""
import subprocess
import time
import httpx
import asyncio
from pathlib import Path


def create_test_apps():
    """Create test applications"""
    
    # HasAPI app
    hasapi_code = '''
import sys
sys.path.insert(0, '..')
from hasapi import HasAPI, JSONResponse

app = HasAPI(title="Benchmark", docs=False)

@app.get("/")
async def root(request):
    return JSONResponse({"message": "Hello from HasAPI"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
'''
    
    fastapi_code = '''
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None)

@app.get("/")
async def root():
    return JSONResponse({"message": "Hello from FastAPI"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error")
'''
    
    flask_code = '''
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def root():
    return jsonify({"message": "Hello from Flask"})

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="127.0.0.1", port=8003)
'''
    
    Path('_hasapi_test.py').write_text(hasapi_code)
    Path('_fastapi_test.py').write_text(fastapi_code)
    Path('_flask_test.py').write_text(flask_code)


async def benchmark_endpoint(url: str, num_requests: int = 5000, concurrency: int = 50):
    """Benchmark an endpoint"""
    async with httpx.AsyncClient() as client:
        start_time = time.perf_counter()
        
        successful = 0
        failed = 0
        
        async def make_request():
            nonlocal successful, failed
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    successful += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        
        # Run requests in batches
        for i in range(0, num_requests, concurrency):
            batch_size = min(concurrency, num_requests - i)
            tasks = [make_request() for _ in range(batch_size)]
            await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        return {
            'successful': successful,
            'failed': failed,
            'total_time': elapsed,
            'rps': successful / elapsed if elapsed > 0 else 0,
            'avg_latency': (elapsed / successful * 1000) if successful > 0 else 0
        }


def test_framework(name: str, port: int, script: str):
    """Test a framework"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    
    # Start server
    print(f"Starting {name} server...")
    process = subprocess.Popen(
        ['python', script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Check if server is running
    try:
        response = httpx.get(f'http://127.0.0.1:{port}/', timeout=5.0)
        if response.status_code == 200:
            print(f"✅ {name} is ready")
        else:
            print(f"❌ {name} returned status {response.status_code}")
            process.terminate()
            return None
    except Exception as e:
        print(f"❌ {name} failed to start: {e}")
        process.terminate()
        return None
    
    # Run benchmark
    print(f"Running benchmark (5000 requests, 50 concurrent)...")
    result = asyncio.run(benchmark_endpoint(f'http://127.0.0.1:{port}/'))
    
    print(f"  Successful: {result['successful']}/5000")
    print(f"  Failed: {result['failed']}")
    print(f"  Total time: {result['total_time']:.2f}s")
    print(f"  RPS: {result['rps']:.0f}")
    print(f"  Avg latency: {result['avg_latency']:.2f}ms")
    
    # Stop server
    process.terminate()
    process.wait()
    
    return result


def main():
    print("🚀 HasAPI vs FastAPI vs Flask Benchmark")
    print("="*60)
    
    # Create test apps
    create_test_apps()
    
    # Check dependencies
    try:
        import httpx
        import uvicorn
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install httpx uvicorn")
        return
    
    # Run benchmarks
    results = {}
    results['HasAPI'] = test_framework('HasAPI', 8001, '_hasapi_test.py')
    results['FastAPI'] = test_framework('FastAPI', 8002, '_fastapi_test.py')
    results['Flask'] = test_framework('Flask', 8003, '_flask_test.py')
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Results Summary")
    print("="*60)
    
    valid_results = {k: v for k, v in results.items() if v is not None}
    
    if valid_results:
        print("\n| Framework | RPS    | Avg Latency (ms) | Success Rate |")
        print("|-----------|--------|------------------|--------------|")
        
        for name, result in valid_results.items():
            success_rate = result['successful'] / 5000 * 100
            print(f"| {name:9} | {result['rps']:6.0f} | {result['avg_latency']:16.2f} | {success_rate:11.1f}% |")
        
        # Find winner
        winner = max(valid_results.items(), key=lambda x: x[1]['rps'])
        print(f"\n🥇 Winner: {winner[0]} with {winner[1]['rps']:.0f} requests/second")
        
        # Calculate speedup
        if 'HasAPI' in valid_results and 'FastAPI' in valid_results:
            speedup = valid_results['HasAPI']['rps'] / valid_results['FastAPI']['rps']
            print(f"   HasAPI is {speedup:.2f}x {'faster' if speedup > 1 else 'slower'} than FastAPI")
        
        if 'HasAPI' in valid_results and 'Flask' in valid_results:
            speedup = valid_results['HasAPI']['rps'] / valid_results['Flask']['rps']
            print(f"   HasAPI is {speedup:.2f}x {'faster' if speedup > 1 else 'slower'} than Flask")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    Path('_hasapi_test.py').unlink(missing_ok=True)
    Path('_fastapi_test.py').unlink(missing_ok=True)
    Path('_flask_test.py').unlink(missing_ok=True)
    
    print("Done!")


if __name__ == "__main__":
    main()
