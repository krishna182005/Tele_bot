# main.py
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from dotenv import load_dotenv
import os
import json
import datetime

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in environment variables!")
    exit(1)

# Flask app for keeping service alive on Render
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Trusty Lads Bot is Live and Running!"

# ... (all your other functions like PRODUCTS, start, view_cart, etc. go here)
# Copy the entire first code block from our previous conversation here.
# It is the correct and complete version.

# ---- PASTE THE FULL E-COMMERCE BOT CODE HERE ----

# Let's re-paste the full bot code to be 100% sure:

@flask_app.route('/health')
def health():
    return {"status": "healthy", "service": "trusty-lads-bot"}

# Product catalog
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
    ]
}

# User data storage
user_carts = {}
user_states = {}

# Create orders directory
os.makedirs("orders", exist_ok=True)

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"
    
    buttons = [
        ["🛒 Browse Products", "🛍️ View Cart"],
        ["📦 My Orders", "ℹ️ About Us"],
        ["📞 Contact Support", "💰 Offers"]
    ]
    
    welcome_text = """
🌟 *Welcome to Trusty Lads!* 🌟

Your one-stop shop for:
✨ Premium Hair Care Products
🧔 Professional Beard Care
📱 Latest Electronics

Choose an option below to get started! 👇
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for category in PRODUCTS.keys():
        keyboard.append([InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")])
    
    await update.message.reply_text(
        "🛒 *Choose a Product Category:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_products_in_category(query, category):
    keyboard = []
    text = f"📂 *{category} Products:*\n\n"
    
    for i, product in enumerate(PRODUCTS[category]):
        text += f"{i+1}. {product['name']} - ₹{product['price']}\n   _{product['description']}_\n\n"
        keyboard.append([InlineKeyboardButton(f"🛒 Add {product['name']}", callback_data=f"add_{category}_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_categories")])
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await update.message.reply_text("🛍️ Your cart is empty! Browse products to add items.")
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

async def show_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    offers_text = """
🎉 *Current Offers & Deals!* 🎉

💸 *FLAT20* - Get 20% off on orders above ₹500
🎁 *NEWUSER* - 15% off for first-time buyers  
🛍️ *COMBO50* - Buy 2 get 1 free on hair care products
⚡ *FLASH10* - Extra 10% off on electronics

*Offer codes are valid till month end!*
    """
    await update.message.reply_text(offers_text, parse_mode='Markdown')

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
ℹ️ *About Trusty Lads*

🏢 We are a premium lifestyle brand offering:
• Quality grooming products
• Latest electronics & accessories
• Affordable pricing with premium quality

📍 *Address:* 123 Fashion Street, Style City
📞 *Phone:* +91-9876543210
📧 *Email:* support@trustylads.com

⭐ *Why Choose Us?*
✅ Genuine Products
✅ Fast Delivery 
✅ 24/7 Customer Support
✅ Easy Returns & Exchanges
    """
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_text = """
📞 *Contact Support*

🎧 *Customer Care:* +91-9876543210
📧 *Email:* support@trustylads.com
💬 *WhatsApp:* +91-9876543210

⏰ *Support Hours:*
Monday - Saturday: 9:00 AM - 8:00 PM
Sunday: 10:00 AM - 6:00 PM
    """
    await update.message.reply_text(contact_text, parse_mode='Markdown')

async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders_file = f"orders/user_{user_id}_orders.json"
    
    if not os.path.exists(orders_file):
        await update.message.reply_text("📦 You haven't placed any orders yet!")
        return
    
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
        
        if not orders:
            await update.message.reply_text("📦 You haven't placed any orders yet!")
            return
        
        text = "📦 *Your Order History:*\n\n"
        for order in orders[-3:]:  # Show last 3 orders
            text += f"🆔 *Order ID:* {order['order_id']}\n"
            text += f"📅 *Date:* {order['date']}\n"
            text += f"💰 *Total:* ₹{order['total']}\n"
            text += f"📋 *Status:* {order['status']}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text("❌ Error loading orders. Please contact support.")

