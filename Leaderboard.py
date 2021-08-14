'''
Created on Nov 5, 2020

@author: willg
'''
from builtins import isinstance

'''
Created on Sep 28, 2020

@author: willg
'''
import discord
import Shared
from datetime import datetime, timedelta
import asyncio
from typing import List
import dill as p
import os

medium_delete = 10
long_delete = 30

lounge_player_data_rt = None
lounge_player_data_ct = None
global_cached = {}

rt_specific_url = "https://mariokartboards.com/lounge/api/ladderplayer.php?ladder_id=1&all=1"
ct_specific_url = "https://mariokartboards.com/lounge/api/ladderplayer.php?ladder_id=2&all=1"

currently_pulling = True
interval_time = 1 #wait this many seconds between each ping to mkboards.com
extra_wait_time = 20
chunk_size = 25
time_between_pulls = timedelta(hours=4)
rt_last_updated = None
ct_last_updated = None
rt_progress = 0.0
ct_progress = 0.0


date_filter_time = timedelta(days=14)
TOP_N_RESULTS = 50

LEADERBOARD_WAIT_TIME = timedelta(seconds=20)
STATS_WAIT_TIME = timedelta(seconds=10)
inactivity_time_period = timedelta(minutes=30)


embed_page_time = timedelta(minutes=1)

LEFT_ARROW_EMOTE = '\u25c0'
RIGHT_ARROW_EMOTE = '\u25b6'

#We're not using these
FULL_LEFT_ARROW_EMOTE = '\u23ee'
FULL_RIGHT_ARROW_EMOTE = '\u23ed'

#await client.add_reaction(message,'\u25b6')'

player_id_json_name = 'player_id'


leaderboard_terms = {"leader", "leaderboard", "ldr", "board"}
leaderboard_type_terms = {'rt', 'ct'}
blacklist_user_terms = {"blacklistuser", "banuser", "ban"}
remove_blacklist_user_terms = {"unban", "unbanuser", "removeban", "unblacklist", "unblacklistuser", "removeblacklist", "blacklistuserremove"}
check_blacklist_terms = {"blacklist", "check", "checkblacklist", "displayblacklist", "banlist"}
inrole_terms = {'inrole'}
"""
{
   "player_id":"260",
   "player_name":"Az",
   "player_country_flag":"jp",
   "base_mmr":"11117",
   "base_lr":"4605",
   "strikes":"0",
   "current_mmr":"11429",
   "current_lr":"9067",
   "peak_mmr":"11709",
   "peak_lr":"9067",
   "lowest_mmr":"10561",
   "lowest_lr":"4605",
   "wins":"25",
   "loss":"7",
   "max_gain_mmr":"266",
   "max_gain_lr":"282",
   "max_loss_mmr":"-457",
   "max_loss_lr":"-150",
   "win_percentage":"0.78125",
   "gainloss10_mmr":"868",
   "gainloss10_lr":"1830",
   "wins10":"9",
   "loss10":"1",
   "win10_percentage":"0.9",
   "win_streak":"3",
   "top_score":"124",
   "average_score":"97.5938",
   "average10_score":"104.9",
   "std_score":"14.8216",
   "std10_score":"9.25689",
   "total_events":"32",
   "penalties":"0",
   "max_strikes":"5",
   "ranking":"1",
   "percentile":"99.8733",
   "previous_ranking":"1",
   "previous_percentile":"99.8731",
   "last_event_date":"2021-08-14 01:00:34",
   "total_events_since_date":"32",
   "since_date":null,
   "update_date":"2021-08-14 01:00:34",
   "current_division":"Ruby",
   "current_class":"Class X",
   "url":"https:\/\/mariokartboards.com\/lounge\/ladder\/player.php?player_id=260&ladder_id=1",
   "current_emblem":"https:\/\/mariokartboards.com\/lounge\/images\/emblems\/ruby.png"
}
"""
#key is command arg, tuple is:
#field name in the JSON, embed name, time filter, and reversed, minimum events needed
stat_terms = {'avg10':('average10_score', "Current Average (Last 10)", True, True, 5),
              'topscore':('top_score', 'Top Score', False, True, -1),
              'mmr':('current_mmr', "Current MMR", False, True, 5),
              'mmrgain10':('gainloss10_mmr', "Current MMR Gained (Last 10)", True, True, -1),
              'mmrloss10':('gainloss10_mmr', "Current MMR Lost (Last 10)", True, False, -1),
              'pens':('penalties', "Most Penalties", False, False, -1),
              'peakmmr':('peak_mmr', "Peak MMR", False, True, 5),
              'wins':('wins', "Most Wins", False, True, -1),
              'losses':('loss', "Most Losses", False, True, -1),
              'maxgain':('max_gain_mmr', "Largest MMR Gain", False, True, -1),
              'maxloss':('max_loss_mmr', "Largest MMR Loss", False, False, -1),
              'winpercentage':('win_percentage', "Win Percentage", True, True, 10),
              'wins10':('wins10', "Current Wins (Last 10)", True, True, -1),
              'losses10':('loss10', "Current Losses (Last 10)", True, True, -1),
              'winstreak':('win_streak', "Current Win Streak", True, True, -1),
              'avg':('average_score', "Current Average", False, True, 10),
              'events':('total_wars', "Events Played", False, True, -1)
              }
