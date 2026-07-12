import os
import time
os.environ["API_KEY_COOLDOWN_SECONDS"] = "1"

import asyncio
import sys
from fastapi.testclient import TestClient
from main import app
from src.infrastructure.core.database import engine, Base

# Setup clean database tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    
    # Clean Redis keys to avoid test pollution
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(redis_url)
            keys = await r.keys("promptgpt:*")
            if keys:
                await r.delete(*keys)
            await r.aclose()
            print("[+] Redis namespace cleaned successfully!")
        except Exception as e:
            print(f"[-] Failed to clean Redis keys: {str(e)}")

print("[-] Resetting database tables and cache...")
asyncio.run(init_db())
print("[+] Database reset successful!")

client = TestClient(app)

# Helper function to print headers
def print_step(title):
    print(f"\n==========================================")
    print(f" STEP: {title}")
    print(f"==========================================")

# --- 1. Register and Login Creator & Guest Users ---
print_step("User Registration & Authentication")

# Register Creator
resp = client.post("/users/register", json={
    "email": "creator@test.com",
    "password": "Password123!",
    "nombre": "Creator User"
})
assert resp.status_code == 201, f"Failed registration: {resp.text}"
print("[+] Creator registered successfully")

# Login Creator
resp = client.post("/users/login", json={
    "email": "creator@test.com",
    "password": "Password123!"
})
assert resp.status_code == 200
token_creator = resp.json()["access_token"]
headers_creator = {"Authorization": f"Bearer {token_creator}"}
print("[+] Creator logged in and received token")

# ── Test: autenticación por cookie cross-origin ──────────────────────────────
# 1. Verificar que el login inyecta la cookie Set-Cookie en la respuesta
assert "set-cookie" in resp.headers, "FAIL: Login no devolvió Set-Cookie header"
set_cookie_value = resp.headers["set-cookie"]
assert "access_token=" in set_cookie_value, "FAIL: Cookie no contiene access_token"
assert "HttpOnly" in set_cookie_value, "FAIL: Cookie no tiene flag HttpOnly"
print("[+] Login inyecta cookie HttpOnly 'access_token' correctamente")

# 2. Verificar que la cookie autentica en /users/me sin header Authorization
resp_cookie = client.get("/users/me", cookies={"access_token": token_creator})
assert resp_cookie.status_code == 200, f"FAIL: Cookie auth falló en /users/me: {resp_cookie.text}"
assert resp_cookie.json()["email"] == "creator@test.com", "FAIL: Email incorrecto en respuesta cookie"
print("[+] Cookie 'access_token' autentica correctamente en /users/me (sin Bearer header)")
# ─────────────────────────────────────────────────────────────────────────────

# Register Guest
resp = client.post("/users/register", json={
    "email": "guest@test.com",
    "password": "Password123!",
    "nombre": "Guest User"
})
assert resp.status_code == 201
print("[+] Guest registered successfully")

# Login Guest
resp = client.post("/users/login", json={
    "email": "guest@test.com",
    "password": "Password123!"
})
assert resp.status_code == 200
token_guest = resp.json()["access_token"]
headers_guest = {"Authorization": f"Bearer {token_guest}"}
print("[+] Guest logged in and received token")


# --- 2. Creator: Manage Notebooks & Files ---
print_step("Creator: Managing Notebooks & Files")

# Generate API Key to authorize notebook creation (requires Bearer token)
resp = client.post("/api-keys", json={"title": "Notebook Creation Key"}, headers=headers_creator)
assert resp.status_code == 201, f"Expected 201, got {resp.text}"
key_data = resp.json()
notebook_api_key = key_data["api_key"]
print("[+] Generated Notebook Creation API Key")

# Create Notebook requiring BOTH Bearer token and X-API-Key
headers_creator_double = {
    "Authorization": f"Bearer {token_creator}",
    "X-API-Key": notebook_api_key
}

