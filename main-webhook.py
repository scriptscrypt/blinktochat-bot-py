import os
import certifi
import urllib3
urllib3.disable_warnings()
from telegram import Update, ReplyKeyboardMarkup, Chat, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
from flask import Flask, request

# Load environment variables
load_dotenv()

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv('ENV_TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('ENV_MONGO_URI')
db_name = os.getenv('ENV_MONGO_DB_NAME')
WEBHOOK_URL = os.getenv('ENV_WEBHOOK_URL')  # Add this to your .env file
if db_name is None:
    raise ValueError("ENV_MONGO_DB_NAME is not set in environment variables")

# Connect to MongoDB with CA Bundle
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[os.getenv('ENV_MONGO_DB_NAME')]
groups_collection = db['groups']

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

keyboard_layout = [['Make the group private'], ['/magic <walAddress>']]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

        chat = update.effective_chat

        # Check if the chat is a group
        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            await update.message.reply_text("This bot can only be used in group chats.")
            return

        bot_username = context.bot.username
        reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            f"Hello! I'm @{bot_username}. Follow the steps below:\n\n"
            "1. Make the group private (select the option below and follow instructions)\n"
            "2. Use /magic <walAddress> to proceed",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error displaying commands list: {e}")
        await update.message.reply_text("Sorry, there was an error. Try again later.")

async def make_group_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "To make the group private, follow these steps:\n\n"
        "1. Open the group chat.\n"
        "2. Tap on the group name to open the group info.\n"
        "3. Tap on 'Edit' (or the pencil icon) to edit the group settings.\n"
        "4. Tap on 'Group Type' and select 'Private Group'.\n"
        "5. Save the changes.\n\n"
        "After making the group private, you can proceed with the /magic command."
    )


# # Set up logging
# logging.basicConfig(level=logging.INFO)

# Telegram does not directly provide a property to distinguish private groups from public groups,
# but we can infer this based on the presence of an invite link or username. 
# If a group is private, it won't have a username.

async def magic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Check if the update contains a message
        if not update.message:
            return await update.message.reply_text("There was an error processing your command. Please try again later.")

        # Check if the group is private
        if update.effective_chat.username:
            return await update.message.reply_text("This command can only be used in private groups. use /start to know more")

        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.message.from_user.id)
        if chat_member.status not in ['creator', 'administrator']:
            return await update.message.reply_text("Sorry, only administrators and the group owner can use this command.")

        # Get arguments provided with the command
        args = context.args
        if not args:
            return await update.message.reply_text("Please provide an SPL address.")

        spl_address = ' '.join(args)

        # Assuming groups_collection is already initialized and connected
        groups_collection.insert_one({
            'chatId': update.effective_chat.id,
            'chatUserId': update.message.from_user.id,
            'chatName': update.effective_chat.title,
            'chatType': update.effective_chat.type,
            'splAddress': spl_address,
            'timestamp': str(update.message.date.timestamp())
        })

        blink_url = f"https://blinktochat.fun/api/actions/start/{update.effective_chat.id}/{spl_address}"
        await update.message.reply_text(blink_url)

        dialect_url = f"https://dial.to/devnet?action=solana-action:{blink_url}"
        await update.message.reply_text(dialect_url)

    except Exception as e:
        logging.error(f"Error processing /magic command: {e}")
        await update.message.reply_text("Sorry, there was an error processing your command. Please try again later.")
        
async def set_commands(context: ContextTypes.DEFAULT_TYPE):
    commands = [
        BotCommand("start", "Start the bot and see the options"),
        BotCommand("magic", "Use /magic <walAddress> to proceed")
    ]
    await context.bot.set_my_commands(commands)

# Initialize Flask app
app = Flask(__name__)

# Initialize bot application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("magic", magic))
application.add_handler(MessageHandler(filters.Regex('Make the group private'), make_group_private))

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.process_update(update)
    return 'OK'

async def setup_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)
    await set_commands(ContextTypes.DEFAULT_TYPE(application))

def main():
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Create a JobQueue and set it up in the application
    job_queue = application.job_queue

    # Schedule the set_commands function to run every hour to ensure commands are set
    job_queue.run_repeating(set_commands, interval=3600, first=0)

    # Add handlers - if not the commands doesn't start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("magic", magic))
    application.add_handler(MessageHandler(filters.Regex('Make the group private'), make_group_private))

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    from asyncio import get_event_loop
    loop = get_event_loop()
    loop.run_until_complete(setup_webhook())
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))