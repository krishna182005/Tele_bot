# main.py - Trusty Lads Customer Service Bot with Enhanced Button Features

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import json
import datetime
import os
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Your bot token from @BotFather (stored securely in .env file or environment)
BOT_TOKEN = os.getenv('BOT_TOKEN', os.environ.get('BOT_TOKEN', 'PASTE_YOUR_TOKEN_HERE'))

# Validate bot token
if BOT_TOKEN == 'PASTE_YOUR_TOKEN_HERE' or not BOT_TOKEN:
    print("❌ ERROR: Bot token not found!")
    print("🔐 Please set BOT_TOKEN in environment variables or .env file")
    exit(1)

# Flask app for 24/7 hosting
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return """
    <html>
        <head><title>Trusty Lads Bot</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h1>🤖 Trusty Lads Bot is Online!</h1>
            <p>✅ Bot Status: <strong style="color: green;">Running</strong></p>
            <p>🕐 Last Check: <span id="time"></span></p>
            <p>📱 Start chatting: <a href="https://t.me/YOUR_BOT_USERNAME">@YOUR_BOT_USERNAME</a></p>
            <script>
                document.getElementById('time').innerHTML = new Date().toLocaleString();
            </script>
        </body>
    </html>
    """

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    """Starts Flask server in a separate thread to keep bot alive 24/7"""
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🌐 Flask server started for 24/7 hosting!")

# Enhanced Product Categories
PRODUCTS = {
    "Hair Care": [
        {"name": "🖤 Hair Comb", "price": 199, "description": "Premium wooden hair comb"},
        {"name": "💇‍♂️ Hair Gel", "price": 149, "description": "Strong hold styling gel"},
        {"name": "🧴 Shampoo", "price": 299, "description": "Natural ingredients shampoo"},
        {"name": "✨ Hair Serum", "price": 399, "description": "Nourishing hair serum"}
    ],
    "Beard Care": [
        {"name": "🧴 Beard Oil", "price": 249, "description": "Premium beard conditioning oil"},
        {"name": "🪒 Beard Balm", "price": 199, "description": "Styling and conditioning balm"},
        {"name": "✂️ Beard Trimmer", "price": 899, "description": "Electric precision trimmer"},
        {"name": "🧼 Beard Wash", "price": 179, "description": "Gentle cleansing beard wash"}
    ],
    "Electronics": [
        {"name": "🎧 Bluetooth Earbuds", "price": 799, "description": "Wireless stereo earbuds"},
        {"name": "📱 Phone Case", "price": 299, "description": "Protective phone case"},
        {"name": "⌚ Smart Watch", "price": 1299, "description": "Fitness tracking smartwatch"},
        {"name": "🔌 Power Bank", "price": 699, "description": "10000mAh portable charger"}
    ],
    "Accessories": [
        {"name": "👔 Tie", "price": 349, "description": "Silk formal tie"},
        {"name": "🧢 Cap", "price": 199, "description": "Stylish baseball cap"},
        {"name": "👓 Sunglasses", "price": 499, "description": "UV protection sunglasses"},
        {"name": "💼 Wallet", "price": 599, "description": "Leather bi-fold wallet"}
    ]
}

# User cart and state storage (in production, use a database)
user_carts = {}
user_states = {}

# Create orders directory if it doesn't exist
if not os.path.exists("orders"):
    os.makedirs("orders")

# Custom keyboard for main menu
MAIN_MENU_KEYBOARD = [
    ["🛒 Browse Products", "🛍️ View Cart"],
    ["📦 My Orders", "ℹ️ About Us"],
    ["📞 Contact Support", "💰 Offers"]
]

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"
    
    welcome_text = """
🌟 *Welcome to Trusty Lads!* 🌟

Your one-stop shop for:
✨ Premium Hair Care Products
🧔 Professional Beard Care
📱 Latest Electronics
👔 Stylish Accessories

Choose an option below to get started! 👇
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
    )

# Show product categories
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    keyboard = []
    for category in PRODUCTS.keys():
        keyboard.append([InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")])
    
    await update.message.reply_text(
        "🛒 *Choose a Product Category:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Show products in category
async def show_products_in_category(query, category):
    keyboard = []
    text = f"📂 *{category} Products:*\n\n"
    
    for i, product in enumerate(PRODUCTS[category]):
        text += f"{i+1}. {product['name']} - ₹{product['price']}\n   _{product['description']}_\n\n"
        keyboard.append([InlineKeyboardButton(f"🛒 Add {product['name']}", callback_data=f"add_{category}_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_categories")])
    keyboard.append([InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")])
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle cart operations
async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await update.message.reply_text(
            "🛍️ Your cart is empty! Browse products to add items.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
        )
        return
    
    text = "🛍️ *Your Cart:*\n\n"
    total = 0
    
    for i, item in enumerate(cart):
        text += f"{i+1}. {item['name']} - ₹{item['price']} x{item['quantity']}\n"
        total += item['price'] * item['quantity']
    
    text += f"\n💰 *Total: ₹{total}*"
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")],
        [InlineKeyboardButton("📦 Checkout", callback_data="checkout")],
        [InlineKeyboardButton("🔙 Continue Shopping", callback_data="back_categories")]
    ]
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Show offers
async def show_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    offers_text = """
🎉 *Current Offers & Deals!* 🎉

