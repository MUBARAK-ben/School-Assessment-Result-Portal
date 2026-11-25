from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)  # Staff ID or Admission No.
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # admin | staff | student
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=True)  # Used for students
    gender = Column(String(15), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student_class = relationship(
        "SchoolClass",
        back_populates="students",
        foreign_keys=[class_id],
    )
    form_classes = relationship(
        "SchoolClass",
        back_populates="form_teacher",
        foreign_keys="[SchoolClass.form_teacher_id]",
    )
    staff_assignments = relationship(
        "StaffAssignment",
        back_populates="staff",
        cascade="all, delete-orphan",
    )
    scores = relationship(
        "Score",
        back_populates="student",
        foreign_keys="[Score.student_id]",
        cascade="all, delete-orphan",
    )
    graded_scores = relationship(
        "Score",
        back_populates="entered_by",
        foreign_keys="[Score.entered_by_id]",
    )
    report_summaries = relationship(
        "TermReportSummary",
        back_populates="student",
        cascade="all, delete-orphan",
    )


class SchoolClass(Base):
    __tablename__ = "school_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)  # e.g., JSS 1A, SSS 2 Science
    level = Column(String(50), nullable=True)               # e.g., Junior Secondary
    form_teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    students = relationship(
        "User",
        back_populates="student_class",
        foreign_keys="[User.class_id]",
    )
    form_teacher = relationship(
        "User",
        back_populates="form_classes",
        foreign_keys=[form_teacher_id],
    )
    staff_assignments = relationship(
        "StaffAssignment",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )
    scores = relationship(
        "Score",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )
    report_summaries = relationship(
        "TermReportSummary",
        back_populates="school_class",
        cascade="all, delete-orphan",
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., Arabic Language, Mathematics
    code = Column(String(20), unique=True, nullable=True)

    staff_assignments = relationship(
        "StaffAssignment",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    scores = relationship(
        "Score",
        back_populates="subject",
        cascade="all, delete-orphan",
    )


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"
    __table_args__ = (
        UniqueConstraint("staff_id", "class_id", "subject_id", name="uq_staff_class_subject"),
    )

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    staff = relationship("User", back_populates="staff_assignments")
    school_class = relationship("SchoolClass", back_populates="staff_assignments")
    subject = relationship("Subject", back_populates="staff_assignments")


class AssessmentTemplate(Base):
    __tablename__ = "assessment_templates"

    id = Column(Integer, primary_key=True, index=True)
    school_name = Column(String(200), nullable=False, default="AL-HILAL MODEL ACADEMY")
    school_motto = Column(String(250), nullable=False, default="Knowledge, Discipline & Excellence")
    school_address = Column(String(250), nullable=False, default="Okene / Zaria, Nigeria")
    academic_session = Column(String(40), nullable=False, default="2026/2027")
    current_term = Column(String(40), nullable=False, default="First Term")
    ca1_label = Column(String(40), nullable=False, default="1st CA")
    ca1_max = Column(Float, nullable=False, default=20.0)
    ca2_label = Column(String(40), nullable=False, default="2nd CA")
    ca2_max = Column(Float, nullable=False, default=20.0)
    exam_label = Column(String(40), nullable=False, default="Exam")
    exam_max = Column(Float, nullable=False, default=60.0)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "class_id",
            "academic_session",
            "term",
            name="uq_student_subject_session_term",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    academic_session = Column(String(40), nullable=False)
    term = Column(String(40), nullable=False)
    ca1 = Column(Float, nullable=True)
    ca2 = Column(Float, nullable=True)
    exam = Column(Float, nullable=True)
    total = Column(Float, nullable=False, default=0.0)
    grade = Column(String(5), nullable=False, default="F")
    remark = Column(String(60), nullable=False, default="Fail")
    entered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    student = relationship("User", back_populates="scores", foreign_keys=[student_id])
    subject = relationship("Subject", back_populates="scores")
    school_class = relationship("SchoolClass", back_populates="scores")
    entered_by = relationship("User", back_populates="graded_scores", foreign_keys=[entered_by_id])


class TermReportSummary(Base):
    __tablename__ = "term_report_summaries"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "class_id",
            "academic_session",
            "term",
            name="uq_report_student_class_session_term",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    academic_session = Column(String(40), nullable=False)
    term = Column(String(40), nullable=False)
    days_opened = Column(Integer, nullable=True)
    days_present = Column(Integer, nullable=True)
    form_teacher_remark = Column(String(300), nullable=True)
    principal_remark = Column(String(300), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    student = relationship("User", back_populates="report_summaries")
    school_class = relationship("SchoolClass", back_populates="report_summaries")