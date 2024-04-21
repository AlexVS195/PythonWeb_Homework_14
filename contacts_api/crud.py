from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from libgravatar import Gravatar
from datetime import datetime, timedelta
from src.database.models import Contact, User
from src.schemas import ContactCreate, UserModel


def add_contact(db: Session, contact: ContactCreate, user: User):
    db_contact = Contact(**contact.model_dump(), user_id=user.id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def get_contact(db: Session, contact_id: int, user: User):
    return db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()


def get_contacts(db: Session,  user: User, skip: int = 0, limit: int = 10, query: str = None):
    if query:
        return db.query(Contact).filter(
            or_(
                Contact.first_name.ilike(f"%{query}%"),
                Contact.last_name.ilike(f"%{query}%"),
                Contact.email.ilike(f"%{query}%")
            )
        ).offset(skip).limit(limit).all()
    return db.query(Contact).filter(Contact.user_id == user.id).offset(skip).limit(limit).all()


def refresh_contact(db: Session, user: User, contact_id: int, contact: ContactCreate):
    db_contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()
    for key, value in contact.model_dump().items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def remove_contact(db: Session, contact_id: int, user: User):
    db_contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()
    db.delete(db_contact)
    db.commit()
    return db_contact

def get_upcoming_birthdays(db: Session, user: User):
    today = datetime.now().date()
    end_date = today + timedelta(days=7)
    return db.query(Contact).filter(
        func.extract('month', Contact.birthday) == today.month,
        func.extract('day', Contact.birthday) >= today.day,
    ).union(
        db.query(Contact).filter(
            func.extract('month', Contact.birthday) == end_date.month,
            func.extract('day', Contact.birthday) <= end_date.day,
        )
    ).filter(
        Contact.user_id == user.id
    ).all()

async def get_user_by_email(email: str, db: Session, user: User) -> User:
    return db.query(User).filter(User.email == email, Contact.user_id == user.id).first()

async def create_user(body: UserModel, db: Session, user: User) -> User:
    avatar = None
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as e:
        print(e)
    new_user = User(**body.model_dump(), avatar=avatar) # dict don't work 
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user