mult_100_fields = {"win_percentage"}


stats_count = None
total_stats = None

    
            
#Pickling
def load_stats_in():
    global stats_count
    global total_stats
    if stats_count == None:
        if os.path.exists(Shared.counter_file):
            with open(Shared.counter_file, "rb") as pickle_in:
                try:
                    stats_count = p.load(pickle_in)
                except:
                    print("Could not read in the pickle for stats count. Using default.")
                    stats_count = [0,0]
        else:
            print("No stats count pkl found. Using default.")
            stats_count = [0,0]
    
    if total_stats == None:
        if os.path.exists(Shared.total_stats_file):
            with open(Shared.total_stats_file, "rb") as pickle_in:
                try:
                    total_stats = p.load(pickle_in)
                except:
                    print("Could not read in the pickle for total stats file. Using default.")
                    total_stats = {}
                    for type_key in leaderboard_type_terms:
                        total_stats[type_key] = {}
                        for key in stat_terms:
                            total_stats[type_key][key] = 0
        else:
            print("No stats file pkl found. Using default.")
            total_stats = {}
            for type_key in leaderboard_type_terms:
                total_stats[type_key] = {}
                for key in stat_terms:
                    total_stats[type_key][key] = 0
   
def pickle_stats():
    with open(Shared.total_stats_file, "wb") as pickle_out:
        try:
            p.dump(total_stats, pickle_out)
        except:
            print("Could not dump total stats. Current dict:", total_stats)         
    with open(Shared.counter_file, "wb") as pickle_out:
        try:
            p.dump(stats_count, pickle_out)
        except:
            print("Could not dump stats_counter. Current dict:", stats_count)         
    
    
def pickle_player_data():
    if lounge_player_data_rt != None and len(lounge_player_data_rt) > 0:
        with open("rts.pkl", "wb") as pickle_out:
            try:
                p.dump(lounge_player_data_rt, pickle_out)
            except:
                print("Could not dump pickle for rts.pkl.")
    if lounge_player_data_ct != None and len(lounge_player_data_ct) > 0:
        with open("cts.pkl", "wb") as pickle_out:
            try:
                p.dump(lounge_player_data_ct, pickle_out)
            except:
                print("Could not dump pickle for cts.pkl.")
                
                
def load_player_pickle_data():
    global lounge_player_data_ct
    global ct_last_updated
    global lounge_player_data_rt
    global rt_last_updated
    
    if lounge_player_data_rt == None:
        if os.path.exists('rts.pkl'):
            with open('rts.pkl', "rb") as pickle_in:
                try:
                    lounge_player_data_rt = p.load(pickle_in)
                except:
                    print("Could not read lounge player rts in.")
                    lounge_player_data_rt = {}
                rt_last_updated = datetime.now()
    if lounge_player_data_ct == None:
        if os.path.exists('cts.pkl'):
            with open('cts.pkl', "rb") as pickle_in:
                try:
                    lounge_player_data_ct = p.load(pickle_in)
                except:
                    print("Could not read lounge player cts in.")
                    lounge_player_data_ct = {}
                ct_last_updated = datetime.now()
            


