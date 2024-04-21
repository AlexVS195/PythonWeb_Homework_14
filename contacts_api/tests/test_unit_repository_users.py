import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock, patch 
from sqlalchemy.orm import Session
from libgravatar import Gravatar
from src.database.models import User
from src.schemas import UserModel
from src.repository.users import get_user_by_email, create_user, update_token, confirm_email


class TestUsers(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.session = MagicMock(spec=Session)

    async def test_get_user_by_email_found(self):
        # Test if user is found by email
        user = User(email="test@example.com")
        self.session.query().filter().first.return_value = user
        result = await get_user_by_email(email="test@example.com", db=self.session)
        self.assertEqual(result, user)

    async def test_get_user_by_email_not_found(self):
        # Test if user is not found by email
        self.session.query().filter().first.return_value = None
        result = await get_user_by_email(email="test@example.com", db=self.session)
        self.assertIsNone(result)

    async def test_create_user_with_gravatar(self):
        # Test creating a user with Gravatar
        body = UserModel(username="test_user", email="test@example.com", password="test_password")
        gravatar_mock = MagicMock(spec=Gravatar)
        gravatar_mock.get_image.return_value = "http://example.com/avatar.jpg"
        with patch("src.repository.users.Gravatar", return_value=gravatar_mock): 
            result = await create_user(body=body, db=self.session)
            self.assertEqual(result.email, body.email)
            self.assertEqual(result.avatar, "http://example.com/avatar.jpg")

    async def test_create_user_without_gravatar(self):
        # Test creating a user without Gravatar
        body = UserModel(username="test_user", email="test@example.com", password="test_password")
        gravatar_mock = MagicMock(spec=Gravatar)
        gravatar_mock.get_image.side_effect = Exception("Gravatar not available")
        with patch("src.repository.users.Gravatar", return_value=gravatar_mock): 
            result = await create_user(body=body, db=self.session)
            self.assertEqual(result.email, body.email)
            self.assertIsNone(result.avatar)

    async def test_update_token(self):
        # Test updating user token
        user = User()
        token = "test_token"
        await update_token(user=user, token=token, db=self.session)
        self.assertEqual(user.refresh_token, token)
        self.session.commit.assert_called_once()

    async def test_confirm_email_success(self):
        # Test confirming user email successfully
        token = "test@example.com"
        user = User(email="test@example.com")
        self.session.query().filter().first.return_value = user
        result = await confirm_email(token=token, db=self.session)
        self.assertTrue(result)
        self.assertTrue(user.email_verified)
        self.session.commit.assert_called_once()

    async def test_confirm_email_failure(self):
        # Test failing to confirm user email
        token = "test@example.com"
        self.session.query().filter().first.return_value = None
        result = await confirm_email(token=token, db=self.session)
        self.assertFalse(result)
        self.session.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()