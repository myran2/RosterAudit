#!/usr/bin/python3

import datetime
import requests
import traceback
from ratelimit import limits, sleep_and_retry
import mysql.connector as mariadb
from wowapi import WowApi
from wowapi.mixins.profile import ProfileMixin
import Config

WOW_WEEKLY_RESET_TIME_UTC = 15
WOW_EXPANSION_SHADOWLANDS = 499
WOW_CURRENT_RAID_ENCOUNTER_ID = 1195 # Sepulcher of the First Ones
WOW_REPUTATION_THE_ENLIGHTED = 2478

PVP_BRACKET_TO_ID = {
    "2v2": 0,
    "3v3": 1,
    "rbg": 2
}

RAID_DIFFICULTY_TO_ID = {
    "MYTHIC": 0,
    "HEROIC": 1,
    "NORMAL": 2,
    "LFR": 3,
}

# connect to DB
DBCON = mariadb.connect(
    host=Config.mysqlHost,
    user=Config.mysqlUser,
    passwd=Config.mysqlPasswd,
    database=Config.mysqlDb
)
DB = DBCON.cursor()

def getLastWeeklyResetDateTime():
    curTime = datetime.datetime.utcnow()
    addlWeekOffset = 0
    # if it's currently a tuesday but before reset, we want last tuesday's date instead
    if curTime.weekday == 1 and curTime.hour < WOW_WEEKLY_RESET_TIME_UTC:
        addlWeekOffset = 7
    # go back to monday of last week
    lastReset = curTime - datetime.timedelta(days=curTime.weekday()+addlWeekOffset)
    # add a whole day, becoming tuesday
    lastReset += datetime.timedelta(days=1)
    # set time to exactly the reset hour
    lastReset = lastReset.replace(hour=WOW_WEEKLY_RESET_TIME_UTC, minute=0, second=0, microsecond=0)

    # format as SQL DATETIME
    return lastReset

@sleep_and_retry
@limits(calls=300, period=60)
def getWeeklyKeysForPlayer(name, server):
    # retrieve the player's ten highest Mythic+ runs by Mythic+ level for the current raid week (current season only)
    rioRequestUrl = "https://raider.io/api/v1/characters/profile?region=us&realm={0}&name={1}&fields=mythic_plus_weekly_highest_level_runs".format(server, name)
    rioResponse = requests.get(rioRequestUrl)

    if rioResponse.status_code != 200:
        raise Exception('API response: {} - {}'.format(rioResponse.status_code, rioRequestUrl))

    return rioResponse.json()['mythic_plus_weekly_highest_level_runs']

def getReputationForPlayer(API, rep_id, name, server):
    character_rep_res = ProfileMixin.get_character_reputations_summary(API, 'us', 'profile-us', server, name)
    for r in character_rep_res['reputations']:
        if r['faction']['id'] != WOW_REPUTATION_THE_ENLIGHTED:
            continue
        return r['standing']['raw']
    return 0

def refreshRoster(API):

    # get blizz IDs of all members already in the DB
    query = "SELECT blizz_id FROM raider"
    DB.execute(query)
    existing_blizz_ids_dbo = DB.fetchall()
    existing_blizz_ids = []
    for row in existing_blizz_ids_dbo:
        existing_blizz_ids.append(row[0])

    guild = ProfileMixin.get_guild_roster(API, 'us', 'profile-us', Config.guildRealmSlug, Config.guildNameSlug)
    for member in guild['members']:
        if member['rank'] not in Config.guildTrackRanks:
            continue

        char = member['character']
        if char['id'] not in existing_blizz_ids:
            query = "INSERT INTO raider (blizz_id, name, playerClass) VALUES(%s, %s, %s)"
            values = (char['id'], char['name'], char['playable_class']['id'])
            DB.execute(query, values)

    DBCON.commit()


