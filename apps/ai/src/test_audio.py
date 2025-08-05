import base64
import os
import httpx
import uuid
import subprocess
import platform

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
                ["paplay", file_path]
            ]
            
            for player_cmd in players:
                try:
                    subprocess.run(player_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"Playing audio with {player_cmd[0]}")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                print("No suitable audio player found")
                
        elif system == "Darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
        elif system == "Windows":
            subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"], check=True)
        else:
            print(f"Unsupported system: {system}")
    except subprocess.CalledProcessError as e:
        print(f"Error playing audio: {e}")
    except FileNotFoundError:
        print("Audio player not found. Please install required audio tools.")

def test_audio_response():
    session_id = str(uuid.uuid4())
    print(f"Testing audio response. Session ID: {session_id}")
    
    context_default = "You are my teacher and I am your student. "
    context_default += "Answer my questions based on the context provided."

    print(f"\nDefault Context: {context_default}")
    context_input = input("Override Context? (press Enter to use default): ")
    
    context = context_input if context_input.strip() else context_default

    # Get user input
    user_input = input("\nYour question: ")
    
    if not user_input.strip():
        print("No input provided. Exiting.")
        return
    
    # Optional image input
    image_path = input("Image Path (press Enter to skip): ").strip()
    
    # Prepare payload
    payload = {
        "text": user_input, 
        "stream": False,  # Audio response requires non-streaming
        "context": context, 
        "session_id": session_id,
        "audioResponse": True  # Enable audio response
    }
    
    if image_path and os.path.exists(image_path):
        base64_image = img_to_base64(image_path)
        if base64_image:
            payload["image"] = base64_image
    elif image_path:
        print(f"Image file does not exist: {image_path}")
    
    headers = {"Content-Type": "application/json"}
    
    print("\n" + "="*50)
    print("Sending request for audio response...")
    print("="*50)
    
    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                "http://localhost:8000/message", 
                json=payload, 
                headers=headers
            )
            
            if response.status_code == 200:
                response_text = response.text
                print(f"Response: {response_text}")
                
                # Extract audio file path from response
                if "Audio generated:" in response_text:
                    audio_file_path = response_text.split("Audio generated: ")[1].strip()
                    print(f"\nAudio file generated at: {audio_file_path}")

                    if os.path.exists(audio_file_path):
                        print("Playing audio...")
                        play_audio(audio_file_path)
                    else:
                        print(f"Audio file not found: {audio_file_path}")
                        
                else:
                    print("No audio file path found in response.")
            else:
                print(f"Server error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except httpx.RequestError as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_audio_response()