let currentTemplate = null;

async function routeByRole(user) {
  document.getElementById("loginView").classList.add("hidden");
  document.getElementById("logoutBtn").classList.remove("hidden");

  const badge = document.getElementById("userBadge");
  badge.textContent = `${user.full_name} (${user.role.toUpperCase()})`;
  badge.classList.remove("hidden");

  currentTemplate = await apiRequest("/template");

  if (user.role === "admin") {
    document.getElementById("adminView").classList.remove("hidden");
    await initAdminPortal();
  } else if (user.role === "staff") {
    document.getElementById("staffView").classList.remove("hidden");
    await initStaffPortal();
  } else if (user.role === "student") {
    await loadAndRenderReportSheet(user.id);
  }
}

// ---------------- ADMIN PORTAL ----------------

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.remove("hidden");
  });
});

document.getElementById("userRole").addEventListener("change", (e) => {
  const wrap = document.getElementById("studentClassWrap");
  wrap.classList.toggle("hidden", e.target.value !== "student");
});

async function initAdminPortal() {
  populateTemplateForm(currentTemplate);
  await refreshAdminData();
}

function populateTemplateForm(tpl) {
  document.getElementById("tplSchoolName").value = tpl.school_name;
  document.getElementById("tplSchoolMotto").value = tpl.school_motto;
  document.getElementById("tplSchoolAddress").value = tpl.school_address;
  document.getElementById("tplPrincipalName").value = tpl.principal_name;
  document.getElementById("tplSession").value = tpl.academic_session;
  document.getElementById("tplTerm").value = tpl.current_term;
  document.getElementById("tplCa1Label").value = tpl.ca1_label;
  document.getElementById("tplCa1Max").value = tpl.ca1_max;
  document.getElementById("tplCa2Label").value = tpl.ca2_label;
  document.getElementById("tplCa2Max").value = tpl.ca2_max;
  document.getElementById("tplExamLabel").value = tpl.exam_label;
  document.getElementById("tplExamMax").value = tpl.exam_max;
  document.getElementById("tplNextTerm").value = tpl.next_term_begins;
}

document.getElementById("templateForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      school_name: document.getElementById("tplSchoolName").value,
      school_motto: document.getElementById("tplSchoolMotto").value,
      school_address: document.getElementById("tplSchoolAddress").value,
      principal_name: document.getElementById("tplPrincipalName").value,
      academic_session: document.getElementById("tplSession").value,
      current_term: document.getElementById("tplTerm").value,
      ca1_label: document.getElementById("tplCa1Label").value,
      ca1_max: parseFloat(document.getElementById("tplCa1Max").value),
      ca2_label: document.getElementById("tplCa2Label").value,
      ca2_max: parseFloat(document.getElementById("tplCa2Max").value),
      exam_label: document.getElementById("tplExamLabel").value,
      exam_max: parseFloat(document.getElementById("tplExamMax").value),
      next_term_begins: document.getElementById("tplNextTerm").value,
    };
    currentTemplate = await apiRequest("/admin/template", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    showBanner("Report sheet template updated successfully.");
  } catch (err) {
    showBanner(err.message, true);
  }
});

async function refreshAdminData() {
  const [classes, subjects, users, assignments] = await Promise.all([
    apiRequest("/classes"),
    apiRequest("/subjects"),
    apiRequest("/admin/users"),
    apiRequest("/assignments"),
  ]);

  document.getElementById("classList").innerHTML = classes
    .map((c) => `<li><strong>${c.name}</strong> (${c.student_count} students)</li>`)
    .join("");

  document.getElementById("subjectList").innerHTML = subjects
    .map((s) => `<li><strong>${s.name}</strong> ${s.code ? `(${s.code})` : ""}</li>`)
    .join("");

  document.getElementById("assignmentList").innerHTML = assignments
    .map((a) => `<li>${a.staff_name} &rarr; <strong>${a.subject_name}</strong> (${a.class_name})</li>`)
    .join("");

  const classOptions = classes.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
  document.getElementById("assignClassId").innerHTML = classOptions;
  document.getElementById("userClassId").innerHTML = classOptions;

  document.getElementById("assignSubjectId").innerHTML = subjects
    .map((s) => `<option value="${s.id}">${s.name}</option>`)
    .join("");

  const staffUsers = users.filter((u) => u.role === "staff");
  document.getElementById("assignStaffId").innerHTML = staffUsers
    .map((u) => `<option value="${u.id}">${u.full_name} (${u.username})</option>`)
    .join("");

  const studentUsers = users.filter((u) => u.role === "student");
  document.getElementById("adminPreviewStudentSelect").innerHTML = studentUsers
    .map((s) => `<option value="${s.id}">${s.full_name} (${s.username}) - ${s.class_name || ""}</option>`)
    .join("");

  document.getElementById("usersTableBody").innerHTML = users
    .map(
      (u) => `
      <tr>
        <td>${u.username}</td>
        <td>${u.full_name}</td>
        <td>${u.role.toUpperCase()}</td>
        <td>${u.class_name || "-"}</td>
      </tr>`
    )
    .join("");
}

