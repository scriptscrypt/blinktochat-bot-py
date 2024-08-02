import os
import certifi
import urllib3
urllib3.disable_warnings()
from telegram import Update, ReplyKeyboardMarkup, Chat, BotCommand, ChatPermissions, ChatMember
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, JobQueue, ChatMemberHandler
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
from helpers.xTimeago import utilXtimeAgo
from telegram.constants import ParseMode
from telegram.error import BadRequest
import requests
from helpers.utilUrlHelper import utilUrlEncode

# Load environment variables
load_dotenv()

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv('ENV_TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('ENV_MONGO_URI')
db_name = os.getenv('ENV_MONGO_DB_NAME')
if db_name is None:
    raise ValueError("ENV_MONGO_DB_NAME is not set in environment variables")
# Connect to MongoDB with CA Bundle
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[os.getenv('ENV_MONGO_DB_NAME')]
groups_collection = db['groups']
users_collection = db['users']


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
# but you can infer this based on the presence of an invite link or username. 
# If a group is private, it won't have a username.
# Define a function to fetch NFT collections for a wallet address

# Define a function to fetch NFT collections for a wallet address
async def fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

        # Check if the user provided a wallet address
        args = context.args
        if not args:
            await update.message.reply_text("Please provide a wallet address. Example: /fetch <walletAddress>")
            return

        wallet_address = ' '.join(args)
        
        # Define the API endpoint and your API key
        api_key = os.getenv('ENV_HELIUS_API_KEY')  # Make sure to add your Helius API key to the environment variables
        url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
        
        # Define the payload for the POST request
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getAssetsByOwner",
            "params": {
                "ownerAddress": wallet_address,
                "page": 1,
                "limit": 1000
            }
        }
        
        # Make the API call
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        response_data = response.json()
        
        # Check for errors in the response
        if 'error' in response_data:
            await update.message.reply_text(f"Error fetching data: {response_data['error']['message']}")
            return
        
        # Extract the list of NFTs
        items = response_data.get('result', {}).get('items', [])
        if not items:
            await update.message.reply_text(f"No NFT collections found for wallet address: {wallet_address}")
        else:
            # Split long responses into multiple messages
            collections_list = ""
            for item in items:
                # Extracting data
                name = item.get('content', {}).get('metadata', {}).get('name', 'Unnamed NFT')
                description = item.get('content', {}).get('metadata', {}).get('description', 'No description available')
                image_url = item.get('content', {}).get('links', {}).get('image', 'No image URL available')
                group_value = next((group['group_value'] for group in item.get('grouping', []) if group.get('group_key') == 'collection'), None)

                # Filter out items without a collection address (group_value)
                if not group_value:
                    continue

                # Format the output for each NFT
                nft_info = (
                    f"Name: {name}\n"
                    f"Collection Address: {group_value}\n\n"
                )

                # Check if the current message exceeds the limit
                if len(collections_list) + len(nft_info) > 4000:
                    await update.message.reply_text(collections_list)
                    collections_list = ""

                collections_list += nft_info
            
            # Send the last accumulated message
            if collections_list:
                await update.message.reply_text(collections_list)
    except Exception as e:
        logging.error(f"Error processing /fetch command: {e}")
        await update.message.reply_text("Sorry, there was an error fetching NFT collections. Please try again later.")

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
            return await update.message.reply_text("Please provide a collection address.")

        collectionAddress = ' '.join(args)

        groups_collection.insert_one({
            'keyChatId': update.effective_chat.id,
            'keyChatUserId': update.message.from_user.id,
            'keyChatName': update.effective_chat.title,
            'keyChatType': update.effective_chat.type,
            'keyCollectionAddress': collectionAddress,
            'keyGatingType': 'NFTCollection',
            'keyTimestamp': str(update.message.date.timestamp())
        })

        blink_url = f"https://blinktochat.fun/{update.effective_chat.id}/{collectionAddress}"
        chat_title = update.effective_chat.title
        
        # Construct the tweet text with the additional line
        tweet_text = f"Join this exclusive {chat_title} chat - Blinktochat\n"
        # Encode the text to ensure spaces and special characters are correctly handled
        encoded_text = utilUrlEncode(tweet_text)
        # Construct the full URL for the Twitter intent
        tweetIntentWeb = f"https://twitter.com/intent/tweet?url={blink_url}&text={encoded_text}"
        # await update.message.reply_text(blink_url)
        await update.message.reply_text("Click here to Share directly on X: \n" + tweetIntentWeb + "\n\n" +"Blink URL: \n" + blink_url)

        # dialect_url = f"https://dial.to/devnet?action=solana-action:{blink_url}"
        # await update.message.reply_text(dialect_url)

    except Exception as e:
        logging.error(f"Error processing /magic command: {e}")
        await update.message.reply_text("Sorry, there was an error processing your command. Please try again later.")
        
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Check if the command is used in a private chat (DM)
        if update.effective_chat.type != Chat.PRIVATE:
            return await update.message.reply_text("This command can only be used in private messages with the bot.")

        # Get arguments provided with the command
        args = context.args
        collection_address = ' '.join(args) if args else None

        if collection_address:
            # Fetch data for the specific collection address
            groups = list(groups_collection.find({'keyCollectionAddress': collection_address}))

            if not groups:
                return await update.message.reply_text(f"No groups found gated with collection address: {collection_address}")

            stats_message = f"Groups gated with collection address {collection_address}:\n\n"
            for group in groups:
                stats_message += f"Chat Name: {group.get('keyChatName', 'Unknown')}\n"
                stats_message += f"Gating Type: {group.get('keyGatingType', 'Unknown')}\n"
                timestamp = group.get('keyTimestamp', 'Unknown')
                stats_message += f"Created: {utilXtimeAgo(timestamp) if timestamp != 'Unknown' else 'Unknown'}\n\n"
                stats_message += "-------------------\n\n"

        else:
            # Fetch all groups
            groups = list(groups_collection.find({}, {'keyChatName': 1, 'keyCollectionAddress': 1}))

            if not groups:
                return await update.message.reply_text("No gated groups found.")

            stats_message = "All gated groups:\n\n"
            for group in groups:
                stats_message += f"Group: {group['keyChatName']}\n"
                stats_message += f"Collection Address: {group['keyCollectionAddress']}\n\n"
                timestamp = group.get('keyTimestamp', 'Unknown')
                stats_message += f"Created: {utilXtimeAgo(timestamp) if timestamp != 'Unknown' else 'Unknown'}\n\n"
                stats_message += "-------------------\n\n"

        # Split long messages if necessary
        if len(stats_message) > 4096:
            for i in range(0, len(stats_message), 4096):
                await update.message.reply_text(stats_message[i:i+4096])
        else:
            await update.message.reply_text(stats_message)

    except Exception as e:
        logging.error(f"Error processing /stats command: {e}")
        await update.message.reply_text("Sorry, there was an error fetching the statistics. Please try again later.")

