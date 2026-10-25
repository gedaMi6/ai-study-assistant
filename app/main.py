import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from app.api.progress import router as progress_router
from app.api.admin import router as admin_router
from app.api.teacher_management import router as teacher_management_router
from app.api.chat_sessions import router as chat_sessions_router

from app.api.documents import router as documents_router
from app.api.ask import router as ask_router
from app.database.database import initialize_database
from app.api.quiz import router as quiz_router
from app.api.flashcards import router as flashcards_router
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router
from app.api.teacher_tasks import router as teacher_tasks_router
from app.api.teacher_exams import router as teacher_exams_router
from app.api.student_tasks import router as student_tasks_router
from app.api.student_exams import (
    router as student_exams_router,
    process_expired_exam_sessions,
)
from app.api.notifications import router as notifications_router
from app.api.teacher_monitoring import router as teacher_monitoring_router
from app.api.student_status import router as student_status_router

@asynccontextmanager
async def lifespan(app):
    worker = asyncio.create_task(_exam_expiry_loop())
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


async def _exam_expiry_loop():
    while True:
        try:
            processed = await asyncio.to_thread(process_expired_exam_sessions)
            if processed:
                print(f"[KANIA exam expiry] Finalized {processed} expired exam(s).")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[KANIA exam expiry] Worker error: {exc}")

        await asyncio.sleep(10)


app = FastAPI(title="KANIA.AI", lifespan=lifespan)
initialize_database()


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


app.mount(
    "/css",
    StaticFiles(directory=FRONTEND_DIR / "css"),
    name="css"
)

app.mount(
    "/js",
    StaticFiles(directory=FRONTEND_DIR / "js"),
    name="js"
)

app.mount(
    "/icons",
    StaticFiles(directory=FRONTEND_DIR / "icons"),
    name="icons"
)


app.include_router(documents_router)
app.include_router(ask_router)
app.include_router(quiz_router)
app.include_router(flashcards_router)
app.include_router(progress_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(admin_router)
app.include_router(teacher_management_router)
app.include_router(chat_sessions_router)
app.include_router(teacher_tasks_router)
app.include_router(teacher_exams_router)
app.include_router(student_tasks_router)
app.include_router(student_exams_router)
app.include_router(notifications_router)
app.include_router(teacher_monitoring_router)
app.include_router(student_status_router)

@app.get("/manifest.json")
def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/service-worker.js")
def service_worker():
    return FileResponse(FRONTEND_DIR / "service-worker.js", media_type="application/javascript")


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/login")
@app.get("/login.html")
def login_page():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/register.html")
def register_page():
    return FileResponse(FRONTEND_DIR / "register.html")


@app.get("/reset-password.html")
def reset_password_page():
    return FileResponse(FRONTEND_DIR / "reset-password.html")


@app.get("/app")
def dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/dashboard.html")
def dashboard_page():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/chat.html")
def chat():
    return FileResponse(FRONTEND_DIR / "chat.html")


@app.get("/flashcards.html")
def flashcards_page():
    return FileResponse(FRONTEND_DIR / "flashcards.html")


@app.get("/quiz.html")
def quiz():
    return FileResponse(FRONTEND_DIR / "quiz.html")


@app.get("/exams.html")
def exams_page():
    return FileResponse(FRONTEND_DIR / "exams.html")


@app.get("/exam.html")
async def exam_page():
    return FileResponse(FRONTEND_DIR / "exam.html")


@app.get("/progress.html")
def progress():
    return FileResponse(FRONTEND_DIR / "progress.html")

@app.get("/admin")
def admin_dashboard():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "KANIA.AI is running"
    }
