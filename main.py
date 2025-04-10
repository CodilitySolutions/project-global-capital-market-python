import asyncio
from app.services.processor import calculate_cost
from app.settings.logger import logger

if __name__ == "__main__":
    logger.info("🏁 Starting property cost calculation process...")

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(calculate_cost())
        logger.info("✅ Property cost calculation completed successfully.")
    except Exception as e:
        logger.exception(f"❌ Unhandled exception occurred in main loop: {e}")
    finally:
        logger.info("🔄 Cleaning up async tasks and closing event loop...")
        loop.run_until_complete(asyncio.sleep(1))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("👋 Shutdown complete.")
