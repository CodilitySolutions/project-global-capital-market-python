from app.services.processor import calculate_cost
import asyncio

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(calculate_cost())
    finally:
        loop.run_until_complete(asyncio.sleep(1))  # Give time for cleanup
        loop.run_until_complete(loop.shutdown_asyncgens())  # Force shutdown of pending async generators
        loop.close()
