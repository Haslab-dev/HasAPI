#!/usr/bin/env python3
"""
HasAPI Benchmark Runner

Compare HasAPI vs FastAPI vs Express.js performance.

Requirements:
- wrk or hey (HTTP benchmarking tool)
- FastAPI (pip install fastapi)
- Express.js (npm install express) - optional

Usage:
    python examples/run_benchmark.py
    python examples/run_benchmark.py --endpoint /json
    python examples/run_benchmark.py --duration 30 --connections 200
"""

import sys
sys.path.insert(0, '.')

from hasapi.benchmarks import run_benchmarks


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='HasAPI Benchmark - Compare HasAPI vs FastAPI vs Express.js'
    )
    
    parser.add_argument(
        '-e', '--endpoint',
        default='/',
        help='API endpoint to benchmark (default: /)'
    )
    
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=10,
        help='Benchmark duration in seconds (default: 10)'
    )
    
    parser.add_argument(
        '-c', '--connections',
        type=int,
        default=100,
        help='Number of concurrent connections (default: 100)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for JSON results'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Benchmark /json endpoint (complex JSON response)'
    )
    
    args = parser.parse_args()
    
    endpoint = '/json' if args.json else args.endpoint
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                  HasAPI Benchmark Suite                       ║
║         Compare HasAPI vs FastAPI vs Express.js               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    run_benchmarks(
        endpoint=endpoint,
        duration=args.duration,
        connections=args.connections,
        output=args.output
    )
