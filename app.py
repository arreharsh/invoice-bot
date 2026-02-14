import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TimedOut, NetworkError
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from datetime import datetime, timedelta
from simple_pdf import generate_pdf
import re
from functools import wraps

load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token validation
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

# Constants
MAX_TEXT_LENGTH = 500
MAX_ITEMS = 50
MAX_QUANTITY = 100000
MAX_RATE = 10000000
CONVERSATION_TIMEOUT = 900  # 15 minutes
USER_COOLDOWN = {}  # Rate limiting

# Conversation states
(CURRENCY, INVOICE_NO, FROM_NAME, FROM_EMAIL, FROM_ADDRESS,
 BILL_TO_NAME, BILL_TO_EMAIL, BILL_TO_ADDRESS,
 ITEM_DESC, ITEM_QTY, ITEM_RATE, MORE_ITEMS,
 TAX, DISCOUNT, NOTES, STYLE, CONFIRM) = range(17)

# Supported currencies
CURRENCIES = [
    {'symbol': '₹', 'code': 'INR', 'name': 'Indian Rupee'},
    {'symbol': '$', 'code': 'USD', 'name': 'US Dollar'},
    {'symbol': '€', 'code': 'EUR', 'name': 'Euro'},
    {'symbol': '£', 'code': 'GBP', 'name': 'British Pound'},
]


# Rate limiting decorator
def rate_limit(cooldown_seconds=3):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            current_time = datetime.now()
            
            if user_id in USER_COOLDOWN:
                time_diff = (current_time - USER_COOLDOWN[user_id]).total_seconds()
                if time_diff < cooldown_seconds:
                    return None
            
            USER_COOLDOWN[user_id] = current_time
            return await func(update, context)
        return wrapper
    return decorator


# Input validation helpers
def validate_email(email):
    """Basic email validation"""
    if not email or email.lower() == 'skip':
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_text_length(text, max_length=MAX_TEXT_LENGTH):
    """Validate text length"""
    return len(text.strip()) <= max_length


def sanitize_input(text):
    """Sanitize user input"""
    return text.strip()[:MAX_TEXT_LENGTH]


# Error handler wrapper
async def safe_edit_message(query, text, reply_markup=None, parse_mode='Markdown'):
    """Safely edit message with error handling"""
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            # Message same hai, ignore karo
            pass
        elif "Message to edit not found" in str(e):
            # Message delete ho gaya, naya bhejo
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            logger.error(f"BadRequest error: {e}")
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except:
            pass


@rate_limit(cooldown_seconds=2)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Welcome message"""
    try:
        # Clear previous data
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("📄 Generate Invoice", callback_data="new_invoice")],
            [InlineKeyboardButton("📞 Contact Us", callback_data="contact_us")],
            [InlineKeyboardButton("❓ How To Use", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎉 *Welcome to Invoice Generator Bot!*\n\n"
            "Generate professional PDF invoices instantly!\n\n"
            "✅ Multiple currencies\n"
            "✅ Auto calculations\n"
            "✅ Professional PDFs\n\n"
            "Click below to start 👇",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again with /start")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks with proper error handling"""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Error answering callback: {e}")
        return
    
    try:
        if query.data == "new_invoice":
            return await start_invoice(update, context)
        
        elif query.data == "help":
            await safe_edit_message(
                query,
                "📚 *How to Use:*\n\n"
                "1️⃣ Click 'Generate Invoice'\n"
                "2️⃣ Select currency\n"
                "3️⃣ Enter details step by step\n"
                "4️⃣ Add items with quantity & rate\n"
                "5️⃣ Set tax & discount\n"
                "6️⃣ Get your PDF!\n\n"
                "💡 *Tip:* Type 'skip' for optional fields.\n\n"
                "Start again with /start"
            )
            return ConversationHandler.END
        
        elif query.data == "contact_us":
            await safe_edit_message(
                query,
                "📞 *Contact Us:*\n\n"
                "For support or inquiries, reach out at:\n"
                "✉️ Email: support@localtools.app\n"
                "🌐 Website: https://localtools.app\n\n"
                "Developed by @arreharsh"
            )
            return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        try:
            await query.message.reply_text("❌ Something went wrong. Please use /start to try again.")
        except:
            pass
        return ConversationHandler.END


