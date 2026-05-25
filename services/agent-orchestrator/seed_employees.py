import os
import random
from datetime import date
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        app = firebase_admin.initialize_app(options={"projectId": os.getenv("GCLOUD_PROJECT", "autonomous-hr-495502")})
    else:
        cred = credentials.ApplicationDefault()
        app = firebase_admin.initialize_app(cred, {"projectId": "autonomous-hr-495502"})

db = firestore.client()

EMPLOYEES = [
    ("EMP001", "Ramesh Patil",       "+919876543210", "hi", "weaving",     "Nagpur",  "2019-03-15"),
    ("EMP002", "Sunita Deshmukh",    "+919876543211", "mr", "dyeing",      "Nagpur",  "2020-07-01"),
    ("EMP003", "Anil Meshram",       "+919876543212", "hi", "finishing",   "Nagpur",  "2018-11-20"),
    ("EMP004", "Kavita Thakur",      "+919876543213", "mr", "weaving",     "Nagpur",  "2021-02-10"),
    ("EMP005", "Dinesh Kolhe",       "+919876543214", "hi", "dyeing",      "Nagpur",  "2017-06-05"),
    ("EMP006", "Rekha Bansod",       "+919876543215", "mr", "quality",     "Nagpur",  "2022-01-15"),
    ("EMP007", "Vijay Hatwar",       "+919876543216", "hi", "weaving",     "Nagpur",  "2016-09-01"),
    ("EMP008", "Pratibha Ukey",      "+919876543217", "mr", "finishing",   "Nagpur",  "2023-03-20"),
    ("EMP009", "Suresh Yawale",      "+919876543218", "hi", "dyeing",      "Nagpur",  "2019-08-12"),
    ("EMP010", "Lata Kumbhare",      "+919876543219", "mr", "quality",     "Nagpur",  "2020-11-30"),
    ("EMP011", "Rajendra Bhagat",    "+919876543220", "hi", "weaving",     "Nagpur",  "2015-04-01"),
    ("EMP012", "Meena Dongre",       "+919876543221", "mr", "finishing",   "Nagpur",  "2021-09-15"),
    ("EMP013", "Pramod Rathod",      "+919876543222", "hi", "dyeing",      "Nagpur",  "2018-02-28"),
    ("EMP014", "Shobha Waghmare",    "+919876543223", "mr", "quality",     "Nagpur",  "2022-06-10"),
    ("EMP015", "Kiran Gajbhiye",     "+919876543224", "hi", "hr",          "Nagpur",  "2014-12-01"),
    ("EMP016", "Nanda Chavhan",      "+919876543225", "mr", "accounts",    "Nagpur",  "2019-05-20"),
    ("EMP017", "Bharat Mankar",      "+919876543226", "hi", "weaving",     "Nagpur",  "2023-01-09"),
    ("EMP018", "Archana Nandanwar",  "+919876543227", "mr", "finishing",   "Nagpur",  "2020-03-14"),
    ("EMP019", "Ganesh Fulzele",     "+919876543228", "hi", "dyeing",      "Nagpur",  "2016-07-22"),
    ("EMP020", "Vandana Ikhar",      "+919876543229", "mr", "quality",     "Nagpur",  "2021-10-05"),
    ("EMP021", "Harish Rewatkar",    "+919876543230", "hi", "weaving",     "Nagpur",  "2017-01-18"),
    ("EMP022", "Sarika Pimpalkar",   "+919876543231", "mr", "finishing",   "Nagpur",  "2022-08-25"),
    ("EMP023", "Nilesh Zade",        "+919876543232", "hi", "dyeing",      "Nagpur",  "2018-04-11"),
    ("EMP024", "Jayashree Kumare",   "+919876543233", "mr", "accounts",    "Nagpur",  "2019-12-03"),
    ("EMP025", "Sunil Ghode",        "+919876543234", "hi", "weaving",     "Nagpur",  "2020-06-16"),
    ("EMP026", "Chhaya Borkar",      "+919876543235", "mr", "quality",     "Nagpur",  "2023-07-01"),
    ("EMP027", "Amit Shah",          "+919876543236", "hi", "sales",       "Mumbai",  "2018-08-20"),
    ("EMP028", "Kaveri Krishnan",    "+919876543237", "ta", "sales",       "Mumbai",  "2020-02-14"),
    ("EMP029", "Rauf Ansari",        "+919876543238", "bn", "dispatch",    "Mumbai",  "2019-11-07"),
    ("EMP030", "Priya Nair",         "+919876543239", "ml", "sales",       "Mumbai",  "2021-04-23"),
    ("EMP031", "Alex Fernandes",     "+919876543240", "en", "dispatch",    "Mumbai",  "2017-03-30"),
    ("EMP032", "Seema Iyer",         "+919876543241", "ta", "sales",       "Mumbai",  "2022-09-12"),
    ("EMP033", "Deepak Shetty",      "+919876543242", "kn", "dispatch",    "Mumbai",  "2018-06-05"),
    ("EMP034", "Fatima Shaikh",      "+919876543243", "ur", "sales",       "Mumbai",  "2020-10-19"),
    ("EMP035", "Rohan Mehta",        "+919876543244", "hi", "accounts",    "Mumbai",  "2019-01-28"),
    ("EMP036", "Nisha Pillai",       "+919876543245", "ml", "dispatch",    "Mumbai",  "2023-05-15"),
    ("EMP037", "Shruti Kulkarni",    "+919876543246", "mr", "design",      "Pune",    "2019-07-10"),
    ("EMP038", "Mahesh Pawar",       "+919876543247", "mr", "sampling",    "Pune",    "2020-09-22"),
    ("EMP039", "Pooja Joshi",        "+919876543248", "hi", "design",      "Pune",    "2021-12-01"),
    ("EMP040", "Santosh Jadhav",     "+919876543249", "mr", "sampling",    "Pune",    "2018-03-17"),
    ("EMP041", "Neha Gadgil",        "+919876543250", "mr", "design",      "Pune",    "2022-04-08"),
    ("EMP042", "Amol Deshpande",     "+919876543251", "mr", "sampling",    "Pune",    "2017-11-14"),
    ("EMP043", "Rutuja Gokhale",     "+919876543252", "mr", "design",      "Pune",    "2023-02-20"),
    ("EMP044", "Vikram Phadke",      "+919876543253", "mr", "sampling",    "Pune",    "2019-06-03"),
    ("EMP045", "Manasi Apte",        "+919876543254", "mr", "design",      "Pune",    "2020-08-29"),
    ("EMP046", "Kedar Limaye",       "+919876543255", "mr", "accounts",    "Pune",    "2021-07-14"),
    ("EMP047", "Tulsiram Ingole",    "+919876543256", "hi", "raw_material","Wardha",  "2016-05-20"),
    ("EMP048", "Shanta Dhote",       "+919876543257", "mr", "raw_material","Wardha",  "2018-10-08"),
    ("EMP049", "Prakash Kalambe",    "+919876543258", "hi", "logistics",   "Wardha",  "2020-04-15"),
    ("EMP050", "Usha Tembhare",      "+919876543259", "mr", "logistics",   "Wardha",  "2019-02-27"),
    ("EMP051", "Ramakant Porte",     "+919876543260", "hi", "raw_material","Wardha",  "2017-08-11"),
    ("EMP052", "Manda Chavan",       "+919876543261", "mr", "logistics",   "Wardha",  "2022-11-03"),
]

