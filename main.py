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

print(f"🔍 BOT_TOKEN found: {'Yes' if BOT_TOKEN else 'No'}")

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
    return jsonify({
        "active_sessions": len(user_sessions),
        "user_data": {str(k): v for k, v in user_sessions.items()},
        "total_messages": sum(session.get('message_count', 0) for session in user_sessions.values())
    })

# --- USER SESSION MANAGEMENT ---
def get_user_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "first_interaction": datetime.now(),
            "message_count": 0,
            "current_context": None,
            "support_tickets": [],
            "preferences": {},
            "last_order": None
        }
    return user_sessions[user_id]

def update_user_session(user_id, **kwargs):
    session = get_user_session(user_id)
    session.update(kwargs)
    session['message_count'] += 1
    session['last_interaction'] = datetime.now()

# --- ENHANCED BOT HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_user_session(user.id)
    logger.info(f"👋 User started bot: {user.first_name} (ID: {user.id})")
    
    # Create custom keyboard
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
    # Create inline keyboard for better UX
    keyboard = [
        [InlineKeyboardButton("🛍️ Products", callback_data="help_products"),
         InlineKeyboardButton("📦 Orders", callback_data="help_orders")],
        [InlineKeyboardButton("🚚 Shipping", callback_data="help_shipping"),
         InlineKeyboardButton("💰 Refunds", callback_data="help_refunds")],
        [InlineKeyboardButton("🔍 FAQ", callback_data="show_faq"),
         InlineKeyboardButton("📞 Contact", callback_data="help_contact")]
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

# --- CALLBACK QUERY HANDLER ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Handle different callback types
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
        
        # Save rating to user session
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

# --- SMART AUTO-REPLY HANDLER ---
async def smart_auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text.lower()
    user_id = user.id
    session = get_user_session(user_id)
    
    logger.info(f"💬 Smart reply from {user.first_name}: {update.message.text}")
    
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
            [InlineKeyboardButton("💰 Process Refund", callback_data="process_refund")],
            [InlineKeyboardButton("📋 Return Policy", callback_data="return_policy")],
            [InlineKeyboardButton("📞 Speak to Agent", callback_data="refund_agent")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = "💰 **Refund & Return Help**\n\nNo worries! We have a 30-day money-back guarantee. I can help you:\n\n• Process your refund instantly\n• Explain our return policy\n• Connect you with a specialist\n\nWhat would you like to do?"
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif any(word in message_text for word in ['promo', 'discount', 'coupon', 'code', 'deal', 'offer']):
        await promo_command(update, context)
    
    elif any(word in message_text for word in ['feedback', 'review', 'rating', 'complain', 'suggest']):
        await feedback_command(update, context)
    
    elif any(word in message_text for word in ['faq', 'question', 'frequently asked', 'common questions']):
        await faq_command(update, context)
    
    elif any(word in message_text for word in ['thank', 'thanks', 'appreciate', 'awesome', 'great']):
        keyboard = [
            [InlineKeyboardButton("⭐ Rate Experience", callback_data="rate_experience")],
            [InlineKeyboardButton("🎁 Get Rewards", callback_data="loyalty_rewards")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = f"😊 You're so welcome, {user.first_name}! That's what we're here for!\n\n🎉 Since you're happy, would you like to:\n• Rate your experience (get 10% off!)\n• Check out our loyalty rewards"
        await update.message.reply_text(response, reply_markup=reply_markup)
    
    elif any(word in message_text for word in ['human', 'agent', 'person', 'speak to', 'talk to']):
        keyboard = [
            [InlineKeyboardButton("👨‍💼 Sales Agent", callback_data="connect_sales")],
            [InlineKeyboardButton("🔧 Technical Support", callback_data="connect_tech")],
            [InlineKeyboardButton("💰 Billing Support", callback_data="connect_billing")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = "👥 **Connect with Human Agent**\n\nI'll connect you with the right specialist:\n\n👨‍💼 **Sales** - Product questions & purchases\n🔧 **Technical** - App/website issues\n💰 **Billing** - Payment & subscription help\n\nWho would you like to speak with?"
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    # Email detection for order lookup
    elif '@' in message_text and '.' in message_text:
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message_text)
        if email_match:
            email = email_match.group(0)
            keyboard = [
                [InlineKeyboardButton("🔍 Search Orders", callback_data=f"search_email_{email}")],
                [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            response = f"📧 **Email Detected:** {email}\n\nI can search for orders associated with this email address. Would you like me to look up your order history?"
            await update.message.reply_text(response, reply_markup=reply_markup)
    
    # Phone number detection
    elif re.search(r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', message_text):
        phone_match = re.search(r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', message_text)
        phone = phone_match.group(0)
        
        keyboard = [
            [InlineKeyboardButton("📱 Verify Phone", callback_data=f"verify_phone_{phone}")],
            [InlineKeyboardButton("🔍 Search Orders", callback_data=f"search_phone_{phone}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = f"📱 **Phone Number Detected:** {phone}\n\nI can help you:\n• Verify this number for your account\n• Search for orders using this phone\n\nWhat would you like to do?"
        await update.message.reply_text(response, reply_markup=reply_markup)
    
    # Default intelligent response
    else:
        keyboard = [
            [InlineKeyboardButton("🛍️ Products", callback_data="view_products"),
             InlineKeyboardButton("📦 Track Order", callback_data="track_order")],
            [InlineKeyboardButton("🆘 Get Help", callback_data="get_help"),
             InlineKeyboardButton("💬 Live Chat", callback_data="live_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = f"""
✨ **Thanks for your message, {user.first_name}!**

I received: *"{update.message.text}"*

🤖 I'm your enhanced AI assistant with smart features! Here's what I can help with:

🎯 **Instant Help:**
• Product info & ordering
• Order tracking & status
• Refunds & returns
• Technical support
• Promo codes & deals

💡 **Smart Features:**
• Context-aware responses
• Order lookup by email/phone
• Interactive menus & buttons
• Real-time support tickets

👆 *Use the buttons below or just tell me what you need!*

**Message #{session['message_count']}** | Session time: {(datetime.now() - session['first_interaction']).seconds // 60} min
        """
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    update_user_session(user_id, current_context="general_chat")

# --- ADDITIONAL ENHANCED FEATURES ---

async def process_advanced_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("product_"):
        product_type = data.split("_")[1]
        
        if product_type == "premium":
            keyboard = [
                [InlineKeyboardButton("🛒 Order Now - $99", callback_data="order_premium")],
                [InlineKeyboardButton("💬 Chat with Sales", callback_data="sales_chat")],
                [InlineKeyboardButton("📊 View Features", callback_data="premium_features")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                """🔥 **Premium Package - $99/month**

**✨ VIP Features:**
• <2 minute response time guarantee
• Dedicated account manager (Sarah M.)
• 24/7 priority phone support
• Advanced analytics dashboard
• Custom integrations available
• Monthly strategy calls
• Exclusive member events

**🎁 Limited Time:** First month 50% off!

**💰 Total Value:** $300+/month
**Your Price:** Just $99/month

**🏆 Perfect for:** Growing businesses, enterprises, power users

Ready to upgrade your experience?""",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    elif data.startswith("ticket_"):
        ticket_type = data.split("_")[1]
        ticket_id = data.split("_")[2]
        
        session = get_user_session(user_id)
        ticket = {
            "id": ticket_id,
            "type": ticket_type,
            "created": datetime.now(),
            "status": "Open",
            "priority": "Normal"
        }
        session['support_tickets'].append(ticket)
        
        keyboard = [
            [InlineKeyboardButton("📝 Add Details", callback_data=f"ticket_details_{ticket_id}")],
            [InlineKeyboardButton("📞 Request Call", callback_data=f"ticket_call_{ticket_id}")],
            [InlineKeyboardButton("📧 Email Updates", callback_data=f"ticket_email_{ticket_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"""✅ **Support Ticket Created**

**Ticket ID:** {ticket_id}
**Type:** {ticket_type.title()}
**Status:** Open
**Priority:** Normal
**Agent:** Will be assigned within 15 minutes

**Next Steps:**
• Add more details about your issue
• Request a callback if urgent
• Get email updates on progress

**Response Time:**
• Premium: <15 minutes
• Standard: <2 hours
• Basic: <24 hours

We'll resolve this quickly!""",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("apply_promo_"):
        promo_code = data.split("_")[2]
        
        keyboard = [
            [InlineKeyboardButton("🛒 Shop Now", callback_data="view_products")],
            [InlineKeyboardButton("💾 Save Code", callback_data=f"save_promo_{promo_code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"""✅ **Promo Code Ready!**

**Code:** {promo_code}
**Status:** Active and ready to use

🎉 **How to Apply:**
1. Browse our products
2. Add items to your cart
3. Enter code at checkout
4. Enjoy your discount!

💡 **Tip:** This code is now saved to your account for easy access during checkout.

Ready to start shopping?""",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

# --- WEBHOOK CLEARING & CONFLICT RESOLUTION ---
async def clear_existing_webhooks():
    try:
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Cleared existing webhooks")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Could not clear webhooks: {e}")
        return False

# --- ENHANCED BOT SETUP ---
async def setup_enhanced_bot():
    global bot_running
    if not BOT_TOKEN:
        logger.error("❌ CRITICAL: BOT_TOKEN not found!")
        return None
    
    try:
        await clear_existing_webhooks()
        await asyncio.sleep(2)
        
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add all command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("products", enhanced_products_command))
        application.add_handler(CommandHandler("track", track_order_command))
        application.add_handler(CommandHandler("faq", faq_command))
        application.add_handler(CommandHandler("support", support_ticket_command))
        application.add_handler(CommandHandler("feedback", feedback_command))
        application.add_handler(CommandHandler("promo", promo_command))
        
        # Add callback query handlers
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(CallbackQueryHandler(process_advanced_callback))
        
        # Add message handler for smart auto-reply
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_auto_reply_handler))
        
        logger.info("✅ Enhanced bot setup complete with all features enabled")
        return application
        
    except Exception as e:
        logger.error(f"❌ Enhanced bot setup failed: {e}")
        return None

async def run_enhanced_bot_async():
    global bot_running
    application = await setup_enhanced_bot()
    if not application:
        return
    
    try:
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                bot_info = await application.bot.get_me()
                logger.info(f"🤖 Enhanced Bot @{bot_info.username} starting... (Attempt {retry_count + 1})")
                
                await application.initialize()
                await application.start()
                await application.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                
                bot_running = True
                logger.info("🚀 Enhanced Bot is now running with all features!")
                logger.info("✨ Features active: Smart replies, Order tracking, Support tickets, FAQ, Feedback, Promos")
                
                while bot_running:
                    await asyncio.sleep(1)
                break
                
            except Conflict as e:
                retry_count += 1
                logger.error(f"❌ Conflict error (attempt {retry_count}): {e}")
                if retry_count < max_retries:
                    wait_time = retry_count * 10
                    logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    await clear_existing_webhooks()
                    await asyncio.sleep(5)
                else:
                    logger.error("❌ Max retries reached. Enhanced bot startup failed.")
            
            except (TimedOut, NetworkError) as e:
                logger.error(f"⚠️ Network error: {e}")
                await asyncio.sleep(5)
                continue
            
            except Exception as e:
                logger.error(f"❌ Enhanced bot error: {e}")
                break
    
    finally:
        bot_running = False
        try:
            if application:
                await application.stop()
                logger.info("🛑 Enhanced bot stopped")
        except Exception:
            pass

def run_enhanced_bot_thread():
    logger.info("🧵 Starting enhanced bot thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_enhanced_bot_async())
    except KeyboardInterrupt:
        logger.info("⏹️ Enhanced bot interrupted")
    except Exception as e:
        logger.error(f"❌ Enhanced bot thread error: {e}")
    finally:
        loop.close()

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    logger.info("🚀 Starting Enhanced Trusty Lads Customer Service Bot...")
    logger.info("✨ New Features: Smart replies, Interactive menus, Order tracking, Support tickets, FAQ system, Feedback, Promos")
    
    bot_thread = Thread(target=run_enhanced_bot_thread, daemon=True)
    bot_thread.start()
    logger.info("✅ Enhanced bot thread started")
    
    run_flask()