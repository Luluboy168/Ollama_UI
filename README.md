# Ollama WebUI

A full-stack chatbot web app with:

-  **FastAPI** backend (supports token authentication)
-  **Vue 3** frontend (single-page app style)
-  JWT login/register/logout support
-  Integration with **Ollama** for AI response
-  One-to-many user-specific chat sessions

---

## Project Structure
```
SDC_final/
├── backend/
│ ├── chat.db # SQLite database (auto created)
│ ├── model.py # FastAPI backend with routes and models
│ ├── utils.py
│ └── __init__.py
├── index.html # Vue3 single-page app
├── script.js
├── style.css
├── README.md
└── LICENSE
```

---

## Setup Instructions

### 1. Backend (FastAPI)

#### Install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy pydantic passlib[bcrypt] python-jose requests
```
#### Run server:
```
uvicorn model:app --reload
```
By default, it's available at: http://127.0.0.1:8000

### 2. Frontend (Vue 3 via CDN)
Simply open the file: `index.html`  
Make sure the backend is running, and you're good to go.

No build step or npm install required.

## Features

1. User Register / Login / Logout via JWT
2. Per-user Chat Session Management
3. Messages persist in SQLite via SQLAlchemy ORM
4. AI response streaming from Ollama
5. Clean and responsive interface

## API Summary

| Route                   | Method | Auth | Description                 |
|-------------------------|--------|------|-----------------------------|
| `/register`             | POST   | ❌   | Register new user           |
| `/token`                | POST   | ❌   | Login, returns JWT token    |
| `/sessions/`            | GET    | ✅   | Get current user's chats    |
| `/sessions/`            | POST   | ✅   | Create new chat session     |
| `/sessions/{id}`        | DELETE | ✅   | Delete a chat session       |
| `/msgs/{session_id}`    | GET    | ✅   | List messages in session    |
| `/msgs/{session_id}`    | POST   | ✅   | Send a message (stream)     |

## Development Notes

Ollama must be running locally (http://localhost:11434/api/generate)
You can run ollama run gemma:2b or other models
Responses are streamed via StreamingResponse and rendered live in Vue

## Authors

Built by [@Luluboy168](https://github.com/Luluboy168) & 
[@17171717171717](https://github.com/17171717171717)  

## License

MIT License – free to use, modify, and share.
