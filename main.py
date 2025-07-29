import asyncio
import os
import logging
import json
import re
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, jsonify, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Conflict, TimedOut, NetworkError
from dotenv import load_dotenv

# --- LOGGING ---
# Basic configuration for logging to monitor bot activity and errors.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ENVIRONMENT SETUP ---
# Loads environment variables from a .env file for secure key management.
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

print(f"🔍 BOT_TOKEN found: {'Yes' if BOT_TOKEN else 'No'}")

# Global flag for clean shutdown and bot status.
bot_running = False

# In-memory storage for user sessions, carts, and orders.
# In a production environment, this would be replaced by a database (e.g., Redis, PostgreSQL).
user_sessions = {}
user_carts = {}
user_orders = {}
order_counter = 1000

# E-COMMERCE PRODUCT CATALOG (Prices in INR)
PRODUCT_CATALOG = {
    "hair_care": {
        "name": "🧴 Hair Care",
        "products": {
            "hair_shampoo": {"name": "Premium Hair Shampoo", "price": 199.00, "description": "Nourishing shampoo for all hair types with natural ingredients"},
            "hair_conditioner": {"name": "Deep Moisturizing Conditioner", "price": 179.00, "description": "Intensive conditioning treatment for smooth, silky hair"},
            "hair_oil": {"name": "Argan Hair Oil", "price": 149.00, "description": "100% pure argan oil for hair strengthening and shine"},
            "hair_mask": {"name": "Protein Hair Mask", "price": 249.00, "description": "Weekly treatment mask for damaged and brittle hair"},
        }
    },
    "beard_care": {
        "name": "🧔 Beard Care",
        "products": {
            "beard_oil": {"name": "Gentleman's Beard Oil", "price": 159.00, "description": "Premium blend of oils for beard conditioning and growth"},
            "beard_balm": {"name": "Styling Beard Balm", "price": 139.00, "description": "Natural balm for beard shaping and moisture"},
            "beard_wash": {"name": "Beard Cleanser", "price": 129.00, "description": "Gentle cleanser specifically formulated for facial hair"},
            "beard_comb": {"name": "Wooden Beard Comb", "price": 99.00, "description": "Handcrafted wooden comb for beard grooming"},
        }
    },
    "electronics": {
        "name": "📱 Electronics",
        "products": {
            "wireless_charger": {"name": "Fast Wireless Charger", "price": 799.00, "description": "15W fast charging pad compatible with all devices"},
            "bluetooth_speaker": {"name": "Portable Bluetooth Speaker", "price": 1499.00, "description": "High-quality sound with 12-hour battery life"},
            "phone_case": {"name": "Premium Phone Case", "price": 349.00, "description": "Drop-proof case with wireless charging support"},
            "power_bank": {"name": "20000mAh Power Bank", "price": 999.00, "description": "High-capacity portable charger with fast charging"},
        }
    },
    "accessories": {
        "name": "👜 Accessories",
        "products": {
            "leather_wallet": {"name": "Genuine Leather Wallet", "price": 899.00, "description": "Handcrafted leather wallet with RFID protection"},
            "sunglasses": {"name": "UV Protection Sunglasses", "price": 1299.00, "description": "Stylish sunglasses with 100% UV protection"},
            "watch": {"name": "Classic Analog Watch", "price": 2499.00, "description": "Elegant timepiece with leather strap"},
            "backpack": {"name": "Travel Backpack", "price": 1799.00, "description": "Durable backpack with laptop compartment"},
        }
    }
}

# OFFERS AND PROMO CODES (Values in INR)
ACTIVE_OFFERS = {
    "WELCOME20": {"discount": 20, "description": "20% off for new customers", "min_order": 0},
    "DIWALI150": {"discount_amount": 150, "description": "₹150 off on orders above ₹1500", "min_order": 1500},
    "BULK1000": {"discount": 15, "description": "15% off on orders above ₹1000", "min_order": 1000},
    "PREMIUM2000": {"discount": 20, "description": "20% off on orders above ₹2000", "min_order": 2000},
    "STUDENT30": {"discount": 30, "description": "30% student discount", "min_order": 0},
}

