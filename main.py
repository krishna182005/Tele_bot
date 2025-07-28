# main.py - FIXED VERSION for python-telegram-bot v20+
import asyncio
import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SETUP ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

print(f"🔍 BOT_TOKEN found: {'Yes' if BOT_TOKEN else 'No'}")
print(f"🔍 BOT_TOKEN length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")

# --- FLASK APP ---
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head><title>Trusty Lads Bot - Fixed</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Trusty Lads Bot - Running</h1>
            <p>✅ Status: <strong style="color: green;">Flask Running</strong></p>
            <p>🔍 Bot Token: {'✅ Found' if BOT_TOKEN else '❌ Missing'}</p>
            <p>🔍 Port: {os.environ.get('PORT', 'Not set')}</p>
            <p>🔍 Environment: {os.environ.get('RENDER', 'Local')}</p>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    return {
        "status": "healthy", 
        "service": "trusty-lads-bot",
        "bot_token_present": bool(BOT_TOKEN),
        "environment": os.environ.get('RENDER', 'local')
    }

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple start command with logging"""
    user = update.effective_user
    logger.info(f"📨 Start command received from user: {user.first_name} (ID: {user.id})")
    
    try:
        await update.message.reply_text(
            f"🎉 Hello {user.first_name}! Bot is working on Render!\n"
            f"🆔 Your ID: {user.id}\n"
            f"⏰ Bot is responding correctly!"
        )
        logger.info("✅ Response sent successfully")
    except Exception as e:
        logger.error(f"❌ Error sending response: {e}")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command for debugging"""
    logger.info("🧪 Test command received")
    await update.message.reply_text("✅ Test successful! Bot is alive and responding.")

# --- SIMPLIFIED BOT SETUP ---
async def run_bot():
    """Setup and run the Telegram bot - FIXED VERSION"""
    if not BOT_TOKEN:
        logger.error("❌ CRITICAL: BOT_TOKEN not found!")
        return
    
    logger.info("🤖 Initializing Telegram Bot...")
    
    try:
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        logger.info("✅ ApplicationBuilder created successfully")
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("test", test_command))
        logger.info("✅ Handlers registered")
        
        # Get bot info for verification
        bot_info = await application.bot.get_me()
        logger.info(f"✅ Bot verified: @{bot_info.username}")
        
        # Start polling - THIS IS THE SIMPLIFIED APPROACH
        logger.info("🚀 Starting bot polling...")
        await application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ CRITICAL BOT ERROR: {e}")
        import traceback
        traceback.print_exc()

# --- FLASK RUNNER ---
def run_flask():
    """Run Flask server"""
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        logger.warning("⚠️ Waitress not found, using Flask dev server")
        app.run(host='0.0.0.0', port=port, debug=False)

def run_bot_in_thread():
    """Run bot in separate event loop"""
    logger.info("🧵 Starting bot thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    except Exception as e:
        logger.error(f"❌ Bot thread error: {e}")
    finally:
        loop.close()
        logger.info("🧵 Bot thread closed")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    logger.info("🚀 Starting Trusty Lads Bot (Fixed Version)...")
    
    # Start bot in background thread
    bot_thread = Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot thread started")
    
    # Start Flask server (main thread)
    run_flask()