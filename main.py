# main.py
# --- IMPORTS ---
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from dotenv import load_dotenv
import os
import json
import datetime

# --- INITIAL SETUP ---
# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in environment variables!")
    exit(1)

# --- FLASK APP (for Render Health Checks) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    # A simple page to show the bot is online
    return """
    <html>
        <head><title>Trusty Lads Bot</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Trusty Lads Bot is Online!</h1>
            <p>✅ Status: <strong style="color: green;">Running</strong></p>
            <p>Your bot is active and listening for messages on Telegram.</p>
        </body>
    </html>
    """

@flask_app.route('/health')
def health_check():
    # Health check endpoint for Render
    return {"status": "healthy", "service": "trusty-lads-bot"}

# --- BOT DATA AND CONFIGURATION ---
# Product Catalog
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

# In-memory storage for user carts and states (will reset on deploy)
user_carts = {}
user_states = {}

# Create 'orders' directory if it doesn't exist
os.makedirs("orders", exist_ok=True)

# --- BOT HANDLER FUNCTIONS ---

# Command: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_carts[user_id] = []  # Clear cart on start
    user_states[user_id] = "main_menu"
    
    buttons = [
        ["🛒 Browse Products", "🛍️ View Cart"],
        ["📦 My Orders", "ℹ️ About Us"],
        ["📞 Contact Support", "💰 Offers"]
    ]
    
    welcome_text = f"""
🌟 *Welcome to Trusty Lads, {user_name}!* 🌟

Your one-stop shop for premium products.
Choose an option below to get started! 👇
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Help & Commands*
/start - Start the bot & see the main menu
/help - Show this help message

*How to Shop:*
1️⃣ Tap *"Browse Products"* to see categories.
2️⃣ Select a category to see items.
3️⃣ Tap *"Add [Item]"* to add to your cart.
4️⃣ Tap *"View Cart"* to review and checkout.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Displays product categories
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")] for category in PRODUCTS.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛒 *Please choose a category:*", parse_mode='Markdown', reply_markup=reply_markup)

# Displays products within a category
async def show_products_in_category(query, category):
    keyboard = []
    text = f"📂 *Products in {category}:*\n\n"
    
    for i, product in enumerate(PRODUCTS[category]):
        text += f"*{product['name']}* - ₹{product['price']}\n_{product['description']}_\n\n"
        keyboard.append([InlineKeyboardButton(f"➕ Add {product['name']}", callback_data=f"add_{category}_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Displays the user's cart
async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await update.message.reply_text("🛍️ Your cart is empty. Use 'Browse Products' to add items.")
        return
    
    text = "🛍️ *Your Shopping Cart:*\n\n"
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    for i, item in enumerate(cart):
        text += f"{i+1}. {item['name']} (x{item['quantity']}) - ₹{item['price'] * item['quantity']}\n"
    
    text += f"\n💰 *Total: ₹{total}*"
    
    keyboard = [
        [InlineKeyboardButton("📦 Proceed to Checkout", callback_data="checkout")],
        [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")]
    ]
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Handles adding items to the cart
def add_to_cart(user_id, category, product_index):
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    product_to_add = PRODUCTS[category][product_index]
    
    # Check if product is already in the cart
    for item in user_carts[user_id]:
        if item['name'] == product_to_add['name']:
            item['quantity'] += 1
            return f"Another {product_to_add['name']} added."

    # Otherwise, add it as a new item
    user_carts[user_id].append({
        'name': product_to_add['name'],
        'price': product_to_add['price'],
        'quantity': 1
    })
    return f"{product_to_add['name']} added to cart."

# Asks for user details for checkout
async def checkout(query):
    user_id = query.from_user.id
    if not user_carts.get(user_id):
        await query.edit_message_text("Your cart is empty. Cannot checkout.")
        return

    user_states[user_id] = "awaiting_order_details"
    text = """
📦 *Checkout*
Please provide your delivery details in a single message:

