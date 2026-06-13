# Smart Campus Management System (SCMS) — Project Plan

## Project Overview

A centralized web application to digitize and automate all major academic and administrative activities within a college or university. The platform connects Students, Faculty, Department Admins, and Organization Admins in a single ecosystem.

**Tech Stack**
- Backend: Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis, JWT
- Frontend: React.js, Tailwind CSS, Redux Toolkit
- AI/ML: Pandas, NumPy, Scikit-Learn, XGBoost
- DevOps: Docker, GitHub Actions, AWS / Azure

---

## Phase Timeline

| Phase | Focus | Duration |
|-------|-------|----------|
| Phase 1 | Foundation & Infrastructure | Week 1–2 |
| Phase 2 | Student & Faculty Management | Week 3–4 |
| Phase 3 | Attendance Management | Week 5–7 |
| Phase 4 | Assignment Management | Week 8–9 |
| Phase 5 | Fee Management | Week 10–11 |
| Phase 6 | Announcements & Notifications | Week 12–13 |
| Phase 7 | Certificate Management | Week 14–15 |
| Phase 8 | Analytics & Dashboards | Week 16–17 |
| Phase 9 | AI Features | Week 18–19 |
| Phase 10 | Frontend Development | Week 20–24 |
| Phase 11 | Testing & Deployment | Week 25–26 |
| Phase 12 | Hostel Management | Week 27–28 |

**Total Duration: ~28 weeks (7 months)**

---

## Phase 1 — Foundation & Infrastructure

**Goal:** Working backend skeleton with authentication before any feature work.

### Module 1.1 — Project Setup

- [ ] Initialize FastAPI project structure
  - [ ] Create folder layout: `app/`, `routers/`, `models/`, `schemas/`, `services/`, `utils/`, `tests/`
  - [ ] Configure `main.py` with FastAPI app instance
  - [ ] Set up dependency injection patterns
  - [ ] Add global exception handlers

- [ ] Configure Database Stack
  - [ ] Set up PostgreSQL connection string
  - [ ] Configure SQLAlchemy `Base` and session factory
  - [ ] Initialize Alembic for migrations
  - [ ] Run first baseline migration

- [ ] Development Environment
  - [ ] Write `docker-compose.yml` (app + postgres + redis)
  - [ ] Create `.env` file and Pydantic settings model
  - [ ] Add `requirements.txt` / `pyproject.toml`
  - [ ] Configure logging (structured JSON logs)

- [ ] Middleware
  - [ ] CORS middleware with allowed origins
  - [ ] Rate limiting middleware (slowapi / Redis-backed)
  - [ ] Request ID and request logging middleware

### Module 1.2 — Authentication & Security

- [ ] User Model
  - [ ] Fields: `id`, `email`, `hashed_password`, `role` (enum), `is_verified`, `is_active`, `created_at`
  - [ ] Role enum: `student`, `faculty`, `dept_admin`, `org_admin`
  - [ ] Create Alembic migration for users table

- [ ] JWT Authentication
  - [ ] Access token (15 min TTL)
  - [ ] Refresh token (7 days TTL)
  - [ ] Token blacklist stored in Redis on logout

- [ ] Register Endpoint
  - [ ] Validate email uniqueness
  - [ ] Hash password with bcrypt
  - [ ] Send verification email on registration

- [ ] Login / Logout Endpoints
  - [ ] Verify credentials, return access + refresh tokens
  - [ ] Refresh token rotation endpoint
  - [ ] Logout: blacklist token in Redis

- [ ] Email Verification
  - [ ] Generate signed verification token (expiry: 24h)
  - [ ] Send verification link via email
  - [ ] Verify endpoint: activate account
  - [ ] Resend verification endpoint (rate-limited)

- [ ] Forgot / Reset Password
  - [ ] Generate OTP or signed reset link (expiry: 15 min)
  - [ ] Send reset email
  - [ ] Reset password endpoint with token validation

- [ ] RBAC Middleware
  - [ ] `get_current_user` FastAPI dependency
  - [ ] `require_role(*roles)` dependency factory
  - [ ] Apply role guards on all protected routes

---

## Phase 2 — Student & Faculty Management

**Goal:** Full profiles for both core user types with admin CRUD.

### Module 2.1 — Student Management

- [ ] Student Model
  - [ ] Fields: `roll_number`, `name`, `email`, `phone`, `dept_id`, `semester_id`, `section`, `blood_group`, `address`, `guardian_name`, `guardian_phone`
  - [ ] Alembic migration for students table

