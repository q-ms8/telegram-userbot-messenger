#!/usr/bin/env python3
"""
Telegram Userbot — Send messages from your personal account via CLI.

Usage:
    # Single recipient
    python send_message.py --to @username --message "Hello!"
    python send_message.py --to +1234567890 --message "Hey there!"
    python send_message.py --to @username --file message.txt
    python send_message.py --to @username  (interactive mode)

    # Bulk send to many recipients
    python send_message.py --list recipients.txt --message "Hello everyone!"
    python send_message.py --list recipients.txt --file message.txt --delay 3
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime

# Fix Windows console encoding — force UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberInvalidError,
    UsernameNotOccupiedError,
    FloodWaitError,
    SessionPasswordNeededError,
    UserPrivacyRestrictedError,
    PeerFloodError,
    ChatWriteForbiddenError,
)

# ─── ANSI Colors ────────────────────────────────────────────────────────────────
class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    DIM     = "\033[2m"


def print_banner():
    """Print a styled banner."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}+----------------------------------------------+
|        [>>] Telegram Userbot Messenger       |
|          Send messages from your account     |
+----------------------------------------------+{Colors.RESET}
"""
    print(banner)


def print_success(msg: str):
    print(f"  {Colors.GREEN}[+]{Colors.RESET} {msg}")


def print_error(msg: str):
    print(f"  {Colors.RED}[x]{Colors.RESET} {msg}")


def print_info(msg: str):
    print(f"  {Colors.CYAN}[i]{Colors.RESET} {msg}")


def print_warning(msg: str):
    print(f"  {Colors.YELLOW}[!]{Colors.RESET} {msg}")


def print_progress(current: int, total: int, msg: str):
    """Print a progress indicator for bulk operations."""
    bar_len = 20
    filled = int(bar_len * current / total)
    bar = f"{'#' * filled}{'-' * (bar_len - filled)}"
    pct = int(100 * current / total)
    print(f"  {Colors.CYAN}[{bar}] {pct}%{Colors.RESET} ({current}/{total}) {msg}")


def load_config() -> tuple[int, str, str | None]:
    """Load API credentials from .env file."""
    load_dotenv()

    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE")

    if not api_id or not api_hash:
        print_error("Missing API_ID or API_HASH in .env file.")
        print_info("1. Go to https://my.telegram.org")
        print_info("2. Create an app and get your API_ID and API_HASH")
        print_info("3. Copy .env.example to .env and fill in the values")
        sys.exit(1)

    try:
        api_id_int = int(api_id)
    except ValueError:
        print_error("API_ID must be a number.")
        sys.exit(1)

    return api_id_int, api_hash, phone


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Send Telegram messages from your personal account.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (single recipient):
  python send_message.py --to @username --message "Hello!"
  python send_message.py --to +1234567890 --message "Hey!"
  python send_message.py --to @username --file message.txt
  python send_message.py --to @username   (interactive mode)

Examples (bulk send):
  python send_message.py --list recipients.txt --message "Hello everyone!"
  python send_message.py --list recipients.txt --file message.txt
  python send_message.py --list recipients.txt --message "Hi!" --delay 5
        """,
    )

    # Recipient: single or bulk
    recipient_group = parser.add_mutually_exclusive_group(required=True)
    recipient_group.add_argument(
        "--to",
        help="Single recipient: @username, phone number (+1234567890), or numeric user ID",
    )
    recipient_group.add_argument(
        "--list", "-l",
        dest="recipient_list",
        help="Path to a text file with one recipient per line (username, phone, or user ID)",
    )

    # Message source
    msg_group = parser.add_mutually_exclusive_group()
    msg_group.add_argument(
        "--message", "-m",
        help="The message text to send",
    )
    msg_group.add_argument(
        "--file", "-f",
        help="Path to a text file containing the message to send",
    )

    # Bulk options
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=2.0,
        help="Delay in seconds between messages in bulk mode (default: 2.0)",
    )

    return parser.parse_args()


def resolve_recipient(to: str) -> str | int:
    """
    Resolve the --to argument to a Telethon-compatible entity.
    Returns username (str) or user ID (int).
    """
    # Numeric user ID
    if to.isdigit():
        return int(to)

    # Phone number or username — pass through
    return to


