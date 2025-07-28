from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from dotenv import load_dotenv
import os
import json
import datetime
import traceback

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
    return """
    <html>
        <head><title>Trusty Lads Bot</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h1>🤖 Trusty Lads Bot is Online!</h1>
            <p>✅ Bot Status: <strong style="color: green;">Running</strong></p>
            <p>🕐 Last Check: <span id="time"></span></p>
            <p>📱 Start chatting with the bot on Telegram!</p>
            <script>
                document.getElementById('time').innerHTML = new Date().toLocaleString();
            </script>
        </body>
    </html>
    """

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

user_carts = {}
user_states = {}

os.makedirs("orders", exist_ok=True)

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🛍️ Browse Products", "🛒 View Cart"],
            ["📦 My Orders", "ℹ️ About Us"],
            ["📞 Contact Support", "💰 Special Offers"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"
    welcome_text = """
🌟 *Welcome to Trusty Lads!* 🌟

Your one-stop shop for:
✨ Premium Hair Care Products
🧔 Professional Beard Care
📱 Latest Electronics

Use the buttons below to navigate our store!
    """
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for category in PRODUCTS.keys():
        keyboard.append([InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")])
    await update.message.reply_text(
        "🛍️ *Browse Our Categories:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_products_in_category(query, category):
    keyboard = []
    text = f"📂 *{category} Products:*\n\n"
    for i, product in enumerate(PRODUCTS[category]):
        text += f"{i+1}. {product['name']} - ₹{product['price']}\n   _{product['description']}_\n\n"
        keyboard.append([InlineKeyboardButton(f"➕ Add {product['name']}", callback_data=f"add_{category}_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_categories")])
    keyboard.append([InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")])
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def view_cart(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(update_or_query, 'message') and update_or_query.message:
        user_id = update_or_query.effective_user.id
    else:
        user_id = update_or_query.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        if hasattr(update_or_query, 'message') and update_or_query.message:
            await update_or_query.message.reply_text(
                "🛒 Your cart is empty! Browse products to add items.",
                reply_markup=get_main_menu_keyboard())
        else:
            await update_or_query.edit_message_text(
                "🛒 Your cart is empty! Browse products to add items.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ Browse Products", callback_data="back_categories")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                ])
            )
        return
    text = "🛒 *Your Shopping Cart:*\n\n"
    total = 0
    for i, item in enumerate(cart):
        text += f"{i+1}. {item['name']} - ₹{item['price']} × {item['quantity']}\n"
        total += item['price'] * item['quantity']
    text += f"\n💰 *Total: ₹{total}*"
    keyboard = [
        [InlineKeyboardButton("➖ Remove Item", callback_data="remove_item"),
         InlineKeyboardButton("➕ Add More", callback_data="add_more")],
        [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart"),
         InlineKeyboardButton("💳 Checkout", callback_data="checkout")],
        [InlineKeyboardButton("🔙 Continue Shopping", callback_data="back_categories")]
    ]
    if hasattr(update_or_query, 'message') and update_or_query.message:
        await update_or_query.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))

async def show_offers(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    offers_text = """
🎉 *Current Special Offers!* 🎉

💸 *FLAT20* - 20% off on orders above ₹500
🎁 *NEWUSER* - 15% off for first-time buyers  
🛍️ *COMBO50* - Buy 2 get 1 free on hair care
⚡ *FLASH10* - Extra 10% off on electronics

Use these codes at checkout!
    """
    keyboard = [
        [InlineKeyboardButton("🛍️ Browse Products", callback_data="back_categories")],
        [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
    ]
    if hasattr(update_or_query, 'message') and update_or_query.message:
        await update_or_query.message.reply_text(
            offers_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text(
            offers_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))

async def about_us(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
ℹ️ *About Trusty Lads*

🏢 Premium lifestyle brand offering:
• Quality grooming products
• Latest electronics
• Affordable pricing

📍 *Address:* 123 Fashion Street, Style City
📞 *Phone:* +91-9876543210
📧 *Email:* support@trustylads.com

⭐ *Why Choose Us?*
✅ Genuine Products
✅ Fast Delivery 
✅ 24/7 Support
✅ Easy Returns
    """
    keyboard = [
        [InlineKeyboardButton("🛍️ Start Shopping", callback_data="back_categories")],
        [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
    ]
    if hasattr(update_or_query, 'message') and update_or_query.message:
        await update_or_query.message.reply_text(
            about_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text(
            about_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))

async def contact_support(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    contact_text = """
📞 *Contact Our Support Team*

🕒 *Hours:* Mon-Sat: 9AM-8PM | Sun: 10AM-6PM

📲 *Phone:* +91-9876543210
📧 *Email:* support@trustylads.com
💬 *WhatsApp:* +91-9876543210

📍 *Address:* 
123 Fashion Street, Style City
    """
    keyboard = [
        [InlineKeyboardButton("🛍️ Browse Products", callback_data="back_categories")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
    ]
    if hasattr(update_or_query, 'message') and update_or_query.message:
        await update_or_query.message.reply_text(
            contact_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text(
            contact_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))

async def show_my_orders(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(update_or_query, 'message') and update_or_query.message:
        user_id = update_or_query.effective_user.id
    else:
        user_id = update_or_query.from_user.id
    orders_file = f"orders/user_{user_id}_orders.json"
    if not os.path.exists(orders_file):
        if hasattr(update_or_query, 'message') and update_or_query.message:
            await update_or_query.message.reply_text(
                "📦 You haven't placed any orders yet!",
                reply_markup=get_main_menu_keyboard())
        else:
            await update_or_query.edit_message_text(
                "📦 You haven't placed any orders yet!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ Shop Again", callback_data="back_categories")],
                    [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                ])
            )
        return
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
        if not orders:
            if hasattr(update_or_query, 'message') and update_or_query.message:
                await update_or_query.message.reply_text(
                    "📦 You haven't placed any orders yet!",
                    reply_markup=get_main_menu_keyboard())
            else:
                await update_or_query.edit_message_text(
                    "📦 You haven't placed any orders yet!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛍️ Shop Again", callback_data="back_categories")],
                        [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
                        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                    ])
                )
            return
        text = "📦 *Your Recent Orders:*\n\n"
        for order in orders[-3:]:
            text += f"🆔 *Order ID:* {order['order_id']}\n"
            text += f"📅 *Date:* {order['date']}\n"
            text += f"💰 *Total:* ₹{order['total']}\n"
            text += f"📋 *Status:* {order['status']}\n\n"
        keyboard = [
            [InlineKeyboardButton("🛍️ Shop Again", callback_data="back_categories")],
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
        ]
        if hasattr(update_or_query, 'message') and update_or_query.message:
            await update_or_query.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update_or_query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        if hasattr(update_or_query, 'message') and update_or_query.message:
            await update_or_query.message.reply_text(
                "❌ Error loading orders. Please contact support.",
                reply_markup=get_main_menu_keyboard())
        else:
            await update_or_query.edit_message_text(
                "❌ Error loading orders. Please contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                ])
            )

async def checkout(query, user_id):
    cart = user_carts.get(user_id, [])
    if not cart:
        await query.edit_message_text(
            "🛒 Your cart is empty!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Browse Products", callback_data="back_categories")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
            ])
        )
        return
    user_states[user_id] = "awaiting_order_details"
    text = "💳 *Checkout Process*\n\n"
    text += "Please send your details in this format:\n\n"
    text += "Name: Your Full Name\n"
    text += "Phone: Your Phone Number\n" 
    text += "Address: Your Complete Address\n"
    text += "Payment: COD/Online\n\n"
    text += "*Example:*\n"
    text += "Name: John Doe\n"
    text += "Phone: 9876543210\n"
    text += "Address: 123 Main St, City, PIN\n"
    text += "Payment: COD"
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Cart", callback_data="view_cart")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]
    ]
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard))

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, order_details):
    cart = user_carts.get(user_id, [])
    if not cart:
        await update.message.reply_text(
            "🛒 Your cart is empty!",
            reply_markup=get_main_menu_keyboard())
        return
    total = sum(item['price'] * item['quantity'] for item in cart)
    order_id = f"TL{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    user_name = update.effective_user.first_name or "Customer"
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
    orders_file = f"orders/user_{user_id}_orders.json"
    orders = []
    if os.path.exists(orders_file):
        with open(orders_file, 'r') as f:
            orders = json.load(f)
    orders.append(order_data)
    with open(orders_file, 'w') as f:
        json.dump(orders, f, indent=2)
    with open("orders/all_orders.txt", "a", encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"ORDER ID: {order_id}\n")
        f.write(f"DATE: {order_data['date']}\n")
        f.write(f"CUSTOMER: {user_name}\n")
        f.write(f"USER ID: {user_id}\n")
        f.write(f"DETAILS:\n{order_details}\n")
        f.write(f"ITEMS:\n")
        for item in cart:
            f.write(f"- {item['name']} ×{item['quantity']} = ₹{item['price'] * item['quantity']}\n")
        f.write(f"TOTAL: ₹{total}\n")
        f.write(f"{'='*50}\n")
    user_carts[user_id] = []
    user_states[user_id] = "main_menu"
    confirmation_text = f"""
✅ *Order Confirmed!* ✅

🆔 *Order ID:* {order_id}
💰 *Total:* ₹{total}
📅 *Date:* {order_data['date']}

📦 Your order will be processed within 24 hours.
📞 We'll contact you for confirmation.

*Thank you for shopping with Trusty Lads!* 🙏
    """
    keyboard = [
        [InlineKeyboardButton("🛍️ Shop More", callback_data="back_categories")],
        [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]
    ]
    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard))

async def add_to_cart(query, user_id, category, product_index):
    if user_id not in user_carts:
        user_carts[user_id] = []
    product = PRODUCTS[category][product_index]
    for item in user_carts[user_id]:
        if item['name'] == product['name']:
            item['quantity'] += 1
            await query.edit_message_text(
                f"✅ Added another {product['name']} to your cart!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
                    [InlineKeyboardButton("🛍️ Continue Shopping", callback_data=f"cat_{category}")]
                ])
            )
            return
    user_carts[user_id].append({
        'name': product['name'],
        'price': product['price'],
        'quantity': 1,
        'category': category
    })
    await query.edit_message_text(
        f"✅ {product['name']} added to your cart!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
            [InlineKeyboardButton("🛍️ Continue Shopping", callback_data=f"cat_{category}")]
        ])
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    await query.answer()
    
    try:
        if data == "back_main":
            await query.edit_message_text(
                "🏠 *Main Menu* - What would you like to do?\n\nPlease use the buttons below to navigate:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ Browse Products", callback_data="back_categories")],
                    [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
                    [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
                    [InlineKeyboardButton("ℹ️ About Us", callback_data="about_us")],
                    [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
                    [InlineKeyboardButton("💰 Special Offers", callback_data="special_offers")]
                ])
            )
        elif data == "back_categories":
            keyboard = []
            for category in PRODUCTS.keys():
                keyboard.append([InlineKeyboardButton(f"📂 {category}", callback_data=f"cat_{category}")])
            keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")])
            await query.edit_message_text(
                "🛍️ *Browse Our Categories:*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
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
                    await query.edit_message_text("❌ Invalid product selection!")
        elif data == "view_cart":
            await view_cart(query, context)
        elif data == "clear_cart":
            user_carts[user_id] = []
            await query.edit_message_text(
                "🗑️ Your cart has been cleared.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ Browse Products", callback_data="back_categories")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                ])
            )
        elif data == "checkout":
            await checkout(query, user_id)
        elif data == "contact_support":
            await contact_support(query, context)
        elif data == "my_orders":
            await show_my_orders(query, context)
        elif data == "special_offers":
            await show_offers(query, context)
        elif data == "about_us":
            await about_us(query, context)
        else:
            await query.edit_message_text(
                "❌ Unknown command. Please use the menu buttons.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                ])
            )
    except Exception as e:
        print(f"Error in button_callback: {e}")
        traceback.print_exc()
        try:
            await query.edit_message_text(
                "❌ Something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
                ])
            )
        except:
            pass

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        user_id = update.effective_user.id
        user_state = user_states.get(user_id, "main_menu")

        if "🛍️ Browse Products" in text:
            await show_categories(update, context)
        elif "🛒 View Cart" in text:
            await view_cart(update, context)
        elif "📦 My Orders" in text:
            await show_my_orders(update, context)
        elif "ℹ️ About Us" in text:
            await about_us(update, context)
        elif "📞 Contact Support" in text:
            await contact_support(update, context)
        elif "💰 Special Offers" in text:
            await show_offers(update, context)
        elif user_state == "awaiting_order_details":
            await process_order(update, context, user_id, text)
        else:
            await update.message.reply_text(
                "🤔 I didn't understand that. Please use the menu buttons below:",
                reply_markup=get_main_menu_keyboard())
    except Exception as e:
        print(f"Error in message_handler: {e}")
        traceback.print_exc()
        try:
            await update.message.reply_text(
                "❌ Something went wrong. Please try again or use /start to restart.",
                reply_markup=get_main_menu_keyboard())
        except:
            pass

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a telegram message to notify the developer."""
    print(f"Exception while handling an update: {context.error}")
    traceback.print_exc()

# Telegram bot function
def run_telegram_bot():
    """Run the Telegram bot"""
    try:
        print("🤖 Starting Telegram bot...")
        
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        print("✅ Telegram bot handlers registered")
        print("🚀 Bot is now running...")
        
        # Start polling
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error starting Telegram bot: {e}")
        traceback.print_exc()

# Flask function
def run_flask():
    """Run Flask web server"""
    try:
        port = int(os.environ.get('PORT', 10000))
        print(f"🌐 Starting Flask server on port {port}...")
        flask_app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        traceback.print_exc()

# Main execution
if __name__ == '__main__':
    print("🔐 Bot token loaded successfully!")
    print("🚀 Starting Trusty Lads Bot services...")
    
    try:
        # Start Telegram bot in a separate thread
        bot_thread = Thread(target=run_telegram_bot, daemon=True)
        bot_thread.start()
        print("✅ Telegram bot thread started")
        
        # Start Flask server (this will block and keep the app alive)
        run_flask()
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        traceback.print_exc()