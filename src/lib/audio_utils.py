import whisper
import pyttsx3
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import os

# Constants
SAMPLE_RATE = 16000  # 16kHz sample rate for Whisper
RECORDING_PATH = "temp_recording.wav"
WHISPER_MODEL = "base.en"  # A good balance of speed and accuracy

# Load models once to be efficient
whisper_model = whisper.load_model(WHISPER_MODEL)
tts_engine = pyttsx3.init()


def record_audio(duration_seconds: int = 7):
    print(f"Recording for {duration_seconds} seconds...")
    recording = sd.rec(
        int(duration_seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    write(RECORDING_PATH, SAMPLE_RATE, recording)
    print("Recording finished.")
    return RECORDING_PATH


def transcribe_audio(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "Error: Audio file not found."

    result = whisper_model.transcribe(file_path)
    os.remove(file_path)  # Clean up the temporary audio file
    return result.get("text", "Could not transcribe audio.")


def text_to_speech(text: str):
    print(f"\nAI: {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()
