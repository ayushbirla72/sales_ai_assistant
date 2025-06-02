from faster_whisper import WhisperModel
import tempfile
import os
from pydub import AudioSegment
import io

# Load the model once
model = WhisperModel("base", compute_type="int8")

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    try:
        # First try to load the audio using pydub to validate format
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Convert to WAV format if needed
        wav_bytes = io.BytesIO()
        audio.export(wav_bytes, format="wav")
        wav_bytes.seek(0)
        
        # Use delete=False to avoid PermissionError on Windows
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes.read())
            tmp.flush()
            tmp_path = tmp.name  # Store path so we can use and delete it later

        try:
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
