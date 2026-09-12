# Assessment Admin Phase 2 Tools

These tools are intended for pre-pilot cleanup and template maintenance. They do not change scoring formulas and do not recalculate historical finalized attempts.

## Deactivate Or Activate Templates

Deactivate a template when it should no longer be used for new assessments but must remain available for historical attempts:

```bash
curl -X PATCH "$API_URL/api/v1/assessments/templates/{template_id}/deactivate" \
  -H "Authorization: Bearer $TOKEN"
```

Reactivate it when it is safe to use again:

```bash
curl -X PATCH "$API_URL/api/v1/assessments/templates/{template_id}/activate" \
  -H "Authorization: Bearer $TOKEN"
```

The endpoints set `is_active` only. Historical assessment attempts remain linked to the template.

## Safe Physical Delete

Templates without assessment history can be deleted:

```bash
curl -X DELETE "$API_URL/api/v1/assessments/templates/{template_id}" \
  -H "Authorization: Bearer $TOKEN"
```

The delete operation removes rows from `assessment_template_exercises` for that template, then deletes the template. It does not delete global rows from `assessment_exercises`.

If the template has assessment or exercise-attempt history, the API returns HTTP 409:

```json
{
  "detail": {
    "code": "TEMPLATE_HAS_HISTORY",
    "message": "La plantilla tiene intentos asociados y no puede eliminarse físicamente. Desactívala en su lugar.",
    "recommendation": "Usar endpoint de deactivate/archive."
  }
}
```

## Find Invalid Legacy Points

Phase 2 only accepts template-exercise `points` values `1`, `2`, or `3`. Find legacy rows outside that range:

```bash
curl "$API_URL/api/v1/assessments/admin/templates/invalid-points" \
  -H "Authorization: Bearer $TOKEN"
```

Each row includes `template_id`, `template_name`, `template_version`, `is_active`, `template_exercise_id`, `exercise_id`, `exercise_type`, `order_index`, `current_points`, and `reason`.

## Correct Points

Update a template-exercise relation to an explicit Phase 2 weight:

```bash
curl -X PATCH "$API_URL/api/v1/assessments/templates/{template_id}/exercises/{template_exercise_id}/points" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"points": 2}'
```

Allowed values are `1`, `2`, and `3`. The endpoint verifies that the relation belongs to the requested template. Existing finalized results are not recalculated.

## Mark Official Templates As Global

Global templates use `assessment_templates.created_by_teacher_id = NULL`. They are visible to all teachers and read-only from normal teacher-facing API endpoints.

Preview exact-name matches without changing data:

```bash
python scripts/admin/mark_templates_global.py \
  --template-name TAMIZAI_6A \
  --template-name TAMIZAI_9A \
  --template-name TAMIZAI_11A
```

Apply the conversion only after reviewing the dry-run output:

```bash
python scripts/admin/mark_templates_global.py \
  --template-name TAMIZAI_6A \
  --template-name TAMIZAI_9A \
  --template-name TAMIZAI_11A \
  --execute \
  --confirm-mark-global
```

The script does not create templates or exercises, change points, or activate templates. See `docs/assessment/global_templates.md` for the full visibility and mutability rules.

## Demo Data Reset Script

The reset script defaults to dry-run behavior and requires explicit confirmation:

```bash
python scripts/admin/reset_demo_assessment_data.py \
  --confirm-reset-demo-data \
  --template-name-prefix "Demo"
```

Apply the plan only after reviewing the dry-run output:

```bash
python scripts/admin/reset_demo_assessment_data.py \
  --confirm-reset-demo-data \
  --execute \
  --template-name-prefix "Demo"
```

Safety rules:

- At least one explicit filter is required: `--teacher-id`, `--template-name-prefix`, `--student-name-prefix`, or `--classroom-name-prefix`.
- Production is blocked unless `ALLOW_DEMO_DATA_RESET=true`.
- Templates without history are physically deleted.
- Templates with history are deactivated if active, or reported if already inactive.
- The script does not delete global exercises.

Once pilot data collection starts, avoid physical deletes. Prefer deactivation and explicit point correction so historical auditability remains intact.
