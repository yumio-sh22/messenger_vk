from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.migrations import run_lightweight_migrations
from app.routers import auth, chats, messages, users

Base.metadata.create_all(bind=engine)
run_lightweight_migrations()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(messages.router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/register", include_in_schema=False)
def register_page() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/app", include_in_schema=False)
def app_page() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
