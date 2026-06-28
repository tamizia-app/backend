# Writing Evaluation Metrics

## ¿Qué evalúa Writing?

El módulo Writing evalúa la producción escrita digital del estudiante en ejercicios de copia o
dictado (READING_WRITING y LISTENING_WRITING). Actualmente, la evaluación se realiza mediante:

1. **OCR (Azure AI Vision)** — extrae el texto escrito de la imagen del canvas digital.
2. **Comparación textual** — compara el texto reconocido por OCR contra el texto esperado
   (`expected_text`) que está definido en el backend como parte del ejercicio.
3. **Métricas cinestésicas** — strokes, presión, velocidad, pausas, área de escritura
   (provenientes del canvas Flutter).

## ¿Qué NO evalúa?

- No evalúa caligrafía, legibilidad visual, ni calidad del trazo individual.
- No evalúa ortografía ni gramática de forma explícita (aunque CER/WER pueden reflejar
  errores ortográficos incidentales).
- No diagnostica dislexia, trastornos del aprendizaje ni problemas de lectoescritura.
- No produce baremos clínicos por grado escolar, edad ni tipo de ejercicio.

## Advertencia

> Estas métricas son indicadores técnicos preliminares de comparación entre el texto
> esperado y el texto reconocido por OCR. No constituyen diagnóstico clínico ni
> sustituyen una evaluación profesional.

## Población objetivo

El MVP está orientado a ejercicios diseñados para estudiantes de 2.º a 4.º grado de
primaria. Sin embargo, los umbrales y puntajes actuales son baseline técnico y aún no
cuentan con baremos clínicos validados por grado, edad o tipo de ejercicio.

---

## Normalización del texto

Antes de la comparación, tanto `expected_text` como `recognized_text` se normalizan:

1. **Minúsculas** — `lower()`
2. **Trim** — `strip()`
3. **Colapsar espacios múltiples** — `\s+` → `" "`
4. **Quitar puntuación común** — `. , ; : ! ? ¿ ¡ " ' " " ( ) [ ]`
5. **Mantener `ñ`** — no se elimina
6. **Mantener tildes** — por ahora se conservan; puede ajustarse con especialistas

```python
normalize_text("El gato duerme.")  # → "el gato duerme"
```

---

## CER (Character Error Rate)

Evalúa la distancia a nivel de caracteres entre el texto normalizado esperado y el
reconocido.

### Fórmula

```
cer = levenshtein_distance(expected_normalized, recognized_normalized) / max(1, len(expected_normalized))
```

### Implementación

```python
def calculate_cer(expected: str, recognized: str) -> float:
    distance = levenshtein_distance(norm_expected, norm_recognized)
    return round(distance / max(1, len(norm_expected)), 3)
```

### Interpretación

| CER     | Significado                     |
|---------|---------------------------------|
| 0.000   | Perfect match                   |
| 0.000–0.100 | Excelente                   |
| 0.100–0.250 | Aceptable                   |
| ≥ 0.250 | Alta tasa de error (revisión)   |
| 1.000   | Completamente diferente o vacío |

---

## WER (Word Error Rate)

Evalúa la distancia a nivel de palabras. Cada palabra se tokeniza por espacio luego de
la normalización.

### Fórmula

```
wer = levenshtein_distance_words(expected_words, recognized_words) / max(1, len(expected_words))
```

Donde `levenshtein_distance_words` aplica el mismo algoritmo de Levenshtein pero
operando sobre listas de palabras (cada palabra es una unidad).

### Interpretación

| WER     | Significado                     |
|---------|---------------------------------|
| 0.000   | Perfect match                   |
| 0.000–0.333 | Baja tasa de error          |
| ≥ 0.500 | Alta tasa de error (revisión)   |
| 1.000   | Todas las palabras distintas    |

---

## similarity_score

Combinación ponderada de la precisión de caracteres y palabras.

### Fórmula

```python
char_score   = max(0.0, 100.0 * (1.0 - cer))
word_score   = max(0.0, 100.0 * (1.0 - wer))
similarity   = (0.75 * char_score) + (0.25 * word_score)
```

El peso de 75% en caracteres y 25% en palabras prioriza la precisión a nivel de letras
(apropiado para ejercicios de copia en los que el estudiante escribe palabra por
palabra).

### Interpretación

| similarity_score | Significado              |
|------------------|--------------------------|
| 100.00           | Perfect match            |
| 90.00–99.99      | Muy buena                |
| 75.00–89.99      | Buena / aceptable        |
| < 75.00          | Baja similitud (revisión)|

---

## char_accuracy y word_accuracy

Son los valores `char_score` y `word_score` individuales, reportados como métricas
derivadas (no persistidas).

```python
char_accuracy = max(0.0, 100.0 * (1.0 - cer))
word_accuracy = max(0.0, 100.0 * (1.0 - wer))
```

---

## confidence_avg

Es el promedio de confianza por palabra devuelto por Azure Vision OCR. Cada palabra
tiene un `confidence` entre 0.0 y 1.0.

- **≥ 0.90**: Confianza alta
- **0.70–0.89**: Confianza media
- **< 0.70**: Confianza baja → puede activar revisión manual

---

## review_required y review_reasons

### Reglas baseline

`review_required = true` si se cumple **alguna** de las siguientes condiciones:

