# main.py - Trusty Lads E-commerce Bot with Full Shopping Experience (Indian Version)

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

# In-memory storage for user sessions, carts, and orders
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


# --- FLASK APP ---
app = Flask(__name__)

@app.route('/')
def home():
    stats = {
        "active_users": len(user_sessions),
        "total_orders": len(user_orders),
        "total_products": sum(len(cat["products"]) for cat in PRODUCT_CATALOG.values()),
        "active_carts": len([cart for cart in user_carts.values() if cart]),
        "bot_uptime": "Online" if bot_running else "Starting..."
    }
    
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
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }}
                .stat {{ text-align: center; padding: 15px; background: rgba(255,255,255,0.5); border-radius: 10px; }}
                .feature {{ margin: 10px 0; padding: 10px; background: rgba(19, 136, 8, 0.1); border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛒 TrustyLads® India E-commerce Bot</h1>
                
                <div class="card">
                    <h2>📊 Live E-commerce Statistics</h2>
                    <div class="stats">
                        <div class="stat">
                            <h3>{stats['active_users']}</h3>
                            <p>Active Users</p>
                        </div>
                        <div class="stat">
                            <h3>{stats['total_orders']}</h3>
                            <p>Total Orders</p>
                        </div>
                        <div class="stat">
                            <h3>{stats['total_products']}</h3>
                            <p>Products Available</p>
                        </div>
                        <div class="stat">
                            <h3>{stats['active_carts']}</h3>
                            <p>Active Carts</p>
                        </div>
                        <div class="stat">
                            <h3>{'✅' if bot_running else '⏳'}</h3>
                            <p>{stats['bot_uptime']}</p>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h2>🛍️ E-commerce Features</h2>
                    <div class="feature">🛒 Complete Shopping Cart System</div>
                    <div class="feature">📦 Product Catalog with 4 Categories</div>
                    <div class="feature">💳 Full Checkout Process with COD</div>
                    <div class="feature">📋 Order History & Tracking</div>
                    <div class="feature">🎁 Promo Codes & Offers (INR)</div>
                    <div class="feature">🏪 About Us & Company Info</div>
                    <div class="feature">📞 Customer Support System</div>
                    <div class="feature">💾 Order Management & Storage</div>
                    <div class="feature">📱 Mobile-Friendly Interface</div>
                    <div class="feature">🔐 Session Management</div>
                </div>

                <div class="card">
                    <h2>📈 Business Information</h2>
                    <p><strong>Company:</strong> {COMPANY_INFO['name']}</p>
                    <p><strong>Products:</strong> {stats['total_products']} items across 4 categories</p>
                    <p><strong>Bot Status:</strong> {'✅ Online' if bot_running else '❌ Offline'}</p>
                    <p><a href="/health" style="color: #138808;">Health Check</a> | 
                       <a href="/orders" style="color: #138808;">Order Management</a></p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy" if bot_running else "starting",
        "service": "trusty-lads-ecommerce-bot-india",
        "version": "4.0-IN",
        "features": [
            "product_catalog", "shopping_cart", "checkout_process", 
            "order_management", "promo_codes_inr", "customer_support",
            "order_history", "company_info_in"
        ],
        "active_users": len(user_sessions),
        "total_orders": len(user_orders),
        "bot_running": bot_running
    })

@app.route('/orders')
def orders_dashboard():
    return jsonify({
        "total_orders": len(user_orders),
        "orders": user_orders,
        "active_carts": {str(k): v for k, v in user_carts.items() if v}
    })

# --- USER SESSION & CART MANAGEMENT ---
def get_user_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "first_interaction": datetime.now(),
            "message_count": 0,
            "current_context": None,
            "user_info": {},
            "last_order": None,
            "checkout_data": {}
        }
    return user_sessions[user_id]

def get_user_cart(user_id):
    if user_id not in user_carts:
        user_carts[user_id] = {}
    return user_carts[user_id]

