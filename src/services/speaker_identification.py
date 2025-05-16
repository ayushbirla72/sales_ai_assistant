from pyannote.audio import Pipeline
import whisper
from pydub import AudioSegment
import os
import torchaudio
import numpy as np
import torch
from speechbrain.inference.speaker import EncoderClassifier
import json
from src.config import HUGGINGFACE_TOKEN
# from faster_whisper import WhisperModel

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load global models
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=HUGGINGFACE_TOKEN
)
speaker_recognizer = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    run_opts={"device": str(device)}
)
whisper_model = whisper.load_model("large")
# whisper_model = WhisperModel("base")


def transcribe_audio(file_path: str) -> str:
    segments, _ = whisper_model.transcribe(file_path)
    return " ".join([segment.text for segment in segments])



def load_reference_embedding(audio_path: str) -> np.ndarray:
    ref_signal, ref_fs = torchaudio.load(audio_path)
    if ref_fs != 16000:
        ref_signal = torchaudio.transforms.Resample(orig_freq=ref_fs, new_freq=16000)(ref_signal)
    embedding = speaker_recognizer.encode_batch(ref_signal.to(device)).squeeze().mean(axis=0).detach().cpu().numpy()
    return embedding


def run_diarization(audio_path: str):
    return pipeline(audio_path)


def get_segment_embedding(segment_path: str) -> np.ndarray:
    signal, fs = torchaudio.load(segment_path)
    if fs != 16000:
        signal = torchaudio.transforms.Resample(orig_freq=fs, new_freq=16000)(signal)
    embedding = speaker_recognizer.encode_batch(signal.to(device)).squeeze().mean(axis=0).detach().cpu().numpy()
    return embedding


def compute_cosine_similarity(e1, e2) -> float:
    return np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))


def identify_speaker(segment_embedding: np.ndarray, ref_embedding: np.ndarray, speaker: str, unknown_speakers: dict, counter: int):
    similarity = compute_cosine_similarity(ref_embedding, segment_embedding)
    print(f"[SIMILARITY] Score with Salesperson: {similarity:.4f}")
    if similarity > 0.6:
        print(f"[LABEL] Identified as: Salesperson")
        return "Salesperson", counter
    else:
        if speaker not in unknown_speakers:
            unknown_speakers[speaker] = f"Speaker {counter}"
            counter += 1
            print(f"[LABEL] Identified as: { unknown_speakers[speaker]}")
        return unknown_speakers[speaker], counter


def transcribe_audio(path: str) -> str:
    result = whisper_model.transcribe(path)
    return result.get("text", "").strip()


def process_segments(diarization, audio_path: str, ref_embedding: np.ndarray):
    audio = AudioSegment.from_file(audio_path)
    unknown_speakers = {}
    counter = 1
    results = []

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        duration = turn.end - turn.start
        if duration < 0.5:
            segment_duration = turn.end - turn.start
            print(f"[SKIP] Segment too short ({segment_duration:.2f}s)skipping.")
            continue

        print(f"[SEGMENT] Speaker: {speaker}, Time: {turn.start:.2f}s - {turn.end:.2f}s")
        segment = audio[turn.start * 1000: turn.end * 1000]
        temp_path = f"temp_{speaker}_{turn.start:.2f}.wav"
        segment.export(temp_path, format="wav")

        segment_embedding = get_segment_embedding(temp_path)
        speaker_label, counter = identify_speaker(segment_embedding, ref_embedding, speaker, unknown_speakers, counter)
        text = transcribe_audio(temp_path)

        results.append({
            "speaker": speaker_label,
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "text": text
        })

        os.remove(temp_path)

    return results