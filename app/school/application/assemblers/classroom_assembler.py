from app.school.application.results.classroom_result import ClassroomResult
from app.school.domain.classroom import Classroom


class ClassroomAssembler:
    @staticmethod
    def to_result(classroom: Classroom) -> ClassroomResult:
        return ClassroomResult(
            classroom_id=classroom.id,
            homeroom_teacher_id=classroom.homeroom_teacher_id,
            name=classroom.name,
            grade_level=classroom.grade_level.value,
            section=classroom.section.value,
            school_year=classroom.school_year,
        )
