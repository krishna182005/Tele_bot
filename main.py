# main.py - Enhanced Trusty Lads Customer Service Bot with Advanced Features

import asyncio
import os
import logging
import json
import re
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, jsonify, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Conflict, TimedOut, NetworkError
from dotenv import load_dotenv

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ENVIRONMENT SETUP ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Log token availability (avoid logging actual token for security)
logger.info(f"🔍 BOT_TOKEN found: {'Yes' if BOT_TOKEN else 'No'}")

# Global flag for clean shutdown
bot_running = False

# In-memory storage for user sessions and data
user_sessions = {}
fake_orders = {
    "TL-12345": {"status": "Shipped", "tracking": "1Z999AA1234567890", "items": "Premium Service Package", "total": "$99.00"},
    "TL-67890": {"status": "Processing", "tracking": "Pending", "items": "Standard Package", "total": "$49.00"},
    "TL-11111": {"status": "Delivered", "tracking": "1Z999BB9876543210", "items": "Basic Package", "total": "$19.00"}
}

# FAQ Database
faq_data = {
    "How do I cancel my order?": "You can cancel your order within 24 hours of purchase. Use /cancel with your order number or contact support.",
    "What's your refund policy?": "We offer a 30-day money-back guarantee. No questions asked!",
    "Do you offer discounts?": "Yes! Use code TRUSTY20 for 20% off your first month. Students get 50% off with valid ID.",
    "How long does shipping take?": "Standard shipping: 5-7 days (FREE over $50), Express: 2-3 days ($9.99), Overnight: 1 day ($19.99)",
    "Can I change my shipping address?": "Yes, if your order hasn't shipped yet. Contact us immediately with your order number.",
    "Do you ship internationally?": "Yes! We ship to US, Canada, UK, EU, Australia, and New Zealand.",
    "How do I track my package?": "You'll receive tracking info via SMS and email. Use /track with your tracking number.",
    "What payment methods do you accept?": "We accept all major credit cards, PayPal, Apple Pay, Google Pay, and cryptocurrency."
}

# --- FLASK APP ---
app = Flask(__name__)

