import os
from google.cloud import firestore

PROJECT_ID = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
FIRESTORE_EMULATOR = os.getenv("FIRESTORE_EMULATOR_HOST", "")

db = firestore.Client(project=PROJECT_ID)

# Seed one test employee
employee = {
    "employee_id": "EMP001",
    "name": "Ramesh Patil",
    "worker_wa_id": "whatsapp:+919825880424",
    "department": "Weaving",
    "location": "Nagpur",
    "language": "hi",
}

leave_balance = {
    "employee_id": "EMP001",
    "casual": 8,
    "sick": 5,
    "earned": 12,
    "unpaid": 0,
}

db.collection("employees").document("EMP001").set(employee)
db.collection("leave_balances").document("EMP001").set(leave_balance)

print("Seeded EMP001 — Ramesh Patil")
print(f"Leave balance: {leave_balance}")
