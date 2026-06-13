export type Role = "student" | "faculty" | "dept-admin" | "org-admin" | "warden";

export const ROLES: { id: Role; title: string; tagline: string; emoji: string; accent: string }[] = [
  { id: "student", title: "Student", tagline: "Track attendance, assignments, fees & more", emoji: "🎒", accent: "bg-gradient-warm" },
  { id: "faculty", title: "Faculty", tagline: "Mark attendance, grade work, send updates", emoji: "📚", accent: "bg-gradient-cool" },
  { id: "dept-admin", title: "Dept Admin", tagline: "Run a department end-to-end", emoji: "🏛️", accent: "bg-gradient-sun" },
  { id: "warden", title: "Warden", tagline: "Outpasses, visitors, rooms — hostel at a glance", emoji: "🛏️", accent: "bg-gradient-cool" },
  { id: "org-admin", title: "Org Admin", tagline: "See the whole campus at a glance", emoji: "🌐", accent: "bg-gradient-warm" },
];

export const student = {
  name: "Aarav Sharma",
  rollNo: "21CS042",
  dept: "Computer Science",
  semester: 5,
  section: "B",
  email: "aarav.s@campus.edu",
  attendancePct: 82,
  cgpa: 8.7,
  guardian: "Rohit Sharma · +91 98xxxxx210",
};

export const subjects = [
  { code: "CS501", name: "Machine Learning", faculty: "Dr. Meera Iyer", attendance: 88 },
  { code: "CS502", name: "Compiler Design", faculty: "Prof. Anil Verma", attendance: 76 },
  { code: "CS503", name: "Distributed Systems", faculty: "Dr. Kavya Rao", attendance: 71 },
  { code: "CS504", name: "Web Engineering", faculty: "Prof. Sahil Khan", attendance: 92 },
  { code: "HU501", name: "Tech Communication", faculty: "Dr. Pooja Nair", attendance: 84 },
];

export const assignments = [
  { id: "a1", title: "ML Lab 4 — Regression report", subject: "CS501", due: "2026-06-18", status: "pending" as const, grade: null },
  { id: "a2", title: "Compiler — Lexical analyzer", subject: "CS502", due: "2026-06-15", status: "submitted" as const, grade: null },
  { id: "a3", title: "DS — Raft paper review", subject: "CS503", due: "2026-06-22", status: "pending" as const, grade: null },
  { id: "a4", title: "Web — Final project demo", subject: "CS504", due: "2026-06-10", status: "graded" as const, grade: "A" },
  { id: "a5", title: "TC — Group presentation", subject: "HU501", due: "2026-06-25", status: "pending" as const, grade: null },
];

export const announcements = [
  { id: "n1", title: "Mid-sem timetable released", body: "Check your dashboard for the updated schedule.", scope: "College", time: "2h ago", urgent: false },
  { id: "n2", title: "Library closed Saturday", body: "Annual stocktake. Reopens Monday 9am.", scope: "College", time: "5h ago", urgent: false },
  { id: "n3", title: "Power outage — Block C", body: "Scheduled 1pm–3pm tomorrow. Classes moved to Block A.", scope: "Department", time: "1d ago", urgent: true },
  { id: "n4", title: "ML guest lecture", body: "Dr. Patel from IISc on diffusion models, Friday 4pm.", scope: "Subject", time: "2d ago", urgent: false },
];

export const fees = {
  total: 84000,
  paid: 60000,
  pending: 24000,
  dueDate: "2026-06-30",
  history: [
    { id: "p1", label: "Semester 5 — Tuition (Part 1)", amount: 35000, date: "2026-02-12", method: "UPI" },
    { id: "p2", label: "Lab fee", amount: 8000, date: "2026-02-12", method: "UPI" },
    { id: "p3", label: "Hostel — Q1", amount: 17000, date: "2026-03-01", method: "Net Banking" },
  ],
};

export const certificates = [
  { id: "c1", type: "Bonafide Certificate", status: "Approved", date: "2026-05-22" },
  { id: "c2", type: "Internship Letter", status: "Faculty Review", date: "2026-06-08" },
  { id: "c3", type: "No Due Certificate", status: "Pending Admin", date: "2026-06-09" },
];

export const facultyMe = {
  name: "Dr. Meera Iyer",
  empId: "FAC-2049",
  dept: "Computer Science",
  designation: "Associate Professor",
  classesToday: 3,
  pendingEvaluations: 28,
  studentsTaught: 142,
};

export const todayClasses = [
  { time: "09:00", subject: "CS501 · ML", room: "Block A · 204", batch: "5B" },
  { time: "11:00", subject: "CS501 · ML Lab", room: "Lab 3", batch: "5A" },
  { time: "14:30", subject: "CS599 · Seminar", room: "Auditorium", batch: "5 All" },
];

export const classRoster = [
  { roll: "21CS041", name: "Aanya Mehta", attendance: 91, status: "P" as const },
  { roll: "21CS042", name: "Aarav Sharma", attendance: 82, status: "P" as const },
  { roll: "21CS043", name: "Diya Khanna", attendance: 68, status: "A" as const },
  { roll: "21CS044", name: "Ishaan Gupta", attendance: 74, status: "L" as const },
  { roll: "21CS045", name: "Kabir Patel", attendance: 95, status: "P" as const },
  { roll: "21CS046", name: "Maya Reddy", attendance: 88, status: "P" as const },
  { roll: "21CS047", name: "Neel Joshi", attendance: 59, status: "A" as const },
  { roll: "21CS048", name: "Riya Kapoor", attendance: 86, status: "P" as const },
];

