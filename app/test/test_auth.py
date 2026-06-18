"""Tests del módulo de autenticación."""

import pytest
from fastapi import status


class TestRegister:
    def test_register_ok(self, client, normal_user_data):
        """POST /user/ con datos válidos → 201 + UserResponse."""
        resp = client.post("/user/", json=normal_user_data)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["email"] == normal_user_data["email"]
        assert "id" in data


class TestLogin:
    def test_login_ok(self, client, normal_user):
        """POST /auth/login con credenciales válidas → 200 + cookie + mensaje."""
        resp = client.post(
            "/auth/login",
            data={"username": normal_user["email"], "password": "TestPass123!"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "access_token" in resp.cookies
        assert "refresh_token" in resp.cookies
        assert resp.cookies["access_token"] is not None
        assert resp.cookies["refresh_token"] is not None
        assert resp.json() == {"message": "Login exitoso. Sesión iniciada"}

    def test_login_invalid_credentials(self, client, normal_user_data):
        """POST /auth/login con password incorrecto → 401."""
        client.post("/user/", json=normal_user_data)

        resp = client.post(
            "/auth/login",
            data={
                "username": normal_user_data["email"],
                "password": "wrong_password",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutRevocation:
    def test_logout_revocation(self, client, normal_user):
        """Token inválido no accede a endpoint protegido."""
        login_resp = client.post(
            "/auth/login",
            data={"username": normal_user["email"], "password": "TestPass123!"},
        )
        assert login_resp.status_code == status.HTTP_200_OK
        cookie = login_resp.cookies["access_token"]

        # Con token válido → funciona
        resp = client.get("/profile/me", headers={"Cookie": f"access_token={cookie}"})
        assert resp.status_code == status.HTTP_200_OK

        # Sin token → 401
        resp = client.get("/profile/me")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

        # Token inválido → 401
        resp = client.get(
            "/profile/me", headers={"Cookie": "access_token=token_invalido"}
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestRateLimit:
    def test_rate_limit_auth(self, client, normal_user):
        """4 requests a /auth/login: los 3 primeros OK, el 4to 429."""
        for i in range(3):
            resp = client.post(
                "/auth/login",
                data={
                    "username": normal_user["email"],
                    "password": "TestPass123!",
                },
            )
            assert (
                resp.status_code == status.HTTP_200_OK
            ), f"Intento {i + 1} falló: {resp.text}"

        resp = client.post(
            "/auth/login",
            data={"username": normal_user["email"], "password": "TestPass123!"},
        )
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
