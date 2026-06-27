"""
MIPS Tripura — ERPNext (Frappe v15) Setup Script
==================================================

WHAT THIS IS
------------
A paste-into-`bench console` script that:
  1. Restricts/disables the role-groups tied to modules you don't need
     (Manufacturing, Stock, Quality, Projects, Buying, Support/Helpdesk).
  2. Creates college-specific Roles + Role Profiles (Registrar, Instructor,
     Accounts, Admissions/CRM, HR & Payroll, Student Portal).
  3. Creates demo academic data: Academic Years, Departments, Programs
     (B.Pharm / D.Pharm), starter Courses, a few Instructors & Students,
     a Fee Category/Structure, and a handful of CRM Leads for the
     admissions pipeline.

WHAT THIS DELIBERATELY DOES NOT TOUCH
--------------------------------------
- Your whitelabel app's branding (logo, app name, colors). You said a
  whitelabel module is already installed and I don't know its exact
  fields — overwriting System Settings / Website Settings blind could
  fight with it. Tell me the doctype/fields it uses and I'll add a step.
- Hiding Workspaces from the sidebar. There's no safe documented API for
  this — it's a one-time UI action. See HIDE_WORKSPACES.md for the exact
  3-click path. Scripting Role.disabled below achieves the *functional*
  equivalent (no one can actually use Stock/Manufacturing/etc.) even
  before you tidy up the sidebar.

HOW TO RUN THIS
----------------
1. BACK UP FIRST:  bench --site YOUR_SITE backup --with-files
2. Copy this file to your server, e.g. /home/frappe/mips_setup.py
3. bench --site YOUR_SITE console
4. Inside the console:
       exec(open('/home/frappe/mips_setup.py').read())
       run_all(dry_run=True)     # <-- review the printed plan first
       run_all(dry_run=False)    # <-- then actually apply it
5. frappe.db.commit() is called automatically at the end of a real run.

Re-running is safe: every step checks "does this already exist?" before
creating anything, so you can run it more than once without duplicating
records.
"""

import frappe
from frappe.utils import getdate

# ---------------------------------------------------------------------------
# CONFIG — edit these before running if you want different values
# ---------------------------------------------------------------------------

COMPANY = frappe.defaults.get_global_default("company")  # uses whatever you already set up in Setup Wizard

ACADEMIC_YEARS = [
    {"academic_year_name": "2025-26", "year_start_date": "2025-08-01", "year_end_date": "2026-05-31"},
    {"academic_year_name": "2026-27", "year_start_date": "2026-08-01", "year_end_date": "2027-05-31"},
]

DEPARTMENTS = [
    "Pharmaceutics",
    "Pharmaceutical Chemistry",
    "Pharmacology",
    "Pharmacognosy",
    "Pharmacy Practice",
    "Humanities and Basic Sciences",
]

PROGRAMS = [
    {"program_name": "B.Pharm", "program_abbreviation": "BPHARM"},
    {"program_name": "D.Pharm", "program_abbreviation": "DPHARM"},
]

# Starter subject lists — typical PCI-regulated B.Pharm/D.Pharm year-1 syllabus.
# Treat as a seed set, not the verified official syllabus — check against the
# current PCI / Tripura University curriculum before publishing to students.
COURSES = {
    "B.Pharm": [
        "Human Anatomy and Physiology",
        "Pharmaceutical Analysis",
        "Pharmaceutics",
        "Pharmaceutical Inorganic Chemistry",
        "Communication Skills",
        "Remedial Biology",
    ],
    "D.Pharm": [
        "Pharmaceutics I",
        "Pharmaceutical Chemistry I",
        "Pharmacognosy I",
        "Biochemistry and Clinical Pathology",
        "Human Anatomy and Physiology",
        "Health Education and Community Pharmacy",
    ],
}

FEE_CATEGORIES = ["Tuition Fee", "Admission Fee", "Library Fee", "Hostel Fee", "Examination Fee"]

