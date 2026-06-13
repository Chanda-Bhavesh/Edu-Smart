/**
 * Typed API functions for every SCMS endpoint used by the frontend.
 * All paths match backend /api/v1/... routes.
 */
import { api, BASE } from "./client";

// ── Auth ───────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string; user: import("./client").AuthUser }>(
      "/auth/login",
      { email, password },
      { skipAuth: true } as never,
    ),

  logout: (refreshToken: string) =>
    api.post("/auth/logout", { refresh_token: refreshToken }),

  me: () => api.get<import("./client").AuthUser>("/auth/me"),
};

// ── Student ────────────────────────────────────────────────────────────────────
export const studentApi = {
  me: () => api.get<StudentProfile>("/students/me"),
  attendance: () =>
    api.get<BackendAttendanceReport>("/attendance/my-report").then(transformAttendanceReport),
  assignments: () => api.get<Assignment[]>("/assignments/my"),
  fees: () => api.get<StudentFeeSummary>("/fees/my"),
  feePayments: (feeId: string) => api.get<FeePaymentResponse[]>(`/fees/my/${feeId}/payments`),
  downloadReceipt: (paymentId: string) =>
    `${BASE}/fee-payments/${paymentId}/receipt`,
  certificates: () => api.get<CertificateRequest[]>("/certificates/my"),
  requestCertificate: (type: string, purpose?: string) =>
    api.post<CertificateRequest>("/certificates/request", { certificate_type: type, purpose }),
  downloadCertificate: (certId: string) =>
    `${BASE}/certificates/${certId}/download`,
  submitAssignment: (assignmentId: string, formData: FormData) =>
    api.upload<Submission>(`/assignments/${assignmentId}/submit`, formData),
  notifications: () => api.get<Notification[]>("/notifications"),
  markNotificationRead: (id: string) => api.put(`/notifications/${id}/read`),
  // Hostel
  applyOutpass: (data: OutpassCreate) => api.post<OutpassResponse>("/hostels/outpass", data),
  myOutpasses: () => api.get<OutpassResponse[]>("/hostels/outpass/me"),
  applyLeave: (data: LeaveCreate) => api.post<LeaveResponse>("/hostels/leave", data),
  myLeaves: () => api.get<LeaveResponse[]>("/hostels/leave/me"),
  // AI
  myRisk: () => api.get<StudentRiskReport>("/ai/attendance-risk/me"),
  myPerformance: () => api.get<PerformancePrediction>("/ai/performance/me"),
  chat: (message: string, session_id?: string) =>
    api.post<ChatResponse>("/ai/chat", { message, session_id }),
  chatSessions: () => api.get<ChatSession[]>("/ai/chat/sessions"),
  chatHistory: (sessionId: string) =>
    api.get<ChatHistoryResponse>(`/ai/chat/sessions/${sessionId}`),
};

// ── Faculty ────────────────────────────────────────────────────────────────────
export const facultyApi = {
  me: () => api.get<FacultyProfile>("/faculty/me"),
  courseAssignments: () => api.get<CourseAssignment[]>("/course-assignments"),
  timetableToday: () =>
    api
      .get<{ date: string; day_of_week: string; slots: TimetableSlot[] }>("/timetable/my-today")
      .then((d) => d.slots),
  getStudentsForSlot: (courseAssignmentId: string) =>
    api
      .get<CourseAssignmentWithStudents>(`/course-assignments/${courseAssignmentId}/students`)
      .then((d) => d.students),
  markBulkAttendance: (slotId: string, date: string, records: AttendanceRecord[]) =>
    api.post("/attendance/manual", {
      timetable_slot_id: slotId,
      date,
      entries: records.map((r) => ({ student_id: r.student_id, status: r.status })),
    }),
  getSessionAttendance: (slotId: string) =>
    api.get<AttendanceSession>(`/attendance/session/${slotId}`),
  assignments: () => api.get<Assignment[]>("/assignments"),
  createAssignment: (data: AssignmentCreate) => api.post<Assignment>("/assignments", data),
  getSubmissions: (assignmentId: string) =>
    api.get<Submission[]>(`/assignments/${assignmentId}/submissions`),
  gradeSubmission: (submissionId: string, marks: number, feedback?: string) =>
    api.put(`/submissions/${submissionId}/grade`, { marks, feedback }),
  createAnnouncement: (data: AnnouncementCreate) =>
    api.post("/announcements", data),
  leaveRequests: () => api.get<FacultyLeave[]>("/faculty-attendance/leave/me"),
  applyLeave: (data: FacultyLeaveCreate) =>
    api.post<FacultyLeave>("/faculty-attendance/leave", data),
};

