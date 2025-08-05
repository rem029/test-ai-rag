import base64
import os
import httpx

def img_to_base64(image_path: str) -> str:
    """
    Convert an image file to a base64 encoded string.
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
    except FileNotFoundError:
        print(f"Image file not found: {image_path}")
        return ""
    except Exception as e:
        print(f"Error reading image file: {e}")
        return ""


def chat_with_server():
    print("Connected to the chat server. Type your message:")

    while True:
        # Get user input
        user_input = input("\nYou:\n---\n")
        image_path = input("\nImage Path:\n---\n")
        print("---\n")

        context = "You are my teacher and I am your student. "
        context += "Answer my questions based on the context provided."
        image_path = image_path.strip()
        # Send the input to the /message endpoint
        payload = {"text": user_input, "stream": True, "context": context}
        if image_path:
            if os.path.exists(image_path):
                base64_image = img_to_base64(image_path)
                if base64_image:
                    payload["image"] = base64_image
            else:
                print(f"Image file does not exist: {image_path}")
        
        headers = {"Content-Type": "application/json"}

        with httpx.Client(timeout=300.0) as client:
            with client.stream(
                "POST", "http://localhost:8000/message", json=payload, headers=headers
            ) as response:
                print("Mary Test:", end="\n---\n")
                if response.status_code == 200:
                    # Stream the server's response character by character
                    for char in response.iter_text():
                        print(char, end="", flush=True)
                else:
                    print(f"Server error: {response.status_code}")


# Run the chat client
if __name__ == "__main__":
    chat_with_server()
