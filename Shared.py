'''
Created on Sep 26, 2020

@author: willg
'''
import aiohttp
import discord
from pathlib import Path
counter_file = "stats_counter.pkl"
total_stats_file = "total_stats.pkl"
blacklisted_users_file = "blacklisted_users.pkl"
backup_file_list = [counter_file, total_stats_file, 'rts.pkl', 'cts.pkl']
backup_folder = "backups/"
import shutil
from datetime import datetime
import os
import dill as p
from collections import defaultdict

prefix = "!"


blacklistedUsers = None
bot_abuse_tracking = defaultdict(int)
blacklisted_command_count = defaultdict(int)
BOT_ABUSE_REPORT_CHANNEL_ID = 766272946091851776
SPAM_THRESHOLD = 10
WARN_THRESHOLD = 10
AUTO_BAN_THRESHOLD = 15
CAN_BLACKLIST_IDS = [706120725882470460]

def has_prefix(message:str, prefix:str=prefix):
    message = message.strip()
    return message.startswith(prefix)

def strip_prefix(message:str, prefix:str=prefix):
    message = message.strip()
    if message.startswith(prefix):
        return message[len(prefix):]
    
def is_in(message:str, valid_terms:set, prefix:str=prefix):
    if (has_prefix(message, prefix)):
        message = strip_prefix(message, prefix).strip()
        args = message.split()
        if len(args) == 0:
            return False
        return args[0].lower().strip() in valid_terms
            
    return False    

def strip_prefix_and_command(message:str, valid_terms:set, prefix:str=prefix):
    message = strip_prefix(message, prefix)
    args = message.split()
    if len(args) == 0:
        return message
    if args[0].lower().strip() in valid_terms:
        message = message[len(args[0].lower().strip()):]
    return message.strip()


async def blacklist(message:discord.Message):
    args = message.content.split()
    if len(args) < 2:
        await safe_send(message.channel, "Provide an ID to blacklist.")
    elif not args[1].isnumeric():
        await safe_send(message.channel, "The ID to blacklist must be a number.")
    else:
        reason = "No reason specified."
        if len(args) > 2:
            reason = " ".join(args[2:])
        blacklist_id = int(args[1])
        blacklistedUsers[blacklist_id] = reason
        await safe_send(message.channel, "Blacklisted " + str(blacklist_id))
        
async def remove_blacklist(message:discord.Message):
    args = message.content.split()
    if len(args) < 1:
        await safe_send(message.channel, "Provide an ID to remove the blacklist for.")
    elif not args[1].isnumeric():
        await safe_send(message.channel, "The ID to blacklist must be a number.")
    else:
        blacklist_id = int(args[1])
        if blacklist_id not in blacklistedUsers:
            await safe_send(message.channel, str(blacklist_id) + " is not blacklisted")
        else:
            del blacklistedUsers[blacklist_id]
            await safe_send(message.channel, "Removed blacklist for " + str(blacklist_id))
        if blacklist_id in blacklisted_command_count:
            del blacklisted_command_count[blacklist_id]
async def send_blacklist(message:discord.Message):
    blacklist_str = "No users blacklisted"
    if blacklistedUsers != None and len(blacklistedUsers) > 0:
        blacklist_str = ""
        for user_id, reason in blacklistedUsers.items():
            blacklist_str += "Discord ID: " + str(user_id) + " - Reason: " + reason + "\n\n"
    await safe_send(message.channel, blacklist_str)
    
async def process_blacklist(client, message:discord.Message):
    global blacklisted_command_count
    author_id = message.author.id
    is_blacklisted = author_id in blacklistedUsers
    if is_blacklisted:
        if blacklisted_command_count[message.author.id] % 30 == 0:
            await safe_send(message.channel, "You have been blacklisted and are not allowed to use this bot. Reason: " + blacklistedUsers[message.author.id])
            blacklisted_command_count[message.author.id] += 1
    else:
        bot_abuse_tracking[author_id] += 1
        if bot_abuse_tracking[author_id] == WARN_THRESHOLD:
            await safe_send(message.channel, message.author.mention + " slow down - you're abusing the bot. Wait 5 minutes or you risk getting banned.")
        elif bot_abuse_tracking[author_id] == AUTO_BAN_THRESHOLD: #certain spam
            is_blacklisted = True
            blacklistedUsers[author_id] = "Automated ban - you spammed the bot. This hurts users everywhere because it slows down the bot for everyone. You can appeal 1 week after you were banned. (If you think this is an error, you can send proof to Bad Wolf.)"
            await client.get_channel(BOT_ABUSE_REPORT_CHANNEL_ID).send("Automatic ban for spamming bot:\nDiscord: " + str(message.author) + "\nDiscord ID: " + str(author_id) + "\nDisplay name: " + message.author.display_name  + "\nLast message: " + message.content)
    return is_blacklisted

