# main.py - TrustyLads E-commerce Bot with Product Customization (Indian Version)

import asyncio
import os
import logging
import json
import re
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify
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

# --- GLOBAL STATE ---
bot_running = False
user_sessions = {}
user_carts = {}
user_orders = {}
order_counter = 1000

# --- E-COMMERCE DATA (INDIAN CONTEXT) ---

# PRODUCT CATALOG WITH CUSTOMIZABLE OPTIONS
PRODUCT_CATALOG = {
    "electronics": {
        "name": "📱 Electronics",
        "products": {
            "smartphone": {"name": "Flagship Smartphone", "price": 49999.00, "description": "High-end smartphone with advanced features", "customizable": ["color", "storage"]},
            "laptop": {"name": "Ultraportable Laptop", "price": 69999.00, "description": "Lightweight laptop for productivity", "customizable": ["color", "ram"]},
            "wireless_earbuds": {"name": "Premium Wireless Earbuds", "price": 8999.00, "description": "Noise-cancelling wireless earbuds", "customizable": ["color"]},
            "smartwatch": {"name": "Fitness Smartwatch", "price": 12999.00, "description": "Advanced fitness tracking smartwatch", "customizable": ["color", "strap"]},
        }
    },
    "clothing": {
        "name": "👕 Apparel",
        "products": {
            "tshirt": {"name": "Classic T-Shirt", "price": 499.00, "description": "100% Cotton, comfortable fit", "customizable": ["size", "color"]},
            "jeans": {"name": "Slim Fit Jeans", "price": 1299.00, "description": "Durable denim, modern style", "customizable": ["size", "color"]},
            "hoodie": {"name": "Premium Hoodie", "price": 1899.00, "description": "Warm and comfortable hoodie", "customizable": ["size", "color"]},
            "polo_shirt": {"name": "Polo Shirt", "price": 899.00, "description": "Smart casual polo shirt", "customizable": ["size", "color"]},
        }
    },
    "accessories": {
        "name": "👜 Accessories",
        "products": {
            "leather_wallet": {"name": "Genuine Leather Wallet", "price": 1899.00, "description": "Handcrafted leather wallet with RFID protection", "customizable": ["color", "material"]},
            "sunglasses": {"name": "UV Protection Sunglasses", "price": 2299.00, "description": "Stylish sunglasses with 100% UV protection", "customizable": ["color"]},
            "backpack": {"name": "Travel Backpack", "price": 2799.00, "description": "Durable backpack with laptop compartment", "customizable": ["color", "size"]},
            "wristwatch": {"name": "Classic Analog Watch", "price": 4999.00, "description": "Elegant timepiece with leather strap", "customizable": ["color", "strap"]},
        }
    },
    "home_decor": {
        "name": "🏠 Home & Decor",
        "products": {
            "table_lamp": {"name": "Modern Table Lamp", "price": 1599.00, "description": "Stylish LED table lamp", "customizable": ["color"]},
            "wall_art": {"name": "Abstract Wall Art", "price": 999.00, "description": "Beautiful canvas wall art", "customizable": ["size", "color"]},
            "cushion_cover": {"name": "Designer Cushion Cover", "price": 299.00, "description": "Premium quality cushion cover", "customizable": ["size", "color", "material"]},
            "photo_frame": {"name": "Wooden Photo Frame", "price": 599.00, "description": "Handcrafted wooden photo frame", "customizable": ["size", "color"]},
        }
    }
}

# AVAILABLE OPTIONS FOR CUSTOMIZATION
CUSTOMIZATION_OPTIONS = {
    "size": ["XS", "S", "M", "L", "XL", "XXL"],
    "color": ["Black", "White", "Red", "Blue", "Green", "Yellow", "Pink", "Purple", "Gray", "Brown"],
    "material": ["Cotton", "Leather", "Polyester", "Wool", "Silk", "Canvas"],
    "storage": ["64GB", "128GB", "256GB", "512GB", "1TB"],
    "ram": ["8GB", "16GB", "32GB"],
    "strap": ["Leather", "Metal", "Silicone", "Fabric"]
}

