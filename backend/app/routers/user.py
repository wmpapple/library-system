# app/routers/User.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_current_user, get_unprotected_db_dependency
from ..security import create_access_token

router = APIRouter(tags=["User"])

# === 配置: 管理员注册密钥 ===
# 在这里硬编码一个密钥，只有知道这个密钥的人才能注册管理员
from ..config import ADMIN_REGISTRATION_SECRET

@router.post("/user/register", response_model=schemas.UserRead)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_unprotected_db_dependency)):
    # 1. 如果尝试注册管理员角色，必须验证 Token
    if user.role == schemas.RoleEnum.ADMIN:
        if user.admin_token != ADMIN_REGISTRATION_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="管理员注册密钥错误 (Invalid Admin Token)"
            )
    # 2. 调用 CRUD 创建用户
    try:
        created = crud.create_user(db, user, db_key="MySQL")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return created


@router.post("/user/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_unprotected_db_dependency)):
    db_user = crud.authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.username, "db_key": user.db_key})
    return schemas.Token(access_token=token)


@router.get("/users/me", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user