from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, forms, functions, nonfunctions, messages, files
import os
from dotenv import load_dotenv
from app.routers import ws as ws_router



load_dotenv()

app = FastAPI(title="SyncBridge API (Minimal)")

# CORS
frontend = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend] if frontend != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(forms.router, prefix="/api/v1", tags=["forms"])
app.include_router(functions.router, prefix="/api/v1", tags=["functions"])
app.include_router(nonfunctions.router, prefix="/api/v1", tags=["nonfunctions"])
app.include_router(messages.router, prefix="/api/v1", tags=["messages"])
app.include_router(files.router, prefix="/api/v1", tags=["files"])
app.include_router(ws_router, prefix="/api/v1")

# create DB tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"status":"success","message":"OK","data":{"info":"SyncBridge API running"}}