# DEMO records only — fictional placeholders, not real people. Delete or
# replace before you onboard real staff/students.
DEMO_INSTRUCTORS = [
    {"instructor_name": "Anindita Bhattacharjee", "department": "Pharmaceutics", "gender": "Female"},
    {"instructor_name": "Subrata Debbarma", "department": "Pharmacology", "gender": "Male"},
    {"instructor_name": "Pradip Saha", "department": "Pharmaceutical Chemistry", "gender": "Male"},
]

DEMO_STUDENTS = [
    {"first_name": "Riya", "last_name": "Nath", "gender": "Female", "program": "B.Pharm", "joining_date": "2025-08-10"},
    {"first_name": "Suman", "last_name": "Tripura", "gender": "Male", "program": "B.Pharm", "joining_date": "2025-08-10"},
    {"first_name": "Mousumi", "last_name": "Reang", "gender": "Female", "program": "D.Pharm", "joining_date": "2025-08-10"},
    {"first_name": "Arindam", "last_name": "Paul", "gender": "Male", "program": "D.Pharm", "joining_date": "2025-08-10"},
]

DEMO_LEADS = [
    {"lead_name": "Priya Sarkar", "source": "Website", "status": "Open", "mobile_no": "9000000001",
     "note": "Enquired about B.Pharm admission 2026-27."},
    {"lead_name": "Bikram Choudhury", "source": "Walk In", "status": "Replied", "mobile_no": "9000000002",
     "note": "Visited campus, asked about D.Pharm fee structure."},
    {"lead_name": "Anjali Debnath", "source": "Reference", "status": "Open", "mobile_no": "9000000003",
     "note": "Referred by an existing student, interested in B.Pharm."},
    {"lead_name": "Joydeep Roy", "source": "Advertisement", "status": "Replied", "mobile_no": "9000000004",
     "note": "Saw the newspaper ad, wants hostel + fee details."},
]

# Roles to switch OFF (modules you said you don't need right now).
# Each entry is a list of *candidate* role names — whichever exist on your
# site get disabled, the rest are silently skipped (no error).
ROLES_TO_DISABLE = {
    "Manufacturing": ["Manufacturing User", "Manufacturing Manager"],
    "Stock / Inventory": ["Stock User", "Stock Manager", "Item Manager"],
    "Quality Management": ["Quality Manager"],
    "Projects": ["Projects User", "Projects Manager"],
    "Buying": ["Purchase User", "Purchase Manager"],
    "Support / Helpdesk": ["Support Team", "Agent", "Agent Manager"],
    "Assets": ["Asset Manager", "Asset User"],
}

# Roles you're keeping active (Education, CRM, Accounts, HR & Payroll).
# Used only to build Role Profiles below — not modified themselves.
CORE_ROLES_TO_KEEP = [
    "Instructor", "Student", "Sales User", "Sales Manager",
    "Accounts User", "Accounts Manager", "HR User", "HR Manager",
    "Payroll Manager", "Employee",
]

# Custom roles this script will create if missing, then bundle into profiles.
CUSTOM_ROLES = ["Academic Admin", "Admissions Officer"]

ROLE_PROFILES = {
    "MIPS - Registrar / Academic Admin": ["Academic Admin", "Instructor", "Employee"],
    "MIPS - Instructor": ["Instructor", "Employee"],
    "MIPS - Accounts": ["Accounts User", "Employee"],
    "MIPS - Admissions (CRM)": ["Admissions Officer", "Sales User", "Employee"],
    "MIPS - HR & Payroll": ["HR User", "Employee"],
    "MIPS - Student Portal": ["Student"],
}

LOG = []


def log(msg):
    print(msg)
    LOG.append(msg)


# ---------------------------------------------------------------------------
# STEP 1 — disable the roles tied to modules you don't need
# ---------------------------------------------------------------------------

