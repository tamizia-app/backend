from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import ExerciseAssembler
from app.assessment.application.ports.repositories import (
    ExerciseRepository,
    MCAnswerOptionRepository,
    MCQuestionRepository,
    OSAnswerRepository,
    OSQuestionRepository,
    ExpectedAnswerRepository,
    PromptExerciseRepository,
)
from app.assessment.application.results import ExerciseResult
from app.assessment.domain.enums import ExerciseType
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.question import MCAnswerOption, MCQuestion, OSAnswer, OSQuestion
from app.assessment.domain.prompt import ExpectedAnswer, PromptExercise


@dataclass
class MCAnswerOptionData:
    text: str
    is_correct: bool
    order_index: int


@dataclass
class MCQuestionData:
    question_text: str
    image_blob_path: str | None
    options: list[MCAnswerOptionData]


@dataclass
class OSQuestionData:
    question_text: str
    image_blob_path: str | None
    correct_word: str
    syllables_json: list[str]


@dataclass
class PromptExerciseData:
    prompt_text: str | None
    text_to_show: str | None
    audio_blob_path: str | None
    image_blob_path: str | None
    language_code: str
    expected_text: str


@dataclass
class CreateExerciseCommand:
    type: ExerciseType
    title: str
    instructions: str | None
    stimulus_type: str | None
    response_type: str | None
    difficulty_level: int | None
    created_by_teacher_id: UUID | None
    mc_question: MCQuestionData | None = None
    os_question: OSQuestionData | None = None
    prompt_exercise: PromptExerciseData | None = None


class CreateExerciseUseCase:
    def __init__(
        self,
        exercise_repo: ExerciseRepository,
        mc_question_repo: MCQuestionRepository,
        mc_option_repo: MCAnswerOptionRepository,
        os_question_repo: OSQuestionRepository,
        os_answer_repo: OSAnswerRepository,
        prompt_exercise_repo: PromptExerciseRepository,
        expected_answer_repo: ExpectedAnswerRepository,
    ) -> None:
        self._exercise_repo = exercise_repo
        self._mc_question_repo = mc_question_repo
        self._mc_option_repo = mc_option_repo
        self._os_question_repo = os_question_repo
        self._os_answer_repo = os_answer_repo
        self._prompt_exercise_repo = prompt_exercise_repo
        self._expected_answer_repo = expected_answer_repo

    def execute(self, command: CreateExerciseCommand) -> ExerciseResult:
        now = datetime.now(timezone.utc)
        exercise = self._exercise_repo.create(
            AssessmentExercise(
                id=UUID(int=0),
                type=command.type,
                title=command.title,
                instructions=command.instructions,
                stimulus_type=command.stimulus_type,
                response_type=command.response_type,
                difficulty_level=command.difficulty_level,
                is_active=True,
                created_by_teacher_id=command.created_by_teacher_id,
                created_at=now,
                updated_at=now,
            )
        )

        if command.type == ExerciseType.MULTIPLE_CHOICE and command.mc_question:
            mc_q = self._mc_question_repo.create(
                MCQuestion(
                    id=UUID(int=0),
                    exercise_id=exercise.id,
                    question_text=command.mc_question.question_text,
                    image_blob_path=command.mc_question.image_blob_path,
                    created_at=now,
                    updated_at=now,
                )
            )
            for opt_data in command.mc_question.options:
                self._mc_option_repo.create(
                    MCAnswerOption(
                        id=UUID(int=0),
                        mc_question_id=mc_q.id,
                        text=opt_data.text,
                        is_correct=opt_data.is_correct,
                        order_index=opt_data.order_index,
                        created_at=now,
                        updated_at=now,
                    )
                )

        elif command.type == ExerciseType.ORDER_SYLLABLES and command.os_question:
            os_q = self._os_question_repo.create(
                OSQuestion(
                    id=UUID(int=0),
                    exercise_id=exercise.id,
                    question_text=command.os_question.question_text,
                    image_blob_path=command.os_question.image_blob_path,
                    created_at=now,
                    updated_at=now,
                )
            )
            self._os_answer_repo.create(
                OSAnswer(
                    id=UUID(int=0),
                    os_question_id=os_q.id,
                    correct_word=command.os_question.correct_word,
                    syllables_json=command.os_question.syllables_json,
                    created_at=now,
                    updated_at=now,
                )
            )

        elif command.type in (
            ExerciseType.READING_SPEAKING,
            ExerciseType.READING_WRITING,
            ExerciseType.LISTENING_SPEAKING,
            ExerciseType.LISTENING_WRITING,
        ) and command.prompt_exercise:
            prompt = self._prompt_exercise_repo.create(
                PromptExercise(
                    id=UUID(int=0),
                    exercise_id=exercise.id,
                    prompt_text=command.prompt_exercise.prompt_text,
                    text_to_show=command.prompt_exercise.text_to_show,
                    audio_blob_path=command.prompt_exercise.audio_blob_path,
                    image_blob_path=command.prompt_exercise.image_blob_path,
                    language_code=command.prompt_exercise.language_code,
                    created_at=now,
                    updated_at=now,
                )
            )
            self._expected_answer_repo.create(
                ExpectedAnswer(
                    id=UUID(int=0),
                    prompt_exercise_id=prompt.id,
                    expected_text=command.prompt_exercise.expected_text,
                    created_at=now,
                    updated_at=now,
                )
            )

        return ExerciseAssembler.to_result(exercise)
