import asyncio
from contextlib import suppress

from fastapi import FastAPI

from app.api.v1 import auth, files, forms, functions, messages, nonfunctions, ws
from app.services.reminders import start_urgent_loop, start_normal_loop

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