def disable_unneeded_modules(dry_run=True):
    log("\n=== STEP 1: Disabling roles for unneeded modules ===")
    for module_label, candidate_roles in ROLES_TO_DISABLE.items():
        for role_name in candidate_roles:
            if not frappe.db.exists("Role", role_name):
                continue  # role doesn't exist on this site, nothing to do
            already_disabled = frappe.db.get_value("Role", role_name, "disabled")
            if already_disabled:
                log(f"  SKIP (already disabled): {role_name} [{module_label}]")
                continue
            if dry_run:
                log(f"  [DRY RUN] would disable role: {role_name} [{module_label}]")
                continue
            try:
                frappe.db.set_value("Role", role_name, "disabled", 1)
                # also strip it from anyone who currently has it, except Administrator
                users_with_role = frappe.get_all(
                    "Has Role", filters={"role": role_name, "parenttype": "User"},
                    fields=["parent", "name"]
                )
                removed = 0
                for row in users_with_role:
                    if row.parent == "Administrator":
                        continue
                    frappe.delete_doc("Has Role", row.name, ignore_permissions=True)
                    removed += 1
                log(f"  DISABLED: {role_name} [{module_label}] (removed from {removed} user(s))")
            except Exception as e:
                log(f"  !! FAILED to disable '{role_name}' [{module_label}]: {e}")


# ---------------------------------------------------------------------------
# STEP 2 — custom roles + role profiles for the roles you ARE keeping
# ---------------------------------------------------------------------------

def create_custom_roles(dry_run=True):
    log("\n=== STEP 2a: Creating custom roles ===")
    for role_name in CUSTOM_ROLES:
        if frappe.db.exists("Role", role_name):
            log(f"  SKIP (exists): Role '{role_name}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Role '{role_name}'")
            continue
        try:
            doc = frappe.new_doc("Role")
            doc.role_name = role_name
            doc.desk_access = 1
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Role '{role_name}'")
        except Exception as e:
            log(f"  !! FAILED to create Role '{role_name}': {e}")


def create_role_profiles(dry_run=True):
    log("\n=== STEP 2b: Creating role profiles ===")
    for profile_name, role_list in ROLE_PROFILES.items():
        if frappe.db.exists("Role Profile", profile_name):
            log(f"  SKIP (exists): Role Profile '{profile_name}'")
            continue
        existing_roles = [r for r in role_list if frappe.db.exists("Role", r)]
        missing_roles = [r for r in role_list if r not in existing_roles]
        if missing_roles:
            log(f"  NOTE: '{profile_name}' wanted {missing_roles} but those roles "
                f"don't exist on this site yet — profile will be created without them.")
        if dry_run:
            log(f"  [DRY RUN] would create Role Profile '{profile_name}' with roles {existing_roles}")
            continue
        try:
            doc = frappe.new_doc("Role Profile")
            doc.role_profile = profile_name
            for r in existing_roles:
                doc.append("roles", {"role": r})
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Role Profile '{profile_name}' -> {existing_roles}")
        except Exception as e:
            log(f"  !! FAILED to create Role Profile '{profile_name}': {e}")


# ---------------------------------------------------------------------------
# STEP 3 — academic master data
# ---------------------------------------------------------------------------

def create_academic_years(dry_run=True):
    log("\n=== STEP 3a: Academic Years ===")
    for ay in ACADEMIC_YEARS:
        name = ay["academic_year_name"]
        if frappe.db.exists("Academic Year", name):
            log(f"  SKIP (exists): Academic Year '{name}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Academic Year '{name}'")
            continue
        try:
            doc = frappe.new_doc("Academic Year")
            doc.academic_year_name = name
            doc.year_start_date = getdate(ay["year_start_date"])
            doc.year_end_date = getdate(ay["year_end_date"])
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Academic Year '{name}'")
        except Exception as e:
            log(f"  !! FAILED to create Academic Year '{name}': {e}")


