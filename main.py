# main.py - Fixed Bot with Conflict Resolution
import asyncio
import os
import logging
import signal
import sys
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, TimedOut, NetworkError
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

# Global flag for clean shutdown
bot_running = False

# --- FLASK APP ---
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head><title>Trusty Lads Bot</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <h1>🤖 Trusty Lads Bot</h1>
            <p>✅ Status: <strong style="color: #90EE90;">{'Online & Running' if bot_running else 'Starting...'}</strong></p>
            <p>🔍 Bot Token: {'✅ Found' if BOT_TOKEN else '❌ Missing'}</p>
            <p>📱 Features: Auto-Reply, Commands, Customer Service</p>
            <p>🌐 Environment: {os.environ.get('RENDER', 'Local Development')}</p>
            <hr style="margin: 30px 0; border: 1px solid rgba(255,255,255,0.3);">
            <p><em>Bot is ready to serve your customers!</em></p>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    return {
        "status": "healthy" if bot_running else "starting", 
        "service": "trusty-lads-bot",
        "bot_token_present": bool(BOT_TOKEN),
        "bot_running": bot_running,
        "features": ["auto_reply", "customer_service", "commands"]
    }

# Clear any existing webhooks (common cause of conflicts)
@app.route('/clear_webhook')
def clear_webhook():
    """Clear webhook to prevent conflicts"""
    try:
        import requests
        response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        return {"status": "webhook_cleared", "response": response.json()}
    except Exception as e:
        return {"error": str(e)}

# --- BOT HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when user starts the bot"""
    user = update.effective_user
    logger.info(f"👋 New user started bot: {user.first_name} (ID: {user.id})")
    
    welcome_message = f"""
🎉 **Welcome to Trusty Lads, {user.first_name}!**

I'm your automated customer service assistant. Here's how I can help:

🔸 **Auto-Reply**: I respond to all your messages instantly
🔸 **Product Info**: Ask about our products and services  
🔸 **Support**: Get help with orders, shipping, and more
🔸 **Commands**: Use /help to see all available commands

💬 **Just send me any message and I'll respond immediately!**

---
✨ *Powered by Trusty Lads Customer Service*
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands"""
    help_text = """
🆘 **Available Commands:**

/start - Welcome message
/help - Show this help menu
/products - View our product catalog
/contact - Get contact information
/status - Check order status
/shipping - Shipping information
/support - Customer support options

💬 **Or just send any message for instant auto-reply!**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product information"""
    products_text = """
🛍️ **Trusty Lads Product Catalog:**

🔸 **Premium Service Package** - $99/month
   • 24/7 customer support
   • Priority handling
   • Dedicated account manager

🔸 **Standard Package** - $49/month  
   • Business hours support
   • Email & chat support
   • Quick response times

🔸 **Basic Package** - $19/month
   • Email support
   • FAQ resources
   • Community forum access

💰 *Special offer: 20% off first month with code TRUSTY20*

Want to order? Just reply with the package name!
    """
    await update.message.reply_text(products_text, parse_mode='Markdown')

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show contact information"""
    contact_text = """
📞 **Contact Trusty Lads:**

🌐 **Website**: trustylads.com
📧 **Email**: support@trustylads.com  
📱 **Phone**: +1 (555) 123-LADS
💬 **Live Chat**: Available 24/7 via this bot

🏢 **Office Hours:**
Monday - Friday: 9 AM - 6 PM EST
Saturday: 10 AM - 4 PM EST
Sunday: Closed

⚡ **Emergency Support**: Always available via this bot!
    """
    await update.message.reply_text(contact_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check order status"""
    status_text = """
📦 **Check Your Order Status:**

To check your order status, please provide:
• Order number (starts with TL-)
• Email address used for the order

💡 **Example**: 
"My order TL-12345 status please"

🔍 **Don't have your order number?**
No problem! Send me your email and I'll look it up.

⏰ **Typical Processing Times:**
• Standard: 2-3 business days
• Premium: Same day processing
• Custom orders: 5-7 business days
    """
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def shipping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show shipping information"""
    shipping_text = """
🚚 **Shipping Information:**

📦 **Shipping Options:**
• Standard Shipping (5-7 days) - FREE on orders $50+
• Express Shipping (2-3 days) - $9.99
• Overnight Shipping (1 day) - $19.99

🌍 **We Ship To:**
• United States (all 50 states)
• Canada  
• United Kingdom
• European Union
• Australia & New Zealand

📱 **Tracking:**
You'll receive tracking info via SMS and email once shipped.

🎁 **Special Services:**
• Gift wrapping available (+$5)
• Signature required delivery
• Hold at location pickup
    """
    await update.message.reply_text(shipping_text, parse_mode='Markdown')

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support options"""
    support_text = """
🆘 **Customer Support Options:**

🤖 **This Bot** - Instant responses 24/7
📧 **Email** - support@trustylads.com (2-4 hour response)
📞 **Phone** - +1 (555) 123-LADS (business hours)
💬 **Live Chat** - Website chat widget

🔥 **Common Issues We Solve:**
• Order modifications & cancellations
• Refunds & returns (30-day policy)
• Product recommendations  
• Technical support
• Billing questions
• Account management

⚡ **Priority Support Available:**
Premium customers get 15-minute response times!

Just describe your issue and I'll help immediately!
    """
    await update.message.reply_text(support_text, parse_mode='Markdown')

