import asyncio
from contextlib import suppress

from fastapi import FastAPI

from app.api.v1 import auth, files, forms, functions, messages, nonfunctions, ws
from app.services.reminders import start_reminder_loop

app = FastAPI()

app.include_router(auth.router, prefix="/api/v1")
app.include_router(forms.router, prefix="/api/v1")
app.include_router(functions.router, prefix="/api/v1")
app.include_router(nonfunctions.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")


@app.on_event("startup")
async def _startup():
	app.state.reminder_task = asyncio.create_task(start_reminder_loop())


@app.on_event("shutdown")
async def _shutdown():
	task = getattr(app.state, "reminder_task", None)
	if task:
		task.cancel()
		with suppress(asyncio.CancelledError):
			await task