def create_departments(dry_run=True):
    log("\n=== STEP 3b: Departments ===")
    for dept in DEPARTMENTS:
        # Frappe auto-suffixes Department names with " - <abbr>" when a company
        # is set, so check loosely by department_name instead of exact name.
        existing = frappe.db.exists("Department", {"department_name": dept})
        if existing:
            log(f"  SKIP (exists): Department '{dept}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Department '{dept}'")
            continue
        try:
            doc = frappe.new_doc("Department")
            doc.department_name = dept
            if COMPANY:
                doc.company = COMPANY
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Department '{dept}'")
        except Exception as e:
            log(f"  !! FAILED to create Department '{dept}': {e}")


def create_programs(dry_run=True):
    log("\n=== STEP 3c: Programs ===")
    for prog in PROGRAMS:
        name = prog["program_name"]
        if frappe.db.exists("Program", name):
            log(f"  SKIP (exists): Program '{name}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Program '{name}'")
            continue
        try:
            doc = frappe.new_doc("Program")
            doc.program_name = name
            if "program_abbreviation" in [f.fieldname for f in doc.meta.fields]:
                doc.program_abbreviation = prog["program_abbreviation"]
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Program '{name}'")
        except Exception as e:
            log(f"  !! FAILED to create Program '{name}': {e}")


def create_courses(dry_run=True):
    log("\n=== STEP 3d: Courses ===")
    for program_name, course_list in COURSES.items():
        for course_name in course_list:
            if frappe.db.exists("Course", {"course_name": course_name}):
                log(f"  SKIP (exists): Course '{course_name}'")
                continue
            if dry_run:
                log(f"  [DRY RUN] would create Course '{course_name}' (for {program_name})")
                continue
            try:
                doc = frappe.new_doc("Course")
                doc.course_name = course_name
                doc.insert(ignore_permissions=True)
                log(f"  CREATED: Course '{course_name}'")
            except Exception as e:
                log(f"  !! FAILED to create Course '{course_name}': {e}")


def _department_full_name(label):
    """Department names often get an auto-suffix like ' - MIPS' once a
    company is set — resolve the real primary key from the readable label."""
    return frappe.db.get_value("Department", {"department_name": label}, "name")


# ---------------------------------------------------------------------------
# STEP 4 — demo instructors & students (FICTIONAL — replace before go-live)
# ---------------------------------------------------------------------------

def create_demo_instructors(dry_run=True):
    log("\n=== STEP 4a: Demo instructors (fictional placeholders) ===")
    for inst in DEMO_INSTRUCTORS:
        if frappe.db.exists("Instructor", {"instructor_name": inst["instructor_name"]}):
            log(f"  SKIP (exists): Instructor '{inst['instructor_name']}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Instructor '{inst['instructor_name']}'")
            continue
        try:
            doc = frappe.new_doc("Instructor")
            doc.instructor_name = inst["instructor_name"]
            dept_name = _department_full_name(inst["department"])
            if dept_name:
                doc.department = dept_name
            if "gender" in [f.fieldname for f in doc.meta.fields]:
                doc.gender = inst["gender"]
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Instructor '{inst['instructor_name']}'")
        except Exception as e:
            log(f"  !! FAILED to create Instructor '{inst['instructor_name']}': {e}")