async def abuseCheck(client):
    global bot_abuse_tracking
    abuserIDs = set()
    
    for user_id, message_count in bot_abuse_tracking.items():
        if message_count > SPAM_THRESHOLD:
            if user_id not in blacklistedUsers:
                abuserIDs.add(str(user_id))
    bot_abuse_tracking.clear()
    
    
    if len(abuserIDs) > 0:
        await client.get_channel(BOT_ABUSE_REPORT_CHANNEL_ID).send("Check logs, the following IDs might be abusing the bot: " + ", ".join(abuserIDs))
        

async def send_missing_permissions(channel:discord.TextChannel, content=None, delete_after=7):
    try:
        return await channel.send("I'm missing permissions. Contact your admins. The bot needs the following permissions:\n- Send Messages\n- Embed Links\n- Add Reactions (for pages)\n- Manage Messages (to remove reactions)", delete_after=delete_after)
    except discord.errors.Forbidden: #We can't send messages
        pass
    

#Won't throw exceptions if we're missing permissions, it's "safe"
async def safe_send(channel:discord.TextChannel, content=None, embed=None, delete_after=None):
    try:
        return await channel.send(content=content, embed=embed, delete_after=delete_after)
    except discord.errors.Forbidden: #Missing permissions
        try:
            return await channel.send("I'm missing permissions. Contact your admins. The bot needs the following permissions:\n- Send Messages\n- Embed Links\n- Add Reactions (for pages)\n- Manage Messages (to remove reactions)")
        except discord.errors.Forbidden: #We can't send messages
            pass
    


#============== Synchronous HTTPS Functions ==============
async def fetch(url, headers=None):
    async with aiohttp.ClientSession() as session:
        if headers == None:
            async with session.get(url) as response:
                return await response.json()
        else:
            async with session.get(url, headers=headers) as response:
                return await response.json()
            
#================= File stuff ============================
def backup_files(to_back_up=backup_file_list):
    Path(backup_folder).mkdir(parents=True, exist_ok=True)
    todays_backup_path = backup_folder + str(datetime.date(datetime.now())) + "/"
    Path(todays_backup_path).mkdir(parents=True, exist_ok=True)
    for file_name in to_back_up:
        try:
            if not os.path.exists(file_name):
                continue
            temp_file_n = file_name
            if os.path.exists(todays_backup_path + temp_file_n):
                for i in range(50):
                    temp_file_n = file_name + "_" + str(i) 
                    if not os.path.exists(todays_backup_path + temp_file_n):
                        break
            shutil.copy2(file_name, todays_backup_path + temp_file_n)
        except Exception as e:
            print(e)

def load_blacklisted_users():
    global blacklistedUsers
    if blacklistedUsers == None:
        if os.path.exists(blacklisted_users_file):
            with open(blacklisted_users_file, "rb") as pickle_in:
                try:
                    blacklistedUsers = p.load(pickle_in)
                except:
                    print("Could not read in the pickle for blacklisted users file. Using default.")
                    blacklistedUsers = {}
        else:
            print("No blacklisted users file pkl found. Using default.")
            blacklistedUsers = {}
            
def can_blacklist(author:discord.Member):
    return author.id in CAN_BLACKLIST_IDS

def pickle_blacklisted_users():
    with open(blacklisted_users_file, "wb") as pickle_out:
        try:
            p.dump(blacklistedUsers, pickle_out)
        except:
            print("Could not dump pickle for blacklisted users. Current blacklisted users: ", blacklistedUsers)
    
def log_text(text, file_name="messages_logging.txt"):
    if not os.path.isfile(file_name):
        f = open(file_name, "w")
        f.close()
    with open(file_name, "a+") as f:
        f.write("\n")
        f.write(str(datetime.now()))
        f.write(": ")
        try:
            f.write(text)
        except:
            pass
        
def log_message(message:discord.Message):
    log_text("Server name: " + str(message.guild) +\
             " - Server ID: " + str("DMs" if message.guild == None else message.guild.id) +\
             " - Channel name: " + str(message.channel) +\
             " - Channel ID: " + str(message.channel.id) +\
             " - User name: " + str(message.author) +\
             " - User discord: " + str(message.author.display_name) +\
             " - Discord ID: " + str(message.author.id) +\
             " - Command: " + message.content)
