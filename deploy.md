# Heroku Deployment Guide

## 1. Setup
```bash
# Install Heroku CLI
# Create Heroku app
heroku create your-scanner-bot

# Set bot token
heroku config:set BOT_TOKEN=your_actual_bot_token_here

# Deploy
git init
git add .
git commit -m "Deploy scanner bot"
git push heroku main
```

## 2. Scale Worker
```bash
heroku ps:scale worker=1
```

## 3. Monitor
```bash
heroku logs --tail
```

## Bot Commands
- `/start` - Show help
- `/scan` - Start 2M+ pattern scan
- `/status` - Check progress
- `/results` - Get results + download
- `/stop` - Stop scan

## Performance
- **2+ Million patterns**
- **40 concurrent workers**
- **~1000 req/sec**
- **24/7 Heroku hosting**