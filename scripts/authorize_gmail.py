from src.communication.gmail_email_channel import (
    DEFAULT_GMAIL_CREDENTIALS_PATH,
    DEFAULT_GMAIL_TOKEN_PATH,
    build_gmail_service,
)


def main() -> None:
    print("Starting Gmail OAuth authorization.")
    print("Client credentials:", DEFAULT_GMAIL_CREDENTIALS_PATH)
    print("Token output:", DEFAULT_GMAIL_TOKEN_PATH)

    # This triggers browser OAuth the first time.
    # It does NOT send any email.
    build_gmail_service()

    print("Gmail OAuth authorization completed successfully.")
    print("No email was sent.")


if __name__ == "__main__":
    main()