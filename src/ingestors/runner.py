import asyncio
import signal
import sys
from typing import Optional

from src.common.logging import setup_logging
from src.common.config import settings
from src.ingestors.air.ingestor import AirDomainIngestor
from src.ingestors.maritime.ingestor import MaritimeDomainIngestor
from src.ingestors.seismic.ingestor import SeismicDomainIngestor
from src.ingestors.rf.ingestor import RFIngestor
from src.ingestors.cyber.ingestor import CyberDomainIngestor

logger = setup_logging("ingestor-runner")

INGESTORS = {
    "air": AirDomainIngestor,
    "maritime": MaritimeDomainIngestor,
    "seismic": SeismicDomainIngestor,
    "rf": RFIngestor,
    "cyber": CyberDomainIngestor,
}


async def main():
    ingestor_type = settings.ingestor_type.lower()
    if ingestor_type not in INGESTORS:
        logger.error(f"Unknown ingestor type: {ingestor_type}", extra={"available": list(INGESTORS.keys())})
        sys.exit(1)

    ingestor_class = INGESTORS[ingestor_type]
    ingestor = ingestor_class()

    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _signal_handler():
        if not shutdown_event.is_set():
            logger.info("Shutdown signal received")
            shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, ValueError):
            pass

    logger.info(f"Starting {ingestor_type} ingestor")
    main_task = asyncio.create_task(ingestor.start())

    try:
        done, _ = await asyncio.wait(
            [main_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if main_task in done:
            exc = main_task.exception()
            if exc:
                logger.critical("Ingestor crashed", extra={"error": str(exc)})
                sys.exit(1)
    except asyncio.CancelledError:
        pass
    finally:
        if not shutdown_event.is_set():
            logger.info("Shutting down ingestor")
            await ingestor.stop()
            main_task.cancel()
            try:
                await main_task
            except (asyncio.CancelledError, Exception):
                pass


if __name__ == "__main__":
    asyncio.run(main())