async def checkout(query, user_id):
    cart = user_carts.get(user_id, [])
    if not cart:
        await query.edit_message_text("🛍️ Your cart is empty!")
        return
    
    user_states[user_id] = "awaiting_order_details"
    
    text = "📦 *Checkout Process*\n\n"
    text += "Please provide your details in this format:\n\n"
    text += "*Name:* Your Full Name\n"
    text += "*Phone:* Your Phone Number\n" 
    text += "*Address:* Your Complete Address\n"
    text += "*Payment:* COD/Online\n\n"
    text += "Example:\n"
    text += "Name: John Doe\n"
    text += "Phone: 9876543210\n"
    text += "Address: 123 Main St, City, PIN\n"
    text += "Payment: COD"
    
    await query.edit_message_text(text, parse_mode='Markdown')

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, order_details):
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await update.message.reply_text("🛍️ Your cart is empty!")
        return
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    # Generate order ID
    order_id = f"TL{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Get user name
    user_name = update.effective_user.first_name or "Unknown"
    
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
            try:
                orders = json.load(f)
            except json.JSONDecodeError:
                orders = []
    
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
    
    await update.message.reply_text(confirmation_text, parse_mode='Markdown')

async def add_to_cart(query, user_id, category, product_index):
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    product = PRODUCTS[category][product_index]
    
    # Check if product already in cart
    for item in user_carts[user_id]:
        if item['name'] == product['name']:
            item['quantity'] += 1
            await query.answer(f"✅ {product['name']} quantity updated in cart!")
            return
    
    # Add new product to cart
    user_carts[user_id].append({
        'name': product['name'],
        'price': product['price'],
        'quantity': 1,
        'category': category
    })
    
    await query.answer(f"✅ {product['name']} added to cart!")

# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    await query.answer() # Answer callback query quickly
    
    if data == "back_main":
        # This case is tricky as we can't edit a message to show ReplyKeyboard.
        # It's better to send a new message or handle this flow differently.
        # For now, let's just edit the text.
        welcome_text = "Choose an option from the main menu below 👇"
        await query.edit_message_text(welcome_text, parse_mode='Markdown')
    
    elif data == "back_categories":
        keyboard = []
        for category in PRODUCTS.keys():
            keyboard.append([InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")])
        
        await query.edit_message_text(
            "🛒 *Choose a Product Category:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        await show_products_in_category(query, category)
    
    elif data.startswith("add_"):
        parts = data.split("_")
        category = parts[1]
        product_index = int(parts[2])
        await add_to_cart(query, user_id, category, product_index)
        # after adding, show the same product list again so user can add more
        await show_products_in_category(query, category)

    elif data == "clear_cart":
        user_carts[user_id] = []
        await query.edit_message_text("🗑️ Cart cleared successfully!")
    
    elif data == "checkout":
        await checkout(query, user_id)

# Message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, "main_menu")

    if "Browse Products" in text:
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
    elif user_state == "awaiting_order_details":
        await process_order(update, context, user_id, text)
    else:
        await update.message.reply_text(
            "🤔 I didn't understand that. Please use the menu buttons below or type /start to see all options."
        )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(help_text, parse_mode='Markdown')

def run_telegram_bot():
    """Run the Telegram bot"""
    try:
        print("🤖 Starting Telegram bot...")
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        print("✅ Telegram bot handlers registered")
        print("🚀 Bot is now polling...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error starting Telegram bot: {e}")

def run_flask():
    """Run Flask web server"""
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Starting Flask server on port {port}...")
    # Use a production-ready WSGI server like Gunicorn or Waitress instead of flask_app.run() in production
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=port)

if __name__ == '__main__':
    print("🔐 Bot token loaded successfully!")
    print("🚀 Starting Trusty Lads Bot services...")
    
    bot_thread = Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    run_flask()
