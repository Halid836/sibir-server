from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from . import models  # важно: регистрирует таблицы
from .routers import auth, users, posts, channels, chats, ws

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sibir Messenger API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(channels.router)
app.include_router(chats.router)
app.include_router(ws.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "Sibir Messenger API"}
