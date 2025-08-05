import base64
import os
import httpx
import uuid

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
    session_id = str(uuid.uuid4())
    print(f"Connected to the chat server. Session ID: {session_id}")
    print("Type your message:")

    context_default = "You are my teacher and I am your student. "
    context_default += "Answer my questions based on the context provided."

    context_input = input(f"\nOverrride Context?:\n---\nDefault: {context_default}\nType your context or press Enter to use default:\n---\n")

    while True:
        print("\n")
        context = context_input

        # Get user input
        user_input = input("You:\n---\n")

        
        if not context.strip():
            context = context_default

        if not user_input.strip():
            print("Exiting chat.")
            break
        
        image_path = input("Image Path:\n---\nType the image path or press Enter to skip:\n---\n")
        print("---\n")

        image_path = image_path.strip()       

        # Send the input to the /message endpoint
        payload = {"text": user_input, "stream": True, "context": context, "session_id": session_id}
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
