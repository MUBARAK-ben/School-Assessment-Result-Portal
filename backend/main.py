import os
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

try:
    from backend.auth import (
        create_access_token,
        get_current_user,
        hash_password,
        require_admin,
        require_staff,
        verify_password,
    )
    from backend.db import Base, SessionLocal, engine, get_db
    from backend.models import (
        AssessmentTemplate,
        SchoolClass,
        Score,
        StaffAssignment,
        Subject,
        TermReportSummary,
        User,
    )
    from backend.schemas import (
        AssignmentCreate,
        AssignmentOut,
        ClassCreate,
        ClassOut,
        LoginRequest,
        ReportSheetOut,
        ScoreEntry,
        ScoreOut,
        SubjectCreate,
        SubjectOut,
        SummaryUpdate,
        TemplateOut,
        TemplateUpdate,
        TokenResponse,
        UserCreate,
        UserOut,
    )
except ModuleNotFoundError:
    from auth import (
        create_access_token,
        get_current_user,
        hash_password,
        require_admin,
        require_staff,
        verify_password,
    )
    from db import Base, SessionLocal, engine, get_db
    from models import (
        AssessmentTemplate,
        SchoolClass,
        Score,
        StaffAssignment,
        Subject,
        TermReportSummary,
        User,
    )
    from schemas import (
        AssignmentCreate,
        AssignmentOut,
        ClassCreate,
        ClassOut,
        LoginRequest,
        ReportSheetOut,
        ScoreEntry,
        ScoreOut,
        SubjectCreate,
        SubjectOut,
        SummaryUpdate,
        TemplateOut,
        TemplateUpdate,
        TokenResponse,
        UserCreate,
        UserOut,
    )


def calculate_grade(percentage: float) -> tuple[str, str]:
    if percentage >= 70:
        return "A", "Excellent"
    if percentage >= 60:
        return "B", "Very Good"
    if percentage >= 50:
        return "C", "Credit"
    if percentage >= 45:
        return "D", "Pass"
    if percentage >= 40:
        return "E", "Fair"
    return "F", "Fail"


def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def serialize_user(user: User, db: Session) -> UserOut:
    class_name = None
    if user.class_id:
        cls = db.query(SchoolClass).filter(SchoolClass.id == user.class_id).first()
        class_name = cls.name if cls else None
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        class_id=user.class_id,
        class_name=class_name,
        gender=user.gender,
        is_active=user.is_active,
    )


def seed_initial_data():
    db = SessionLocal()
    try:
        if not db.query(AssessmentTemplate).first():
            db.add(AssessmentTemplate())

        if not db.query(User).filter(User.username == "admin").first():
            db.add(
                User(
                    username="admin",
                    full_name="School Principal / Exam Officer",
                    email="admin@schoolportal.edu.ng",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
            )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_initial_data()
    yield


app = FastAPI(title="School Assessment & Result Portal API", lifespan=lifespan)

raw_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "https://school-assessment-result-portal-1.onrender.com,http://127.0.0.1:5500,http://localhost:5500",
    )
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "online"}


# -------------------- AUTHENTICATION --------------------

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/admission number or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(user)
    return TokenResponse(access_token=token, user=serialize_user(user, db))


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_user(current_user, db)


# -------------------- ADMIN: USERS, CLASSES, SUBJECTS & TEMPLATE --------------------

@app.post("/admin/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username / Admission number already exists")

    if payload.role == "student" and not payload.class_id:
        raise HTTPException(status_code=400, detail="Students must be assigned to a class")

    user = User(
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        email=payload.email.strip() if payload.email else None,
        password_hash=hash_password(payload.password),
        role=payload.role,
        class_id=payload.class_id if payload.role == "student" else None,
        gender=payload.gender,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user, db)