// ── Admin (dept + org) ─────────────────────────────────────────────────────────
export const adminApi = {
  dashboard: () => api.get<AdminDashboard>("/dashboard/admin"),
  students: (params?: { semester_id?: string; section?: string; search?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<StudentProfile[]>(`/students${q ? "?" + q : ""}`);
  },
  faculty: () => api.get<{ items: FacultyProfile[]; total: number }>("/faculty").then((d) => d.items),
  departments: () => api.get<Department[]>("/departments"),
  announcements: () => api.get<AnnouncementItem[]>("/announcements"),
  createAnnouncement: (data: AnnouncementCreate) => api.post("/announcements", data),
  atRiskStudents: () => api.get<AtRiskSummary[]>("/ai/attendance-risk"),
  certificates: () => api.get<CertificateRequest[]>("/certificates/requests"),
  approveCertificate: (id: string) =>
    api.put(`/certificates/${id}/review`, { status: "approved" }),
  rejectCertificate: (id: string, reason: string) =>
    api.put(`/certificates/${id}/review`, { status: "rejected", admin_remarks: reason }),
  feeReport: () =>
    api.get<AdminDashboard>("/dashboard/admin").then((d) => ({
      total_collected: d.total_fee_collected,
      total_pending: d.total_fee_expected - d.total_fee_collected,
      collection_by_type: [] as FeeByType[],
    })),
  attendanceReport: () =>
    api.get<AdminDashboard>("/dashboard/admin").then((d) => ({
      overall_pct: d.today_attendance_rate,
      departments: d.dept_stats.map((s) => ({
        department: s.department_name,
        pct: s.today_attendance_rate ?? 0,
      })),
    })),
  studentFees: () => api.get<StudentFeeList[]>("/student-fees"),
};

// ── Warden / Hostel ────────────────────────────────────────────────────────────
export const hostelApi = {
  myHostels: () => api.get<HostelItem[]>("/hostels"),
  dashboard: (hostelId: string) =>
    api.get<WardenDashboard>(`/hostels/${hostelId}/dashboard`),
  rooms: (hostelId: string) => api.get<RoomItem[]>(`/hostels/${hostelId}/rooms`),
  allocations: (hostelId: string) =>
    api.get<AllocationItem[]>(`/hostels/${hostelId}/allocations`),
  // Outpasses
  outpasses: (hostelId: string, status?: string) => {
    const q = status ? `?status=${status}` : "";
    return api.get<OutpassResponse[]>(`/hostels/${hostelId}/outpass${q}`);
  },
  reviewOutpass: (outpassId: string, action: "approve" | "reject", remarks?: string) =>
    api.patch<OutpassResponse>(`/hostels/outpass/${outpassId}/review`, { action, remarks }),
  checkoutOutpass: (outpassId: string) =>
    api.patch<OutpassResponse>(`/hostels/outpass/${outpassId}/checkout`),
  returnOutpass: (outpassId: string) =>
    api.patch<OutpassResponse>(`/hostels/outpass/${outpassId}/return`),
  // Leaves
  leaves: (hostelId: string, status?: string) => {
    const q = status ? `?status=${status}` : "";
    return api.get<LeaveResponse[]>(`/hostels/${hostelId}/leave${q}`);
  },
  reviewLeave: (leaveId: string, action: "approve" | "reject", remarks?: string) =>
    api.patch<LeaveResponse>(`/hostels/leave/${leaveId}/review`, { action, remarks }),
  // Visitors
  visitors: (hostelId: string, todayOnly = false) =>
    api.get<VisitorItem[]>(`/hostels/${hostelId}/visitors?today_only=${todayOnly}`),
  logVisitor: (hostelId: string, data: VisitorCreate) =>
    api.post<VisitorItem>(`/hostels/${hostelId}/visitors`, data),
  checkoutVisitor: (visitorId: string) =>
    api.patch<VisitorItem>(`/hostels/visitors/${visitorId}/checkout`),
};

// ── Shared Types ───────────────────────────────────────────────────────────────

export type StudentProfile = {
  id: string;
  roll_number: string;
  section: string | null;
  phone: string | null;
  status: string;
  user: { id: string; email: string; full_name: string; role: string };
  department: { id: string; name: string };
  semester: { id: string; number: number };
};

export type FacultyProfile = {
  id: string;
  employee_id: string;
  designation: string;
  user: { id: string; email: string; full_name: string };
  department: { id: string; name: string };
};

export type Department = {
  id: string;
  name: string;
  code: string;
};

export type CourseAssignment = {
  id: string;
  subject: { id: string; name: string; code: string };
  faculty: { id: string; user: { full_name: string } };
  semester: { id: string; number: number };
  section: string;
  academic_year: string;
};

export type TimetableSlot = {
  id: string;
  course_assignment_id: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  room_number: string | null;
  is_active: boolean;
  subject: { id: string; name: string; code: string };
  faculty_name: string;
  section: string;
  semester_number: number;
};

export type AttendanceRecord = {
  student_id: string;
  status: "present" | "absent" | "late" | "medical";
};

export type AttendanceSession = {
  timetable_slot_id: string;
  date: string;
  records: Array<{ student_id: string; status: string; student_name: string }>;
};

export type AttendanceReport = {
  subjects: Array<{
    subject_id: string;
    subject_name: string;
    subject_code: string;
    sessions_attended: number;
    total_sessions: number;
    attendance_pct: number;
    faculty_name: string;
  }>;
  overall_pct: number;
  total_present: number;
  total_sessions: number;
};

export type Assignment = {
  id: string;
  title: string;
  description: string | null;
  subject: { id: string; name: string; code: string };
  due_date: string;
  max_marks: number;
  status: "open" | "closed" | "graded";
  my_submission?: Submission | null;
};

export type AssignmentCreate = {
  title: string;
  description?: string;
  subject_id: string;
  due_date: string;
  max_marks: number;
};

export type Submission = {
  id: string;
  assignment_id: string;
  student_id: string;
  student_name?: string;
  submitted_at: string;
  file_url: string | null;
  marks: number | null;
  feedback: string | null;
  status: string;
};

export type StudentFeeDetail = {
  id: string;
  total_amount: number;
  discount_amount: number;
  fine_amount: number;
  net_amount: number;
  amount_paid: number;
  balance: number;
  status: "pending" | "partial" | "paid" | "overdue";
  due_date: string;
  waiver_reason: string | null;
  academic_year: string | null;
  tuition_fee: number | null;
  exam_fee: number | null;
  library_fee: number | null;
  lab_fee: number | null;
  other_fee: number | null;
  department_name: string | null;
  semester_number: number | null;
};

export type StudentFeeSummary = {
  student_id: string;
  student_name: string;
  roll_number: string;
  fees: StudentFeeDetail[];
  total_paid_ever: number;
  total_outstanding: number;
};

export type FeePaymentResponse = {
  id: string;
  amount: number;
  payment_mode: string;
  payment_date: string;
  transaction_id: string | null;
  receipt_number: string | null;
};

export type StudentFeeList = StudentFeeDetail;

export type CertificateRequest = {
  id: string;
  certificate_type: string;
  purpose: string | null;
  status: "pending" | "under_review" | "approved" | "rejected" | "issued";
  certificate_number: string | null;
  created_at: string;
  issued_at: string | null;
};

export type Notification = {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
};

export type AnnouncementItem = {
  id: string;
  title: string;
  content: string;
  target: string;
  priority: string;
  created_at: string;
  author: { full_name: string };
};

export type AnnouncementCreate = {
  title: string;
  content: string;
  target_type: "all" | "students" | "faculty" | "department" | "dept_students" | "dept_faculty" | "semester_section";
  priority: "normal" | "important" | "urgent";
  department_id?: string;
  semester_id?: string;
  section?: string;
};

export type AtRiskSummary = {
  student_id: string;
  student_name: string;
  roll_number: string;
  section: string;
  overall_attendance_pct: number;
  overall_risk_level: "low" | "medium" | "high" | "critical";
  critical_subject_count: number;
};

export type StudentRiskReport = {
  student_id: string;
  student_name: string;
  roll_number: string;
  overall_attendance_pct: number;
  overall_risk_level: string;
  subject_risks: Array<{
    subject_name: string;
    subject_code: string;
    current_attendance_pct: number;
    sessions_needed_for_75: number;
    sessions_remaining: number;
    is_recoverable: boolean;
    risk_level: string;
    recommendation: string;
  }>;
  critical_subjects: number;
  at_risk_subjects: number;
  safe_subjects: number;
  predicted_at: string;
};

export type PerformancePrediction = {
  overall_weighted_score: number;
  predicted_overall_grade: string;
  failure_risk: "low" | "medium" | "high";
  subject_predictions: Array<{
    subject_name: string;
    attendance_pct: number;
    avg_marks_pct: number;
    predicted_grade: string;
  }>;
  key_concerns: string[];
  strengths: string[];
};

export type ChatResponse = {
  session_id: string;
  session_title: string;
  reply: string;
  created_at: string;
};

export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
};

