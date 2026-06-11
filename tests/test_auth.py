def test_login_me_refresh_logout(client):
    login_response = client.post("/api/v1/auth/login", json={"email": "teacher@example.com", "password": "secret123"})
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]

    me_response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {payload['access_token']}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "teacher@example.com"

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"] != payload["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_response.json()["refresh_token"]})
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out successfully."
