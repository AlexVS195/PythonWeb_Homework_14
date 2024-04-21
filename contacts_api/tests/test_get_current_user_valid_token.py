import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.services.auth import Auth
from fastapi import HTTPException
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from src.repository import users as repository_users

async def test_get_current_user_valid_token():
    # Arrange
    auth_service = Auth()
    token = "valid_access_token"
    db_mock = MagicMock(spec=Session)
    payload = {
        "sub": "test_user@example.com",
        "scope": "access_token"
    }
    Auth.decode_refresh_token = MagicMock(return_value=payload)
    repository_users.get_user_by_email = MagicMock(return_value="test_user")

    # Act
    user = await auth_service.get_current_user(token=token, db=db_mock)

    # Assert
    assert user == "test_user"

async def test_get_current_user_invalid_token():
    # Arrange
    auth_service = Auth()
    token = "invalid_access_token"
    db_mock = MagicMock(spec=Session)
    payload = {
        "scope": "access_token"
    }
    Auth.decode_refresh_token = MagicMock(return_value=payload)
    repository_users.get_user_by_email = MagicMock(return_value=None)

    # Act & Assert
    try:
        await auth_service.get_current_user(token=token, db=db_mock)
    except HTTPException as e:
        assert e.status_code == 401
        assert e.detail == "Could not validate credentials"
