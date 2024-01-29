import sys
sys.path.append('c:\\Users\\payal\\Desktop\\reportlab')
from fastapi import FastAPI, Depends, HTTPException, Path, APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from starlette import status
from models import Users, ClientInfo, PartnerInfo
from database import SessionLocal
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from routers.auth import get_current_user
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
import re
from routers.Allowed_roles_checker import partner_creation_role_check,client_creation_role_check

router = APIRouter(
    prefix='/client',
    tags=['client']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class CreateClientRequest(BaseModel):
    company_short_name: str = Field(min_length=4, max_length=10)
    company_full_name: str = Field(min_length=10, max_length=50)
    company_email: str = Field(min_length=10, max_length=50)
    company_phone: str = Field(min_length=10, max_length=15)
    company_website: str = Field(min_length=5, max_length=30)
    company_address: str = Field(min_length=10, max_length=100)
    currency_type: Optional[str] = Field(min_length=3, max_length=3, default='USD')

    class Config:
        json_schema_extra = {
            'example': {
                'company_short_name': 'unique_name',
                'company_full_name': 'unique_email@domain.com',
                'company_email': 'company@email.com',
                'company_phone': 'min10_max15_Opt',
                'company_website': 'www.mygenomebox.com',
                'company_address': 'Company Address for Invoice and White Label Report',
                'currency_type': 'USD|INR|KRW',
            }
        }


class CreatePartnerRequest(BaseModel):
    partner_username: str = Field(min_length=3, max_length=20)
    company_short_name: str = Field(min_length=4, max_length=10)
    company_full_name: str = Field(min_length=10, max_length=50)
    company_email: str = Field(min_length=10, max_length=50)
    company_phone: str = Field(min_length=10, max_length=15)
    company_website: str = Field(min_length=5, max_length=30)
    company_address: str = Field(min_length=10, max_length=100)
    bill_to: str = Field(max_length=10)
    currency_type: Optional[str] = Field(min_length=3, max_length=3, default='USD')

    class Config:
        json_schema_extra = {
            'example': {
                'partner_username': 'partner_username_in_reportlab',
                'company_short_name': 'unique_name',
                'company_full_name': 'unique_email@domain.com',
                'company_email': 'company@email.com',
                'company_phone': 'min10_max15_Opt',
                'company_website': 'www.mygenomebox.com',
                'company_address': 'Company Address for Invoice and White Label Report',
                'bill_to': 'client|partner',
                'currency_type': 'USD|INR|KRW',
            }
        }


@router.post("/create_client_info/", status_code=status.HTTP_201_CREATED)
async def create_client_info(user: user_dependency, db: db_dependency, create_client_request: CreateClientRequest):
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if user is None or not user_model.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user!!')
    if not client_creation_role_check.is_role_allowed(user_model.role):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="You don't seems to have appropriate permission, please contact the admin!!")

    # Check if the user already registered as a client
    existing_client = db.query(ClientInfo).filter(ClientInfo.owner_id == user.get('id')).first()
    if existing_client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already registered as client!")

    # Check if client's company short name already exists
    if db.query(ClientInfo).filter(ClientInfo.company_short_name == create_client_request.company_short_name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company Short Name already exists!")

    try:
        # Get the total count of entries in the ClientInfo table
        total_entries = db.query(func.count(ClientInfo.id)).scalar()
        # Generate the custom client ID based on the total count
        new_id = total_entries + 1
        client_id_pattern = "C{:04d}".format(new_id)

        create_client_request_model = ClientInfo(
            client_id=client_id_pattern,
            company_short_name=create_client_request.company_short_name,
            company_full_name=create_client_request.company_full_name,
            company_email=create_client_request.company_email,
            company_phone=create_client_request.company_phone,
            company_website=create_client_request.company_website,
            company_address=create_client_request.company_address,
            currency_type=create_client_request.currency_type,
            owner_id=user.get('id')
        )
        db.add(create_client_request_model)
        db.commit()
        return {"message": "Client registration successful!!"}

    except IntegrityError as e:
        # Handle other types of IntegrityError or log the error
        print("An error occurred:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/create_partner_info/", status_code=status.HTTP_201_CREATED)
async def create_partner_info(user: user_dependency, db: db_dependency, create_partner_request: CreatePartnerRequest):
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if user is None or not user_model.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user!!')

    # allowed_roles_pattern = re.compile(r"client|admin", re.IGNORECASE)
    if not partner_creation_role_check.is_role_allowed(user_model.role):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="You don't seems to have appropriate permission, please contact the admin!!")

    # Fetch user_id of partner
    partner_user_model = db.query(Users).filter(Users.username == create_partner_request.partner_username).first()
    if partner_user_model is None:
        raise HTTPException(status_code=404, detail="No user found with the provided partner_username")
    partner_owner_id = partner_user_model.id

    # Fetch client_id
    client_info_m = db.query(ClientInfo).filter(ClientInfo.owner_id == user.get('id')).first()
    if client_info_m is None:
        raise HTTPException(status_code=404, detail="Please add client detail using the client/create_client_info "
                                                    "end-point before trying to add a partner")
    client_id = client_info_m.client_id

    # Check of the user is already registered as partner by the same client
    partner_table_check = db.query(PartnerInfo).filter(PartnerInfo.client_id == client_id,
                                                       PartnerInfo.owner_id == partner_owner_id).first()
    if partner_table_check:
        raise HTTPException(status_code=404, detail="User is already registered as partner by the client")

    # Check if user is already registered by any client, then use the same partner_id
    partner_table_check2 = db.query(PartnerInfo).filter(PartnerInfo.owner_id == partner_owner_id).first()
    if partner_table_check2:
        partner_id_pattern = partner_table_check2.partner_id
        print(partner_id_pattern)
    else:
        # Get the last available ID in the ClientInfo table
        last_id = db.query(func.max(PartnerInfo.id)).scalar()
        print("I am here" + str(last_id))
        new_id = last_id + 1 if last_id is not None else 1
        # Generate the custom client ID based on the last available ID
        partner_id_pattern = "P{:04d}".format(new_id)

    # Check if partner's company short name already exists
    if db.query(PartnerInfo).filter(
            PartnerInfo.company_short_name == create_partner_request.company_short_name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Partner company Short Name already exists!")

    try:
        # Conditionally set currency_type to None if bill_to is "client"
        currency_type = create_partner_request.currency_type if create_partner_request.bill_to == "partner" else None

        create_partner_request_model = PartnerInfo(
            partner_id=partner_id_pattern,
            company_short_name=create_partner_request.company_short_name,
            company_full_name=create_partner_request.company_full_name,
            company_email=create_partner_request.company_email,
            company_phone=create_partner_request.company_phone,
            company_website=create_partner_request.company_website,
            company_address=create_partner_request.company_address,
            bill_to=create_partner_request.bill_to,
            client_id=client_id,
            currency_type=currency_type,
            owner_id=partner_owner_id
        )
        db.add(create_partner_request_model)
        db.commit()
        return {"message": "Partner registration successful!!"}

    except IntegrityError as e:
        # Handle other types of IntegrityError or log the error
        print("An error occurred:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
