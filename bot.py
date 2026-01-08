import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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



load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Conversation states
(CURRENCY, INVOICE_NO, FROM_NAME, FROM_EMAIL, FROM_ADDRESS,
 BILL_TO_NAME, BILL_TO_EMAIL, BILL_TO_ADDRESS,
 ITEM_DESC, ITEM_QTY, ITEM_RATE, MORE_ITEMS,
 TAX, DISCOUNT, NOTES, STYLE, CONFIRM) = range(17)

# Supported currencies
CURRENCIES = [
    {'symbol': 'INR', 'name': 'Indian Rupee'},
    {'symbol': '$', 'name': 'US Dollar'},
    {'symbol': '€', 'name': 'Euro'},
    {'symbol': '£', 'name': 'British Pound'},
]

# Temporary storage (in memory)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    """Start command - Welcome message"""
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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "new_invoice":
        return await start_invoice(update, context)
    elif query.data == "help":
        await query.edit_message_text(
            "📚 *How to Use:*\n\n"
            "1️⃣ Click 'Generate Invoice'\n"
            "2️⃣ Select currency\n"
            "3️⃣ Enter details step by step\n"
            "4️⃣ Add items with quantity & rate\n"
            "5️⃣ Set tax & discount\n"
            "6️⃣ Get your PDF!\n\n"
            "💡 *Tip:* Type 'skip' for optional fields.\n\n"
            "Start again with /Start",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif query.data == "contact_us":
        await query.edit_message_text(
            "📞 *Contact Us:*\n\n"
            "For support or inquiries, reach out at:\n"
            "✉️ Email: support@localtools.app\n"
            "🌐 Website: https://localtools.app\n\n"
            "Developed by @arreharsh",
            parse_mode='Markdown'
        )
        return ConversationHandler.END


async def start_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start invoice creation"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    data = context.user_data
    data.clear()

    
    data['items'] = []
    data['invoice_date'] = datetime.now().strftime('%Y-%m-%d')
    data['due_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
   
    
    # Currency selection
    keyboard = [
        [InlineKeyboardButton(f"{c['symbol']} {c['name']}", callback_data=f"curr_{c['symbol']}")]
        for c in CURRENCIES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *Step 1: Select Currency*\n\nChoose your currency:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CURRENCY


async def currency_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    context.user_data['currency'] = query.data.split('_')[1]
    
    await query.edit_message_text(
        f"✅ Currency set to: *{query.data.split('_')[1]}*\n\n"
        "📝 *Step 2: Invoice Number*\n\nEnter invoice number (e.g., INV-001):",
        parse_mode='Markdown'
    )
    return INVOICE_NO


async def invoice_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get invoice number"""
    user_id = update.effective_user.id
    context.user_data['invoice_no'] = update.message.text.strip()
    
    await update.message.reply_text(
        "🏢 *Step 3: Your Company Details*\n\nEnter your company name:",
        parse_mode='Markdown'
    )
    return FROM_NAME


async def from_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get company name"""
    user_id = update.effective_user.id
    context.user_data['from_name'] = update.message.text.strip()
    
    await update.message.reply_text(
        "📧 Enter your company email (or type 'skip'):"
    )
    return FROM_EMAIL


async def from_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get company email"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    context.user_data['from_email'] = "" if text.lower() == 'skip' else text
    
    await update.message.reply_text(
        "🏠 Enter your company address (or type 'skip'):"
    )
    return FROM_ADDRESS


async def from_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get company address"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    context.user_data['from_address'] = "" if text.lower() == 'skip' else text
    
    await update.message.reply_text(
        "👤 *Step 4: Client Details*\n\nEnter client name:",
        parse_mode='Markdown'
    )
    return BILL_TO_NAME


async def bill_to_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get client name"""
    user_id = update.effective_user.id
    context.user_data['bill_to_name'] = update.message.text.strip()
    
    await update.message.reply_text(
        "📧 Enter client email (or type 'skip'):"
    )
    return BILL_TO_EMAIL


async def bill_to_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get client email"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    context.user_data['bill_to_email'] = "" if text.lower() == 'skip' else text
    
    await update.message.reply_text(
        "🏠 Enter client address (or type 'skip'):"
    )
    return BILL_TO_ADDRESS


async def bill_to_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get client address"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    context.user_data['bill_to_address'] = "" if text.lower() == 'skip' else text
    
    await update.message.reply_text(
        "📦 *Step 5: Add Items*\n\nEnter item description:",
        parse_mode='Markdown'
    )
    return ITEM_DESC


async def item_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get item description"""
    user_id = update.effective_user.id
    context.user_data['current_item'] = {'description': update.message.text.strip()}
    
    await update.message.reply_text("🔢 Enter quantity:")
    return ITEM_QTY


async def item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get item quantity"""
    user_id = update.effective_user.id
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError
        context.user_data['current_item']['qty'] = qty
        
        await update.message.reply_text("💵 Enter rate/price per unit:")
        return ITEM_RATE
    except:
        await update.message.reply_text("❌ Invalid quantity! Please enter a positive number:")
        return ITEM_QTY


async def item_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get item rate"""
    user_id = update.effective_user.id
    try:
        rate = float(update.message.text.strip())
        if rate < 0:
            raise ValueError
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
    except:
        await update.message.reply_text("❌ Invalid rate! Please enter a valid number:")
        return ITEM_RATE


async def more_items_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add more items or continue"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_item":
        await query.edit_message_text("📦 Enter next item description:")
        return ITEM_DESC
    else:
        await query.edit_message_text(
            "💰 *Step 6: Tax & Discount*\n\nEnter tax percentage (e.g., 18 for 18%):",
            parse_mode='Markdown'
        )
        return TAX


async def tax_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get tax percentage"""
    user_id = update.effective_user.id
    try:
        tax = float(update.message.text.strip())
        if tax < 0:
            raise ValueError
        context.user_data['tax'] = tax
        
        await update.message.reply_text("💸 Enter discount percentage (or 0 for no discount):")
        return DISCOUNT
    except:
        await update.message.reply_text("❌ Invalid tax! Please enter a valid number:")
        return TAX


async def discount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get discount percentage"""
    user_id = update.effective_user.id
    try:
        discount = float(update.message.text.strip())
        if discount < 0 or discount > 100:
            raise ValueError
        context.user_data['discount'] = discount
        
        await update.message.reply_text(
            "📝 *Step 7: Notes*\n\nEnter any notes (or type 'skip'):",
            parse_mode='Markdown'
        )
        return NOTES
    except:
        await update.message.reply_text("❌ Invalid discount! Enter 0-100:")
        return DISCOUNT


async def notes_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get notes"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
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


async def style_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle style selection and show preview"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
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
    
    await query.edit_message_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    return CONFIRM


async def generate_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send PDF"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Invoice generation cancelled. Use /start to create a new one.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    data = context.user_data
    
    await query.edit_message_text("⏳ Generating your professional invoice PDF...")
    
    try:
        # Generate PDF
        pdf_path = generate_pdf(data)
        
        # Send PDF to user
        with open(pdf_path, 'rb') as pdf_file:
            await context.bot.send_document(
                chat_id=user_id,
                document=pdf_file,
                filename=f"{data['invoice_no']}.pdf",
                caption=f"✅ Invoice generated successfully!\n\n📄 {data['invoice_no']}\n💰 Total: {data['currency']} {sum(i['qty']*i['rate'] for i in data['items']):.2f}"
            )
        
        # Clean up
        os.remove(pdf_path)
        context.user_data.clear()
        
        await query.message.reply_text(
            "🎉 Invoice sent successfully!\n\nUse /start to create another invoice.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        await query.edit_message_text(
            f"❌ Error generating PDF: {str(e)}\n\nPlease try again with /start"
        )
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operation cancelled. Use /start to begin again."
    )
    return ConversationHandler.END


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Sorry, I didn't understand that.\n\n"
        "👉 Use /start to create an invoice\n"
        "or use the buttons below."
    )


def main():
    """Start the bot"""
    # Create temp folder if doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler
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
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    
    # Start bot
    logger.info("🚀 Invoice Bot Started!")
    print("🚀 Invoice Bot Started!")
    print("Bot is running... Press Ctrl+C to stop.")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()