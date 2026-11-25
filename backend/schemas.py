from typing import List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=80)
    full_name: str = Field(..., min_length=2, max_length=150)
    email: Optional[str] = None
    password: str = Field(..., min_length=4)
    role: str = Field(..., pattern="^(admin|staff|student)$")
    class_id: Optional[int] = None
    gender: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: Optional[str] = None
    role: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ClassCreate(BaseModel):
    name: str
    level: Optional[str] = None
    form_teacher_id: Optional[int] = None


class ClassOut(BaseModel):
    id: int
    name: str
    level: Optional[str] = None
    form_teacher_id: Optional[int] = None
    student_count: int = 0


class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None


class SubjectOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None


class AssignmentCreate(BaseModel):
    staff_id: int
    class_id: int
    subject_id: int


class AssignmentOut(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str


class TemplateUpdate(BaseModel):
    school_name: str
    school_motto: str
    school_address: str
    academic_session: str
    current_term: str
    ca1_label: str
    ca1_max: float
    ca2_label: str
    ca2_max: float
    exam_label: str
    exam_max: float
    next_term_begins: Optional[str] = None
    principal_name: Optional[str] = None


class TemplateOut(TemplateUpdate):
    id: int

    class Config:
        from_attributes = True


class ScoreEntry(BaseModel):
    student_id: int
    class_id: int
    subject_id: int
    ca1: float = Field(..., ge=0)
    ca2: float = Field(..., ge=0)
    exam: float = Field(..., ge=0)


class ScoreOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    admission_no: str
    subject_id: int
    subject_name: str
    ca1: float
    ca2: float
    exam: float
    total: float
    grade: str
    remark: str


class SummaryUpdate(BaseModel):
    student_id: int
    days_opened: int = 65
    days_present: int = 60
    punctuality: str = "Very Good"
    neatness: str = "Very Good"
    conduct: str = "Very Good"
    teacher_remark: str = ""
    principal_remark: str = ""


class ReportSheetOut(BaseModel):
    template: TemplateOut
    student: UserOut
    scores: List[ScoreOut]
    summary: SummaryUpdate
    grand_total: float
    max_obtainable: float
    average: float
    overall_grade: str
    class_size: int
    position: str