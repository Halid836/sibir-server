from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models import Chat, Message, User
from ..schemas import ChatOut, MessageIn, MessageOut
from ..deps import get_current_user
from ..ws_manager import manager

router = APIRouter(prefix="/chats", tags=["chats"])

def _chat_out(db: Session, chat: Chat, me: User) -> ChatOut:
    other_id = chat.user2_id if chat.user1_id == me.id else chat.user1_id
    other = db.query(User).filter(User.id == other_id).first()
    last = db.query(Message).filter(Message.chat_id == chat.id)\
        .order_by(Message.created_at.desc()).first()
    return ChatOut(
        id=chat.id, other_id=other.id, other_name=other.name,
        other_username=other.username, other_avatar=other.avatar,
        last_message=last.text if last else None,
    )

@router.get("", response_model=list[ChatOut])
def my_chats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chats = db.query(Chat).filter(
        or_(Chat.user1_id == user.id, Chat.user2_id == user.id)
    ).order_by(Chat.created_at.desc()).all()
    return [_chat_out(db, c, user) for c in chats]

@router.post("/with/{username}", response_model=ChatOut)
def open_chat(username: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    other = db.query(User).filter(User.username == username).first()
    if not other: raise HTTPException(404, "Пользователь не найден")
    if other.id == user.id: raise HTTPException(400, "Это вы")

    chat = db.query(Chat).filter(
        or_(
            (Chat.user1_id == user.id) & (Chat.user2_id == other.id),
            (Chat.user1_id == other.id) & (Chat.user2_id == user.id),
        )
    ).first()
    if not chat:
        chat = Chat(user1_id=user.id, user2_id=other.id)
        db.add(chat); db.commit(); db.refresh(chat)

    return _chat_out(db, chat, user)

@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def messages(chat_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or user.id not in (chat.user1_id, chat.user2_id):
        raise HTTPException(403, "Нет доступа")

    rows = db.query(Message).filter(Message.chat_id == chat_id)\
        .order_by(Message.created_at.asc()).all()
    result = []
    for m in rows:
        s = db.query(User).filter(User.id == m.sender_id).first()
        result.append(MessageOut(
            id=m.id, chat_id=m.chat_id, sender_id=m.sender_id,
            sender_username=s.username if s else "", text=m.text, created_at=m.created_at,
        ))
    return result

@router.post("/{chat_id}/messages", response_model=MessageOut)
async def send_message(chat_id: int, data: MessageIn,
                       db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or user.id not in (chat.user1_id, chat.user2_id):
        raise HTTPException(403, "Нет доступа")

    m = Message(chat_id=chat_id, sender_id=user.id, text=data.text)
    db.add(m); db.commit(); db.refresh(m)

    out = MessageOut(
        id=m.id, chat_id=m.chat_id, sender_id=m.sender_id,
        sender_username=user.username, text=m.text, created_at=m.created_at,
    )

    other_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    await manager.send_to_user(other_id, {"type": "message", "data": out.model_dump(mode="json")})
    return out