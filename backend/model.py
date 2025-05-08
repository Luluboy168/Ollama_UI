from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import requests
import json

# gemma3:1b 
# ollama run gemma3:1b 
# uvicorn main:app --reload

DATABASE_URL = "sqlite:///./chat.db"

app = FastAPI()

# Allow frontend on all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------------------
# Database Models
# ---------------------
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")

Base.metadata.create_all(bind=engine)

# ---------------------
# Pydantic Schemas
# ---------------------
class SessionCreate(BaseModel):
    title: str

class MessageCreate(BaseModel):
    user_msg: str

# ---------------------
# Session Routes
# ---------------------
@app.post("/sessions/")
def create_session(session: SessionCreate):
    db = SessionLocal()
    new_session = ChatSession(title=session.title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    db.close()
    return {"id": new_session.id, "title": new_session.title}

@app.get("/sessions/")
def list_sessions():
    db = SessionLocal()
    sessions = db.query(ChatSession).all()
    db.close()
    return [{"id": s.id, "title": s.title} for s in sessions]

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int):
    db = SessionLocal()
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    db.close()
    return {"message": "Session deleted"}

# ---------------------
# Message Routes
# ---------------------
@app.get("/msgs/{session_id}")
def get_messages(session_id: int):
    db = SessionLocal()
    msgs = db.query(ChatMessage).filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
    db.close()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]

@app.post("/msgs/{session_id}")
def post_message(session_id: int, msg: MessageCreate):
    db = SessionLocal()
    chat_session = db.query(ChatSession).filter_by(id=session_id).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ChatMessage(session_id=session_id, role="user", content=msg.user_msg)
    db.add(user_msg)
    db.commit()

    def save_full_response(full_response):
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=full_response)
        db.add(assistant_msg)
        db.commit()
        db.close()

    def event_stream():
        # Call Ollama API
        try:
            full = []
            with requests.post("http://localhost:11434/api/generate", json={
                "model": "llama2:latest",
                "prompt": msg.user_msg,
                "stream": True
            }, stream=True) as r:
                for line in r.iter_lines(chunk_size=512):
                    if line:
                        data = json.loads(line.decode("utf-8"))
                        if "response" in data:
                            chunk = data["response"]
                            full.append(chunk)
                            yield chunk + "\n"
        except Exception as e:
            yield "[錯誤] 無法從 Ollama 取得回答。"
        finally:
            save_full_response(''.join(full))


    return StreamingResponse(event_stream(), media_type="text/plain")

# ---------------------
# Ping Test Route
# ---------------------
@app.get("/")
def root():
    return {"message": "Ollama Chatbot API 正常運作中"}