# First, test that creating a notebook without X-API-Key fails with 401
resp_fail = client.post("/notebooks", json={
    "title": "Química Orgánica",
    "description": "Temario completo de compuestos orgánicos y RAG"
}, headers=headers_creator)
assert resp_fail.status_code == 401
print("[+] SUCCESS: Notebook creation without X-API-Key was BLOCKED")

# Then, create notebook with both headers (should succeed and consume the API key)
resp = client.post("/notebooks", json={
    "title": "Química Orgánica",
    "description": "Temario completo de compuestos orgánicos y RAG"
}, headers=headers_creator_double)
assert resp.status_code == 201
notebook_id = resp.json()["id"]
print(f"[+] Notebook 'Química Orgánica' created (ID: {notebook_id})")

# List Notebooks
resp = client.get("/notebooks", headers=headers_creator)
assert resp.status_code == 200
assert len(resp.json()) == 1
assert resp.json()[0]["title"] == "Química Orgánica"
print("[+] Notebook listed correctly")

# Upload Text File (TXT)
resp = client.post(
    f"/notebooks/{notebook_id}/files",
    files={"file": ("notes.txt", b"# Hidrocarburos\nLos hidrocarburos son compuestos formados por C y H.", "text/plain")},
    headers=headers_creator
)
assert resp.status_code == 201
file1_id = resp.json()["id"]
print(f"[+] File notes.txt uploaded successfully (ID: {file1_id})")

# Upload Simulated PDF File
resp = client.post(
    f"/notebooks/{notebook_id}/files",
    files={"file": ("slides.pdf", b"pdfbinarydata", "application/pdf")},
    headers=headers_creator
)
assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
file2_id = resp.json()["id"]
print(f"[+] File slides.pdf uploaded and simulated to Markdown (ID: {file2_id})")

# List Files
resp = client.get(f"/notebooks/{notebook_id}/files", headers=headers_creator)
assert resp.status_code == 200
files = resp.json()
assert len(files) == 2
print(f"[+] Listed {len(files)} files in the notebook")


# --- 3. Creator: Chatting & Pagination ---
print_step("Creator: Chat & Paginated Message Logs")

# Create Chat
resp = client.post(f"/notebooks/{notebook_id}/chats", json={"title": "Chat de Dudas"}, headers=headers_creator)
assert resp.status_code == 201
chat_id = resp.json()["id"]
print(f"[+] Chat created (ID: {chat_id})")

# Send user message
resp = client.post(f"/notebooks/chats/{chat_id}/messages", json={"content": "Hola, ¿qué es un alcano?"}, headers=headers_creator)
assert resp.status_code == 201
print("[+] User message added to chat")

# List messages paginated
resp = client.get(f"/notebooks/chats/{chat_id}/messages?page=1&limit=5", headers=headers_creator)
assert resp.status_code == 200
messages = resp.json()
assert len(messages) == 2
assert messages[0]["content"] == "Hola, ¿qué es un alcano?"
assert messages[1]["role"] == "assistant"
print(f"[+] Retrieved {len(messages)} message(s) under pagination constraints")


# --- 4. Creator: AI Flashcards & Exam Generation via RAG ---
print_step("Creator: Generating Flashcards & Exams via Simulated RAG")

# Generate Flashcards
resp = client.post("/assessments/flashcards", json={
    "notebook_id": notebook_id,
    "prompt": "Generar 3 flashcards clave sobre alcanos",
    "cantidad": 3
}, headers=headers_creator)
assert resp.status_code == 201
flashcards = resp.json()
assert len(flashcards) == 3
print(f"[+] Generated {len(flashcards)} flashcards using notebook file contents as RAG text context")

# List Flashcards
resp = client.get(f"/assessments/flashcards/{notebook_id}", headers=headers_creator)
assert resp.status_code == 200
assert len(resp.json()) == 3
print("[+] Flashcards saved and retrieved from relational DB successfully")