def main():

    API = WowApi(Config.blizzApiClientId, Config.blizzApiClientSecret)

    refreshRoster(API)

    roster = []
    DB.execute("SELECT name, realm FROM raider WHERE NOT `ignore`")
    for row in DB:
        roster.append({
            "name": row[0].lower(),
            "realm": row[1].lower()
        })

    for raider in roster:
        character_raids = None
        try:
            character_raids = API.get_character_raids('us', 'profile-us', raider['realm'], raider['name'])
        except Exception as err:
            print(err)
            print("{} not found. skipping.".format(raider['name']))
            traceback.print_exc()
            break

        raiderPvpBrackets = dict()
        for bracket in PVP_BRACKET_TO_ID.keys():
            apiRes = None
            try:
                apiRes = API.get_character_pvp_bracket_stats('us', 'profile-us', raider['realm'], raider['name'], bracket)
            except Exception as err:
                continue

            if apiRes is not None:
                raiderPvpBrackets[bracket] = apiRes

        charName = character_raids["character"]["name"]
        charId = character_raids["character"]["id"]

        print(charName)

        # boss kills (by difficulty)
        query = "DELETE FROM raider_boss_history WHERE timestamp >= %s AND raider_id = %s"
        values = (getLastWeeklyResetDateTime(), charId)
        DB.execute(query, values)
        if 'expansions' not in character_raids:
            print("\tNo expansions in character raid statistics")
        else:
            for ex in character_raids['expansions']:
                if ex['expansion']['id'] != WOW_EXPANSION_SHADOWLANDS:
                    continue
                for instance in ex['instances']:
                    if instance['instance']['id'] != WOW_CURRENT_RAID_ENCOUNTER_ID:
                        continue
                    for m in instance['modes']:
                        difficulty_id = RAID_DIFFICULTY_TO_ID[m['difficulty']['type']]
                        boss_kill_count = 0
                        for p in m['progress']['encounters']:
                            if datetime.datetime.fromtimestamp(float(p['last_kill_timestamp'])/1000.0) > getLastWeeklyResetDateTime():
                                boss_kill_count += 1

                        if boss_kill_count > 0:
                            query = "INSERT INTO raider_boss_history (raider_id, raid_difficulty, boss_kill_count) VALUES (%s, %s, %s)"
                            values = (charId, difficulty_id, boss_kill_count)
                            DB.execute(query, values)

        # 10 highest weekly keys (from r.io)
        highest10Keystones = getWeeklyKeysForPlayer(raider['name'], raider['realm'])
        query = "DELETE FROM raider_key_history WHERE timestamp >= %s AND raider_id = %s"
        values = (getLastWeeklyResetDateTime(), charId)
        DB.execute(query, values)
        for key in highest10Keystones:
            query = "INSERT INTO raider_key_history (raider_id, key_level, dungeon) VALUES (%s, %s, %s)"
            values = (charId, key['mythic_level'], key['zone_id'])
            DB.execute(query, values)

        # rated PvP wins
        today = datetime.datetime.now()
        today_midnight = today.replace(hour=0, minute=0, second=0, microsecond=0)
        query = "DELETE FROM raider_pvp_history WHERE timestamp >= %s AND raider_id = %s"
        values = (str(today_midnight), charId)
        DB.execute(query, values)
        for bracket, apiRes in raiderPvpBrackets.items():
            rating = apiRes['rating'] if 'rating' in apiRes else 0

            wins = 0
            losses = 0
            bracket_id = PVP_BRACKET_TO_ID[bracket]
            if 'weekly_match_statistics' in apiRes:
                wins = apiRes['weekly_match_statistics']['won']
                losses = apiRes['weekly_match_statistics']['lost']

            if wins + losses > 0:
                print("{} won: {}, lost:{}".format(raider['name'], wins, losses))
                query = "INSERT INTO raider_pvp_history (raider_id, bracket, win_count, loss_count, rating) VALUES (%s, %s, %s, %s, %s)"
                values = (charId, bracket_id, wins, losses, rating)
                DB.execute(query, values)

        # The Enlightened rep
        query = "DELETE FROM raider_rep_history WHERE timestamp >= %s AND raider_id = %s"
        values = (str(today_midnight), charId)
        DB.execute(query, values)

        raw_rep = getReputationForPlayer(API, WOW_REPUTATION_THE_ENLIGHTED, raider['name'], raider['realm'])
        if raw_rep > 0:
            query = "INSERT INTO raider_rep_history (raider_id, faction_id, raw_reputation) VALUES (%s, %s, %s)"
            values = (charId, WOW_REPUTATION_THE_ENLIGHTED, raw_rep)
            DB.execute(query, values)


    DBCON.commit()


if __name__ == '__main__':
  main()