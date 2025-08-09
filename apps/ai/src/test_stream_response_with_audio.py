import base64
import os
import random
import httpx
import uuid
import subprocess
import platform
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from rich.columns import Columns
from rich.table import Table
from datetime import datetime
import logging
try:
    # Try to import PIL for image preview
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Initialize Rich console with file recording
console = Console(record=True)

# Set up beautiful logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger("RobotNavBrain")

# Global variables for logging
session_logger = None
log_file_path = None

def setup_session_logging(session_id: str):
    """
    Set up logging for a specific session.
    Creates a session-specific log file and configures logging.
    """
    global session_logger, log_file_path
    
    # Create session-specific log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"robotnav_session_{session_id[:8]}_{timestamp}.log"
    log_file_path = os.path.join(LOGS_DIR, log_filename)
    
    # Create session logger
    session_logger = logging.getLogger(f"Session_{session_id[:8]}")
    session_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    session_logger.handlers.clear()
    
    # Create file handler for session logs
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    session_logger.addHandler(file_handler)
    
    return log_file_path

def log_and_print(message: str, style: str = "white", log_level: str = "info"):
    """
    Print to console with Rich formatting AND log to session file.
    """
    global session_logger
    
    # Print to console with Rich formatting
    console.print(message)
    
    # Log to session file (strip Rich formatting for clean log)
    if session_logger:
        # Remove Rich markup for clean file logging
        clean_message = re.sub(r'\[.*?\]', '', message)
        clean_message = re.sub(r'[🤖📁✅❌🔊🎵⚠️💭📷🖼️🚫💤📸─]', '', clean_message).strip()
        
        if log_level.lower() == "info":
            session_logger.info(clean_message)
        elif log_level.lower() == "warning":
            session_logger.warning(clean_message)
        elif log_level.lower() == "error":
            session_logger.error(clean_message)
