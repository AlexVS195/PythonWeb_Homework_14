import pytest
import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import status
from httpx import AsyncClient
from main import app



@pytest.mark.asyncio
async def test_failed_authentication():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Намірено передаємо невірні дані аутентифікації
        response = await client.post(
            "/api/auth/login",
            data={"username": "incorrect_username", "password": "incorrect_password"},
        )
        # Перевіряємо, що відповідь має код 401 (неспівпадіння аутентифікації)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Перевіряємо, що в тілі відповіді міститься відповідне повідомлення про помилку
        assert response.json() == {"detail": "Could not validate credentials"}