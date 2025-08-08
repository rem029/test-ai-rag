import os
import uuid
import subprocess
import platform
from yapper import PiperSpeaker


async def text_to_speech_yapper(text: str) -> str:
    """
    Generate TTS audio for the given text using yapper-tts.
    Returns the path to the generated audio file.
    """
    try:
        # Create output directory if it doesn't exist
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, "tmp", "audio_output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(output_dir, filename)

        # Initialize PiperSpeaker
        speaker = PiperSpeaker()
        # Generate audio file
        speaker.text_to_wave(text, filepath)

        print(f"Audio file generated: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise e


async def text_to_speech(text: str) -> str:
    """
    Generate TTS audio for the given text using pyttsx3 (offline).
    Returns the path to the generated audio file.
    """
    try:
        # Create output directory if it doesn't exist
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, "tmp", "audio_output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(output_dir, filename)

        def _generate_speech():
            engine = None
            try:
                engine = pyttsx3.init()
                # Optional: Configure voice properties
                engine.setProperty("rate", 120)  # Speed of speech
                engine.setProperty("volume", 0.9)  # Volume level (0.0 to 1.0)

                # Save to file
                engine.save_to_file(text, filepath)
                engine.runAndWait()

                # Properly stop the engine
                engine.stop()

            except Exception as e:
                print(f"Error in TTS engine: {e}")
                raise e
            finally:
                # Clean up the engine
                if engine:
                    try:
                        engine.stop()
                    except:
                        pass
                    del engine

        # Run the blocking operation in a thread pool
        await asyncio.to_thread(_generate_speech)

        print(f"Audio file generated: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise e


def play_audio(file_path: str):
    """
    Play audio file using system's default audio player.
    """
    try:
        system = platform.system()
        if system == "Linux":
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
        elif system == "Darwin":
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
