import time

import httpx


BASE_URL = "http://localhost:8000"


def main() -> None:
    for _ in range(30):
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(1)
    else:
        raise SystemExit("API is not available")

    login = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "writer@example.com", "password": "Password123!"},
        timeout=5,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    chats = httpx.get(f"{BASE_URL}/api/chats", headers=headers, timeout=5)
    chats.raise_for_status()
    chat_id = chats.json()[0]["id"]

    message = httpx.post(
        f"{BASE_URL}/api/chats/{chat_id}/messages",
        headers=headers,
        json={"body": "Smoke test message"},
        timeout=5,
    )
    message.raise_for_status()

    search = httpx.get(
        f"{BASE_URL}/api/messages/search",
        headers=headers,
        params={"q": "Smoke"},
        timeout=5,
    )
    search.raise_for_status()
    assert search.json(), "Search returned no messages"
    print("Smoke test passed")


if __name__ == "__main__":
    main()