async def start_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start invoice creation"""
    query = update.callback_query
    
    try:
        # Clear and initialize user data
        context.user_data.clear()
        context.user_data['items'] = []
        context.user_data['invoice_date'] = datetime.now().strftime('%Y-%m-%d')
        context.user_data['due_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        context.user_data['start_time'] = datetime.now()
        
        # Currency selection
        keyboard = [
            [InlineKeyboardButton(f"{c['symbol']} {c['name']}", callback_data=f"curr_{c['code']}")]
            for c in CURRENCIES
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(
            query,
            "💰 *Step 1: Select Currency*\n\nChoose your currency:",
            reply_markup=reply_markup
        )
        return CURRENCY
    
    except Exception as e:
        logger.error(f"Error starting invoice: {e}")
        await query.message.reply_text("❌ Error starting invoice. Please try /start again.")
        return ConversationHandler.END


async def currency_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency selection"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        currency_code = query.data.split('_')[1]
        currency_data = next((c for c in CURRENCIES if c['code'] == currency_code), None)
        
        if not currency_data:
            await query.message.reply_text("❌ Invalid currency. Please use /start to try again.")
            return ConversationHandler.END
        
        context.user_data['currency'] = currency_code
        context.user_data['currency_code'] = currency_code
        
        await safe_edit_message(
            query,
            f"✅ Currency set to: *{currency_data['symbol']} {currency_data['name']}*\n\n"
            "📝 *Step 2: Invoice Number*\n\nEnter invoice number (e.g., INV-001):"
        )
        return INVOICE_NO
    
    except Exception as e:
        logger.error(f"Error in currency selection: {e}")
        await query.message.reply_text("❌ Error processing selection. Please use /start to try again.")
        return ConversationHandler.END


async def invoice_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get invoice number"""
    try:
        text = sanitize_input(update.message.text)
        
        if not text or not validate_text_length(text, 50):
            await update.message.reply_text("❌ Invalid invoice number. Please enter a valid number (max 50 characters):")
            return INVOICE_NO
        
        context.user_data['invoice_no'] = text
        
        await update.message.reply_text(
            "🏢 *Step 3: Your Company Details*\n\nEnter your company name:",
            parse_mode='Markdown'
        )
        return FROM_NAME
    
    except Exception as e:
        logger.error(f"Error in invoice_number: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return INVOICE_NO


async def from_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get company name"""
    try:
        text = sanitize_input(update.message.text)
        
        if not text or not validate_text_length(text, 200):
            await update.message.reply_text("❌ Invalid name. Please enter a valid company name (max 200 characters):")
            return FROM_NAME
        
        context.user_data['from_name'] = text
        
        await update.message.reply_text("📧 Enter your company email (or type 'skip'):")
        return FROM_EMAIL
    
    except Exception as e:
        logger.error(f"Error in from_name: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return FROM_NAME


async def from_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get company email"""
    try:
        text = sanitize_input(update.message.text)
        
        if text.lower() != 'skip' and not validate_email(text):
            await update.message.reply_text("❌ Invalid email format. Please enter a valid email or type 'skip':")
            return FROM_EMAIL
        
        context.user_data['from_email'] = "" if text.lower() == 'skip' else text
        
        await update.message.reply_text("🏠 Enter your company address (or type 'skip'):")
        return FROM_ADDRESS
    
    except Exception as e:
        logger.error(f"Error in from_email: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return FROM_EMAIL


async def from_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get company address"""
    try:
        text = sanitize_input(update.message.text)
        
        if not validate_text_length(text, 300):
            await update.message.reply_text("❌ Address too long. Please enter a shorter address (max 300 characters):")
            return FROM_ADDRESS
        
        context.user_data['from_address'] = "" if text.lower() == 'skip' else text
        
        await update.message.reply_text(
            "👤 *Step 4: Client Details*\n\nEnter client name:",
            parse_mode='Markdown'
        )
        return BILL_TO_NAME
    
    except Exception as e:
        logger.error(f"Error in from_address: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return FROM_ADDRESS


async def bill_to_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get client name"""
    try:
        text = sanitize_input(update.message.text)
        
        if not text or not validate_text_length(text, 200):
            await update.message.reply_text("❌ Invalid name. Please enter a valid client name (max 200 characters):")
            return BILL_TO_NAME
        
        context.user_data['bill_to_name'] = text
        
        await update.message.reply_text("📧 Enter client email (or type 'skip'):")
        return BILL_TO_EMAIL
    
    except Exception as e:
        logger.error(f"Error in bill_to_name: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return BILL_TO_NAME


async def bill_to_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get client email"""
    try:
        text = sanitize_input(update.message.text)
        
        if text.lower() != 'skip' and not validate_email(text):
            await update.message.reply_text("❌ Invalid email format. Please enter a valid email or type 'skip':")
            return BILL_TO_EMAIL
        
        context.user_data['bill_to_email'] = "" if text.lower() == 'skip' else text
        
        await update.message.reply_text("🏠 Enter client address (or type 'skip'):")
        return BILL_TO_ADDRESS
    
    except Exception as e:
        logger.error(f"Error in bill_to_email: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return BILL_TO_EMAIL


async def bill_to_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get client address"""
    try:
        text = sanitize_input(update.message.text)
        
        if not validate_text_length(text, 300):
            await update.message.reply_text("❌ Address too long. Please enter a shorter address (max 300 characters):")
            return BILL_TO_ADDRESS
        
        context.user_data['bill_to_address'] = "" if text.lower() == 'skip' else text
        
        await update.message.reply_text(
            "📦 *Step 5: Add Items*\n\nEnter item description:",
            parse_mode='Markdown'
        )
        return ITEM_DESC
    
    except Exception as e:
        logger.error(f"Error in bill_to_address: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return BILL_TO_ADDRESS


async def item_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get item description"""
    try:
        # Check max items limit
        if len(context.user_data.get('items', [])) >= MAX_ITEMS:
            await update.message.reply_text(f"❌ Maximum {MAX_ITEMS} items allowed. Please continue to next step.")
            return MORE_ITEMS
        
        text = sanitize_input(update.message.text)
        
        if not text or not validate_text_length(text, 300):
            await update.message.reply_text("❌ Invalid description. Please enter a valid item description (max 300 characters):")
            return ITEM_DESC
        
        context.user_data['current_item'] = {'description': text}
        
        await update.message.reply_text("🔢 Enter quantity (1-100000):")
        return ITEM_QTY
    
    except Exception as e:
        logger.error(f"Error in item_description: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return ITEM_DESC


async def item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get item quantity"""
    try:
        text = update.message.text.strip()
        
        try:
            qty = int(text)
            if qty <= 0 or qty > MAX_QUANTITY:
                raise ValueError
        except:
            await update.message.reply_text(f"❌ Invalid quantity! Please enter a number between 1 and {MAX_QUANTITY}:")
            return ITEM_QTY
        
        context.user_data['current_item']['qty'] = qty
        
        await update.message.reply_text(f"💵 Enter rate/price per unit (max {MAX_RATE}):")
        return ITEM_RATE
    
    except Exception as e:
        logger.error(f"Error in item_quantity: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return ITEM_QTY


async def item_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get item rate"""
    try:
        text = update.message.text.strip()
        
        try:
            rate = float(text)
            if rate < 0 or rate > MAX_RATE:
                raise ValueError
        except:
            await update.message.reply_text(f"❌ Invalid rate! Please enter a valid number (0-{MAX_RATE}):")
            return ITEM_RATE
        
        context.user_data['current_item']['rate'] = rate
        
        # Add item to list
        context.user_data['items'].append(context.user_data['current_item'])
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Another Item", callback_data="add_item")],
            [InlineKeyboardButton("✅ Done, Continue", callback_data="done_items")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        items_count = len(context.user_data['items'])
        await update.message.reply_text(
            f"✅ Item added! ({items_count} item(s) total)\n\nWant to add more items?",
            reply_markup=reply_markup
        )
        return MORE_ITEMS
    
    except Exception as e:
        logger.error(f"Error in item_rate: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return ITEM_RATE


async def more_items_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add more items or continue"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        if query.data == "add_item":
            if len(context.user_data.get('items', [])) >= MAX_ITEMS:
                await safe_edit_message(query, f"❌ Maximum {MAX_ITEMS} items reached. Continuing to next step...")
                await asyncio.sleep(1)
                await query.message.reply_text(
                    "💰 *Step 6: Tax & Discount*\n\nEnter tax percentage (e.g., 18 for 18%):",
                    parse_mode='Markdown'
                )
                return TAX
            
            await safe_edit_message(query, "📦 Enter next item description:")
            return ITEM_DESC
        else:
            await safe_edit_message(
                query,
                "💰 *Step 6: Tax & Discount*\n\nEnter tax percentage (e.g., 18 for 18%):"
            )
            return TAX
    
    except Exception as e:
        logger.error(f"Error in more_items_handler: {e}")
        await query.message.reply_text("❌ Error processing selection. Please use /start to try again.")
        return ConversationHandler.END


async def tax_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get tax percentage"""
    try:
        text = update.message.text.strip()
        
        try:
            tax = float(text)
            if tax < 0 or tax > 100:
                raise ValueError
        except:
            await update.message.reply_text("❌ Invalid tax! Please enter a number between 0 and 100:")
            return TAX
        
        context.user_data['tax'] = tax
        
        await update.message.reply_text("💸 Enter discount percentage (0-100, or 0 for no discount):")
        return DISCOUNT
    
    except Exception as e:
        logger.error(f"Error in tax_input: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return TAX


async def discount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get discount percentage"""
    try:
        text = update.message.text.strip()
        
        try:
            discount = float(text)
            if discount < 0 or discount > 100:
                raise ValueError
        except:
            await update.message.reply_text("❌ Invalid discount! Enter a number between 0 and 100:")
            return DISCOUNT
        
        context.user_data['discount'] = discount
        
        await update.message.reply_text(
            "📝 *Step 7: Notes*\n\nEnter any notes (or type 'skip'):",
            parse_mode='Markdown'
        )
        return NOTES
    
    except Exception as e:
        logger.error(f"Error in discount_input: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return DISCOUNT


async def notes_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get notes"""
    try:
        text = sanitize_input(update.message.text)
        
        if not validate_text_length(text, 500):
            await update.message.reply_text("❌ Notes too long. Please enter shorter notes (max 500 characters):")
            return NOTES
        
        context.user_data['notes'] = "Thank you for your business!" if text.lower() == 'skip' else text
        
        # PDF style selection
        keyboard = [
            [InlineKeyboardButton("🎨 Color PDF", callback_data="style_color")],
            [InlineKeyboardButton("⚫ Black & White", callback_data="style_bw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎨 *Step 8: PDF Style*\n\nChoose PDF style:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return STYLE
    
    except Exception as e:
        logger.error(f"Error in notes_input: {e}")
        await update.message.reply_text("❌ Error processing input. Please try again:")
        return NOTES


async def style_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle style selection and show preview"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        context.user_data['is_bw'] = (query.data == "style_bw")
        
        # Calculate totals for preview
        data = context.user_data
        subtotal = sum(item['qty'] * item['rate'] for item in data['items'])
        discount_amount = subtotal * data['discount'] / 100
        tax_amount = (subtotal - discount_amount) * data['tax'] / 100
        total = subtotal - discount_amount + tax_amount
        
        curr = data['currency']
        
        summary = f"""
📄 *Invoice Preview*

📋 Invoice: {data['invoice_no']}
💰 Currency: {curr}

🏢 *From:* {data['from_name']}
👤 *Bill To:* {data['bill_to_name']}

📦 *Items:* {len(data['items'])} item(s)

💵 *Summary:*
  Subtotal: {curr} {subtotal:.2f}
  Discount ({data['discount']}%): -{curr} {discount_amount:.2f}
  Tax ({data['tax']}%): +{curr} {tax_amount:.2f}
  
  *Total: {curr} {total:.2f}*

🎨 Style: {"Black & White" if data['is_bw'] else "Color"}

Ready to generate?
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Generate PDF", callback_data="generate")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, summary, reply_markup=reply_markup)
        return CONFIRM
    
    except Exception as e:
        logger.error(f"Error in style_selection: {e}")
        await query.message.reply_text("❌ Error processing selection. Please use /start to try again.")
        return ConversationHandler.END


async def generate_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send PDF"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        if query.data == "cancel":
            await safe_edit_message(query, "❌ Invoice generation cancelled. Use /start to create a new one.")
            context.user_data.clear()
            return ConversationHandler.END
        
        user_id = update.effective_user.id
        data = context.user_data
        
        await safe_edit_message(query, "⏳ Generating your professional invoice PDF...")
        
        # Calculate final total
        subtotal = sum(item['qty'] * item['rate'] for item in data['items'])
        discount_amount = subtotal * data['discount'] / 100
        tax_amount = (subtotal - discount_amount) * data['tax'] / 100
        total = subtotal - discount_amount + tax_amount
        
        # Generate PDF
        pdf_path = None
        try:
            pdf_path = generate_pdf(data)
            
            # Validate PDF was created
            if not pdf_path or not os.path.exists(pdf_path):
                raise Exception("PDF file not created")
            
            # Check file size (max 50MB for Telegram)
            file_size = os.path.getsize(pdf_path)
            if file_size > 50 * 1024 * 1024:
                raise Exception("PDF file too large")
            
            # Send PDF to user
            with open(pdf_path, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=pdf_file,
                    filename=f"{data['invoice_no']}.pdf",
                    caption=f"✅ Invoice generated successfully!\n\n📄 {data['invoice_no']}\n💰 Total: {data['currency']} {total:.2f}"
                )
            
            await query.message.reply_text(
                "🎉 Invoice sent successfully!\n\nUse /start to create another invoice.",
                parse_mode='Markdown'
            )
            
            logger.info(f"Invoice generated successfully for user {user_id}: {data['invoice_no']}")
        
        except Exception as pdf_error:
            logger.error(f"PDF generation error for user {user_id}: {pdf_error}")
            await query.message.reply_text(
                "❌ Error generating PDF. Please try again with /start\n\n"
                "If the problem persists, contact support."
            )
        
        finally:
            # Clean up PDF file
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except Exception as e:
                    logger.error(f"Error deleting PDF file: {e}")
            
            # Clear user data
            context.user_data.clear()
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error in generate_pdf_handler: {e}")
        try:
            await query.message.reply_text("❌ An error occurred. Please try again with /start")
            context.user_data.clear()
        except:
            pass
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    try:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Operation cancelled. Use /start to begin again."
        )
    except Exception as e:
        logger.error(f"Error in cancel: {e}")
    
    return ConversationHandler.END


async def conversation_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation timeout"""
    try:
        context.user_data.clear()
        if update.message:
            await update.message.reply_text(
                "⏰ Session expired due to inactivity.\n\n"
                "Use /start to create a new invoice."
            )
        elif update.callback_query:
            await update.callback_query.message.reply_text(
                "⏰ Session expired due to inactivity.\n\n"
                "Use /start to create a new invoice."
            )
    except Exception as e:
        logger.error(f"Error in timeout handler: {e}")
    
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    try:
        logger.error(f"Update {update} caused error {context.error}")
        
        # Inform user about error
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again with /start\n\n"
                "If the issue persists, contact support at support@localtools.app"
            )
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown messages"""
    try:
        await update.message.reply_text(
            "❌ Sorry, I didn't understand that.\n\n"
            "👉 Use /start to create an invoice"
        )
    except Exception as e:
        logger.error(f"Error in unknown_message: {e}")


# ===============================
# 🚀 WEBHOOK MODE 
# ===============================

from fastapi import FastAPI, Request

app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()


def setup_handlers(application):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(button_handler, pattern='^new_invoice$')
        ],
        states={
            CURRENCY: [CallbackQueryHandler(currency_selected, pattern='^curr_')],
            INVOICE_NO: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_number)],
            FROM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_name)],
            FROM_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_email)],
            FROM_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_address)],
            BILL_TO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bill_to_name)],
            BILL_TO_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bill_to_email)],
            BILL_TO_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, bill_to_address)],
            ITEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_description)],
            ITEM_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_quantity)],
            ITEM_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_rate)],
            MORE_ITEMS: [CallbackQueryHandler(more_items_handler)],
            TAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, tax_input)],
            DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, discount_input)],
            NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, notes_input)],
            STYLE: [CallbackQueryHandler(style_selection, pattern='^style_')],
            CONFIRM: [CallbackQueryHandler(generate_pdf_handler)],
            ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, conversation_timeout)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=CONVERSATION_TIMEOUT
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    application.add_error_handler(error_handler)


@app.on_event("startup")
async def startup():
    os.makedirs('temp', exist_ok=True)
    setup_handlers(telegram_app)
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(
        url="https://invoice-bot-af6a.onrender.com/webhook"
    )
    print("🚀 Webhook Active")


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/")
async def health():
    return {"status": "Bot Running"}
