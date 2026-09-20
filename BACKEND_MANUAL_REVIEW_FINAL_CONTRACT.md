# Backend Manual Review Final Contract

## 1. Resumen del flujo

El backend expone `GET /api/v1/assessments/attempts/{attempt_id}/review` como fuente principal para que Flutter pinte la revisión docente. La revisión manual modifica solo el estado canónico de scoring de un `exercise_attempt` mediante `PATCH /api/v1/assessments/exercise-attempts/{exercise_attempt_id}/manual-review`.

El baseline automático se conserva en campos `original_*`. Los campos `current_*` representan el estado vigente después de confirmaciones, ajustes, correcciones de evidencia o revert. El historial se guarda en `assessment_exercise_manual_reviews` desde el momento en que se aplica una acción manual; no se inventa historial retroactivo.

## 2. GET review

Método: `GET`

Path: `/api/v1/assessments/attempts/{attempt_id}/review`

Campos principales:

- `attempt_id`, `status`, `started_at`, `completed_at`
- `student`
- `assessment`
- `result`
- `exercise_reviews`

Cada item de `exercise_reviews` incluye, entre otros:

- `exercise_attempt_id`, `exercise_id`, `order_index`, `type`, `title`, `status`
- `score`, `original_score`, `current_score`
- `response`, `expected`, `metrics`
- `review_required`, `review_reasons`, `technical_status`, `score_eligible`, `quality_reasons`
- `scoring_components`, `original_scoring_components`, `current_scoring_components`
- `review_status`: `not_required`, `pending`, `confirmed`, `overridden`, `reverted`
- `review_version`: entero monotónico por ejercicio; inicia en `0`
- `manual_review_history`: lista de eventos manuales del ejercicio
- `metric_sources`: origen de métricas actuales cuando aplica
- `automatic_analysis`: análisis automático original disponible para speaking/writing
- `reviewed_analysis`: análisis recalculado desde evidencia corregida cuando existe
- `response.reviewed_recognized_text`: texto writing corregido por docente
- `response.reviewed_free_transcription_text`: transcripción speaking corregida por docente

## 3. PATCH manual-review

Método: `PATCH`

Path: `/api/v1/assessments/exercise-attempts/{exercise_attempt_id}/manual-review`

Path params:

- `exercise_attempt_id`: UUID del ejercicio a revisar.

Actions soportadas:

- `confirm`
- `override_metrics`
- `correct_evidence`
- `revert`

Respuesta principal:

- `exercise_attempt_id`, `exercise_type`
- `original_score`, `current_score`
- `original_metrics`, `current_metrics`
- `score_eligible`
- `manual_review_required`
- `manual_adjustment_applied`
- `review_status`
- `review_version`
- `metric_sources`
- `review_event_summary`
- `teacher_observation`
- `adjusted_by_teacher_id`, `adjusted_at`
- `assessment_result`

## 4. Request confirm

Ejemplo:

```json
{
  "action": "confirm",
  "teacher_observation": "La evidencia automática es aceptable.",
  "base_review_version": 0
}
```

Obligatorio: `action`, `teacher_observation`.

Efecto: limpia `manual_review_required`, marca `review_status="confirmed"`, incrementa `review_version`, registra evento y recalcula el resultado si ya existe.

## 5. Request override_metrics

Ejemplo speaking:

```json
{
  "action": "override_metrics",
  "metrics": {
    "accuracy_score": 90,
    "fluency_score": 85,
    "pronunciation_score": 88,
    "completeness_score": 95,
    "lexical_match": 100
  },
  "teacher_observation": "Ajuste docente.",
  "base_review_version": 0
}
```

Ejemplo writing:

```json
{
  "action": "override_metrics",
  "metrics": {
    "char_accuracy": 92,
    "word_accuracy": 88
  },
  "teacher_observation": "OCR subestimó la escritura.",
  "base_review_version": 0
}
```

Métricas permitidas:

- Speaking: `accuracy_score`, `fluency_score`, `pronunciation_score`, `completeness_score`, `lexical_match`
- Writing: `char_accuracy`, `word_accuracy`

