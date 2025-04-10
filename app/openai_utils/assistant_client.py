import openai
import asyncio
from app.settings.config import OPENAI_API_KEY, ASSISTANT_ID

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

async def get_openai_response(prompt):
    result = ""

    try:
        # Step 1: Create a Thread
        thread = await client.beta.threads.create()

        # Step 2: Post the prompt as a message
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Step 3: Run the Assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Wait for completion
        while True:
            run_status = await client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            await asyncio.sleep(1)

        # Step 5: Get the messages (assistant's reply)
        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        result = messages.data[0].content[0].text.value

    except Exception as e:
        print("Exception: ", e)

    return result