# COMPANY INFORMATION (CHENNAI, INDIA)
COMPANY_INFO = {
    "name": "TrustyLads®",
    "mission": "Providing premium quality products for the modern gentleman with uncompromising standards, delivered across India.",
    "address": "123 Anna Salai, T. Nagar, Chennai, Tamil Nadu, 600017",
    "phone": "+91 6369360123",
    "email": "support.in@trustylads.com",
    "whatsapp": "+91 6369360123",
    "hours": "Monday - Sunday: 8:00 AM - 11:00 PM IST",
    "why_choose": "✅ Premium Quality Products\n✅ Fast & Reliable Shipping Across India\n✅ Cash on Delivery (COD) Available\n✅ 30-Day Money Back Guarantee\n✅ 24/7 Customer Support\n✅ Secure Payment Processing"
}


# --- FLASK APP for Health Checks & Dashboard ---
app = Flask(__name__)

@app.route('/')
def home():
    """Provides a simple HTML dashboard with bot statistics."""
    stats = {
        "active_users": len(user_sessions),
        "total_orders": sum(len(orders) for orders in user_orders.values()),
        "total_products": sum(len(cat["products"]) for cat in PRODUCT_CATALOG.values()),
        "active_carts": len([cart for cart in user_carts.values() if cart]),
        "bot_uptime": "Online" if bot_running else "Starting..."
    }
    
    # Simple HTML/CSS for the dashboard page.
    return f"""
    <html>
        <head>
            <title>TrustyLads® India E-commerce Bot Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; 
                       background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%); 
                       color: #333; min-height: 100vh; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .card {{ background: rgba(255,255,255,0.8); padding: 20px; margin: 20px 0; 
                        border-radius: 15px; backdrop-filter: blur(10px); border: 1px solid #ddd;}}
                h1, h2 {{ color: #003366; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>🛒 TrustyLads® India E-commerce Bot</h1>
                    <p><strong>Bot Status:</strong> {'✅ Online' if bot_running else '⏳ Starting...'}</p>
                    <p>
                       <a href="/health" style="color: #138808;">Health Check</a> | 
                       <a href="/orders" style="color: #138808;">Order Management</a>
                    </p>
                </div>
                <div class="card">
                    <h2>📊 Live Statistics</h2>
                    <p><strong>Active Users:</strong> {stats['active_users']}</p>
                    <p><strong>Total Orders:</strong> {stats['total_orders']}</p>
                    <p><strong>Products Available:</strong> {stats['total_products']}</p>
                    <p><strong>Active Carts:</strong> {stats['active_carts']}</p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring services."""
    return jsonify({
        "status": "healthy" if bot_running else "starting",
        "service": "trusty-lads-ecommerce-bot-india",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/orders')
def orders_dashboard():
    """Endpoint to view all current orders and active carts in JSON format."""
    return jsonify({
        "total_orders": sum(len(orders) for orders in user_orders.values()),
        "orders": user_orders,
        "active_carts": {str(k): v for k, v in user_carts.items() if v}
    })

# --- USER SESSION & CART MANAGEMENT ---
def get_user_session(user_id: int):
    """Retrieves or creates a session for a user."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_context": None,
            "checkout_data": {}
        }
    return user_sessions[user_id]

def get_user_cart(user_id: int):
    """Retrieves or creates a shopping cart for a user."""
    if user_id not in user_carts:
        user_carts[user_id] = {}
    return user_carts[user_id]

def add_to_cart(user_id: int, category: str, product_id: str):
    """Adds a product to the user's cart or increments its quantity."""
    cart = get_user_cart(user_id)
    item_key = f"{category}_{product_id}"
    
    if item_key in cart:
        cart[item_key]["quantity"] += 1
    else:
        product = PRODUCT_CATALOG[category]["products"][product_id]
        cart[item_key] = {
            "name": product["name"], "price": product["price"], "quantity": 1,
            "category": category, "product_id": product_id
        }
    return cart[item_key]

def calculate_cart_total(user_id: int) -> float:
    """Calculates the total price of items in a user's cart."""
    cart = get_user_cart(user_id)
    return round(sum(item["price"] * item["quantity"] for item in cart.values()), 2)

def clear_user_cart(user_id: int):
    """Empties a user's shopping cart."""
    if user_id in user_carts:
        user_carts[user_id] = {}

def save_order(user_id: int, order_data: dict) -> str:
    """Saves a completed order to memory and local files."""
    global order_counter
    order_id = f"TL-IN-{order_counter}"
    order_counter += 1
    
    order = {
        "order_id": order_id, "user_id": user_id,
        "date": datetime.now().isoformat(), "status": "Confirmed", **order_data
    }
    
    if user_id not in user_orders:
        user_orders[user_id] = []
    user_orders[user_id].append(order)
    
    try:
        os.makedirs("orders", exist_ok=True)
        with open(f"orders/order_{order_id}.json", "w") as f:
            json.dump(order, f, indent=4)
        logger.info(f"Saved order {order_id} to file.")
    except Exception as e:
        logger.error(f"Error saving order file for {order_id}: {e}")
        
    return order_id

# --- MAIN MENU KEYBOARD ---
def get_main_menu_keyboard():
    """Returns the main ReplyKeyboardMarkup for navigation."""
    keyboard = [
        [KeyboardButton("🛒 Browse Products"), KeyboardButton("🛍️ View Cart")],
        [KeyboardButton("📦 My Orders"), KeyboardButton("ℹ️ About Us")],
        [KeyboardButton("📞 Contact Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- BOT COMMAND HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command. Welcomes the user and shows the main menu."""
    user = update.effective_user
    session = get_user_session(user.id)
    session['current_context'] = "main_menu"
    logger.info(f"👋 User started bot: {user.first_name} (ID: {user.id})")
    
    welcome_message = f"""
🎉 **Welcome to TrustyLads®, {user.first_name}!**

Your premium destination for quality products, now in India! 🛍️

*Use the menu buttons below to start shopping or type /help for assistance.*
    """
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown', 
        reply_markup=get_main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command. Provides user guidance."""
    help_text = """
🆘 **TrustyLads® Bot Help**

**Main Menu Buttons:**
• `🛒 Browse Products`: View our product categories.
• `🛍️ View Cart`: See items in your shopping cart and checkout.
• `📦 My Orders`: Check your past order history.
• `ℹ️ About Us`: Learn about our company.
• `📞 Contact Support`: Get help from our team.

**How to Shop:**
1.  Tap `🛒 Browse Products` to see categories.
2.  Select a category to view products.
3.  Add items to your cart.
4.  Tap `🛍️ View Cart` and proceed to checkout when ready.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# --- CORE FEATURE HANDLERS ---
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays product categories as inline buttons."""
    keyboard = [
        [InlineKeyboardButton(cat_data["name"], callback_data=f"category_{cat_id}")]
        for cat_id, cat_data in PRODUCT_CATALOG.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    catalog_text = "🛒 **Product Catalog**\n\nChoose a category to browse:"
    
    # Edit the message if it's from a callback, otherwise send a new one.
    if update.callback_query:
        await update.callback_query.edit_message_text(catalog_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(catalog_text, parse_mode='Markdown', reply_markup=reply_markup)

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's shopping cart contents and total."""
    user_id = update.effective_user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        cart_text = "🛍️ **Your Cart is Empty**"
        keyboard = [[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]
    else:
        cart_text = "🛍️ **Your Shopping Cart**\n\n"
        total = calculate_cart_total(user_id)
        for item in cart.values():
            item_total = item["price"] * item["quantity"]
            cart_text += f"• *{item['name']}*\n  `{item['quantity']} x ₹{item['price']:.2f} = ₹{item_total:.2f}`\n"
        cart_text += f"\n💰 **Total: ₹{total:.2f}**"
        
        keyboard = [
            [InlineKeyboardButton("💳 Proceed to Checkout", callback_data="start_checkout")],
            [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")],
            [InlineKeyboardButton("🛒 Continue Shopping", callback_data="browse_products")]
        ]
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's past 5 orders."""
    user_id = update.effective_user.id
    orders = user_orders.get(user_id, [])
    
    if not orders:
        orders_text = "📦 **No Orders Yet**\nYou haven't placed any orders."
        keyboard = [[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]
    else:
        orders_text = "📦 **Your Recent Orders**\n\n"
        for order in reversed(orders[-5:]): # Show latest 5
            order_date = datetime.fromisoformat(order['date']).strftime("%d %b %Y")
            orders_text += f"🔸 **Order {order['order_id']}** on {order_date}\n"
            orders_text += f"   Total: `₹{order['total']:.2f}`, Status: *{order['status']}*\n\n"
        keyboard = [[InlineKeyboardButton("🛒 Shop Again", callback_data="browse_products")]]
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays company information."""
    about_text = f"""
ℹ️ **About TrustyLads® India**

**Our Mission:**
_{COMPANY_INFO['mission']}_

📍 **Address:**
`{COMPANY_INFO['address']}`

🕒 **Hours:**
`{COMPANY_INFO['hours']}`

🌟 **Why Choose Us?**
{COMPANY_INFO['why_choose']}
    """
    keyboard = [[InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays contact information with quick action buttons."""
    support_text = f"""
📞 **Contact TrustyLads® Support**

Our team is ready to help you.

• **Phone:** `{COMPANY_INFO['phone']}`
• **Email:** `{COMPANY_INFO['email']}`
• **WhatsApp:** `{COMPANY_INFO['whatsapp']}`

🕒 **Support Hours:**
`{COMPANY_INFO['hours']}`
    """
    clean_phone = COMPANY_INFO['whatsapp'].replace(' ', '').replace('+', '')
    keyboard = [
        [InlineKeyboardButton("📞 Call Now", url=f"tel:{COMPANY_INFO['phone']}")],
        [InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{clean_phone}")],
        [InlineKeyboardButton("📧 Send Email", url=f"mailto:{COMPANY_INFO['email']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)


# --- CHECKOUT PROCESS ---
async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates the checkout process, starting with collecting the user's name."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not get_user_cart(user_id):
        await query.answer("Your cart is empty!", show_alert=True)
        return
    
    session = get_user_session(user_id)
    session['current_context'] = "checkout_name"
    session['checkout_data'] = {} # Reset checkout data
    
    await query.edit_message_text(
        "📝 **Checkout Step 1 of 3**\n\nPlease enter your **full name**:",
        parse_mode='Markdown'
    )

async def process_checkout_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user text input during the multi-step checkout."""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    message_text = update.message.text.strip()
    current_context = session.get('current_context')

    if current_context == "checkout_name":
        if len(message_text) < 3:
            await update.message.reply_text("Please enter a valid full name.")
            return
        session['checkout_data']['full_name'] = message_text
        session['current_context'] = "checkout_phone"
        await update.message.reply_text(
            f"✅ Name: {message_text}\n\n📝 **Checkout Step 2 of 3**\nPlease enter your **10-digit phone number**:",
            parse_mode='Markdown'
        )

    elif current_context == "checkout_phone":
        if not (message_text.isdigit() and len(message_text) == 10):
            await update.message.reply_text("Please enter a valid 10-digit Indian phone number.")
            return
        session['checkout_data']['phone'] = message_text
        session['current_context'] = "checkout_address"
        await update.message.reply_text(
            f"✅ Phone: {message_text}\n\n📝 **Checkout Step 3 of 3**\nPlease enter your **complete delivery address (including Pincode)**:",
            parse_mode='Markdown'
        )
        
    elif current_context == "checkout_address":
        if len(message_text) < 15:
            await update.message.reply_text("Please enter a complete and valid address.")
            return
        session['checkout_data']['address'] = message_text
        session['current_context'] = "checkout_payment"
        keyboard = [
            [InlineKeyboardButton("💰 Cash on Delivery (COD)", callback_data="payment_cod")],
            [InlineKeyboardButton("💳 Online Payment (Coming Soon)", callback_data="payment_online")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ Address: {message_text}\n\n💳 Please select your **payment method**:",
            parse_mode='Markdown', reply_markup=reply_markup
        )

async def handle_payment_selection(update: Update, payment_method: str):
    """Handles the user's payment method selection."""
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    if payment_method == "Online Payment":
        await query.answer("Online payment is not available yet. Please choose COD.", show_alert=True)
        return
        
    session['checkout_data']['payment_method'] = payment_method
    session['current_context'] = "awaiting_confirmation"
    await prompt_for_order_confirmation(update, context)


async def prompt_for_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a final summary for the user to confirm before placing the order."""
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    cart = get_user_cart(user_id)
    checkout_data = session.get('checkout_data', {})

    subtotal = calculate_cart_total(user_id)
    final_total = subtotal # Assuming no promo codes for now.
    
    summary_text = "✅ **Please Confirm Your Order**\n\n"
    summary_text += f"👤 **Name:** {checkout_data.get('full_name', 'N/A')}\n"
    summary_text += f"📞 **Phone:** {checkout_data.get('phone', 'N/A')}\n"
    summary_text += f"📍 **Address:** {checkout_data.get('address', 'N/A')}\n"
    summary_text += f"💳 **Payment:** {checkout_data.get('payment_method', 'N/A')}\n\n"
    
    summary_text += "📦 **Items in Cart:**\n"
    for item in cart.values():
        summary_text += f"• `{item['name']} x{item['quantity']}`\n"
        
    summary_text += f"\n💰 **Total Amount: ₹{final_total:.2f}**\n\n"
    
    # Per your request, add a clear instruction for corrections.
    summary_text += "*If any correction is needed, please select '✏️ Edit Details' to enter your information again.*"
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Place Order", callback_data="confirm_final_order")],
        [InlineKeyboardButton("✏️ Edit Details", callback_data="start_checkout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(summary_text, parse_mode='Markdown', reply_markup=reply_markup)


async def finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalizes the order, saves it, clears the cart, and sends a confirmation."""
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    cart = get_user_cart(user_id)
    checkout_data = session.get('checkout_data', {})

    cart_items = list(cart.values())
    total = calculate_cart_total(user_id)
    
    order_data = {
        "full_name": checkout_data.get('full_name'), "phone": checkout_data.get('phone'),
        "address": checkout_data.get('address'), "payment_method": checkout_data.get('payment_method'),
        "items": cart_items, "total": total
    }
    
    order_id = save_order(user_id, order_data)
    clear_user_cart(user_id)
    session['current_context'] = "main_menu"
    
    confirmation_text = f"🎉 **Order Confirmed!**\n\nThank you for your purchase.\n\n"
    confirmation_text += f"**Order ID:** `{order_id}`\n"
    confirmation_text += f"**Total Amount:** `₹{total:.2f}`\n"
    confirmation_text += f"**Payment Method:** {checkout_data.get('payment_method')}\n\n"
    confirmation_text += f"🚚 Your order will be shipped to:\n`{checkout_data.get('address')}`\n\n"
    confirmation_text += "You will receive tracking information via SMS shortly. Use '📦 My Orders' to check status."

    keyboard = [
        [InlineKeyboardButton("🛒 Shop Again", callback_data="browse_products")],
        [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)


# --- CALLBACK QUERY HANDLER ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The main handler for all inline button presses."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    
    data = query.data
    user_id = query.from_user.id
    
    try:
        if data.startswith("category_"):
            category_id = data.split("_", 1)[1]
            category_data = PRODUCT_CATALOG[category_id]
            keyboard = [[InlineKeyboardButton(f"{prod['name']} - ₹{prod['price']:.2f}", callback_data=f"product_{category_id}_{prod_id}")] for prod_id, prod in category_data["products"].items()]
            keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="browse_products")])
            await query.edit_message_text(f"**{category_data['name']}**\n\nSelect a product:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("product_"):
            _, category_id, product_id = data.split("_", 2)
            product = PRODUCT_CATALOG[category_id]["products"][product_id]
            product_text = f"**{product['name']}**\n\n__{product['description']}__\n\n**Price:** `₹{product['price']:.2f}`"
            keyboard = [
                [InlineKeyboardButton("➕ Add to Cart", callback_data=f"add_cart_{category_id}_{product_id}")],
                [InlineKeyboardButton(f"🔙 Back to {PRODUCT_CATALOG[category_id]['name']}", callback_data=f"category_{category_id}")],
                [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")]
            ]
            await query.edit_message_text(product_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("add_cart_"):
            _, category_id, product_id = data.split("_", 2)
            added_item = add_to_cart(user_id, category_id, product_id)
            await query.answer(f"✅ Added '{added_item['name']}' to cart!", show_alert=False)
        
        elif data == "browse_products": await browse_products(update, context)
        elif data == "view_cart": await view_cart(update, context)
        elif data == "my_orders": await my_orders(update, context)
        elif data == "about_us": await about_us(update, context)
        elif data == "contact_support": await contact_support(update, context)

        elif data == "clear_cart":
            clear_user_cart(user_id)
            await query.edit_message_text("🗑️ Your cart has been emptied.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]))
        
        elif data == "start_checkout": await start_checkout(update, context)
        elif data == "confirm_final_order": await finalize_order(update, context)
        
        elif data.startswith("payment_"):
            method = "Cash on Delivery" if data == "payment_cod" else "Online Payment"
            await handle_payment_selection(update, method)

    except Exception as e:
        logger.error(f"Error in button_callback: {e}", exc_info=True)
        await query.message.reply_text("An error occurred. Please try again or type /start.")

# --- MESSAGE HANDLER FOR MENU BUTTONS & CHECKOUT ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages, routing them to checkout or menu actions."""
    message_text = update.message.text
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # If user is in a checkout flow, process the text as a checkout step.
    if session.get('current_context', '').startswith('checkout'):
        await process_checkout_step(update, context)
        return
    
    # Otherwise, map the text to a main menu action.
    menu_actions = {
        "🛒 Browse Products": browse_products, "🛍️ View Cart": view_cart,
        "📦 My Orders": my_orders, "ℹ️ About Us": about_us,
        "📞 Contact Support": contact_support
    }
    
    action = menu_actions.get(message_text)
    if action:
        await action(update, context)
    else:
        await update.message.reply_text("Sorry, I didn't understand. Please use the menu buttons or type /help.")

# --- BOT SETUP AND EXECUTION ---
async def setup_bot():
    """Initializes the bot application and its handlers."""
    if not BOT_TOKEN:
        logger.critical("❌ CRITICAL: BOT_TOKEN not found in environment!")
        return None
    
    try:
        # Clear any lingering webhooks from previous runs
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Cleared existing webhooks.")
        await asyncio.sleep(1)

        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        logger.info("✅ Bot application setup complete.")
        return application
    except Exception as e:
        logger.critical(f"❌ Bot setup failed: {e}")
        return None

async def run_bot_async():
    """The main asynchronous function to run the bot."""
    global bot_running
    application = await setup_bot()
    if not application: return
    
    try:
        logger.info("🤖 Bot starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        bot_running = True
        logger.info("🚀 Bot is now running!")
        while bot_running: await asyncio.sleep(1)
    except (Conflict, TimedOut, NetworkError) as e:
        logger.error(f"⚠️ Bot network/conflict error: {e}. Retrying might be needed.")
    except Exception as e:
        logger.error(f"❌ Unhandled error in bot execution: {e}", exc_info=True)
    finally:
        bot_running = False
        if application and application.updater.running: await application.updater.stop()
        if application and application.running: await application.stop()
        logger.info("🛑 Bot has stopped.")

def run_bot_thread():
    """Runs the bot in a separate thread to not block the Flask app."""
    logger.info("🧵 Starting bot thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

def run_flask():
    """Runs the Flask web server."""
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on http://0.0.0.0:{port}")
    try:
        # Use a production-ready server if available
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        # Fallback to Flask's development server
        app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    logger.info("🚀 Initializing TrustyLads® India E-commerce Bot...")
    
    # Start the Telegram bot in a background thread
    bot_thread = Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    
    # Start the Flask app in the main thread
    run_flask()

