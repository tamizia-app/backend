from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.school.application.ports.consent_repository import StudentConsentRepository
from app.school.application.ports.student_repository import StudentRepository
from app.school.domain.enums import Gender
from app.school.domain.student import Student as StudentDomain
from app.school.domain.student import StudentConsent as StudentConsentDomain
from app.school.infrastructure.models.student_model import Student, StudentConsent


class SQLAlchemyStudentRepository(StudentRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, student_id: UUID) -> StudentDomain | None:
        model = self._db.get(Student, student_id)
        return self._to_domain(model) if model else None

    def find_by_classroom_id(self, classroom_id: UUID) -> list[StudentDomain]:
        models = self._db.scalars(
            select(Student).where(Student.classroom_id == classroom_id).order_by(Student.code)
        )
        return [self._to_domain(m) for m in models]

    def find_by_code_in_classroom(self, code: str, classroom_id: UUID, exclude_id: UUID | None = None) -> StudentDomain | None:
        query = select(Student).where(
            Student.code == code,
            Student.classroom_id == classroom_id,
        )
        if exclude_id is not None:
            query = query.where(Student.id != exclude_id)
        model = self._db.scalar(query)
        return self._to_domain(model) if model else None

    def find_by_code(self, code: str) -> StudentDomain | None:
        model = self._db.scalar(select(Student).where(Student.code == code))
        return self._to_domain(model) if model else None

    def create(self, student: StudentDomain) -> StudentDomain:
        model = Student(
            classroom_id=student.classroom_id,
            code=student.code,
            age=student.age,
            gender=student.gender.value,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, student: StudentDomain) -> StudentDomain:
        model = self._db.get(Student, student.id)
        if model:
            model.code = student.code
            model.age = student.age
            model.gender = student.gender.value
            self._db.flush()
        return self._to_domain(model)

    def delete(self, student_id: UUID) -> None:
        model = self._db.get(Student, student_id)
        if model:
            self._db.delete(model)
            self._db.flush()

    @staticmethod
    def _to_domain(model: Student) -> StudentDomain:
        return StudentDomain(
            id=model.id,
            classroom_id=model.classroom_id,
            code=model.code,
            age=model.age,
            gender=Gender(model.gender),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyStudentConsentRepository(StudentConsentRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_student_id(self, student_id: UUID) -> StudentConsentDomain | None:
        model = self._db.scalar(
            select(StudentConsent).where(StudentConsent.student_id == student_id)
        )
        return self._to_domain(model) if model else None

    def create(self, consent: StudentConsentDomain) -> StudentConsentDomain:
        model = StudentConsent(
            student_id=consent.student_id,
            status=consent.status,
            consent_date=consent.consent_date,
            revoked_at=consent.revoked_at,
            evidence_blob_path=consent.evidence_blob_path,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, consent: StudentConsentDomain) -> StudentConsentDomain:
        model = self._db.get(StudentConsent, consent.id)
        if model:
            model.status = consent.status
            model.consent_date = consent.consent_date
            model.revoked_at = consent.revoked_at
            model.evidence_blob_path = consent.evidence_blob_path
            self._db.flush()
        return self._to_domain(model)

    def delete_by_student_id(self, student_id: UUID) -> None:
        model = self._db.scalar(
            select(StudentConsent).where(StudentConsent.student_id == student_id)
        )
        if model:
            self._db.delete(model)
            self._db.flush()

    @staticmethod
    def _to_domain(model: StudentConsent) -> StudentConsentDomain:
        return StudentConsentDomain(
            id=model.id,
            student_id=model.student_id,
            status=model.status,
            consent_date=model.consent_date,
            revoked_at=model.revoked_at,
            evidence_blob_path=model.evidence_blob_path,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