async def auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-reply to all messages with intelligent responses"""
    user = update.effective_user
    message_text = update.message.text.lower()
    
    logger.info(f"💬 Auto-reply triggered by {user.first_name}: {update.message.text}")
    
    # Intelligent keyword-based responses
    if any(word in message_text for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
        response = f"👋 Hello {user.first_name}! Thanks for contacting Trusty Lads! How can I assist you today? Use /help to see what I can do for you!"
        
    elif any(word in message_text for word in ['order', 'purchase', 'buy', 'price', 'cost']):
        response = "🛒 Interested in our products? Great choice! Use /products to see our catalog or /contact to speak with a sales representative. What specific product are you looking for?"
        
    elif any(word in message_text for word in ['problem', 'issue', 'help', 'support', 'broken', 'not working']):
        response = "🆘 I'm sorry to hear you're having an issue! I'm here to help resolve it quickly. Can you describe the problem in detail? For urgent issues, use /support for more contact options."
        
    elif any(word in message_text for word in ['refund', 'return', 'cancel', 'money back']):
        response = "💰 No problem! We have a 30-day money-back guarantee. I can help process your refund. Please provide your order number (starts with TL-) and reason for return."
        
    elif any(word in message_text for word in ['shipping', 'delivery', 'tracking', 'when arrive']):
        response = "📦 I can help with shipping info! Use /shipping for all delivery options and times. If you have a tracking number, I can look up your package status. What's your tracking number?"
        
    elif any(word in message_text for word in ['thank', 'thanks', 'appreciate']):
        response = "😊 You're very welcome! That's what we're here for. Is there anything else I can help you with today? We love happy customers!"
        
    elif 'tl-' in message_text:  # Order number detected
        order_num = [word for word in message_text.split() if 'tl-' in word][0]
        response = f"🔍 Looking up order {order_num.upper()}... Great news! Your order is being processed. You'll receive tracking info within 24 hours. Need any changes to this order?"
        
    else:
        # Generic auto-reply for any other message
        response = f"""
✨ **Thanks for your message, {user.first_name}!**

I received: "{update.message.text}"

🤖 I'm Trusty Lads' AI assistant, ready to help 24/7! Here's what I can do:

• Answer product questions (/products)
• Check order status (/status)  
• Process returns & refunds
• Provide shipping info (/shipping)
• Connect you with human support (/contact)

💬 **Just tell me what you need help with and I'll respond instantly!**
        """
    
    await update.message.reply_text(response, parse_mode='Markdown')

# --- CONFLICT RESOLUTION ---
async def clear_existing_webhooks():
    """Clear any existing webhooks that might cause conflicts"""
    try:
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Cleared existing webhooks")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Could not clear webhooks: {e}")
        return False

# --- BOT SETUP WITH CONFLICT HANDLING ---
async def setup_bot():
    """Setup bot with proper async handling and conflict resolution"""
    global bot_running
    
    if not BOT_TOKEN:
        logger.error("❌ CRITICAL: BOT_TOKEN not found!")
        return None
    
    try:
        # Clear any existing webhooks first
        await clear_existing_webhooks()
        
        # Wait a moment for cleanup
        await asyncio.sleep(2)
        
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("products", products_command))
        application.add_handler(CommandHandler("contact", contact_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("shipping", shipping_command))
        application.add_handler(CommandHandler("support", support_command))
        
        # Add auto-reply handler for all text messages (excluding commands)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply_handler))
        
        logger.info("✅ Bot setup complete with auto-reply enabled")
        return application
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        return None

async def run_bot_async():
    """Run bot with proper error handling and retry logic"""
    global bot_running
    
    application = await setup_bot()
    if not application:
        return
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Get bot info
            bot_info = await application.bot.get_me()
            logger.info(f"🤖 Bot @{bot_info.username} is starting... (Attempt {retry_count + 1})")
            
            # Initialize and start with conflict handling
            await application.initialize()
            await application.start()
            
            # Start polling with retries on conflict
            await application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            bot_running = True
            logger.info("🚀 Bot is now running with auto-reply enabled!")
            
            # Keep running
            while bot_running:
                await asyncio.sleep(1)
                
            break  # Exit retry loop if successful
            
        except Conflict as e:
            retry_count += 1
            logger.error(f"❌ Conflict error (attempt {retry_count}): {e}")
            
            if retry_count < max_retries:
                wait_time = retry_count * 10
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                
                # Try to clear webhooks again
                await clear_existing_webhooks()
                await asyncio.sleep(5)
            else:
                logger.error("❌ Max retries reached. Bot startup failed.")
                
        except (TimedOut, NetworkError) as e:
            logger.error(f"⚠️ Network error: {e}")
            await asyncio.sleep(5)
            continue
            
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
            break
            
    finally:
        bot_running = False
        try:
            if application:
                await application.stop()
                logger.info("🛑 Bot stopped")
        except:
            pass

def run_bot_thread():
    """Run bot in thread with new event loop"""
    logger.info("🧵 Starting bot thread...")
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot_async())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot interrupted")
    except Exception as e:
        logger.error(f"❌ Bot thread error: {e}")
    finally:
        loop.close()

# --- FLASK RUNNER ---
def run_flask():
    """Run Flask server"""
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=False)

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    logger.info("🚀 Starting Trusty Lads Customer Service Bot...")
    
    # Start bot in background thread
    bot_thread = Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot thread started")
    
    # Start Flask server (main thread)  
    run_flask()