💸 *FLAT20* - Get 20% off on orders above ₹500
🎁 *NEWUSER* - 15% off for first-time buyers  
🛍️ *COMBO50* - Buy 2 get 1 free on hair care products
⚡ *FLASH10* - Extra 10% off on electronics
🎯 *BULK25* - 25% off on orders above ₹1000

*Offer codes are valid till month end!*

👇 *Enter an offer code or browse products:*
    """
    
    keyboard = [
        [InlineKeyboardButton("🎁 Apply Offer Code", callback_data="apply_offer")],
        [InlineKeyboardButton("🛒 Browse Products", callback_data="back_categories")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
    ]
    
    await update.message.reply_text(
        offers_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Show about us
async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    about_text = """
ℹ️ *About Trusty Lads*

🏢 We are a premium lifestyle brand offering:
• Quality grooming products
• Latest electronics & accessories
• Affordable pricing with premium quality

📍 *Address:* 123 Fashion Street, Style City
📞 *Phone:* +91-9876543210
📧 *Email:* support@trustylads.com
🌐 *Website:* www.trustylads.com

⭐ *Why Choose Us?*
✅ Genuine Products
✅ Fast Delivery 
✅ 24/7 Customer Support
✅ Easy Returns & Exchanges
    """
    
    await update.message.reply_text(
        about_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
    )

# Contact support
async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    contact_text = """
📞 *Contact Support*

🎧 *Customer Care:* +91-9876543210
📧 *Email:* support@trustylads.com
💬 *WhatsApp:* +91-9876543210

⏰ *Support Hours:*
Monday - Saturday: 9:00 AM - 8:00 PM
Sunday: 10:00 AM - 6:00 PM

📝 *For Order Issues:*
Please provide your order ID and describe the issue.

🔄 *For Returns/Exchanges:*
Contact us within 7 days of delivery.

👇 *Choose an option:*
    """
    
    keyboard = [
        [InlineKeyboardButton("🎫 Create Support Ticket", callback_data="create_support_ticket")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
    ]
    
    await update.message.reply_text(
        contact_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle checkout process
async def checkout(query, user_id):
    cart = user_carts.get(user_id, [])
    if not cart:
        await query.edit_message_text(
            "🛍️ Your cart is empty!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Browse Products", callback_data="back_categories")]
            ])
        )
        return
    
    user_states[user_id] = "awaiting_order_details"
    
    text = "📦 *Checkout Process*\n\n"
    text += "Please provide the following details in this format:\n\n"
    text += "*Name:* Your Full Name\n"
    text += "*Phone:* Your Phone Number\n" 
    text += "*Address:* Your Complete Address\n"
    text += "*Payment:* COD/Online\n"
    text += "*Offer Code:* (if any)\n\n"
    text += "Example:\n"
    text += "Name: John Doe\n"
    text += "Phone: 9876543210\n"
    text += "Address: 123 Main St, City, PIN\n"
    text += "Payment: COD\n"
    text += "Offer Code: FLAT20"
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Cancel Checkout", callback_data="back_categories")]
        ])
    )

# Handle callback queries (inline button clicks)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query or not update.effective_user:
        return
        
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    if not data:
        return
    
    await query.answer()
    
    if data == "back_main":
        await start_callback(query)
    elif data == "back_categories":
        await show_categories_callback(query)
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        await show_products_in_category(query, category)
    elif data.startswith("add_"):
        parts = data.split("_")
        if len(parts) >= 3:
            category = parts[1]
            try:
                product_index = int(parts[2])
                await add_to_cart(query, user_id, category, product_index)
            except (ValueError, IndexError):
                await query.edit_message_text(
                    "❌ Invalid product selection!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Categories", callback_data="back_categories")]
                    ])
                )
    elif data == "clear_cart":
        user_carts[user_id] = []
        await query.edit_message_text(
            "🗑️ Cart cleared successfully!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Browse Products", callback_data="back_categories")]
            ])
        )
    elif data == "checkout":
        await checkout(query, user_id)
    elif data == "view_cart":
        await view_cart_callback(query, user_id)
    elif data == "apply_offer":
        user_states[user_id] = "awaiting_offer_code"
        await query.edit_message_text(
            "🎁 Please enter your offer code:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]
            ])
        )
    elif data == "create_support_ticket":
        user_states[user_id] = "awaiting_support_issue"
        await query.edit_message_text(
            "🎫 Please describe your issue or question:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]
            ])
        )

# Add product to cart
async def add_to_cart(query, user_id, category, product_index):
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    product = PRODUCTS[category][product_index]
    
    # Check if product already in cart
    for item in user_carts[user_id]:
        if item['name'] == product['name']:
            item['quantity'] += 1
            await query.edit_message_text(
                f"✅ {product['name']} quantity updated in cart!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")],
                    [InlineKeyboardButton("🔙 Continue Shopping", callback_data="back_categories")]
                ])
            )
            return
    
    # Add new product to cart
    user_carts[user_id].append({
        'name': product['name'],
        'price': product['price'],
        'quantity': 1,
        'category': category
    })
    
    await query.edit_message_text(
        f"✅ {product['name']} added to cart!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")],
            [InlineKeyboardButton("🔙 Continue Shopping", callback_data="back_categories")]
        ])
    )

# Callback versions for inline buttons
async def start_callback(query):
    welcome_text = """
