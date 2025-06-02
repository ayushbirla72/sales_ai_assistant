from faster_whisper import WhisperModel
import tempfile
import os
from pydub import AudioSegment
import io
import wave
import struct

# Load the model once
model = WhisperModel("base", compute_type="int8")

def is_valid_wav(data):
    try:
        with wave.open(io.BytesIO(data), 'rb') as wav_file:
            return True
    except:
        return False

def convert_to_wav(audio_bytes):
    try:
        # Try to load with pydub
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_bytes = io.BytesIO()
        audio.export(wav_bytes, format="wav", parameters=["-ar", "16000", "-ac", "1"])
        return wav_bytes.getvalue()
    except Exception as e:
        print(f"Error converting audio: {str(e)}")
        raise ValueError(f"Failed to convert audio format: {str(e)}")

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    try:
        # Check if it's already a valid WAV file
        if not is_valid_wav(audio_bytes):
            print("Converting audio to WAV format...")
            audio_bytes = convert_to_wav(audio_bytes)
        
        # Use delete=False to avoid PermissionError on Windows
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name

        try:
            print(f"Transcribing audio file: {tmp_path}")
            segments, _ = model.transcribe(tmp_path)
            full_text = ""
            for segment in segments:
                full_text += segment.text.strip() + " "
            return full_text.strip()

        finally:
            # Manually delete the temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        print(f"Error in transcribe_audio_bytes: {str(e)}")
        raise ValueError(f"Error processing audio: {str(e)}")



# import whisper

# def load_whisper_model():
#     print("[INFO] Loading Whisper model...")
#     model = whisper.load_model("large")
#     return model

def transcribe_segment(audio_path):
    result = model.transcribe(audio_path)
    text = result.get("text", "").strip()
    return text
