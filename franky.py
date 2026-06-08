import os
import anthropic
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()
conversation_history = []

with open("system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()
def chat(user_message):
    conversation_history.append({"role": "user", "content": user_message})
    
    print(f"[DEBUG] History length: {len(conversation_history)} messages")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=conversation_history,
        )
    except anthropic.AuthenticationError:
        print("Your API key is invalid. Check your .env file.")
        return None
    except anthropic.RateLimitError:
        print("Too many requests. Wait a moment and try again.")
        return None
    except Exception as e:
        print(f"Something went wrong: {e}")
        return None

    assistant_message = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_message})
    return assistant_message

def main():
    print("Franky Fitness Agent")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "bye":
            print("See you next time!")
            break

        response = chat(user_input)
        print(f"FRANKY SAYS: {response}")

if __name__ == "__main__":
    main()