- [ ] Student CRUD APIs
  - [ ] `POST /students` — create (org_admin / dept_admin)
  - [ ] `GET /students/{id}` — read (self + admin)
  - [ ] `PUT /students/{id}` — update profile
  - [ ] `DELETE /students/{id}` — soft delete (set `is_active = false`)

- [ ] Department & Semester Mapping
  - [ ] Department model: `id`, `name`, `code`, `head_faculty_id`
  - [ ] Semester model: `id`, `number`, `dept_id`, `start_date`, `end_date`
  - [ ] Course enrollment junction table: `student_id`, `subject_id`

- [ ] Search & Filter
  - [ ] Filter by department, semester, section, status
  - [ ] Full-text search by name or roll number
  - [ ] Paginated results

- [ ] Student Status Management
  - [ ] Status enum: `active`, `suspended`, `alumni`, `transferred`
  - [ ] Status change endpoint (admin only) with audit log

### Module 2.2 — Faculty Management

- [ ] Faculty Model
  - [ ] Fields: `employee_id`, `name`, `dept_id`, `designation`, `email`, `phone`, `is_active`
  - [ ] Alembic migration for faculty table

- [ ] Faculty CRUD APIs
  - [ ] `POST /faculty` — create (org_admin / dept_admin)
  - [ ] `GET /faculty/{id}` — read (self + admin)
  - [ ] `PUT /faculty/{id}` — update profile
  - [ ] `DELETE /faculty/{id}` — deactivate

- [ ] Subject & Department Assignment
  - [ ] Subject model: `id`, `name`, `code`, `dept_id`, `credits`
  - [ ] Faculty-Subject junction table
  - [ ] Assign/unassign subject endpoints

---

## Phase 3 — Attendance Management

**Goal:** All three attendance methods with full reporting and alerts.

### Module 3.1 — Student Attendance

- [ ] Attendance Model
  - [ ] Fields: `student_id`, `subject_id`, `faculty_id`, `date`, `status` (Present/Absent/Late/Medical), `marked_at`
  - [ ] Alembic migration for attendance table

- [ ] Manual Attendance
  - [ ] `POST /attendance/manual` — bulk mark by class + subject
  - [ ] `PUT /attendance/{id}` — edit within 24h window
  - [ ] Prevent duplicate entries for same student/subject/date

- [ ] QR Code Attendance
  - [ ] Generate session QR code (JWT-signed, 10 min TTL)
  - [ ] `POST /attendance/qr/generate` — faculty creates QR session
  - [ ] `POST /attendance/qr/scan` — student marks attendance via QR scan
  - [ ] Validate QR token not expired and student is enrolled

- [ ] Face Recognition Attendance
  - [ ] Store face encodings per student during registration
  - [ ] OpenCV + DeepFace integration for recognition
  - [ ] `POST /attendance/face` — process image, identify student, mark attendance

- [ ] Attendance Reports
  - [ ] Daily attendance view (faculty)
  - [ ] Monthly calendar heatmap (student/faculty)
  - [ ] Subject-wise attendance percentage per student
  - [ ] Export as CSV / PDF

- [ ] Attendance Alerts
  - [ ] Scheduled job (daily): calculate attendance % per student per subject
  - [ ] Flag students below 75%
  - [ ] Trigger in-app and email notification for flagged students

### Module 3.2 — Faculty Attendance

- [ ] Faculty Check-In / Check-Out
  - [ ] `POST /faculty-attendance/checkin` — timestamp-based
  - [ ] `POST /faculty-attendance/checkout` — calculate working hours
  - [ ] Optional: IP or geolocation validation

- [ ] Leave Requests
  - [ ] Leave model: `faculty_id`, `type`, `start_date`, `end_date`, `reason`, `status`
  - [ ] `POST /leaves` — submit leave request
  - [ ] `PUT /leaves/{id}/approve` — dept_admin approves/rejects

- [ ] Faculty Attendance Reports
  - [ ] Present days count, leave days, total working hours per month
  - [ ] Export CSV

---

## Phase 4 — Assignment Management

**Goal:** End-to-end assignment lifecycle from creation to graded result.

### Module 4.1 — Assignments

- [ ] Assignment Model
  - [ ] Fields: `title`, `description`, `subject_id`, `faculty_id`, `deadline`, `max_marks`, `file_url`, `is_published`

