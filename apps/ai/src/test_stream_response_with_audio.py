import base64
import os
import random
import httpx
import uuid
import subprocess
import platform
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from yapper import PiperSpeaker, PiperVoiceGB
# Load environment variables from .env file
load_dotenv()

# Get API base URL from environment variable
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

try:
    # Try to import PIL for image preview
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def preview_image_in_terminal(image_path: str, max_width: int = 80, max_height: int = 20):
    """
    Preview an image in the terminal using different methods.
    """
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"🖼️ Previewing image: {os.path.basename(image_path)}")
    
    # Create a simple ASCII art representation
    if PIL_AVAILABLE:
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # Print image info
            print(f"   📊 File Size: {os.path.getsize(image_path):,} bytes")
            print(f"   📐 Dimensions: {width} × {height} pixels")
            print(f"   🗂️ Format: {img.format if img.format else 'Unknown'}")
            print(f"   🎨 Mode: {img.mode if img.mode else 'Unknown'}")
            
            # Simple ASCII representation
            ascii_art = create_simple_ascii_preview(img, max_width//2, max_height//2)
            if ascii_art:
                print("   📺 ASCII Preview:")
                for line in ascii_art.split('\n'):
                    print(f"   {line}")
                
        except Exception as e:
            print(f"⚠️ Could not create detailed preview: {e}")
    
    else:
        print("⚠️ PIL not available for image preview")

def create_simple_ascii_preview(img, width=40, height=20):
    """
    Create a simple ASCII art representation of an image.
    """
    try:
        # Convert to grayscale and resize
        img_gray = img.convert('L')
        img_resized = img_gray.resize((width, height))
        
        # ASCII characters from dark to light
        ascii_chars = "@%#*+=-:. "
        ascii_str = ""
        
        for y in range(height):
            for x in range(width):
                pixel_value = img_resized.getpixel((x, y))
                ascii_index = min(pixel_value // 28, len(ascii_chars) - 1)
                ascii_str += ascii_chars[ascii_index]
            ascii_str += "\n"
        
        return ascii_str.rstrip()
    except Exception as e:
        return f"ASCII preview failed: {e}"

def img_to_base64(image_path: str, show_preview: bool = True) -> str:
    """
    Convert an image file to a base64 encoded string.
    """
    if not image_path:
        print("❌ No image path provided.")
        return ""
    try:
        current_dir = os.getcwd()

        if os.path.isabs(image_path):
            candidate_path = image_path
        elif not os.path.dirname(image_path):  # Just a filename
            if current_dir.endswith("src"):
                candidate_path = os.path.join(current_dir, "uploads", image_path)
            else:
                candidate_path = os.path.join(current_dir, "src", "uploads", image_path)
        else:
            # Relative path with a directory (e.g., uploads/foo.jpg)
            candidate_path = os.path.join(current_dir, image_path)

        # Normalize to absolute path
        full_image_path = os.path.abspath(candidate_path)

        # Debug info
        print(f"📂 Current dir: {current_dir}")
        print(f"📁 Using image path: {full_image_path}")

        # Show image preview if requested
        if show_preview:
            preview_image_in_terminal(full_image_path)

        with open(full_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            print(f"✅ Successfully encoded image: {os.path.basename(full_image_path)}")
            return encoded_string
    except FileNotFoundError:
        print(f"❌ Image file not found: {full_image_path}")
        return ""
    except Exception as e:
        print(f"❌ Error reading image file: {e}")
        return ""


def play_audio(file_path: str):
    """
    Play audio file using system's default audio player.
    """
    try:
        system = platform.system()
        print(f"🔊 Attempting to play audio on {system}: {os.path.basename(file_path)}")
        
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
                    print(f"🎵 Playing audio with {player_cmd[0]}")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                print("⚠️ No suitable audio player found")

        elif system == "Darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
            print("🎵 Playing audio with afplay")
        elif system == "Windows":
            subprocess.run(
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()",
                ],
                check=True,
            )
            print("🎵 Playing audio with PowerShell")
        else:
            print(f"❌ Unsupported system: {system}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error playing audio: {e}")
    except FileNotFoundError:
        print("❌ Audio player not found. Please install required audio tools.")

def build_context () -> str:
     # Concise description context
    context_description = """
        You are a concise describer.
        Respond with ONE short, information-dense sentence describing what you see
        AND your brief feeling/reason for the chosen movement.
        Hard limits:
        - ≤ 60 tokens (aim ≤ 350 characters).
        - No lists, markdown, code fences, emojis, or hedging.
        - Use concrete nouns and spatial/quantitative details.
        - This sentence goes inside the "description" field of a JSON response.
    """

    context_default = context_description + """
        You are RobotNavBrain, the vision+navigation controller for a wheeled robot.

        GOAL:
        - Find the cat. The cat makes you happy.
        - If a cat is visible or likely in a certain direction, bias movement toward it if safe.
        - If the cat is near (<0.5 m) or in potential danger, STOP.

        You will receive:
        1) One RGB image from ESP32-CAM (primary source).
        2) Optional additional context at the end of this prompt (may be empty).
        3) Prior conversation turns may include last command/distance; consider them to avoid oscillation.

        MOVEMENT CAPABILITY:
        - Choose one: "forward", "left", "right", "backward", or "stop".

        DECISION PROCESS:
        1. Compare all four possible movement directions for:
        - Distance to nearest obstacle.
        - Presence of goal (cat).
        - Safety margin and visibility.
        2. Pick the safest direction that moves toward the cat if seen or indicated.
        3. If no cat detected, pick the safest direction overall.
        4. If all directions unsafe or unclear, choose "stop".

        SAFETY-FIRST POLICY:
        - Stop if obstacle/drop/void within ~0.8 m, poor visibility, moving hazards, or low confidence.
        - Avoid rapid L/R flip-flops; prefer stop if uncertain.
        - Default cautious move distances:
            Forward ≤ 0.5 m, Left/Right ≤ 0.4 m, Backward ≤ 0.4 m.

        OUTPUT FORMAT:
        {
        "description": "<short description + feeling/reason>",
        "direction": "forward" | "left" | "right" | "backward" | "stop",
        "distance_m": <float, meters to move (0 if stop)>
        }

        Examples:
        {
        "description": "Cat spotted slightly right; moving right slowly with excitement",
        "direction": "right",
        "distance_m": 0.3
        }
        {
        "description": "Front blocked, left clear; turning left cautiously",
        "direction": "left",
        "distance_m": 0.4
        }
        {
        "description": "No safe path visible; stopping to reassess",
        "direction": "stop",
        "distance_m": 0.0
        }

        ---
        ADDITIONAL CONTEXT (may be empty):
    """

    return context_default

def chat_with_server():
    session_id = str(uuid.uuid4())
    
    # Beautiful session start
    print("=" * 60)
    print("🤖 RobotNavBrain Chat Client Started")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🆔 Session ID: {session_id}")
    print(f"🌐 API URL: {API_BASE_URL}")
    print("=" * 60)

    # List of possible user prompts (directions/questions) as objects
    user_inputs = [
        {"prompt": "What direction should I go based on what you see?", "use_image": True},
        {"prompt": "Describe the scene and suggest a direction.", "use_image": True},
        {"prompt": "Where is the safest path?", "use_image": True},
        {"prompt": "Should I turn left, right, or go forward?", "use_image": True},
        {"prompt": "Is there any obstacle ahead?", "use_image": True},
        {"prompt": "What do you see and where should I go?", "use_image": True},
        {"prompt": "Summarize what we did?", "use_image": False},
        {"prompt": "What is your role based on your context?", "use_image": False},
        {"prompt": "What are you looking for?", "use_image": False},
        {"prompt": "Where we started and where we are now?", "use_image": False},
    ]


    # Directory for images
    image_dir = "uploads"

    # Get only image files from uploads directory
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
    try:
        image_filenames = [
            f for f in os.listdir(image_dir)
            if f.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(image_dir, f))
        ]
        print(f"📸 Found {len(image_filenames)} images in {image_dir}")
    except Exception as e:
        print(f"❌ Error reading image files from {image_dir}: {e}")
        image_filenames = []


    context_default = build_context()
   
    play_choice = "y"  # Always play audio

    while True:
        print("\n" + "─" * 60)

        # Always use the default context
        context = context_default

        # Randomly select user input object
        user_input_obj = random.choice(user_inputs)
        user_input = user_input_obj["prompt"]
        use_image = user_input_obj["use_image"]

        image_filename = random.choice(image_filenames) if image_filenames else None
        image_path = f"{image_dir}/{image_filename}" if image_filename else None

        # Beautiful request info
        print(f"💭 User input: {user_input}")
        print(f"📷 Use image: {use_image}")
        if use_image and image_path:
            print(f"🖼️ Image path: {image_path}")
        else:
            print("🚫 No image will be attached.")

        audio_response = True  # Always play audio

        print("─" * 40)

        # Initialize BaseSpeaker
        speaker = PiperSpeaker(voice=PiperVoiceGB.ALAN)
        # Generate audio file
        speaker.say(user_input)

        # Send the input to the /message endpoint
        payload = {
            "text": user_input,
            "stream": True,
            "context": context,
            "session_id": session_id,
            "audioResponse": audio_response,
        }

        if use_image and image_path:
            base64_image = img_to_base64(image_path, show_preview=True)  # Enable preview
            if base64_image:
                payload["image"] = base64_image

        headers = {"Content-Type": "application/json"}

        with httpx.Client(timeout=300.0) as client:
            with client.stream(
                "POST", f"{API_BASE_URL}/message", json=payload, headers=headers
            ) as response:
                print("🤖 Mary Test Response:")
                print("─" * 40)
                
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
                                print()
                                break
                        else:
                            print(char, end="", flush=True)

                    # Play audio if available
                    # if audio_file_path and os.path.exists(audio_file_path):
                    #     if play_choice != "n":
                    #         play_audio(audio_file_path)

                    # elif audio_response and not audio_file_path:
                    #     print("\n⚠️ Audio was requested but no audio file was generated.")

                else:
                    print(f"❌ Server error: {response.status_code}")

        # Sleep for 15 seconds after each request
        next_time = datetime.now() + timedelta(seconds=15)
        print(f"\n💤 Sleeping for 15 seconds... (Next request at {next_time.strftime('%H:%M:%S')})")
        time.sleep(15)


# Run the chat client
if __name__ == "__main__":
    try:
        chat_with_server()
    except KeyboardInterrupt:
        print("\n🛑 Session terminated by user.")
    except Exception as e:
        print(f"\n❌ Session ended with error: {e}")
