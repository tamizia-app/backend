from app.profile.application.ports.user_management_port import UserData
from app.profile.application.results.teacher_result import TeacherResult
from app.profile.domain.teacher import Teacher


class TeacherAssembler:
    @staticmethod
    def to_result(teacher: Teacher, user: UserData) -> TeacherResult:
        return TeacherResult(
            teacher_id=teacher.id,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
            institute_name=teacher.institute_name,
            phone=teacher.phone,
        )