def add_to_cart(user_id, category, product_id):
    cart = get_user_cart(user_id)
    item_key = f"{category}_{product_id}"
    
    if item_key in cart:
        cart[item_key]["quantity"] += 1
    else:
        product = PRODUCT_CATALOG[category]["products"][product_id]
        cart[item_key] = {
            "name": product["name"],
            "price": product["price"],
            "quantity": 1,
            "category": category,
            "product_id": product_id
        }
    return cart[item_key]

def calculate_cart_total(user_id):
    cart = get_user_cart(user_id)
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    return round(total, 2)

def clear_user_cart(user_id):
    user_carts[user_id] = {}

def save_order(user_id, order_data):
    global order_counter
    order_id = f"TL-IN-{order_counter}"
    order_counter += 1
    
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "date": datetime.now().isoformat(),
        "status": "Confirmed",
        **order_data
    }
    
    # Save to user orders
    if user_id not in user_orders:
        user_orders[user_id] = []
    user_orders[user_id].append(order)
    
    # Save individual order file
    try:
        os.makedirs("orders", exist_ok=True)
        with open(f"orders/order_{order_id}.json", "w") as f:
            json.dump(order, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving order file: {e}")
    
    # Append to all orders file
    try:
        with open("all_orders_in.txt", "a") as f:
            f.write(f"\n--- ORDER {order_id} ---\n")
            f.write(f"Date: {order['date']}\n")
            f.write(f"Customer: {order_data.get('full_name', 'N/A')}\n")
            f.write(f"Phone: {order_data.get('phone', 'N/A')}\n")
            f.write(f"Total: ₹{order_data.get('total', 0):.2f}\n")
            f.write(f"Payment: {order_data.get('payment_method', 'N/A')}\n")
            f.write("Items:\n")
            for item in order_data.get('items', []):
                f.write(f"  - {item['name']} x{item['quantity']} (₹{item['price']:.2f})\n")
            f.write("-" * 30 + "\n")
    except Exception as e:
        logger.error(f"Error appending to all_orders_in.txt: {e}")
    
    return order_id

# --- MAIN MENU KEYBOARD ---
def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🛒 Browse Products"), KeyboardButton("🛍️ View Cart")],
        [KeyboardButton("📦 My Orders"), KeyboardButton("ℹ️ About Us")],
        [KeyboardButton("📞 Contact Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- BOT COMMAND HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_user_session(user.id)
    logger.info(f"👋 User started e-commerce bot: {user.first_name} (ID: {user.id})")
    
    reply_markup = get_main_menu_keyboard()
    
    welcome_message = f"""
🎉 **Welcome to TrustyLads®, {user.first_name}!**

Your premium destination for quality products, now in India! 🛍️

🏪 **What We Offer:**
• 🧴 Premium Hair Care Products
• 🧔 Professional Beard Care
• 📱 Latest Electronics & Gadgets
• 👜 Stylish Accessories

🚀 **Shopping Made Easy:**
• Browse our complete catalog
• Add items to your cart instantly
• Secure checkout with COD & Online Payments
• Track your orders in real-time

🎁 **Special Offer:** Use code **WELCOME20** for 20% off your first order!

👆 *Use the menu buttons below to start shopping!*
    """
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )
    
    session['current_context'] = "main_menu"

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **TrustyLads® Bot Help**

**🛒 Shopping Commands:**
• Browse Products - View our product catalog
• View Cart - See items in your shopping cart
• My Orders - Check your order history

**ℹ️ Information:**
• About Us - Learn about TrustyLads®
• Contact Support - Get help from our team

**💡 How to Shop:**
1. **Browse** - Select "🛒 Browse Products"
2. **Choose** - Pick a category and products
3. **Add to Cart** - Click "Add to Cart" buttons
4. **Checkout** - Go to "🛍️ View Cart" and checkout
5. **Track** - Use "📦 My Orders" to track delivery

**🎁 Promo Codes (INR):**
• WELCOME20 - 20% off first order
• DIWALI150 - ₹150 off on orders ₹1500+
• BULK1000 - 15% off on orders ₹1000+
• PREMIUM2000 - 20% off on orders ₹2000+

Need more help? Use "📞 Contact Support"!
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for category_id, category_data in PRODUCT_CATALOG.items():
        keyboard.append([InlineKeyboardButton(
            category_data["name"], 
            callback_data=f"category_{category_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    catalog_text = """
🛒 **TrustyLads® Product Catalog**

Choose a category to browse our premium products:

🧴 **Hair Care** - Shampoos, conditioners, oils & treatments
🧔 **Beard Care** - Oils, balms, cleansers & grooming tools  
📱 **Electronics** - Chargers, speakers, cases & accessories
👜 **Accessories** - Wallets, watches, sunglasses & bags

💡 *Click a category below to see available products*
    """
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(catalog_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(catalog_text, parse_mode='Markdown', reply_markup=reply_markup)

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        keyboard = [
            [InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        cart_text = "🛍️ **Your Cart is Empty**\n\nStart shopping to add items to your cart!"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.message.reply_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)
        return
    
    cart_text = "🛍️ **Your Shopping Cart**\n\n"
    total = 0
    
    for item in cart.values():
        item_total = item["price"] * item["quantity"]
        total += item_total
        cart_text += f"• **{item['name']}**\n"
        cart_text += f"  Quantity: {item['quantity']} × ₹{item['price']:.2f} = ₹{item_total:.2f}\n\n"
    
    cart_text += f"💰 **Total: ₹{total:.2f}**"
    
    keyboard = [
        [InlineKeyboardButton("💳 Proceed to Checkout", callback_data="start_checkout")],
        [InlineKeyboardButton("🛒 Continue Shopping", callback_data="browse_products")],
        [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders = user_orders.get(user_id, [])
    
    if not orders:
        keyboard = [
            [InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        orders_text = "📦 **No Orders Yet**\n\nYou haven't placed any orders yet. Start shopping to see your orders here!"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.message.reply_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
        return
    
    orders_text = "📦 **Your Order History**\n\n"
    
    for order in orders[-5:]:
        order_date = datetime.fromisoformat(order['date']).strftime("%B %d, %Y")
        orders_text += f"🔸 **Order {order['order_id']}**\n"
        orders_text += f"Date: {order_date}\n"
        orders_text += f"Total: ₹{order['total']:.2f}\n"
        orders_text += f"Status: {order['status']}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Shop Again", callback_data="browse_products")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = f"""
ℹ️ **About TrustyLads® India**

🏪 **Our Mission:**
{COMPANY_INFO['mission']}

📍 **Address:**
{COMPANY_INFO['address']}

📞 **Contact Information:**
Phone: {COMPANY_INFO['phone']}
Email: {COMPANY_INFO['email']}
WhatsApp: {COMPANY_INFO['whatsapp']}

🕒 **Business Hours:**
{COMPANY_INFO['hours']}

🌟 **Why Choose TrustyLads®?**
{COMPANY_INFO['why_choose']}

🎯 **Our Promise:**
We're committed to providing you with premium quality products, exceptional customer service, and a seamless shopping experience.

Thank you for choosing TrustyLads®! 🙏
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Browse Products", callback_data="browse_products")],
        [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    support_text = f"""
📞 **Contact TrustyLads® Support**

**🆘 Get Help With:**
• Order issues & tracking
• Product questions
• Returns & exchanges
• Account problems
• General inquiries

**📱 Contact Methods:**
• **Phone:** {COMPANY_INFO['phone']}
• **Email:** {COMPANY_INFO['email']}
• **WhatsApp:** {COMPANY_INFO['whatsapp']}

**🕒 Support Hours:**
{COMPANY_INFO['hours']}

**⚡ Response Times:**
• Phone/WhatsApp: Immediate during business hours
• Email: Within 24 hours

**🔄 Returns & Exchanges:**
• 30-day return policy
• Free returns on defective items
• Easy exchange process
• Full refund guarantee

Need immediate help? Call or WhatsApp us now! 📞
    """
    
    clean_phone = COMPANY_INFO['whatsapp'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    
    keyboard = [
        [InlineKeyboardButton("📞 Call Now", url=f"tel:{COMPANY_INFO['phone']}")],
        [InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{clean_phone}")],
        [InlineKeyboardButton("📧 Send Email", url=f"mailto:{COMPANY_INFO['email']}")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)

# --- CALLBACK QUERY HANDLERS ---
async def handle_category_selection(update: Update, category_id: str):
    query = update.callback_query
    
    if category_id not in PRODUCT_CATALOG:
        await query.edit_message_text("❌ Category not found. Please try again.")
        return
    
    category_data = PRODUCT_CATALOG[category_id]
    keyboard = []
    for product_id, product in category_data["products"].items():
        keyboard.append([InlineKeyboardButton(
            f"{product['name']} - ₹{product['price']:.2f}",
            callback_data=f"product_{category_id}_{product_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="browse_products")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    category_text = f"🛒 **{category_data['name']} Products**\n\n"
    category_text += "Select a product to view details and add to cart:\n\n"
    
    for product in category_data["products"].values():
        category_text += f"• **{product['name']}** - ₹{product['price']:.2f}\n"
        category_text += f"  _{product['description']}_\n\n"
    
    await query.edit_message_text(category_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_product_selection(update: Update, category_id: str, product_id: str):
    query = update.callback_query
    
    if category_id not in PRODUCT_CATALOG or product_id not in PRODUCT_CATALOG[category_id]["products"]:
        await query.edit_message_text("❌ Product not found. Please try again.")
        return
    
    product = PRODUCT_CATALOG[category_id]["products"][product_id]
    
    keyboard = [
        [InlineKeyboardButton("🛒 Add to Cart", callback_data=f"add_cart_{category_id}_{product_id}")],
        [InlineKeyboardButton("🔙 Back to Category", callback_data=f"category_{category_id}")],
        [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    product_text = f"📦 **{product['name']}**\n\n"
    product_text += f"💰 **Price:** ₹{product['price']:.2f}\n\n"
    product_text += f"📝 **Description:**\n{product['description']}\n\n"
    product_text += "✅ **Features:**\n"
    product_text += "• Premium quality guaranteed\n"
    product_text += "• Fast shipping across India\n"
    product_text += "• 30-day money back guarantee\n"
    product_text += "• Secure payment processing\n\n"
    product_text += "Ready to add this to your cart?"
    
    await query.edit_message_text(product_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_add_to_cart(update: Update, category_id: str, product_id: str):
    query = update.callback_query
    user_id = query.from_user.id
    
    if category_id not in PRODUCT_CATALOG or product_id not in PRODUCT_CATALOG[category_id]["products"]:
        await query.edit_message_text("❌ Product not found. Please try again.")
        return
    
    added_item = add_to_cart(user_id, category_id, product_id)
    cart_total = calculate_cart_total(user_id)
    cart_count = sum(item["quantity"] for item in get_user_cart(user_id).values())
    
    keyboard = [
        [InlineKeyboardButton("🛒 Continue Shopping", callback_data=f"category_{category_id}")],
        [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("💳 Checkout Now", callback_data="start_checkout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    success_text = f"✅ **Added to Cart!**\n\n"
    success_text += f"**{added_item['name']}**\n"
    success_text += f"Quantity: {added_item['quantity']}\n"
    success_text += f"Price: ₹{added_item['price']:.2f}\n\n"
    success_text += f"🛍️ **Cart Summary:**\n"
    success_text += f"Items: {cart_count}\n"
    success_text += f"Total: ₹{cart_total:.2f}\n\n"
    success_text += "What would you like to do next?"
    
    await query.edit_message_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)

# --- CHECKOUT PROCESS ---
async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        await query.edit_message_text("Your cart is empty! Please add some items first.")
        return
    
    session = get_user_session(user_id)
    session['current_context'] = "checkout_name"
    session['checkout_data'] = {}
    
    cart_summary = "🛍️ **Order Summary:**\n\n"
    total = 0
    
    for item in cart.values():
        item_total = item["price"] * item["quantity"]
        total += item_total
        cart_summary += f"• {item['name']} x{item['quantity']} - ₹{item_total:.2f}\n"
    
    cart_summary += f"\n💰 **Subtotal: ₹{total:.2f}**\n\n"
    cart_summary += "📝 **Checkout Process:**\n"
    cart_summary += "1. Full Name ←\n"
    cart_summary += "2. Phone Number\n"
    cart_summary += "3. Delivery Address (with Pincode)\n"
    cart_summary += "4. Payment Method\n"
    cart_summary += "5. Promo Code (Optional)\n\n"
    cart_summary += "Please enter your **full name**:"
    
    await query.edit_message_text(cart_summary, parse_mode='Markdown')

async def process_checkout_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    message_text = update.message.text.strip()
    
    current_context = session.get('current_context')
    
    if current_context == "checkout_name":
        if not message_text:
            await update.message.reply_text("Please enter a valid name.")
            return
        session['checkout_data']['full_name'] = message_text
        session['current_context'] = "checkout_phone"
        await update.message.reply_text(f"✅ Name: {message_text}\n\n📱 Please enter your **10-digit phone number**:", parse_mode='Markdown')
    
    elif current_context == "checkout_phone":
        if not (message_text.isdigit() and len(message_text) == 10):
            await update.message.reply_text("Please enter a valid 10-digit phone number.")
            return
        session['checkout_data']['phone'] = message_text
        session['current_context'] = "checkout_address"
        await update.message.reply_text(f"✅ Phone: {message_text}\n\n📍 Please enter your **complete delivery address, including Pincode**:", parse_mode='Markdown')
    
    elif current_context == "checkout_address":
        if not message_text:
            await update.message.reply_text("Please enter a valid address.")
            return
        session['checkout_data']['address'] = message_text
        session['current_context'] = "checkout_payment"
        keyboard = [
            [InlineKeyboardButton("💰 Cash on Delivery (COD)", callback_data="payment_cod")],
            [InlineKeyboardButton("💳 Online Payment", callback_data="payment_online")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"✅ Address: {message_text}\n\n💳 Please select your **payment method**:", parse_mode='Markdown', reply_markup=reply_markup)
    
    elif current_context == "checkout_promo":
        promo_code = message_text.upper()
        if promo_code in ACTIVE_OFFERS:
            offer = ACTIVE_OFFERS[promo_code]
            cart_total = calculate_cart_total(user_id)
            
            if cart_total >= offer['min_order']:
                discount_amount = 0
                if "discount" in offer: # Percentage discount
                    discount_amount = cart_total * (offer['discount'] / 100)
                elif "discount_amount" in offer: # Fixed amount discount
                    discount_amount = offer['discount_amount']
                
                final_total = cart_total - discount_amount
                
                session['checkout_data']['promo_code'] = promo_code
                session['checkout_data']['discount'] = discount_amount
                session['checkout_data']['final_total'] = final_total
                
                await finalize_order(update, context)
            else:
                await update.message.reply_text(f"❌ Minimum order of ₹{offer['min_order']:.2f} required for this promo code.\n\nType 'SKIP' to proceed without promo code or enter a different code:")
        elif promo_code == "SKIP":
            session['checkout_data']['final_total'] = calculate_cart_total(user_id)
            await finalize_order(update, context)
        else:
            await update.message.reply_text("❌ Invalid promo code. Type 'SKIP' to proceed without promo code or enter a valid code:")

async def handle_payment_selection(update: Update, payment_method: str):
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    # TODO: For "Online Payment", integrate with Razorpay/PayU/Instamojo API here.
    # The current implementation proceeds directly for demonstration.
    
    session['checkout_data']['payment_method'] = payment_method
    session['current_context'] = "checkout_promo"
    
    promo_text = f"✅ Payment Method: {payment_method}\n\n"
    promo_text += "🎁 **Enter a promo code** for additional discounts or type **SKIP** to continue:\n\n"
    promo_text += "**Available Codes:**\n"
    
    for code, offer in ACTIVE_OFFERS.items():
        promo_text += f"• **{code}** - {offer['description']}\n"
    
    await query.edit_message_text(promo_text, parse_mode='Markdown')

async def finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    cart = get_user_cart(user_id)
    checkout_data = session.get('checkout_data', {})
    
    cart_items = []
    subtotal = 0
    
    for item in cart.values():
        cart_items.append({"name": item["name"], "price": item["price"], "quantity": item["quantity"], "total": item["price"] * item["quantity"]})
        subtotal += item["price"] * item["quantity"]
    
    final_total = checkout_data.get('final_total', subtotal)
    discount = checkout_data.get('discount', 0)
    
    order_data = {
        "full_name": checkout_data.get('full_name', 'N/A'), "phone": checkout_data.get('phone', 'N/A'),
        "address": checkout_data.get('address', 'N/A'), "payment_method": checkout_data.get('payment_method', 'N/A'),
        "items": cart_items, "subtotal": subtotal, "discount": discount, "total": final_total,
        "promo_code": checkout_data.get('promo_code', 'None')
    }
    
    order_id = save_order(user_id, order_data)
    clear_user_cart(user_id)
    session['current_context'] = "main_menu"
    session['last_order'] = order_id
    session['checkout_data'] = {}
    
    confirmation_text = f"✅ **Order Confirmed!**\n\n"
    confirmation_text += f"**Order ID:** {order_id}\n"
    confirmation_text += f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n"
    confirmation_text += f"**Customer:** {checkout_data.get('full_name', 'N/A')}\n"
    confirmation_text += f"**Phone:** {checkout_data.get('phone', 'N/A')}\n"
    confirmation_text += f"**Address:** {checkout_data.get('address', 'N/A')}\n"
    confirmation_text += f"**Payment:** {checkout_data.get('payment_method', 'N/A')}\n\n"
    
    confirmation_text += "📦 **Items Ordered:**\n"
    for item in cart_items:
        confirmation_text += f"• {item['name']} x{item['quantity']} - ₹{item['total']:.2f}\n"
    
    confirmation_text += f"\n💰 **Order Total:**\n"
    confirmation_text += f"Subtotal: ₹{subtotal:.2f}\n"
    
    if discount > 0:
        confirmation_text += f"Discount ({checkout_data.get('promo_code')}): -₹{discount:.2f}\n"
    
    confirmation_text += f"**Final Total: ₹{final_total:.2f}**\n\n"
    confirmation_text += "🚚 **Delivery Info:**\n"
    confirmation_text += "• Processing time: 1-2 business days\n"
    confirmation_text += "• Delivery time: 5-7 business days (across India)\n"
    confirmation_text += "• You'll receive tracking info via SMS within 24-48 hours\n\n"
    confirmation_text += "Thank you for shopping with TrustyLads®! 🙏"
    
    keyboard = [
        [InlineKeyboardButton("📦 Track Order", callback_data=f"track_{order_id}")],
        [InlineKeyboardButton("🛒 Shop Again", callback_data="browse_products")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)

# --- MAIN CALLBACK QUERY HANDLER ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    try:
        if data.startswith("category_"):
            category_id = data.split("_", 1)[1]
            await handle_category_selection(update, category_id)
        
        elif data.startswith("product_"):
            parts = data.split("_")
            if len(parts) >= 3:
                category_id, product_id = parts[1], "_".join(parts[2:])
                await handle_product_selection(update, category_id, product_id)
        
        elif data.startswith("add_cart_"):
            parts = data.split("_")
            if len(parts) >= 4:
                category_id, product_id = parts[2], "_".join(parts[3:])
                await handle_add_to_cart(update, category_id, product_id)
        
        elif data == "browse_products":
            await browse_products(update, context)
        
        elif data == "view_cart":
            await view_cart(update, context)
        
        elif data == "clear_cart":
            clear_user_cart(user_id)
            keyboard = [
                [InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🗑️ **Cart Cleared!**\n\nYour shopping cart is now empty.",
                parse_mode='Markdown', reply_markup=reply_markup
            )
        
        elif data == "start_checkout":
            await start_checkout(update, context)
        
        elif data.startswith("payment_"):
            payment_method = "Cash on Delivery" if data == "payment_cod" else "Online Payment"
            await handle_payment_selection(update, payment_method)
        
        elif data == "contact_support":
            await contact_support(update, context)
        
        elif data == "back_to_menu":
            keyboard = [
                [InlineKeyboardButton("🛒 Browse Products", callback_data="browse_products")],
                [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
                [InlineKeyboardButton("ℹ️ About Us", callback_data="about_us")],
                [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🏠 **Main Menu**\n\nUse the buttons below to navigate:",
                parse_mode='Markdown', reply_markup=reply_markup
            )
        
        elif data == "my_orders":
            await my_orders(update, context)
        
        elif data == "about_us":
            await about_us(update, context)
        
        elif data.startswith("track_"):
            order_id = data.split("_", 1)[1]
            await query.edit_message_text(
                f"📦 **Order Tracking**\n\nOrder ID: {order_id}\nStatus: Confirmed\n\nYour order is being processed and will be shipped within 1-2 business days. You will receive tracking details via SMS.",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")

# --- MESSAGE HANDLER FOR MENU BUTTONS ---
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if session.get('current_context', '').startswith('checkout'):
        await process_checkout_step(update, context)
        return
    
    menu_actions = {
        "🛒 Browse Products": browse_products,
        "🛍️ View Cart": view_cart,
        "📦 My Orders": my_orders,
        "ℹ️ About Us": about_us,
        "📞 Contact Support": contact_support
    }
    
    action = menu_actions.get(message_text)
    if action:
        await action(update, context)
    else:
        await update.message.reply_text(
            "I didn't understand that. Please use the menu buttons below or type /help for assistance.",
            reply_markup=get_main_menu_keyboard()
        )

# --- WEBHOOK CLEARING & BOT SETUP ---
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

async def setup_bot():
    global bot_running
    if not BOT_TOKEN:
        logger.error("❌ CRITICAL: BOT_TOKEN not found!")
        return None
    
    try:
        await clear_existing_webhooks()
        await asyncio.sleep(2)
        
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
        
        logger.info("✅ E-commerce bot setup complete")
        return application
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        return None

async def run_bot_async():
    global bot_running
    application = await setup_bot()
    if not application: return
    
    try:
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                bot_info = await application.bot.get_me()
                logger.info(f"🤖 E-commerce Bot @{bot_info.username} starting... (Attempt {retry_count + 1})")
                await application.initialize()
                await application.start()
                await application.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
                bot_running = True
                logger.info("🚀 E-commerce Bot (India) is now running!")
                logger.info("🛍️ Features: Product catalog, Shopping cart, Checkout (COD), Order management")
                while bot_running: await asyncio.sleep(1)
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
                else: logger.error("❌ Max retries reached. Bot startup failed.")
            except (TimedOut, NetworkError) as e:
                logger.error(f"⚠️ Network error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"❌ Bot error: {e}")
                break
    finally:
        bot_running = False
        if application: await application.stop()
        logger.info("🛑 E-commerce bot stopped")

def run_bot_thread():
    logger.info("🧵 Starting e-commerce bot thread...")
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

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    logger.info("🚀 Starting TrustyLads® India E-commerce Bot...")
    logger.info("🛍️ Features: Full shopping experience with cart, checkout, and order management")
    
    bot_thread = Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    logger.info("✅ E-commerce bot thread started")
    
    run_flask()
