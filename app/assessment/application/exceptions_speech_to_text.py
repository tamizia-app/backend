class SpeechToTextError(Exception):
    code = "STT_ERROR"
    public_message = "Local speech transcription failed."


class WhisperModelUnavailableError(SpeechToTextError):
    code = "WHISPER_MODEL_UNAVAILABLE"
    public_message = "The configured Whisper model is unavailable."


class WhisperModelLoadError(SpeechToTextError):
    code = "WHISPER_MODEL_LOAD_ERROR"
    public_message = "The Whisper model could not be loaded or downloaded."


class WhisperDeviceError(SpeechToTextError):
    code = "WHISPER_DEVICE_ERROR"
    public_message = "The configured Whisper device or compute type is unavailable."


class WhisperOutOfMemoryError(SpeechToTextError):
    code = "WHISPER_OUT_OF_MEMORY"
    public_message = "There is not enough memory to run the Whisper model."


class WhisperInferenceError(SpeechToTextError):
    code = "WHISPER_INFERENCE_ERROR"
    public_message = "Whisper could not transcribe the audio."
