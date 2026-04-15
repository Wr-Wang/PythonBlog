"""社区关系接口：作者关注。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthorFollow, User

router = APIRouter(prefix="/api/social", tags=["social"])


class FollowAuthorIn(BaseModel):
    user_key: str = Field(min_length=4, max_length=128)
    author_id: int = Field(ge=1)


@router.get("/follows/authors")
def list_followed_authors(
    user_key: str,
    db: Annotated[Session, Depends(get_db)],
):
    rows = db.query(AuthorFollow.author_id).filter(AuthorFollow.user_key == user_key).all()
    return {"items": [int(r[0]) for r in rows]}


@router.post("/follows/authors")
def follow_author(
    body: FollowAuthorIn,
    db: Annotated[Session, Depends(get_db)],
):
    if db.query(User.id).filter(User.id == body.author_id).first() is None:
        raise HTTPException(status_code=404, detail="作者不存在")
    row = (
        db.query(AuthorFollow)
        .filter(AuthorFollow.user_key == body.user_key, AuthorFollow.author_id == body.author_id)
        .first()
    )
    if row is None:
        db.add(AuthorFollow(user_key=body.user_key, author_id=body.author_id))
        db.commit()
    return {"ok": True, "author_id": body.author_id, "followed": True}


@router.post("/follows/authors/unfollow")
def unfollow_author(
    body: FollowAuthorIn,
    db: Annotated[Session, Depends(get_db)],
):
    row = (
        db.query(AuthorFollow)
        .filter(AuthorFollow.user_key == body.user_key, AuthorFollow.author_id == body.author_id)
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return {"ok": True, "author_id": body.author_id, "followed": False}