- [ ] Submission Model
  - [ ] Fields: `assignment_id`, `student_id`, `file_url`, `submitted_at`, `is_late`, `marks`, `feedback`, `graded_at`

- [ ] Faculty: Create & Manage Assignments
  - [ ] `POST /assignments` — create with file upload and deadline
  - [ ] `PUT /assignments/{id}` — edit (before any submission)
  - [ ] `DELETE /assignments/{id}` — delete
  - [ ] `PUT /assignments/{id}/publish` — publish to students

- [ ] Faculty: Grade Submissions
  - [ ] `GET /assignments/{id}/submissions` — paginated list
  - [ ] `PUT /submissions/{id}/grade` — enter marks + feedback
  - [ ] `PUT /assignments/{id}/publish-grades` — release all grades

- [ ] Student: View & Submit
  - [ ] `GET /assignments` — list with status (pending/submitted/graded)
  - [ ] `POST /assignments/{id}/submit` — file upload, check deadline
  - [ ] `GET /submissions/{id}` — view own submission and grade

---

## Phase 5 — Fee Management

**Goal:** Full fee lifecycle from structure definition to paid receipt.

### Module 5.1 — Fee Management

- [ ] Fee Structure Model
  - [ ] Fields: `dept_id`, `semester_id`, `academic_year`, `tuition_fee`, `lab_fee`, `exam_fee`, `other_fee`, `total`, `due_date`

- [ ] Student Fee Record Model
  - [ ] Fields: `student_id`, `fee_structure_id`, `paid_amount`, `balance`, `status` (paid/partial/pending/overdue)

- [ ] Payment Model
  - [ ] Fields: `student_fee_id`, `amount`, `method`, `transaction_id`, `gateway_response`, `paid_at`, `status`

- [ ] Admin: Fee Structure APIs
  - [ ] `POST /fee-structures` — create structure
  - [ ] `PUT /fee-structures/{id}` — update
  - [ ] `POST /fee-structures/{id}/assign` — assign to batch of students

- [ ] Late Fee Calculation
  - [ ] Daily scheduled job: check overdue records
  - [ ] Apply configured penalty (flat or percentage per day/week)
  - [ ] Update balance automatically

- [ ] Payment Gateway Integration
  - [ ] Razorpay or Stripe order creation endpoint
  - [ ] Webhook endpoint for payment confirmation
  - [ ] Update student fee record on successful payment

- [ ] PDF Receipt Generation
  - [ ] WeasyPrint / ReportLab template with institution letterhead
  - [ ] `GET /payments/{id}/receipt` — generate and return PDF

- [ ] Payment History
  - [ ] `GET /students/{id}/payments` — paginated, filterable by year/semester

---

## Phase 6 — Announcements & Notifications

**Goal:** Multi-channel communication reaching the right audience.

### Module 6.1 — Announcements

- [ ] Announcement Model
  - [ ] Fields: `title`, `body`, `type` (college/dept/subject/emergency), `author_id`, `target_dept_id`, `target_subject_id`, `is_active`, `created_at`

- [ ] Announcement CRUD APIs
  - [ ] `POST /announcements` — create (role-scoped: faculty → subject; admin → dept/college)
  - [ ] `GET /announcements` — filtered by caller's role and audience
  - [ ] `PUT /announcements/{id}` — update (author only)
  - [ ] `DELETE /announcements/{id}` — soft delete

- [ ] Email Delivery
  - [ ] Celery background task on announcement creation
  - [ ] SMTP / SendGrid integration
  - [ ] Batch email to target audience

- [ ] Push Notification Delivery
  - [ ] FCM (Firebase Cloud Messaging) integration
  - [ ] Device token model: `user_id`, `token`, `platform`
  - [ ] `POST /devices` — register device token

### Module 6.2 — Notifications

- [ ] Notification Model
  - [ ] Fields: `user_id`, `type`, `title`, `message`, `is_read`, `created_at`, `meta` (JSON)

- [ ] Event Triggers
  - [ ] Assignment deadline approaching (T-24h)
  - [ ] Fee due date approaching (T-3 days)
  - [ ] Attendance below 75% (daily job)
  - [ ] Certificate status changed
  - [ ] New announcement published

