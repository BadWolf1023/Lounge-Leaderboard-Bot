'''
Created on Sep 14, 2020

@author: willg
'''

import discord
from discord.ext import tasks

import Shared
import sys
import atexit
import signal
import Leaderboard
from collections import defaultdict

testing_server = False
bot_key = None
testing_bot_key = None

private_info_file = "private.txt"
switch_status = True
finished_on_ready = False

leaderboard_instances = defaultdict(lambda: defaultdict(Leaderboard.Leaderboard))
client = discord.Client(intents=discord.Intents.all())


@client.event
async def on_message(message: discord.Message):
    server_id = "DMs"
    if message.guild != None: #Not a DM
        server_id = message.guild.id
    
    #ignore your own messages
    if message.author == client.user:
        return
    #ignore bots
    if message.author.bot:
        return
    
    message_str = message.content.strip()

    if message_str == "" or (message_str[0] != Shared.prefix and client.user not in message.mentions):
        return
    
    channel_id = message.channel.id
    
    
    
    leaderboard_instance = leaderboard_instances[server_id][channel_id]
    await leaderboard_instance.process_leaderboard_command(client, message)
        

@tasks.loop(hours=Shared.hours_between_pulls)
async def leaderboard_pull():
    await Leaderboard.pull_data()
    
@tasks.loop(seconds=60)
async def checkBotAbuse():
    await Shared.abuseCheck(client)
    
@tasks.loop(seconds=30)
async def updatePresence():
    global switch_status
    game_str = ""
    if switch_status:
        game_str = "!leaderboard for Lounge leaderboards"
    else:
        game_str = "Mention me to see stats"
    
    switch_status = not switch_status
    
    game = discord.Game(game_str)
    await client.change_presence(status=discord.Status.online, activity=game)

    
#This function will run every 30 min. It will remove any table bots that are
#inactive, as defined by TableBot.isinactive() (currently 2.5 hours)
@tasks.loop(minutes=15)
async def removeInactiveInstances():
    to_remove = []
    for server_id in leaderboard_instances:
        for channel_id in leaderboard_instances[server_id]:
            if leaderboard_instances[server_id][channel_id].isInactive(): #if the table bot is inactive, delete it
                to_remove.append((server_id, channel_id))
                
    for (serv_id, chan_id) in to_remove:
        del(leaderboard_instances[serv_id][chan_id])

@tasks.loop(hours=24)
async def backup():
    Shared.backup_files(Shared.backup_file_list)
    Leaderboard.pickle_stats()
    Leaderboard.pickle_player_countries()
    Shared.pickle_blacklisted_users()

def private_data_init():
    global testing_bot_key
    global bot_key
    with open(private_info_file, "r") as f:
        testing_bot_key = f.readline().strip("\n")
        bot_key = f.readline().strip("\n")


    


@client.event
async def on_ready():
    global finished_on_ready
    if not finished_on_ready:
        Leaderboard.load_player_pickle_data()
        Leaderboard.load_player_country_mapping()
        Leaderboard.load_stats_in()
        Shared.load_blacklisted_users()
        #Leaderboard.dump_data_to_csv() #Uncomment to dump the pulled data to a csv
        
        leaderboard_pull.start()
        removeInactiveInstances.start()
        updatePresence.start()
        checkBotAbuse.start()
        backup.start()
        
        print("Finished on ready.")
        finished_on_ready = True
    
    

def on_exit():
    Shared.backup_files()
    Leaderboard.pickle_stats()
    Leaderboard.pickle_player_countries()
    Shared.pickle_blacklisted_users()
    
    print("Exiting...")
        
def handler(signum, frame):
    sys.exit()

signal.signal(signal.SIGINT, handler)

atexit.register(on_exit)

private_data_init()

if testing_server == True:
    client.run(testing_bot_key)
else:
    client.run(bot_key)