# HIDDEN PROMO CODES (NOT SHOWN TO USER)
ACTIVE_OFFERS = {
    "INDIAAFFIRM": {"discount": 10, "description": "10% off on all orders", "min_order": 0},
    "FESTIVESAVE": {"discount_amount": 500, "description": "₹500 off on orders above ₹5000", "min_order": 5000},
    "WELCOME15": {"discount": 15, "description": "15% off for new customers", "min_order": 0},
    "BULK20": {"discount": 20, "description": "20% off on orders above ₹10000", "min_order": 10000},
    "STUDENT25": {"discount": 25, "description": "25% student discount", "min_order": 0},
    "SAVE1000": {"discount_amount": 1000, "description": "₹1000 off on orders above ₹15000", "min_order": 15000},
}

# COMPANY INFORMATION
COMPANY_INFO = {
    "name": "TrustyLads®",
    "mission": "Providing premium quality products for the modern lifestyle with uncompromising standards, delivered across India.",
    "address": "123 Anna Salai, T. Nagar, Chennai, Tamil Nadu, 600017",
    "phone": "+91 6369360104",
    "email": "trustylads@gmail.com",
    "whatsapp": "+91 6369360104",
    "hours": "Monday - Sunday: 8:00 AM - 11:00 PM IST",
    "why_choose": "✅ Premium Quality Products\n✅ Fast & Reliable Shipping Across India\n✅ Cash on Delivery (COD) Available\n✅ 30-Day Money Back Guarantee\n✅ 24/7 Customer Support\n✅ Secure Payment Processing"
}

# --- FLASK WEB DASHBOARD ---
app = Flask(__name__)

@app.route('/')
def home():
    stats = {
        "active_users": len(user_sessions),
        "total_orders": sum(len(v) for v in user_orders.values()),
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
                        <div class="stat"><h3>{stats['active_users']}</h3><p>Active Users</p></div>
                        <div class="stat"><h3>{stats['total_orders']}</h3><p>Total Orders</p></div>
                        <div class="stat"><h3>{stats['total_products']}</h3><p>Products Available</p></div>
                        <div class="stat"><h3>{stats['active_carts']}</h3><p>Active Carts</p></div>
                        <div class="stat"><h3>{'✅' if bot_running else '⏳'}</h3><p>{stats['bot_uptime']}</p></div>
                    </div>
                </div>
                <div class="card">
                    <h2>🛍️ Enhanced E-commerce Features</h2>
                    <div class="feature">🛒 Complete Shopping Cart System</div>
                    <div class="feature">🎨 Product Customization (Size, Color, Material)</div>
                    <div class="feature">📦 Product Catalog with 4 Categories</div>
                    <div class="feature">💳 Full Checkout Process with COD</div>
                    <div class="feature">📋 Order History & Tracking</div>
                    <div class="feature">🔒 Hidden Promo Code System</div>
                    <div class="feature">📞 Functional Contact Support</div>
                    <div class="feature">💾 Order Management & Storage</div>
                </div>
                <div class="card">
                    <h2>📈 Business Information</h2>
                    <p><strong>Company:</strong> {COMPANY_INFO['name']}</p>
                    <p><strong>Products:</strong> {stats['total_products']} customizable items across 4 categories</p>
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
        "service": "trusty-lads-ecommerce-bot-india-enhanced",
        "version": "5.0-IN",
        "features": [
            "product_catalog", "product_customization", "shopping_cart", "checkout_process", 
            "order_management", "hidden_promo_codes", "customer_support",
            "order_history", "company_info_in", "functional_contact_links"
        ],
        "active_users": len(user_sessions),
        "total_orders": sum(len(v) for v in user_orders.values()),
        "bot_running": bot_running
    })