- [ ] In-App Notification Center
  - [ ] `GET /notifications` — paginated list for current user
  - [ ] `PUT /notifications/{id}/read` — mark as read
  - [ ] `PUT /notifications/read-all` — mark all as read
  - [ ] Unread count badge endpoint

---

## Phase 7 — Certificate Management

**Goal:** Fully digital certificate lifecycle with multi-step approval.

### Module 7.1 — Certificates

- [ ] Certificate Model
  - [ ] Fields: `student_id`, `type` (bonafide/study/transfer/conduct/internship/no-due), `reason`, `status` (applied/faculty-verified/approved/rejected/generated), `applied_at`, `approved_at`, `pdf_url`, `remarks`

- [ ] Student: Apply
  - [ ] `POST /certificates` — select type, auto-fill student data, add reason
  - [ ] `GET /certificates` — view own certificates and statuses

- [ ] Faculty: Verify
  - [ ] `GET /certificates/pending-verification` — queue of pending requests
  - [ ] `PUT /certificates/{id}/verify` — approve or reject with comment

- [ ] Admin: Final Approval
  - [ ] `GET /certificates/pending-approval` — faculty-verified requests
  - [ ] `PUT /certificates/{id}/approve` — approve, trigger PDF generation
  - [ ] `PUT /certificates/{id}/reject` — reject with reason

- [ ] PDF Generation
  - [ ] One template per certificate type
  - [ ] Auto-fill student data, date, institution name, authority signature placeholder
  - [ ] Store PDF to file storage (S3 or local)

- [ ] Student: Download
  - [ ] `GET /certificates/{id}/download` — return signed URL or stream PDF
  - [ ] Track download count

---

## Phase 8 — Analytics & Dashboards

**Goal:** Real-time widgets and downloadable reports for every role.

### Module 8.1 — Dashboards

- [ ] Student Dashboard API
  - [ ] Overall attendance percentage (all subjects)
  - [ ] Subject-wise attendance summary
  - [ ] Pending fee balance + due date
  - [ ] Upcoming assignment deadlines (next 7 days)
  - [ ] Certificate request statuses
  - [ ] Latest 5 announcements

- [ ] Faculty Dashboard API
  - [ ] Today's scheduled classes
  - [ ] Pending submissions to grade (count per assignment)
  - [ ] Attendance summary for today
  - [ ] Student performance overview (average marks per subject)
  - [ ] Latest announcements

- [ ] Admin Dashboard API
  - [ ] Total students and faculty (org-wide and per dept)
  - [ ] Attendance rate today (org-wide)
  - [ ] Total fee collected this semester vs target
  - [ ] Pending certificate requests count
  - [ ] Department-wise statistics

### Module 8.2 — Reports

- [ ] Student Reports
  - [ ] Attendance report (date range, subject filter, export PDF/CSV)
  - [ ] Assignment submission and marks report
  - [ ] Fee statement (all payments, balance)

- [ ] Faculty Reports
  - [ ] Faculty attendance report
  - [ ] Subject performance report (class average, top/bottom performers)

- [ ] Organization Reports
  - [ ] Department-wise attendance trends (chart data)
  - [ ] Fee collection trends by month/semester
  - [ ] Student performance trends across semesters

---

## Phase 9 — AI Features

**Goal:** ML models and chatbot to deliver predictive analytics.

### Module 9.1 — AI / ML

- [ ] Attendance Risk Prediction
  - [ ] Feature engineering: past attendance %, subject, semester, section
  - [ ] Train XGBoost classifier to flag at-risk students
  - [ ] Weekly batch job to run predictions and store results
  - [ ] Expose `GET /ai/attendance-risk` for admin/faculty

- [ ] Academic Performance Prediction
  - [ ] Features: attendance %, assignment scores, prior CGPA
  - [ ] Predict GPA range and failure risk per student
  - [ ] `GET /ai/performance-prediction/{student_id}`

- [ ] Student Recommendation Engine
  - [ ] Content-based filtering on academic profile
  - [ ] Recommend courses, certifications, internships
  - [ ] `GET /ai/recommendations/{student_id}`

- [ ] AI Chatbot
  - [ ] Intent classifier or RAG pipeline
  - [ ] Cover: fee queries, attendance queries, certificate status, assignment deadlines
  - [ ] `POST /ai/chat` — message in, response out
  - [ ] Store conversation history per session

---

## Phase 10 — Frontend Development

**Goal:** Complete React SPA connected to all backend APIs.

### Module 10.1 — React Frontend

