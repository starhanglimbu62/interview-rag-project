import concurrent.futures
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import redis
from sqlalchemy import select

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models import Booking

BASE_URL = "http://127.0.0.1:8000/api/v1/bookings/conversation"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KATHMANDU = ZoneInfo("Asia/Kathmandu")

results = []

def report(name, passed, detail=""):
    results.append((name, passed, detail))
    status = "PASS" if passed is True else "FAIL" if passed is False else "SKIP"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")


def post(payload, timeout=120):
    return httpx.post(BASE_URL, json=payload, timeout=timeout)

def new_slot(days=20, hour=10, minute=None):
    unique = uuid.uuid4().int
    days += unique % 300

    if minute is None:
        minute = (unique // 300) % 60

    target = datetime.now(KATHMANDU) + timedelta(days=days)

    return target.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

def create_complete_booking(name, email, slot):
    message = (
        f"My name is {name}, my email is {email}, "
        f"and I want an interview on "
        f"{slot.strftime('%B %d, %Y at %I:%M %p')} Nepal time."
    )
    response = post({"message": message})
    response.raise_for_status()
    return response.json()

def db_count(email=None, slot=None):
    with SessionLocal() as db:
        query = select(Booking)
        if email:
            query = query.where(Booking.email == email)
        if slot:
            query = query.where(Booking.interview_at == slot.astimezone(ZoneInfo("UTC")))
        return len(db.scalars(query).all())

print("\n========== BOOKING FAILURE-PATH TESTS ==========\n")

# API health
try:
    health = httpx.get("http://127.0.0.1:8000/health", timeout=5)
    report("API health", health.status_code == 200)
except Exception as exc:
    report("API health", False, str(exc))
    raise SystemExit("API is not reachable. Start uvicorn first.")

# Redis health
try:
    redis_client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=3)
    redis_client.ping()
    report("Redis health", True)
except Exception as exc:
    report("Redis health", False, str(exc))
    raise SystemExit("Redis must be running before these tests.")

# Ollama health
try:
    ollama = httpx.get("http://localhost:11434/api/tags", timeout=5)
    report("Ollama health", ollama.status_code == 200)
except Exception as exc:
    report("Ollama health", False, str(exc))
    raise SystemExit("Ollama must be running before these tests.")

# -------------------------------------------------
# TEST 1: Confirmation invalidation after update
# -------------------------------------------------
try:
    email = f"state-{uuid.uuid4().hex[:8]}@example.com"
    first_slot = new_slot(20, 10)
    second_slot = new_slot(21, 15)

    first = create_complete_booking("State Test", email, first_slot)
    cid = first["conversation_id"]

    if first["status"] != "awaiting_confirmation":
        raise AssertionError(f"Initial status: {first['status']}")

    changed = post({
        "message": (
            f"Change my interview to "
            f"{second_slot.strftime('%B %d, %Y at %I:%M %p')} Nepal time."
        ),
        "conversation_id": cid
    })
    changed.raise_for_status()
    changed_data = changed.json()

    correct_time = (
        datetime.fromisoformat(changed_data["booking_details"]["interview_at"])
        == second_slot
    )

    confirmed = post({
        "message": "I confirm the updated interview booking.",
        "conversation_id": cid,
        "confirm_booking": True
    })
    confirmed.raise_for_status()
    confirmed_data = confirmed.json()

    passed = (
        correct_time
        and changed_data["status"] == "awaiting_confirmation"
        and confirmed_data["status"] == "confirmed"
        and datetime.fromisoformat(
            confirmed_data["booking"]["interview_at"]
        ) == second_slot
    )

    report(
        "Confirmation invalidation after date change",
        passed,
        (
            f"Expected updated slot: {second_slot.isoformat()}\\n"
            f"Actual updated slot: {changed_data.get('booking_details', {}).get('interview_at')}\\n"
            f"Update status: {changed_data.get('status')}\\n"
            f"Confirmation status: {confirmed_data.get('status')}\\n"
            f"Confirmed slot: "
            f"{confirmed_data.get('booking', {}).get('interview_at') if confirmed_data.get('booking') else None}\\n"
            f"Time matched: {correct_time}"
        )
    )
