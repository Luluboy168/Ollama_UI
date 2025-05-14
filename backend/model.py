from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import requests
import json
from jose import jwt, JWTError
from utils import hash_password, verify_password, create_access_token, oauth2_scheme, SECRET_KEY, ALGORITHM

# gemma3:1b 
# ollama run gemma3:1b 
# uvicorn main:app --reload

DATABASE_URL = "sqlite:///./chat.db"

app = FastAPI()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_current_user(token: str = Depends(oauth2_scheme)):
    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------------------
# Database Models
# ---------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="owner")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="session")
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
    model: str = "gemma3:1b"

# Allow frontend on all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------
# Auth Routes
# ---------------------
@app.post("/register")
def register(form: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    if db.query(User).filter_by(username=form.username).first():
        raise HTTPException(status_code=400, detail="Username exists")
    user = User(username=form.username, password=hash_password(form.password))
    db.add(user)
    db.commit()
    return {"message": "Registered"}
@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter_by(username=form.username).first()
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# ---------------------
# Session Routes
# ---------------------
@app.post("/sessions/")
def create_session(session: SessionCreate, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    new_session = ChatSession(title=session.title, user_id=current_user.id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    db.close()
    return {"id": new_session.id, "title": new_session.title}

@app.get("/sessions/")
def list_sessions(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    sessions = db.query(ChatSession).filter_by(user_id=current_user.id).all()
    db.close()
    return [{"id": s.id, "title": s.title} for s in sessions]

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    session = db.query(ChatSession).filter_by(id=session_id, user_id=current_user.id).first()
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
                "model": msg.model,
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