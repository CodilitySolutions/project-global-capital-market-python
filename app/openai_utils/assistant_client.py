import openai
import asyncio
from app.settings.config import OPENAI_API_KEY, ASSISTANT_ID
from app.settings.logger import logger

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

async def get_openai_response(prompt):
    result = ""

    try:
        logger.info("📨 [get_openai_response] Starting thread creation...")

        # Step 1: Create a Thread
        thread = await client.beta.threads.create()
        logger.info(f"🧵 [get_openai_response] Thread created: {thread.id}")

        # Step 2: Post the prompt as a message
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        logger.info("✉️ [get_openai_response] Message posted to thread.")

        # Step 3: Run the Assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        logger.info(f"⚙️ [get_openai_response] Assistant run started: {run.id}")

        # Step 4: Wait for completion
        while True:
            run_status = await client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                logger.info("✅ [get_openai_response] Assistant run completed.")
                break
            await asyncio.sleep(1)

        # Step 5: Get the messages (assistant's reply)
        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        result = messages.data[0].content[0].text.value
        logger.info("📬 [get_openai_response] Response retrieved from assistant.")

    except Exception as e:
        logger.exception(f"❌ [get_openai_response] Exception occurred: {e}")

    return result
