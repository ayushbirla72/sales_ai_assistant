from pyannote.audio import Pipeline
from src.config import HUGGINGFACE_TOKEN

pipeline = Pipeline.from_pretrained( "pyannote/speaker-diarization-3.1",
                                    use_auth_token=HUGGINGFACE_TOKEN)

# def diarize_audio(file_path: str) -> list:
#     diarization = pipeline(file_path)
#     segments = []

#     for turn, _, speaker in diarization.itertracks(yield_label=True):
#         segments.append({
#             "start": round(turn.start, 2),
#             "end": round(turn.end, 2),
#             "speaker": speaker
#         })
#     return segments

def diarize_audio(file_path: str):
    print("[INFO] Running speaker diarization on audio...")
    diarization = pipeline(file_path)
    return diarization