"""seed demo templates and exercises (MC, OS, Reading, Listening)

Revision ID: 20260628_0009
Revises: 20260328_0008
Create Date: 2026-06-28 12:00:00
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Session

import hashlib


revision = "20260628_0009"
down_revision = "20260328_0008"
branch_labels = None
depends_on = None

NAMESPACE_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


def _uid(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE_UUID, name)


def _now() -> datetime:
    return datetime.now(UTC)


DEMO_USER_UUID = _uid("demo-user")
DEMO_TEACHER_UUID = _uid("demo-teacher")

TEMPLATE_MC_UUID = _uid("template-mc")
TEMPLATE_OS_UUID = _uid("template-os")
TEMPLATE_RS_UUID = _uid("template-rs")
TEMPLATE_RW_UUID = _uid("template-rw")
TEMPLATE_LS_UUID = _uid("template-ls")
TEMPLATE_LW_UUID = _uid("template-lw")
TEMPLATE_MIX_UUID = _uid("template-mix")

EX_MC_PREFIX = "ex-mc"
EX_OS_PREFIX = "ex-os"
EX_RS_PREFIX = "ex-rs"
EX_RW_PREFIX = "ex-rw"
EX_LS_PREFIX = "ex-ls"
EX_LW_PREFIX = "ex-lw"

TEMPLATE_MC_EXERCISES = [
    (f"{EX_MC_PREFIX}-1", "[DEMO] MC - ¿Qué animal aparece en la imagen?", "Selecciona la respuesta correcta.", "IMAGE", "MULTIPLE_CHOICE", 1),
    (f"{EX_MC_PREFIX}-2", "[DEMO] MC - ¿Qué objeto se usa para escribir?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 1),
    (f"{EX_MC_PREFIX}-3", "[DEMO] MC - ¿Qué fruta es amarilla?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 2),
    (f"{EX_MC_PREFIX}-4", "[DEMO] MC - ¿Qué animal ladra?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 1),
    (f"{EX_MC_PREFIX}-5", "[DEMO] MC - ¿Qué usamos para leer?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 1),
    (f"{EX_MC_PREFIX}-6", "[DEMO] MC - ¿Qué hay en el cielo durante el día?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 2),
    (f"{EX_MC_PREFIX}-7", "[DEMO] MC - ¿Qué objeto sirve para sentarse?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 1),
    (f"{EX_MC_PREFIX}-8", "[DEMO] MC - ¿Qué animal dice 'miau'?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 1),
    (f"{EX_MC_PREFIX}-9", "[DEMO] MC - ¿Qué usamos para tomar agua?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 2),
    (f"{EX_MC_PREFIX}-10", "[DEMO] MC - ¿Qué medio tiene ruedas?", "Selecciona la respuesta correcta.", "TEXT", "MULTIPLE_CHOICE", 1),
]

MC_OPTIONS = [
    ("Gato", True), ("Perro", False), ("Casa", False),
    ("Lápiz", True), ("Zapato", False), ("Pelota", False),
    ("Plátano", True), ("Mesa", False), ("Auto", False),
    ("Perro", True), ("Pato", False), ("Silla", False),
    ("Libro", True), ("Cuchara", False), ("Balón", False),
    ("Sol", True), ("Zapato", False), ("Pez", False),
    ("Silla", True), ("Manzana", False), ("Lápiz", False),
    ("Gato", True), ("Vaca", False), ("Perro", False),
    ("Vaso", True), ("Cuaderno", False), ("Puerta", False),
    ("Auto", True), ("Nube", False), ("Árbol", False),
]

TEMPLATE_OS_EXERCISES = [
    (f"{EX_OS_PREFIX}-1", "[DEMO] OS - Ordenar sílabas: casa", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 1, "casa", ["sa", "ca"]),
    (f"{EX_OS_PREFIX}-2", "[DEMO] OS - Ordenar sílabas: gato", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 1, "gato", ["to", "ga"]),
    (f"{EX_OS_PREFIX}-3", "[DEMO] OS - Ordenar sílabas: mesa", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 1, "mesa", ["sa", "me"]),
    (f"{EX_OS_PREFIX}-4", "[DEMO] OS - Ordenar sílabas: perro", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 1, "perro", ["rro", "pe"]),
    (f"{EX_OS_PREFIX}-5", "[DEMO] OS - Ordenar sílabas: luna", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 1, "luna", ["na", "lu"]),
    (f"{EX_OS_PREFIX}-6", "[DEMO] OS - Ordenar sílabas: pelota", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 2, "pelota", ["ta", "lo", "pe"]),
    (f"{EX_OS_PREFIX}-7", "[DEMO] OS - Ordenar sílabas: camisa", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 2, "camisa", ["sa", "mi", "ca"]),
    (f"{EX_OS_PREFIX}-8", "[DEMO] OS - Ordenar sílabas: zapato", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 2, "zapato", ["to", "pa", "za"]),
    (f"{EX_OS_PREFIX}-9", "[DEMO] OS - Ordenar sílabas: escuela", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 2, "escuela", ["la", "cue", "es"]),
    (f"{EX_OS_PREFIX}-10", "[DEMO] OS - Ordenar sílabas: mariposa", "Ordena las sílabas para formar la palabra correcta.", "TEXT", "ORDER_SYLLABLES", 2, "mariposa", ["sa", "po", "ri", "ma"]),
]

TEMPLATE_RS_EXERCISES = [
    (f"{EX_RS_PREFIX}-1", "[DEMO] RS - Lectura en voz alta 1", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "El gato duerme."),
    (f"{EX_RS_PREFIX}-2", "[DEMO] RS - Lectura en voz alta 2", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "La casa es grande."),
    (f"{EX_RS_PREFIX}-3", "[DEMO] RS - Lectura en voz alta 3", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "Mi mamá lee un libro."),
    (f"{EX_RS_PREFIX}-4", "[DEMO] RS - Lectura en voz alta 4", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "El perro corre rápido."),
    (f"{EX_RS_PREFIX}-5", "[DEMO] RS - Lectura en voz alta 5", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "La luna brilla en la noche."),
    (f"{EX_RS_PREFIX}-6", "[DEMO] RS - Lectura en voz alta 6", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 2, "El niño juega con la pelota."),
    (f"{EX_RS_PREFIX}-7", "[DEMO] RS - Lectura en voz alta 7", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 2, "La maestra escribe en la pizarra."),
    (f"{EX_RS_PREFIX}-8", "[DEMO] RS - Lectura en voz alta 8", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 2, "La niña toma agua."),
    (f"{EX_RS_PREFIX}-9", "[DEMO] RS - Lectura en voz alta 9", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "El sol sale por la mañana."),
    (f"{EX_RS_PREFIX}-10", "[DEMO] RS - Lectura en voz alta 10", "Lee la siguiente oración en voz alta.", "TEXT", "READING_SPEAKING", 1, "Mi escuela tiene un patio."),
]

TEMPLATE_RW_EXERCISES = [
    (f"{EX_RW_PREFIX}-1", "[DEMO] RW - Escritura 1", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "El gato duerme."),
    (f"{EX_RW_PREFIX}-2", "[DEMO] RW - Escritura 2", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "La mesa es roja."),
    (f"{EX_RW_PREFIX}-3", "[DEMO] RW - Escritura 3", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "Mi perro juega."),
    (f"{EX_RW_PREFIX}-4", "[DEMO] RW - Escritura 4", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "La luna está alta."),
    (f"{EX_RW_PREFIX}-5", "[DEMO] RW - Escritura 5", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "El niño lee."),
    (f"{EX_RW_PREFIX}-6", "[DEMO] RW - Escritura 6", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 2, "La casa tiene puerta."),
    (f"{EX_RW_PREFIX}-7", "[DEMO] RW - Escritura 7", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 2, "Mi lápiz es azul."),
    (f"{EX_RW_PREFIX}-8", "[DEMO] RW - Escritura 8", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 2, "La pelota rebota."),
    (f"{EX_RW_PREFIX}-9", "[DEMO] RW - Escritura 9", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "El sol calienta."),
    (f"{EX_RW_PREFIX}-10", "[DEMO] RW - Escritura 10", "Lee la siguiente oración y escríbela.", "TEXT", "READING_WRITING", 1, "La flor es bonita."),
]

TEMPLATE_LS_EXERCISES = [
    (f"{EX_LS_PREFIX}-1", "[DEMO] LS - Listening Speaking 1", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "El pato nada."),
    (f"{EX_LS_PREFIX}-2", "[DEMO] LS - Listening Speaking 2", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "La vaca come pasto."),
    (f"{EX_LS_PREFIX}-3", "[DEMO] LS - Listening Speaking 3", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "El tren pasa rápido."),
    (f"{EX_LS_PREFIX}-4", "[DEMO] LS - Listening Speaking 4", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "Mi hermano canta."),
    (f"{EX_LS_PREFIX}-5", "[DEMO] LS - Listening Speaking 5", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 2, "La lluvia cae fuerte."),
    (f"{EX_LS_PREFIX}-6", "[DEMO] LS - Listening Speaking 6", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 2, "El bebé ríe."),
    (f"{EX_LS_PREFIX}-7", "[DEMO] LS - Listening Speaking 7", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "La puerta está abierta."),
    (f"{EX_LS_PREFIX}-8", "[DEMO] LS - Listening Speaking 8", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "El pez nada en el agua."),
    (f"{EX_LS_PREFIX}-9", "[DEMO] LS - Listening Speaking 9", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 2, "La campana suena."),
    (f"{EX_LS_PREFIX}-10", "[DEMO] LS - Listening Speaking 10", "Escucha el audio y repite la oración en voz alta.", "AUDIO", "LISTENING_SPEAKING", 1, "El pájaro vuela."),
]

TEMPLATE_LW_EXERCISES = [
    (f"{EX_LW_PREFIX}-1", "[DEMO] LW - Listening Writing 1", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "La casa es blanca."),
    (f"{EX_LW_PREFIX}-2", "[DEMO] LW - Listening Writing 2", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "El gato toma leche."),
    (f"{EX_LW_PREFIX}-3", "[DEMO] LW - Listening Writing 3", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "Mi mochila es nueva."),
    (f"{EX_LW_PREFIX}-4", "[DEMO] LW - Listening Writing 4", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "El árbol tiene hojas."),
    (f"{EX_LW_PREFIX}-5", "[DEMO] LW - Listening Writing 5", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 2, "La niña pinta una flor."),
    (f"{EX_LW_PREFIX}-6", "[DEMO] LW - Listening Writing 6", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 2, "El niño come pan."),
    (f"{EX_LW_PREFIX}-7", "[DEMO] LW - Listening Writing 7", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "La mesa está limpia."),
    (f"{EX_LW_PREFIX}-8", "[DEMO] LW - Listening Writing 8", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 2, "El perro duerme."),
    (f"{EX_LW_PREFIX}-9", "[DEMO] LW - Listening Writing 9", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "La escuela abre temprano."),
    (f"{EX_LW_PREFIX}-10", "[DEMO] LW - Listening Writing 10", "Escucha el audio y escribe la oración.", "AUDIO", "LISTENING_WRITING", 1, "El lápiz está en la mesa."),
]

ALL_EXERCISES = (
    TEMPLATE_MC_EXERCISES
    + TEMPLATE_OS_EXERCISES
    + TEMPLATE_RS_EXERCISES
    + TEMPLATE_RW_EXERCISES
    + TEMPLATE_LS_EXERCISES
    + TEMPLATE_LW_EXERCISES
)

TEMPLATES = [
    (TEMPLATE_MC_UUID, "[DEMO] Template Multiple Choice", "Template de selección múltiple para evaluación de vocabulario e identificación de imágenes.", 1),
    (TEMPLATE_OS_UUID, "[DEMO] Template Order Syllables", "Template de ordenar sílabas para evaluación de conciencia fonológica.", 1),
    (TEMPLATE_RS_UUID, "[DEMO] Template Reading Speaking", "Template de lectura en voz alta para evaluación de expresión oral.", 1),
    (TEMPLATE_RW_UUID, "[DEMO] Template Reading Writing", "Template de escritura espontánea para evaluación de producción escrita.", 1),
    (TEMPLATE_LS_UUID, "[DEMO] Template Listening Speaking", "Template de comprensión auditiva + expresión oral.", 1),
    (TEMPLATE_LW_UUID, "[DEMO] Template Listening Writing", "Template de comprensión auditiva + escritura.", 1),
    (TEMPLATE_MIX_UUID, "[DEMO] Template Mixto", "Template mixto con ejercicios de todos los tipos.", 1),
]

TEMPLATE_EXERCISES = [
    (TEMPLATE_MC_UUID, [f"{EX_MC_PREFIX}-{i}" for i in range(1, 11)]),
    (TEMPLATE_OS_UUID, [f"{EX_OS_PREFIX}-{i}" for i in range(1, 11)]),
    (TEMPLATE_RS_UUID, [f"{EX_RS_PREFIX}-{i}" for i in range(1, 11)]),
    (TEMPLATE_RW_UUID, [f"{EX_RW_PREFIX}-{i}" for i in range(1, 11)]),
    (TEMPLATE_LS_UUID, [f"{EX_LS_PREFIX}-{i}" for i in range(1, 11)]),
    (TEMPLATE_LW_UUID, [f"{EX_LW_PREFIX}-{i}" for i in range(1, 11)]),
    (TEMPLATE_MIX_UUID, [
        f"{EX_MC_PREFIX}-1", f"{EX_MC_PREFIX}-2",
        f"{EX_OS_PREFIX}-1", f"{EX_OS_PREFIX}-2",
        f"{EX_RS_PREFIX}-1", f"{EX_RS_PREFIX}-2",
        f"{EX_RW_PREFIX}-1", f"{EX_RW_PREFIX}-2",
        f"{EX_LS_PREFIX}-1", f"{EX_LW_PREFIX}-1",
    ]),
]


def _hash_password(password: str) -> str:
    import passlib.hash
    return passlib.hash.pbkdf2_sha256.hash(password)


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    teacher_exists = session.execute(
        sa.select(sa.text("1")).select_from(sa.text("teachers_iam")).where(
            sa.text("id = :tid")
        ).params(tid=str(DEMO_TEACHER_UUID))
    ).scalar()

    teacher_id = DEMO_TEACHER_UUID
    if not teacher_exists:
        user_exists = session.execute(
            sa.select(sa.text("1")).select_from(sa.text("users_iam")).where(
                sa.text("email = :email")
            ).params(email="demo.teacher@tamizai.dev")
        ).scalar()
        if not user_exists:
            session.execute(
                sa.text("""
                    INSERT INTO users_iam (id, name, lastname, email, password_hash, is_active, created_at, updated_at)
                    VALUES (:id, :name, :lastname, :email, :password_hash, true, :now, :now)
                """),
                {
                    "id": str(DEMO_USER_UUID),
                    "name": "Demo",
                    "lastname": "Teacher",
                    "email": "demo.teacher@tamizai.dev",
                    "password_hash": _hash_password("Demo123456"),
                    "now": _now(),
                },
            )
        session.execute(
            sa.text("""
                INSERT INTO teachers_iam (id, user_id, institute_name, phone, created_at, updated_at)
                VALUES (:id, :user_id, 'TamizAI Demo', NULL, :now, :now)
            """),
            {
                "id": str(DEMO_TEACHER_UUID),
                "user_id": str(DEMO_USER_UUID),
                "now": _now(),
            },
        )
        session.commit()

    template_exists = session.execute(
        sa.select(sa.text("1")).select_from(sa.text("assessment_templates")).where(
            sa.text("name LIKE '[DEMO]%'")
        ).limit(1)
    ).scalar()
    if template_exists:
        session.close()
        return

    exercise_ids = {}
    response_type_map = {
        "READING_SPEAKING": "SPEAKING",
        "LISTENING_SPEAKING": "SPEAKING",
        "READING_WRITING": "WRITING",
        "LISTENING_WRITING": "WRITING",
        "MULTIPLE_CHOICE": "MULTIPLE_CHOICE",
        "ORDER_SYLLABLES": "ORDER_SYLLABLES",
    }
    for ex_key, title, instructions, stimulus_type, ex_type, diff, *rest in ALL_EXERCISES:
        ex_id = _uid(ex_key)
        exercise_ids[ex_key] = ex_id
        session.execute(
            sa.text("""
                INSERT INTO assessment_exercises
                (id, type, title, instructions, stimulus_type, response_type, difficulty_level, is_active, created_by_teacher_id, created_at, updated_at)
                VALUES (:id, :type, :title, :instructions, :stimulus_type, :response_type, :difficulty_level, true, :teacher_id, :now, :now)
            """),
            {
                "id": str(ex_id),
                "type": ex_type,
                "title": title,
                "instructions": instructions,
                "stimulus_type": stimulus_type,
                "response_type": response_type_map.get(ex_type, ex_type),
                "difficulty_level": diff,
                "teacher_id": str(teacher_id),
                "now": _now(),
            },
        )

    mc_idx = 0
    for ex_key, title, *_ in TEMPLATE_MC_EXERCISES:
        ex_id = exercise_ids[ex_key]
        mc_q_id = _uid(f"{ex_key}-mcq")
        _, _, question_text = title.partition(" - ")
        session.execute(
            sa.text("""
                INSERT INTO assessment_mc_questions (id, exercise_id, question_text, image_blob_path, created_at, updated_at)
                VALUES (:id, :exercise_id, :question_text, NULL, :now, :now)
            """),
            {
                "id": str(mc_q_id),
                "exercise_id": str(ex_id),
                "question_text": question_text,
                "now": _now(),
            },
        )
        for i in range(3):
            opt = MC_OPTIONS[mc_idx * 3 + i]
            session.execute(
                sa.text("""
                    INSERT INTO assessment_mc_answer_options (id, mc_question_id, text, is_correct, order_index, created_at, updated_at)
                    VALUES (:id, :mc_question_id, :text, :is_correct, :order_index, :now, :now)
                """),
                {
                    "id": str(_uid(f"{ex_key}-opt-{i}")),
                    "mc_question_id": str(mc_q_id),
                    "text": opt[0],
                    "is_correct": opt[1],
                    "order_index": i + 1,
                    "now": _now(),
                },
            )
        mc_idx += 1

    os_idx = 0
    for ex_key, title, instructions, stimulus_type, ex_type, diff, correct_word, syllables in TEMPLATE_OS_EXERCISES:
        ex_id = exercise_ids[ex_key]
        os_q_id = _uid(f"{ex_key}-osq")
        session.execute(
            sa.text("""
                INSERT INTO assessment_os_questions (id, exercise_id, question_text, image_blob_path, created_at, updated_at)
                VALUES (:id, :exercise_id, :question_text, NULL, :now, :now)
            """),
            {
                "id": str(os_q_id),
                "exercise_id": str(ex_id),
                "question_text": f"Ordena las sílabas: {correct_word}",
                "now": _now(),
            },
        )
        session.execute(
            sa.text("""
                INSERT INTO assessment_os_answers (id, os_question_id, correct_word, syllables_json, created_at, updated_at)
                VALUES (:id, :os_question_id, :correct_word, :syllables_json, :now, :now)
            """),
            {
                "id": str(_uid(f"{ex_key}-osa")),
                "os_question_id": str(os_q_id),
                "correct_word": correct_word,
                "syllables_json": json.dumps(syllables),
                "now": _now(),
            },
        )
        os_idx += 1

    for ex_key, title, instructions, stimulus_type, ex_type, diff, expected_text in TEMPLATE_RS_EXERCISES:
        ex_id = exercise_ids[ex_key]
        prompt_id = _uid(f"{ex_key}-prompt")
        session.execute(
            sa.text("""
                INSERT INTO assessment_prompt_exercises
                (id, exercise_id, prompt_text, text_to_show, audio_blob_path, image_blob_path, language_code, created_at, updated_at)
                VALUES (:id, :exercise_id, 'Lee la siguiente oración en voz alta.', :text_to_show, NULL, NULL, 'es-PE', :now, :now)
            """),
            {
                "id": str(prompt_id),
                "exercise_id": str(ex_id),
                "text_to_show": expected_text,
                "now": _now(),
            },
        )
        session.execute(
            sa.text("""
                INSERT INTO assessment_expected_answers (id, prompt_exercise_id, expected_text, created_at, updated_at)
                VALUES (:id, :prompt_exercise_id, :expected_text, :now, :now)
            """),
            {
                "id": str(_uid(f"{ex_key}-ea")),
                "prompt_exercise_id": str(prompt_id),
                "expected_text": expected_text,
                "now": _now(),
            },
        )

    for ex_key, title, instructions, stimulus_type, ex_type, diff, expected_text in TEMPLATE_RW_EXERCISES:
        ex_id = exercise_ids[ex_key]
        prompt_id = _uid(f"{ex_key}-prompt")
        session.execute(
            sa.text("""
                INSERT INTO assessment_prompt_exercises
                (id, exercise_id, prompt_text, text_to_show, audio_blob_path, image_blob_path, language_code, created_at, updated_at)
                VALUES (:id, :exercise_id, 'Lee la siguiente oración y escríbela.', :text_to_show, NULL, NULL, 'es-PE', :now, :now)
            """),
            {
                "id": str(prompt_id),
                "exercise_id": str(ex_id),
                "text_to_show": expected_text,
                "now": _now(),
            },
        )
        session.execute(
            sa.text("""
                INSERT INTO assessment_expected_answers (id, prompt_exercise_id, expected_text, created_at, updated_at)
                VALUES (:id, :prompt_exercise_id, :expected_text, :now, :now)
            """),
            {
                "id": str(_uid(f"{ex_key}-ea")),
                "prompt_exercise_id": str(prompt_id),
                "expected_text": expected_text,
                "now": _now(),
            },
        )

    for ex_key, title, instructions, stimulus_type, ex_type, diff, expected_text in TEMPLATE_LS_EXERCISES:
        ex_id = exercise_ids[ex_key]
        prompt_id = _uid(f"{ex_key}-prompt")
        session.execute(
            sa.text("""
                INSERT INTO assessment_prompt_exercises
                (id, exercise_id, prompt_text, text_to_show, audio_blob_path, image_blob_path, language_code, created_at, updated_at)
                VALUES (:id, :exercise_id, 'Escucha el audio y repite la oración en voz alta.', 'Repite la oración escuchada.', NULL, NULL, 'es-PE', :now, :now)
            """),
            {
                "id": str(prompt_id),
                "exercise_id": str(ex_id),
                "now": _now(),
            },
        )
        session.execute(
            sa.text("""
                INSERT INTO assessment_expected_answers (id, prompt_exercise_id, expected_text, created_at, updated_at)
                VALUES (:id, :prompt_exercise_id, :expected_text, :now, :now)
            """),
            {
                "id": str(_uid(f"{ex_key}-ea")),
                "prompt_exercise_id": str(prompt_id),
                "expected_text": expected_text,
                "now": _now(),
            },
        )

    for ex_key, title, instructions, stimulus_type, ex_type, diff, expected_text in TEMPLATE_LW_EXERCISES:
        ex_id = exercise_ids[ex_key]
        prompt_id = _uid(f"{ex_key}-prompt")
        session.execute(
            sa.text("""
                INSERT INTO assessment_prompt_exercises
                (id, exercise_id, prompt_text, text_to_show, audio_blob_path, image_blob_path, language_code, created_at, updated_at)
                VALUES (:id, :exercise_id, 'Escucha el audio y escribe la oración.', 'Escribe la oración escuchada.', NULL, NULL, 'es-PE', :now, :now)
            """),
            {
                "id": str(prompt_id),
                "exercise_id": str(ex_id),
                "now": _now(),
            },
        )
        session.execute(
            sa.text("""
                INSERT INTO assessment_expected_answers (id, prompt_exercise_id, expected_text, created_at, updated_at)
                VALUES (:id, :prompt_exercise_id, :expected_text, :now, :now)
            """),
            {
                "id": str(_uid(f"{ex_key}-ea")),
                "prompt_exercise_id": str(prompt_id),
                "expected_text": expected_text,
                "now": _now(),
            },
        )

    for tmpl_id, tmpl_name, tmpl_desc, tmpl_ver in TEMPLATES:
        session.execute(
            sa.text("""
                INSERT INTO assessment_templates
                (id, name, description, version, is_active, created_by_teacher_id, created_at, updated_at)
                VALUES (:id, :name, :description, :version, true, :teacher_id, :now, :now)
            """),
            {
                "id": str(tmpl_id),
                "name": tmpl_name,
                "description": tmpl_desc,
                "version": tmpl_ver,
                "teacher_id": str(teacher_id),
                "now": _now(),
            },
        )

    te_order_counter = {}
    for tmpl_id, ex_keys in TEMPLATE_EXERCISES:
        for order_idx, ex_key in enumerate(ex_keys, start=1):
            ex_id = exercise_ids[ex_key]
            te_id = _uid(f"te-{str(tmpl_id)}-{ex_key}")
            session.execute(
                sa.text("""
                    INSERT INTO assessment_template_exercises
                    (id, template_id, exercise_id, order_index, points, is_required, created_at, updated_at)
                    VALUES (:id, :template_id, :exercise_id, :order_index, 10, true, :now, :now)
                """),
                {
                    "id": str(te_id),
                    "template_id": str(tmpl_id),
                    "exercise_id": str(ex_id),
                    "order_index": order_idx,
                    "now": _now(),
                },
            )

    session.commit()
    session.close()


def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    session.execute(
        sa.text("DELETE FROM assessment_template_exercises WHERE template_id IN (:t1,:t2,:t3,:t4,:t5,:t6,:t7)"),
        {
            "t1": str(TEMPLATE_MC_UUID),
            "t2": str(TEMPLATE_OS_UUID),
            "t3": str(TEMPLATE_RS_UUID),
            "t4": str(TEMPLATE_RW_UUID),
            "t5": str(TEMPLATE_LS_UUID),
            "t6": str(TEMPLATE_LW_UUID),
            "t7": str(TEMPLATE_MIX_UUID),
        },
    )
    session.execute(
        sa.text("DELETE FROM assessment_templates WHERE id IN (:t1,:t2,:t3,:t4,:t5,:t6,:t7)"),
        {
            "t1": str(TEMPLATE_MC_UUID),
            "t2": str(TEMPLATE_OS_UUID),
            "t3": str(TEMPLATE_RS_UUID),
            "t4": str(TEMPLATE_RW_UUID),
            "t5": str(TEMPLATE_LS_UUID),
            "t6": str(TEMPLATE_LW_UUID),
            "t7": str(TEMPLATE_MIX_UUID),
        },
    )
    session.execute(sa.text("DELETE FROM assessment_expected_answers WHERE prompt_exercise_id IN (SELECT id FROM assessment_prompt_exercises WHERE exercise_id IN (SELECT id FROM assessment_exercises WHERE title LIKE '[DEMO]%%'))"))
    session.execute(sa.text("DELETE FROM assessment_prompt_exercises WHERE exercise_id IN (SELECT id FROM assessment_exercises WHERE title LIKE '[DEMO]%%')"))
    session.execute(sa.text("DELETE FROM assessment_mc_answer_options WHERE mc_question_id IN (SELECT id FROM assessment_mc_questions WHERE exercise_id IN (SELECT id FROM assessment_exercises WHERE title LIKE '[DEMO]%%'))"))
    session.execute(sa.text("DELETE FROM assessment_mc_questions WHERE exercise_id IN (SELECT id FROM assessment_exercises WHERE title LIKE '[DEMO]%%')"))
    session.execute(sa.text("DELETE FROM assessment_os_answers WHERE os_question_id IN (SELECT id FROM assessment_os_questions WHERE exercise_id IN (SELECT id FROM assessment_exercises WHERE title LIKE '[DEMO]%%'))"))
    session.execute(sa.text("DELETE FROM assessment_os_questions WHERE exercise_id IN (SELECT id FROM assessment_exercises WHERE title LIKE '[DEMO]%%')"))
    session.execute(sa.text("DELETE FROM assessment_exercises WHERE title LIKE '[DEMO]%%'"))
    session.execute(
        sa.text("DELETE FROM teachers_iam WHERE id = :id"),
        {"id": str(DEMO_TEACHER_UUID)},
    )
    session.execute(
        sa.text("DELETE FROM users_iam WHERE email = :email"),
        {"email": "demo.teacher@tamizai.dev"},
    )
    session.commit()
    session.close()