| Condición                                    | Razón                      |
|----------------------------------------------|----------------------------|
| `recognized_text` vacío                     | `EMPTY_RECOGNIZED_TEXT`    |
| `confidence_avg < 0.70`                     | `LOW_OCR_CONFIDENCE`        |
| `similarity_score < 75`                     | `LOW_TEXT_SIMILARITY`       |
| `cer >= 0.25`                               | `HIGH_CHARACTER_ERROR_RATE` |
| `wer >= 0.50` **y** `char_accuracy < 85`    | `HIGH_WORD_ERROR_RATE`      |

### Advertencia sobre umbrales

> Los umbrales descritos arriba son baseline técnico. Deben ser validados y ajustados
> por especialistas en lectoescritura, psicopedagogía o neuropsicología infantil antes
> de usar estas métricas para decisiones pedagógicas o clínicas. En una fase posterior
> se debe normalizar por grado escolar, edad, tipo de ejercicio y dificultad.

---

## Ejemplo de cálculo

### Caso: falta una letra al final

```
expected_text:    "El gato duerme."
recognized_text:  "El gato duerm"
confidence_avg:   0.948
```

| Métrica          | Valor  | Cálculo                                                |
|------------------|--------|--------------------------------------------------------|
| CER              | 0.071  | 1 carácter de diferencia / 14 caracteres normalizados  |
| WER              | 0.333  | 1 palabra de diferencia / 3 palabras esperadas          |
| similarity_score | 86.31  | 0.75 × 92.86 + 0.25 × 66.67                            |
| char_accuracy    | 92.86  | max(0, 100 × (1 - 0.071))                               |
| word_accuracy    | 66.67  | max(0, 100 × (1 - 0.333))                               |
| review_required  | false  | Ninguna condición se cumple                             |

Este caso NO requiere revisión porque:
- `confidence_avg (0.948) ≥ 0.70`
- `similarity_score (86.31) ≥ 75`
- `CER (0.071) < 0.25`
- `WER (0.333) < 0.50`

---

## Integración con el scoring general (Fase 2C)

### Regla base

```python
writing_score = similarity_score
```

Writing entra al `final_score` solo cuando `similarity_score` no es `None`. Esto
significa que:

- Writing con OCR exitoso y similaridad calculada → **puntuable** (entra a
  `scored_exercises` y al denominador de `final_score`)
- Writing sin OCR o con OCR fallido → **no puntuable** (`similarity_score` es
  `None`, no afecta `final_score`)
- Writing sin OCR previo a Fase 2C → comportamiento preservado (no puntuable)

### Cálculo de final_score

```python
total_score = sum(MIC, OS, Speaking, Writing)
scored_exercises = count(ejercicios con score)
final_score = total_score / scored_exercises  # si scored_exercises > 0
max_score = scored_exercises * 100
```

### writing_average_score

```python
writing_average_score = sum(writing_scores) / len(writing_scores)
```

Donde `writing_scores` son los `similarity_score` de cada Writing con OCR
exitoso. Actualmente solo hay un Writing por assessment, pero el cálculo soporta
múltiples.

### writing_review_required_count

```python
writing_review_required_count = count(writing donde similarity_score < 75)
```

Se usa para elevar `intervention_level` (ver reglas abajo).

### Intervención por writing review

El `intervention_level` sigue la lógica existente de `_determine_intervention_level`
con los siguientes ajustes:

| Condición | Nivel |
|-----------|-------|
| `final_score ≥ 80` sin reviews | LOW |
| `final_score ≥ 80` con reviews | MEDIUM |
| `final_score ≥ 50` | MEDIUM |
| `final_score < 50` | HIGH |
| Cualquier ejercicio fallido | HIGH |
| `writing_review_required_count > 0` y `final_score < 70` y nivel MEDIUM | **HIGH** |

### Ejemplo

```
expected_text:    "El gato duerme."
recognized_text:  "El gato duerm"
similarity_score: 86.35
```

| Campo | Valor |
|-------|-------|
| `final_score` | 86.35 |
| `max_score` | 100.0 |
| `writing_completed_count` | 1 |
| `writing_average_score` | 86.35 |
| `writing_review_required_count` | 0 |
| `intervention_level` | LOW |
| `total_exercises` | 1 |
| `evaluated_exercises` | 1 |
| `pending_exercises` | 0 |

### Assessment mixto

Si hay MC=100, OS=100, Speaking=90, Writing=86.35:

```python
scored_exercises = 4
total_score = 100 + 100 + 90 + 86.35 = 376.35
final_score = 376.35 / 4 = 94.09
max_score = 400
```

### Advertencia

> `review_required` no constituye diagnóstico. Solo marca la necesidad de que
> un docente revise manualmente la respuesta escrita. Los umbrales siguen siendo
> baseline técnico para MVP y deben calibrarse por grado escolar, edad y criterio
> profesional en una fase posterior.

---

## Referencias

- `app/assessment/domain/writing_text_comparison.py` — implementación de CER, WER,
  similarity_score y reglas de revisión
- `app/assessment/application/use_cases/upload_writing_response.py` — punto de
  integración (OCR + comparación textual)
- `app/assessment/presentation/schemas.py` — `WritingMetricsResponse` con todos los
  campos de evaluación
- `app/assessment/domain/metrics.py` — `WritingMetrics` dominio con `cer`, `wer`,
  `similarity_score`, `confidence_avg`
