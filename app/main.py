from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from app.api.progress import router as progress_router
from app.api.admin import router as admin_router
from app.api.chat_sessions import router as chat_sessions_router

from app.api.documents import router as documents_router
from app.api.ask import router as ask_router
from app.database.database import initialize_database
from app.api.quiz import router as quiz_router
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router

app = FastAPI(title="AI Study Assistant")
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


app.include_router(documents_router)
app.include_router(ask_router)
app.include_router(quiz_router)
app.include_router(progress_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(admin_router)
app.include_router(chat_sessions_router)

@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


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
def dashboard(request: Request):
    from app.api.auth import get_current_user

    if not get_current_user(request):
        return RedirectResponse("/login.html")

    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/dashboard.html")
def dashboard_page(request: Request):
    from app.api.auth import get_current_user

    if not get_current_user(request):
        return RedirectResponse("/login.html")

    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/chat.html")
def chat(request: Request):
    from app.api.auth import get_current_user

    if not get_current_user(request):
        return RedirectResponse("/login.html")

    return FileResponse(FRONTEND_DIR / "chat.html")


@app.get("/quiz.html")
def quiz(request: Request):
    from app.api.auth import get_current_user

    if not get_current_user(request):
        return RedirectResponse("/login.html")

    return FileResponse(FRONTEND_DIR / "quiz.html")


@app.get("/progress.html")
def progress(request: Request):
    from app.api.auth import get_current_user

    if not get_current_user(request):
        return RedirectResponse("/login.html")

    return FileResponse(FRONTEND_DIR / "progress.html")

@app.get("/admin")
def admin_dashboard(request: Request):
    from app.api.auth import get_current_user

    user = get_current_user(request)

    if not user:
        return RedirectResponse("/login.html")

    if user["role"] != "admin":
        return RedirectResponse("/app")

    return FileResponse(FRONTEND_DIR / "admin.html")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "AI Study Assistant is running"
    }
