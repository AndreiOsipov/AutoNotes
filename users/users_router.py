from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm


from db import Users, get_session
from users.users import UserOut, UserCreate, get_password_hash, authenticate_user, create_access_token, Token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter()


# Регистрация
@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_session)):
    db_user = db.exec(select(Users).where(Users.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = Users(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Логин
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: Users = Depends(get_current_active_user)):
    return current_user