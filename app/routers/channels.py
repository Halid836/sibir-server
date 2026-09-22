from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Channel, ChannelPost, ChannelSub, ChannelLike, ChannelComment, User
from ..schemas import (ChannelIn, ChannelUpdate, ChannelOut,
                       ChannelPostIn, ChannelPostOut,
                       ChannelCommentIn, ChannelCommentOut)
from ..deps import get_current_user

router = APIRouter(prefix="/channels", tags=["channels"])

def _channel_out(db: Session, ch: Channel, me: User) -> ChannelOut:
    subs = db.query(ChannelSub).filter(ChannelSub.channel_id == ch.id).count()
    owner = db.query(User).filter(User.id == ch.owner_id).first()
    subbed = db.query(ChannelSub).filter(
        ChannelSub.channel_id == ch.id, ChannelSub.user_id == me.id
    ).first() is not None
    return ChannelOut(
        id=ch.id, name=ch.name, username=ch.username, bio=ch.bio, avatar=ch.avatar,
        owner_id=ch.owner_id, owner_username=owner.username if owner else "",
        subscribers=subs, is_subscribed=subbed,
    )

@router.get("", response_model=list[ChannelOut])
def all_channels(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    channels = db.query(Channel).order_by(Channel.id.desc()).all()
    return [_channel_out(db, c, me) for c in channels]

@router.post("", response_model=ChannelOut)
def create(data: ChannelIn, db: Session = Depends(get_db),
           me: User = Depends(get_current_user)):
    if db.query(Channel).filter(Channel.username == data.username).first():
        raise HTTPException(400, "Юзернейм канала занят")
    ch = Channel(name=data.name, username=data.username, bio=data.bio,
                 avatar=data.avatar, owner_id=me.id)
    db.add(ch); db.commit(); db.refresh(ch)
    return _channel_out(db, ch, me)

@router.get("/{channel_id}", response_model=ChannelOut)
def get_channel(channel_id: int, db: Session = Depends(get_db),
                me: User = Depends(get_current_user)):
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch: raise HTTPException(404, "Канал не найден")
    return _channel_out(db, ch, me)

@router.put("/{channel_id}", response_model=ChannelOut)
def update(channel_id: int, data: ChannelUpdate,
           db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch: raise HTTPException(404, "Канал не найден")
    if ch.owner_id != me.id: raise HTTPException(403, "Не ваш канал")

    if data.username and data.username != ch.username:
        if db.query(Channel).filter(Channel.username == data.username).first():
            raise HTTPException(400, "Юзернейм занят")
        ch.username = data.username
    if data.name is not None: ch.name = data.name
    if data.bio is not None: ch.bio = data.bio
    if data.avatar is not None: ch.avatar = data.avatar

    db.commit(); db.refresh(ch)
    return _channel_out(db, ch, me)

@router.delete("/{channel_id}")
def delete(channel_id: int, db: Session = Depends(get_db),
           me: User = Depends(get_current_user)):
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch: raise HTTPException(404, "Канал не найден")
    if ch.owner_id != me.id: raise HTTPException(403, "Не ваш канал")
    db.delete(ch); db.commit()
    return {"ok": True}

@router.post("/{channel_id}/subscribe")
def subscribe(channel_id: int, db: Session = Depends(get_db),
              me: User = Depends(get_current_user)):
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch: raise HTTPException(404, "Канал не найден")

    sub = db.query(ChannelSub).filter(
        ChannelSub.channel_id == channel_id, ChannelSub.user_id == me.id
    ).first()
    if sub:
        db.delete(sub); db.commit(); return {"subscribed": False}
    db.add(ChannelSub(channel_id=channel_id, user_id=me.id))
    db.commit(); return {"subscribed": True}

# ---------- Посты канала ----------

@router.get("/{channel_id}/posts", response_model=list[ChannelPostOut])
def channel_posts(channel_id: int, db: Session = Depends(get_db),
                  me: User = Depends(get_current_user)):
    rows = db.query(ChannelPost).filter(ChannelPost.channel_id == channel_id)\
        .order_by(ChannelPost.created_at.desc()).all()
    result = []
    for p in rows:
        author = db.query(User).filter(User.id == p.author_id).first()
        liked = db.query(ChannelLike).filter(
            ChannelLike.post_id == p.id, ChannelLike.user_id == me.id
        ).first() is not None
        result.append(ChannelPostOut(
            id=p.id, channel_id=p.channel_id, author_id=p.author_id,
            author_username=author.username if author else "",
            text=p.text, likes=p.likes, created_at=p.created_at,
            liked_by_me=liked,
        ))
    return result

@router.post("/{channel_id}/posts", response_model=ChannelPostOut)
def add_channel_post(channel_id: int, data: ChannelPostIn,
                     db: Session = Depends(get_db),
                     me: User = Depends(get_current_user)):
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch: raise HTTPException(404, "Канал не найден")
    if ch.owner_id != me.id: raise HTTPException(403, "Только владелец")

    p = ChannelPost(channel_id=channel_id, author_id=me.id, text=data.text)
    db.add(p); db.commit(); db.refresh(p)
    return ChannelPostOut(
        id=p.id, channel_id=p.channel_id, author_id=p.author_id,
        author_username=me.username, text=p.text, likes=p.likes,
        created_at=p.created_at, liked_by_me=False,
    )

@router.delete("/posts/{post_id}")
def delete_channel_post(post_id: int, db: Session = Depends(get_db),
                        me: User = Depends(get_current_user)):
    p = db.query(ChannelPost).filter(ChannelPost.id == post_id).first()
    if not p: raise HTTPException(404, "Не найден")
    ch = db.query(Channel).filter(Channel.id == p.channel_id).first()
    if ch.owner_id != me.id: raise HTTPException(403, "Только владелец")
    db.delete(p); db.commit()
    return {"ok": True}

@router.post("/posts/{post_id}/like")
def like_channel_post(post_id: int, db: Session = Depends(get_db),
                      me: User = Depends(get_current_user)):
    p = db.query(ChannelPost).filter(ChannelPost.id == post_id).first()
    if not p: raise HTTPException(404, "Не найден")

    existing = db.query(ChannelLike).filter(
        ChannelLike.post_id == post_id, ChannelLike.user_id == me.id
    ).first()
    if existing:
        db.delete(existing); p.likes = max(0, p.likes - 1)
        db.commit(); return {"liked": False, "likes": p.likes}
    db.add(ChannelLike(post_id=post_id, user_id=me.id)); p.likes += 1
    db.commit(); return {"liked": True, "likes": p.likes}

@router.get("/posts/{post_id}/comments", response_model=list[ChannelCommentOut])
def channel_comments(post_id: int, db: Session = Depends(get_db),
                     me: User = Depends(get_current_user)):
    rows = db.query(ChannelComment).filter(ChannelComment.post_id == post_id)\
        .order_by(ChannelComment.created_at.asc()).all()
    result = []
    for c in rows:
        a = db.query(User).filter(User.id == c.author_id).first()
        result.append(ChannelCommentOut(
            id=c.id, post_id=c.post_id, author_id=c.author_id,
            author_name=a.name if a else "", author_username=a.username if a else "",
            text=c.text, created_at=c.created_at,
        ))
    return result

@router.post("/posts/{post_id}/comments", response_model=ChannelCommentOut)
def add_channel_comment(post_id: int, data: ChannelCommentIn,
                        db: Session = Depends(get_db),
                        me: User = Depends(get_current_user)):
    p = db.query(ChannelPost).filter(ChannelPost.id == post_id).first()
    if not p: raise HTTPException(404, "Не найден")
    c = ChannelComment(post_id=post_id, author_id=me.id, text=data.text)
    db.add(c); db.commit(); db.refresh(c)
    return ChannelCommentOut(
        id=c.id, post_id=c.post_id, author_id=c.author_id,
        author_name=me.name, author_username=me.username,
        text=c.text, created_at=c.created_at,
    )