def load_recipients(file_path: str) -> list[str]:
    """Load a list of recipients from a text file (one per line)."""
    if not os.path.isfile(file_path):
        print_error(f"Recipients file not found: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    recipients = []
    for line in lines:
        line = line.strip()
        # Skip empty lines and comments
        if line and not line.startswith("#"):
            recipients.append(line)

    if not recipients:
        print_error("Recipients file is empty (no valid entries found).")
        sys.exit(1)

    return recipients


def get_message_text(args: argparse.Namespace) -> str:
    """Get the message text from args, file, or interactive input."""
    if args.message:
        return args.message

    if args.file:
        file_path = args.file
        if not os.path.isfile(file_path):
            print_error(f"File not found: {file_path}")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            print_error("The file is empty.")
            sys.exit(1)
        print_info(f"Loaded message from {file_path} ({len(text)} chars)")
        return text

    # Interactive mode
    print_info("No message provided. Enter your message below:")
    print(f"  {Colors.DIM}(Press Enter twice to send, Ctrl+C to cancel){Colors.RESET}")
    lines = []
    empty_count = 0
    try:
        while True:
            line = input(f"  {Colors.MAGENTA}|{Colors.RESET} ")
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
    except KeyboardInterrupt:
        print(f"\n")
        print_warning("Cancelled.")
        sys.exit(0)

    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()

    text = "\n".join(lines).strip()
    if not text:
        print_error("Empty message. Nothing to send.")
        sys.exit(1)

    return text


async def send_single(client: TelegramClient, recipient_raw: str, message_text: str) -> dict:
    """
    Send a message to a single recipient.
    Returns a result dict with status info.
    """
    recipient = resolve_recipient(recipient_raw)
    try:
        entity = await client.get_entity(recipient)
        sent_msg = await client.send_message(entity, message_text)

        entity_name = getattr(entity, "first_name", None) or getattr(entity, "title", None) or str(recipient)
        timestamp = sent_msg.date.strftime("%Y-%m-%d %H:%M:%S UTC")

        return {
            "recipient": recipient_raw,
            "entity_name": entity_name,
            "status": "sent",
            "msg_id": sent_msg.id,
            "timestamp": timestamp,
            "error": None,
        }

    except UsernameNotOccupiedError:
        return {"recipient": recipient_raw, "status": "failed", "error": f"Username does not exist"}
    except FloodWaitError as e:
        return {"recipient": recipient_raw, "status": "flood", "error": f"Rate limited — wait {e.seconds}s", "wait": e.seconds}
    except PeerFloodError:
        return {"recipient": recipient_raw, "status": "flood", "error": "Too many messages sent — Telegram blocked further sends"}
    except UserPrivacyRestrictedError:
        return {"recipient": recipient_raw, "status": "failed", "error": "User privacy settings prevent messaging"}
    except ChatWriteForbiddenError:
        return {"recipient": recipient_raw, "status": "failed", "error": "Cannot write to this chat"}
    except ValueError as e:
        return {"recipient": recipient_raw, "status": "failed", "error": f"Could not find user: {e}"}
    except Exception as e:
        return {"recipient": recipient_raw, "status": "failed", "error": str(e)}


async def main():
    """Main async entry point."""
    print_banner()

    args = parse_args()
    api_id, api_hash, phone = load_config()
    message_text = get_message_text(args)

    # Determine recipients
    is_bulk = args.recipient_list is not None
    if is_bulk:
        recipients = load_recipients(args.recipient_list)
        print_info(f"Loaded {Colors.BOLD}{len(recipients)}{Colors.RESET} recipients from {args.recipient_list}")
    else:
        recipients = [args.to]

    # Session file stored alongside the script
    session_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "userbot_session")

    client = TelegramClient(session_path, api_id, api_hash)

    print_info("Connecting to Telegram...")

    try:
        await client.start(phone=phone if phone else lambda: input(f"  {Colors.CYAN}Enter your phone number: {Colors.RESET}"))
    except PhoneNumberInvalidError:
        print_error("Invalid phone number. Use international format, e.g. +1234567890")
        sys.exit(1)
    except SessionPasswordNeededError:
        print_warning("Two-Factor Authentication is enabled.")
        password = input(f"  {Colors.CYAN}Enter your 2FA password: {Colors.RESET}")
        await client.sign_in(password=password)
    except Exception as e:
        print_error(f"Authentication failed: {e}")
        sys.exit(1)

    me = await client.get_me()
    display_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    print_success(f"Logged in as {Colors.BOLD}{display_name}{Colors.RESET} (@{me.username or 'N/A'})")

    # ─── Single message mode ────────────────────────────────────────────────
    if not is_bulk:
        print_info(f"Sending message to {Colors.BOLD}{args.to}{Colors.RESET}...")

        result = await send_single(client, args.to, message_text)

        if result["status"] == "sent":
            preview = message_text[:80].replace("\n", " ")
            if len(message_text) > 80:
                preview += "..."

            print()
            print(f"  {Colors.GREEN}{Colors.BOLD}+-- Message Delivered -----------------------{Colors.RESET}")
            print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}To:{Colors.RESET}        {result['entity_name']}")
            print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}Time:{Colors.RESET}      {result['timestamp']}")
            print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}Msg ID:{Colors.RESET}    {result['msg_id']}")
            print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}Preview:{Colors.RESET}   {preview}")
            print(f"  {Colors.GREEN}{Colors.BOLD}+--------------------------------------------{Colors.RESET}")
            print()
        else:
            print_error(f"Failed: {result['error']}")
            sys.exit(1)

    # ─── Bulk message mode ──────────────────────────────────────────────────
    else:
        total = len(recipients)
        delay = args.delay

        # Preview
        preview = message_text[:60].replace("\n", " ")
        if len(message_text) > 60:
            preview += "..."

        print()
        print(f"  {Colors.YELLOW}{Colors.BOLD}+-- Bulk Send Summary --------------------------{Colors.RESET}")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Recipients:{Colors.RESET}  {total}")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Delay:{Colors.RESET}       {delay}s between messages")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Message:{Colors.RESET}     {preview}")
        est_time = total * delay
        mins = int(est_time // 60)
        secs = int(est_time % 60)
        print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Est. time:{Colors.RESET}   ~{mins}m {secs}s")
        print(f"  {Colors.YELLOW}{Colors.BOLD}+------------------------------------------------{Colors.RESET}")
        print()

        # Confirm
        try:
            confirm = input(f"  {Colors.YELLOW}Proceed? (y/n): {Colors.RESET}").strip().lower()
        except KeyboardInterrupt:
            print()
            print_warning("Cancelled.")
            await client.disconnect()
            sys.exit(0)

        if confirm not in ("y", "yes"):
            print_warning("Cancelled by user.")
            await client.disconnect()
            sys.exit(0)

        print()
        results = {"sent": [], "failed": [], "flood": []}
        flood_stopped = False

        for i, recipient_raw in enumerate(recipients, 1):
            if flood_stopped:
                results["failed"].append({"recipient": recipient_raw, "error": "Skipped (flood protection)"})
                continue

            print_progress(i, total, f"-> {recipient_raw}")

            result = await send_single(client, recipient_raw, message_text)

            if result["status"] == "sent":
                results["sent"].append(result)
                print_success(f"{result['entity_name']} ({recipient_raw})")

            elif result["status"] == "flood":
                results["flood"].append(result)
                print_error(f"{recipient_raw}: {result['error']}")

                # If PeerFlood, stop entirely
                if "blocked" in result.get("error", "").lower():
                    print_warning("Telegram has blocked further sends. Stopping bulk operation.")
                    flood_stopped = True
                    continue

                # If FloodWait, wait the required time
                wait_time = result.get("wait", 60)
                if wait_time <= 300:  # Only auto-wait if <= 5 minutes
                    print_warning(f"Waiting {wait_time}s for rate limit to clear...")
                    await asyncio.sleep(wait_time)
                else:
                    print_error(f"Rate limit too long ({wait_time}s). Stopping.")
                    flood_stopped = True
                    continue
            else:
                results["failed"].append(result)
                print_error(f"{recipient_raw}: {result['error']}")

            # Delay between messages (skip on last message)
            if i < total and not flood_stopped:
                await asyncio.sleep(delay)

        # ─── Final Report ────────────────────────────────────────────────
        sent_count = len(results["sent"])
        failed_count = len(results["failed"])
        flood_count = len(results["flood"])

        print()
        print(f"  {Colors.CYAN}{Colors.BOLD}+== BULK SEND REPORT ===========================+{Colors.RESET}")
        print(f"  {Colors.CYAN}|{Colors.RESET}  {Colors.GREEN}Sent:{Colors.RESET}       {sent_count}/{total}")
        print(f"  {Colors.CYAN}|{Colors.RESET}  {Colors.RED}Failed:{Colors.RESET}     {failed_count}/{total}")
        if flood_count:
            print(f"  {Colors.CYAN}|{Colors.RESET}  {Colors.YELLOW}Flood:{Colors.RESET}      {flood_count}/{total}")
        print(f"  {Colors.CYAN}{Colors.BOLD}+================================================+{Colors.RESET}")

        # Show failed details
        if results["failed"]:
            print()
            print(f"  {Colors.RED}{Colors.BOLD}Failed recipients:{Colors.RESET}")
            for r in results["failed"]:
                print(f"    {Colors.RED}-{Colors.RESET} {r['recipient']}: {r.get('error', 'Unknown error')}")

        if flood_count:
            print()
            print(f"  {Colors.YELLOW}{Colors.BOLD}Flood-limited recipients:{Colors.RESET}")
            for r in results["flood"]:
                print(f"    {Colors.YELLOW}-{Colors.RESET} {r['recipient']}: {r.get('error', 'Rate limited')}")

        print()

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