- [ ] Project Setup
  - [ ] Vite + React + TypeScript
  - [ ] Tailwind CSS configuration
  - [ ] Redux Toolkit store setup
  - [ ] React Router v6 route definitions
  - [ ] Axios instance with JWT interceptor (auto-refresh on 401)
  - [ ] Role-based route guards (PrivateRoute component)

- [ ] Authentication Pages
  - [ ] Register page with form validation
  - [ ] Login page
  - [ ] Email verification page
  - [ ] Forgot password page
  - [ ] Reset password page

- [ ] Student Portal
  - [ ] Dashboard with all widgets
  - [ ] Attendance view (calendar + subject-wise table)
  - [ ] Assignments list, submission form, grades view
  - [ ] Fee payment page + payment history + receipt download
  - [ ] Certificate application form + status tracking

- [ ] Faculty Portal
  - [ ] Dashboard with all widgets
  - [ ] Mark attendance (manual + QR generation)
  - [ ] Assignment creation form, submissions list, grading interface
  - [ ] Announcement composer

- [ ] Admin Portal
  - [ ] Student management table (CRUD + search/filter)
  - [ ] Faculty management table
  - [ ] Fee structure creator + assignment
  - [ ] Reports page with chart visualizations (Recharts / Chart.js)
  - [ ] Analytics overview with KPI cards

- [ ] Shared Components
  - [ ] Responsive sidebar + topbar layout
  - [ ] Dark mode toggle
  - [ ] Notification bell with unread count
  - [ ] Toast notification system
  - [ ] File upload component with progress
  - [ ] Paginated table component

---

## Phase 11 — Testing & Deployment

**Goal:** Production-ready, tested, containerized, and cloud-deployed.

### Module 11.1 — Testing

- [ ] Unit Tests
  - [ ] pytest setup with fixtures and factory functions
  - [ ] Service layer tests with mocked repository
  - [ ] Utility function tests (fee calculation, JWT, password hashing)

- [ ] Integration Tests
  - [ ] FastAPI `TestClient` for all API endpoints
  - [ ] Dedicated test PostgreSQL database (auto-reset per test session)
  - [ ] Test coverage > 80%

- [ ] Load Testing
  - [ ] Locust scenarios: bulk attendance marking, concurrent fee payments
  - [ ] Identify and resolve bottlenecks
  - [ ] Target: 200 concurrent users without degradation

### Module 11.2 — Deployment

- [ ] Docker
  - [ ] `Dockerfile` for FastAPI app (multi-stage build)
  - [ ] `Dockerfile` for React frontend (nginx static serve)
  - [ ] `docker-compose.prod.yml` with nginx, app, postgres, redis

- [ ] CI/CD Pipeline (GitHub Actions)
  - [ ] Lint → Test → Build Docker image → Push to registry
  - [ ] Auto-deploy to staging on `develop` branch merge
  - [ ] Manual approval gate for production deploy

- [ ] Cloud Deployment
  - [ ] AWS EC2 / ECS or Azure App Service for API
  - [ ] AWS RDS for PostgreSQL
  - [ ] AWS ElastiCache for Redis
  - [ ] S3 bucket for file storage (assignments, certificates, receipts)

- [ ] Domain & SSL
  - [ ] Nginx reverse proxy configuration
  - [ ] Let's Encrypt SSL certificate (Certbot auto-renew)
  - [ ] Custom domain DNS configuration

---

## Phase 12 — Hostel Management

**Goal:** Full digital hostel lifecycle — room allocation, outpass, leave requests, visitor log, and warden dashboard.

### Module 12.1 — Hostel Setup

- [ ] Hostel & Room Models
  - [ ] `Hostel`: id, name, total_rooms, warden_id (FK faculty/user), gender, address
  - [ ] `HostelRoom`: id, hostel_id, room_number, floor, capacity, room_type (single/double/triple)
  - [ ] `HostelAllocation`: student_id, room_id, hostel_id, academic_year, check_in_date, check_out_date, is_active
  - [ ] UniqueConstraint: one active allocation per student per academic year

- [ ] Hostel Admin APIs
  - [ ] `POST /hostels` — create hostel (org_admin)
  - [ ] `POST /hostels/{id}/rooms` — add rooms
  - [ ] `POST /hostels/{id}/allocate` — assign student to room
  - [ ] `PUT /allocations/{id}/checkout` — mark student as checked out
  - [ ] `GET /hostels/{id}/rooms` — list rooms with occupancy status
  - [ ] `GET /hostels/{id}/students` — list all allocated students

