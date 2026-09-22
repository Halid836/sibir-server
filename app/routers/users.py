from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Follow, Post
from ..schemas import UserOut, UserUpdate
from ..deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

def _user_out(db: Session, user: User) -> UserOut:
    followers = db.query(Follow).filter(Follow.following_id == user.id).count()
    following = db.query(Follow).filter(Follow.follower_id == user.id).count()
    return UserOut(
        id=user.id, email=user.email, username=user.username,
        name=user.name, avatar=user.avatar, bio=user.bio,
        followers=followers, following=following,
    )

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_out(db, user)

@router.get("/search")
def search(q: str = Query(..., min_length=1), db: Session = Depends(get_db),
           current: User = Depends(get_current_user)):
    users = db.query(User).filter(
        ((User.username.ilike(f"%{q}%")) | (User.name.ilike(f"%{q}%")))
        & (User.id != current.id)
    ).limit(20).all()
    return [{"id": u.id, "username": u.username, "name": u.name, "avatar": u.avatar}
            for u in users]

@router.get("/{username}", response_model=UserOut)
def get_user(username: str, db: Session = Depends(get_db),
             current: User = Depends(get_current_user)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Не найден")
    return _user_out(db, user)

@router.put("/me", response_model=UserOut)
def update_me(data: UserUpdate, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    if data.username and data.username != user.username:
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(status_code=400, detail="Юзернейм занят")
        user.username = data.username
    if data.name is not None: user.name = data.name
    if data.bio is not None: user.bio = data.bio
    if data.avatar is not None: user.avatar = data.avatar
    db.commit()
    db.refresh(user)
    return _user_out(db, user)

@router.post("/{username}/follow")
def follow(username: str, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="Не найден")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")

    existing = db.query(Follow).filter(
        Follow.follower_id == user.id, Follow.following_id == target.id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"following": False}
    else:
        db.add(Follow(follower_id=user.id, following_id=target.id))
        db.commit()
        return {"following": True}