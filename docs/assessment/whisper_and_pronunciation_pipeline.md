# Independent ASR and Pronunciation Assessment pipeline

## Purpose

Azure Pronunciation Assessment remains the source of pronunciation, accuracy,
fluency, completeness, word, phoneme, offset, and duration metrics. Its
scripted recognizer is conditioned by the reference text, so its transcript is
retained as diagnostic information and is not treated as neutral ASR.

`faster-whisper` runs locally and independently. It never receives the expected
text as an initial prompt, hotword, correction source, or fallback. Its
transcript is compared with the expected text by dynamic-programming word
alignment:

```text
WER = (substitutions + omissions + insertions) / expected word count
```

The response therefore separates:

- `recognized_text` and `stt_recognized_text`: local faster-whisper output.
- `assessment_recognized_text`: Azure's reference-conditioned transcript.
- `assessment_display_text` and `assessment_lexical_text`: detailed Azure data.
- `pronunciation_assessment`: metrics returned by Azure only.
- `comparison`: expected text versus faster-whisper only.

## Processing flow

```text
uploaded audio
    |
    +-- one temporary normalization: PCM s16le / mono / 16 kHz
            |
            +-- faster-whisper local ASR (worker thread)
            |
            +-- Azure scripted Pronunciation Assessment (worker thread)
```

The providers execute concurrently after normalization. The temporary input and
normalized files are deleted in `finally`. Audio content and full
transcriptions are not logged by the module.

If one provider fails, the contract returns a traceable `partial` response and
does not copy the successful provider's data into the failed provider's fields.
No pronunciation score is fabricated when Azure fails.

## Configuration

Recommended local CPU configuration:

```env
ASSESSMENT_STT_PROVIDER=faster_whisper
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=es
WHISPER_BEAM_SIZE=5
WHISPER_WORD_TIMESTAMPS=true
WHISPER_VAD_FILTER=false
WHISPER_MODEL_DOWNLOAD_ROOT=
WHISPER_LOW_CONFIDENCE_THRESHOLD=-1.0
```

For a CUDA deployment, set `WHISPER_DEVICE=cuda` and
`WHISPER_COMPUTE_TYPE=float16` after verifying compatible NVIDIA drivers and
CTranslate2 runtime libraries.

The model is loaded lazily and cached once per process and configuration. It is
not loaded during API startup and is not loaded per request. Each
Uvicorn/Gunicorn worker has a separate Python process and therefore its own
model copy. The first request can be substantially slower because it may
download and load model files.

`small` generally needs materially more CPU time and memory than `tiny` or
`base`. Worker count must be selected with the model's resident memory in mind;
many workers can multiply RAM consumption.

## Manual review

`review.required` is a transparent quality flag, not a clinical decision. It
can be enabled by:

- empty ASR output or high `no_speech_prob`;
- low segment log probability or low mean word probability;
- very short audio or poor segment-duration coverage;
- invalid timestamps or obvious repeated words;
- large Whisper/Azure transcript divergence;
- a partial provider failure.

Reasons are returned as stable codes such as `LOW_ASR_QUALITY`,
`ASR_AZURE_TRANSCRIPT_DIVERGENCE`, and `PRONUNCIATION_PROVIDER_FAILED`.
`confidence_heuristic` remains `null`; faster-whisper does not expose a
calibrated utterance-level confidence.

## Limitations

Neither provider is ground truth. Child speech, background noise, regional
accents, very short utterances, invented words, pseudowords, and early-literacy
pronunciations can reduce ASR accuracy. Azure scripted results remain
reference-conditioned, while Whisper can hallucinate or normalize unexpected
speech. Human review remains necessary for ambiguous cases.

The pipeline evaluates reading signals only. It must not be interpreted as a
diagnosis of dyslexia or any other clinical or educational condition.

## Diagnostics

Full pipeline:

```bash
python scripts/diagnose_assessment_pipeline.py \
  --audio audios/laperra.wav \
  --expected-text "El gato está en casa" \
  --whisper-model tiny
```

Whisper-only control:

```bash
python scripts/diagnose_assessment_pipeline.py \
  --audio audios/laperra.wav \
  --expected-text "El gato está en casa" \
  --whisper-model tiny \
  --skip-azure \
  --output-json whisper-result.json
```

The diagnostic reports model/load/inference time, total provider times, audio
duration, and approximate real-time factor. It never prints Azure credentials.

## Local validation (2026-06-27)

The full six-case matrix ran with `tiny`, CPU/int8, Spanish forced, and Azure
`es-MX`. These are observations for the supplied recordings, not accuracy
guarantees:

| Audio / expected | Whisper | Azure scripted | Whisper-based WER | Review |
|---|---|---|---:|---|
| `elgato.wav` / El gato... | El gato está en la casa. | El gato está en casa casa. | 20% | no |
| `laperra.wav` / El gato... | la pérrez está en casa | El gato está está en casa. | 40% | transcript divergence |
| `laperra.wav` / La perra... | la pérrez está en casa | La perra está en casa. | 20% | no |
| `elperro.wav` / El gato... | El perro está afuera. | El gato está. | 60% | no |
| `gatoel.wav` / El gato... | Cato, él está en casa. | Gato, El está en casa. | 40% | no |
| `elgato.mp3` / El gato... | El gato está en la casa. | El gato está en casa casa. | 20% | no |

After initial loading, `tiny` inference took 319-383 ms for 3.18-4.08 second
audio (approximate RTF 0.086-0.109). The first observed load was 783 ms from
the local cache.

The default `small` CPU/int8 control correctly returned
`La perra está en casa.` for `laperra.wav`. A repeated-process measurement
showed:

- model load from local disk cache: 1,669 ms;
- first inference: 1,805 ms, RTF 0.543;
- second inference with the same process-local model: 1,716 ms, RTF 0.516;
- process RSS: approximately 25 MB before loading and 411-415 MB after use.

Initial network download time is environment-dependent and is not included in
the cached-load figures. Production capacity planning must measure the target
CPU, recordings, model, and worker count.
