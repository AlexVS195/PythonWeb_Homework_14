import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app
from src.database.models import User
from src.services.auth import Auth
from src.database.db import get_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_create_user(client, monkeypatch):
    mock_send_email = MagicMock()
    monkeypatch.setattr("src.services.auth.send_email", mock_send_email)

    response = client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "password"},
    )
    assert response.status_code == 201
    assert mock_send_email.called

def test_repeat_create_user(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "password"},
    )
    assert response.status_code == 400


def test_login_user_not_confirmed(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "password"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email not confirmed"


def test_login_user(client, db: Session):
    user = User(email="test@example.com")
    db.add(user)
    db.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "password"},
    )
    assert response.status_code == 200


def test_login_wrong_password(client, db: Session):
    user = User(email="test@example.com")
    db.add(user)
    db.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "wrong_password"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_wrong_email(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "wrong_email@example.com", "password": "password"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"