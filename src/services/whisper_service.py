from faster_whisper import WhisperModel

model = WhisperModel("base")

def transcribe_audio(file_path: str) -> str:
    segments, _ = model.transcribe(file_path)
    return " ".join([segment.text for segment in segments])