export type ChatHistoryResponse = {
  session_id: string;
  title: string;
  messages: Array<{ id: string; role: "user" | "assistant"; content: string; created_at: string }>;
};

export type FeeReport = {
  total_collected: number;
  total_pending: number;
  collection_by_type: Array<{ fee_type: string; amount: number }>;
};

export type AttendanceReportSummary = {
  overall_pct: number;
  departments: Array<{ department: string; pct: number }>;
};

export type HostelItem = {
  id: string;
  name: string;
  hostel_type: string;
  warden_name: string | null;
  total_capacity: number;
  is_active: boolean;
};

export type RoomItem = {
  id: string;
  room_number: string;
  floor: number;
  room_type: string;
  capacity: number;
  current_occupancy: number;
  is_active: boolean;
};

export type AllocationItem = {
  id: string;
  student_name: string;
  roll_number: string;
  room_number: string;
  allocated_date: string;
  is_active: boolean;
};

export type WardenDashboard = {
  hostel_id: string;
  hostel_name: string;
  total_capacity: number;
  current_occupancy: number;
  available_beds: number;
  pending_outpasses: number;
  pending_leaves: number;
  todays_visitors: number;
  recent_outpasses: OutpassResponse[];
  recent_leaves: LeaveResponse[];
};

export type OutpassCreate = {
  reason: string;
  destination: string;
  contact_at_destination?: string;
  from_datetime: string;
  to_datetime: string;
};