@app.route('/')
def home():
    """Render the bot's dashboard with live statistics and features."""
    stats = {
        "active_users": len(user_sessions),
        "total_messages": sum(session.get('message_count', 0) for session in user_sessions.values()),
        "bot_uptime": "Online" if bot_running else "Starting..."
    }
    
    return f"""
    <html>
        <head>
            <title>Trusty Lads Bot Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; 
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; min-height: 100vh; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .card {{ background: rgba(255,255,255,0.1); padding: 20px; margin: 20px 0; 
                        border-radius: 15px; backdrop-filter: blur(10px); }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .stat {{ text-align: center; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 10px; }}
                .feature {{ margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Trusty Lads Customer Service Bot</h1>
                
                <div class="card">
                    <h2>📊 Live Statistics</h2>
                    <div class="stats">
                        <div class="stat">
                            <h3>{stats['active_users']}</h3>
                            <p>Active Users</p>
                        </div>
                        <div class="stat">
                            <h3>{stats['total_messages']}</h3>
                            <p>Messages Handled</p>
                        </div>
                        <div class="stat">
                            <h3>{'✅' if bot_running else '⏳'}</h3>
                            <p>{stats['bot_uptime']}</p>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h2>🚀 Enhanced Features</h2>
                    <div class="feature">🎯 Smart Auto-Reply with Context Understanding</div>
                    <div class="feature">🔍 Instant Order Tracking & Status Updates</div>
                    <div class="feature">💬 Interactive Menus & Quick Buttons</div>
                    <div class="feature">🤖 AI-Powered FAQ & Help System</div>
                    <div class="feature">📱 Custom Keyboards for Easy Navigation</div>
                    <div class="feature">🎫 Support Ticket System</div>
                    <div class="feature">⭐ Feedback & Rating System</div>
                    <div class="feature">🔔 Smart Notifications & Reminders</div>
                    <div class="feature">📊 User Session Management</div>
                    <div class="feature">🎁 Promo Code Validation</div>
                </div>

                <div class="card">
                    <h2>📞 Quick Actions</h2>
                    <p>Bot Token: {'✅ Found' if BOT_TOKEN else '❌ Missing'}</p>
                    <p>Environment: {os.environ.get('RENDER', 'Local Development')}</p>
                    <p><a href="/health" style="color: #90EE90;">Health Check</a> | 
                       <a href="/clear_webhook" style="color: #90EE90;">Clear Webhook</a> |
                       <a href="/analytics" style="color: #90EE90;">Analytics</a></p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    """Return the health status of the bot."""
    return jsonify({
        "status": "healthy" if bot_running else "starting",
        "service": "trusty-lads-enhanced-bot",
        "version": "2.0",
        "features": [
            "smart_auto_reply", "order_tracking", "interactive_menus", 
            "faq_system", "support_tickets", "feedback_system",
            "session_management", "promo_validation"
        ],
        "active_users": len(user_sessions),
        "bot_running": bot_running
    })

@app.route('/analytics')
def analytics():
    """Return analytics data for the bot."""
    return jsonify({
        "active_sessions": len(user_sessions),
        "user_data": {str(k): v for k, v in user_sessions.items()},
        "total_messages": sum(session.get('message_count', 0) for session in user_sessions.values())
    })

@app.route('/clear_webhook', methods=['POST'])
async def clear_webhook():
    """Clear the Telegram webhook configuration."""
    try:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        await application.bot.set_webhook(url='')
        logger.info("Webhook cleared successfully")
        return jsonify({"status": "success", "message": "Webhook cleared"})
    except Exception as e:
        logger.error(f"Failed to clear webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- USER SESSION MANAGEMENT ---
def get_user_session(user_id):
    """Initialize or retrieve a user session."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "first_interaction": datetime.now(),
            "message_count": 0,
            "current_context": None,
            "support_tickets": [],
            "preferences": {},
            "last_order": None,
            "last_rating": None
        }
    return user_sessions[user_id]

def update_user_session(user_id, **kwargs):
    """Update user session with new data."""
    session = get_user_session(user_id)
    session.update(kwargs)
    session['message_count'] += 1
    session['last_interaction'] = datetime.now()

