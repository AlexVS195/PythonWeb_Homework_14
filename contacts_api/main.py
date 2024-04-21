from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer
from sqlalchemy.orm import Session
from typing import List
from src.database.db import engine, get_db
from src.schemas import ContactCreate, Contact, UserModel, UserResponse, TokenModel
from crud import add_contact, get_contacts, get_contact, refresh_contact, remove_contact, get_upcoming_birthdays
from src.repository import users as repository_users
from src.services.auth import auth_service
from src.database.models import Base, User
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import smtplib
import cloudinary.uploader
import redis

# Redis configuration
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
USER_CACHE_KEY_PREFIX = "user:"
USER_CACHE_EXPIRE_SECONDS = 3600

# FastAPI application initialization
app = FastAPI()

# Database initialization
Base.metadata.create_all(bind=engine)

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify a list of allowed domains, if known
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to cache user data
async def get_user_from_cache_or_db(email: str, db_session: Session):
    """
    Get user data from cache or database.
    
    Args:
        email (str): The email of the user.
        db_session (Session): SQLAlchemy database session.

    Returns:
        str: Cached user data or user data from the database.
    """
    cached_user_data = redis_client.get(USER_CACHE_KEY_PREFIX + email)
    if cached_user_data:
        return cached_user_data
    user = await repository_users.get_user_by_email(email, db_session)
    redis_client.setex(USER_CACHE_KEY_PREFIX + email, USER_CACHE_EXPIRE_SECONDS, user)
    return user

# Signup route
@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserModel, db: Session = Depends(get_db)):
    """
    Signup route for creating a new user account.

    Args:
        body (UserModel): Request body containing user data.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Response containing user data and success message.
    """
    exist_user = await repository_users.get_user_by_email(body.email, db)
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    body.password = auth_service.get_password_hash(body.password)
    new_user = await repository_users.create_user(body, db)

    # Generating and sending email confirmation
    confirmation_link = f"http://example.com/confirm_email?token={new_user.email_verification_token}"
    send_confirmation_email(body.email, confirmation_link)

    return {"user": new_user, "detail": "User successfully created"}

# Login route
@app.post("/login", response_model=TokenModel)
async def login(body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login route for user authentication.

    Args:
        body (OAuth2PasswordRequestForm): Request body containing login credentials.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Response containing access token, refresh token, and token type.
    """
    user = await repository_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    # Generate JWT
    access_token = await auth_service.create_access_token(data={"sub": user.email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.email})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# HTTPBearer for authentication
security = HTTPBearer()

# Refresh token route
@app.get('/refresh_token', response_model=TokenModel)
async def refresh_token(credentials: HTTPAuthorizationCredentials = security, db: Session = Depends(get_db)):
    """
    Route for refreshing access token using refresh token.

    Args:
        credentials (HTTPAuthorizationCredentials): HTTP authorization credentials.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Response containing new access token, new refresh token, and token type.
    """
    token = credentials.credentials
    email = await auth_service.decode_refresh_token(token)
    user = await repository_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await repository_users.update_token(user, None, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth_service.create_access_token(data={"sub": email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": email})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# Route for updating user avatar
@app.put("/avatar", status_code=status.HTTP_200_OK)
async def update_avatar(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Route for updating user avatar.

    Args:
        file (UploadFile): Uploaded file containing the new avatar image.
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        dict: Response indicating the success of the avatar update.
    """
    # Upload file to Cloudinary
    response = cloudinary.uploader.upload(file.file)
    # Update user avatar URL in the database
    user = await repository_users.get_user_by_email(current_user.email, db)
    user.avatar = response["secure_url"]
    db.commit()
    return {"detail": "Avatar updated successfully"}

# Confirm email route
@app.get("/confirm_email")
async def confirm_email(token: str, db: Session = Depends(get_db)):
    """
    Route for confirming user email.

    Args:
        token (str): Confirmation token received via email.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Response indicating the success of the email confirmation.
    """
    if await repository_users.confirm_email(token, db):
        return {"detail": "Email confirmed successfully"}
    else:
        raise HTTPException(status_code=404, detail="Token not found or expired")

# Function to send confirmation email
def send_confirmation_email(email, confirmation_link):
    """
    Function to send confirmation email.

    Args:
        email (str): Email address of the recipient.
        confirmation_link (str): Link for confirming email address.
    """
    # Email configuration
    sender_email = "your_email@example.com"
    receiver_email = email
    password = "your_email_password"

    # Create email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Confirmation Email"

    # Message body
    body = f"Please click the following link to confirm your email address: {confirmation_link}"
    msg.attach(MIMEText(body, 'plain'))

    # Send email message through SMTP server
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)

# Create contact
@app.post("/contacts/", response_model=Contact, status_code=status.HTTP_201_CREATED)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(auth_service.get_current_user)):
    """
    Route for creating a new contact.

    Args:
        contact (ContactCreate): Contact data to be created.
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        dict: Response containing the created contact data.
    """
    return add_contact(db=db, contact=contact, user=current_user)

# Read contacts
@app.get("/contacts/", response_model=List[Contact])
def read_contacts(
    skip: int = 0, limit: int = 10, query: str = None, db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Route for reading contacts.

    Args:
        skip (int): Number of items to skip.
        limit (int): Maximum number of items to return.
        query (str): Query string for filtering contacts.
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        list: List of contacts.
    """
    return get_contacts(db=db, skip=skip, limit=limit, query=query, user=current_user)

# Read contact by ID
@app.get("/contacts/{contact_id}", response_model=Contact)
def read_contact(contact_id: int, db: Session = Depends(get_db), 
                 current_user: User = Depends(auth_service.get_current_user)):
    """
    Route for reading a contact by ID.

    Args:
        contact_id (int): ID of the contact to retrieve.
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        dict: Contact data.
    """
    db_contact = get_contact(db=db, contact_id=contact_id, user=current_user)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

# Update contact
@app.put("/contacts/{contact_id}", response_model=Contact)
def update_contact(contact_id: int, contact: ContactCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(auth_service.get_current_user)):
    """
    Route for updating a contact.

    Args:
        contact_id (int): ID of the contact to update.
        contact (ContactCreate): Updated contact data.
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        dict: Updated contact data.
    """
    db_contact = get_contact(db=db, contact_id=contact_id, user=current_user)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return refresh_contact(db=db, contact_id=contact_id, contact=contact, user=current_user)

# Delete contact
@app.delete("/contacts/{contact_id}", response_model=Contact)
def delete_contact(contact_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(auth_service.get_current_user)):
    """
    Route for deleting a contact.

    Args:
        contact_id (int): ID of the contact to delete.
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        dict: Deleted contact data.
    """
    db_contact = get_contact(db=db, contact_id=contact_id, user=current_user)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return remove_contact(db=db, contact_id=contact_id, user=current_user)

# Get contacts with upcoming birthdays
@app.get("/contacts/upcoming_birthdays/", response_model=List[Contact])
def get_upcoming_birthdays_list(db: Session = Depends(get_db),
                                current_user: User = Depends(auth_service.get_current_user)):
    """
    Route for retrieving contacts with upcoming birthdays.

    Args:
        db (Session): SQLAlchemy database session.
        current_user (User): Current authenticated user.

    Returns:
        list: List of contacts with upcoming birthdays.
    """
    return get_upcoming_birthdays(db=db, user=current_user)
