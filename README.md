# Telegram & WhatsApp Messenger

Send messages **from your personal accounts** via the command line. Supports single and bulk messaging.

| Platform | Script | Library | Auth |
|----------|--------|---------|------|
| Telegram | `send_message.py` | [Telethon](https://docs.telethon.dev/) | API ID + OTP |
| WhatsApp | `send_whatsapp.py` | [Playwright](https://playwright.dev/) | QR Code scan |

---

## 🚀 Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Chromium browser for WhatsApp (one-time)
playwright install chromium
```

---

## 📱 Telegram Setup

### 1. Get API Credentials
1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Log in → **"API Development Tools"** → Create an app
3. Copy the **API ID** and **API Hash**

### 2. Configure
```bash
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
```
Edit `.env` and fill in `API_ID`, `API_HASH`, and `PHONE`.

### 3. Usage
```bash
# Send to a single user
python send_message.py --to "@username" --message "Hello!"

# Bulk send to many users
python send_message.py --list recipients.txt --message "Hello everyone!"
python send_message.py --list recipients.txt --message "Hi!" --delay 5
```

### Telegram Options
| Flag | Description |
|------|-------------|
| `--to` | Single recipient: `@username`, `+phone`, or user ID |
| `--list`, `-l` | File with one recipient per line |
| `--message`, `-m` | Message text |
| `--file`, `-f` | Read message from a text file |
| `--delay`, `-d` | Seconds between messages in bulk mode (default: 2) |

---

## 💬 WhatsApp Setup

### 1. First Run (QR Code)
On the first run, a browser window opens with WhatsApp Web:
1. Open WhatsApp on your phone
2. Go to **Settings → Linked Devices → Link a Device**
3. Scan the QR code in the browser

The session is saved — you won't need to scan again.

### 2. Usage
```bash
# Send to a single contact (use their name as it appears in your contacts)
python send_whatsapp.py --to "John Doe" --message "Hello!"

# Send to a phone number
python send_whatsapp.py --to "+1234567890" --message "Hey!"

# Bulk send
python send_whatsapp.py --list wa_recipients.txt --message "Hello everyone!"
python send_whatsapp.py --list wa_recipients.txt --file message.txt --delay 15
```

### WhatsApp Options
| Flag | Description |
|------|-------------|
| `--to` | Single recipient: contact name or `+phone` |
| `--list`, `-l` | File with one recipient per line |
| `--message`, `-m` | Message text |
| `--file`, `-f` | Read message from a text file |
| `--delay`, `-d` | Base delay between messages (default: 10s, min: 8s) |
| `--headless` | Run browser without a window (don't use on first login) |

### Built-in Safety Features
| Feature | Details |
|---------|---------|
| **Max messages** | 40 per session |
| **Random delays** | Base delay + 2–6s random jitter |
| **Human typing** | Characters typed one-by-one at random speed |
| **Cool-down** | 15–30s pause every 10 messages |
| **Confirmation** | Asks `y/n` before bulk sending |

---

## 📁 Project Structure

```
Antigravity/
├── .env.example              # Template for Telegram API credentials
├── .env                      # Your credentials (git-ignored)
├── .gitignore                # Ignores secrets, sessions, and private data
├── requirements.txt          # Python dependencies
├── send_message.py           # Telegram CLI messenger
├── send_whatsapp.py          # WhatsApp Web CLI messenger
├── recipients_example.txt    # Sample Telegram recipients list
├── wa_recipients_example.txt # Sample WhatsApp recipients list
└── README.md                 # This file
```

---

## ⚠️ Important Notes

### Telegram
- **Session file**: `*.session` contains your login — keep it private.
- **Rate limits**: Telegram may temporarily block you if you send too fast.
- **ToS**: Don't use for spam. [Telegram API Terms](https://core.telegram.org/api/terms).

### WhatsApp
- **No official API**: WhatsApp does not provide a Client API for personal accounts. This tool automates WhatsApp Web via a real browser.
- **Account risk**: Sending too many messages too fast can get your account banned. The built-in safety features reduce this risk significantly.
- **Session folder**: `whatsapp_session/` contains your browser login — keep it private.
- **Contact names**: Use the exact name as it appears in your WhatsApp contacts.

---

## 🐛 Troubleshooting

### Telegram
| Problem | Solution |
|---------|----------|
| `Missing API_ID or API_HASH` | Make sure `.env` exists with valid values |
| `PhoneNumberInvalidError` | Use international format: `+1234567890` |
| `FloodWaitError` | You're rate-limited — wait the specified time |

### WhatsApp
| Problem | Solution |
|---------|----------|
| `Playwright is not installed` | Run `pip install playwright` then `playwright install chromium` |
| QR code won't scan | Delete `whatsapp_session/` folder and try again |
| Contact not found | Use the exact name from your WhatsApp contacts |
| Browser crashes | Make sure no other Playwright instance is running |