def isfloat(value:str):
    try:
        float(value)
        return True
    except ValueError:
        return False
    
def isint(value:str):
    try:
        int(value)
        return True
    except ValueError:
        return False

def detailed_players_is_corrupt(json_data, caller_checks_null=True):
    if not isinstance(json_data, list):
        return True
    #update_date":"2020-11-02 23:41:22"
    for player in json_data:
        
        if not isinstance(player, dict):
            return True
        
        #We'll allow this, 
        if caller_checks_null:
            if 'name' in player and player['name'] is None:
                continue
            
        
         
        if player_id_json_name in player and isinstance(player[player_id_json_name], str) and isint(player[player_id_json_name])\
        and 'name' in player and isinstance(player['name'], str) \
        and 'strikes' in player and isinstance(player['strikes'], str) and isint(player['strikes'])\
        and 'current_mmr' in player and isinstance(player['current_mmr'], str) and isint(player['current_mmr'])\
        and 'peak_mmr' in player and isinstance(player['peak_mmr'], str) and isint(player['peak_mmr'])\
        and 'lowest_mmr' in player and isinstance(player['lowest_mmr'], str) and isint(player['lowest_mmr'])\
        and 'wins' in player and isinstance(player['wins'], str) and isint(player['wins'])\
        and 'loss' in player and isinstance(player['loss'], str) and isint(player['loss'])\
        and 'max_gain_mmr' in player and isinstance(player['max_gain_mmr'], str) and isint(player['max_gain_mmr'])\
        and 'max_loss_mmr' in player and isinstance(player['max_loss_mmr'], str) and isint(player['max_loss_mmr'])\
        and 'win_percentage' in player and isinstance(player['win_percentage'], str) and isfloat(player['win_percentage']) \
        and 'gainloss10_mmr' in player and isinstance(player['gainloss10_mmr'], str) and isint(player['gainloss10_mmr'])\
        and 'wins10' in player and isinstance(player['wins10'], str) and isint(player['wins10'])\
        and 'loss10' in player and isinstance(player['loss10'], str) and isint(player['loss10'])\
        and 'win10_percentage' in player and isinstance(player['win10_percentage'], str) and isfloat(player['win10_percentage'])\
        and 'win_streak' in player and isinstance(player['win_streak'], str) and isint(player['win_streak'])\
        and 'top_score' in player and isinstance(player['top_score'], str) and isint(player['top_score'])\
        and 'average_score' in player and isinstance(player['average_score'], str) and isfloat(player['average_score'])\
        and 'average10_score' in player and isinstance(player['average10_score'], str) and isfloat(player['average10_score'])\
        and 'total_wars' in player and isinstance(player['total_wars'], str) and isint(player['total_wars']) \
        and 'penalties' in player and isinstance(player['penalties'], str) and isint(player['penalties']) \
        and 'total_strikes' in player and isinstance(player['total_strikes'], str) and isint(player['total_strikes']) \
        and 'ranking' in player and isinstance(player['ranking'], str) and (isint(player['ranking']) or player['ranking'] == "Unranked") \
        and 'update_date' in player and isinstance(player['update_date'], str) \
        and 'url' in player and isinstance(player['url'], str):
            continue
        
        for key in player:
            print('key:', key, 'value:', player[key], "type:", type(player[key]))
        return True
    return False


