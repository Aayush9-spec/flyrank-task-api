import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

base_url = os.getenv("LLM_BASE_URL")
api_key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL")

if not all([base_url, api_key, model]):
    sys.exit("Error: Missing LLM configuration in .env")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    timeout=30.0,
    max_retries=0,
)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise AI assistant. Follow the user's instruction exactly.",
            },
            {
                "role": "user",
                "content": "Reply with exactly: FlyRank BE-07 configured successfully.",
            },
        ],
        temperature=0,
    )

    print("AI response:", response.choices[0].message.content)
    print("Model:", response.model)

    if response.usage:
        print("Prompt tokens:", response.usage.prompt_tokens)
        print("Completion tokens:", response.usage.completion_tokens)
        print("Total tokens:", response.usage.total_tokens)

except Exception as exc:
    sys.exit(f"AI request failed: {type(exc).__name__}: {exc}")
