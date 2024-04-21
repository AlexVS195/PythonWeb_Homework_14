from libgravatar import Gravatar
from sqlalchemy.orm import Session
from src.database.models import User
from src.schemas import UserModel


async def get_user_by_email(email: str, db: Session) -> User:
    """
    Retrieve a user by email from the database.

    Args:
        email (str): User's email.
        db (Session): Database session.

    Returns:
        User: User object from the database or None if user not found.
    """
    return db.query(User).filter(User.email == email).first()


async def create_user(body: UserModel, db: Session) -> User:
    """
    Create a new user in the database.

    Args:
        body (UserModel): New user data.
        db (Session): Database session.

    Returns:
        User: New user object.
    """
    avatar = None
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as e:
        print(e)
    new_user = User(**body.dict(), avatar=avatar)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


async def update_token(user: User, token: str | None, db: Session) -> None:
    """
    Update the refresh token for a user in the database.

    Args:
        user (User): User object.
        token (str | None): Refresh token. If None, the token is removed.
        db (Session): Database session.

    Returns:
        None
    """
    user.refresh_token = token
    db.commit()


async def confirm_email(token: str, db: Session):
    """
    Confirm a user's email.

    Args:
        token (str): Email confirmation token.
        db (Session): Database session.

    Returns:
        bool: Returns True if confirmation is successful, and False otherwise.
    """
    user = db.query(User).filter(User.email == token).first()
    if user:
        user.email_verified = True
        db.commit()
        return True
    return False