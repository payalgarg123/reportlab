from fastapi import FastAPI, Depends, HTTPException, Path, APIRouter, Query
from starlette import status
import sys
sys.path.append('c:\\Users\\payal\\Desktop\\reportlab')
from models import Users, ClientInfo, PartnerInfo
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from routers.auth import get_current_user
from cachetools import TTLCache
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix='/admin',
    tags=['admin']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# Define a cache with a time-to-live (TTL) of 60 seconds
cache = TTLCache(maxsize=100, ttl=60)


@router.get("/users", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency, skip: int = Query(0, alias="page", ge=0),
                   limit: int = Query(10, le=100)):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')

    # Calculate the offset based on the page and limit
    offset = skip * limit
    # Check if the result is in the cache
    cache_key = f"todos:{offset}:{limit}"
    cached_users = cache.get(cache_key)
    if cached_users:
        return cached_users
    # Fetch paginated todos from the database
    users = db.query(Users).offset(offset).limit(limit).all()
    # Store the result in the cache with the cache key and TTL
    cache[cache_key] = users
    return users

'''
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    user_model = db.query(Users).filter(Users.id == user_id).first()

    if user_model is None:
        raise HTTPException(status_code=404, detail='user not found!!')
    db.query(Users).filter(Users.id == user_id).delete()
    db.commit()
'''


@router.put("/users/deactivate/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def user_deactivate(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    user_model = db.query(Users).filter(Users.id == user_id).first()

    if user_model is None:
        raise HTTPException(status_code=404, detail='user not found!!')
    user_model.is_active = False
    db.add(user_model)
    db.commit()


@router.put("/users/activate/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def user_activate(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')

    user_model = db.query(Users).filter(Users.id == user_id).first()
    if user_model is None:
        raise HTTPException(status_code=404, detail='user not found!!')
    user_model.is_active = True
    db.add(user_model)
    db.commit()


# Endpoint to approve user's new_role_request
@router.put("/approve_new_role/{user_id}")
async def approve_new_role(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')

    user_model = db.query(Users).filter(Users.id == user_id).first()
    if user_model is None:
        raise HTTPException(status_code=404, detail='user not found!!')
    if user_model.new_role_request_pending:
        user_model.role = user_model.new_role_requested
        user_model.new_role_requested = None
        user_model.new_role_request_pending = False
        db.add(user_model)
        db.commit()
        return JSONResponse(content={"message": "user's role updated successfully"}, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(content={"message": "User's role change request not found, please raise the request again "
                                                "using new_role_request endpoint!!"}, status_code=status.HTTP_200_OK)