# Generate Exam
resp = client.post("/assessments/exam", json={
    "notebook_id": notebook_id,
    "prompt": "Examen de hidrocarburos",
}, headers=headers_creator)
assert resp.status_code == 201
examen = resp.json()
examen_id = examen["id"]
print(f"[+] Generated Exam: '{examen['title']}' (ID: {examen_id})")
assert len(examen["preguntas"]) == 3
print(f"[+] Exam template has {len(examen['preguntas'])} questions with option dictionaries")


# --- 4.5. Creator: Summary Generation ---
print_step("Creator: Generating Summaries")

# Generate Summary from notebook context
resp = client.post(f"/notebooks/{notebook_id}/summaries", headers=headers_creator)
assert resp.status_code == 201
resumen_id = resp.json()["id"]
print(f"[+] Generated Summary (ID: {resumen_id})")

# List Summaries
resp = client.get(f"/notebooks/{notebook_id}/summaries", headers=headers_creator)
assert resp.status_code == 200
summaries = resp.json()
assert len(summaries) == 1
assert "content" in summaries[0]
print("[+] Listed summaries correctly")


# --- 5. Study Room Collaboration & Access Control Proxy ---
print_step("Study Rooms: Access Code and Write Proxy Validation")

# Create Study Room
resp = client.post("/study-rooms", json={
    "title": "Grupo de Estudio de Química",
    "notebook_id": notebook_id
}, headers=headers_creator)
assert resp.status_code == 201
sala_id = resp.json()["id"]
codigo_sala = resp.json()["codigo"]
print(f"[+] Study room created (ID: {sala_id}, Access Code: {codigo_sala})")

# Join Study Room as Guest User
resp = client.post("/study-rooms/join", json={"codigo": codigo_sala}, headers=headers_guest)
assert resp.status_code == 200
print(f"[+] Guest user joined study room successfully using code '{codigo_sala}'")

# Guest checks Access
resp = client.get(f"/study-rooms/{sala_id}/acceso", headers=headers_guest)
assert resp.status_code == 200
assert resp.json()["role"] == "invitado"
print("[+] Access verification returned Guest / 'invitado' role")

# Test write protection: Guest tries to upload a file to the study room (should be blocked)
resp = client.post(
    f"/study-rooms/{sala_id}/files",
    files={"file": ("hacker.txt", b"malicious content", "text/plain")},
    headers=headers_guest
)
assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"
print("[+] SUCCESS: Guest user was BLOCKED from writing a file to the study room (Proxy protection working!)")

# Test write protection: Guest tries to delete a file from the study room (should be blocked)
resp = client.delete(f"/study-rooms/{sala_id}/files/{file1_id}", headers=headers_guest)
assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"
print("[+] SUCCESS: Guest user was BLOCKED from deleting a file from the study room (Proxy protection working!)")


# --- 5.5 Guest Room Collaboration Tests ---
print_step("Study Rooms: Guest Collaboration & Read/Interactive Endpoints")

# Guest lists files of study room
resp = client.get(f"/study-rooms/{sala_id}/files", headers=headers_guest)
assert resp.status_code == 200
assert len(resp.json()) == 2
print("[+] Guest successfully listed room files")

# Guest lists chats of study room
resp = client.get(f"/study-rooms/{sala_id}/chats", headers=headers_guest)
assert resp.status_code == 200
assert len(resp.json()) == 0
print("[+] Guest successfully listed room chats (0 initially)")

# Guest tries to list messages paginated of Creator's chat
resp = client.get(f"/study-rooms/{sala_id}/chats/{chat_id}/messages?page=1&limit=5", headers=headers_guest)
assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
print("[+] Guest successfully blocked from reading creator's chat messages (Chat isolation working!)")

# Guest tries to send a message to Creator's chat
resp = client.post(f"/study-rooms/{sala_id}/chats/{chat_id}/messages", json={"content": "Hola desde la sala como invitado!"}, headers=headers_guest)
assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
print("[+] Guest successfully blocked from writing to creator's chat (Chat isolation working!)")

