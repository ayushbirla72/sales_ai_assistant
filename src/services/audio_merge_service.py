from pydub import AudioSegment

def merge_audio_chunks(file_paths: list, output_path: str):
    combined = AudioSegment.empty()
    for path in file_paths:
        combined += AudioSegment.from_file(path)
    combined.export(output_path, format="wav")