"""Pulling data from API"""
async def pull_API_data(new_full_data_dict, is_rt=True):
    #await asyncio.sleep(interval_time)
    success = True
    specific_url = rt_specific_url if is_rt else ct_specific_url
    chunk_data = None
    for i in range(5):
        try:
            chunk_data = await Shared.fetch(specific_url)
            chunk_is_corrupt = detailed_players_is_corrupt(chunk_data)
            if chunk_is_corrupt:
                print("Chunk was corrupt")
            else:
                break
        except:
            print("Failed to send url request, attempt #" + str(i))
        if i < 4:
            await asyncio.sleep(interval_time*(i+1)) #We wait an increasing amount of time if we fail, we try 5 times remember
    else: #not breaking the loop means we failed 5 times
        success = False
    
    if success and chunk_data != None:
        for player in chunk_data:
            if player['name'] == None:
                continue
            if player['ranking'] == 'Unranked':
                continue
            if player['name'].endswith("_false"):
                continue
            
            player[player_id_json_name] = int(player[player_id_json_name])
            player['strikes'] = int(player['strikes'])
            player['current_mmr'] = int(player['current_mmr'])
            player['peak_mmr'] = int(player['peak_mmr'])
            player['lowest_mmr'] = int(player['lowest_mmr'])
            player['wins'] = int(player['wins'])
            player['loss'] = int(player['loss'])
            player['max_gain_mmr'] = int(player['max_gain_mmr'])
            player['max_loss_mmr'] = int(player['max_loss_mmr'])
            player['win_percentage'] = float(player['win_percentage'])
            player['gainloss10_mmr'] = int(player['gainloss10_mmr'])
            player['wins10'] = int(player['wins10'])
            player['loss10'] = int(player['loss10'])
            player['win10_percentage'] = float(player['win10_percentage'])
            player['win_streak'] = int(player['win_streak'])
            player['top_score'] = int(player['top_score'])
            player['average_score'] = float(player['average_score'])
            player['average10_score'] = float(player['average10_score'])
            player['total_wars'] = int(player['total_wars'])
            player['penalties'] = int(player['penalties'])
            player['total_strikes'] = int(player['total_strikes'])
            player['ranking'] = int(player['ranking'])           
            
            try:
                if isinstance(player['update_date'], str):
                    player['update_date'] = datetime.strptime(player['update_date'], '%Y-%m-%d %H:%M:%S')
                else:
                    player['update_date'] = datetime.min
            except:
                print(player['update_date'])
                player['update_date'] = datetime.min
            new_full_data_dict[player[player_id_json_name]] = player
            
                
    return success
        


"""endcollapse"""
#Returns False is there was an error pulling the data
async def pull_all_data(is_rt=True):
    global lounge_player_data_ct
    global ct_last_updated
    global lounge_player_data_rt
    global rt_last_updated
    global rt_progress
    global ct_progress

    success = True
    new_dict_data = {}
    chunk_success = await pull_API_data(new_dict_data, is_rt)
    
    if not chunk_success:
        print("Failed to pull chunk.")
        success = False  
                    
    if success:
        if is_rt:
            lounge_player_data_rt = new_dict_data
            rt_last_updated = datetime.now()
        else:
            lounge_player_data_ct = new_dict_data
            ct_last_updated = datetime.now() 
                        
    return success

async def pull_data():
    global currently_pulling
    global lounge_player_data_rt
    global lounge_player_data_ct
    global rt_progress
    global ct_progress
    global global_cached
    currently_pulling = True
    rt_progress = 0.0
    ct_progress = 0.0
    
    #RTs first
    rt_success = await pull_all_data(True)
    rt_progress = 100.0
    await asyncio.sleep(interval_time)
    ct_success = await pull_all_data(False)
    ct_progress = 100.0
    global_cached = {}
    
        
    currently_pulling = False
    pickle_player_data()
        
    return rt_success and ct_success