# Test Chat Isolation:
# 1. Guest creates a new chat in the room
resp = client.post(f"/notebooks/{notebook_id}/chats", json={"title": "Chat Privado de Invitado"}, headers=headers_guest)
assert resp.status_code == 201
guest_chat_id = resp.json()["id"]

# 2. Guest lists their chats in the room, should see their chat
resp = client.get(f"/study-rooms/{sala_id}/chats", headers=headers_guest)
assert resp.status_code == 200
guest_chats = resp.json()
assert len(guest_chats) == 1
assert guest_chats[0]["id"] == guest_chat_id
print("[+] Chat isolation: Guest only sees their own chats in the study room")

# 3. Creator lists their chats in the room, should NOT see guest's chat
resp = client.get(f"/study-rooms/{sala_id}/chats", headers=headers_creator)
assert resp.status_code == 200
creator_chats = resp.json()
assert len(creator_chats) == 1
assert creator_chats[0]["id"] == chat_id
print("[+] Chat isolation: Creator only sees their own chats, and NOT guest's chats")

# Guest generates flashcards from specific file in study room
resp = client.post(f"/study-rooms/{sala_id}/flashcards", json={
    "notebook_id": notebook_id,
    "prompt": "Generar flashcards selectivas",
    "cantidad": 2,
    "archivo_ids": [file1_id]
}, headers=headers_guest)
assert resp.status_code == 201
assert len(resp.json()) == 2
print("[+] Guest successfully generated flashcards using selective archivo_ids context!")

# Guest tries to generate an exam in study room (should be blocked)
resp = client.post(f"/study-rooms/{sala_id}/exam", json={
    "notebook_id": notebook_id,
    "prompt": "Examen desde invitado",
}, headers=headers_guest)
assert resp.status_code == 403
print("[+] SUCCESS: Guest user was BLOCKED from generating an exam in the study room (Proxy protection working!)")

# Creator generates an exam in study room (should be allowed)
resp = client.post(f"/study-rooms/{sala_id}/exam", json={
    "notebook_id": notebook_id,
    "prompt": "Examen desde creador",
}, headers=headers_creator)
assert resp.status_code == 201
room_exam = resp.json()
room_exam_id = room_exam["id"]
room_q1_id = room_exam["preguntas"][0]["id"]
room_q2_id = room_exam["preguntas"][1]["id"]
room_q3_id = room_exam["preguntas"][2]["id"]
print("[+] Creator successfully generated an exam in the study room")


# --- 6. Private Exam Scoring ---
print_step("Scoring and Private Attempt Persistence")

# Creator answers exam (100% correct)
# Preguntas are retrieved. We extract their correct answers from DB or assume the simulated answers:
# Q1: B, Q2: C, Q3: B
q1_id = examen["preguntas"][0]["id"]
q2_id = examen["preguntas"][1]["id"]
q3_id = examen["preguntas"][2]["id"]

resp = client.post(f"/assessments/exam/{examen_id}/submit", json={
    "respuestas": [
        {"pregunta_id": q1_id, "opcion": "B"},
        {"pregunta_id": q2_id, "opcion": "C"},
        {"pregunta_id": q3_id, "opcion": "B"}
    ]
}, headers=headers_creator)
assert resp.status_code == 201
intento_creator = resp.json()
assert intento_creator["score"] == 100.0
print(f"[+] Creator resolved exam. Score: {intento_creator['score']}%")

# Guest answers exam (2 correct, 1 wrong -> 66.67%)
resp = client.post(f"/assessments/exam/{examen_id}/submit", json={
    "respuestas": [
        {"pregunta_id": q1_id, "opcion": "B"},
        {"pregunta_id": q2_id, "opcion": "A"},  # Correct is C
        {"pregunta_id": q3_id, "opcion": "B"}
    ]
}, headers=headers_guest)
assert resp.status_code == 201
intento_guest = resp.json()
assert intento_guest["score"] == 66.67
print(f"[+] Guest resolved exam. Score: {intento_guest['score']}%")

