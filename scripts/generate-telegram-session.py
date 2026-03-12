from telethon import TelegramClient
from telethon.sessions import StringSession


def main() -> None:
    api_id = int(input("TELEGRAM_API_ID: ").strip())
    api_hash = input("TELEGRAM_API_HASH: ").strip()

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        client.start()
        session = client.session.save()
        print("\nTELEGRAM_SESSION_STRING:\n")
        print(session)


if __name__ == "__main__":
    main()
