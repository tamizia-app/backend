from app.school.application.ports.user_management_port import UserData
from app.school.application.results.homeroom_teacher_result import HomeroomTeacherResult
from app.school.domain.homeroom_teacher import HomeroomTeacher


class HomeroomTeacherAssembler:
    @staticmethod
    def to_result(teacher: HomeroomTeacher, user: UserData) -> HomeroomTeacherResult:
        return HomeroomTeacherResult(
            teacher_id=teacher.id,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
            institute_name=teacher.institute_name,
            phone=teacher.phone,
        )