class Leaderboard(object):

    def __init__(self):
        self.last_leaderboard_sent = None
        self.last_stats_sent = None
        self.last_used = None
    
    def isInactive(self):
        if self.last_used == None:
            return False
        else:
            curTime = datetime.now()
            time_passed_since_last_used = curTime - self.last_used
            return time_passed_since_last_used > inactivity_time_period
    
    def is_leaderboard_command(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, leaderboard_terms, prefix)
    
    def is_inrole_command(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, inrole_terms, prefix)
    
    def is_inrole_command_allowed(self, message:discord.Message):
        valid_channels = {389521626645004302}
        valid_categories = {430167221600518174}
        return message.channel.id in valid_channels or message.channel.category_id in valid_categories
        
    
    def is_blacklist_command(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, blacklist_user_terms, prefix)
    def is_remove_blacklist_command(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, remove_blacklist_user_terms, prefix)
    def display_blacklist_command(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, check_blacklist_terms, prefix)
    
    
    def can_send_leaderboard(self):
        if self.last_leaderboard_sent == None:
            return True
        time_passed = datetime.now() - self.last_leaderboard_sent
        return time_passed >= LEADERBOARD_WAIT_TIME
    
    def can_send_stats(self):
        if self.last_stats_sent == None:
            return True
        time_passed = datetime.now() - self.last_stats_sent
        return time_passed >= STATS_WAIT_TIME
    
    def __get_ago_str(self, last_updated):
        last_updated_str = "last updated: "
        how_long_ago = datetime.now() - last_updated
        days = how_long_ago.days
        seconds = int(how_long_ago.total_seconds())
        hours = seconds//3600
        minutes = (seconds//60)%60
        stuffs = []
        if days != 0:
            temp = str(days) + " day"
            if days != 1:
                temp += "s"
            stuffs.append(temp)
        if hours != 0:
            temp = str(hours) + " hour"
            if hours != 1:
                temp += "s"
            stuffs.append(temp)
        if minutes != 0:
            temp = str(minutes) + " minute"
            if minutes != 1:
                temp += "s"
            stuffs.append(temp)
        seconds = seconds % 60
        temp = str(seconds) + " second"
        if seconds != 1:
            temp += "s"
        stuffs.append(temp)
        last_updated_str += ", ".join(stuffs) + " ago"
        return last_updated_str
    
    async def send_inrole_message(self, client, message:discord.Message, prefix=Shared.prefix):
        
        # roles = await ctx.guild.fetch_roles().flatten()
        roleName = " ".join(message.content.split()[1:])
        roles = message.guild.roles
        role = None
        for r in roles:
            if r.name.lower().replace(" ", "") == roleName.lower().replace(" ", ""):
                role = r
                break
                
        if role == None:
            await message.channel.send("That role doesn't exist.")
        else:
            members = await message.guild.fetch_members(limit=None).flatten()
            
            filtered_members = sorted(map(lambda member: f"{member.display_name} ({str(member)})", filter(lambda member: role in member.roles, members)), key=lambda s:s.upper())
            current_page = 0
            max_page = ((len(filtered_members) - 1)//20)
            new_embed = discord.Embed(
                title=f"Members with the {role.name} role:",
                colour = discord.Colour.dark_blue(),
                description='\n'.join(filtered_members[0:20]))
            new_embed.set_footer(text=f"{current_page+1}/{max_page+1}")
    
            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in {LEFT_ARROW_EMOTE, RIGHT_ARROW_EMOTE}
    
            if len(filtered_members) <= 20:
                await message.channel.send(embed=new_embed)
                return
            else:
                embed_page_start_time = datetime.now()
                sent_missing_perms_message = False
                msg = await message.channel.send(embed=new_embed)
                await msg.add_reaction(LEFT_ARROW_EMOTE)
                await msg.add_reaction(RIGHT_ARROW_EMOTE)
                while (datetime.now() - embed_page_start_time) < embed_page_time:

                    timeout_time_delta = embed_page_time - (datetime.now() - embed_page_start_time)
                    timeout_seconds = timeout_time_delta.total_seconds()
                    if timeout_seconds <= 0:
                        break
        
                    try:
                        reaction, user = await client.wait_for('reaction_add', timeout=timeout_seconds, check=check)
                        if(str(reaction.emoji) == LEFT_ARROW_EMOTE):
                            current_page = (current_page - 1) % (max_page + 1)
                        else:
                            current_page = (current_page + 1) % (max_page + 1)

                        new_embed.description = '\n'.join(filtered_members[20*current_page:(20*(current_page+1))])
                        new_embed.set_footer(text=f"{current_page+1}/{max_page+1}")
                        await msg.edit(embed=new_embed)

                    except asyncio.TimeoutError:
                        break
                
                try:
                    await msg.clear_reaction(LEFT_ARROW_EMOTE)
                    await msg.clear_reaction(RIGHT_ARROW_EMOTE)
                except discord.errors.Forbidden:
                    try:
                        await msg.remove_reaction(LEFT_ARROW_EMOTE, client.user)
                        await msg.remove_reaction(RIGHT_ARROW_EMOTE, client.user)
                    except:
                        pass
                    if message.guild != None and not sent_missing_perms_message:
                        await Shared.send_missing_permissions(message.channel)

    """#TODO: Add reaction text"""
    def get_extra_text(self, is_rt=True, is_dm=False):
        total_message = "- Data updates every " + str(int(time_between_pulls.total_seconds())//3600) + " hours"
        cooldown_message = ""
        if not is_dm:
            cooldown_message = '\n- You can do !leaderboard again in ' + str(int(LEADERBOARD_WAIT_TIME.total_seconds())) + " seconds"
        if is_rt:
            if rt_last_updated != None:
                total_message += "\n- RTs " + self.__get_ago_str(rt_last_updated)
        else:
            if ct_last_updated != None:
                total_message += "\n- CTs " + self.__get_ago_str(ct_last_updated)
            

        if currently_pulling:
            if is_rt:
                total_message += "\n- Currently pulling new data. RT progress: " + str(rt_progress) + "%"
            else:
                total_message += "\n- Currently pulling new data. CT progress: " + str(ct_progress) + "%"
        total_message += cooldown_message
        return total_message
    
    def __get_results(self, command_name, field_name, date_filter, should_reverse, minimum_events_needed, x_number, is_rt=True):
        if is_rt not in global_cached:
            global_cached[is_rt] = {}
            
        if command_name in global_cached[is_rt]:
            return global_cached[is_rt][command_name]
        
        to_sort = []
        player_data = lounge_player_data_rt if is_rt else lounge_player_data_ct
        
        if date_filter:
            date_cutoff = datetime.now() - date_filter_time
            for player in player_data.values():
                if player['total_wars'] < minimum_events_needed:
                    continue
                if player['update_date'] < date_cutoff:
                    continue
                #The +1 is to allow them to sub once, and 
                if field_name == 'win_streak' and (player['wins10']+1) < player['win_streak'] and player['wins10'] < 10:
                    continue
                to_sort.append(player)
        else:
            for player in player_data.values():
                if player['total_wars'] < minimum_events_needed:
                    continue
                if field_name == 'win_streak' and (player['wins10']+1) < player['win_streak'] and player['wins10'] < 10:
                    continue
                to_sort.append(player)
            
        to_sort.sort(key=lambda p:p[field_name], reverse=should_reverse)
        results = to_sort[:x_number]
        global_cached[is_rt][command_name] = results
        return results
        
        

    async def send_leaderboard_message(self, client, message:discord.Message, prefix=Shared.prefix):
        self.last_used = datetime.now()
        command_end = Shared.strip_prefix_and_command(message.content, leaderboard_terms, prefix).strip().split()        
        cooldown_message = ""
        global stats_count
        if message.guild == None:
            self.last_leaderboard_sent = None
            stats_count[0] += 1
        else:
            stats_count[1] += 1
            cooldown_message = '\n\n`You can do !leaderboard again in ' + str(int(LEADERBOARD_WAIT_TIME.total_seconds())) + " seconds`"
            self.last_leaderboard_sent = datetime.now()
        if len(command_end) != 2:
            await Shared.safe_send(message.channel, "Here's how to use this command: *!leaderboard  <rt/ct>  <stat>*\n**stat** can be any of the following: *" + ",  ".join(stat_terms) + "*" + cooldown_message)
        
        else:
            if command_end[0].lower() not in leaderboard_type_terms:
                await Shared.safe_send(message.channel, "Specify a leaderboard type: rt or ct" + cooldown_message)
            else:
                if command_end[1].lower() not in stat_terms:
                    await Shared.safe_send(message.channel, "Your **stat** was not valid. Here's how to use this command:\n*!leaderboard  <rt/ct>  <stat>*\n**stat** can be any of the following: *" + ",  ".join(stat_terms) + "*" + cooldown_message)
                else:
                    is_rt = command_end[0].lower() == 'rt'
                    total_stats[command_end[0].lower()][command_end[1].lower()] += 1
                    
                    still_booting = False
                    if is_rt and lounge_player_data_rt == None:
                        await Shared.safe_send(message.channel, "The bot just booted up. Player data is still loading for RTs: **" + str(rt_progress) + "%** - This can take several minutes, try again later." + cooldown_message)
                        still_booting = True
                    if not is_rt and lounge_player_data_ct == None:
                        await Shared.safe_send(message.channel, "The bot just booted up. Player data is still loading for CTs: **" + str(ct_progress) + "%** - This can take several minutes, try again later." + cooldown_message)
                        still_booting = True
                    
                    #The bot has fully booted up
                    if not still_booting:
                        #=========== Zero in here ============
                        field_name, embed_name, date_filter, should_reverse, minimum_events_needed = stat_terms[command_end[1].lower()]
                        results = self.__get_results(command_end[1].lower(), field_name, date_filter, should_reverse, minimum_events_needed, TOP_N_RESULTS, is_rt)
                        
                        is_dm = message.guild == None
                        page_num = 1
                        first_page_embed = self.get_embed_page(page_num, results, is_rt, embed_name, field_name, is_dm)             
                        embed_message = await Shared.safe_send(message.channel, embed=first_page_embed)
                        
                        try:
                            await embed_message.add_reaction(LEFT_ARROW_EMOTE)
                            await embed_message.add_reaction(RIGHT_ARROW_EMOTE)
                        except discord.errors.Forbidden:
                            await Shared.send_missing_permissions(message.channel)
                            return
                        
                        message_author = message.author
                        
                        embed_page_start_time = datetime.now()
                        sent_missing_perms_message = False
                        while (datetime.now() - embed_page_start_time) < embed_page_time:
                            def check(reaction, user):
                                return reaction.message.id == embed_message.id and user == message_author and (str(reaction.emoji) == LEFT_ARROW_EMOTE or str(reaction.emoji) == RIGHT_ARROW_EMOTE)
        
                            should_send_error_message = False
                            timeout_time_delta = embed_page_time - (datetime.now() - embed_page_start_time)
                            timeout_seconds = timeout_time_delta.total_seconds()
                            if timeout_seconds <= 0:
                                break
                            reaction, user = None, None
                            try:
                                reaction, user = await client.wait_for('reaction_add', timeout=timeout_seconds, check=check)
                            except asyncio.TimeoutError:
                                break
                            
                            #We know the original author added left or right arrow reaction
                            if message.guild != None:
                                try:
                                    await embed_message.remove_reaction(reaction, user)
                                except discord.errors.Forbidden:
                                    should_send_error_message = True
                            
                            if str(reaction.emoji) == LEFT_ARROW_EMOTE:
                                if page_num > 1:
                                    page_num -= 1
                            elif str(reaction.emoji) == RIGHT_ARROW_EMOTE:
                                if page_num < 5:
                                    page_num += 1
                                    
                            embed_page = self.get_embed_page(page_num, results, is_rt, embed_name, field_name, is_dm)
                                
                            try:
                                await embed_message.edit(embed=embed_page, suppress=False)
                            except discord.errors.Forbidden:
                                should_send_error_message = True
                            
                            if should_send_error_message:
                                Shared.send_missing_permissions(message.channel)
                                sent_missing_perms_message = True
                                
                        try:
                            await embed_message.clear_reaction(LEFT_ARROW_EMOTE)
                            await embed_message.clear_reaction(RIGHT_ARROW_EMOTE)
                        except discord.errors.Forbidden:
                            try:
                                await embed_message.remove_reaction(LEFT_ARROW_EMOTE, client.user)
                                await embed_message.remove_reaction(RIGHT_ARROW_EMOTE, client.user)
                            except:
                                pass
                            if message.guild != None and not sent_missing_perms_message:
                                await Shared.send_missing_permissions(message.channel)
                            
                        
                        
    def get_embed_page(self, page_num, results, is_rt, embed_name, field_name, is_dm=False) -> discord.Embed:
        embed_name = ("RT - " if is_rt else "CT - ") + embed_name + " - Page " + str(page_num) + "/5"
        embed = discord.Embed(
                    title = embed_name,
                    colour = discord.Colour.dark_blue()
                )
            
        
        to_display = results[(page_num-1)*10:(page_num*10)]
        
        if len(to_display) > 1:
            for rank, player in enumerate(to_display, start=((page_num-1)*10)+1):
                player_name = player['name']
                data_piece = player[field_name]
                if isinstance(data_piece, float):
                    if field_name in mult_100_fields:
                        data_piece = str(round((data_piece*100), 1)) + "%"
                    else:
                        data_piece = round(data_piece, 1)
                data_piece = str(data_piece)
                value_field = "[\u200b\u200b" + data_piece + "](" + player['url'] + ")"
                embed.add_field(name=player_name, value=value_field, inline=False)
        else:
            embed.add_field(name="No more players", value="\u200b", inline=False)
        
        page_number_text = "- Page " + str(page_num) + "/5\n"
        embed.set_footer(text=self.get_extra_text(is_rt, is_dm))
        
        return embed
        
    
    
    def get_top_x_stats_str(self, top_x=3):
        rt_top = sorted(total_stats['rt'].items(), key=lambda item: item[1], reverse=True)
        ct_top = sorted(total_stats['ct'].items(), key=lambda item: item[1], reverse=True)
        
        total_str = "**Most used leaderboard commands (RT):**\n"
        for field_name, amount in rt_top[:top_x]:
            total_str += "- " + field_name + ": " + str(amount) + " commands\n"
            
        total_str += "\n**Most used leaderboard commands (CT):**\n"
        for field_name, amount in ct_top[:top_x]:
            total_str += "- " + field_name + ": " + str(amount) + " commands\n"
        return total_str
    
    async def send_stats(self, message, top_x=3):
        if message.guild == None:
            self.last_stats_sent = None
        else:
            self.last_stats_sent = datetime.now()
            
        part1_str = "Could not find leaderboard command count."
        if stats_count != None:
            part1_str = "**Leaderboard commands processed:** "
            part1_str += str(stats_count[0]) + " in DMs | " + str(stats_count[1]) + " in servers"
            
        part2_str = "Could not get top " + str(top_x) + " stats."
        if total_stats != None and len(total_stats['rt']) >= top_x and len(total_stats['ct']) >= top_x:
            part2_str = self.get_top_x_stats_str(top_x)
            
            
        await Shared.safe_send(message.channel, part2_str + "\n" + part1_str)
        
        
        
    async def process_leaderboard_command(self, client, message:discord.Message, prefix=Shared.prefix):
        if client.user in message.mentions:
            Shared.log_message(message)
            if await Shared.process_blacklist(client, message):
                pass
            elif self.can_send_stats():
                await self.send_stats(message)
                
        if not Shared.has_prefix(message.content, prefix):
            return False
        if self.is_leaderboard_command(message.content, prefix):
            Shared.log_message(message)
            if await Shared.process_blacklist(client, message):
                pass
            elif self.can_send_leaderboard():
                await self.send_leaderboard_message(client, message, prefix)
        if self.is_inrole_command(message.content, prefix):
            if await Shared.process_blacklist(client, message):
                pass
            if self.is_inrole_command_allowed(message):
                await self.send_inrole_message(client, message, prefix)
        if self.is_blacklist_command(message.content, prefix):
            if Shared.can_blacklist(message.author):
                await Shared.blacklist(message)
        if self.is_remove_blacklist_command(message.content, prefix):
            if Shared.can_blacklist(message.author):
                await Shared.remove_blacklist(message)
        if self.display_blacklist_command(message.content, prefix):
            if Shared.can_blacklist(message.author):
                await Shared.send_blacklist(message)
        else:
            return False
        return True
    