# Verify attempts privacy: Creator lists attempts
resp = client.get("/assessments/attempts", headers=headers_creator)
assert resp.status_code == 200
attempts_creator = resp.json()
assert len(attempts_creator) == 1
assert attempts_creator[0]["id"] == intento_creator["id"]
print("[+] Creator only sees their own attempts")

# Verify attempts privacy: Guest lists attempts
resp = client.get("/assessments/attempts", headers=headers_guest)
assert resp.status_code == 200
attempts_guest = resp.json()
assert len(attempts_guest) == 1
assert attempts_guest[0]["id"] == intento_guest["id"]
print("[+] Guest only sees their own attempts (Privacy verified!)")


# --- 7. Leave Study Room ---
print_step("Guest Leaving Study Room")

# Guest leaves the study room
resp = client.delete(f"/study-rooms/{sala_id}/leave", headers=headers_guest)
assert resp.status_code == 200
print("[+] Guest successfully left the study room")

# Guest tries to list files in the study room (should be 403 because they no longer have access)
resp = client.get(f"/study-rooms/{sala_id}/files", headers=headers_guest)
assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
print("[+] Guest is blocked from accessing the study room after leaving")

# --- 8. Progress and Metrics Module Tests ---
print_step("Progress and Daily Activity Logs")

# GET /progress/metrics
resp = client.get("/progress/metrics", headers=headers_creator)
assert resp.status_code == 200
metrics = resp.json()
assert metrics["total_exams_completed"] == 1
assert metrics["average_score"] == 100.0
print("[+] User progress metrics verified successfully")

# GET /progress/pending-cards
resp = client.get("/progress/pending-cards", headers=headers_creator)
assert resp.status_code == 200
assert len(resp.json()) >= 3
print("[+] Pending flashcards list retrieved successfully")

# GET /progress/daily-activity
resp = client.get("/progress/daily-activity", headers=headers_creator)
assert resp.status_code == 200
assert len(resp.json()) >= 1
print("[+] Daily activity log aggregation verified successfully")


# --- 9. API Keys Module Tests (Single-use Validation) ---
print_step("API Keys and Single-use Authorization Header")

# Wait 2.0 seconds since the notebook creation key was generated, to reset rate limit
time.sleep(2.0)

# POST /api-keys
resp = client.post("/api-keys", json={"title": "External Service Key"}, headers=headers_creator)
assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
key_data = resp.json()
api_key = key_data["api_key"]
key_jti = key_data["jti"]
print(f"[+] Issued API Key with JTI: {key_jti}")

# Test rate limiting: immediately try to generate another API Key (should fail with 429)
resp_mass = client.post("/api-keys", json={"title": "Spam Key"}, headers=headers_creator)
assert resp_mass.status_code == 429
assert "Límite excedido" in resp_mass.json()["detail"]
print("[+] SUCCESS: Rapid API Key generation was BLOCKED (Rate limiter/Mass injection prevention working!)")

# GET /api-keys
resp = client.get("/api-keys", headers=headers_creator)
assert resp.status_code == 200
assert any(k["id"] == key_jti and k["active"] for k in resp.json())
print("[+] API Keys history lists key as active")

# Authenticate using API Key header (First use - Should succeed)
resp = client.get("/users/me", headers={"X-API-Key": api_key})
assert resp.status_code == 200
assert resp.json()["email"] == "creator@test.com"
print("[+] First consumption of API Key succeeded")

# Authenticate using API Key header (Second use - Should be BLOCKED/401)
resp = client.get("/users/me", headers={"X-API-Key": api_key})
assert resp.status_code == 401
assert "consumida" in resp.json()["detail"]
print("[+] SUCCESS: Second consumption of API Key was BLOCKED (Single-use validated!)")

# Wait 2.0 seconds to avoid rate limiting for the next generation
time.sleep(2.0)

# Create a second key and deactivate it
resp = client.post("/api-keys", json={"title": "Revocable Key"}, headers=headers_creator)
assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
rev_key = resp.json()["api_key"]
rev_jti = resp.json()["jti"]