async def handle_member_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract the new member status change event
    chat_member_update = update.chat_member
    new_member = chat_member_update.new_chat_member.user

    if chat_member_update.new_chat_member.status in [ChatMember.MEMBER, ChatMember.RESTRICTED]:
        # Get the username and user ID
        username = new_member.username
        user_id = new_member.id

        # Update the hasJoined status and telegramIdIp in the users_collection
        users_collection = db['users']  # Assuming you have a users collection

        # Define the update fields
        update_fields = {
            'keyHasJoined': True,
            'keyTelegramId': user_id
        }

        # Check if the user has a username
        if username:
            user_record = users_collection.find_one({'keyUsername': username})
        else:
            user_record = users_collection.find_one({'keyTelegramId': user_id})

        if user_record:
            # Update the user's hasJoined status and telegramIdIp if the record is found
            users_collection.update_one(
                {'_id': user_record['_id']},
                {'$set': update_fields}
            )
            logging.info(f"User {username or user_id} marked as joined in the database.")
        else:
            logging.info(f"User {username or user_id} joined but not found in the database.")
    else:
        # Handle other cases, like when members leave or change status
        logging.info("Chat member status change event received, not a join.")
async def validate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

        # Ensure the command is used in a group chat and by an admin
        chat = update.effective_chat
        chat_member = await context.bot.get_chat_member(chat.id, update.message.from_user.id)

        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            await update.message.reply_text("This command can only be used in group chats.")
            return

        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("Only administrators can use this command.")
            return

        # Query the database for users with hasTransacted set to false
        non_transacted_users = users_collection.find({'keyTgChatId': chat.id, 'keyHasTransacted': False})

        # Check if there are any non-transacted users
        if non_transacted_users.count() == 0:
            await update.message.reply_text("All members have transacted. No removals needed.")
            return

        # Process each user who hasn't transacted
        removed_users = []
        for user in non_transacted_users:
            user_id = user['keyTelegramId']
            try:
                await context.bot.ban_chat_member(chat.id, user_id)
                removed_users.append(user_id)
            except BadRequest as e:
                logging.error(f"Error removing user {user_id}: {e}")

        # Provide feedback on the action taken
        if removed_users:
            await update.message.reply_text(f"Removed {len(removed_users)} user(s) who have not transacted.")
            await update.message.reply_text(f"Users removed: {removed_users}")
        else:
            await update.message.reply_text("No users were removed. Some may already have left or cannot be removed.")

    except Exception as e:
        logging.error(f"Error processing /validate command: {e}")
        await update.message.reply_text("Sorry, there was an error processing the validation. Please try again later.")
     
async def set_commands(context: ContextTypes.DEFAULT_TYPE):
    commands = [
        BotCommand("start", "Start the bot and see the options"),
        BotCommand("magic", "Use /magic <collection address> to gate with NFT collection"),
        BotCommand("fetch", "Use /fetch <walAddress> to fetch NFT collections for a wallet address"),
        BotCommand("stats", "Get statistics about registered groups (only works in DM)"),
        BotCommand("validate", "Validate members who have not transacted"),
        
]
    await context.bot.set_my_commands(commands)

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
    application.add_handler(CommandHandler("fetch", fetch))
    application.add_handler(CommandHandler("stats", stats))  # Add this line
    application.add_handler(CommandHandler("validate", validate))

    application.add_handler(MessageHandler(filters.Regex('Make the group private'), make_group_private))
    
     # Add ChatMemberHandler for handling member status changes
    member_handler = ChatMemberHandler(handle_member_join, ChatMemberHandler.MY_CHAT_MEMBER)
    application.add_handler(member_handler)

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()