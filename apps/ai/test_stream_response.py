import httpx


def chat_with_server():
    print("Connected to the chat server. Type your message:")

    while True:
        # Get user input
        user_input = input("\nYou:\t")

        # Send the input to the /message endpoint
        payload = {"text": user_input, "stream": True}
        headers = {"Content-Type": "application/json"}

        with httpx.Client() as client:
            with client.stream(
                "POST", "http://localhost:8000/message", json=payload, headers=headers
            ) as response:
                print("Mary Test:", end="\t")
                if response.status_code == 200:
                    # Stream the server's response character by character
                    for char in response.iter_text():
                        print(char, end="", flush=True)
                else:
                    print(f"Server error: {response.status_code}")


# Run the chat client
if __name__ == "__main__":
    chat_with_server()