document.getElementById("classForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiRequest("/admin/classes", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("className").value,
        level: document.getElementById("classLevel").value,
      }),
    });
    e.target.reset();
    showBanner("Class created.");
    await refreshAdminData();
  } catch (err) {
    showBanner(err.message, true);
  }
});

document.getElementById("subjectForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiRequest("/admin/subjects", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("subjectName").value,
        code: document.getElementById("subjectCode").value,
      }),
    });
    e.target.reset();
    showBanner("Subject added.");
    await refreshAdminData();
  } catch (err) {
    showBanner(err.message, true);
  }
});

document.getElementById("assignForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiRequest("/admin/assignments", {
      method: "POST",
      body: JSON.stringify({
        staff_id: Number(document.getElementById("assignStaffId").value),
        class_id: Number(document.getElementById("assignClassId").value),
        subject_id: Number(document.getElementById("assignSubjectId").value),
      }),
    });
    showBanner("Staff assigned to subject and class.");
    await refreshAdminData();
  } catch (err) {
    showBanner(err.message, true);
  }
});

document.getElementById("userForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const role = document.getElementById("userRole").value;
    await apiRequest("/admin/users", {
      method: "POST",
      body: JSON.stringify({
        role,
        username: document.getElementById("userUsername").value,
        full_name: document.getElementById("userFullName").value,
        gender: document.getElementById("userGender").value,
        class_id: role === "student" ? Number(document.getElementById("userClassId").value) : null,
        password: document.getElementById("userPassword").value,
      }),
    });
    e.target.reset();
    document.getElementById("studentClassWrap").classList.add("hidden");
    showBanner("Account created successfully.");
    await refreshAdminData();
  } catch (err) {
    showBanner(err.message, true);
  }
});

document.getElementById("adminLoadReportBtn").addEventListener("click", async () => {
  const studentId = document.getElementById("adminPreviewStudentSelect").value;
  if (studentId) {
    await loadAndRenderReportSheet(Number(studentId));
  }
});

// ---------------- STAFF PORTAL ----------------

let staffAssignments = [];

async function initStaffPortal() {
  staffAssignments = await apiRequest("/assignments");
  const select = document.getElementById("staffAssignmentSelect");
  select.innerHTML = staffAssignments
    .map(
      (a) =>
        `<option value="${a.class_id}:${a.subject_id}">${a.class_name} — ${a.subject_name}</option>`
    )
    .join("");

  const students = await apiRequest("/admin/users?role=student");
  document.getElementById("summaryStudentId").innerHTML = students
    .map((s) => `<option value="${s.id}">${s.full_name} (${s.username})</option>`)
    .join("");
}

document.getElementById("loadSheetBtn").addEventListener("click", async () => {
  const val = document.getElementById("staffAssignmentSelect").value;
  if (!val) return;
  const [classId, subjectId] = val.split(":").map(Number);

  document.getElementById("thCa1").textContent = `${currentTemplate.ca1_label} (${currentTemplate.ca1_max})`;
  document.getElementById("thCa2").textContent = `${currentTemplate.ca2_label} (${currentTemplate.ca2_max})`;
  document.getElementById("thExam").textContent = `${currentTemplate.exam_label} (${currentTemplate.exam_max})`;

  const [students, existingScores] = await Promise.all([
    apiRequest(`/staff/class-students/${classId}`),
    apiRequest(`/staff/scores?class_id=${classId}&subject_id=${subjectId}`),
  ]);

  const scoreMap = Object.fromEntries(existingScores.map((s) => [s.student_id, s]));
  const tbody = document.getElementById("scoreEntryBody");

  tbody.innerHTML = students
    .map((st) => {
      const sc = scoreMap[st.id] || { ca1: 0, ca2: 0, exam: 0, total: 0, grade: "-" };
      return `
        <tr data-student-id="${st.id}">
          <td>${st.username}</td>
          <td>${st.full_name}</td>
          <td><input type="number" step="0.5" min="0" max="${currentTemplate.ca1_max}" class="inp-ca1" value="${sc.ca1}" /></td>
          <td><input type="number" step="0.5" min="0" max="${currentTemplate.ca2_max}" class="inp-ca2" value="${sc.ca2}" /></td>
          <td><input type="number" step="0.5" min="0" max="${currentTemplate.exam_max}" class="inp-exam" value="${sc.exam}" /></td>
          <td class="cell-total">${sc.total}</td>
          <td class="cell-grade">${sc.grade}</td>
          <td><button type="button" class="btn btn-primary btn-save-score">Save</button></td>
        </tr>`;
    })
    .join("");

  tbody.querySelectorAll(".btn-save-score").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const row = btn.closest("tr");
      const studentId = Number(row.dataset.studentId);
      const ca1 = parseFloat(row.querySelector(".inp-ca1").value) || 0;
      const ca2 = parseFloat(row.querySelector(".inp-ca2").value) || 0;
      const exam = parseFloat(row.querySelector(".inp-exam").value) || 0;

      try {
        const saved = await apiRequest("/staff/scores", {
          method: "POST",
          body: JSON.stringify({ student_id: studentId, class_id: classId, subject_id: subjectId, ca1, ca2, exam }),
        });
        row.querySelector(".cell-total").textContent = saved.total;
        row.querySelector(".cell-grade").textContent = saved.grade;
        showBanner(`Saved score for ${saved.student_name}: ${saved.total} (${saved.grade})`);
      } catch (err) {
        showBanner(err.message, true);
      }
    });
  });

  document.getElementById("scoreSheetContainer").classList.remove("hidden");
});

