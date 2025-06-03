from faster_whisper import WhisperModel
import tempfile
import os
import soundfile as sf
import numpy as np
import io
import wave
from pydub import AudioSegment
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
        # Create a temporary file to store the audio data
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name

        try:
            # Try to read the audio file with soundfile
            print(f"Reading audio file: {tmp_path}")
            data, samplerate = sf.read(tmp_path)
            
            # Convert to mono if stereo
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            
            # Resample to 16kHz if needed
            if samplerate != 16000:
                print(f"Resampling from {samplerate}Hz to 16000Hz")
                from scipy import signal
                samples = len(data)
                new_samples = int(samples * 16000 / samplerate)
                data = signal.resample(data, new_samples)
                samplerate = 16000
            
            # Save the processed audio
            processed_path = tmp_path + "_processed.wav"
            sf.write(processed_path, data, samplerate)
            
            print(f"Transcribing processed audio file: {processed_path}")
            segments, _ = model.transcribe(processed_path)
            full_text = ""
            for segment in segments:
                full_text += segment.text.strip() + " "
            return full_text.strip()

        finally:
            # Clean up temporary files
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(processed_path):
                os.remove(processed_path)
                
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
