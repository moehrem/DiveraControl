#!/usr/bin/env python3
"""Test script to check if Divera API enforces rate-limiting for parallel requests."""

import asyncio
import time
from aiohttp import ClientSession, ClientTimeout

# Replace with your actual API key and UCR IDs
API_KEY = "YOUR_API_KEY"
UCR_IDS = ["641834", "641835", "641842", "641845", "641846"] * 3  # 15 parallel requests
API_URL = "https://app.divera247.com/api/v2/pull/all"


async def fetch_data(session: ClientSession, ucr_id: str, request_id: int) -> None:
    """Fetch data from Divera API for a given UCR ID."""
    params = {
        "accesskey": API_KEY,
        "ucr": ucr_id,
    }
    start_time = time.time()
    try:
        async with session.get(API_URL, params=params, timeout=ClientTimeout(total=10)) as response:
            duration = time.time() - start_time
            if response.status == 200:
                print(f"✅ Request {request_id} (UCR {ucr_id}): {duration:.3f}s (success)")
            else:
                print(f"❌ Request {request_id} (UCR {ucr_id}): {duration:.3f}s (HTTP {response.status})")
    except Exception as e:
        duration = time.time() - start_time
        print(f"⚠️ Request {request_id} (UCR {ucr_id}): {duration:.3f}s (Error: {type(e).__name__})")


async def main() -> None:
    """Run parallel API requests and measure execution time."""
    async with ClientSession() as session:
        tasks = [fetch_data(session, ucr_id, i) for i, ucr_id in enumerate(UCR_IDS)]
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_duration = time.time() - start_time
        print(f"\n📊 Total execution time: {total_duration:.3f}s")
        print(f"📈 Average time per request: {total_duration / len(UCR_IDS):.3f}s")


if __name__ == "__main__":
    asyncio.run(main())