*Name:*
*Phone Number:*
*Full Address (with Pincode):*
*Payment Method:* (e.g., COD, UPI)
    """
    await query.edit_message_text(text, parse_mode='Markdown')

# Processes the final order
async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cart = user_carts.get(user_id, [])
    order_details_text = update.message.text
    
    total = sum(item['price'] * item['quantity'] for item in cart)
    order_id = f"TL-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
    
    order_data = {
        'order_id': order_id,
        'user_id': user_id,
        'user_name': update.effective_user.first_name,
        'date': datetime.datetime.now().isoformat(),
        'items': cart,
        'total': total,
        'customer_details': order_details_text,
        'status': 'Confirmed'
    }
    
    # Save order to a user-specific file
    orders_file = f"orders/user_{user_id}_orders.json"
    all_orders = []
    if os.path.exists(orders_file):
        with open(orders_file, 'r') as f:
            try:
                all_orders = json.load(f)
            except json.JSONDecodeError:
                pass # File is empty or corrupt, start fresh
    all_orders.append(order_data)
    with open(orders_file, 'w') as f:
        json.dump(all_orders, f, indent=4)
        
    # Send confirmation to user
    confirmation_text = f"""
✅ *Order Confirmed!*

Thank you for your purchase!
*Order ID:* `{order_id}`
*Total Amount:* ₹{total}

We will contact you shortly to confirm the delivery.
    """
    await update.message.reply_text(confirmation_text, parse_mode='Markdown')
    
    # Reset cart and state
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"

# General message handler for main menu buttons
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Check if we are awaiting order details
    if user_states.get(user_id) == "awaiting_order_details":
        await process_order(update, context)
        return

    # Handle main menu buttons
    if "Browse Products" in text:
        await show_categories(update, context)
    elif "View Cart" in text:
        await view_cart(update, context)
    elif "My Orders" in text:
        await update.message.reply_text("Feature coming soon!")
    elif "About Us" in text:
        await update.message.reply_text("Trusty Lads is your #1 source for premium lifestyle products.")
    elif "Contact Support" in text:
        await update.message.reply_text("You can reach us at support@trustylads.com.")
    elif "Offers" in text:
        await update.message.reply_text("No special offers right now, but check back soon!")
    else:
        await update.message.reply_text("Sorry, I didn't understand that. Please use the menu buttons or type /start.")

# Handler for inline button callbacks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Always answer the callback
    
    user_id = query.from_user.id
    data = query.data

    if data.startswith("cat_"):
        category = data.split("_", 1)[1]
        await show_products_in_category(query, category)
        
    elif data.startswith("add_"):
        _, category, product_index_str = data.split("_")
        message = add_to_cart(user_id, category, int(product_index_str))
        await query.answer(text=message, show_alert=False) # Show small notification
        
    elif data == "back_to_categories":
        # Re-create the category view by simulating a message
        # A bit of a workaround, but effective for inline keyboards
        keyboard = [[InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")] for category in PRODUCTS.keys()]
        await query.edit_message_text("🛒 *Please choose a category:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "clear_cart":
        user_carts[user_id] = []
        await query.edit_message_text("🗑️ Your cart has been cleared.")
        
    elif data == "checkout":
        await checkout(query)

# --- BOT AND SERVER EXECUTION ---

def run_telegram_bot():
    """Initializes and runs the Telegram bot."""
    print("🤖 Starting Telegram bot polling...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Start the bot
    application.run_polling(drop_pending_updates=True)

def run_flask_app():
    """Runs the Flask app using a production-ready server."""
    port = int(os.environ.get('PORT', 10000))
    from waitress import serve
    print(f"🌐 Starting Flask server on http://0.0.0.0:{port}")
    serve(flask_app, host="0.0.0.0", port=port)

if __name__ == '__main__':
    print("🚀 Starting Trusty Lads Bot services...")
    
    # Start the Telegram bot in a background thread
    bot_thread = Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Run the Flask app in the main thread (this will block and keep the container alive)
    run_flask_app()