@app.route('/orders')
def orders_dashboard():
    return jsonify({
        "total_orders": sum(len(v) for v in user_orders.values()),
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
            "checkout_data": {},
            "customization_data": {}
        }
    return user_sessions[user_id]

def get_user_cart(user_id):
    if user_id not in user_carts:
        user_carts[user_id] = {}
    return user_carts[user_id]

def add_to_cart(user_id, category, product_id, customizations=None):
    cart = get_user_cart(user_id)
    custom_key_part = ""
    if customizations:
        # Create a sorted, consistent key for customizations
        sorted_customs = sorted(customizations.items())
        custom_key_part = "_" + "_".join([f"{k}-{v}" for k, v in sorted_customs])
    
    item_key = f"{category}_{product_id}{custom_key_part}"
    
    if item_key in cart:
        cart[item_key]["quantity"] += 1
    else:
        product = PRODUCT_CATALOG[category]["products"][product_id]
        cart[item_key] = {
            "name": product["name"],
            "price": product["price"],
            "quantity": 1,
            "category": category,
            "product_id": product_id,
            "customizations": customizations or {}
        }
    return cart[item_key]

def calculate_cart_total(user_id):
    cart = get_user_cart(user_id)
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    return round(total, 2)

def clear_user_cart(user_id):
    if user_id in user_carts:
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
    
    if user_id not in user_orders:
        user_orders[user_id] = []
    user_orders[user_id].append(order)
    
    try:
        os.makedirs("orders", exist_ok=True)
        with open(f"orders/order_{order_id}.json", "w") as f:
            json.dump(order, f, indent=4)
        
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
                if item.get('customizations'):
                    custom_str = ", ".join([f"{k.title()}: {v}" for k,v in item['customizations'].items()])
                    f.write(f"    Customizations: {custom_str}\n")
            f.write("-" * 30 + "\n")
    except Exception as e:
        logger.error(f"Error saving order file: {e}")
    
    return order_id

# --- UI & KEYBOARDS ---
def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🛒 Browse Products"), KeyboardButton("🛍️ View Cart")],
        [KeyboardButton("📦 My Orders"), KeyboardButton("ℹ️ About Us")],
        [KeyboardButton("📞 Contact Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- BOT COMMAND HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_session(user.id)['current_context'] = "main_menu"
    logger.info(f"👋 User started bot: {user.first_name} (ID: {user.id})")
    
    welcome_message = f"""
🎉 **Welcome to TrustyLads®, {user.first_name}!**

Your premium destination for customizable quality products in India! 🛍️

**🎨 Personalize Your Products:**
Choose size, color, and other options to create items that are uniquely yours.

**🚀 Shopping Made Easy:**
• Browse our complete catalog
• Customize and add items to your cart
• Secure checkout with **Cash on Delivery (COD)**
• Track your orders in real-time

**💰 Special Offers:**
Have a promo code? Apply it during checkout for amazing discounts!

👆 *Use the menu buttons below to start shopping!*
    """
    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown', 
        reply_markup=get_main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **TrustyLads® Bot Help**

**🛒 How to Shop:**
1.  **Browse**: Select "🛒 Browse Products".
2.  **Choose**: Pick a category, then a product.
3.  **Customize**: Follow the prompts to select size, color, etc.
4.  **Add to Cart**: Confirm your customizations to add the item.
5.  **Checkout**: Go to "🛍️ View Cart" and proceed to checkout.
6.  **Track**: Use "📦 My Orders" to see your order history.

**ℹ️ Information:**
• **About Us**: Learn about TrustyLads®.
• **Contact Support**: Get help from our team via Phone, WhatsApp, or Email.

**💰 Payment Methods:**
• Cash on Delivery (COD) is available for all orders.
• Online Payment options are coming soon!

*If you get stuck, you can always type /start to return to the main menu.*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(cat_data["name"], callback_data=f"category_{cat_id}")]
        for cat_id, cat_data in PRODUCT_CATALOG.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    catalog_text = "🛒 **Product Catalog**\n\nChoose a category to browse our premium customizable products:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(catalog_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(catalog_text, parse_mode='Markdown', reply_markup=reply_markup)

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        cart_text = "🛍️ **Your Cart is Empty**\n\nStart shopping to add customized items!"
        keyboard = [[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]
    else:
        cart_text = "🛍️ **Your Shopping Cart**\n\n"
        total = 0
        for item in cart.values():
            item_total = item["price"] * item["quantity"]
            total += item_total
            cart_text += f"• **{item['name']}**\n"
            if item.get('customizations'):
                customs = ", ".join([f"{k.title()}: {v}" for k, v in item['customizations'].items()])
                cart_text += f"  🎨 *Customizations: {customs}*\n"
            cart_text += f"  *Quantity: {item['quantity']} × ₹{item['price']:.2f} = ₹{item_total:.2f}*\n\n"
        
        cart_text += f"💰 **Total: ₹{total:.2f}**"
        keyboard = [
            [InlineKeyboardButton("💳 Proceed to Checkout", callback_data="start_checkout")],
            [InlineKeyboardButton("🛒 Continue Shopping", callback_data="browse_products")],
            [InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders = user_orders.get(user_id, [])
    
    if not orders:
        orders_text = "📦 **No Orders Yet**\n\nYou haven't placed any orders. Start shopping to see your orders here!"
        keyboard = [[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]
    else:
        orders_text = "📦 **Your Recent Orders**\n\n"
        for order in orders[-5:]: # Show last 5 orders
            order_date = datetime.fromisoformat(order['date']).strftime("%B %d, %Y")
            orders_text += f"🔸 **Order {order['order_id']}**\n"
            orders_text += f"   *Date*: {order_date}\n"
            orders_text += f"   *Total*: ₹{order['total']:.2f}\n"
            orders_text += f"   *Status*: {order['status']}\n\n"
        keyboard = [[InlineKeyboardButton("🛒 Shop Again", callback_data="browse_products")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = f"""
ℹ️ **About TrustyLads® India**

**Our Mission:**
{COMPANY_INFO['mission']}

**Why Choose Us?**
{COMPANY_INFO['why_choose']}

**Contact Information:**
📍 {COMPANY_INFO['address']}
📞 {COMPANY_INFO['phone']}
📧 {COMPANY_INFO['email']}
💬 {COMPANY_INFO['whatsapp']} (WhatsApp)
🕒 {COMPANY_INFO['hours']}

*We are committed to providing you with premium quality products and a seamless shopping experience.*
    """
    keyboard = [
        [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    support_text = f"""
📞 **Contact TrustyLads® Support**

Our team is here to help with order issues, product questions, or any other inquiries.

**📱 Contact Methods:**
• **Phone**: {COMPANY_INFO['phone']}
• **Email**: {COMPANY_INFO['email']}
• **WhatsApp**: {COMPANY_INFO['whatsapp']}

**🕒 Support Hours:**
{COMPANY_INFO['hours']}

*Use the buttons below to contact us directly!*
    """
    clean_phone = re.sub(r'\D', '', COMPANY_INFO['whatsapp'])
    keyboard = [
        [InlineKeyboardButton("📞 Call Now", url=f"tel:{COMPANY_INFO['phone']}")],
        [InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{clean_phone}")],
        [InlineKeyboardButton("📧 Send Email", url=f"mailto:{COMPANY_INFO['email']}")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)

# --- BOT CALLBACK & MESSAGE HANDLERS ---
async def handle_category_selection(update: Update, category_id: str):
    query = update.callback_query
    category_data = PRODUCT_CATALOG[category_id]
    
    keyboard = [
        [InlineKeyboardButton(f"{prod['name']} - ₹{prod['price']:.2f}", callback_data=f"product_{category_id}_{prod_id}")]
        for prod_id, prod in category_data["products"].items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="browse_products")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    category_text = f"🛒 **{category_data['name']}**\n\nSelect a product to view details and customize:"
    await query.edit_message_text(category_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_product_selection(update: Update, category_id: str, product_id: str):
    query = update.callback_query
    product = PRODUCT_CATALOG[category_id]["products"][product_id]
    
    product_text = f"📦 **{product['name']}**\n\n"
    product_text += f"💰 *Price: ₹{product['price']:.2f}*\n\n"
    product_text += f"📝 **Description:**\n{product['description']}\n\n"
    
    keyboard = []
    if product.get('customizable'):
        product_text += "🎨 *This product can be customized.*"
        keyboard.append([InlineKeyboardButton("🎨 Customize & Add to Cart", callback_data=f"customize_{category_id}_{product_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🛒 Add to Cart", callback_data=f"add_cart_{category_id}_{product_id}")])
    
    keyboard.extend([
        [InlineKeyboardButton("🔙 Back to Category", callback_data=f"category_{category_id}")],
        [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(product_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_product_customization(update: Update, category_id: str, product_id: str):
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    product = PRODUCT_CATALOG[category_id]["products"][product_id]
    customizable_options = product.get('customizable', [])
    
    session['customization_data'] = {
        'category_id': category_id,
        'product_id': product_id,
        'options': customizable_options,
        'current_option_index': 0,
        'selections': {}
    }
    await show_customization_option(update, context)

async def show_customization_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    custom_data = session['customization_data']
    idx = custom_data['current_option_index']
    
    # If all options are selected, add to cart
    if idx >= len(custom_data['options']):
        await add_customized_product_to_cart(update, context)
        return
        
    option_type = custom_data['options'][idx]
    product = PRODUCT_CATALOG[custom_data['category_id']]["products"][custom_data['product_id']]
    
    custom_text = f"🎨 **Customize {product['name']}**\n\n"
    custom_text += f"*Step {idx + 1} of {len(custom_data['options'])}: Select {option_type.title()}*\n\n"
    
    # Show previous selections
    if custom_data['selections']:
        selections_str = ", ".join([f"{k.title()}: {v}" for k, v in custom_data['selections'].items()])
        custom_text += f"✅ *Current choice(s): {selections_str}*\n\n"

    options = CUSTOMIZATION_OPTIONS.get(option_type, [])
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"select_{option_type}_{opt}")] for opt in options
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back to Product", callback_data=f"product_{custom_data['category_id']}_{custom_data['product_id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(custom_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_customization_selection(update: Update, option_type: str, selected_value: str):
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    custom_data = session['customization_data']
    custom_data['selections'][option_type] = selected_value
    custom_data['current_option_index'] += 1
    
    await show_customization_option(update, None)

async def add_customized_product_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    custom_data = session.pop('customization_data', {})
    if not custom_data:
        await query.edit_message_text("❌ Session expired. Please try again.")
        return

    category_id = custom_data['category_id']
    product_id = custom_data['product_id']
    selections = custom_data['selections']
    
    added_item = add_to_cart(user_id, category_id, product_id, selections)
    await show_add_to_cart_confirmation(query, added_item, user_id)

async def handle_add_to_cart(update: Update, category_id: str, product_id: str):
    query = update.callback_query
    user_id = query.from_user.id
    added_item = add_to_cart(user_id, category_id, product_id)
    await show_add_to_cart_confirmation(query, added_item, user_id)

async def show_add_to_cart_confirmation(query, added_item, user_id):
    cart_total = calculate_cart_total(user_id)
    cart_count = sum(item["quantity"] for item in get_user_cart(user_id).values())
    
    success_text = f"✅ **Added to Cart!**\n\n"
    success_text += f"**{added_item['name']}**\n"
    if added_item.get('customizations'):
        customs = ", ".join([f"{k.title()}: {v}" for k, v in added_item['customizations'].items()])
        success_text += f"  🎨 *Customizations: {customs}*\n"
    
    success_text += f"\n🛍️ **Cart Summary:**\n"
    success_text += f"   *Items*: {cart_count}\n"
    success_text += f"   *Total*: ₹{cart_total:.2f}\n\n"
    success_text += "What would you like to do next?"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Continue Shopping", callback_data=f"category_{added_item['category']}")],
        [InlineKeyboardButton("🛍️ View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("💳 Checkout Now", callback_data="start_checkout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)

# --- CHECKOUT PROCESS ---
async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not get_user_cart(user_id):
        await query.edit_message_text("Your cart is empty! Add items before checking out.", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]))
        return
    
    session = get_user_session(user_id)
    session['current_context'] = "checkout_name"
    session['checkout_data'] = {}
    
    await query.edit_message_text(
        "📝 **Checkout Step 1 of 3**\n\nPlease enter your **full name**:",
        parse_mode='Markdown'
    )

async def process_checkout_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    message_text = update.message.text.strip()
    
    current_context = session.get('current_context')
    
    if current_context == "checkout_name":
        session['checkout_data']['full_name'] = message_text
        session['current_context'] = "checkout_phone"
        await update.message.reply_text(f"✅ Name: {message_text}\n\n📝 **Checkout Step 2 of 3**\n\nPlease enter your **10-digit Indian mobile number**:", parse_mode='Markdown')
    
    elif current_context == "checkout_phone":
        if not (message_text.isdigit() and len(message_text) == 10):
            await update.message.reply_text("❌ Invalid number. Please enter a valid 10-digit mobile number.")
            return
        session['checkout_data']['phone'] = message_text
        session['current_context'] = "checkout_address"
        await update.message.reply_text(f"✅ Phone: {message_text}\n\n📝 **Checkout Step 3 of 3**\n\nPlease enter your **complete delivery address, including Pincode**:", parse_mode='Markdown')
    
    elif current_context == "checkout_address":
        session['checkout_data']['address'] = message_text
        session['current_context'] = "checkout_confirmation"
        await show_checkout_confirmation(update, context)
        
    elif current_context == "checkout_promo":
        promo_code = message_text.upper()
        cart_total = calculate_cart_total(user_id)
        
        if promo_code == "SKIP":
            session['checkout_data']['final_total'] = cart_total
            await finalize_order(update, context)
        elif promo_code in ACTIVE_OFFERS:
            offer = ACTIVE_OFFERS[promo_code]
            if cart_total >= offer['min_order']:
                discount = offer.get("discount", 0)
                discount_amount = offer.get("discount_amount", cart_total * (discount / 100))
                
                session['checkout_data']['promo_code'] = promo_code
                session['checkout_data']['discount'] = round(discount_amount, 2)
                session['checkout_data']['final_total'] = round(max(cart_total - discount_amount, 0), 2)
                
                await update.message.reply_text(f"✅ Promo code '{promo_code}' applied!", parse_mode='Markdown')
                await finalize_order(update, context)
            else:
                await update.message.reply_text(f"❌ Minimum order of ₹{offer['min_order']:.2f} required. Type 'SKIP' or enter a different code.")
        else:
            await update.message.reply_text("❌ Invalid promo code. Type 'SKIP' to proceed without one, or try another code.")

async def show_checkout_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    checkout_data = get_user_session(user_id).get('checkout_data', {})
    cart = get_user_cart(user_id)
    
    confirmation_text = "📋 **Please Confirm Your Order**\n\n"
    confirmation_text += "👤 **Delivery Details:**\n"
    confirmation_text += f"• **Name:** {checkout_data.get('full_name', 'N/A')}\n"
    confirmation_text += f"• **Phone:** {checkout_data.get('phone', 'N/A')}\n"
    confirmation_text += f"• **Address:** {checkout_data.get('address', 'N/A')}\n\n"
    
    confirmation_text += "🛍️ **Items:**\n"
    for item in cart.values():
        confirmation_text += f"• {item['name']} x{item['quantity']}\n"
        if item.get('customizations'):
            customs = ", ".join([f"{k.title()}: {v}" for k, v in item['customizations'].items()])
            confirmation_text += f"  🎨 *({customs})*\n"
    
    confirmation_text += f"\n💰 **Total: ₹{calculate_cart_total(user_id):.2f}**\n\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Select Payment", callback_data="confirm_details")],
        [InlineKeyboardButton("✏️ Make Corrections", callback_data="make_corrections")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_payment_selection(update: Update, payment_method: str):
    query = update.callback_query
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    session['checkout_data']['payment_method'] = payment_method
    session['current_context'] = "checkout_promo"
    
    promo_text = f"✅ Payment Method: **{payment_method}**\n\n"
    promo_text += "🎁 If you have a promo code, enter it now. Otherwise, type `SKIP` to complete your order."
    
    await query.edit_message_text(promo_text, parse_mode='Markdown')

async def finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    checkout_data = session['checkout_data']
    cart = get_user_cart(user_id)
    
    order_items = [{
        "name": item["name"], "price": item["price"], "quantity": item["quantity"],
        "total": item["price"] * item["quantity"], "customizations": item.get("customizations", {})
    } for item in cart.values()]
    
    subtotal = calculate_cart_total(user_id)
    discount = checkout_data.get('discount', 0)
    final_total = checkout_data.get('final_total', subtotal)
    
    order_data = {
        "full_name": checkout_data.get('full_name'), "phone": checkout_data.get('phone'),
        "address": checkout_data.get('address'), "payment_method": checkout_data.get('payment_method'),
        "items": order_items, "subtotal": subtotal, "discount": discount, "total": final_total,
        "promo_code": checkout_data.get('promo_code', 'None')
    }
    
    order_id = save_order(user_id, order_data)
    clear_user_cart(user_id)
    session['current_context'] = "main_menu"
    session['checkout_data'] = {}

    # Build final confirmation message
    confirmation_text = f"✅ **Order Confirmed!**\n\n"
    confirmation_text += f"Thank you for your purchase, {order_data['full_name']}.\n\n"
    confirmation_text += f"**Order ID:** `{order_id}`\n"
    confirmation_text += f"**Payment:** {order_data['payment_method']}\n\n"
    confirmation_text += "📦 **Items Ordered:**\n"
    for item in order_items:
        confirmation_text += f"• {item['name']} x{item['quantity']}\n"
        if item.get('customizations'):
            custom_text = ", ".join([f"{k.title()}: {v}" for k, v in item['customizations'].items()])
            confirmation_text += f"  🎨 *({custom_text})*\n"
    
    confirmation_text += f"\n💰 **Order Summary:**\n"
    confirmation_text += f"   Subtotal: ₹{subtotal:.2f}\n"
    if discount > 0:
        confirmation_text += f"   Discount ({order_data['promo_code']}): -₹{discount:.2f}\n"
    confirmation_text += f"   **Final Total: ₹{final_total:.2f}**\n\n"
    confirmation_text += "🚚 **Delivery Info:**\n"
    confirmation_text += "Your order will be delivered in **5-7 business days** across India. You'll receive tracking info via SMS within 48 hours.\n\n"
    confirmation_text += "Thank you for shopping with TrustyLads®! 🙏"
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📦 My Orders", callback_data="my_orders")]])
    await update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    try:
        if data.startswith("category_"):
            await handle_category_selection(update, data.split("_", 1)[1])
        elif data.startswith("product_"):
            _, category_id, product_id = data.split("_", 2)
            await handle_product_selection(update, category_id, product_id)
        elif data.startswith("customize_"):
            _, category_id, product_id = data.split("_", 2)
            await handle_product_customization(update, category_id, product_id)
        elif data.startswith("select_"):
            _, option_type, selected_value = data.split("_", 2)
            await handle_customization_selection(update, option_type, selected_value)
        elif data.startswith("add_cart_"):
            _, category_id, product_id = data.split("_", 2)
            await handle_add_to_cart(update, category_id, product_id)
        elif data == "browse_products":
            await browse_products(update, context)
        elif data == "view_cart":
            await view_cart(update, context)
        elif data == "clear_cart":
            clear_user_cart(user_id)
            await query.edit_message_text("🗑️ **Cart Cleared!**", parse_mode='Markdown', 
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Start Shopping", callback_data="browse_products")]]))
        elif data == "start_checkout":
            await start_checkout(update, context)
        elif data == "confirm_details":
            keyboard = [
                [InlineKeyboardButton("💰 Cash on Delivery (COD)", callback_data="payment_COD")],
                [InlineKeyboardButton("💳 Online Payment (Coming Soon)", callback_data="payment_online_disabled")]
            ]
            await query.edit_message_text("💳 Please select your payment method:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif data == "make_corrections":
            get_user_session(user_id)['current_context'] = "main_menu" # Reset context
            await query.message.delete()
            await start_command(update, context) # Restart the process
        elif data.startswith("payment_"):
            if data == "payment_COD":
                await handle_payment_selection(update, "Cash on Delivery (COD)")
            else:
                await query.answer("This payment method is not yet available.", show_alert=True)
        elif data == "contact_support":
            await contact_support(update, context)
        elif data == "back_to_menu":
            await query.message.delete()
            await start_command(update, context)
        elif data == "my_orders":
            await my_orders(update, context)
        elif data == "about_us":
            await about_us(update, context)

    except Exception as e:
        logger.error(f"Error in button_callback: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ An unexpected error occurred. Please try again or type /start to reset.")
        except:
            pass # Message might have been deleted

async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Prioritize checkout context over menu buttons
    if 'checkout' in session.get('current_context', ''):
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
        await update.message.reply_text("I didn't understand that. Please use the menu buttons or type /help.")

# --- BOT & SERVER INITIALIZATION ---
async def clear_existing_webhooks(bot: "telegram.Bot"):
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Cleared existing webhooks.")
    except Exception as e:
        logger.warning(f"⚠️ Could not clear webhooks: {e}")

async def run_bot_async():
    global bot_running
    if not BOT_TOKEN:
        logger.critical("❌ CRITICAL: BOT_TOKEN not found! The bot cannot start.")
        return

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    
    try:
        await clear_existing_webhooks(application.bot)
        await application.initialize()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await application.start()
        bot_running = True
        logger.info(f"🚀 Bot @{application.bot.username} is now running!")
        while bot_running:
            await asyncio.sleep(1)
    except (Conflict, TimedOut, NetworkError) as e:
        logger.error(f"❌ Network/Conflict error, retrying in 15s: {e}")
        await asyncio.sleep(15)
    except Exception as e:
        logger.critical(f"❌ A critical error occurred in the bot loop: {e}", exc_info=True)
    finally:
        bot_running = False
        if application.updater and application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        logger.info("🛑 Bot has been stopped.")

def run_bot_thread():
    logger.info("🧵 Starting bot thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot_async())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot interrupted by user (KeyboardInterrupt).")
    finally:
        loop.close()

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on http://0.0.0.0:{port}")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port, threads=8)
    except ImportError:
        logger.warning("⚠️ Waitress not found. Using Flask's development server (not for production).")
        app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    logger.info("🚀 Initializing TrustyLads® India E-commerce Bot...")
    bot_thread = Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    
    run_flask()
