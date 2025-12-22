import os
import asyncio
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, files, forms, functions, messages, nonfunctions, ws
from app.services.reminders import start_urgent_loop, start_normal_loop

app = FastAPI()

# CORS configuration via env: CORS_ALLOW_ORIGINS="https://a.com,https://b.com" or "*" (default)
_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
if _cors_origins.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(forms.router, prefix="/api/v1")
app.include_router(functions.router, prefix="/api/v1")
app.include_router(nonfunctions.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")


@app.on_event("startup")
async def _startup():
	# 启动两个独立的提醒循环：urgent 每分钟，normal 每小时
	app.state.reminder_urgent_task = asyncio.create_task(start_urgent_loop())
	app.state.reminder_normal_task = asyncio.create_task(start_normal_loop())


@app.on_event("shutdown")
async def _shutdown():
	for name in ("reminder_urgent_task", "reminder_normal_task"):
		task = getattr(app.state, name, None)
		if task:
			task.cancel()
			with suppress(asyncio.CancelledError):
				await task
