import os
import uuid

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
