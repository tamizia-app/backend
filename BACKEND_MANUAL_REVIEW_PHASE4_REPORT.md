# Backend Manual Review Phase 4 Report

## 1. Resumen

Fase 4 cerró el feature con hardening mínimo: bloqueo de reemplazo silencioso de evidencia, verificación de propiedad docente en endpoints de speaking/writing y documentación final para Flutter. No se cambiaron fórmulas de scoring, no se agregó versionado de evidencia, no se tocaron raw provider results y no se creó migración.

## 2. Archivos modificados

- `app/assessment/application/exceptions.py`
- `app/assessment/application/use_cases/upload_speaking_response.py`
- `app/assessment/application/use_cases/upload_writing_response.py`
- `app/assessment/presentation/routes.py`
- `tests/test_assessment.py`
- `BACKEND_MANUAL_REVIEW_FINAL_CONTRACT.md`
- `BACKEND_MANUAL_REVIEW_PHASE4_REPORT.md`

## 3. Migraciones creadas

Ninguna. La fase usa columnas ya existentes: `review_status`, `review_version`, `manual_adjustment_applied` y el historial `assessment_exercise_manual_reviews`.

## 4. Protección contra reemplazo de evidencia

Se agregó `AssessmentEvidenceLockedError` con HTTP `409` y código `ASSESSMENT_EVIDENCE_LOCKED`.

Speaking y writing rechazan uploads antes de subir archivo o recalcular proveedores si:

- `AssessmentAttempt.status == COMPLETED`
- `review_version > 0`
- `manual_adjustment_applied == true`
- `review_status in ("confirmed", "overridden", "reverted")`

El mensaje devuelto es:

```json
{
  "code": "ASSESSMENT_EVIDENCE_LOCKED",
  "message": "La evidencia no puede reemplazarse porque la evaluación ya fue completada o revisada."
}
```

El re-upload antes de finish/review se mantiene compatible.

## 5. Autorización revisada/corregida

`GET /speaking-response`, `POST /speaking-response`, `GET /writing-response` y `POST /writing-response` ahora validan que el `exercise_attempt_id` pertenezca a una evaluación cuyo `homeroom_teacher_id` coincide con el docente autenticado.

La validación usa el patrón existente de ocultar recursos ajenos con `404`.

Rutas ya protegidas o verificadas:

- `GET /attempts/{attempt_id}/review`: valida alumno/aula del docente actual.
- `PATCH /exercise-attempts/{exercise_attempt_id}/manual-review`: el use case valida que la evaluación pertenezca al docente.

## 6. Paridad finish/manual-review

Se revisó la equivalencia entre finish y manual-review:

- Ambos usan score canónico por ejercicio.
- Ambos calculan final con media ponderada por `template_exercise.points`.
- Ambos incluyen scores elegibles y `PARTIAL`.
- Ambos mantienen `score_denominator` como suma de pesos incluidos.
- `intervention_level` depende solo del score final: `>=80 LOW`, `>=50 MEDIUM`, `<50 HIGH`.
- Warnings/review pending no elevan intervention level.
- `manual-review` recalcula `AssessmentResult` si ya existe.
- `revert` restaura current score/metrics desde baseline y recalcula result.

No se hizo refactor compartido porque implicaría tocar dos use cases sensibles; la lógica actual ya está alineada y cubierta por tests.

## 7. Listening/tipos mixtos

Los enums `LISTENING_SPEAKING` y `LISTENING_WRITING` existen y los flujos de upload/finish/GET review los contemplan.

La revisión manual sigue limitada a `READING_SPEAKING` y `READING_WRITING`. No se agregó soporte nuevo para listening en manual review porque no era trivial ni pedido como cambio funcional seguro para Fase 4.

GET review/result conserva ejercicios no revisados y tipos mixtos existentes porque itera todos los exercise attempts del intento.

## 8. Contrato final Flutter

Creado: `BACKEND_MANUAL_REVIEW_FINAL_CONTRACT.md`.

Incluye:

- Flujo de revisión manual.
- Contrato GET review.
- Contrato PATCH manual-review.
- Ejemplos de `confirm`, `override_metrics`, `correct_evidence`, `revert`.
- Versionado y conflicto `MANUAL_REVIEW_VERSION_CONFLICT`.
- Estados.
- Errores HTTP, incluido `ASSESSMENT_EVIDENCE_LOCKED`.
- Recomendaciones concretas para Flutter.

## 9. Tests agregados/ajustados

Agregados o endurecidos en `tests/test_assessment.py`:

- Speaking upload después de `COMPLETED` devuelve `ASSESSMENT_EVIDENCE_LOCKED`.
- Writing upload después de `COMPLETED` devuelve `ASSESSMENT_EVIDENCE_LOCKED`.
- Speaking upload después de `review_version > 0` falla y preserva evidencia previa.
- Writing upload después de `review_version > 0` falla y preserva evidencia previa.
- Docente ajeno no puede hacer POST/GET speaking response.
- Docente ajeno no puede hacer POST/GET writing response.
- Docente ajeno no puede hacer PATCH manual-review.
- GET review teacher isolation ahora usa un attempt real, no un UUID aleatorio.

Tests existentes mantienen cobertura de:

- `confirm`
- `override_metrics`
- `correct_evidence`
- `revert`
- historial y versionado en GET review
- current final score/intervention level
- tipos mixtos en result/review

## 10. Resultado de tests

Ejecutado:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_manual_metric_review.py tests\test_scoring_phase2.py tests\test_assessment.py
```

Resultado:

- `195 passed`
- Warnings conocidos: `StarletteDeprecationWarning`, `InsecureKeyLengthWarning`.

Ejecutado:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Resultado:

- `304 passed`
- Warnings conocidos: `StarletteDeprecationWarning`, `InsecureKeyLengthWarning`.

## 11. Limitaciones restantes

- Manual review no soporta todavía `LISTENING_SPEAKING` ni `LISTENING_WRITING`.
- No hay idempotency keys por decisión explícita.
- No hay versionado de evidencia física.
- No hay historial retroactivo para revisiones anteriores a Fase 3.
- No se recalculan métricas Azure desde texto corregido.
- No se hizo refactor profundo para compartir cálculo finish/manual-review.

## 12. Recomendación antes de merge a main

- Revisar Swagger para confirmar que los schemas `ManualReviewRequest`, `ManualReviewResponse` y `ReviewResultResponse` se ven correctamente.
- Probar manualmente un flujo completo en ambiente local/staging: upload, finish, GET review, confirm, override, correct_evidence, revert, reintento de upload bloqueado.
- Verificar que Flutter maneje `409 MANUAL_REVIEW_VERSION_CONFLICT` y `409 ASSESSMENT_EVIDENCE_LOCKED`.
- Mantener listening manual review fuera de este merge salvo que se defina contrato específico.

## 13. Checklist de validación Swagger final

- `GET /api/v1/assessments/attempts/{attempt_id}/review` muestra `review_status`.
- Muestra `review_version`.
- Muestra `manual_review_history`.
- Muestra `metric_sources`.
- Muestra `automatic_analysis`.
- Muestra `reviewed_analysis`.
- Muestra `reviewed_recognized_text` para writing.
- Muestra `reviewed_free_transcription_text` para speaking.
- `PATCH /manual-review` acepta `action`.
- `PATCH /manual-review` acepta `metrics`.
- `PATCH /manual-review` acepta `corrections`.
- `PATCH /manual-review` acepta `base_review_version` y `expected_review_version`.
- Errores 409 documentados en Swagger/OpenAPI o en contrato Flutter.