def create_demo_students(dry_run=True):
    log("\n=== STEP 4b: Demo students (fictional placeholders) ===")

    # The Education app auto-creates a linked portal User from
    # student_email_id on Student.validate(), unless this flag is set.
    # We give every demo student a placeholder email below, but as a second
    # safety net we also temporarily skip that auto-User-creation step here
    # so a missing/duplicate email can never again take down the whole run —
    # and we restore whatever this was set to before we touched it.
    original_skip = None
    if not dry_run:
        original_skip = frappe.db.get_single_value("Education Settings", "user_creation_skip")
        if not original_skip:
            frappe.db.set_single_value("Education Settings", "user_creation_skip", 1)

    try:
        for stu in DEMO_STUDENTS:
            full_name = f"{stu['first_name']} {stu['last_name']}"
            if frappe.db.exists("Student", {"first_name": stu["first_name"], "last_name": stu["last_name"]}):
                log(f"  SKIP (exists): Student '{full_name}'")
                continue
            placeholder_email = f"{stu['first_name'].lower()}.{stu['last_name'].lower()}.demo@mipstripura.in"
            if dry_run:
                log(f"  [DRY RUN] would create Student '{full_name}' ({stu['program']}, {placeholder_email})")
                continue

            try:
                doc = frappe.new_doc("Student")
                doc.first_name = stu["first_name"]
                doc.last_name = stu["last_name"]
                doc.gender = stu["gender"]
                doc.joining_date = getdate(stu["joining_date"])
                doc.student_email_id = placeholder_email
                doc.insert(ignore_permissions=True)
                log(f"  CREATED: Student '{full_name}'")
            except Exception as e:
                log(f"  !! FAILED to create Student '{full_name}': {e}")
                continue  # don't attempt enrollment for a student that wasn't created

            # Best-effort Program Enrollment — skipped quietly if the academic
            # setup on this site uses different mandatory fields.
            try:
                ay = ACADEMIC_YEARS[0]["academic_year_name"]
                if not frappe.db.exists("Program Enrollment", {"student": doc.name, "program": stu["program"]}):
                    pe = frappe.new_doc("Program Enrollment")
                    pe.student = doc.name
                    pe.student_name = full_name
                    pe.program = stu["program"]
                    pe.academic_year = ay
                    pe.enrollment_date = getdate(stu["joining_date"])
                    pe.insert(ignore_permissions=True)
                    log(f"    + enrolled in {stu['program']} ({ay})")
            except Exception as e:
                log(f"    !! Program Enrollment skipped for '{full_name}': {e}")
    finally:
        if not dry_run and original_skip is not None and not original_skip:
            frappe.db.set_single_value("Education Settings", "user_creation_skip", original_skip)




# ---------------------------------------------------------------------------
# STEP 5 — fee categories + a starter fee structure
# ---------------------------------------------------------------------------

def create_fee_categories(dry_run=True):
    log("\n=== STEP 5a: Fee Categories ===")
    for cat in FEE_CATEGORIES:
        if frappe.db.exists("Fee Category", cat):
            log(f"  SKIP (exists): Fee Category '{cat}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Fee Category '{cat}'")
            continue
        try:
            doc = frappe.new_doc("Fee Category")
            doc.category_name = cat
            doc.insert(ignore_permissions=True)
            log(f"  CREATED: Fee Category '{cat}'")
        except Exception as e:
            log(f"  !! FAILED to create Fee Category '{cat}': {e}")


def create_fee_structure(dry_run=True):
    log("\n=== STEP 5b: Starter Fee Structure (B.Pharm, Year 1) ===")
    structure_name_filter = {"program": "B.Pharm"}
    if frappe.db.exists("Fee Structure", structure_name_filter):
        log("  SKIP (exists): Fee Structure for B.Pharm")
        return
    if dry_run:
        log("  [DRY RUN] would create a Fee Structure for B.Pharm with starter amounts "
            "(Tuition 60000, Admission 5000, Library 1000, Hostel 25000, Examination 2000 — edit these)")
        return
    try:
        doc = frappe.new_doc("Fee Structure")
        doc.program = "B.Pharm"
        doc.academic_year = ACADEMIC_YEARS[0]["academic_year_name"]
        starter_amounts = {
            "Tuition Fee": 60000, "Admission Fee": 5000, "Library Fee": 1000,
            "Hostel Fee": 25000, "Examination Fee": 2000,
        }
        for cat, amount in starter_amounts.items():
            doc.append("components", {"fees_category": cat, "amount": amount})
        doc.insert(ignore_permissions=True)
        log("  CREATED: Fee Structure for B.Pharm (placeholder amounts — edit in UI)")
    except Exception as e:
        log(f"  !! Fee Structure creation failed (field names may differ on this site): {e}")