@app.get("/admin/users", response_model=List[UserOut])
def list_users(
    role: Optional[str] = None,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.order_by(User.full_name.asc()).all()
    return [serialize_user(u, db) for u in users]


@app.post("/admin/classes", response_model=ClassOut)
def create_class(
    payload: ClassCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(SchoolClass).filter(SchoolClass.name == payload.name.strip()).first():
        raise HTTPException(status_code=400, detail="Class already exists")
    cls = SchoolClass(
        name=payload.name.strip(),
        level=payload.level,
        form_teacher_id=payload.form_teacher_id,
    )
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return ClassOut(
        id=cls.id,
        name=cls.name,
        level=cls.level,
        form_teacher_id=cls.form_teacher_id,
        student_count=0,
    )


@app.get("/classes", response_model=List[ClassOut])
def list_classes(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    classes = db.query(SchoolClass).order_by(SchoolClass.name.asc()).all()
    result = []
    for c in classes:
        count = db.query(User).filter(User.role == "student", User.class_id == c.id).count()
        result.append(
            ClassOut(
                id=c.id,
                name=c.name,
                level=c.level,
                form_teacher_id=c.form_teacher_id,
                student_count=count,
            )
        )
    return result


@app.post("/admin/subjects", response_model=SubjectOut)
def create_subject(
    payload: SubjectCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(Subject).filter(Subject.name == payload.name.strip()).first():
        raise HTTPException(status_code=400, detail="Subject already exists")
    subj = Subject(name=payload.name.strip(), code=payload.code)
    db.add(subj)
    db.commit()
    db.refresh(subj)
    return subj


@app.get("/subjects", response_model=List[SubjectOut])
def list_subjects(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Subject).order_by(Subject.name.asc()).all()


@app.post("/admin/assignments", response_model=AssignmentOut)
def assign_staff(
    payload: AssignmentCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    staff = db.query(User).filter(User.id == payload.staff_id, User.role == "staff").first()
    cls = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
    subj = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not staff or not cls or not subj:
        raise HTTPException(status_code=404, detail="Staff, Class, or Subject not found")

    existing = (
        db.query(StaffAssignment)
        .filter_by(staff_id=payload.staff_id, class_id=payload.class_id, subject_id=payload.subject_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This assignment already exists")

    item = StaffAssignment(
        staff_id=payload.staff_id,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AssignmentOut(
        id=item.id,
        staff_id=staff.id,
        staff_name=staff.full_name,
        class_id=cls.id,
        class_name=cls.name,
        subject_id=subj.id,
        subject_name=subj.name,
    )


@app.get("/assignments", response_model=List[AssignmentOut])
def list_assignments(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    query = db.query(StaffAssignment)
    if current_user.role == "staff":
        query = query.filter(StaffAssignment.staff_id == current_user.id)

    rows = query.all()
    output = []
    for r in rows:
        staff = db.query(User).filter(User.id == r.staff_id).first()
        cls = db.query(SchoolClass).filter(SchoolClass.id == r.class_id).first()
        subj = db.query(Subject).filter(Subject.id == r.subject_id).first()
        if staff and cls and subj:
            output.append(
                AssignmentOut(
                    id=r.id,
                    staff_id=staff.id,
                    staff_name=staff.full_name,
                    class_id=cls.id,
                    class_name=cls.name,
                    subject_id=subj.id,
                    subject_name=subj.name,
                )
            )
    return output


@app.get("/template", response_model=TemplateOut)
def get_template(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tpl = db.query(AssessmentTemplate).first()
    if not tpl:
        tpl = AssessmentTemplate()
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
    return tpl


@app.put("/admin/template", response_model=TemplateOut)
def update_template(
    payload: TemplateUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if round(payload.ca1_max + payload.ca2_max + payload.exam_max, 2) != 100.0:
        raise HTTPException(
            status_code=400,
            detail="CA1 + CA2 + Exam maximum scores must equal 100%",
        )
    tpl = db.query(AssessmentTemplate).first()
    for key, value in payload.model_dump().items():
        setattr(tpl, key, value)
    db.commit()
    db.refresh(tpl)
    return tpl


# -------------------- STAFF PORTAL: SCORES & REMARKS --------------------

@app.get("/staff/class-students/{class_id}", response_model=List[UserOut])
def get_class_students(
    class_id: int,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    students = (
        db.query(User)
        .filter(User.role == "student", User.class_id == class_id)
        .order_by(User.full_name.asc())
        .all()
    )
    return [serialize_user(s, db) for s in students]


@app.get("/staff/scores", response_model=List[ScoreOut])
def get_class_subject_scores(
    class_id: int,
    subject_id: int,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    tpl = db.query(AssessmentTemplate).first()
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")

    scores = (
        db.query(Score)
        .filter_by(
            class_id=class_id,
            subject_id=subject_id,
            session=tpl.academic_session,
            term=tpl.current_term,
        )
        .all()
    )
    out = []
    for sc in scores:
        st = db.query(User).filter(User.id == sc.student_id).first()
        if st:
            out.append(
                ScoreOut(
                    id=sc.id,
                    student_id=st.id,
                    student_name=st.full_name,
                    admission_no=st.username,
                    subject_id=subj.id,
                    subject_name=subj.name,
                    ca1=sc.ca1,
                    ca2=sc.ca2,
                    exam=sc.exam,
                    total=sc.total,
                    grade=sc.grade,
                    remark=sc.remark,
                )
            )
    return out


@app.post("/staff/scores", response_model=ScoreOut)
def save_score(
    payload: ScoreEntry,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    tpl = db.query(AssessmentTemplate).first()
    if payload.ca1 > tpl.ca1_max or payload.ca2 > tpl.ca2_max or payload.exam > tpl.exam_max:
        raise HTTPException(
            status_code=400,
            detail=f"Scores exceed template limits ({tpl.ca1_max}/{tpl.ca2_max}/{tpl.exam_max})",
        )

    if current_user.role == "staff":
        assigned = (
            db.query(StaffAssignment)
            .filter_by(
                staff_id=current_user.id,
                class_id=payload.class_id,
                subject_id=payload.subject_id,
            )
            .first()
        )
        if not assigned:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to teach this subject in this class",
            )

    student = db.query(User).filter(User.id == payload.student_id, User.role == "student").first()
    subj = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not student or not subj:
        raise HTTPException(status_code=404, detail="Student or Subject not found")

    total = round(payload.ca1 + payload.ca2 + payload.exam, 2)
    grade, remark = calculate_grade(total)

    existing = (
        db.query(Score)
        .filter_by(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            session=tpl.academic_session,
            term=tpl.current_term,
        )
        .first()
    )

    if existing:
        existing.ca1 = payload.ca1
        existing.ca2 = payload.ca2
        existing.exam = payload.exam
        existing.total = total
        existing.grade = grade
        existing.remark = remark
        existing.staff_id = current_user.id
        score_obj = existing
    else:
        score_obj = Score(
            student_id=payload.student_id,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            staff_id=current_user.id,
            session=tpl.academic_session,
            term=tpl.current_term,
            ca1=payload.ca1,
            ca2=payload.ca2,
            exam=payload.exam,
            total=total,
            grade=grade,
            remark=remark,
        )
        db.add(score_obj)

    db.commit()
    db.refresh(score_obj)

    return ScoreOut(
        id=score_obj.id,
        student_id=student.id,
        student_name=student.full_name,
        admission_no=student.username,
        subject_id=subj.id,
        subject_name=subj.name,
        ca1=score_obj.ca1,
        ca2=score_obj.ca2,
        exam=score_obj.exam,
        total=score_obj.total,
        grade=score_obj.grade,
        remark=score_obj.remark,
    )


@app.post("/staff/summary", response_model=SummaryUpdate)
def save_student_summary(
    payload: SummaryUpdate,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    tpl = db.query(AssessmentTemplate).first()
    existing = (
        db.query(TermReportSummary)
        .filter_by(
            student_id=payload.student_id,
            session=tpl.academic_session,
            term=tpl.current_term,
        )
        .first()
    )
    if existing:
        for k, v in payload.model_dump().items():
            setattr(existing, k, v)
    else:
        db.add(
            TermReportSummary(
                session=tpl.academic_session,
                term=tpl.current_term,
                **payload.model_dump(),
            )
        )
    db.commit()
    return payload


# -------------------- STUDENT & REPORT SHEET ENDPOINT --------------------

@app.get("/reports/student/{student_id}", response_model=ReportSheetOut)
def get_student_report_sheet(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Authorization check: Students can ONLY access their own report sheet
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only view their own report sheet",
        )

    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    tpl = db.query(AssessmentTemplate).first()
    scores = (
        db.query(Score)
        .filter_by(
            student_id=student.id,
            session=tpl.academic_session,
            term=tpl.current_term,
        )
        .all()
    )

    score_items: List[ScoreOut] = []
    for sc in scores:
        subj = db.query(Subject).filter(Subject.id == sc.subject_id).first()
        score_items.append(
            ScoreOut(
                id=sc.id,
                student_id=student.id,
                student_name=student.full_name,
                admission_no=student.username,
                subject_id=sc.subject_id,
                subject_name=subj.name if subj else "Subject",
                ca1=sc.ca1,
                ca2=sc.ca2,
                exam=sc.exam,
                total=sc.total,
                grade=sc.grade,
                remark=sc.remark,
            )
        )

    score_items.sort(key=lambda x: x.subject_name)

    grand_total = round(sum(s.total for s in score_items), 2)
    max_obtainable = float(len(score_items) * 100)
    average = round(grand_total / len(score_items), 2) if score_items else 0.0
    overall_grade, _ = calculate_grade(average)

    # Calculate class rank based on average
    classmates = db.query(User).filter(User.role == "student", User.class_id == student.class_id).all()
    averages = []
    for mate in classmates:
        mate_scores = (
            db.query(Score)
            .filter_by(student_id=mate.id, session=tpl.academic_session, term=tpl.current_term)
            .all()
        )
        mate_avg = (sum(m.total for m in mate_scores) / len(mate_scores)) if mate_scores else 0.0
        averages.append((mate.id, round(mate_avg, 2)))

    averages.sort(key=lambda x: x[1], reverse=True)
    rank = next((idx + 1 for idx, item in enumerate(averages) if item[0] == student.id), 1)

    summary_row = (
        db.query(TermReportSummary)
        .filter_by(student_id=student.id, session=tpl.academic_session, term=tpl.current_term)
        .first()
    )
    summary_data = (
        SummaryUpdate(
            student_id=student.id,
            days_opened=summary_row.days_opened,
            days_present=summary_row.days_present,
            punctuality=summary_row.punctuality,
            neatness=summary_row.neatness,
            conduct=summary_row.conduct,
            teacher_remark=summary_row.teacher_remark,
            principal_remark=summary_row.principal_remark,
        )
        if summary_row
        else SummaryUpdate(student_id=student.id)
    )

    return ReportSheetOut(
        template=TemplateOut.model_validate(tpl),
        student=serialize_user(student, db),
        scores=score_items,
        summary=summary_data,
        grand_total=grand_total,
        max_obtainable=max_obtainable,
        average=average,
        overall_grade=overall_grade,
        class_size=len(classmates),
        position=ordinal(rank),
    )