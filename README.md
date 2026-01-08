# Invoice Bot 🤖

A Telegram bot for generating invoices quickly and easily.

**Live Bot:** [@localtools_bot](https://t.me/localtools_bot)

## 📋 Overview

Invoice Bot is a Telegram-based bot that allows users to generate professional invoices directly through Telegram. Simply interact with the bot and get your invoices generated instantly.

## ✨ Features

- 🧾 **Invoice Generation** - Create professional invoices via Telegram
- ⚡ **Fast & Easy** - Simple commands to generate invoices
- 🔒 **Secure** - Your data is handled securely
- 📱 **Mobile Friendly** - Use it anywhere through Telegram

## 🚀 Tech Stack

- **Language:** Python
- **Platform:** Telegram Bot API
- **PDF Generation:** Custom PDF generator

## 🛠️ Installation

### Prerequisites
- Python 3.x installed
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/arreharsh/invoice-bot.git

# Navigate to project directory
cd invoice-bot

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Copy example.env to .env
cp example.env .env

# Edit .env file and add your credentials
# Add your Telegram Bot Token and other required variables

# Run the bot
python bot.py
```

## ⚙️ Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
BOT_TOKEN=your_telegram_bot_token
# Add other required environment variables as per example.env
```

## 📖 Usage

1. Start the bot on Telegram: [@localtools_bot](https://t.me/localtools_bot)
2. Follow the bot's instructions to generate your invoice
3. Provide the required details
4. Receive your generated invoice as a PDF

## 📁 Project Structure

- `bot.py` - Main bot application
- `simple_pdf.py` - PDF generation module
- `requirements.txt` - Python dependencies
- `example.env` - Environment variables template
- `runtime.txt` - Python runtime version

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

## 📧 Contact

For questions or support, reach out via:
- Telegram: [@localtools_bot](https://t.me/localtools_bot)
- Email: [arreharsh@gmail.com](mailto:arreharsh@gmail.com)
- GitHub Issues

## 📄 License

This project is open source and available for use.

---

Made with ❤️ for easy invoice generation