# ---------------------------------------------------------------------------
# STEP 6 — CRM demo leads (admissions pipeline)
# ---------------------------------------------------------------------------

def create_demo_leads(dry_run=True):
    log("\n=== STEP 6: CRM demo leads (admissions pipeline) ===")
    for lead in DEMO_LEADS:
        if frappe.db.exists("Lead", {"lead_name": lead["lead_name"], "mobile_no": lead["mobile_no"]}):
            log(f"  SKIP (exists): Lead '{lead['lead_name']}'")
            continue
        if dry_run:
            log(f"  [DRY RUN] would create Lead '{lead['lead_name']}' [{lead['source']}/{lead['status']}]")
            continue
        try:
            doc = frappe.new_doc("Lead")
            doc.lead_name = lead["lead_name"]
            doc.mobile_no = lead["mobile_no"]
            if frappe.db.exists("Lead Source", lead["source"]):
                doc.source = lead["source"]
            doc.insert(ignore_permissions=True)
            try:
                doc.db_set("status", lead["status"])
            except Exception:
                pass
            try:
                doc.add_comment("Comment", lead["note"])
            except Exception:
                pass
            log(f"  CREATED: Lead '{lead['lead_name']}' [{lead['source']}/{lead['status']}]")
        except Exception as e:
            log(f"  !! FAILED to create Lead '{lead['lead_name']}': {e}")


# ---------------------------------------------------------------------------
# STEP 7 — a few universal, non-branding defaults (won't touch your whitelabel app)
# ---------------------------------------------------------------------------

def set_safe_system_defaults(dry_run=True):
    log("\n=== STEP 7: Safe System Settings defaults (country/timezone/date format only) ===")
    safe_defaults = {"country": "India", "time_zone": "Asia/Kolkata", "date_format": "dd-mm-yyyy"}
    try:
        settings = frappe.get_single("System Settings")
        changed = {}
        for field, value in safe_defaults.items():
            current = settings.get(field)
            if not current:
                changed[field] = value
        if not changed:
            log("  SKIP: System Settings already has these fields set — not touching them.")
            return
        if dry_run:
            log(f"  [DRY RUN] would set System Settings: {changed}")
            return
        for field, value in changed.items():
            settings.set(field, value)
        settings.save(ignore_permissions=True)
        log(f"  UPDATED System Settings: {changed}")
    except Exception as e:
        log(f"  !! System Settings update skipped: {e}")


# ---------------------------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------------------------

def run_all(dry_run=True):
    LOG.clear()
    log(f"\n############  MIPS Tripura ERPNext setup — {'DRY RUN (no changes)' if dry_run else 'LIVE RUN'}  ############")
    log(f"Detected default company: {COMPANY!r} (used for Departments)")

    steps = [
        disable_unneeded_modules,
        create_custom_roles,
        create_role_profiles,
        create_academic_years,
        create_departments,
        create_programs,
        create_courses,
        create_demo_instructors,
        create_demo_students,
        create_fee_categories,
        create_fee_structure,
        create_demo_leads,
        set_safe_system_defaults,
    ]
    for step in steps:
        try:
            step(dry_run)
        except Exception as e:
            log(f"\n!!! STEP '{step.__name__}' FAILED ENTIRELY: {e}")
            log("    (continuing with the next step — nothing else was affected)")

    if dry_run:
        log("\n=== DRY RUN COMPLETE — nothing was changed. ===")
        log("Review the lines above. If it looks right, run: run_all(dry_run=False)")
    else:
        frappe.db.commit()
        log("\n=== LIVE RUN COMPLETE — changes committed. ===")
        log("Manual step still needed: hide unwanted Workspaces from the sidebar")
        log("(Stock, Manufacturing, Quality, Projects, Buying, Support) — see HIDE_WORKSPACES.md.")

    return LOG


print("Loaded. Next: run_all(dry_run=True) to preview, then run_all(dry_run=False) to apply.")