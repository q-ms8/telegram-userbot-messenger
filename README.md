# 📨 Telegram Userbot Messenger

Send Telegram messages **from your personal account** via the command line. Built with [Telethon](https://docs.telethon.dev/).

---

## 🚀 Quick Start

### 1. Get Telegram API Credentials

1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Click **"API Development Tools"**
4. Create a new application (any name/short name is fine)
5. Copy the **API ID** and **API Hash**

### 2. Setup

```bash
# Clone/navigate to the project
cd Antigravity

# Install dependencies
pip install -r requirements.txt

# Create your .env file from the template
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
```

Edit `.env` and fill in your credentials:

```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
PHONE=+1234567890
```

### 3. First Run (Authentication)

On the first run, Telethon will ask you to:
1. Enter your phone number (if not in `.env`)
2. Enter the OTP code sent to your Telegram app
3. Enter your 2FA password (if enabled)

A session file (`userbot_session.session`) is created so you **won't need to authenticate again**.

---

## 📖 Usage

### Send a message to a username
```bash
python send_message.py --to @username --message "Hello from CLI!"
```

### Send to a phone number
```bash
python send_message.py --to +1234567890 --message "Hey there!"
```

### Send to a user ID
```bash
python send_message.py --to 123456789 --message "Hi!"
```

### Send a long message from a file
```bash
python send_message.py --to @username --file message.txt
```

### Interactive mode (type your message)
```bash
python send_message.py --to @username
```
This opens an interactive prompt where you can type a multi-line message. Press **Enter twice** to send.

---

## 🛠 Options

| Flag             | Description                                |
|------------------|--------------------------------------------|
| `--to`           | **(Required)** Recipient: `@username`, `+phone`, or user ID |
| `--message`, `-m`| Message text to send                       |
| `--file`, `-f`   | Path to a text file containing the message |

If neither `--message` nor `--file` is provided, interactive mode is activated.

---

## 📁 Project Structure

```
Antigravity/
├── .env.example        # Template for API credentials
├── .env                # Your actual credentials (git-ignored)
├── .gitignore          # Ignores secrets and session files
├── requirements.txt    # Python dependencies
├── send_message.py     # Main CLI script
└── README.md           # This file
```

---

## ⚠️ Important Notes

- **Session security**: The `.session` file contains your login session. Keep it private — anyone with this file can access your Telegram account.
- **Rate limits**: Telegram enforces rate limits. If you send too many messages too quickly, you may be temporarily blocked.
- **Terms of Service**: Using the Client API for spam or abuse violates [Telegram's ToS](https://core.telegram.org/api/terms). Use responsibly.
- **First message**: You can only message users who you've had prior contact with, or whose privacy settings allow messages from anyone.

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `Missing API_ID or API_HASH` | Make sure `.env` exists and has valid values |
| `PhoneNumberInvalidError` | Use international format: `+1234567890` |
| `UsernameNotOccupiedError` | Double-check the username spelling |
| `FloodWaitError` | You're rate-limited — wait the specified time |
| `SessionPasswordNeededError` | Enter your 2FA password when prompted |
| `Could not find user` | Ensure you've had prior contact with the user, or try their phone number |