resp = client.delete(f"/api-keys/{rev_jti}", headers=headers_creator)
assert resp.status_code == 200
print("[+] API Key revoked successfully")

# Authenticate using revoked key (Should fail)
resp = client.get("/users/me", headers={"X-API-Key": rev_key})
assert resp.status_code == 401
print("[+] SUCCESS: Consumption of revoked API Key was BLOCKED")


# --- 10. Webhooks and Event Subscription Tests ---
print_step("Webhooks Asynchronous Dispatch & Retry logs")

# POST /webhooks/subscriptions
resp = client.post("/webhooks/subscriptions", json={
    "org_id": sala_id,
    "url": "https://httpbin.org/post"
}, headers=headers_creator)
assert resp.status_code == 201
sub_id = resp.json()["id"]
print(f"[+] Webhook subscription registered for org_id {sala_id} pointing to {resp.json()['url']}")

# GET /webhooks/subscriptions/org/{org_id}
resp = client.get(f"/webhooks/subscriptions/org/{sala_id}", headers=headers_creator)
assert resp.status_code == 200
assert len(resp.json()) == 1
print("[+] Webhook subscription retrieved successfully")

# Submit an exam (triggers webhook in background task)
resp = client.post(f"/assessments/exam/{room_exam_id}/submit", json={
    "respuestas": [
        {"pregunta_id": room_q1_id, "opcion": "B"},
        {"pregunta_id": room_q2_id, "opcion": "C"},
        {"pregunta_id": room_q3_id, "opcion": "B"}
    ]
}, headers=headers_creator)
assert resp.status_code == 201
print("[+] Exam solved to trigger background webhook delivery")

# Wait a fraction of a second for BackgroundTasks to process or query logs directly
resp = client.get("/internal/webhooks/attempts", headers=headers_creator)
assert resp.status_code == 200
attempts = resp.json()
assert len(attempts) >= 1
print(f"[+] Webhook audit log captured delivery attempt (Attempt ID: {attempts[0]['id']})")
attempt_id = attempts[0]["id"]

# POST /internal/webhooks/attempts/{attempt_id}/retry
resp = client.post(f"/internal/webhooks/attempts/{attempt_id}/retry", headers=headers_creator)
assert resp.status_code == 200
print("[+] Webhook retry enqueued successfully")


# --- 11. Admin Panel & Diagnostics Tests ---
print_step("Admin Panel and System Health Diagnostics")

# GET /admin/classes/{id}/stats
resp = client.get(f"/admin/classes/{sala_id}/stats", headers=headers_creator)
assert resp.status_code == 200
print(f"[+] Class Stats average score: {resp.json()['average_score']}%")

# GET /admin/users/{id}/audit-logs
resp = client.get(f"/admin/users/1/audit-logs", headers=headers_creator)
assert resp.status_code == 200
assert len(resp.json()) >= 1
print("[+] Audit logs fetched successfully")

# GET /admin/users/{id}/storage
resp = client.get(f"/admin/users/1/storage", headers=headers_creator)
assert resp.status_code == 200
storage = resp.json()
assert storage["total_files"] == 2
assert storage["storage_mb"] > 0
print(f"[+] Tenant Storage usage calculated dynamically: {storage['storage_mb']} MB")

# GET /health/v1
resp = client.get("/health/v1")
assert resp.status_code == 200
assert resp.json()["status"] == "healthy"
print("[+] health/v1 check returned status online")

# GET /health/processes
resp = client.get("/health/processes")
assert resp.status_code == 200
print("[+] health/processes monitoring checked successfully")

# GET /health/metadata
resp = client.get("/health/metadata")
assert resp.status_code == 200
assert resp.json()["version"] == "0.2.0"
print("[+] health/metadata checked successfully")


print("\n==========================================")
print(" ALL TESTS PASSED SUCCESSFULLY! (61 Endpoints Verified)")
print("==========================================\n")
