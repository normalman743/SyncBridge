# SyncBridge API (FastAPI Backend)

SyncBridge is a requirement-management system that supports structured collaboration between **clients** and **developers**.  
This backend implements user authentication, requirement forms, negotiation subforms, messaging, file sharing, and real-time communication.

---

## 🚀 Features

- User registration with **license-based role activation**
- JWT authentication
- Mainform + Subform requirement workflow
- Functional & Non-functional requirement modules
- Messaging system with discussion blocks
- File upload/download (10MB)
- Full permission control based on project rules
- WebSocket real-time updates for messages

---

## 📁 Project Structure

```
app/
  main.py
  models.py
  schemas.py
  crud.py
  utils.py
  permissions.py
  websocket_manager.py
  routers/
    auth.py
    forms.py
    functions.py
    nonfunctions.py
    messages.py
    files.py
    ws.py
uploads/
.env
requirements.txt
```

---

## 🔧 Installation

### 1. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# or
source .venv/bin/activate     # macOS/Linux
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables (`.env`)
```
SECRET_KEY=your-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./app.db
```

### 4. Initialize database
```bash
python -c "from app.database import Base,engine; Base.metadata.create_all(bind=engine)"
```

---

## ▶ Run the Server

```bash
uvicorn app.main:app --reload
```

API Docs:

```
http://127.0.0.1:8000/docs
```

---

## 🔑 API Summary

### Authentication
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Forms
- `POST /form`
- `GET /forms`
- `GET /form/{id}`
- `PUT /form/{id}`
- `POST /form/{id}/subform`
- `PUT /form/{id}/status`

### Functions & Nonfunctions
- `GET /functions`
- `POST /function`
- `PUT /function/{id}`
- `DELETE /function/{id}`  
(Same for nonfunctions)

### Messages
- `GET /messages`
- `POST /message`
- `PUT /message/{id}`
- `DELETE /message/{id}`

### Files
- `POST /file`
- `GET /file/{id}`
- `DELETE /file/{id}`

---

## 🔌 WebSocket

```
/api/v1/ws?token=<JWT>&form_id=<id>
```

Used for:
- Live message updates
- Real-time notifications

---

## ✔ Ready for Submission

This backend includes:
- Working CRUD APIs  
- Role-based permissions  
- Real-time messaging  
- Clean modular architecture  
- Fully testable endpoints via Swagger UI  