except Exception as exc:
    report("Confirmation invalidation after date change", False, str(exc))

# -------------------------------------------------
# TEST 2: Confirmation without complete details
# -------------------------------------------------
try:
    cid = str(uuid.uuid4())
    response = post({
        "message": "I confirm my booking.",
        "conversation_id": cid,
        "confirm_booking": True
    })

    data = response.json()
    passed = (
        response.status_code == 422
        and data.get("detail") == "No booking details exist for this conversation"
    )

    report(
        "Confirmation without required details",
        passed,
        f"HTTP {response.status_code}, status={data.get('status')}"
    )
except Exception as exc:
    report("Confirmation without required details", False, str(exc))

# -------------------------------------------------
# TEST 3: Concurrent booking attempts
# -------------------------------------------------
try:
    slot = new_slot(30, 11)
    emails = [
        f"race-{uuid.uuid4().hex[:8]}@example.com",
        f"race-{uuid.uuid4().hex[:8]}@example.com"
    ]

    def attempt(email, candidate):
        try:
            data = create_complete_booking(candidate, email, slot)
            if data["status"] == "awaiting_confirmation":
                result = post({
                    "message": "I confirm this interview.",
                    "conversation_id": data["conversation_id"],
                    "confirm_booking": True
                })
                return result.status_code, result.json()
            return 200, data
        except Exception as exc:
            return 0, {"error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt, emails[0], "Race Candidate A"),
            executor.submit(attempt, emails[1], "Race Candidate B")
        ]
        outcomes = [future.result() for future in futures]

    count = db_count(slot=slot)
    statuses = [item[1].get("status") for item in outcomes]

    passed = count == 1 and statuses.count("confirmed") == 1

    report(
        "Concurrent duplicate-slot protection",
        passed,
        f"Database records={count}; outcomes={statuses}"
    )
except Exception as exc:
    report("Concurrent duplicate-slot protection", False, str(exc))

# -------------------------------------------------
# TEST 4: Redis unavailable
# -------------------------------------------------
print("\nRedis failure test requires temporarily stopping Redis.")

redis_service_stopped = False
try:
    print("This test will attempt to stop the local Redis Docker container.")
    containers = subprocess.check_output(
        ["docker", "ps", "--format", "{{.Names}}"],
        text=True
    ).splitlines()

    redis_candidates = [
        name for name in containers
        if "redis" in name.lower()
    ]

    if not redis_candidates:
        report(
            "Redis unavailable handling",
            False,
            "No running Redis Docker container found. Test skipped."
        )
    else:
        container_name = redis_candidates[0]
        subprocess.run(["docker", "stop", container_name], check=True)
        redis_service_stopped = True
        time.sleep(2)

        response = post({
            "message": "My name is Redis Failure, my email is redis-failure@example.com."
        }, timeout=15)

        report(
            "Redis unavailable handling",
            response.status_code == 503,
            f"HTTP status: {response.status_code}"
        )

except Exception as exc:
    report("Redis unavailable handling", False, str(exc))
finally:
    if redis_service_stopped:
        subprocess.run(
            ["docker", "start", container_name],
            check=False
        )
        time.sleep(3)

# -------------------------------------------------
# TEST 5: Ollama unavailable
# -------------------------------------------------
print("\nOllama outage test skipped.")

report(
    "Ollama unavailable handling",
    None,
    "Not tested. Requires a separate isolated connection-failure test."
)

# SUMMARY
# -------------------------------------------------
print("\n========== TEST SUMMARY ==========")

passed = sum(1 for _, ok, _ in results if ok is True)
failed = sum(1 for _, ok, _ in results if ok is False)
skipped = sum(1 for _, ok, _ in results if ok is None)

for name, ok, detail in results:
    status = "PASS" if ok is True else "FAIL" if ok is False else "SKIP"
    print(f"{status}: {name}")

print(f"\nPassed: {passed}")
print(f"Failed: {failed}")
print(f"Skipped: {skipped}")
print(f"Total:  {len(results)}")

if failed:
    raise SystemExit(1)
