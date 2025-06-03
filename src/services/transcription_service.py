from faster_whisper import WhisperModel
import tempfile
import os

# Load the model once
model = WhisperModel("large", compute_type="int8")

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    # Use delete=False to avoid PermissionError on Windows
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
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



# import whisper

# def load_whisper_model():
#     print("[INFO] Loading Whisper model...")
#     model = whisper.load_model("large")
#     return model

def transcribe_segment(audio_path):
    result = model.transcribe(audio_path)
    text = result.get("text", "").strip()
    return text
