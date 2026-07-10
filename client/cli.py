import argparse
import asyncio
import json
from pathlib import Path

import httpx
import websockets

BASE_URL = "http://localhost:8000"
TOKEN_FILE = Path.home() / ".messenger_case_token"


def save_token(token: str) -> None:
    TOKEN_FILE.write_text(token, encoding="utf-8")


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise SystemExit("Сначала выполните login")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {load_token()}"}


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def register(args: argparse.Namespace) -> None:
    response = httpx.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": args.email, "username": args.username, "password": args.password},
        timeout=10,
    )
    response.raise_for_status()
    print_json(response.json())


def login(args: argparse.Namespace) -> None:
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": args.email, "password": args.password},
        timeout=10,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    save_token(token)
    print("Token saved")


def me(_: argparse.Namespace) -> None:
    response = httpx.get(f"{BASE_URL}/api/users/me", headers=headers(), timeout=10)
    response.raise_for_status()
    print_json(response.json())


def chats(_: argparse.Namespace) -> None:
    response = httpx.get(f"{BASE_URL}/api/chats", headers=headers(), timeout=10)
    response.raise_for_status()
    print_json(response.json())


def create_chat(args: argparse.Namespace) -> None:
    members = [{"user_id": int(user_id), "role": "member"} for user_id in args.member]
    response = httpx.post(
        f"{BASE_URL}/api/chats",
        headers=headers(),
        json={"title": args.title, "type": "group", "members": members},
        timeout=10,
    )
    response.raise_for_status()
    print_json(response.json())


def history(args: argparse.Namespace) -> None:
    response = httpx.get(
        f"{BASE_URL}/api/chats/{args.chat_id}/messages",
        headers=headers(),
        timeout=10,
    )
    response.raise_for_status()
    print_json(response.json())


def send(args: argparse.Namespace) -> None:
    response = httpx.post(
        f"{BASE_URL}/api/chats/{args.chat_id}/messages",
        headers=headers(),
        json={"body": args.body},
        timeout=10,
    )
    response.raise_for_status()
    print_json(response.json())


def search(args: argparse.Namespace) -> None:
    response = httpx.get(
        f"{BASE_URL}/api/messages/search",
        headers=headers(),
        params={"q": args.query},
        timeout=10,
    )
    response.raise_for_status()
    print_json(response.json())


async def listen_async(chat_id: int) -> None:
    token = load_token()
    url = f"ws://localhost:8000/ws/chats/{chat_id}?token={token}"
    async with websockets.connect(url) as socket:
        print(f"Listening chat #{chat_id}")
        async for message in socket:
            print_json(json.loads(message))


def listen(args: argparse.Namespace) -> None:
    asyncio.run(listen_async(args.chat_id))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="messenger")
    sub = parser.add_subparsers(required=True)

    cmd = sub.add_parser("register")
    cmd.add_argument("email")
    cmd.add_argument("username")
    cmd.add_argument("password")
    cmd.set_defaults(func=register)

    cmd = sub.add_parser("login")
    cmd.add_argument("email")
    cmd.add_argument("password")
    cmd.set_defaults(func=login)

    cmd = sub.add_parser("me")
    cmd.set_defaults(func=me)

    cmd = sub.add_parser("chats")
    cmd.set_defaults(func=chats)

    cmd = sub.add_parser("create-chat")
    cmd.add_argument("title")
    cmd.add_argument("--member", action="append", default=[])
    cmd.set_defaults(func=create_chat)

    cmd = sub.add_parser("history")
    cmd.add_argument("chat_id", type=int)
    cmd.set_defaults(func=history)

    cmd = sub.add_parser("send")
    cmd.add_argument("chat_id", type=int)
    cmd.add_argument("body")
    cmd.set_defaults(func=send)

    cmd = sub.add_parser("search")
    cmd.add_argument("query")
    cmd.set_defaults(func=search)

    cmd = sub.add_parser("listen")
    cmd.add_argument("chat_id", type=int)
    cmd.set_defaults(func=listen)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

