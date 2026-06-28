from __future__ import annotations

from app.assessment.application.ports.speech_to_text import TranscriptionResult
from app.assessment.domain.text_comparison import compare_texts, tokenize


def determine_manual_review(
    transcription: TranscriptionResult | None,
    *,
    azure_text: str | None,
    audio_duration_seconds: float | None,
    low_logprob_threshold: float,
    stt_failed: bool = False,
    azure_failed: bool = False,
    evaluation_status: str | None = None,
    pronunciation_score: float | None = None,
    accuracy_score: float | None = None,
    completeness_score: float | None = None,
    comparison: dict | None = None,
) -> dict:
    reasons: list[str] = []
    if stt_failed:
        reasons.append("STT_PROVIDER_FAILED")
    if azure_failed:
        reasons.append("PRONUNCIATION_PROVIDER_FAILED")
    if transcription is None:
        return {"required": True, "reasons": reasons or ["EMPTY_ASR_TRANSCRIPTION"]}

    if not transcription.text.strip():
        reasons.append("EMPTY_ASR_TRANSCRIPTION")
    no_speech_values = [
        segment.no_speech_prob
        for segment in transcription.segments
        if segment.no_speech_prob is not None
    ]
    if no_speech_values and max(no_speech_values) >= 0.6:
        reasons.append("HIGH_NO_SPEECH_PROBABILITY")

    logprobs = [
        segment.avg_logprob
        for segment in transcription.segments
        if segment.avg_logprob is not None
    ]
    if logprobs and sum(logprobs) / len(logprobs) < low_logprob_threshold:
        reasons.append("LOW_ASR_QUALITY")

    word_probabilities = [
        word.probability
        for segment in transcription.segments
        for word in segment.words
        if word.probability is not None
    ]
    if word_probabilities and sum(word_probabilities) / len(word_probabilities) < 0.5:
        reasons.append("LOW_WORD_PROBABILITY")

    if audio_duration_seconds is not None and audio_duration_seconds < 0.5:
        reasons.append("AUDIO_TOO_SHORT")
    if transcription.segments and audio_duration_seconds:
        covered_until = max(segment.end_seconds for segment in transcription.segments)
        if abs(audio_duration_seconds - covered_until) > max(1.0, audio_duration_seconds * 0.5):
            reasons.append("AUDIO_SEGMENT_DURATION_MISMATCH")

    if _has_invalid_timestamps(transcription, audio_duration_seconds):
        reasons.append("INVALID_WORD_TIMESTAMPS")
    if _has_obvious_repetition(transcription.text):
        reasons.append("ASR_REPETITION")

    if transcription.text.strip() and azure_text and azure_text.strip():
        divergence = compare_texts(transcription.text, azure_text)
        if divergence.wer is not None and divergence.wer >= 0.6:
            reasons.append("ASR_AZURE_TRANSCRIPT_DIVERGENCE")

    if evaluation_status == "partial":
        reasons.append("PARTIAL_EVALUATION")
    elif evaluation_status == "failed":
        reasons.append("FAILED_EVALUATION")

    if comparison:
        wer_pct = comparison.get("wer_percentage")
        if wer_pct is not None and wer_pct >= 40:
            reasons.append("HIGH_WORD_ERROR_RATE")
        lexical_match = comparison.get("lexical_match_percentage")
        if lexical_match is not None and lexical_match < 70:
            reasons.append("LOW_LEXICAL_MATCH")

    if pronunciation_score is not None and pronunciation_score < 70:
        reasons.append("LOW_PRONUNCIATION_SCORE")
    if accuracy_score is not None and accuracy_score < 70:
        reasons.append("LOW_ACCURACY_SCORE")
    if completeness_score is not None and completeness_score < 70:
        reasons.append("LOW_COMPLETENESS_SCORE")

    return {"required": bool(reasons), "reasons": list(dict.fromkeys(reasons))}


def _has_invalid_timestamps(
    transcription: TranscriptionResult,
    audio_duration_seconds: float | None,
) -> bool:
    for segment in transcription.segments:
        if segment.start_seconds < 0 or segment.end_seconds < segment.start_seconds:
            return True
        for word in segment.words:
            if word.start_seconds is None or word.end_seconds is None:
                continue
            if word.start_seconds < 0 or word.end_seconds < word.start_seconds:
                return True
            if audio_duration_seconds and word.end_seconds > audio_duration_seconds + 1:
                return True
    return False


def _has_obvious_repetition(text: str) -> bool:
    words = [token.normalized for token in tokenize(text)]
    return any(words[index] == words[index + 1] == words[index + 2] for index in range(len(words) - 2))
