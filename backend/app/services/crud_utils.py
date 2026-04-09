"""通用 CRUD 小工具：减少路由重复样板代码。"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session


def get_by_id_or_404(db: Session, model, id_value: int, detail: str):
    row = db.query(model).filter(model.id == id_value).first()
    if row is None:
        raise HTTPException(status_code=404, detail=detail)
    return row


def ensure_unique_field(db: Session, model, field_name: str, value: str, detail: str, exclude_id: int | None = None) -> None:
    field = getattr(model, field_name)
    q = db.query(model).filter(field == value)
    if exclude_id is not None:
        q = q.filter(model.id != exclude_id)
    if q.first() is not None:
        raise HTTPException(status_code=400, detail=detail)


def apply_updates(obj, data: dict) -> None:
    for k, v in data.items():
        setattr(obj, k, v)


def commit_and_refresh(db: Session, obj) -> None:
    db.commit()
    db.refresh(obj)


def delete_and_commit(db: Session, obj) -> None:
    db.delete(obj)
    db.commit()