document.getElementById("summaryForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiRequest("/staff/summary", {
      method: "POST",
      body: JSON.stringify({
        student_id: Number(document.getElementById("summaryStudentId").value),
        days_opened: Number(document.getElementById("sumDaysOpened").value),
        days_present: Number(document.getElementById("sumDaysPresent").value),
        punctuality: document.getElementById("sumPunctuality").value,
        neatness: document.getElementById("sumNeatness").value,
        conduct: document.getElementById("sumConduct").value,
        teacher_remark: document.getElementById("sumTeacherRemark").value,
        principal_remark: document.getElementById("sumPrincipalRemark").value,
      }),
    });
    showBanner("Student attendance and termly remarks saved.");
  } catch (err) {
    showBanner(err.message, true);
  }
});

// ---------------- REPORT SHEET RENDERER ----------------

async function loadAndRenderReportSheet(studentId) {
  try {
    const data = await apiRequest(`/reports/student/${studentId}`);
    const { template: t, student: s, scores, summary } = data;

    document.getElementById("repSchoolName").textContent = t.school_name;
    document.getElementById("repSchoolMotto").textContent = `"${t.school_motto}"`;
    document.getElementById("repSchoolAddress").textContent = t.school_address;
    document.getElementById("repStudentName").textContent = s.full_name;
    document.getElementById("repAdmissionNo").textContent = s.username;
    document.getElementById("repClassName").textContent = s.class_name || "-";
    document.getElementById("repGender").textContent = s.gender || "-";
    document.getElementById("repSession").textContent = t.academic_session;
    document.getElementById("repTerm").textContent = t.current_term;
    document.getElementById("repPosition").textContent = `${data.position} out of ${data.class_size}`;
    document.getElementById("repNextTerm").textContent = t.next_term_begins;

    document.getElementById("repThCa1").textContent = `${t.ca1_label} (${t.ca1_max})`;
    document.getElementById("repThCa2").textContent = `${t.ca2_label} (${t.ca2_max})`;
    document.getElementById("repThExam").textContent = `${t.exam_label} (${t.exam_max})`;

    document.getElementById("repScoresBody").innerHTML = scores.length
      ? scores
          .map(
            (sc) => `
            <tr>
              <td>${sc.subject_name}</td>
              <td>${sc.ca1}</td>
              <td>${sc.ca2}</td>
              <td>${sc.exam}</td>
              <td><strong>${sc.total}</strong></td>
              <td><strong>${sc.grade}</strong></td>
              <td>${sc.remark}</td>
            </tr>`
          )
          .join("")
      : `<tr><td colspan="7">No assessment scores recorded for this term yet.</td></tr>`;

    document.getElementById("repMaxObtainable").textContent = data.max_obtainable;
    document.getElementById("repGrandTotal").textContent = data.grand_total;
    document.getElementById("repAverage").textContent = data.average;
    document.getElementById("repOverallGrade").textContent = data.overall_grade;

    document.getElementById("repAttendance").textContent = `${summary.days_present} / ${summary.days_opened} days`;
    document.getElementById("repPunctuality").textContent = summary.punctuality;
    document.getElementById("repNeatness").textContent = summary.neatness;
    document.getElementById("repConduct").textContent = summary.conduct;
    document.getElementById("repTeacherRemark").textContent = summary.teacher_remark;
    document.getElementById("repPrincipalRemark").textContent = summary.principal_remark;
    document.getElementById("repPrincipalName").textContent = t.principal_name;

    document.getElementById("reportSheetSection").classList.remove("hidden");
  } catch (err) {
    showBanner(err.message, true);
  }
}

document.getElementById("printReportBtn").addEventListener("click", () => window.print());

// ---------------- BOOTSTRAP ----------------

(async function init() {
  await checkApiStatus();
  const savedUser = getSavedUser();
  if (savedUser && getToken()) {
    try {
      const freshUser = await apiRequest("/auth/me");
      await routeByRole(freshUser);
    } catch {
      clearSession();
    }
  }
})();