export type OutpassResponse = {
  id: string;
  student_name: string;
  roll_number: string;
  reason: string;
  destination: string;
  from_datetime: string;
  to_datetime: string;
  status: "pending" | "approved" | "rejected" | "checked_out" | "returned";
  reviewer_name: string | null;
  warden_remarks: string | null;
  requested_at: string;
};

export type LeaveCreate = {
  reason: string;
  destination: string;
  from_date: string;
  to_date: string;
  parent_name?: string;
  parent_contact?: string;
  parent_relation?: string;
};

export type LeaveResponse = {
  id: string;
  student_name: string;
  roll_number: string;
  reason: string;
  destination: string;
  from_date: string;
  to_date: string;
  status: "pending" | "approved" | "rejected";
  reviewer_name: string | null;
  warden_remarks: string | null;
  requested_at: string;
};

export type VisitorCreate = {
  student_id: string;
  visitor_name: string;
  visitor_relation: string;
  visitor_phone?: string;
  visitor_id_type?: string;
  visitor_id_number?: string;
  purpose?: string;
};

export type VisitorItem = {
  id: string;
  student_name: string;
  roll_number: string;
  visitor_name: string;
  visitor_relation: string;
  visitor_phone: string | null;
  check_in_time: string;
  check_out_time: string | null;
  purpose: string | null;
};

export type FacultyLeave = {
  id: string;
  leave_type: string;
  from_date: string;
  to_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  applied_at: string;
};

export type FacultyLeaveCreate = {
  leave_type: string;
  from_date: string;
  to_date: string;
  reason: string;
};

export type StudentInClass = {
  id: string;
  roll_number: string;
  section: string;
  full_name: string;
  email: string;
};

type CourseAssignmentWithStudents = {
  assignment: CourseAssignment;
  students: StudentInClass[];
  total_students: number;
};

export type AdminDashboard = {
  total_students: number;
  total_faculty: number;
  total_departments: number;
  today_attendance_rate: number;
  total_fee_expected: number;
  total_fee_collected: number;
  fee_collection_pct: number;
  overdue_fee_count: number;
  pending_certificate_requests: number;
  open_assignments: number;
  dept_stats: Array<{
    department_id: string;
    department_name: string;
    department_code: string;
    total_students: number;
    total_faculty: number;
    today_attendance_rate: number | null;
    pending_fee_count: number;
  }>;
  total_unread_system_notifications: number;
};

export type DashboardData = AdminDashboard;

type FeeByType = { fee_type: string; amount: number };

type BackendAttendanceReport = {
  student_id: string;
  roll_number: string;
  full_name: string;
  overall_percentage: number;
  subjects: Array<{
    subject_id: string;
    subject_name: string;
    subject_code: string;
    total_sessions: number;
    present: number;
    absent: number;
    late: number;
    medical: number;
    percentage: number;
    is_at_risk: boolean;
  }>;
};

function transformAttendanceReport(data: BackendAttendanceReport): AttendanceReport {
  const totalPresent = data.subjects.reduce((s, sub) => s + sub.present, 0);
  const totalSessions = data.subjects.reduce((s, sub) => s + sub.total_sessions, 0);
  return {
    subjects: data.subjects.map((s) => ({
      subject_id: s.subject_id,
      subject_name: s.subject_name,
      subject_code: s.subject_code,
      sessions_attended: s.present,
      total_sessions: s.total_sessions,
      attendance_pct: s.percentage,
      faculty_name: "",
    })),
    overall_pct: data.overall_percentage,
    total_present: totalPresent,
    total_sessions: totalSessions,
  };
}
