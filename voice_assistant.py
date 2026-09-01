"""Dukan AI - Voice Assistant
Speech-to-text input and Urdu text-to-speech output.
"""
import io
import tempfile
from gtts import gTTS
import config

try:
    import speech_recognition as sr
    _recogniser = sr.Recognizer()
    _HAS_SR = True
except ImportError:
    _HAS_SR = False


def is_voice_available() -> bool:
    return _HAS_SR


def listen(timeout: int = 5) -> str:
    if not _HAS_SR:
        return "⚠ Voice input not available. Install SpeechRecognition and PyAudio."

    try:
        with sr.Microphone() as source:
            _recogniser.adjust_for_ambient_noise(source, duration=0.5)
            audio = _recogniser.listen(source, timeout=timeout)

        try:
            return _recogniser.recognize_google(audio, language="ur-PK")
        except sr.UnknownValueError:
            return _recogniser.recognize_google(audio, language="en-PK")
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return "⚠ Could not understand audio. Please speak more clearly."
    except sr.RequestError as e:
        return f"⚠ Speech service error: {e}"
    except OSError:
        return "⚠ No microphone found. Please connect a microphone."


def text_to_speech_bytes(text: str, lang: str = None) -> bytes:
    lang = lang or config.VOICE_LANG
    tts = gTTS(text=text, lang=lang, slow=config.VOICE_SLOW)
    buffer = io.BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def text_to_speech_file(text: str, lang: str = None) -> str:
    lang = lang or config.VOICE_LANG
    tts = gTTS(text=text, lang=lang, slow=config.VOICE_SLOW)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    return tmp.name
