import io, base64, speech_recognition as sr
from pydub import AudioSegment

recognizer = sr.Recognizer()

def transcribe_audio_base64(audio_base64: str) -> str:
    audio_bytes = base64.b64decode(audio_base64)
    try:
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
    except Exception:
        try:
            seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
        except Exception as e:
            raise ValueError(f"Could not decode audio: {e}")
    buf = io.BytesIO()
    seg.export(buf, format="wav")
    buf.seek(0)
    with sr.AudioFile(buf) as src:
        audio_data = recognizer.record(src)
    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        raise ValueError("Could not understand audio. Please speak clearly.")
    except sr.RequestError as e:
        raise ConnectionError(f"Speech recognition error: {e}")
