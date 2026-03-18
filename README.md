# Telegram Org Scanner Bot

A Telegram bot that scans for valid ClassPlus organization codes.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a bot with @BotFather on Telegram and get your token

3. Replace `YOUR_BOT_TOKEN_HERE` in `bot.py` with your actual bot token

4. Run the bot:
```bash
python bot.py
```

## Commands

- `/start` - Show help
- `/scan` - Start scanning for org codes
- `/status` - Check scan progress
- `/results` - View found organizations
- `/stop` - Stop current scan

## Features

- Async scanning with real-time updates
- Progress tracking
- Results saved to JSON file
- Rate limiting to avoid API blocks
- Clean, minimal code

## How it works

The bot tests organization codes against the ClassPlus API endpoint and reports valid organizations found during the scan.