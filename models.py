from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index, CheckConstraint

# Base User Model
class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(15), nullable=False)
    last_name = Column(String(15), nullable=False)
    hashed_password = Column(String(200))
    is_active = Column(Boolean, default=True)
    role = Column(String(10), default='b2c')
    new_role_requested = Column(String(10), nullable=True)
    new_role_request_pending = Column(Boolean, default=False)
    phone_number = Column(String(15))

    # Add constraints to enforce minimum lengths
    __table_args__ = (
        Index('idx_username', 'username', unique=True),
        Index('idx_email', 'email', unique=True),
        CheckConstraint('LENGTH(email) >= 10', name='check_email_length'),
        CheckConstraint('LENGTH(username) >= 3', name='check_username_length'),
        CheckConstraint('LENGTH(first_name) >= 2', name='check_first_name_length'),
        CheckConstraint('LENGTH(last_name) >= 2', name='check_last_name_length'),
        CheckConstraint('LENGTH(phone_number) >= 3', name='check_phone_number_length'),
    )

    # Add a relationship to the ClientInfo model with ondelete='SET NULL'
    client_info = relationship("ClientInfo", back_populates="user", cascade="all, delete-orphan")
    # Add a relationship to the PartnerInfo model with ondelete='SET NULL'
    partner_info = relationship("PartnerInfo", back_populates="user", cascade="all, delete-orphan")


# ClientInfo Model
class ClientInfo(Base):
    __tablename__ = 'client_info'

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(5), unique=True, nullable=False)
    company_short_name = Column(String(10), unique=True, nullable=False)
    company_full_name = Column(String(50), nullable=False)
    company_email = Column(String(50), nullable=False)
    company_phone = Column(String(15), nullable=False)
    company_website = Column(String(30))
    company_address = Column(String(100))
    currency_type = Column(String(3), nullable=False, default='USD')  # INR, USD, KRW

    # User ID as ForeignKey with ondelete='SET NULL'
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    user = relationship("Users", back_populates="client_info")


    # Add constraints to enforce minimum lengths
    __table_args__ = (
        Index('idx_client_id', 'client_id', unique=True),
        CheckConstraint('LENGTH(company_short_name) >= 4', name='check_client_company_short_name_length'),
        CheckConstraint('LENGTH(company_full_name) >= 10', name='check_client_company_full_name_length'),
        CheckConstraint('LENGTH(company_email) >= 10', name='check_client_company_email_length'),
        CheckConstraint('LENGTH(company_phone) >= 10', name='check_client_company_phone_length'),
        CheckConstraint('LENGTH(company_website) >= 5', name='check_client_company_website_length'),
        CheckConstraint('LENGTH(company_address) >= 10', name='check_client_company_address_length'),
    )


# PartnerInfo Model
class PartnerInfo(Base):
    __tablename__ = 'partner_info'

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(String(10), nullable=False)
    company_short_name = Column(String(20), unique=True, nullable=False)
    company_full_name = Column(String(50), nullable=False)
    company_email = Column(String(50), nullable=False)
    company_phone = Column(String(15), nullable=False)
    company_website = Column(String(30))
    company_address = Column(String(100))
    bill_to = Column(String(10), nullable=False, server_default='client')  # 'client' or 'partner'
    currency_type = Column(String(3), nullable=True)  # INR, USD, KRW, Nullable
    client_id = Column(String(6), ForeignKey('client_info.client_id', ondelete='SET NULL'))  # Added client_id

    # User ID as ForeignKey with ondelete='SET NULL'
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    user = relationship("Users", back_populates="partner_info")

    # Add constraints to enforce minimum lengths
    __table_args__ = (
        CheckConstraint("((bill_to = 'partner' AND currency_type IS NOT NULL) OR (bill_to = 'client' AND "
                        "currency_type IS NULL))", name='check_currency_type'),
        CheckConstraint('LENGTH(company_short_name) >= 4', name='check_partner_company_short_name_length'),
        CheckConstraint('LENGTH(company_full_name) >= 10', name='check_partner_company_full_name_length'),
        CheckConstraint('LENGTH(company_email) >= 10', name='check_partner_company_email_length'),
        CheckConstraint('LENGTH(company_phone) >= 3', name='check_partner_company_phone_length'),
        CheckConstraint('LENGTH(company_website) >= 5', name='check_partner_company_website_length'),
        CheckConstraint('LENGTH(company_address) >= 10', name='check_partner_company_address_length'),
    )
