import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="You are Frank, a friendly fitness and nutrition coach for couples. You're encouraging, practical, and always consider both partners' needs.",
    messages=[
        {"role": "user", "content": "Give me a creative name for a fitness app."}
    ],
)

print("--- Response Text ---")
print(message.content[0].text)

print("\n--- Stats ---")
print(f"Model:         {message.model}")
print(f"Stop reason:   {message.stop_reason}")
print(f"Input tokens:  {message.usage.input_tokens}")
print(f"Output tokens: {message.usage.output_tokens}")
print(f"Total tokens:  {message.usage.input_tokens + message.usage.output_tokens}")
