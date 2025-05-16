# from pyannote.audio import Pipeline
# import whisper
# from pydub import AudioSegment
# import os
# import torchaudio
# import numpy as np
# import torch
# from speechbrain.inference.speaker import EncoderClassifier
# import json
# from dotenv import load_dotenv

# # Load pyannote speaker diarization pipeline
# print("[INFO] Loading pyannote pipeline...")
# pipeline = Pipeline.from_pretrained(
#     "pyannote/speaker-diarization-3.1",
#     use_auth_token= os.getenv("HUGGINGFACE_TOKEN")
# )

# # Set device
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"[INFO] Using device: {device}")

# # Load SpeechBrain speaker recognition model
# print("[INFO] Loading SpeechBrain speaker recognizer...")
# speaker_recognizer = EncoderClassifier.from_hparams(
#     source="speechbrain/spkrec-ecapa-voxceleb",
#     run_opts={"device": str(device)}
# )

# # Load reference audio of known speaker (e.g., Salesperson)
# salesperson_audio_path = "./iasMeetHost.wav"
# print(f"[INFO] Loading reference audio: {salesperson_audio_path}")
# ref_signal, ref_fs = torchaudio.load(salesperson_audio_path)
# if ref_fs != 16000:
#     print(f"[INFO] Resampling reference audio from {ref_fs} Hz to 16000 Hz")
#     ref_signal = torchaudio.transforms.Resample(orig_freq=ref_fs, new_freq=16000)(ref_signal)
# salesperson_embedding = speaker_recognizer.encode_batch(ref_signal.to(device)).squeeze().mean(axis=0).detach().cpu().numpy()
# print("[INFO] Reference speaker embedding computed.")

# # Apply diarization on input audio
# print("[INFO] Running speaker diarization on meeting audio...")
# diarization = pipeline("./iasmeeting2.wav")

# # Load Whisper model
# print("[INFO] Loading Whisper model...")
# model = whisper.load_model("large")

# # Load full audio using pydub
# audio = AudioSegment.from_file("./iasmeeting2.wav")

# # Cosine similarity helper
# def compute_cosine_similarity(embedding1, embedding2):
#     return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

# # Track unknown speakers
# unknown_speakers = {}
# speaker_counter = 1
# results = []

# print("[INFO] Processing diarized segments...\n")

# # Process each segment
# for turn, _, speaker in diarization.itertracks(yield_label=True):
#     segment_duration = turn.end - turn.start
#     if segment_duration < 0.5:
#         print(f"[SKIP] Segment too short ({segment_duration:.2f}s), skipping.")
#         continue

#     print(f"[SEGMENT] Speaker: {speaker}, Time: {turn.start:.2f}s - {turn.end:.2f}s")

#     segment_audio = audio[turn.start * 1000: turn.end * 1000]
#     segment_path = f"temp_segment_{speaker}_{turn.start:.2f}.wav"
#     segment_audio.export(segment_path, format="wav")

#     segment_signal, segment_fs = torchaudio.load(segment_path)
#     if segment_fs != 16000:
#         print(f"[INFO] Resampling segment from {segment_fs} Hz to 16000 Hz")
#         segment_signal = torchaudio.transforms.Resample(orig_freq=segment_fs, new_freq=16000)(segment_signal)

#     segment_embedding = speaker_recognizer.encode_batch(segment_signal.to(device)).squeeze().mean(axis=0).detach().cpu().numpy()
#     similarity = compute_cosine_similarity(salesperson_embedding, segment_embedding)
#     print(f"[SIMILARITY] Score with Salesperson: {similarity:.4f}")

#     if similarity > 0.6:
#         speaker_label = "Salesperson"
#         print(f"[LABEL] Identified as: {speaker_label}")
#     else:
#         if speaker not in unknown_speakers:
#             unknown_speakers[speaker] = f"Speaker {speaker_counter}"
#             speaker_counter += 1
#         speaker_label = unknown_speakers[speaker]
#         print(f"[LABEL] Identified as: {speaker_label}")

#     result = model.transcribe(segment_path)
#     text = result.get("text", "").strip()

#     print(f"[TRANSCRIPTION] {speaker_label}: {text}\n")

#     results.append({
#         "speaker": speaker_label,
#         "start": round(turn.start, 2),
#         "end": round(turn.end, 2),
#         "text": text
#     })

#     os.remove(segment_path)

# # Save results
# with open("transcription_results.json", "w", encoding="utf-8") as f:
#     json.dump(results, f, indent=2, ensure_ascii=False)

# print("\n✅ Transcription complete. Results saved to 'transcription_results.json'.")


from fastapi import FastAPI
from src.routes.audio import router as audio_router
from src.routes.auth import router as auth_router
from src.routes.suggestion import router as suggestion_router

app = FastAPI(title="Audio Uploader with Transcription & Diarization")

app.include_router(audio_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(suggestion_router, prefix="/api/sg")
