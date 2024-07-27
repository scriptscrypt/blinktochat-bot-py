import os
import certifi
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv('ENV_TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('ENV_MONGO_URI')
db_name = os.getenv('ENV_MONGO_DB_NAME')

# Connect to MongoDB with CA Bundle
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[os.getenv('ENV_MONGO_DB_NAME')]

groups_collection = db['groups']

# Define the keyboard layout
keyboard_layout = [
    ["Help"]
]

# Handler for the /start command
async def start(update: Update, context: CallbackContext):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        bot_username = context.bot.username
        reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            f"Hello! I'm @{bot_username}. Choose an option below:",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error displaying commands list: {e}")
        await update.message.reply_text("Sorry, there was an error. Try again later.")

# Handler for the /help command
async def help_command(update: Update, context: CallbackContext):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        help_text = """
Available commands:
/sol-amt - Enter the SOL amount
/start - Start a new session
/help - Show this help message
"""
        await update.message.reply_text(help_text)
    except Exception as e:
        print(f"Error displaying help message: {e}")
        await update.message.reply_text("Sorry, there was an error. Try again later.")

# Handler for the /commands command
async def commands(update: Update, context: CallbackContext):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        commands_keyboard = [
            ["Enter SOL Amount"],
            ["Start"],
            ["Show Help"]
        ]
        reply_markup = ReplyKeyboardMarkup(commands_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Choose a command:", reply_markup=reply_markup)
    except Exception as e:
        print(f"Error displaying commands keyboard: {e}")
        await update.message.reply_text("Sorry, there was an error. Try again later.")

# Handler for the /magic command
async def magic(update: Update, context: CallbackContext):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        if not update.message:
            return await update.message.reply_text("There was an error processing your command. Please try again later.")

        chat_member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
        if chat_member.status not in ['creator', 'administrator']:
            return await update.message.reply_text("Sorry, only administrators and the group owner can use this command.")

        args = context.args
        if not args:
            return await update.message.reply_text("Please provide an SPL address.")

        spl_address = ' '.join(args)

        groups_collection.insert_one({
            'chatId': update.message.chat_id,
            'chatUserId': update.message.from_user.id,
            'chatName': update.message.chat.title,
            'chatType': update.message.chat.type,
            'splAddress': spl_address,
            'timestamp': str(update.message.date.timestamp())
        })

        blink_url = f"https://blinktochat.fun/api/actions/start/{update.message.chat_id}/{spl_address}"
        await update.message.reply_text(blink_url)

        dialect_url = f"https://dial.to/devnet?action=solana-action:{blink_url}"
        await update.message.reply_text(dialect_url)

    except Exception as e:
        print(f"Error processing /magic command: {e}")
        await update.message.reply_text("Sorry, there was an error processing your command. Please try again later.")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CommandHandler("magic", magic))

    application.run_polling()

if __name__ == '__main__':
    main()