def preview_image_in_terminal(image_path: str, max_width: int = 80, max_height: int = 20):
    """
    Preview an image in the terminal using different methods.
    """
    if not os.path.exists(image_path):
        log_and_print(f"❌ [red]Image not found:[/red] [yellow]{image_path}[/yellow]", log_level="error")
        return
    
    log_and_print(f"🖼️ [cyan]Previewing image:[/cyan] [yellow]{os.path.basename(image_path)}[/yellow]")
    
    # Method 1: Try Rich's built-in image support (if terminal supports it)
    try:
        # Some terminals support Rich image rendering
        from rich.console import Console
        preview_console = Console()
        
        # Create a simple ASCII art representation
        if PIL_AVAILABLE:
            try:
                img = Image.open(image_path)
                width, height = img.size
                
                # Create an info table about the image
                image_info = Table(title=f"🖼️ Image Preview: {os.path.basename(image_path)}")
                image_info.add_column("Property", style="cyan", no_wrap=True)
                image_info.add_column("Value", style="yellow")
                
                image_info.add_row("File Size", f"{os.path.getsize(image_path):,} bytes")
                image_info.add_row("Dimensions", f"{width} × {height} pixels")
                image_info.add_row("Format", img.format if img.format else "Unknown")
                image_info.add_row("Mode", img.mode if img.mode else "Unknown")
                
                console.print(image_info)
                
                # Simple ASCII representation
                ascii_art = create_simple_ascii_preview(img, max_width//2, max_height//2)
                if ascii_art:
                    console.print(Panel(ascii_art, title="[bold blue]ASCII Preview[/bold blue]", border_style="blue"))
                
            except Exception as e:
                log_and_print(f"⚠️ [yellow]Could not create detailed preview:[/yellow] [red]{e}[/red]", log_level="warning")
        
    except Exception as e:
        log_and_print(f"⚠️ [yellow]Terminal image preview not available:[/yellow] [red]{e}[/red]", log_level="warning")

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
            log_and_print(f"📁 [cyan]Using image path:[/cyan] [yellow]{full_image_path}[/yellow]")
        else:
            full_image_path = image_path  # Use full path if provided

        # Show image preview if requested
        if show_preview:
            preview_image_in_terminal(full_image_path)

        with open(full_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            log_and_print(f"✅ [green]Successfully encoded image:[/green] [blue]{os.path.basename(full_image_path)}[/blue]")
            return encoded_string
    except FileNotFoundError:
        log_and_print(f"❌ [red]Image file not found:[/red] [yellow]{full_image_path}[/yellow]", log_level="error")
        return ""
    except Exception as e:
        log_and_print(f"❌ [red]Error reading image file:[/red] [yellow]{e}[/yellow]", log_level="error")
        return ""


def play_audio(file_path: str):
    """
    Play audio file using system's default audio player.
    """
    try:
        system = platform.system()
        log_and_print(f"🔊 [blue]Attempting to play audio on {system}:[/blue] [yellow]{os.path.basename(file_path)}[/yellow]")
        
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
                    log_and_print(f"🎵 [green]Playing audio with[/green] [bold cyan]{player_cmd[0]}[/bold cyan]")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                log_and_print("⚠️ [yellow]No suitable audio player found[/yellow]", log_level="warning")

        elif system == "Darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
            log_and_print("🎵 [green]Playing audio with[/green] [bold cyan]afplay[/bold cyan]")
        elif system == "Windows":
            subprocess.run(
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()",
                ],
                check=True,
            )
            log_and_print("🎵 [green]Playing audio with[/green] [bold cyan]PowerShell[/bold cyan]")
        else:
            log_and_print(f"❌ [red]Unsupported system:[/red] [yellow]{system}[/yellow]", log_level="error")
    except subprocess.CalledProcessError as e:
        log_and_print(f"❌ [red]Error playing audio:[/red] [yellow]{e}[/yellow]", log_level="error")
    except FileNotFoundError:
        log_and_print("❌ [red]Audio player not found. Please install required audio tools.[/red]", log_level="error")

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
    import random
    import time
    session_id = str(uuid.uuid4())
    
    # Setup session-specific logging
    log_path = setup_session_logging(session_id)
    
    # Beautiful session start
    session_start_panel = Panel.fit(
        f"🤖 [bold green]RobotNavBrain Chat Client Started[/bold green]\n"
        f"📅 [cyan]Time:[/cyan] [yellow]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/yellow]\n"
        f"🆔 [cyan]Session ID:[/cyan] [blue]{session_id}[/blue]\n"
        f"📄 [cyan]Log File:[/cyan] [magenta]{log_path}[/magenta]",
        title="[bold magenta]AI Chat Session[/bold magenta]",
        border_style="green"
    )
    console.print(session_start_panel)
    
    # Log session start
    if session_logger:
        session_logger.info(f"=== RobotNavBrain Chat Session Started ===")
        session_logger.info(f"Session ID: {session_id}")
        session_logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        session_logger.info(f"Log File: {log_path}")
        session_logger.info("=" * 50)

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
        log_and_print(f"📸 [green]Found {len(image_filenames)} images in[/green] [cyan]{image_dir}[/cyan]")
    except Exception as e:
        log_and_print(f"❌ [red]Error reading image files from {image_dir}:[/red] [yellow]{e}[/yellow]", log_level="error")
        image_filenames = []


    context_default = build_context()
   
    play_choice = "y"  # Always play audio

    while True:
        log_and_print("\n" + "─" * 60)

        # Always use the default context
        context = context_default

        # Randomly select user input object
        user_input_obj = random.choice(user_inputs)
        user_input = user_input_obj["prompt"]
        use_image = user_input_obj["use_image"]

        image_filename = random.choice(image_filenames) if image_filenames else None
        image_path = f"{image_dir}/{image_filename}" if image_filename else None

        # Beautiful request info with logging
        log_and_print(f"💭 [bold blue]User input:[/bold blue] [white]{user_input}[/white]")
        log_and_print(f"📷 [bold blue]Use image:[/bold blue] [{'green' if use_image else 'red'}]{use_image}[/{'green' if use_image else 'red'}]")
        if use_image and image_path:
            log_and_print(f"🖼️  [bold blue]Image path:[/bold blue] [yellow]{image_path}[/yellow]")
        else:
            log_and_print("🚫 [dim]No image will be attached.[/dim]")

        audio_response = True  # Always play audio

        log_and_print("─" * 40)

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
                "POST", "http://192.168.18.101:8000/message", json=payload, headers=headers
            ) as response:
                log_and_print("🤖 [bold green]Mary Test Response:[/bold green]")
                log_and_print("─" * 40)
                
                if response.status_code == 200:
                    full_response = ""
                    audio_file_path = None

                    # Log the start of response streaming
                    if session_logger:
                        session_logger.info("SERVER RESPONSE: Starting to receive streamed response")

                    # Stream the server's response character by character
                    for char in response.iter_text():
                        full_response += char

                        # Check if we received an audio file marker
                        if "[AUDIO_FILE:" in full_response and "]" in full_response:
                            # Extract the audio file path
                            match = re.search(r"\[AUDIO_FILE:(.*?)\]", full_response)
                            if match:
                                audio_file_path = match.group(1)
                                console.print()
                                # Log the complete response
                                if session_logger:
                                    clean_response = re.sub(r'\[AUDIO_FILE:.*?\]', '', full_response).strip()
                                    session_logger.info(f"SERVER RESPONSE: {clean_response}")
                                    session_logger.info(f"AUDIO FILE GENERATED: {audio_file_path}")
                                break
                        else:
                            print(char, end="", flush=True)
                    
                    # If no audio marker was found, log the complete response
                    if not audio_file_path and session_logger:
                        session_logger.info(f"SERVER RESPONSE: {full_response}")

                    # Play audio if available
                    if audio_file_path and os.path.exists(audio_file_path):
                        if play_choice != "n":
                            play_audio(audio_file_path)

                    elif audio_response and not audio_file_path:
                        log_and_print(
                            "\n⚠️ [yellow]Audio was requested but no audio file was generated.[/yellow]",
                            log_level="warning"
                        )

                else:
                    log_and_print(f"❌ [red]Server error:[/red] [bold red]{response.status_code}[/bold red]", log_level="error")

        # Sleep for 15 seconds after each request
        from datetime import timedelta
        next_time = datetime.now() + timedelta(seconds=15)
        log_and_print(f"\n💤 [dim]Sleeping for 15 seconds... (Next request at {next_time.strftime('%H:%M:%S')})[/dim]")
        time.sleep(15)


# Run the chat client
if __name__ == "__main__":
    try:
        chat_with_server()
    except KeyboardInterrupt:
        if session_logger:
            session_logger.info("=== Session terminated by user ===")
            session_logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print("\n🛑 [red]Session terminated by user.[/red]")
    except Exception as e:
        if session_logger:
            session_logger.error(f"Session ended with error: {e}")
            session_logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"\n❌ [red]Session ended with error:[/red] [yellow]{e}[/yellow]")
    finally:
        if log_file_path:
            console.print(f"\n📄 [green]Session logs saved to:[/green] [blue]{log_file_path}[/blue]")
