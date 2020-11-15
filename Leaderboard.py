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
__rt_main_url_deprecated = "https://mariokartboards.com/lounge/json/player.php?type=rt&all"
__ct_main_url_deprecated = "https://mariokartboards.com/lounge/json/player.php?type=ct&all"
__rt_specific_url_deprecated = "https://mariokartboards.com/lounge/json/player.php?type=rt&name="
__ct_specific_url_deprecated = "https://mariokartboards.com/lounge/json/player.php?type=ct&name="

rt_specific_url = "https://mariokartboards.com/lounge/json/leaderboard.php?type=rt"
ct_specific_url = "https://mariokartboards.com/lounge/json/leaderboard.php?type=ct"

currently_pulling = True
interval_time = 20 #wait this many seconds between each ping to mkboards.com
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



leaderboard_terms = {"leader", "leaderboard", "ldr", "board"}
leaderboard_type_terms = {'rt', 'ct'}
blacklist_user_terms = {"blacklistuser", "banuser", "ban"}
remove_blacklist_user_terms = {"unban", "unbanuser", "removeban", "unblacklist", "unblacklistuser", "removeblacklist", "blacklistuserremove"}
check_blacklist_terms = {"blacklist", "check", "checkblacklist", "displayblacklist", "banlist"}
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
            

#JSON Data corruption checks - No longer used since new Lounge API is favored     
def __all_player_is_corrupt_deprecated(json_data):
    if not isinstance(json_data, list):
        return True
    if len(json_data) < 1:
        return True
    
    for item in json_data:
        if not isinstance(item, dict):
            return True
        if 'pid' not in item or 'name' not in item or not isinstance(item['pid'], int) or not isinstance(item['name'], str):
            return True
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
         
         
        if 'pid' in player and isinstance(player['pid'], int) \
        and 'name' in player and isinstance(player['name'], str) \
        and 'strikes' in player and isinstance(player['strikes'], int) \
        and 'current_mmr' in player and isinstance(player['current_mmr'], int) \
        and 'peak_mmr' in player and isinstance(player['peak_mmr'], int) \
        and 'lowest_mmr' in player and isinstance(player['lowest_mmr'], int) \
        and 'wins' in player and isinstance(player['wins'], int) \
        and 'loss' in player and isinstance(player['loss'], int) \
        and 'max_gain_mmr' in player and isinstance(player['max_gain_mmr'], int) \
        and 'max_loss_mmr' in player and isinstance(player['max_loss_mmr'], int) \
        and 'win_percentage' in player and isinstance(player['win_percentage'], (float, int)) \
        and 'gainloss10_mmr' in player and isinstance(player['gainloss10_mmr'], int) \
        and 'wins10' in player and isinstance(player['wins10'], int) \
        and 'loss10' in player and isinstance(player['loss10'], int) \
        and 'win10_percentage' in player and isinstance(player['win10_percentage'], (float, int)) \
        and 'win_streak' in player and isinstance(player['win_streak'], int) \
        and 'top_score' in player and isinstance(player['top_score'], int) \
        and 'average_score' in player and isinstance(player['average_score'], (float, int)) \
        and 'average10_score' in player and isinstance(player['average10_score'], (float, int)) \
        and 'total_wars' in player and isinstance(player['total_wars'], int) \
        and 'penalties' in player and isinstance(player['penalties'], int) \
        and 'total_strikes' in player and isinstance(player['total_strikes'], int) \
        and 'ranking' in player and isinstance(player['ranking'], str) and (player['ranking'].isnumeric() or player['ranking'] == "Unranked") \
        and 'update_date' in player and isinstance(player['update_date'], str) \
        and 'url' in player and isinstance(player['url'], str):
            continue
        
        for key in player:
            print('key:', key, 'value:', player[key], "type:", type(player[key]))
        return True
    return False

#TODO: Fix this



"""Pulling data from API"""
async def pull_API_data(new_full_data_dict, is_rt=True):
    await asyncio.sleep(interval_time)
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
            
            try:
                if isinstance(player['update_date'], str):
                    player['update_date'] = datetime.strptime(player['update_date'], '%Y-%m-%d %H:%M:%S')
                else:
                    player['update_date'] = datetime.min
            except:
                print(player['update_date'])
                player['update_date'] = datetime.min
            new_full_data_dict[player['pid']] = player
            
                
    return success
        

"""Pulling data from API"""
async def __pull_chunk_deprecated(player_name:List[str], new_full_data_dict, is_rt=True):
    await asyncio.sleep(interval_time)
    success = True
    specific_url = __rt_specific_url_deprecated if is_rt else __ct_specific_url_deprecated
    specific_url += ",".join(player_name).replace(" ","")
    chunk_data = None
    for i in range(5):
        try:
            chunk_data = await Shared.fetch(specific_url)
            chunk_is_corrupt = detailed_players_is_corrupt(chunk_data, False)
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
            if player['ranking'] == 'Unranked':
                continue
            try:
                if isinstance(player['update_date'], str):
                    player['update_date'] = datetime.strptime(player['update_date'], '%Y-%m-%d %H:%M:%S')
                else:
                    player['update_date'] = datetime.min
            except:
                print(player['update_date'])
                player['update_date'] = datetime.min
            new_full_data_dict[player['pid']] = player
            
                
    return success
        

#Returns False is there was an error pulling the data - deprecated in favor of pull_all_data
#since that uses the new Leaderboard API, which means pinging only once 
async def __pull_all_data_deprecated(is_rt=True):
    global lounge_player_data_ct
    global ct_last_updated
    global lounge_player_data_rt
    global rt_last_updated
    global rt_progress
    global ct_progress

    all_players = None
    success = True
    main_url = __rt_main_url_deprecated if is_rt else __ct_main_url_deprecated
    new_dict_data = {}
    
    try:
        all_players = await Shared.fetch(main_url)
    except:
        success = False
    data_is_corrupt = __all_player_is_corrupt_deprecated(all_players)
    if data_is_corrupt:
        success = False
    else:
        #do good stuff
        all_players.sort(key=lambda x:x['pid'])
        next_chunk = []
        
        for i, player in enumerate(all_players):
            if player['name'].endswith("_false"):
                continue
            next_chunk.append(player['name'])
            
            
            if len(next_chunk) == chunk_size:
                chunk_success = await __pull_chunk_deprecated(next_chunk, new_dict_data, is_rt)
                if not chunk_success:
                    print("Failed to pull chunk.")
                    success = False
                    break
                next_chunk = []
                if is_rt:
                    rt_progress = round( (i/len(all_players))*100, 1)
                    
                else:
                    ct_progress = round( (i/len(all_players))*100, 1)

    
        else:
            if len(next_chunk) > 0:
                chunk_success = await __pull_chunk_deprecated(next_chunk, new_dict_data, is_rt)
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
            
    if is_rt:
        rt_progress = 100.0
    else:
        ct_progress = 100.0
                        
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
                if field_name == 'win_streak' and player['wins10'] < player['win_streak']:
                    continue
                to_sort.append(player)
        else:
            for player in player_data.values():
                if player['total_wars'] < minimum_events_needed:
                    continue
                if field_name == 'win_streak' and player['wins10'] < player['win_streak']:
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
    