🌟 *Welcome to Trusty Lads!* 🌟

Your one-stop shop for:
✨ Premium Hair Care Products
🧔 Professional Beard Care
📱 Latest Electronics
👔 Stylish Accessories

Choose an option below to get started! 👇
    """
    
    await query.edit_message_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
    )

async def show_categories_callback(query):
    keyboard = []
    for category in PRODUCTS.keys():
        keyboard.append([InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")])
    
    await query.edit_message_text(
        "🛒 *Choose a Product Category:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def view_cart_callback(query, user_id):
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await query.edit_message_text(
            "🛍️ Your cart is empty! Browse products to add items.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Browse Products", callback_data="back_categories")]
            ])
        )
        return
    
    text = "🛍️ *Your Cart:*\n\n"
    total = 0
    
    for i, item in enumerate(cart):
        text += f"{i+1}. {item['name']} - ₹{item['price']} x{item['quantity']}\n"
        total += item['price'] * item['quantity']
    
    text += f"\n💰 *Total: ₹{total}*"
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")],
        [InlineKeyboardButton("📦 Checkout", callback_data="checkout")],
        [InlineKeyboardButton("🔙 Continue Shopping", callback_data="back_categories")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Enhanced message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return
        
    text = update.message.text
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, "main_menu")

    if user_state == "awaiting_order_details":
        await process_order(update, context, user_id, text)
    elif user_state == "awaiting_offer_code":
        await validate_offer_code(update, context, user_id, text)
    elif user_state == "awaiting_support_issue":
        await process_support_issue(update, context, user_id, text)
    elif "Browse Products" in text:
        await show_categories(update, context)
    elif "View Cart" in text:
        await view_cart(update, context)
    elif "About Us" in text:
        await about_us(update, context)
    elif "Contact Support" in text:
        await contact_support(update, context)
    elif "Offers" in text:
        await show_offers(update, context)
    elif "My Orders" in text:
        await show_my_orders(update, context)
    else:
        await update.message.reply_text(
            "🤔 I didn't understand that. Please use the menu buttons below or type /start to see all options.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
        )

# Validate offer code
async def validate_offer_code(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, code):
    valid_codes = {
        "FLAT20": {"discount": "20%", "min_order": 500},
        "NEWUSER": {"discount": "15%", "min_order": 0},
        "COMBO50": {"discount": "Buy 2 get 1 free", "category": "Hair Care"},
        "FLASH10": {"discount": "10%", "category": "Electronics"},
        "BULK25": {"discount": "25%", "min_order": 1000}
    }
    
    code = code.upper()
    if code in valid_codes:
        user_states[user_id] = "main_menu"
        await update.message.reply_text(
            f"✅ Offer code '{code}' is valid! Apply it during checkout.\n\nDiscount: {valid_codes[code]['discount']}",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Try Another Code", callback_data="apply_offer")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
        ]
        await update.message.reply_text(
            f"❌ Invalid offer code: {code}\n\nTry another code or return to the main menu.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Process support issue
async def process_support_issue(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, issue):
    ticket_id = f"TKT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    user_name = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else "Unknown"
    
    # Save support ticket to file
    with open("orders/support_tickets.txt", "a", encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"TICKET ID: {ticket_id}\n")
        f.write(f"DATE: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"CUSTOMER: {user_name}\n")
        f.write(f"USER ID: {user_id}\n")
        f.write(f"ISSUE: {issue}\n")
        f.write(f"{'='*50}\n")
    
    user_states[user_id] = "main_menu"
    await update.message.reply_text(
        f"🎫 Support ticket created!\n\nTicket ID: {ticket_id}\nOur team will respond within 24 hours.\n\nThank you for reaching out!",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
    )

# Show user's order history
async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    orders_file = f"orders/user_{user_id}_orders.json"
    
    if not os.path.exists(orders_file):
        await update.message.reply_text(
            "📦 You haven't placed any orders yet!",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
        )
        return
    
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
        
        if not orders:
            await update.message.reply_text(
                "📦 You haven't placed any orders yet!",
                reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
            )
            return
        
        text = "📦 *Your Order History:*\n\n"
        for order in orders[-5:]:  # Show last 5 orders
            text += f"🆔 *Order ID:* {order['order_id']}\n"
            text += f"📅 *Date:* {order['date']}\n"
            text += f"💰 *Total:* ₹{order['total']}\n"
            text += f"📋 *Status:* {order['status']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🛒 Browse Products", callback_data="back_categories")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception:
        await update.message.reply_text(
            "❌ Error loading orders. Please contact support.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
        )

# Process order details
async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, order_details):
    if not update.message:
        return
        
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await update.message.reply_text(
            "🛍️ Your cart is empty!",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
        )
        return
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    # Generate order ID
    order_id = f"TL{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Get user name safely
    user_name = "Unknown"
    if update.effective_user and update.effective_user.first_name:
        user_name = update.effective_user.first_name
    
    # Create order data
    order_data = {
        'order_id': order_id,
        'user_id': user_id,
        'user_name': user_name,
        'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'items': cart,
        'total': total,
        'customer_details': order_details,
        'status': 'Confirmed'
    }
    
    # Save order to file
    orders_file = f"orders/user_{user_id}_orders.json"
    orders = []
    
    if os.path.exists(orders_file):
        with open(orders_file, 'r') as f:
            orders = json.load(f)
    
    orders.append(order_data)
    
    with open(orders_file, 'w') as f:
        json.dump(orders, f, indent=2)
    
    # Save to admin orders file
    with open("orders/all_orders.txt", "a", encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"ORDER ID: {order_id}\n")
        f.write(f"DATE: {order_data['date']}\n")
        f.write(f"CUSTOMER: {user_name}\n")
        f.write(f"USER ID: {user_id}\n")
        f.write(f"DETAILS:\n{order_details}\n")
        f.write(f"ITEMS:\n")
        for item in cart:
            f.write(f"- {item['name']} x{item['quantity']} = ₹{item['price'] * item['quantity']}\n")
        f.write(f"TOTAL: ₹{total}\n")
        f.write(f"{'='*50}\n")
    
    # Clear cart and reset state
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"
    
    # Send confirmation
    confirmation_text = f"""
