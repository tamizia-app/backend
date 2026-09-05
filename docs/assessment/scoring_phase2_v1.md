# TamizAI Scoring Phase 2 v1

`scoring_version = "phase2_v1"` keeps scores on a 0-100 scale, where a higher value means better task performance. The risk/intervention interpretation is orientative and inverse to performance: lower performance scores imply higher technical attention. TamizAI does not diagnose dyslexia or any clinical condition.

## ReadingScore v2

Reading exercises use a weighted score:

```text
ReadingScore =
0.25 * accuracy_score +
0.25 * fluency_score +
0.20 * pronunciation_score +
0.15 * completeness_score +
0.15 * lexical_match
```

Each component is expected on a 0-100 scale. If a component is missing, it is excluded and the available weights are renormalized. Missing values are not converted to zero. If no component is available, the ReadingScore is `None`.

`fluency_score` participates in the score starting in Phase 2 v1. Auxiliary metrics such as WER, prosody, diagnostics and review reasons remain traceability data and are not removed from responses.

## WritingScore

Writing keeps the current formula:

```text
WritingScore = 0.75 * CharAccuracy + 0.25 * WordAccuracy
```

OCR confidence, duration, strokes, pauses, speed, pressure and writing area usage remain technical quality or audit signals. They do not change the numeric WritingScore in this phase.

## Template Exercise Points

`points` is now the relative weight of an exercise inside its template:

```text
1 = low or complementary importance
2 = medium importance
3 = high importance
```

New template-exercise attachments only accept `points` values 1, 2 or 3. The default is 2.

Legacy templates may still contain older values such as `points = 10`. Phase 2 v1 does not silently map those values. Attempts based on templates with invalid points are blocked at finalization with a clear error so the template can be corrected before pilot use.

Use the Phase 2 admin tools to list and correct invalid legacy `points` before using templates in pilot flows. Correcting template-exercise points affects future scoring for that template relation; finalized historical results are not recalculated.

## FinalScore

The final score is a weighted mean of eligible exercise scores:

```text
FinalScore = sum(score_i * points_i) / sum(points_i)
```

Only exercises with a canonical ExerciseScore, `score_eligible = true`, and a non-null score enter the calculation. Required exercises without eligible scores continue to block finalization. Optional exercises without eligible scores are excluded.

`score_denominator` is kept only for backward compatibility and is deprecated as an ambiguous field. Starting in Phase 2 v1 it is an alias of `included_weight_sum`; it stores the sum of included exercise weights, not the number of included exercises. New clients should read `score_denominator_type = "included_weight_sum"` and `score_denominator_deprecated = true`.

Use `included_exercise_count` and `total_exercise_count` for exercise counts. Use `coverage_weight_percentage` for weighted technical coverage. `max_score` remains 100.0 and the stored final score is rounded to two decimals.

## Traceability And Coverage

Each snapshot row includes Phase 2 traceability: scoring version, exercise and template-exercise IDs, exercise type, order, required flag, points, inclusion/exclusion state, technical status, review flags, quality reasons, scoring components, weighted contribution and effective weight.

The main result response and snapshot rows include coverage audit fields:

```text
included_weight_sum
total_template_weight_sum
coverage_weight_percentage
included_exercise_count
total_exercise_count
invalid_or_excluded_exercise_count
score_denominator_type
score_denominator_deprecated
```

`technical_status` and `score_eligible` keep technical evidence quality separate from student performance. A technically invalid sample should not be interpreted as poor student performance.

If a required exercise is missing an eligible score, the attempt does not produce a global interpretable result and no partial `AssessmentResult` is created. If an optional exercise is technically invalid or not score-eligible, it is excluded from FinalScore and the lower weighted coverage is exposed in the result.

## Intervention Level

The existing LOW / MEDIUM / HIGH thresholds remain provisional and technical in Phase 2 v1. They use the new weighted FinalScore but are not clinical baremos and are not adjusted by age or grade yet.
