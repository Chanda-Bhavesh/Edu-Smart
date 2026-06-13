"""
Seed script - creates demo users for all roles.
Run from the backend/ directory:
  python seed.py
"""
import asyncio
import uuid
from datetime import date

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.semester import Semester
from app.models.faculty import Faculty, Designation
from app.models.student import Student, StudentStatus
from app.models.hostel import Hostel, HostelRoom, HostelAllocation, HostelType, RoomType
from app.utils.security import hash_password

PASSWORD = "Admin@123"

DEPT_ID   = uuid.uuid4()
SEM_ID    = uuid.uuid4()


async def seed():
    async with AsyncSessionLocal() as db:
        # ── 1. Department ─────────────────────────────────────────────────────
        existing_dept = await db.execute(select(Department).where(Department.code == "CSE"))
        dept = existing_dept.scalar_one_or_none()
        if not dept:
            dept = Department(
                id=DEPT_ID,
                name="Computer Science & Engineering",
                code="CSE",
                description="Undergraduate CS department",
            )
            db.add(dept)
            await db.flush()
            print(f"  Created department: CSE (id={dept.id})")
        else:
            print(f"  Department CSE already exists (id={dept.id})")

        # ── 2. Semester ───────────────────────────────────────────────────────
        existing_sem = await db.execute(
            select(Semester).where(
                Semester.department_id == dept.id,
                Semester.number == 1,
                Semester.academic_year == "2024-2025",
            )
        )
        sem = existing_sem.scalar_one_or_none()
        if not sem:
            sem = Semester(
                id=SEM_ID,
                number=1,
                academic_year="2024-2025",
                department_id=dept.id,
            )
            db.add(sem)
            await db.flush()
            print(f"  Created semester: Sem 1 (id={sem.id})")
        else:
            print(f"  Semester already exists (id={sem.id})")

        # ── Helper: upsert user ───────────────────────────────────────────────
        async def upsert_user(email, full_name, role) -> User:
            res = await db.execute(select(User).where(User.email == email))
            u = res.scalar_one_or_none()
            if u:
                print(f"  User already exists: {email}")
                return u
            u = User(
                email=email,
                hashed_password=hash_password(PASSWORD),
                full_name=full_name,
                role=role,
                is_verified=True,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            print(f"  Created user: {email}  role={role.value}")
            return u

        # ── 3. Org Admin ──────────────────────────────────────────────────────
        await upsert_user("orgadmin@scms.edu", "Org Admin", UserRole.org_admin)

        # ── 4. Dept Admin ─────────────────────────────────────────────────────
        dept_admin_user = await upsert_user("deptadmin@scms.edu", "Dept Admin (CSE)", UserRole.dept_admin)

        # dept_admin also needs a Faculty row to be associated with the department
        res = await db.execute(select(Faculty).where(Faculty.user_id == dept_admin_user.id))
        if not res.scalar_one_or_none():
            db.add(Faculty(
                user_id=dept_admin_user.id,
                employee_id="EMP001",
                department_id=dept.id,
                designation=Designation.professor,
            ))
            await db.flush()
            print("  Created faculty row for dept admin")

        # ── 5. Faculty ────────────────────────────────────────────────────────
        faculty_user = await upsert_user("faculty@scms.edu", "Prof. Arjun Sharma", UserRole.faculty)
        res = await db.execute(select(Faculty).where(Faculty.user_id == faculty_user.id))
        if not res.scalar_one_or_none():
            db.add(Faculty(
                user_id=faculty_user.id,
                employee_id="EMP002",
                department_id=dept.id,
                designation=Designation.assistant_professor,
            ))
            await db.flush()
            print("  Created faculty row for faculty user")

        # ── 6. Student ────────────────────────────────────────────────────────
        student_user = await upsert_user("student@scms.edu", "Riya Patel", UserRole.student)
        res = await db.execute(select(Student).where(Student.user_id == student_user.id))
        if not res.scalar_one_or_none():
            db.add(Student(
                user_id=student_user.id,
                roll_number="CSE2024001",
                department_id=dept.id,
                semester_id=sem.id,
                section="A",
                status=StudentStatus.active,
            ))
            await db.flush()
            print("  Created student row")

        # ── 7. Warden ─────────────────────────────────────────────────────────
        warden_user = await upsert_user("warden@scms.edu", "Mr. Ramesh Kumar", UserRole.warden)

        # ── 8. Hostel ─────────────────────────────────────────────────────────
        existing_hostel = await db.execute(select(Hostel).where(Hostel.name == "Block A - Boys Hostel"))
        hostel = existing_hostel.scalar_one_or_none()
        if not hostel:
            hostel = Hostel(
                name="Block A - Boys Hostel",
                hostel_type=HostelType.boys,
                warden_id=warden_user.id,
                address="Campus North Wing, Block A",
                phone="9876543210",
                total_capacity=100,
            )
            db.add(hostel)
            await db.flush()
            print(f"  Created hostel: Block A (id={hostel.id})")
        else:
            print(f"  Hostel already exists (id={hostel.id})")
            # Ensure warden is assigned
            if hostel.warden_id != warden_user.id:
                hostel.warden_id = warden_user.id
                await db.flush()

        # ── 9. Room ───────────────────────────────────────────────────────────
        existing_room = await db.execute(
            select(HostelRoom).where(HostelRoom.hostel_id == hostel.id, HostelRoom.room_number == "A101")
        )
        room = existing_room.scalar_one_or_none()
        if not room:
            room = HostelRoom(
                hostel_id=hostel.id,
                room_number="A101",
                floor=1,
                room_type=RoomType.double,
                capacity=2,
            )
            db.add(room)
            await db.flush()
            print(f"  Created room: A101 (id={room.id})")
        else:
            print(f"  Room A101 already exists (id={room.id})")

        # ── 10. Student Allocation ────────────────────────────────────────────
        res = await db.execute(select(Student).where(Student.user_id == student_user.id))
        student = res.scalar_one_or_none()
        if student:
            existing_alloc = await db.execute(
                select(HostelAllocation).where(
                    HostelAllocation.student_id == student.id,
                    HostelAllocation.is_active == True,
                )
            )
            if not existing_alloc.scalar_one_or_none():
                alloc = HostelAllocation(
                    student_id=student.id,
                    room_id=room.id,
                    allocated_date=date.today(),
                    is_active=True,
                    allocated_by=warden_user.id,
                )
                db.add(alloc)
                await db.flush()
                print(f"  Allocated student to room A101")
            else:
                print(f"  Student already has active allocation")

        await db.commit()

    print("\nSeed complete. Login credentials:")
    print(f"  Org Admin   -> orgadmin@scms.edu   / {PASSWORD}")
    print(f"  Dept Admin  -> deptadmin@scms.edu  / {PASSWORD}")
    print(f"  Faculty     -> faculty@scms.edu    / {PASSWORD}")
    print(f"  Student     -> student@scms.edu    / {PASSWORD}")
    print(f"  Warden      -> warden@scms.edu     / {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
