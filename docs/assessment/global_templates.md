# Global Assessment Templates

TamizAI uses `assessment_templates.created_by_teacher_id = NULL` to represent a global or official assessment template for the pilot.

## Visibility Rules

A template is visible to a teacher when:

- `is_active = true`
- and either `created_by_teacher_id` matches the teacher id or `created_by_teacher_id IS NULL`

Global templates are visible to every teacher. Private templates are visible only to their owner.

## Public API Behavior

Normal teacher-facing endpoints keep the current response contract. The nullable `created_by_teacher_id` field is enough for clients to distinguish global templates if they need to.

- `GET /api/v1/assessments/templates` returns active global templates and active templates owned by the authenticated teacher.
- `GET /api/v1/assessments/templates/{template_id}` returns active global templates and active templates owned by the authenticated teacher.
- `POST /api/v1/assessments` accepts active global templates and active templates owned by the authenticated teacher.
- Template mutation endpoints are owner-only and reject global templates for normal teachers.

These endpoints intentionally return the same not-found response for inaccessible, inactive, or missing templates so private template ids are not leaked.

## Read-Only Global Templates

Global templates are read-only from the public API. Normal teachers cannot:

- deactivate or activate global templates;
- delete global templates;
- update template-exercise points on global templates;
- attach exercises to global templates.

Teachers can still create and maintain their own private templates through the existing endpoints.

## Administrative Conversion

Use the administrative CLI script to mark existing official templates as global by exact name. The script is dry-run by default:

```bash
python scripts/admin/mark_templates_global.py \
  --template-name TAMIZAI_6A \
  --template-name TAMIZAI_9A \
  --template-name TAMIZAI_11A
```

Apply the reviewed plan with explicit confirmation:

```bash
python scripts/admin/mark_templates_global.py \
  --template-name TAMIZAI_6A \
  --template-name TAMIZAI_9A \
  --template-name TAMIZAI_11A \
  --execute \
  --confirm-mark-global
```

The script only updates matching existing templates by exact name. It does not create exercises, create templates, change points, or activate inactive templates.

## Known Trade-Off

Using `NULL` as global scope avoids a schema migration for the pilot, but it gives `created_by_teacher_id` two meanings: official global template and owner removed by foreign-key `ON DELETE SET NULL`. A future production version should add an explicit `visibility` or `scope` column and migrate official templates to that field.