### Module 12.2 — Outpass System

- [ ] Outpass Model
  - [ ] Fields: `student_id`, `hostel_id`, `reason`, `destination`, `departure_time`, `expected_return_time`, `actual_return_time`, `status` (pending/approved/rejected/expired/returned), `approved_by_id`, `remarks`, `created_at`

- [ ] Student: Apply for Outpass
  - [ ] `POST /outpass` — apply with reason, destination, departure & return time
  - [ ] `GET /outpass/my` — view my outpass history
  - [ ] `DELETE /outpass/{id}` — cancel a pending outpass

- [ ] Warden: Manage Outpass
  - [ ] `GET /outpass/pending` — list all pending outpass requests
  - [ ] `PUT /outpass/{id}/approve` — approve with optional remarks
  - [ ] `PUT /outpass/{id}/reject` — reject with reason
  - [ ] `PUT /outpass/{id}/return` — mark student as returned (gate staff)

- [ ] Auto-Expiry
  - [ ] Mark outpass as `expired` if student has not returned past expected_return_time
  - [ ] Trigger notification to warden on expiry

### Module 12.3 — Student Leave Requests

- [ ] Leave Request Model
  - [ ] Fields: `student_id`, `hostel_id`, `leave_type` (home/medical/emergency/other), `reason`, `destination`, `contact_during_leave`, `start_date`, `end_date`, `return_date` (actual), `status` (pending/approved/rejected/returned), `approved_by_id`, `parent_notified`, `remarks`, `created_at`

- [ ] Student: Apply for Leave
  - [ ] `POST /hostel-leaves` — apply with dates, reason, destination, emergency contact
  - [ ] `GET /hostel-leaves/my` — view my leave requests and status
  - [ ] `DELETE /hostel-leaves/{id}` — cancel a pending request

- [ ] Warden: Manage Leaves
  - [ ] `GET /hostel-leaves/pending` — queue of pending leave requests
  - [ ] `PUT /hostel-leaves/{id}/approve` — approve + optional parent SMS/email notification
  - [ ] `PUT /hostel-leaves/{id}/reject` — reject with reason
  - [ ] `PUT /hostel-leaves/{id}/return` — mark student as returned

- [ ] Parent Notification (on approval)
  - [ ] Send email to parent/guardian with leave details
  - [ ] Include expected return date and contact number

### Module 12.4 — Visitor Management

- [ ] Visitor Log Model
  - [ ] Fields: `student_id`, `hostel_id`, `visitor_name`, `visitor_relation`, `visitor_phone`, `purpose`, `check_in_time`, `check_out_time`, `approved_by_id`

- [ ] Visitor APIs
  - [ ] `POST /visitors` — log a visitor entry (warden/gate staff)
  - [ ] `PUT /visitors/{id}/checkout` — log visitor exit time
  - [ ] `GET /visitors/hostel/{hostel_id}` — today's visitor log (warden)
  - [ ] `GET /visitors/student/{student_id}` — visitor history for a student

### Module 12.5 — Warden Dashboard & Reports

- [ ] Warden Dashboard
  - [ ] Current occupancy count (present / on-leave / on-outpass)
  - [ ] Pending outpass approvals count
  - [ ] Pending leave approvals count
  - [ ] Students currently overdue (outpass expired, leave overdue)
  - [ ] Today's visitor log summary

- [ ] Reports
  - [ ] Monthly leave report per student (export CSV/PDF)
  - [ ] Outpass frequency report (flag students with excessive outpasses)
  - [ ] Room occupancy report

---

## Deliverables Summary

| Deliverable | Phase |
|-------------|-------|
| Working auth system with RBAC | Phase 1 |
| Student & Faculty management APIs | Phase 2 |
| Attendance system (manual + QR + face) | Phase 3 |
| Assignment workflow APIs | Phase 4 |
| Fee payment with gateway integration | Phase 5 |
| Announcements + notification system | Phase 6 |
| Certificate lifecycle with PDF generation | Phase 7 |
| Dashboards and report exports | Phase 8 |
| ML models + AI chatbot | Phase 9 |
| Full React frontend | Phase 10 |
| Tested and deployed production app | Phase 11 |
| Hostel outpass, leave, visitor & warden management | Phase 12 |