# --- ENHANCED BOT HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with a welcome message and custom keyboard."""
    user = update.effective_user
    session = get_user_session(user.id)
    logger.info(f"👋 User started bot: {user.first_name} (ID: {user.id})")
    
    keyboard = [
        [KeyboardButton("🛍️ Products"), KeyboardButton("📦 Track Order")],
        [KeyboardButton("🆘 Get Help"), KeyboardButton("💬 Live Chat")],
        [KeyboardButton("⭐ Leave Feedback"), KeyboardButton("🎁 Promo Codes")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    welcome_message = f"""
🎉 **Welcome to Trusty Lads, {user.first_name}!**

I'm your enhanced AI customer service assistant with tons of new features!

🚀 **What's New:**
• 🎯 Smart context-aware responses
• 📱 Easy-to-use button menus
• 🔍 Real-time order tracking
• 🤖 Instant FAQ answers
• 🎫 Support ticket system
• ⭐ Feedback & ratings

💡 **Getting Started:**
Use the buttons below or type your questions naturally!

👆 *Tap any button to get started, or just chat with me!*
    """
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )
    
    update_user_session(user.id, current_context="welcome")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command with an interactive help menu."""
    keyboard = [
        [InlineKeyboardButton("🛍️ Products", callback_data="help_products"),
         InlineKeyboardButton("📦 Orders", callback_data="help_orders")],
        [InlineKeyboardButton("🚚 Shipping", callback_data="help_shipping"),
         InlineKeyboardButton("💰 Refunds", callback_data="help_refunds")],
        [InlineKeyboardButton("🔍 FAQ", callback_data="show_faq"),
         deerButton("📞 Contact", callback_data="help_contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = """
🆘 **Enhanced Help Center**

Choose a category below for instant help, or use these commands:

**🤖 Smart Commands:**
/start - Welcome & main menu
/help - This help center  
/products - Product catalog
/track - Track your order
/support - Create support ticket
/faq - Frequently asked questions
/feedback - Leave a review
/promo - Check promo codes

**💬 Natural Chat:**
Just type your questions naturally! I understand context and can help with complex requests.

👆 *Click the buttons below for specific help topics*
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def enhanced_products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the product catalog with interactive buttons."""
    keyboard = [
        [InlineKeyboardButton("🔥 Premium Package", callback_data="product_premium"),
         InlineKeyboardButton("⚡ Standard Package", callback_data="product_standard")],
        [InlineKeyboardButton("💫 Basic Package", callback_data="product_basic"),
         InlineKeyboardButton("🎁 View All Deals", callback_data="product_deals")],
        [InlineKeyboardButton("🛒 Quick Order", callback_data="quick_order"),
         InlineKeyboardButton("💬 Chat with Sales", callback_data="sales_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    products_text = """
🛍️ **Trusty Lads Product Catalog** *(Enhanced Edition)*

**🔥 Premium Package - $99/month**
• 24/7 VIP support with <2min response
• Dedicated account manager
• Priority processing & shipping
• Exclusive member benefits
• Advanced analytics dashboard

**⚡ Standard Package - $49/month**
• Business hours support
• Live chat & email support  
• Standard processing
• Monthly reports
• Community access

**💫 Basic Package - $19/month**
• Email support (24-48hr response)
• FAQ & knowledge base
• Community forum
• Basic features

**🎁 Current Promotions:**
• TRUSTY20 - 20% off first month
• STUDENT50 - 50% off for students
• BUNDLE25 - 25% off annual plans

👆 *Click buttons below to learn more or order instantly!*
    """
    
    await update.message.reply_text(products_text, parse_mode='Markdown', reply_markup=reply_markup)

async def track_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /track command for order tracking."""
    user_id = update.effective_user.id
    args = context.args
    
    if args:
        order_num = args[0].upper()
        await process_order_lookup(update, order_num)
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Enter Order Number", callback_data="enter_order_number")],
            [InlineKeyboardButton("📧 Search by Email", callback_data="search_by_email")],
            [InlineKeyboardButton("📱 Use Phone Number", callback_data="search_by_phone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        track_text = """
📦 **Enhanced Order Tracking**

**How would you like to find your order?**

🔍 **Option 1:** Enter order number (TL-XXXXX)
📧 **Option 2:** Search by email address
📱 **Option 3:** Use phone number

**Sample Order Numbers to Try:**
• TL-12345 (Shipped)
• TL-67890 (Processing)  
• TL-11111 (Delivered)

💡 *Tip: Your order number was sent to your email when you purchased*
        """
        
        await update.message.reply_text(track_text, parse_mode='Markdown', reply_markup=reply_markup)
        update_user_session(user_id, current_context="tracking")

async def process_order_lookup(update, order_num):
    """Process an order lookup by order number."""
    if order_num in fake_orders:
        order = fake_orders[order_num]
        status_emoji = {"Shipped": "🚚", "Processing": "⏳", "Delivered": "✅", "Cancelled": "❌"}
        
        keyboard = [
            [InlineKeyboardButton("📍 Track Package", callback_data=f"track_package_{order_num}")],
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"),
             InlineKeyboardButton("🔄 Check Again", callback_data="recheck_order")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        order_text = f"""
📦 **Order Status Found!**

**Order:** {order_num}
**Status:** {status_emoji.get(order['status'], '📦')} {order['status']}
**Items:** {order['items']}
**Total:** {order['total']}
**Tracking:** {order['tracking']}

{'🎉 Your order has been delivered! Hope you love it!' if order['status'] == 'Delivered' else ''}
{'🚚 Your order is on the way! Estimated delivery: 2-3 business days' if order['status'] == 'Shipped' else ''}
{'⏳ Your order is being prepared. You\'ll get tracking info soon!' if order['status'] == 'Processing' else ''}
        """
        
        await update.message.reply_text(order_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Try Again", callback_data="enter_order_number")],
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❌ Order {order_num} not found. Please check the number or contact support.",
            reply_markup=reply_markup
        )

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /faq command to display frequently asked questions."""
    keyboard = []
    for i, question in enumerate(list(faq_data.keys())[:6]):  # Show first 6 FAQs
        keyboard.append([InlineKeyboardButton(f"❓ {question}", callback_data=f"faq_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔍 Search FAQ", callback_data="search_faq")])
    keyboard.append([InlineKeyboardButton("❓ Ask Custom Question", callback_data="ask_question")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    faq_text = """
🤖 **Frequently Asked Questions**

Click any question below for an instant answer, or search for specific topics!

💡 **Popular Topics:**
• Order cancellations & refunds
• Shipping times & costs
• Discount codes & promotions
• International shipping
• Payment methods

👆 *Click a question below or search for something specific*
    """
    
    await update.message.reply_text(faq_text, parse_mode='Markdown', reply_markup=reply_markup)

async def support_ticket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /support command to create a support ticket."""
    user = update.effective_user
    session = get_user_session(user.id)
    
    ticket_id = f"TKT-{len(session['support_tickets']) + 1:04d}"
    
    keyboard = [
        [InlineKeyboardButton("🔧 Technical Issue", callback_data=f"ticket_tech_{ticket_id}")],
        [InlineKeyboardButton("💰 Billing Question", callback_data=f"ticket_billing_{ticket_id}")],
        [InlineKeyboardButton("📦 Order Problem", callback_data=f"ticket_order_{ticket_id}")],
        [InlineKeyboardButton("💬 General Support", callback_data=f"ticket_general_{ticket_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    support_text = f"""
🎫 **Create Support Ticket** 

**Ticket ID:** {ticket_id}
**Priority:** Normal
**Status:** New

**What type of issue are you experiencing?**

Select a category below and I'll connect you with the right specialist:

🔧 **Technical** - App/website issues
💰 **Billing** - Payment & subscription questions  
📦 **Orders** - Shipping, delivery, returns
💬 **General** - Other questions & feedback

⚡ **Response Times:**
• Premium customers: <15 minutes
• Standard customers: <2 hours  
• Basic customers: <24 hours
    """
    
    await update.message.reply_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)
    update_user_session(user.id, current_context="support_ticket")

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /feedback command for user ratings."""
    keyboard = [
        [InlineKeyboardButton("⭐⭐⭐⭐⭐ Excellent", callback_data="rating_5")],
        [InlineKeyboardButton("⭐⭐⭐⭐ Good", callback_data="rating_4")],
        [InlineKeyboardButton("⭐⭐⭐ Average", callback_data="rating_3")],
        [InlineKeyboardButton("⭐⭐ Poor", callback_data="rating_2")],
        [InlineKeyboardButton("⭐ Very Poor", callback_data="rating_1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    feedback_text = """
⭐ **We Value Your Feedback!**

How was your experience with Trusty Lads today?

Your feedback helps us improve our service and better serve you in the future.

**Rate your experience:**
👆 *Click the stars below*

After rating, you'll have the option to leave detailed comments or suggestions.

🎁 **Bonus:** Leave feedback and get a 10% discount code for your next purchase!
    """
    
    await update.message.reply_text(feedback_text, parse_mode='Markdown', reply_markup=reply_markup)

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /promo command to manage promo codes."""
    args = context.args
    
    if args:
        promo_code = args[0].upper()
        await validate_promo_code(update, promo_code)
    else:
        keyboard = [
            [InlineKeyboardButton("🎁 Enter Promo Code", callback_data="enter_promo")],
            [InlineKeyboardButton("📋 View Available Codes", callback_data="show_promos")],
            [InlineKeyboardButton("🔔 Get Notified of New Deals", callback_data="promo_notify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        promo_text = """
🎁 **Promo Codes & Deals**

**Current Active Codes:**
• **TRUSTY20** - 20% off first month
• **STUDENT50** - 50% off for students (ID required)
• **BUNDLE25** - 25% off annual plans
• **WELCOME10** - 10% off for new customers
• **FEEDBACK10** - 10% off after leaving feedback

**💡 How to Use:**
1. Click "Enter Promo Code" below
2. Type your code exactly as shown
3. Apply it during checkout

**🔔 Want More Deals?**
Subscribe to notifications for exclusive promo codes!
        """
        
        await update.message.reply_text(promo_text, parse_mode='Markdown', reply_markup=reply_markup)

async def validate_promo_code(update, code):
    """Validate a promo code and provide feedback."""
    valid_codes = {
        "TRUSTY20": {"discount": "20%", "description": "20% off first month"},
        "STUDENT50": {"discount": "50%", "description": "50% off for students"},
        "BUNDLE25": {"discount": "25%", "description": "25% off annual plans"},
        "WELCOME10": {"discount": "10%", "description": "10% off for new customers"},
        "FEEDBACK10": {"discount": "10%", "description": "10% off after feedback"}
    }
    
    if code in valid_codes:
        promo = valid_codes[code]
        keyboard = [
            [InlineKeyboardButton("🛒 Apply to Order", callback_data=f"apply_promo_{code}")],
            [InlineKeyboardButton("📋 View Products", callback_data="view_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success_text = f"""
✅ **Promo Code Valid!**

**Code:** {code}
**Discount:** {promo['discount']}
**Description:** {promo['description']}

🎉 Great choice! This code is ready to use on your next purchase.

💡 **Next Steps:**
1. Browse our products
2. Add items to cart
3. Enter this code at checkout
4. Enjoy your savings!
        """
        
        await update.message.reply_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Try Another Code", callback_data="enter_promo")],
            [InlineKeyboardButton("📋 View Valid Codes", callback_data="show_promos")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❌ **Invalid Promo Code**\n\nCode '{code}' is not valid or has expired.\n\n💡 Check the spelling or view available codes below.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def smart_auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language messages with context-aware responses."""
    user = update.effective_user
    message_text = update.message.text.lower()
    user_id = user.id
    session = get_user_session(user_id)
    
    logger.info(f"💬 Smart reply from {user.first_name}: {message_text}")
    
    # Handle button presses from custom keyboard
    if update.message.text in ["🛍️ Products", "📦 Track Order", "🆘 Get Help", "💬 Live Chat", "⭐ Leave Feedback", "🎁 Promo Codes"]:
        if update.message.text == "🛍️ Products":
            await enhanced_products_command(update, context)
        elif update.message.text == "📦 Track Order":
            await track_order_command(update, context)
        elif update.message.text == "🆘 Get Help":
            await help_command(update, context)
        elif update.message.text == "💬 Live Chat":
            await support_ticket_command(update, context)
        elif update.message.text == "⭐ Leave Feedback":
            await feedback_command(update, context)
        elif update.message.text == "🎁 Promo Codes":
            await promo_command(update, context)
        return
    
    # Context-aware responses
    current_context = session.get('current_context')
    
    # Handle specific contexts
    if current_context == "tracking":
        await process_order_lookup(update, message_text.upper())
        return
    elif current_context == "promo_entry":
        await validate_promo_code(update, message_text.upper())
        update_user_session(user_id, current_context="general_chat")
        return
    elif current_context == "feedback_comment":
        session['feedback_comment'] = message_text
        await update.message.reply_text(
            f"Thank you for your feedback: '{message_text}'!\n\n🎁 Here's your 10% discount code: **FEEDBACK10**\n\nAnything else I can help with?",
            parse_mode='Markdown'
        )
        update_user_session(user_id, current_context="general_chat")
        return
    elif current_context == "faq_search":
        # Search FAQ for matching questions
        matches = [q for q in faq_data.keys() if any(word in q.lower() for word in message_text.split())]
        if matches:
            response = "🔍 **FAQ Search Results:**\n\n"
            for q in matches[:3]:  # Limit to 3 results
                response += f"❓ **{q}**\n{faq_data[q]}\n\n"
            response += "Was this helpful? Type another question or use /faq for more."
        else:
            response = "🔍 No FAQ matches found. Try rephrasing or use /faq to browse all questions."
        await update.message.reply_text(response, parse_mode='Markdown')
        update_user_session(user_id, current_context="general_chat")
        return
    
    # Order number detection
    order_match = re.search(r'tl-\d+', message_text)
    if order_match:
        order_num = order_match.group(0).upper()
        await process_order_lookup(update, order_num)
        update_user_session(user_id, current_context="order_lookup")
        return
    
    # Smart keyword detection with enhanced responses
    if any(word in message_text for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'start']):
        keyboard = [
            [InlineKeyboardButton("🛍️ Browse Products", callback_data="view_products")],
            [InlineKeyboardButton("📦 Track Order", callback_data="track_order")],
            [InlineKeyboardButton("🆘 Get Help", callback_data="get_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = f"👋 Hello {user.first_name}! Welcome back to Trusty Lads! 🎉\n\nI'm your enhanced AI assistant with lots of new features. What can I help you with today?"
        await update.message.reply_text(response, reply_markup=reply_markup)
    
    elif any(word in message_text for word in ['order', 'purchase', 'buy', 'price', 'cost', 'product']):
        await enhanced_products_command(update, context)
    
    elif any(word in message_text for word in ['track', 'tracking', 'shipment', 'delivery', 'where is']):
        await track_order_command(update, context)
    
    elif any(word in message_text for word in ['problem', 'issue', 'help', 'support', 'broken', 'not working', 'error']):
        await support_ticket_command(update, context)
    
    elif any(word in message_text for word in ['refund', 'return', 'cancel', 'money back']):
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
            [InlineKeyboardButton("🔍 View FAQ", callback_data="show_faq")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        response = f"🔄 **Refund/Cancellation Info**\n\n{faq_data['What\'s your refund policy?']}\n\nNeed more help? Contact support or check our FAQ."
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif any(word in message_text for word in ['ship', 'deliver', 'arrive']):
        keyboard = [
            [InlineKeyboardButton("📦 Track Order", callback_data="track_order")],
            [InlineKeyboardButton("🔍 View FAQ", callback_data="show_faq")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        response = f"🚚 **Shipping Info**\n\n{faq_data['How long does shipping take?']}\n\nWant to track an order or learn more?"
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    else:
        # Fallback to FAQ matching
        response = None
        for question, answer in faq_data.items():
            if any(word in message_text for word in question.lower().split()):
                response = f"🤖 **FAQ Answer**\n\n**{question}**\n{answer}"
                break
        
        if not response:
            response = "🤔 I didn't quite understand that. Could you rephrase? Or try /help to see all options!"
        
        keyboard = [
            [InlineKeyboardButton("🆘 Get Help", callback_data="get_help")],
            [InlineKeyboardButton("🔍 FAQ", callback_data="show_faq")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    update_user_session(user_id, current_context="general_chat")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("faq_"):
        faq_index = int(data.split("_")[1])
        questions = list(faq_data.keys())
        if faq_index < len(questions):
            question = questions[faq_index]
            answer = faq_data[question]
            
            keyboard = [
                [InlineKeyboardButton("❓ Another Question", callback_data="show_faq")],
                [InlineKeyboardButton("💬 Still Need Help?", callback_data="contact_support")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"**Q: {question}**\n\n**A:** {answer}\n\n💡 *Need more help? Use the buttons below*",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    elif data.startswith("rating_"):
        rating = int(data.split("_")[1])
        stars = "⭐" * rating
        
        keyboard = [
            [InlineKeyboardButton("📝 Leave Detailed Feedback", callback_data="detailed_feedback")],
            [InlineKeyboardButton("🎁 Get Discount Code", callback_data="get_feedback_discount")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Thank you for the {stars} rating!\n\n🎁 As a thank you, here's a 10% discount code: **FEEDBACK10**\n\nWould you like to leave more detailed feedback?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        session = get_user_session(user_id)
        session['last_rating'] = rating
    
    elif data == "contact_support":
        keyboard = [
            [InlineKeyboardButton("🎫 Create Ticket", callback_data="create_ticket")],
            [InlineKeyboardButton("💬 Live Chat", callback_data="live_chat")],
            [InlineKeyboardButton("📞 Request Callback", callback_data="request_callback")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📞 **Contact Support Options:**\n\n🎫 Create a support ticket\n💬 Start live chat\n📞 Request a callback\n\nWhat works best for you?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "detailed_feedback":
        await query.edit_message_text("📝 Please type your detailed feedback:")
        update_user_session(user_id, current_context="feedback_comment")
    
    elif data == "get_feedback_discount":
        await query.edit_message_text(
            "🎁 Your 10% discount code is **FEEDBACK10**!\n\nUse it at checkout. Anything else I can help with?",
            parse_mode='Markdown'
        )
        update_user_session(user_id, current_context="general_chat")
    
    elif data == "create_ticket":
        await support_ticket_command(query, context)
    
    elif data == "live_chat":
        await query.edit_message_text(
            "💬 Live chat is not available yet. Please create a support ticket with /support or call +1 (800) 555-0199.",
            parse_mode='Markdown'
        )
    
    elif data == "request_callback":
        await query.edit_message_text(
            "📞 Please provide your phone number, and we'll call you back within 24 hours.",
            parse_mode='Markdown'
        )
        update_user_session(user_id, current_context="callback_request")
    
    elif data == "view_products":
        await enhanced_products_command(query, context)
    
    elif data == "track_order":
        await track_order_command(query, context)
    
    elif data == "get_help":
        await help_command(query, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors that occur during bot operation."""
    logger.error(f"⚠️ Error occurred: {context.error}", exc_info=context.error)
    
    if update and update.message:
        await update.message.reply_text(
            "😖 Oops! Something went wrong. Our team has been notified. Please try again or contact support."
        )
    
    error_details = {
        "timestamp": datetime.now().isoformat(),
        "error": str(context.error),
        "update": str(update) if update else None,
        "user": update.effective_user.id if (update and update.effective_user) else None
    }
    logger.error(json.dumps(error_details, indent=2))

# --- BOT SETUP & STARTUP ---
def setup_handlers(application):
    """Set up all bot handlers for commands, messages, and callbacks."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("products", enhanced_products_command))
    application.add_handler(CommandHandler("track", track_order_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("support", support_ticket_command))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(CommandHandler("promo", promo_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_auto_reply_handler))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_error_handler(error_handler)

async def run_bot(max_retries=3, retry_delay=5):
    """Run the Telegram bot with retry logic for network errors."""
    global bot_running
    attempt = 0
    
    while attempt < max_retries:
        try:
            logger.info("🚀 Starting Trusty Lads Enhanced Bot...")
            
            application = ApplicationBuilder().token(BOT_TOKEN).build()
            setup_handlers(application)
            
            bot_running = True
            logger.info("🤖 Bot is now running and polling for updates...")
            await application.run_polling()
            break  # Exit loop if polling starts successfully
            
        except Conflict as e:
            logger.error("🔴 Another instance is already running. Shutting down...")
            break
        except (TimedOut, NetworkError) as e:
            attempt += 1
            logger.error(f"🟡 Network error (attempt {attempt}/{max_retries}): {e}. Retrying in {retry_delay} seconds...")
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
            else:
                logger.error("🔴 Max retries reached. Bot failed to start.")
                raise
        except Exception as e:
            logger.error(f"🔴 Critical error: {e}")
            raise
        finally:
            bot_running = False
            logger.info("🛑 Bot has been stopped")

def run_flask():
    """Run the Flask server for the dashboard."""
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=False)

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error("🔴 BOT_TOKEN is not set. Please set it in the .env file.")
        exit(1)
    
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run the bot in the main thread
    asyncio.run(run_bot())