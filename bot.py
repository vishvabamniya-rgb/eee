import asyncio
import json
import uuid
import string
import itertools
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import aiofiles
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
RESULTS_FILE = "results.json"

class OrgScanner:
    def __init__(self):
        self.scanning = False
        self.progress = 0
        self.found = 0
        self.total = 0
        self.results = []
        self.start_time = None

    async def test_org_code(self, session, org_code):
        try:
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Api-Version': '52',
                'device-id': str(uuid.uuid4()).replace('-', ''),
                'region': 'IN',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(f"https://api.classplusapp.com/v2/orgs/{org_code}", 
                                 headers=headers, timeout=2) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = {
                        "orgCode": org_code,
                        "orgId": data['data']['orgId'],
                        "orgName": data['data'].get('orgName', 'Unknown'),
                        "found_at": datetime.now().isoformat()
                    }
                    await self.save_result(result)
                    return result
            return None
        except Exception as e:
            logger.error(f"API error for {org_code}: {e}")
            return None

    async def save_result(self, result):
        try:
            results = []
            try:
                async with aiofiles.open(RESULTS_FILE, 'r') as f:
                    content = await f.read()
                    results = json.loads(content)
            except FileNotFoundError:
                pass
            
            results.append(result)
            async with aiofiles.open(RESULTS_FILE, 'w') as f:
                await f.write(json.dumps(results, indent=2))
        except Exception as e:
            logger.error(f"Save error: {e}")

    def generate_patterns(self):
        patterns = []
        
        # 1-4 chars: complete coverage (~475k patterns)
        for length in range(1, 5):
            for combo in itertools.product(string.ascii_lowercase, repeat=length):
                patterns.append(''.join(combo))
            for combo in itertools.product(string.ascii_uppercase, repeat=length):
                patterns.append(''.join(combo))
        
        # 5-8 chars: expanded samples (~960k patterns)
        for length in [5, 6, 7, 8]:
            for i, combo in enumerate(itertools.product(string.ascii_lowercase, repeat=length)):
                if i >= 60000: break
                patterns.append(''.join(combo))
            for i, combo in enumerate(itertools.product(string.ascii_uppercase, repeat=length)):
                if i >= 60000: break
                patterns.append(''.join(combo))
        
        # Mixed case: expanded (~540k patterns)
        for length in [3, 4, 5, 6, 7, 8]:
            for i, combo in enumerate(itertools.product(string.ascii_letters, repeat=length)):
                if i >= 45000: break
                patterns.append(''.join(combo))
        
        # Numbers and alphanumeric: expanded (~280k patterns)
        for length in [2, 3, 4, 5, 6, 7, 8]:
            for i, combo in enumerate(itertools.product(string.ascii_letters + string.digits, repeat=length)):
                if i >= 20000: break
                patterns.append(''.join(combo))
        
        # Special patterns: numbers only
        for length in [1, 2, 3, 4, 5, 6]:
            for combo in itertools.product(string.digits, repeat=length):
                patterns.append(''.join(combo))
        
        # Common abbreviations and acronyms
        common_words = ['edu', 'tech', 'info', 'pro', 'net', 'org', 'app', 'web', 'hub', 'lab', 'dev', 'ai', 'it', 'cs', 'ca', 'ias', 'ips', 'neet', 'jee', 'gate', 'cat', 'gmat', 'sat', 'ielts', 'toefl']
        for word in common_words:
            patterns.append(word)
            patterns.append(word.upper())
            patterns.append(word.capitalize())
            # Add with numbers
            for i in range(10):
                patterns.append(f"{word}{i}")
                patterns.append(f"{i}{word}")
        
        # Education words with prefixes/suffixes
        edu_words = ['class', 'academy', 'institute', 'study', 'coaching', 'school', 'college', 'learn', 'teach', 'tutor', 'guide', 'mentor', 'skill', 'course', 'exam', 'test', 'prep']
        prefixes = list(string.ascii_letters) + ['the', 'my', 'new', 'top', 'best', 'smart', 'super', 'mega', 'ultra', 'pro', 'elite']
        
        for word in edu_words:
            for prefix in prefixes:
                patterns.append(prefix + word)
                patterns.append(word + prefix)
                patterns.append(prefix + word.capitalize())
        
        return list(set(patterns))

    async def scan_batch(self, session, batch, update):
        for org_code in batch:
            if not self.scanning:
                break
                
            result = await self.test_org_code(session, org_code)
            if result:
                self.found += 1
                self.results.append(result)
                await update.message.reply_text(f"🎯 FOUND: {org_code} -> {result['orgName']}")
            
            self.progress += 1
            
            if self.progress % 100 == 0:
                percent = (self.progress / self.total) * 100
                bar_length = 10
                filled = int(bar_length * percent / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                await update.message.reply_text(f"📊 {bar} {percent:.1f}%\n{self.progress}/{self.total} - Found: {self.found}")

scanner = OrgScanner()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 ClassPlus Org Scanner Bot\n\n"
        "Commands:\n"
        "/scan - Start scanning\n"
        "/status - Check progress\n"
        "/results - Get results\n"
        "/stop - Stop scan"
    )

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if scanner.scanning:
        await update.message.reply_text("⚠️ Scan already running!")
        return
    
    scanner.scanning = True
    scanner.progress = 0
    scanner.found = 0
    scanner.results = []
    scanner.start_time = time.time()
    
    patterns = scanner.generate_patterns()
    scanner.total = len(patterns)
    
    await update.message.reply_text(f"🚀 Starting scan with {len(patterns)} patterns...")
    
    try:
        # Original high-performance logic
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=1)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            batch_size = 20
            batches = [patterns[i:i + batch_size] for i in range(0, len(patterns), batch_size)]
            
            # High concurrency with semaphore
            semaphore = asyncio.Semaphore(40)
            
            async def process_batch_with_semaphore(batch):
                async with semaphore:
                    if scanner.scanning:
                        await scanner.scan_batch(session, batch, update)
            
            # Process batches concurrently
            tasks = []
            for batch in batches:
                if not scanner.scanning:
                    break
                tasks.append(process_batch_with_semaphore(batch))
                
                # Process in chunks to manage memory
                if len(tasks) >= 100:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []
            
            # Process remaining tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    scanner.scanning = False
    elapsed = time.time() - scanner.start_time
    
    await update.message.reply_text(
        f"✅ Scan completed!\n"
        f"⏱️ Time: {elapsed:.1f}s\n"
        f"🎯 Found: {scanner.found} orgs"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scanner.scanning and scanner.progress == 0:
        await update.message.reply_text("💤 No scan running. Use /scan to start.")
        return
    
    percent = (scanner.progress / scanner.total) * 100 if scanner.total > 0 else 0
    elapsed = time.time() - scanner.start_time if scanner.start_time else 0
    
    await update.message.reply_text(
        f"📊 Status\n"
        f"🔄 Running: {'Yes' if scanner.scanning else 'No'}\n"
        f"📈 Progress: {scanner.progress}/{scanner.total} ({percent:.1f}%)\n"
        f"🎯 Found: {scanner.found}\n"
        f"⏱️ Elapsed: {elapsed:.1f}s"
    )

async def results_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scanner.results:
        await update.message.reply_text("📭 No results yet.")
        return
    
    text = f"🎯 Found {len(scanner.results)} organizations:\n\n"
    for i, org in enumerate(scanner.results[:10]):
        text += f"{i+1}. {org['orgCode']} - {org['orgName']}\n"
    
    if len(scanner.results) > 10:
        text += f"\n... and {len(scanner.results) - 10} more"
    
    keyboard = [[InlineKeyboardButton("📥 Download Results", callback_data="download")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scanner.scanning = False
    await update.message.reply_text("🛑 Scan stopped.")

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not scanner.results:
        await query.edit_message_text("📭 No results to download.")
        return
    
    # Create download content
    content = f"ClassPlus Organizations Found ({len(scanner.results)} total)\n"
    content += "=" * 50 + "\n\n"
    
    for i, org in enumerate(scanner.results, 1):
        content += f"{i}. Code: {org['orgCode']}\n"
        content += f"   Name: {org['orgName']}\n"
        content += f"   ID: {org['orgId']}\n"
        content += f"   Found: {org['found_at']}\n\n"
    
    # Send as document
    from io import BytesIO
    file_buffer = BytesIO(content.encode('utf-8'))
    file_buffer.name = f"classplus_orgs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    await query.message.reply_document(
        document=file_buffer,
        caption=f"📥 {len(scanner.results)} organizations found"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("results", results_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CallbackQueryHandler(download_callback, pattern="download"))
    
    logger.info("🤖 Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()