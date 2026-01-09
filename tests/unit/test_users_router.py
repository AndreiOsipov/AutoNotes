import pytest

from fastapi import status
from sqlmodel import Session

from db import User

from users.users import get_password_hash
from tests.test_db import engine_test


def create_user_in_db(username: str, password: str):
    with Session(engine_test) as session:
        user = User(username=username, hashed_password=get_password_hash(password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_register_success(client):
    response = client.post(
        "/register",
        json={"username": "user1", "password": "secret"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "user1"
    assert "id" in data


def test_register_duplicate_username(client):
    # первый пользователь
    client.post(
        "/register",
        json={"username": "dupuser", "password": "secret"},
    )
    # второй с тем же username
    response = client.post(
        "/register",
        json={"username": "dupuser", "password": "secret2"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"] == "Username already registered"


def test_login_success(client):
    username = "loginuser"
    password = "secret"
    create_user_in_db(username, password)

    response = client.post(
        "/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    username = "wrongpassuser"
    password = "secret"
    create_user_in_db(username, password)

    response = client.post(
        "/token",
        data={"username": username, "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["detail"] == "Incorrect username or password"


def test_login_nonexistent_user(client):
    response = client.post(
        "/token",
        data={"username": "no_such_user", "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["detail"] == "Incorrect username or password"


def test_users_me_authorized(client):
    username = "meuser"
    password = "secret"
    create_user_in_db(username, password)

    token_resp = client.post(
        "/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = token_resp.json()["access_token"]

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == username


def test_users_me_unauthorized(client):
    response = client.get("/users/me")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )
