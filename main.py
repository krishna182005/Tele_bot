# main.py - Complete Working Version for Render (Flask + Telegram Bot)
import asyncio
import os
import json
import datetime
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

# --- FLASK APP ---
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head><title>Trusty Lads Bot</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Trusty Lads Bot is Online!</h1>
            <p>✅ Status: <strong style="color: green;">Running on Render</strong></p>
            <p>Your Telegram bot is active and listening for messages.</p>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "trusty-lads-bot", "platform": "render"}

# --- BOT DATA ---
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

# Global state storage
user_carts = {}
user_states = {}
os.makedirs("orders", exist_ok=True)

# --- TELEGRAM BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"
    
    buttons = [
        ["🛒 Browse Products", "🛍️ View Cart"],
        ["📦 My Orders", "ℹ️ About Us"],
        ["📞 Contact Support", "💰 Offers"]
    ]
    
    welcome_text = f"🌟 *Welcome to Trusty Lads, {user_name}!* 🌟\n\nChoose an option below to get started! 👇"
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
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

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product categories"""
    keyboard = [[InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")] for category in PRODUCTS.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛒 *Please choose a category:*", parse_mode='Markdown', reply_markup=reply_markup)

async def show_products_in_category(query, category):
    """Show products in selected category"""
    keyboard = []
    text = f"📂 *Products in {category}:*\n\n"
    
    for i, product in enumerate(PRODUCTS[category]):
        text += f"*{product['name']}* - ₹{product['price']}\n_{product['description']}_\n\n"
        keyboard.append([InlineKeyboardButton(f"➕ Add {product['name']}", callback_data=f"add_{category}_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View shopping cart"""
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

def add_to_cart(user_id, category, product_index):
    """Add item to cart (helper function)"""
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    product_to_add = PRODUCTS[category][product_index]
    
    for item in user_carts[user_id]:
        if item['name'] == product_to_add['name']:
            item['quantity'] += 1
            return f"Another {product_to_add['name']} added."

    user_carts[user_id].append({
        'name': product_to_add['name'],
        'price': product_to_add['price'],
        'quantity': 1
    })
    return f"{product_to_add['name']} added to cart."

async def checkout(query):
    """Start checkout process"""
    user_id = query.from_user.id
    if not user_carts.get(user_id):
        await query.answer("Your cart is empty!", show_alert=True)
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

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process order after checkout"""
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
    
    # Save order to file
    orders_file = f"orders/user_{user_id}_orders.json"
    all_orders = []
    if os.path.exists(orders_file):
        with open(orders_file, 'r') as f:
            try:
                all_orders = json.load(f)
            except json.JSONDecodeError:
                pass
    all_orders.append(order_data)
    with open(orders_file, 'w') as f:
        json.dump(all_orders, f, indent=4)
        
    confirmation_text = f"""
✅ *Order Confirmed!*

Thank you for your purchase!
*Order ID:* `{order_id}`
*Total Amount:* ₹{total}

We will contact you shortly to confirm the delivery.
    """
    await update.message.reply_text(confirmation_text, parse_mode='Markdown')
    
    # Clear cart and reset state
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text

    if user_states.get(user_id) == "awaiting_order_details":
        await process_order(update, context)
        return

    if "Browse Products" in text:
        await show_categories(update, context)
    elif "View Cart" in text:
        await view_cart(update, context)
    elif "My Orders" in text:
        await update.message.reply_text("📦 Feature coming soon! You'll be able to track all your orders here.")
    elif "About Us" in text:
        await update.message.reply_text("ℹ️ Trusty Lads is your #1 source for premium lifestyle products. Quality guaranteed!")
    elif "Contact Support" in text:
        await update.message.reply_text("📞 You can reach us at support@trustylads.com or call +91-XXXXXXXXXX")
    elif "Offers" in text:
        await update.message.reply_text("💰 No special offers right now, but check back soon for amazing deals!")
    else:
        await update.message.reply_text("❓ Sorry, I didn't understand that. Please use the menu buttons or type /start.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data

    if data.startswith("cat_"):
        category = data.split("_", 1)[1]
        await show_products_in_category(query, category)
        
    elif data.startswith("add_"):
        _, category, product_index_str = data.split("_")
        message = add_to_cart(user_id, category, int(product_index_str))
        await query.answer(text=message, show_alert=False)
        
    elif data == "back_to_categories":
        keyboard = [[InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")] for category in PRODUCTS.keys()]
        await query.edit_message_text("🛒 *Please choose a category:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "clear_cart":
        if user_id in user_carts:
            user_carts[user_id] = []
        await query.edit_message_text("🗑️ Your cart has been cleared.")
        
    elif data == "checkout":
        await checkout(query)

# --- TELEGRAM BOT SETUP ---
async def run_bot():
    """Setup and run the Telegram bot"""
    print("🤖 Starting Telegram Bot...")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ Bot handlers registered")
    
    # Initialize and start the bot
    await application.initialize()
    await application.start()
    
    # Start polling for updates
    await application.updater.start_polling(drop_pending_updates=True)
    
    print("🚀 Bot is now running and polling for messages!")
    
    # Keep the bot running
    try:
        await application.updater.idle()
    except KeyboardInterrupt:
        print("⏹️ Bot stopped by user")
    finally:
        await application.stop()

# --- FLASK + BOT RUNNER ---
def run_flask():
    """Run Flask server"""
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask server on port {port}")
    
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        print("⚠️ Waitress not found, using Flask dev server")
        app.run(host='0.0.0.0', port=port)

def run_bot_in_thread():
    """Run bot in new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f"❌ Bot error: {e}")
    finally:
        loop.close()

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    print("🚀 Starting Trusty Lads Bot + Flask Server...")
    
    # Start bot in background thread
    bot_thread = Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    print("✅ Bot started in background thread")
    
    # Start Flask server (main thread)
    run_flask()