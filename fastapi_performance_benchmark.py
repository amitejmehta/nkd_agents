"""
FastAPI Performance Benchmark
Demonstrates FastAPI's performance characteristics and async capabilities
"""

import asyncio
import time
import aiohttp
import requests
from typing import List, Dict, Any
import statistics
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

# Simple FastAPI app for benchmarking
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import threading

class Item(BaseModel):
    id: int
    name: str
    value: float

# Create benchmark app
benchmark_app = FastAPI()

# Simulate some data processing
fake_db = {i: Item(id=i, name=f"Item {i}", value=i * 1.5) for i in range(1000)}

@benchmark_app.get("/")
async def root():
    return {"message": "FastAPI Benchmark Server"}

@benchmark_app.get("/sync-cpu-bound")
def sync_cpu_bound():
    """CPU-bound synchronous operation"""
    result = sum(i ** 2 for i in range(10000))
    return {"result": result}

@benchmark_app.get("/async-io-bound")
async def async_io_bound():
    """I/O-bound asynchronous operation"""
    await asyncio.sleep(0.1)  # Simulate I/O delay
    return {"message": "Async operation completed"}

@benchmark_app.get("/items/{item_id}")
async def get_item(item_id: int):
    """Database lookup simulation"""
    if item_id in fake_db:
        return fake_db[item_id]
    return {"error": "Item not found"}

@benchmark_app.get("/items/")
async def list_items(skip: int = 0, limit: int = 10):
    """Paginated list with Pydantic validation"""
    items = list(fake_db.values())[skip:skip + limit]
    return items

@benchmark_app.post("/items/")
async def create_item(item: Item):
    """Create item with Pydantic validation"""
    fake_db[item.id] = item
    return item

class BenchmarkRunner:
    """Performance benchmark runner"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: Dict[str, List[float]] = {}
        
    async def run_async_requests(self, endpoint: str, num_requests: int = 100) -> List[float]:
        """Run async requests and measure response times"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(num_requests):
                tasks.append(self.make_async_request(session, endpoint))
            
            start_time = time.time()
            response_times = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Filter out None values (failed requests)
            valid_times = [t for t in response_times if t is not None]
            
            print(f"Async {endpoint}: {len(valid_times)}/{num_requests} successful")
            print(f"Total time: {total_time:.2f}s, RPS: {len(valid_times)/total_time:.2f}")
            
            return valid_times
    
    async def make_async_request(self, session: aiohttp.ClientSession, endpoint: str) -> float:
        """Make single async request"""
        try:
            start = time.time()
            async with session.get(f"{self.base_url}{endpoint}") as response:
                await response.text()
                return time.time() - start
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def run_sync_requests(self, endpoint: str, num_requests: int = 100) -> List[float]:
        """Run synchronous requests with thread pool"""
        with ThreadPoolExecutor(max_workers=50) as executor:
            start_time = time.time()
            futures = [executor.submit(self.make_sync_request, endpoint) for _ in range(num_requests)]
            response_times = [f.result() for f in futures]
            total_time = time.time() - start_time
            
            # Filter out None values (failed requests)
            valid_times = [t for t in response_times if t is not None]
            
            print(f"Sync {endpoint}: {len(valid_times)}/{num_requests} successful")
            print(f"Total time: {total_time:.2f}s, RPS: {len(valid_times)/total_time:.2f}")
            
            return valid_times
    
    def make_sync_request(self, endpoint: str) -> float:
        """Make single sync request"""
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            response.raise_for_status()
            return time.time() - start
        except Exception as e:
            print(f"Sync request failed: {e}")
            return None
    
    def analyze_results(self, times: List[float], name: str):
        """Analyze response time statistics"""
        if not times:
            print(f"{name}: No successful requests")
            return
            
        stats = {
            'count': len(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'std': statistics.stdev(times) if len(times) > 1 else 0,
            'p95': sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times),
            'p99': sorted(times)[int(len(times) * 0.99)] if len(times) > 100 else max(times)
        }
        
        print(f"\n{name} Statistics:")
        print(f"  Count: {stats['count']}")
        print(f"  Mean: {stats['mean']*1000:.2f}ms")
        print(f"  Median: {stats['median']*1000:.2f}ms")
        print(f"  Min: {stats['min']*1000:.2f}ms")
        print(f"  Max: {stats['max']*1000:.2f}ms")
        print(f"  Std Dev: {stats['std']*1000:.2f}ms")
        print(f"  95th percentile: {stats['p95']*1000:.2f}ms")
        print(f"  99th percentile: {stats['p99']*1000:.2f}ms")
        
        return stats

