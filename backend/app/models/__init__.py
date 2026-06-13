from app.models.user import User, UserRole
from app.models.department import Department
from app.models.semester import Semester
from app.models.subject import Subject, faculty_subjects, student_enrollments
from app.models.student import Student, StudentStatus
from app.models.faculty import Faculty, Designation
from app.models.course_assignment import CourseAssignment
from app.models.timetable import TimetableSlot, DayOfWeek
from app.models.attendance import Attendance, AttendanceStatus, AttendanceMethod, QRSession
from app.models.student_face import StudentFaceEncoding
from app.models.faculty_attendance import FacultyAttendance, FacultyAttendanceStatus, LeaveRequest, LeaveType, LeaveStatus
from app.models.assignment import Assignment, AssignmentStatus, Submission, SubmissionStatus
from app.models.fee import FeeStructure, StudentFee, FeePayment, FeeStatus, PaymentMode
from app.models.notification import (
    Announcement, AnnouncementRead, AnnouncementTarget,
    AnnouncementPriority, Notification, NotificationType,
)
from app.models.certificate import CertificateRequest, CertificateType, CertificateStatus
from app.models.ai_prediction import AIRiskPrediction, RiskLevel, ChatSession, ChatMessage
from app.models.hostel import (
    Hostel, HostelRoom, HostelAllocation, HostelType, RoomType,
    Outpass, OutpassStatus, HostelLeaveRequest, HostelLeaveStatus, VisitorLog,
)

__all__ = [
    "User", "UserRole",
    "Department",
    "Semester",
    "Subject", "faculty_subjects", "student_enrollments",
    "Student", "StudentStatus",
    "Faculty", "Designation",
    "CourseAssignment",
    "TimetableSlot", "DayOfWeek",
    "Attendance", "AttendanceStatus", "AttendanceMethod", "QRSession",
    "StudentFaceEncoding",
    "FacultyAttendance", "FacultyAttendanceStatus",
    "LeaveRequest", "LeaveType", "LeaveStatus",
    "Assignment", "AssignmentStatus", "Submission", "SubmissionStatus",
    "FeeStructure", "StudentFee", "FeePayment", "FeeStatus", "PaymentMode",
    "Announcement", "AnnouncementRead", "AnnouncementTarget",
    "AnnouncementPriority", "Notification", "NotificationType",
    "CertificateRequest", "CertificateType", "CertificateStatus",
    "AIRiskPrediction", "RiskLevel", "ChatSession", "ChatMessage",
    "Hostel", "HostelRoom", "HostelAllocation", "HostelType", "RoomType",
    "Outpass", "OutpassStatus", "HostelLeaveRequest", "HostelLeaveStatus", "VisitorLog",
]
