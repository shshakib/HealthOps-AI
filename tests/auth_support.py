"""Existing workflow tests sign in through the real session endpoint."""

from fastapi.testclient import TestClient as BaseClient

from healthops.auth import NewUser

PASSWORD = "isolated-test-account-password"


class TestClient(BaseClient):
    __test__ = False

    def __enter__(self):
        super().__enter__()
        if not self.app.state.auth.users():
            self.app.state.auth.create_user(
                NewUser(username="test-admin", password=PASSWORD, role="admin"), bootstrap=True
            )
        response = self.post(
            "/api/v1/auth/login", json={"username": "test-admin", "password": PASSWORD}
        )
        assert response.status_code == 200
        return self

    def request(self, method, url, **kwargs):
        if kwargs.get("headers") is None:
            kwargs["headers"] = {"X-HealthOps-Request": "1"}
        return super().request(method, url, **kwargs)
