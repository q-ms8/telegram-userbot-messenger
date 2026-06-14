#!/usr/bin/env python3
"""
WhatsApp Web Messenger — Send messages from your personal account via CLI.
Uses Playwright to automate a real browser (safest approach).

Usage:
    # Single recipient
    python send_whatsapp.py --to "Contact Name" --message "Hello!"
    python send_whatsapp.py --to "+1234567890" --message "Hello!"

    # Bulk send
    python send_whatsapp.py --list recipients.txt --message "Hello everyone!"
    python send_whatsapp.py --list recipients.txt --file message.txt --delay 10

First run: A browser window opens — scan the QR code with your phone.
           The session is saved so you won't need to scan again.
"""

import argparse
import asyncio
import os
import random
import sys
import time

# Fix Windows console encoding — force UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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
{Colors.GREEN}{Colors.BOLD}+----------------------------------------------+
|      [>>] WhatsApp Web Messenger             |
|        Send messages from your account       |
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


# ─── Safety Constants ───────────────────────────────────────────────────────────
# These limits help avoid detection and account bans
MAX_MESSAGES_PER_SESSION = 40          # Hard limit per run
MIN_DELAY_SECONDS = 8                   # Minimum delay between messages
HUMAN_TYPING_MIN_DELAY = 0.03          # Min delay per character (simulated typing)
HUMAN_TYPING_MAX_DELAY = 0.08          # Max delay per character (simulated typing)
RANDOM_EXTRA_DELAY_MIN = 2             # Random extra seconds added to delay
RANDOM_EXTRA_DELAY_MAX = 6             # Random extra seconds added to delay
COOL_DOWN_EVERY = 10                   # Pause every N messages
COOL_DOWN_SECONDS_MIN = 15             # Cool down pause min
COOL_DOWN_SECONDS_MAX = 30             # Cool down pause max


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Send WhatsApp messages from your personal account (via WhatsApp Web).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples (single recipient):
  python send_whatsapp.py --to "John Doe" --message "Hello!"
  python send_whatsapp.py --to "+1234567890" --message "Hey!"

Examples (bulk send):
  python send_whatsapp.py --list wa_recipients.txt --message "Hello everyone!"
  python send_whatsapp.py --list wa_recipients.txt --file message.txt --delay 15

