from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Post, User, Like, Comment
from ..schemas import PostIn, PostOut, CommentIn, CommentOut
from ..deps import get_current_user

router = APIRouter(prefix="/posts", tags=["posts"])

def _post_out(p: Post, author: User) -> PostOut:
    return PostOut(
        id=p.id, author_id=p.author_id,
        author_name=author.name, author_username=author.username,
        author_avatar=author.avatar,
        text=p.text, likes=p.likes, repost_of=p.repost_of,
        created_at=p.created_at,
    )

@router.get("", response_model=list[PostOut])
def feed(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    posts = db.query(Post).filter(Post.repost_of == 0)\
        .order_by(Post.created_at.desc()).limit(100).all()
    result = []
    for p in posts:
        a = db.query(User).filter(User.id == p.author_id).first()
        if a: result.append(_post_out(p, a))
    return result

@router.post("", response_model=PostOut)
def create(data: PostIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    p = Post(author_id=user.id, text=data.text, repost_of=data.repost_of)
    db.add(p); db.commit(); db.refresh(p)
    return _post_out(p, user)

@router.delete("/{post_id}")
def delete(post_id: int, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if not p: raise HTTPException(404, "Не найден")
    if p.author_id != user.id: raise HTTPException(403, "Не ваш пост")
    db.delete(p); db.commit()
    return {"ok": True}

@router.post("/{post_id}/like")
def like(post_id: int, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if not p: raise HTTPException(404, "Не найден")
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user.id).first()
    if existing:
        db.delete(existing); p.likes = max(0, p.likes - 1)
        db.commit(); return {"liked": False, "likes": p.likes}
    else:
        db.add(Like(post_id=post_id, user_id=user.id)); p.likes += 1
        db.commit(); return {"liked": True, "likes": p.likes}

@router.get("/{post_id}/comments", response_model=list[CommentOut])
def comments(post_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    rows = db.query(Comment).filter(Comment.post_id == post_id)\
        .order_by(Comment.created_at.asc()).all()
    result = []
    for c in rows:
        a = db.query(User).filter(User.id == c.author_id).first()
        if a:
            result.append(CommentOut(
                id=c.id, post_id=c.post_id, author_id=c.author_id,
                author_name=a.name, author_username=a.username,
                author_avatar=a.avatar, text=c.text, created_at=c.created_at,
            ))
    return result

@router.post("/{post_id}/comments", response_model=CommentOut)
def add_comment(post_id: int, data: CommentIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if not p: raise HTTPException(404, "Не найден")
    c = Comment(post_id=post_id, author_id=user.id, text=data.text)
    db.add(c); db.commit(); db.refresh(c)
    return CommentOut(
        id=c.id, post_id=c.post_id, author_id=c.author_id,
        author_name=user.name, author_username=user.username,
        author_avatar=user.avatar, text=c.text, created_at=c.created_at,
    )

@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if not c: raise HTTPException(404, "Не найден")
    post = db.query(Post).filter(Post.id == c.post_id).first()
    if c.author_id != user.id and (not post or post.author_id != user.id):
        raise HTTPException(403, "Нет прав")
    db.delete(c); db.commit()
    return {"ok": True}