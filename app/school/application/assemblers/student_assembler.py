from app.school.application.results.student_result import StudentConsentResult, StudentResult
from app.school.domain.student import Student, StudentConsent


class StudentAssembler:
    @staticmethod
    def to_result(student: Student) -> StudentResult:
        return StudentResult(
            student_id=student.id,
            classroom_id=student.classroom_id,
            code=student.code,
            age=student.age,
            gender=student.gender.value,
            is_active=student.is_active,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )


class StudentConsentAssembler:
    @staticmethod
    def to_result(consent: StudentConsent) -> StudentConsentResult:
        return StudentConsentResult(
            consent_id=consent.id,
            student_id=consent.student_id,
            status=consent.status,
            consent_date=consent.consent_date,
            revoked_at=consent.revoked_at,
            evidence_blob_path=consent.evidence_blob_path,
            created_at=consent.created_at,
            updated_at=consent.updated_at,
        )
