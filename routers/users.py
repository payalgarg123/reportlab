import sys
sys.path.append('c:\\Users\\payal\\Desktop\\reportlab')
from fastapi import FastAPI, Depends, HTTPException, Path, APIRouter, status
from pydantic import BaseModel, Field
from starlette import status
from models import Users
from database import SessionLocal
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from routers.auth import get_current_user
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

router = APIRouter(
    prefix='/users',
    tags=['users']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(min_length=10, max_length=50)
    first_name: str = Field(min_length=2, max_length=15)
    last_name: str = Field(min_length=2, max_length=15)
    password: str = Field(min_length=8, max_length=20)
    phone_number: Optional[str] = Field(min_length=10, max_length=15)

    class Config:
        json_schema_extra = {
            'example': {
                'username': 'unique_username',
                'email': 'unique_email@domain.com',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'password': 'password_min8_max20_',
                'phone_number': 'min10_max15_Opt',
            }
        }


class UserVerification(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=20)
    new_password_retype: str = Field(min_length=8, max_length=20)

    class Config:
        json_schema_extra = {
            'example': {
                'current_password': 'current_password',
                'new_password': 'new_password',
                'new_password_retype': 'new_password'
            }
        }


class UserRoleUpdate(BaseModel):
    new_role_requested: str = Field(min_length=3, max_length=20)

    class Config:
        json_schema_extra = {
            'example': {
                'new_role_requested': 'new_role_requested',
            }
        }


class UserInfoUpdate(BaseModel):
    username: Optional[str] = Field(min_length=3, max_length=20)
    email: Optional[str] = Field(min_length=10, max_length=50)
    first_name: Optional[str] = Field(min_length=2, max_length=15)
    last_name: Optional[str] = Field(min_length=2, max_length=15)
    phone_number: Optional[str] = Field(min_length=10, max_length=15)

    class Config:
        json_schema_extra = {
            'example': {
                'username': 'unique_username',
                'email': 'unique_email@domain.com',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'phone_number': 'phone_number'
            }
        }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    with db.begin():
    # Check if username or email already exists
        if db.query(Users).filter(Users.username == create_user_request.username).first() or db.query(Users).filter(
            Users.email == create_user_request.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists!")

        try:
            create_user_model = Users(
            username=create_user_request.username,
            email=create_user_request.email,
            first_name=create_user_request.first_name,
            last_name=create_user_request.last_name,
            phone_number=create_user_request.phone_number,
            hashed_password=bcrypt_context.hash(create_user_request.password),
            is_active=True
        )
            db.add(create_user_model)
            db.commit()

        except IntegrityError as e:
        # Handle other types of IntegrityError or log the error
            print("An error occurred:", str(e))
            db.rollback()
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/", status_code=status.HTTP_200_OK)
async def get_user(user: user_dependency, db: db_dependency):
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if user is None or not user_model.is_active:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Users).filter(Users.id == user.get('id')).all()


@router.put("/change_password/", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if user is None or not user_model.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user!!')

    if not bcrypt_context.verify(user_verification.current_password, user_model.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Current password does not match!!')

    if user_verification.new_password != user_verification.new_password_retype:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Provided New Password in both the'
                                                                                     'fields does not match, please try'
                                                                                     'again!!')

    user_model.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.add(user_model)
    db.commit()


@router.put("/update_info/", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_info(user: user_dependency, db: db_dependency, user_info_update: UserInfoUpdate):
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if user is None or not user_model.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user!!')

    # Check if at least one piece of information is changed
    if any(getattr(user_info_update, field) is not None and getattr(user_info_update, field) != getattr(user_model,
                                                                                                        field)
           for field in UserInfoUpdate.__annotations__):

        # Check if the new username already exists
        if db.query(Users).filter(Users.username == user_info_update.username).first() or db.query(Users).filter(
                Users.email == user_info_update.email).first():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username or email already "
                                                                                         "exists!")

        # Update only the fields that are different and not None
        for field in UserInfoUpdate.__annotations__:
            new_value = getattr(user_info_update, field)
            if new_value is not None and new_value != getattr(user_model, field):
                setattr(user_model, field, new_value)

        db.add(user_model)
        db.commit()
    else:
        # No information changed
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Nothing changed! same/unsupported items!')


@router.post("/new_role_request/", status_code=status.HTTP_201_CREATED)
async def new_role_request(user: user_dependency, db: db_dependency, user_role_update: UserRoleUpdate):
    # Check if the user is active and has the role 'b2c'
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    # if user is None or not user_model.is_active or user_model.role != "b2c":
    if user is None or not user_model.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user!!')

    # Update the user's role to 'client/hospital/CRM/sales/lab/approver/etc'
    if user_model.role != user_role_update.new_role_requested:
        user_model.new_role_requested = user_role_update.new_role_requested
        user_model.new_role_request_pending = True
        db.add(user_model)
        db.commit()
        return {"message": "Application to change the role is submitted for approval"}
    else:
        return {"message": "Application to change the role is not valid! Already have same role"}