async def run_comprehensive_benchmark():
    """Run comprehensive performance benchmark"""
    print("=" * 60)
    print("FastAPI Performance Benchmark")
    print("=" * 60)
    
    # Start FastAPI server in background thread
    def run_server():
        uvicorn.run(benchmark_app, host="127.0.0.1", port=8000, log_level="warning")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Starting FastAPI server...")
    await asyncio.sleep(2)
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/") as resp:
                if resp.status == 200:
                    print("✓ Server is running")
                else:
                    print("✗ Server not responding correctly")
                    return
    except Exception as e:
        print(f"✗ Could not connect to server: {e}")
        return
    
    runner = BenchmarkRunner()
    
    # System info
    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()
    print(f"\nSystem Info:")
    print(f"  CPU Cores: {cpu_count}")
    print(f"  Memory: {memory.total // (1024**3)}GB total, {memory.available // (1024**3)}GB available")
    print(f"  Python Process ID: {os.getpid()}")
    
    # Benchmark different endpoints
    endpoints = {
        "/": "Simple JSON response",
        "/async-io-bound": "Async I/O operation",
        "/sync-cpu-bound": "Sync CPU-bound operation",
        "/items/1": "Database lookup",
        "/items/?skip=0&limit=10": "Paginated list with validation"
    }
    
    print(f"\nRunning benchmarks...")
    print("-" * 40)
    
    all_results = {}
    
    for endpoint, description in endpoints.items():
        print(f"\nTesting {endpoint} - {description}")
        print("-" * 30)
        
        # Test async requests
        try:
            async_times = await runner.run_async_requests(endpoint, 200)
            async_stats = runner.analyze_results(async_times, f"Async {endpoint}")
            all_results[f"async_{endpoint}"] = async_stats
        except Exception as e:
            print(f"Async test failed: {e}")
        
        # Test sync requests (for comparison)
        try:
            sync_times = runner.run_sync_requests(endpoint, 100)
            sync_stats = runner.analyze_results(sync_times, f"Sync {endpoint}")
            all_results[f"sync_{endpoint}"] = sync_stats
        except Exception as e:
            print(f"Sync test failed: {e}")
    
    # Memory usage test
    print(f"\nMemory Usage Test")
    print("-" * 20)
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create many items to test memory usage
    items_data = []
    for i in range(1000):
        item_data = {"id": i + 1000, "name": f"Benchmark Item {i}", "value": i * 2.5}
        items_data.append(item_data)
    
    # Send POST requests
    post_times = []
    async with aiohttp.ClientSession() as session:
        for item_data in items_data[:100]:  # Test with 100 items
            try:
                start = time.time()
                async with session.post(f"{runner.base_url}/items/", json=item_data) as resp:
                    await resp.text()
                    post_times.append(time.time() - start)
            except Exception as e:
                print(f"POST failed: {e}")
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    runner.analyze_results(post_times, "POST /items/ (Pydantic validation)")
    
    print(f"\nMemory Usage:")
    print(f"  Initial: {initial_memory:.2f}MB")
    print(f"  Final: {final_memory:.2f}MB")
    print(f"  Increase: {final_memory - initial_memory:.2f}MB")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    
    print("\nKey Performance Insights:")
    print("• FastAPI excels at async I/O operations")
    print("• Pydantic validation adds minimal overhead")
    print("• Memory usage remains efficient")
    print("• CPU-bound operations should use background tasks")
    print("• High concurrent request handling capability")
    
    if all_results:
        print(f"\nResponse Time Comparison (mean):")
        for name, stats in all_results.items():
            if stats and 'mean' in stats:
                print(f"  {name}: {stats['mean']*1000:.2f}ms")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_benchmark())