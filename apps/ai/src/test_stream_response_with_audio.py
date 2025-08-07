import base64
import os
import httpx
import uuid
import subprocess
import platform
import re


def img_to_base64(image_path: str) -> str:
    """
    Convert an image file to a base64 encoded string.
    """
    try:
        # If it's just a filename, prepend the uploads directory path
        if not os.path.dirname(image_path):  # No directory in the path
            current_dir = os.getcwd()
            if current_dir.endswith("src"):
                # If we're in the src directory, go up one level to uploads
                full_image_path = os.path.join(current_dir, "", "uploads", image_path)
            else:
                full_image_path = os.path.join(
                    current_dir, "src", "uploads", image_path
                )
            print(f"Using image path: {full_image_path}")
        else:
            full_image_path = image_path  # Use full path if provided

        with open(full_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
    except FileNotFoundError:
        print(f"Image file not found: {full_image_path}")
        return ""
    except Exception as e:
        print(f"Error reading image file: {e}")
        return ""


def play_audio(file_path: str):
    """
    Play audio file using system's default audio player.
    """
    try:
        system = platform.system()
        if system == "Linux":
            # Try multiple audio players in order of preference
            players = [
                ["mpv", "--no-video", file_path],
                ["vlc", "--intf", "dummy", "--play-and-exit", file_path],
                ["mpg123", file_path],
                ["aplay", file_path],
                ["paplay", file_path],
            ]

            for player_cmd in players:
                try:
                    subprocess.run(
                        player_cmd,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    print(f"Playing audio with {player_cmd[0]}")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                print("No suitable audio player found")

        elif system == "Darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
        elif system == "Windows":
            subprocess.run(
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()",
                ],
                check=True,
            )
        else:
            print(f"Unsupported system: {system}")
    except subprocess.CalledProcessError as e:
        print(f"Error playing audio: {e}")
    except FileNotFoundError:
        print("Audio player not found. Please install required audio tools.")


def chat_with_server():
    session_id = str(uuid.uuid4())
    print(f"Connected to the chat server. Session ID: {session_id}")
    print("Type your message:")

    context_default = "Lets roleplay, you wander always wants to explore, I am your ride to tell me where to go, Describe what you see and the direction to go,\n"
    context_default += 'respond in this format: "<description of what you see>. #<direction (left, right backward or forward)>. #<distance in meters>"'

    context_input = input(
        f"\nOverrride Context?:\n---\nDefault: {context_default}\nType your context or press Enter to use default:\n---\n"
    )
    play_choice = (
        input(f"\n\n🎵 Should we play audio? (y/n, default: y): ").strip().lower()
    )

    while True:
        print("\n")
        context = context_input

        # Get user input
        user_input = input("You:\n---\n")

        if not context.strip():
            context = context_default

        image_path = input(
            "Image Path:\n---\nType the image path or press Enter to skip:\n---\n"
        )

        # Ask if user wants audio response
        audio_response = play_choice == "y"

        print("---\n")

        image_path = image_path.strip()

        # Send the input to the /message endpoint
        payload = {
            "text": user_input,
            "stream": True,
            "context": context,
            "session_id": session_id,
            "audioResponse": audio_response,
        }

        if image_path:
            base64_image = img_to_base64(image_path)
            if base64_image:
                payload["image"] = base64_image

        headers = {"Content-Type": "application/json"}

        with httpx.Client(timeout=300.0) as client:
            with client.stream(
                "POST", "http://localhost:8000/message", json=payload, headers=headers
            ) as response:
                print("Mary Test:", end="\n---\n")
                if response.status_code == 200:
                    full_response = ""
                    audio_file_path = None

                    # Stream the server's response character by character
                    for char in response.iter_text():
                        full_response += char

                        # Check if we received an audio file marker
                        if "[AUDIO_FILE:" in full_response and "]" in full_response:
                            # Extract the audio file path
                            match = re.search(r"\[AUDIO_FILE:(.*?)\]", full_response)
                            if match:
                                audio_file_path = match.group(1)
                                print("\n")
                                # Remove the audio marker from display
                                # display_text = re.sub(
                                #     r"\[AUDIO_FILE:.*?\]", "", full_response
                                # )
                                # Clear the line and print clean text
                                # print(f"\r{display_text}", end="", flush=True)
                                break
                        else:
                            print(char, end="", flush=True)

                    # Play audio if available
                    if audio_file_path and os.path.exists(audio_file_path):
                        if play_choice != "n":
                            play_audio(audio_file_path)
                    elif audio_response and not audio_file_path:
                        print(
                            "\n⚠️ Audio was requested but no audio file was generated."
                        )

                else:
                    print(f"Server error: {response.status_code}")


# Run the chat client
if __name__ == "__main__":
    chat_with_server()
