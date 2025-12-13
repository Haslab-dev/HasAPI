"""
HasAPI CLI Tool

Command-line interface for HasAPI development and deployment.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional

from .utils import get_logger

logger = get_logger(__name__)


def create_project(name: str, directory: Optional[str] = None):
    """Create a new HasAPI project"""
    if directory is None:
        directory = name
    
    project_path = Path(directory)
    project_path.mkdir(exist_ok=True)
    
    (project_path / "app.py").write_text(f'''"""
HasAPI Application
"""

from hasapi import HasAPI
from hasapi.middleware import CORSMiddleware

app = HasAPI(title="{name} API", version="1.0.0")
app.middleware(CORSMiddleware(allow_origins=["*"]))

@app.get("/")
async def root():
    return {{"message": "Welcome to {name} API!"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''')
    
    (project_path / "requirements.txt").write_text('''hasapi
uvicorn[standard]
''')
    
    (project_path / "README.md").write_text(f'''# {name}

A HasAPI application.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation.
''')
    
    print(f"✅ Created HasAPI project '{name}' in '{directory}'")
    print(f"📁 To get started:")
    print(f"   cd {directory}")
    print(f"   pip install -r requirements.txt")
    print(f"   python app.py")


def run_server(app_file: str = "app.py", host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the development server"""
    if not os.path.exists(app_file):
        print(f"❌ Error: App file '{app_file}' not found")
        sys.exit(1)
    
    print(f"🚀 Starting HasAPI server on http://{host}:{port}")
    print(f"📚 API docs available at http://{host}:{port}/docs")
    
    cmd = ["uvicorn", f"{app_file.replace('.py', '')}:app", "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd)


def create_dockerfile():
    """Create a Dockerfile for the project"""
    Path("Dockerfile").write_text('''FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
''')
    print("✅ Created Dockerfile")


def create_docker_compose():
    """Create a docker-compose.yml file"""
    Path("docker-compose.yml").write_text('''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=development
    volumes:
      - .:/app
''')
    print("✅ Created docker-compose.yml")


def run_benchmark(endpoint: str = '/', duration: int = 10, connections: int = 100, output: str = None):
    """Run performance benchmarks"""
    from .benchmarks.cli import run_benchmarks
    run_benchmarks(endpoint=endpoint, duration=duration, connections=connections, output=output)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="HasAPI CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new HasAPI project")
    create_parser.add_argument("name", help="Project name")
    create_parser.add_argument("--dir", help="Project directory")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the development server")
    run_parser.add_argument("--app", default="app.py", help="App file")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host")
    run_parser.add_argument("--port", type=int, default=8000, help="Port")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    run_parser.add_argument("--engine", choices=['native', 'python'], help="Transport engine")
    
    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run performance benchmarks")
    bench_parser.add_argument("-e", "--endpoint", default="/", help="API endpoint to benchmark")
    bench_parser.add_argument("-d", "--duration", type=int, default=10, help="Duration in seconds")
    bench_parser.add_argument("-c", "--connections", type=int, default=100, help="Concurrent connections")
    bench_parser.add_argument("-o", "--output", help="Output file for JSON results")
    bench_parser.add_argument("--json", action="store_true", help="Benchmark /json endpoint")
    
    # Docker commands
    docker_parser = subparsers.add_parser("docker", help="Docker commands")
    docker_subparsers = docker_parser.add_subparsers(dest="docker_command")
    docker_subparsers.add_parser("file", help="Create Dockerfile")
    docker_subparsers.add_parser("compose", help="Create docker-compose.yml")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_project(args.name, args.dir)
    elif args.command == "run":
        run_server(args.app, args.host, args.port, args.reload)
    elif args.command == "benchmark":
        endpoint = '/json' if args.json else args.endpoint
        run_benchmark(endpoint, args.duration, args.connections, args.output)
    elif args.command == "docker":
        if args.docker_command == "file":
            create_dockerfile()
        elif args.docker_command == "compose":
            create_docker_compose()
        else:
            docker_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
