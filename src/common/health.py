import asyncio
import socket
from typing import Optional
from src.common.logging import setup_logging

logger = setup_logging("health")


async def wait_for_tcp(host: str, port: int, timeout: float = 30.0, interval: float = 2.0) -> bool:
    start = asyncio.get_event_loop().time()
    while True:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed >= timeout:
                logger.error(f"Timeout waiting for {host}:{port} after {timeout}s")
                return False
            logger.info(f"Waiting for {host}:{port}... ({elapsed:.0f}s/{timeout}s)")
            await asyncio.sleep(interval)


async def wait_for_kafka(bootstrap_servers: str, timeout: float = 30.0):
    host, port_str = bootstrap_servers.split(":")
    return await wait_for_tcp(host, int(port_str), timeout)
