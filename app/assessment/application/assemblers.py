from app.assessment.application.results import (
    AssessmentResult,
    AttemptResult,
    ExerciseAttemptResult,
    ExerciseResult,
    FinalResult,
    MCResponseResult,
    OSResponseResult,
    SpeakingResponseResult,
    TemplateExerciseResult,
    TemplateResult,
    WritingResponseResult,
)
from app.assessment.domain.assessment import Assessment
from app.assessment.domain.attempt import AssessmentAttempt, ExerciseAttempt
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.metrics import AssessmentResult as AssessmentResultDomain
from app.assessment.domain.response import MCResponse, OSResponse, SpeakingResponse, WritingResponse
from app.assessment.domain.template import AssessmentTemplate, AssessmentTemplateExercise


class TemplateAssembler:
    @staticmethod
    def to_result(t: AssessmentTemplate) -> TemplateResult:
        return TemplateResult(
            template_id=t.id,
            name=t.name,
            description=t.description,
            version=t.version,
            is_active=t.is_active,
            created_by_teacher_id=t.created_by_teacher_id,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )


class ExerciseAssembler:
    @staticmethod
    def to_result(e: AssessmentExercise) -> ExerciseResult:
        return ExerciseResult(
            exercise_id=e.id,
            type=e.type,
            title=e.title,
            instructions=e.instructions,
            stimulus_type=e.stimulus_type,
            response_type=e.response_type,
            difficulty_level=e.difficulty_level,
            is_active=e.is_active,
            created_by_teacher_id=e.created_by_teacher_id,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class AssessmentAssembler:
    @staticmethod
    def to_result(a: Assessment) -> AssessmentResult:
        return AssessmentResult(
            assessment_id=a.id,
            template_id=a.template_id,
            classroom_id=a.classroom_id,
            homeroom_teacher_id=a.homeroom_teacher_id,
            title=a.title,
            status=a.status,
            scheduled_at=a.scheduled_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )


class AttemptAssembler:
    @staticmethod
    def to_result(a: AssessmentAttempt, exercise_attempts: list[ExerciseAttemptResult] | None = None) -> AttemptResult:
        return AttemptResult(
            attempt_id=a.id,
            assessment_id=a.assessment_id,
            student_id=a.student_id,
            status=a.status,
            started_at=a.started_at,
            completed_at=a.completed_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
            exercise_attempts=exercise_attempts,
        )


class ExerciseAttemptAssembler:
    @staticmethod
    def to_result(ea: ExerciseAttempt) -> ExerciseAttemptResult:
        return ExerciseAttemptResult(
            exercise_attempt_id=ea.id,
            template_exercise_id=ea.template_exercise_id,
            status=ea.status,
            started_at=ea.started_at,
            submitted_at=ea.submitted_at,
        )


class MCResponseAssembler:
    @staticmethod
    def to_result(r: MCResponse) -> MCResponseResult:
        return MCResponseResult(
            response_id=r.id,
            exercise_attempt_id=r.exercise_attempt_id,
            selected_option_id=r.selected_option_id,
            is_correct=r.is_correct,
        )


class OSResponseAssembler:
    @staticmethod
    def to_result(r: OSResponse) -> OSResponseResult:
        return OSResponseResult(
            response_id=r.id,
            exercise_attempt_id=r.exercise_attempt_id,
            selected_syllables=r.selected_syllables_json,
            formed_word=r.formed_word,
            is_correct=r.is_correct,
        )


class SpeakingResponseAssembler:
    @staticmethod
    def to_result(r: SpeakingResponse) -> SpeakingResponseResult:
        return SpeakingResponseResult(
            response_id=r.id,
            exercise_attempt_id=r.exercise_attempt_id,
            audio_blob_path=r.audio_blob_path,
            original_filename=r.original_filename,
            content_type=r.content_type,
            duration_ms=r.duration_ms,
            free_transcription_text=r.free_transcription_text,
            assessment_recognized_text=r.assessment_recognized_text,
            recognized_text=r.recognized_text,
        )


class WritingResponseAssembler:
    @staticmethod
    def to_result(r: WritingResponse) -> WritingResponseResult:
        return WritingResponseResult(
            response_id=r.id,
            exercise_attempt_id=r.exercise_attempt_id,
            image_blob_path=r.image_blob_path,
            original_filename=r.original_filename,
            content_type=r.content_type,
            recognized_text=r.recognized_text,
            strokes_json=r.strokes_json,
            canvas_metadata_json=r.canvas_metadata_json,
            input_metadata_json=r.input_metadata_json,
            frontend_metrics_json=r.frontend_metrics_json,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )


class FinalResultAssembler:
    @staticmethod
    def to_result(r: AssessmentResultDomain) -> FinalResult:
        return FinalResult(
            attempt_id=r.assessment_attempt_id,
            final_score=r.final_score,
            max_score=r.max_score,
            mc_correct_count=r.mc_correct_count,
            os_correct_count=r.os_correct_count,
            speaking_completed_count=r.speaking_completed_count,
            writing_completed_count=r.writing_completed_count,
            intervention_level=r.intervention_level,
            generated_at=r.generated_at,
            speaking_average_score=r.speaking_average_score,
            speaking_review_required_count=r.speaking_review_required_count,
            total_exercises=r.total_exercises,
            evaluated_exercises=r.evaluated_exercises,
            pending_exercises=r.pending_exercises,
        )