def days_employed(joining_str):
    j = date.fromisoformat(joining_str)
    return (date.today() - j).days

def earned_leave_entitlement(joining_str):
    return min(30, days_employed(joining_str) // 20)

def seed_employee(emp):
    emp_id, name, mobile, lang, dept, location, joining = emp
    tenure_days = days_employed(joining)

    db.collection("employees").document(emp_id).set({
        "employee_id":   emp_id,
        "name":          name,
        "mobile":        mobile,
        "language_pref": lang,
        "department":    dept,
        "location":      location,
        "joining_date":  joining,
        "is_active":     True,
        "esic_number":   f"ESIC{emp_id[3:]}MH{random.randint(10000,99999)}",
        "created_at":    firestore.SERVER_TIMESTAMP,
    }, merge=True)

    used_casual = random.randint(0, min(5, tenure_days // 60))
    used_sick   = random.randint(0, min(4, tenure_days // 90))
    earned_total = earned_leave_entitlement(joining)
    used_earned  = random.randint(0, max(0, earned_total - 3))

    db.collection("leave_balances").document(emp_id).set({
        "employee_id": emp_id,
        "year":        date.today().year,
        "casual":  {"entitled": 12, "used": used_casual, "balance": 12 - used_casual},
        "sick":    {"entitled": 7,  "used": used_sick,   "balance": 7  - used_sick},
        "earned":  {"entitled": earned_total, "used": used_earned, "balance": earned_total - used_earned},
        "last_updated": firestore.SERVER_TIMESTAMP,
    }, merge=True)

def main():
    target = "EMULATOR" if os.getenv("FIRESTORE_EMULATOR_HOST") else "PRODUCTION"
    print(f"Seeding {len(EMPLOYEES)} employees to Firestore [{target}]...")
    for i, emp in enumerate(EMPLOYEES, 1):
        seed_employee(emp)
        print(f"  [{i:02d}/{len(EMPLOYEES)}] {emp[0]} — {emp[1]} ({emp[3].upper()}, {emp[5]})")
    print(f"\n✓ Done. {len(EMPLOYEES)} employees + {len(EMPLOYEES)} leave_balance docs written.")

main()