Compatibilidad legacy: si Flutter envía un body antiguo sin `action`, el backend lo interpreta como `override_metrics`.

## 6. Request correct_evidence

Ejemplo writing:

```json
{
  "action": "correct_evidence",
  "corrections": {
    "recognized_text": "El gato duerme."
  },
  "teacher_observation": "Texto OCR corregido.",
  "base_review_version": 0
}
```

Ejemplo speaking:

```json
{
  "action": "correct_evidence",
  "corrections": {
    "free_transcription_text": "El gato duerme."
  },
  "teacher_observation": "Transcripción libre corregida.",
  "base_review_version": 0
}
```

El backend recalcula:

- Writing: `cer`, `wer`, `char_accuracy`, `word_accuracy`, `similarity_score` desde texto esperado y texto revisado.
- Speaking: `lexical_match` desde texto esperado y transcripción revisada; mantiene métricas Azure automáticas.
- `current_score`, snapshot canónico y resultado global si existe.

El backend no recalcula:

- Métricas Azure de pronunciación, fluidez, completitud o prosodia desde texto.
- Raw provider results.
- Baseline `original_*`.

## 7. Request revert

Ejemplo:

```json
{
  "action": "revert",
  "teacher_observation": "Se revierte al baseline automático.",
  "base_review_version": 1
}
```

`base_review_version` es obligatorio para `revert`.

Efecto: restaura métricas/current score desde `original_*`, limpia evidencia revisada, marca `review_status="reverted"`, incrementa `review_version`, registra evento y recalcula resultado si existe.

## 8. Versionado

- `review_version`: versión vigente del ejercicio; inicia en `0` y sube con cada acción manual.
- `base_review_version`: versión que Flutter leyó en GET review y usa para PATCH.
- `expected_review_version`: alias aceptado por compatibilidad.

Si `base_review_version` o `expected_review_version` no coincide con el estado actual:

```json
{
  "code": "MANUAL_REVIEW_VERSION_CONFLICT",
  "current_review_version": 2,
  "provided_review_version": 1
}
```

HTTP: `409 Conflict`.

## 9. Estados

- `manual_review_required`: indica revisión pendiente desde scoring/calidad.
- `review_status`: estado semántico de la revisión manual.
- `manual_adjustment_applied`: `true` cuando se modificó el resultado vigente con override/corrección.
- `technical_status`: validez técnica de la evidencia automática.
- `result_status` y `warnings`: aparecen en snapshots para advertencias del resultado.
- `intervention_level`: se calcula solo por score final: `>=80 LOW`, `>=50 MEDIUM`, `<50 HIGH`; warnings/review pending no elevan intervención.

## 10. Errores HTTP

- `400/422`: payload inválido, action no soportada o métricas/correcciones inválidas.
- `403`: perfil/permiso docente no autorizado cuando aplica.
- `404`: recurso no encontrado o no visible para el docente actual.
- `409 MANUAL_REVIEW_VERSION_CONFLICT`: conflicto de versión en PATCH.
- `409 ASSESSMENT_EVIDENCE_LOCKED`: intento de reemplazar evidencia cuando la evaluación ya fue completada o revisada.

Ejemplo de evidencia bloqueada:

```json
{
  "code": "ASSESSMENT_EVIDENCE_LOCKED",
  "message": "La evidencia no puede reemplazarse porque la evaluación ya fue completada o revisada."
}
```

## 11. Qué debe hacer Flutter

- Usar `GET review` como fuente principal de datos de revisión.
- Enviar `base_review_version` en cada PATCH.
- No enviar `teacher_id`; el backend lo resuelve desde el usuario autenticado.
- No tratar `expected_text` enviado por cliente como fuente de verdad.
- Para `correct_evidence`, enviar solo el texto corregido y dejar que backend recalcule métricas derivables.
- Mostrar `reviewed_analysis` si existe; si no, mostrar `automatic_analysis`.
- Manejar `409 MANUAL_REVIEW_VERSION_CONFLICT` refrescando `GET review`.
- Manejar `409 ASSESSMENT_EVIDENCE_LOCKED` evitando reintentos de upload sobre evidencia cerrada/revisada.