export const submissions = [
  { roll: "21CS041", name: "Aanya Mehta", submittedAt: "2026-06-09 22:14", file: "ml-lab4-aanya.pdf", graded: false },
  { roll: "21CS042", name: "Aarav Sharma", submittedAt: "2026-06-10 09:02", file: "ml-lab4-aarav.zip", graded: true, grade: "A-" },
  { roll: "21CS045", name: "Kabir Patel", submittedAt: "2026-06-10 10:41", file: "lab4-kabir.pdf", graded: false },
  { roll: "21CS048", name: "Riya Kapoor", submittedAt: "2026-06-10 11:55", file: "ml4-riya.pdf", graded: false },
];

export const departments = [
  { id: "cs", name: "Computer Science", students: 612, faculty: 38, attendance: 86, color: "bg-gradient-warm" },
  { id: "ec", name: "Electronics & Comm.", students: 488, faculty: 31, attendance: 81, color: "bg-gradient-cool" },
  { id: "me", name: "Mechanical", students: 401, faculty: 27, attendance: 78, color: "bg-gradient-sun" },
  { id: "ce", name: "Civil", students: 322, faculty: 22, attendance: 74, color: "bg-gradient-cool" },
  { id: "bt", name: "Biotechnology", students: 264, faculty: 19, attendance: 83, color: "bg-gradient-warm" },
];

export const orgStats = {
  students: 2087,
  faculty: 137,
  departments: 5,
  feeCollectedCr: 12.4,
  feeTargetCr: 18.0,
  certificatesPending: 47,
  attendanceAvg: 81,
};

export const atRiskStudents = [
  { roll: "21CS047", name: "Neel Joshi", dept: "CS", attendance: 59, risk: "High" },
  { roll: "21CS043", name: "Diya Khanna", dept: "CS", attendance: 68, risk: "Medium" },
  { roll: "21EC112", name: "Vihaan Bose", dept: "EC", attendance: 64, risk: "High" },
  { roll: "21ME081", name: "Sara Pillai", dept: "ME", attendance: 71, risk: "Medium" },
];

export const wardenMe = {
  name: "Mrs. Lakshmi Pillai",
  empId: "WRD-014",
  hostel: "Nilgiri Block · Boys",
  rooms: 96,
  residents: 312,
  occupancy: 89,
};

export const outpasses = [
  { id: "op1", roll: "21CS042", name: "Aarav Sharma", room: "B-204", reason: "Family wedding · Pune", from: "2026-06-13 18:00", to: "2026-06-15 21:00", status: "pending" as const },
  { id: "op2", roll: "21CS045", name: "Kabir Patel", room: "B-208", reason: "Doctor appointment", from: "2026-06-12 14:00", to: "2026-06-12 19:00", status: "pending" as const },
  { id: "op3", roll: "21EC112", name: "Vihaan Bose", room: "B-117", reason: "Internship interview", from: "2026-06-14 08:00", to: "2026-06-14 20:00", status: "approved" as const },
  { id: "op4", roll: "21ME081", name: "Sara Pillai", room: "G-302", reason: "Weekend home visit", from: "2026-06-13 16:00", to: "2026-06-15 20:00", status: "pending" as const },
  { id: "op5", roll: "21CS047", name: "Neel Joshi", room: "B-221", reason: "Concert", from: "2026-06-10 17:00", to: "2026-06-11 02:00", status: "rejected" as const },
];

export const leaves = [
  { id: "lv1", roll: "21CS044", name: "Ishaan Gupta", reason: "Fever · medical rest", days: 3, from: "2026-06-12", status: "pending" as const },
  { id: "lv2", roll: "21EC076", name: "Tara Nambiar", reason: "Sister's wedding", days: 5, from: "2026-06-18", status: "approved" as const },
  { id: "lv3", roll: "21ME102", name: "Arjun Das", reason: "Family emergency", days: 2, from: "2026-06-11", status: "pending" as const },
];

export const visitors = [
  { id: "v1", name: "Rohit Sharma", visiting: "Aarav Sharma (B-204)", relation: "Father", checkIn: "2026-06-12 10:14", checkOut: null as string | null, idProof: "Aadhaar ••••4321" },
  { id: "v2", name: "Anjali Patel", visiting: "Kabir Patel (B-208)", relation: "Mother", checkIn: "2026-06-11 16:42", checkOut: "2026-06-11 18:30", idProof: "DL ••••9087" },
  { id: "v3", name: "Vikas Bose", visiting: "Vihaan Bose (B-117)", relation: "Uncle", checkIn: "2026-06-10 12:05", checkOut: "2026-06-10 13:50", idProof: "Aadhaar ••••2210" },
  { id: "v4", name: "Meera Joshi", visiting: "Neel Joshi (B-221)", relation: "Mother", checkIn: "2026-06-09 19:20", checkOut: "2026-06-09 20:45", idProof: "Voter ID ••••5566" },
];

export const rooms = [
  { id: "B-204", floor: 2, capacity: 3, occupied: 3, residents: ["Aarav Sharma", "Ishaan Gupta", "Kabir Patel"], status: "full" as const },
  { id: "B-208", floor: 2, capacity: 3, occupied: 2, residents: ["Maya Reddy", "Riya Kapoor"], status: "partial" as const },
  { id: "B-117", floor: 1, capacity: 2, occupied: 2, residents: ["Vihaan Bose", "Arjun Das"], status: "full" as const },
  { id: "B-221", floor: 2, capacity: 3, occupied: 1, residents: ["Neel Joshi"], status: "partial" as const },
  { id: "G-302", floor: 3, capacity: 2, occupied: 0, residents: [], status: "vacant" as const },
  { id: "B-305", floor: 3, capacity: 3, occupied: 3, residents: ["Aanya Mehta", "Diya Khanna", "Sara Pillai"], status: "full" as const },
  { id: "B-310", floor: 3, capacity: 2, occupied: 0, residents: [], status: "maintenance" as const },
];