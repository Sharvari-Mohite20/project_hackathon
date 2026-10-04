import os
import random
from datetime import datetime, timedelta, date
from models import db, User, CampusLocation, Item, Claim, Message, Notification, AuditLog

def seed_database(app):
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # If locations already exist, skip seeding
        if CampusLocation.query.first():
            print("Database already seeded.")
            return

        print("Seeding database with campus locations, users, and realistic items...")

        # 1. Seed Campus Locations
        locations_data = [
            {
                "name": "Central Library (Reading Halls & Digital Lab)",
                "code": "LIB-MAIN",
                "zone": "Academic",
                "description": "3-story modern library including quiet study areas, reference section, and ground floor circulation desk.",
                "icon": "book-open",
                "map_x": 35.0,
                "map_y": 30.0
            },
            {
                "name": "Campus Cafeteria & Food Court",
                "code": "CAFE-CENTRAL",
                "zone": "Recreational",
                "description": "Main food court, juice counter, outdoor seating patio, and student common hall.",
                "icon": "coffee",
                "map_x": 60.0,
                "map_y": 55.0
            },
            {
                "name": "Turing CS & IT Computer Labs (Block C)",
                "code": "CS-LAB",
                "zone": "Academic",
                "description": "High-performance computing labs, project incubators, and server rooms on Block C 2nd floor.",
                "icon": "monitor",
                "map_x": 25.0,
                "map_y": 65.0
            },
            {
                "name": "APJ Abdul Kalam Main Auditorium",
                "code": "AUD-MAIN",
                "zone": "Recreational",
                "description": "1500-seat multi-purpose hall for campus convocations, tech symposiums, and cultural events.",
                "icon": "award",
                "map_x": 75.0,
                "map_y": 40.0
            },
            {
                "name": "University Sports Arena & Gymnasium",
                "code": "SPORT-GYM",
                "zone": "Recreational",
                "description": "Indoor badminton court, basketball arena, gym, and locker changing rooms.",
                "icon": "activity",
                "map_x": 80.0,
                "map_y": 75.0
            },
            {
                "name": "Aryabhatta Hostel Block A (Boys)",
                "code": "HOSTEL-A",
                "zone": "Residential",
                "description": "Undergraduate residence block, common room, laundry area, and mess hall.",
                "icon": "home",
                "map_x": 20.0,
                "map_y": 20.0
            },
            {
                "name": "Gargi Hostel Block B (Girls)",
                "code": "HOSTEL-B",
                "zone": "Residential",
                "description": "Undergraduate women residence hall with 24/7 security reception and study courtyard.",
                "icon": "home",
                "map_x": 85.0,
                "map_y": 20.0
            },
            {
                "name": "Central Security Desk & Admin Office",
                "code": "ADMIN-SEC",
                "zone": "Administrative",
                "description": "Central Campus Security headquarters, lost-and-found repository lockers, and Dean of Students office.",
                "icon": "shield",
                "map_x": 50.0,
                "map_y": 45.0
            },
            {
                "name": "Lecture Hall Complex (Rooms 101-305)",
                "code": "LHC-HALL",
                "zone": "Academic",
                "description": "Multi-tier lecture classrooms, presentation podiums, and faculty rooms.",
                "icon": "layers",
                "map_x": 45.0,
                "map_y": 70.0
            },
            {
                "name": "Student Parking Lot (Zone East)",
                "code": "PARK-EAST",
                "zone": "Other",
                "description": "Two-wheeler and four-wheeler parking shelters near East Entry Gate 2.",
                "icon": "compass",
                "map_x": 15.0,
                "map_y": 80.0
            }
        ]

        created_locations = {}
        for loc in locations_data:
            c_loc = CampusLocation(**loc)
            db.session.add(c_loc)
            created_locations[loc['code']] = c_loc

        # 2. Seed Users
        # Admin User
        admin_user = User(
            name="Officer Rajesh Kumar",
            email="admin@apexuni.edu",
            role="admin",
            student_id="EMP-SEC-042",
            department="Campus Security & Safety",
            phone="+91 98765 43210"
        )
        admin_user.set_password("admin123")
        db.session.add(admin_user)

        # Student 1: Aarav Sharma
        student_1 = User(
            name="Aarav Sharma",
            email="aarav.sharma@apexuni.edu",
            role="student",
            student_id="2023CS104",
            department="Computer Science & Engineering",
            phone="+91 98111 22334"
        )
        student_1.set_password("student123")
        db.session.add(student_1)

        # Student 2: Priya Patel
        student_2 = User(
            name="Priya Patel",
            email="priya.patel@apexuni.edu",
            role="student",
            student_id="2024EC058",
            department="Electronics & Communication",
            phone="+91 98222 33445"
        )
        student_2.set_password("student123")
        db.session.add(student_2)

        # Student 3: Rohit Verma
        student_3 = User(
            name="Rohit Verma",
            email="rohit.verma@apexuni.edu",
            role="student",
            student_id="2023ME089",
            department="Mechanical Engineering",
            phone="+91 98333 44556"
        )
        student_3.set_password("student123")
        db.session.add(student_3)

        # Staff 1: Prof. Mehta
        staff_1 = User(
            name="Prof. Anand Mehta",
            email="prof.mehta@apexuni.edu",
            role="staff",
            student_id="FAC-PHY-12",
            department="Department of Applied Physics",
            phone="+91 98444 55667"
        )
        staff_1.set_password("faculty123")
        db.session.add(staff_1)

        db.session.flush()

        today = date.today()

        # 3. Seed Realistic Items
        items_data = [
            {
                "item_type": "lost",
                "title": "Apple AirPods Pro 2 (in Navy Blue Spigen Case)",
                "category": "Electronics",
                "description": "White Apple AirPods Pro (2nd Generation) kept inside a navy blue silicone protective armor case. Left earbud has a tiny cosmetic scuff on the stem. Contains high emotional and study value.",
                "location_id": created_locations["LIB-MAIN"].id,
                "specific_location": "2nd Floor Silent Reading Room, Table 18 near south window",
                "date_lost_or_found": today - timedelta(days=2),
                "status": "pending_claim",
                "is_urgent": True,
                "reward_amount": 500.0,
                "contact_preference": "in_app",
                "user_id": student_1.id
            },
            {
                "item_type": "found",
                "title": "Apple AirPods Pro (White) with Navy Blue Case",
                "category": "Electronics",
                "description": "Pair of wireless Apple AirPods Pro in good working condition. Found in a dark navy blue rugged silicone case with a small metal ring attachment.",
                "location_id": created_locations["LIB-MAIN"].id,
                "specific_location": "Library 2nd Floor, beneath study cubicle #18",
                "date_lost_or_found": today - timedelta(days=1),
                "status": "pending_claim",
                "is_urgent": False,
                "secret_verification_question": "What brand engraving is on the side of the blue case, and what color is the ring attachment?",
                "safe_custody_info": "Deposited at Central Security Desk repository locker",
                "storage_locker_number": "SEC-LOCKER-12",
                "contact_preference": "in_app",
                "user_id": student_2.id
            },
            {
                "item_type": "lost",
                "title": "Apex University Smart ID Card & Metro Pass",
                "category": "ID & Cards",
                "description": "Blue RFID university smart student card along with a Delhi/State Metro smart card inside a clear plastic sleeve with university logo lanyard.",
                "location_id": created_locations["CAFE-CENTRAL"].id,
                "specific_location": "Canteen billing counter near fresh juice stall",
                "date_lost_or_found": today - timedelta(days=3),
                "status": "active",
                "is_urgent": True,
                "reward_amount": 200.0,
                "contact_preference": "in_app",
                "user_id": student_3.id
            },
            {
                "item_type": "found",
                "title": "Student Identity Card (Mechanical Dept)",
                "category": "ID & Cards",
                "description": "Official college student ID card found hanging on the back of a cafeteria bench. Belongs to a 3rd year Mechanical Engineering student.",
                "location_id": created_locations["CAFE-CENTRAL"].id,
                "specific_location": "Cafeteria booth near back terrace",
                "date_lost_or_found": today - timedelta(days=2),
                "status": "active",
                "is_urgent": False,
                "secret_verification_question": "Please verify your exact student roll number and date of birth printed on the card.",
                "safe_custody_info": "Kept safely with cafeteria supervisor / front cash register",
                "storage_locker_number": "CAFE-CUSTODY-01",
                "contact_preference": "in_app",
                "user_id": student_2.id
            },
            {
                "item_type": "found",
                "title": "Casio Scientific Calculator fx-991CW (Black)",
                "category": "Electronics",
                "description": "Standard engineering advanced scientific calculator with slide-on protective cover. Found after an afternoon tutorial session.",
                "location_id": created_locations["LHC-HALL"].id,
                "specific_location": "Room 204, Lecture Hall Complex, 3rd row desk",
                "date_lost_or_found": today - timedelta(days=3),
                "status": "active",
                "is_urgent": False,
                "secret_verification_question": "What is written or stickered on the inside of the slide-on plastic lid?",
                "safe_custody_info": "With Prof. Mehta in Physics Department Faculty Office (Room 312)",
                "storage_locker_number": "DEPT-PHY-312",
                "contact_preference": "in_app",
                "user_id": staff_1.id
            },
            {
                "item_type": "found",
                "title": "Bunch of Keys with Red Spider-Man Keychain",
                "category": "Keys & Locks",
                "description": "Set of 3 keys (one motorcycle key with Honda emblem and two small Yale door keys) on a soft rubber Marvel Spider-Man keychain.",
                "location_id": created_locations["HOSTEL-A"].id,
                "specific_location": "Hostel Block A main staircase landing between ground & 1st floor",
                "date_lost_or_found": today,
                "status": "active",
                "is_urgent": False,
                "secret_verification_question": "What color is the bike key handle and what letters are stamped on the brass door key?",
                "safe_custody_info": "Handed to Hostel A Warden / Security Guard Post",
                "storage_locker_number": "HA-GUARD-04",
                "contact_preference": "in_app",
                "user_id": student_2.id
            },
            {
                "item_type": "lost",
                "title": "Wildhorn Brown Leather Bi-fold Wallet",
                "category": "Bags & Wallets",
                "description": "Genuine brown leather bi-fold wallet containing state driving license, debit cards, hostel gate pass, and approximately 800 cash.",
                "location_id": created_locations["PARK-EAST"].id,
                "specific_location": "East parking lot near bike shelter #4",
                "date_lost_or_found": today - timedelta(days=1),
                "status": "active",
                "is_urgent": True,
                "reward_amount": 1000.0,
                "contact_preference": "phone",
                "user_id": student_3.id
            },
            {
                "item_type": "lost",
                "title": "Titan Neo Silver Wristwatch with Black Dial",
                "category": "Clothing & Wearables",
                "description": "Men's analog watch with stainless steel mesh band, minimalist black dial, and mineral glass face. Left in changing area.",
                "location_id": created_locations["SPORT-GYM"].id,
                "specific_location": "Sports Arena locker room bench #7",
                "date_lost_or_found": today - timedelta(days=4),
                "status": "active",
                "is_urgent": False,
                "reward_amount": 300.0,
                "contact_preference": "in_app",
                "user_id": student_1.id
            },
            {
                "item_type": "found",
                "title": "Milton Stainless Steel Water Bottle (Matte Blue, 1L)",
                "category": "Bottles & Containers",
                "description": "Insulated blue thermosteel water bottle with screw cap. In pristine condition with a small sticker of Linux Penguin.",
                "location_id": created_locations["CS-LAB"].id,
                "specific_location": "Computer Lab 3 (Turing Lab) Workstation 22",
                "date_lost_or_found": today - timedelta(days=2),
                "status": "active",
                "is_urgent": False,
                "secret_verification_question": "What sticker is near the base of the bottle?",
                "safe_custody_info": "Lab Assistant desk, CS Lab 3",
                "storage_locker_number": "CS-LAB-BOX",
                "contact_preference": "in_app",
                "user_id": student_1.id
            },
            {
                "item_type": "lost",
                "title": "Engineering Mathematics-III Textbook & Spiral Notebook",
                "category": "Books & Stationery",
                "description": "B.S. Grewal Higher Engineering Mathematics (44th Edition) with yellow bookmarks and a spiral notebook with handwritten transform calculus notes.",
                "location_id": created_locations["LIB-MAIN"].id,
                "specific_location": "1st Floor Reference Hall, Desk B",
                "date_lost_or_found": today - timedelta(days=5),
                "status": "resolved",
                "resolved_at": datetime.utcnow() - timedelta(days=1),
                "is_urgent": False,
                "reward_amount": 0.0,
                "contact_preference": "in_app",
                "user_id": student_2.id
            }
        ]

        created_items = []
        for it_data in items_data:
            item = Item(**it_data)
            db.session.add(item)
            created_items.append(item)

        db.session.flush()

        # 4. Seed an Active Claim & Handover PIN on the AirPods (Item index 1 = Found AirPods)
        found_airpods = created_items[1]
        claim_airpods = Claim(
            item_id=found_airpods.id,
            claimant_id=student_1.id,  # Aarav claiming it
            claim_description="Hi! I lost my exact AirPods Pro 2 in the Library 2nd floor on the same day. I have the original Apple bill and serial number matching on my iPhone.",
            answer_to_secret_question="The case has 'Spigen Tough Armor' engraved on the right edge, and the metal clip is gunmetal grey matte finish.",
            status="approved",
            handover_pin="749201",
            created_at=datetime.utcnow() - timedelta(hours=14),
            reviewed_at=datetime.utcnow() - timedelta(hours=2),
            reviewed_by_id=admin_user.id
        )
        db.session.add(claim_airpods)
        db.session.flush()

        # Seed in-app chat messages for this claim
        msg1 = Message(
            claim_id=claim_airpods.id,
            sender_id=student_1.id,
            content="Hello Officer / Finder, I have filed this claim with proof. I can show the AirPods connecting to my iCloud account live.",
            sent_at=datetime.utcnow() - timedelta(hours=12),
            is_read=True
        )
        msg2 = Message(
            claim_id=claim_airpods.id,
            sender_id=admin_user.id,
            content="Hello Aarav, your answer to the secret question matches the item in security custody. Your claim is approved. Please bring your student ID and the 6-digit Handover PIN to Central Security Desk (Admin Block) to collect.",
            sent_at=datetime.utcnow() - timedelta(hours=2),
            is_read=False
        )
        db.session.add_all([msg1, msg2])

        # Seed Notifications
        notif1 = Notification(
            user_id=student_1.id,
            title="High Match Found!",
            message="A found item 'Apple AirPods Pro (White) with Navy Blue Case' at Central Library matches your reported lost item (92% match score).",
            link=f"/items/{found_airpods.id}",
            type="match_found",
            is_read=True,
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        notif2 = Notification(
            user_id=student_1.id,
            title="Claim Approved - Ready for Pickup",
            message="Your claim for 'Apple AirPods Pro (White)' has been approved! Use Handover PIN: 749201 to collect at Central Security Desk.",
            link=f"/claims/{claim_airpods.id}",
            type="claim_approved",
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.session.add_all([notif1, notif2])

        # Seed Audit Logs
        log1 = AuditLog(
            action="ITEM_REPORTED",
            details="Aarav Sharma reported LOST item: Apple AirPods Pro 2",
            user_id=student_1.id,
            item_id=created_items[0].id
        )
        log2 = AuditLog(
            action="ITEM_REPORTED",
            details="Priya Patel reported FOUND item: Apple AirPods Pro (White)",
            user_id=student_2.id,
            item_id=created_items[1].id
        )
        log3 = AuditLog(
            action="CLAIM_APPROVED",
            details="Security Officer approved claim #1 for Aarav Sharma with Handover PIN generation.",
            user_id=admin_user.id,
            item_id=created_items[1].id
        )
        db.session.add_all([log1, log2, log3])

        db.session.commit()
        print("Database seeded successfully with users, items, claims, and campus locations!")