✅ *Order Confirmed!*

🆔 *Order ID:* {order_id}
💰 *Total Amount:* ₹{total}
📅 *Date:* {order_data['date']}

📦 Your order has been received and will be processed within 24 hours.
📞 We'll contact you soon for confirmation!

*Thank you for shopping with Trusty Lads!* 🙏
    """
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
    )

# Add help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    help_text = """
🆘 *Help & Commands*

*Available Commands:*
/start - Start the bot and show main menu
/help - Show this help message

*How to Use:*
1️⃣ Use 🛒 Browse Products to see our catalog
2️⃣ Add items to cart using inline buttons  
3️⃣ Use 🛍️ View Cart to review your items
4️⃣ Click 📦 Checkout when ready to order
5️⃣ Provide your details to complete the order

*Need Help?*
Use 📞 Contact Support for assistance!
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)
    )

# Telegram bot function
def run_telegram_bot():
    """Run the Telegram bot in a separate thread"""
    try:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        print("🤖 Trusty Lads Bot is running...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error starting Telegram bot: {e}")
        print("🔍 Check if your BOT_TOKEN is correct")

# Main function
def main():
    print("🔐 Checking bot token...")
    
    # Verify token is properly loaded
    if not BOT_TOKEN or BOT_TOKEN == 'PASTE_YOUR_TOKEN_HERE':
        print("❌ Bot token not found!")
        return
    
    print("✅ Bot token loaded successfully!")
    
    # Start Flask server for 24/7 hosting
    keep_alive()
    
    # Start Telegram bot in a separate thread
    bot_thread = Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    print("🌐 Bot is running on multiple platforms:")
    print("   • Telegram Bot: ✅ Active")
    print("   • Web Server: ✅ Active")
    print("   • Ready for 24/7 hosting!")
    
    # Keep the main thread alive
    try:
        bot_thread.join()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")

if __name__ == "__main__":
    main()