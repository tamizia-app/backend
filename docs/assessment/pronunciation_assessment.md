# Pronunciation Assessment diagnostics

The assessment adapter performs scripted Azure Speech Pronunciation Assessment
with `HundredMark`, phoneme granularity, and miscue detection enabled. The
recognition locale defaults to `es-MX` and can be configured with
`AZURE_SPEECH_ASSESSMENT_LOCALE`. For Spanish, compare `es-MX` and `es-ES`;
`es-PE` is not assumed to be interchangeable.

`recognized_text` comes from the SDK recognition result (`result.text`), with
Azure's real detailed display text as fallback. It is never reconstructed from
the reference words. `assessment_display_text`, `assessment_lexical_text`, and
`expected_text` remain separate.

Spanish prosody is returned as `null` with `prosody_supported: false`, because
Azure documents prosody assessment as available only for `en-US`.

## Audio

Azure receives PCM signed 16-bit little-endian, mono, 16000 Hz WAV. Compliant
WAV input is passed through. Other recognized audio is converted in temporary
files with FFmpeg; originals are not changed. A missing FFmpeg executable or a
failed conversion produces an explicit assessment audio error.

Repository sample properties:

| File | Codec | Rate | Channels | Bits | Duration |
|---|---|---:|---:|---:|---:|
| `elgato.wav` | PCM s16le | 16000 | 1 | 16 | 3716 ms |
| `elperro.wav` | PCM s16le | 16000 | 1 | 16 | 3179 ms |
| `gatoel.wav` | PCM s16le | 16000 | 2 | 16 | 4079 ms |
| `laperra.wav` | PCM s16le | 16000 | 2 | 16 | 3324 ms |
| `elgato.mp3` | MP3 | 44100 | 2 | n/a | 3716 ms |

## Commands

```bash
python scripts/diagnose_pronunciation_assessment.py \
  --audio audios/laperra.wav \
  --expected-text "El gato está en casa" \
  --locale es-MX
```

```bash
python scripts/diagnose_pronunciation_assessment.py \
  --audio audios/elgato.wav \
  --expected-text "El gato está en casa" \
  --compare-locales \
  --output-json assessment-diagnostic.json
```

## Comparative run (2026-06-27)

SDK 1.50.0 was run against the configured Azure resource. Scores are ordered
as accuracy / fluency / completeness / pronunciation.

| Audio | Reference | Locale | `result.text` | Scores | Lexical comparison |
|---|---|---|---|---|---|
| `elgato.wav` | El gato está en casa | es-MX | El gato está en casa casa. | 97 / 94 / 100 / 95.8 | 5 match, 1 insertion, WER 20% |
| `elgato.wav` | El gato está en casa | es-ES | El gato está en casa casa. | 100 / 95 / 100 / 97 | 5 match, 1 insertion, WER 20% |
| `laperra.wav` | El gato está en casa | es-MX | El gato está está en casa. | 85 / 59 / 80 / 68.4 | 5 match, 1 insertion, WER 20% |
| `laperra.wav` | El gato está en casa | es-ES | Casa está en casa. | 60 / 76 / 60 / 63.2 | 3 match, 1 substitution, 1 omission, WER 40% |
| `elperro.wav` | El gato está en casa | es-MX | El gato está. | 48 / 72 / 40 / 48 | 3 match, 2 omissions, WER 40% |
| `gatoel.wav` | El gato está en casa | es-MX | Gato, El está en casa. | 78 / 75 / 80 / 76.6 | 3 match, 2 substitutions, WER 40% |

The MP3 control (`elgato.mp3`, es-MX) was normalized and produced the same
recognized text and scores as `elgato.wav`, so its source encoding is not the
cause of the observed transcription.

The decisive control used `laperra.wav` with `La perra está en casa` as its
reference. Scripted assessment then returned exactly `La perra está en casa.`
with a pronunciation score of 98.2. With the mismatched `El gato...` reference,
the same audio and locale returned `El gato está está en casa.`. Standard
speech-to-text without the pronunciation configuration returned
`La PR está en casa.`. This demonstrates reference-conditioned recognition in
scripted Pronunciation Assessment, not response reconstruction by this backend.

The primary classification is `AZURE_RECOGNITION_LIMITATION`: scripted
assessment is designed to align audio to a known reading script, so its
recognized text is not a reliable independent transcript when the speaker says
different words. `es-MX` and `es-ES` also differ materially on mismatched
speech, making `LOCALE_MODEL_MISMATCH` a secondary factor. Audio encoding is
ruled out for the compliant mono samples and for the normalized WAV/MP3
controls.