Safety limits (built-in):
  - Max {MAX_MESSAGES_PER_SESSION} messages per session
  - Min {MIN_DELAY_SECONDS}s delay between messages (+ random jitter)
  - Cool-down pause every {COOL_DOWN_EVERY} messages
  - Human-like typing simulation
        """,
    )

    # Recipient: single or bulk
    recipient_group = parser.add_mutually_exclusive_group(required=True)
    recipient_group.add_argument(
        "--to",
        help='Single recipient: contact name ("John Doe") or phone number ("+1234567890")',
    )
    recipient_group.add_argument(
        "--list", "-l",
        dest="recipient_list",
        help="Path to a text file with one recipient per line",
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

    # Options
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=10.0,
        help=f"Base delay in seconds between messages in bulk mode (min: {MIN_DELAY_SECONDS}, default: 10)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (not recommended for first run — you need to scan QR code)",
    )

    args = parser.parse_args()

    # Enforce minimum delay
    if args.delay < MIN_DELAY_SECONDS:
        print_warning(f"Delay too low. Forced to minimum safe value: {MIN_DELAY_SECONDS}s")
        args.delay = MIN_DELAY_SECONDS

    return args


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
        print("\n")
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


async def human_type(page, selector: str, text: str):
    """
    Type text character by character with random delays to simulate human typing.
    """
    element = page.locator(selector)
    await element.click()
    for char in text:
        await element.press_sequentially(char, delay=random.uniform(
            HUMAN_TYPING_MIN_DELAY * 1000,
            HUMAN_TYPING_MAX_DELAY * 1000,
        ))


async def wait_for_login(page):
    """Wait for WhatsApp Web to fully load (either QR scan or auto-login)."""
    print_info("Waiting for WhatsApp Web to load...")

    # Check if already logged in or need QR scan
    try:
        # Wait for either the main chat screen or the QR code
        await page.wait_for_selector(
            'div[data-testid="chat-list"], canvas[aria-label="Scan this QR code to link a device!"], div[data-ref]',
            timeout=30000,
        )
    except Exception:
        pass

    # Check if QR code is showing
    qr_visible = await page.locator('canvas[aria-label="Scan this QR code to link a device!"], div[data-ref]').count()

    if qr_visible > 0:
        print()
        print(f"  {Colors.YELLOW}{Colors.BOLD}+-- QR Code Detected ---------------------------+{Colors.RESET}")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  1. Open WhatsApp on your phone                {Colors.YELLOW}|{Colors.RESET}")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  2. Go to Settings > Linked Devices            {Colors.YELLOW}|{Colors.RESET}")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  3. Tap 'Link a Device'                        {Colors.YELLOW}|{Colors.RESET}")
        print(f"  {Colors.YELLOW}|{Colors.RESET}  4. Scan the QR code in the browser window      {Colors.YELLOW}|{Colors.RESET}")
        print(f"  {Colors.YELLOW}{Colors.BOLD}+------------------------------------------------+{Colors.RESET}")
        print()
        print_info("Waiting for you to scan the QR code...")

    # Wait for the main chat list to appear (means logged in)
    try:
        await page.wait_for_selector(
            'div[data-testid="chat-list"]',
            timeout=120000,  # 2 minutes to scan QR
        )
    except Exception:
        print_error("Login timed out. Please restart and try again.")
        sys.exit(1)

    # Small extra wait for WhatsApp to fully sync
    await asyncio.sleep(3)
    print_success("WhatsApp Web is ready!")


async def send_message_to(page, recipient: str, message_text: str) -> dict:
    """
    Send a message to a single recipient via WhatsApp Web.
    Returns a result dict with status info.
    """
    try:
        # Step 1: Click on the search/new chat area
        search_box = page.locator('div[data-testid="chat-list-search-container"] div[contenteditable="true"]')

        # If search box not found, try clicking the search icon first
        if await search_box.count() == 0:
            search_btn = page.locator('div[data-testid="chat-list-search"]')
            if await search_btn.count() > 0:
                await search_btn.click()
                await asyncio.sleep(1)

        search_box = page.locator('div[data-testid="chat-list-search-container"] div[contenteditable="true"]')

        # Fallback: try the general search box
        if await search_box.count() == 0:
            search_box = page.locator('div[contenteditable="true"][data-tab="3"]')

        await search_box.click()
        await asyncio.sleep(0.5)

        # Clear any existing text
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.3)

        # Type the recipient name/phone
        await search_box.fill(recipient)
        await asyncio.sleep(2)  # Wait for search results

        # Step 2: Click on the first matching result
        # Try to find a matching chat result
        chat_result = page.locator(f'span[title="{recipient}"]').first

        if await chat_result.count() == 0:
            # Try a more flexible match — look in search results list
            chat_result = page.locator('div[data-testid="cell-frame-container"]').first

        if await chat_result.count() == 0:
            return {
                "recipient": recipient,
                "status": "failed",
                "error": "Contact not found in search results",
            }

        await chat_result.click()
        await asyncio.sleep(1.5)

        # Step 3: Find the message input box and type the message
        msg_input = page.locator('div[data-testid="conversation-compose-box-input"]')

        if await msg_input.count() == 0:
            # Fallback selector
            msg_input = page.locator('footer div[contenteditable="true"]')

        if await msg_input.count() == 0:
            return {
                "recipient": recipient,
                "status": "failed",
                "error": "Could not find message input box",
            }

        await msg_input.click()
        await asyncio.sleep(0.3)

        # Type message with human-like speed (character by character)
        # For multi-line messages, use Shift+Enter for new lines
        lines = message_text.split("\n")
        for i, line in enumerate(lines):
            for char in line:
                await msg_input.press_sequentially(char, delay=random.uniform(
                    HUMAN_TYPING_MIN_DELAY * 1000,
                    HUMAN_TYPING_MAX_DELAY * 1000,
                ))
            if i < len(lines) - 1:
                await page.keyboard.press("Shift+Enter")
                await asyncio.sleep(random.uniform(0.1, 0.3))

        await asyncio.sleep(0.5)

        # Step 4: Send the message (press Enter)
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)

        # Step 5: Verify message was sent (look for the sent checkmark)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "recipient": recipient,
            "status": "sent",
            "timestamp": timestamp,
            "error": None,
        }

    except Exception as e:
        return {
            "recipient": recipient,
            "status": "failed",
            "error": str(e),
        }


async def main():
    """Main async entry point."""
    print_banner()

    args = parse_args()
    message_text = get_message_text(args)

    # Determine recipients
    is_bulk = args.recipient_list is not None
    if is_bulk:
        recipients = load_recipients(args.recipient_list)
        print_info(f"Loaded {Colors.BOLD}{len(recipients)}{Colors.RESET} recipients from {args.recipient_list}")

        # Enforce safety limit
        if len(recipients) > MAX_MESSAGES_PER_SESSION:
            print_warning(f"Recipient list exceeds safety limit of {MAX_MESSAGES_PER_SESSION}.")
            print_warning(f"Only the first {MAX_MESSAGES_PER_SESSION} recipients will be messaged.")
            recipients = recipients[:MAX_MESSAGES_PER_SESSION]
    else:
        recipients = [args.to]

    # Import Playwright here (so --help works without it installed)
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print_error("Playwright is not installed.")
        print_info("Install it with: pip install playwright")
        print_info("Then run: playwright install chromium")
        sys.exit(1)

    # Session directory for persistent browser data
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp_session")

    print_info("Launching browser...")

    async with async_playwright() as p:
        # Use persistent context to save the WhatsApp Web session (QR code login)
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=args.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Navigate to WhatsApp Web
        await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        # Wait for login
        await wait_for_login(page)

        # ─── Single message mode ────────────────────────────────────────
        if not is_bulk:
            print_info(f"Sending message to {Colors.BOLD}{args.to}{Colors.RESET}...")

            result = await send_message_to(page, args.to, message_text)

            if result["status"] == "sent":
                preview = message_text[:80].replace("\n", " ")
                if len(message_text) > 80:
                    preview += "..."

                print()
                print(f"  {Colors.GREEN}{Colors.BOLD}+-- Message Delivered -----------------------{Colors.RESET}")
                print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}To:{Colors.RESET}        {result['recipient']}")
                print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}Time:{Colors.RESET}      {result['timestamp']}")
                print(f"  {Colors.GREEN}|{Colors.RESET}  {Colors.DIM}Preview:{Colors.RESET}   {preview}")
                print(f"  {Colors.GREEN}{Colors.BOLD}+--------------------------------------------{Colors.RESET}")
                print()
            else:
                print_error(f"Failed: {result['error']}")

        # ─── Bulk message mode ──────────────────────────────────────────
        else:
            total = len(recipients)
            delay = args.delay

            # Preview
            preview = message_text[:60].replace("\n", " ")
            if len(message_text) > 60:
                preview += "..."

            # Estimate time (base delay + average random extra + average typing time)
            avg_extra = (RANDOM_EXTRA_DELAY_MIN + RANDOM_EXTRA_DELAY_MAX) / 2
            avg_typing = len(message_text) * (HUMAN_TYPING_MIN_DELAY + HUMAN_TYPING_MAX_DELAY) / 2
            est_per_msg = delay + avg_extra + avg_typing + 4  # +4 for search/click delays
            est_total = total * est_per_msg
            cool_downs = (total // COOL_DOWN_EVERY) * (COOL_DOWN_SECONDS_MIN + COOL_DOWN_SECONDS_MAX) / 2
            est_total += cool_downs
            mins = int(est_total // 60)
            secs = int(est_total % 60)

            print()
            print(f"  {Colors.YELLOW}{Colors.BOLD}+-- Bulk Send Summary --------------------------+{Colors.RESET}")
            print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Recipients:{Colors.RESET}  {total}")
            print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Base delay:{Colors.RESET}  {delay}s + random {RANDOM_EXTRA_DELAY_MIN}-{RANDOM_EXTRA_DELAY_MAX}s jitter")
            print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Cool-down:{Colors.RESET}   every {COOL_DOWN_EVERY} messages ({COOL_DOWN_SECONDS_MIN}-{COOL_DOWN_SECONDS_MAX}s pause)")
            print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Message:{Colors.RESET}     {preview}")
            print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Est. time:{Colors.RESET}   ~{mins}m {secs}s")
            print(f"  {Colors.YELLOW}|{Colors.RESET}  {Colors.DIM}Safety cap:{Colors.RESET}  {MAX_MESSAGES_PER_SESSION} messages/session")
            print(f"  {Colors.YELLOW}{Colors.BOLD}+------------------------------------------------+{Colors.RESET}")
            print()

            # Confirm
            try:
                confirm = input(f"  {Colors.YELLOW}Proceed? (y/n): {Colors.RESET}").strip().lower()
            except KeyboardInterrupt:
                print()
                print_warning("Cancelled.")
                await browser.close()
                sys.exit(0)

            if confirm not in ("y", "yes"):
                print_warning("Cancelled by user.")
                await browser.close()
                sys.exit(0)

            print()
            results = {"sent": [], "failed": []}

            for i, recipient in enumerate(recipients, 1):
                print_progress(i, total, f"-> {recipient}")

                result = await send_message_to(page, recipient, message_text)

                if result["status"] == "sent":
                    results["sent"].append(result)
                    print_success(f"{recipient}")
                else:
                    results["failed"].append(result)
                    print_error(f"{recipient}: {result['error']}")

                # Delay between messages (skip on last)
                if i < total:
                    # Add random jitter to the base delay
                    actual_delay = delay + random.uniform(RANDOM_EXTRA_DELAY_MIN, RANDOM_EXTRA_DELAY_MAX)

                    # Cool-down every N messages
                    if i % COOL_DOWN_EVERY == 0:
                        cool = random.uniform(COOL_DOWN_SECONDS_MIN, COOL_DOWN_SECONDS_MAX)
                        print_info(f"Cool-down pause: {cool:.0f}s (for safety)...")
                        await asyncio.sleep(cool)

                    print_info(f"Waiting {actual_delay:.1f}s...")
                    await asyncio.sleep(actual_delay)

            # ─── Final Report ────────────────────────────────────────────
            sent_count = len(results["sent"])
            failed_count = len(results["failed"])

            print()
            print(f"  {Colors.CYAN}{Colors.BOLD}+== BULK SEND REPORT ===========================+{Colors.RESET}")
            print(f"  {Colors.CYAN}|{Colors.RESET}  {Colors.GREEN}Sent:{Colors.RESET}       {sent_count}/{total}")
            print(f"  {Colors.CYAN}|{Colors.RESET}  {Colors.RED}Failed:{Colors.RESET}     {failed_count}/{total}")
            print(f"  {Colors.CYAN}{Colors.BOLD}+================================================+{Colors.RESET}")

            if results["failed"]:
                print()
                print(f"  {Colors.RED}{Colors.BOLD}Failed recipients:{Colors.RESET}")
                for r in results["failed"]:
                    print(f"    {Colors.RED}-{Colors.RESET} {r['recipient']}: {r.get('error', 'Unknown error')}")

            print()

        # Keep browser open briefly for any pending sends
        await asyncio.sleep(2)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
