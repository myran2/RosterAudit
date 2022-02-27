#!/usr/bin/python3

import datetime
import requests
from ratelimit import limits, sleep_and_retry
import mysql.connector as mariadb
from wowapi import WowApi
from wowapi.mixins.profile import ProfileMixin
import Config

WOW_WEEKLY_RESET_TIME_UTC = 15

PVP_BRACKET_TO_ID = {
    "2v2": 0,
    "3v3": 1,
    "rbg": 2
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
    return lastReset.strftime('Y-m-d H:i:s')

@sleep_and_retry
@limits(calls=300, period=60)
def getWeeklyKeysForPlayer(name, server):
    # retrieve the player's ten highest Mythic+ runs by Mythic+ level for the current raid week (current season only)
    rioRequestUrl = "https://raider.io/api/v1/characters/profile?region=us&realm={0}&name={1}&fields=mythic_plus_weekly_highest_level_runs".format(server, name)
    rioResponse = requests.get(rioRequestUrl)

    if rioResponse.status_code != 200:
        raise Exception('API response: {} - {}'.format(rioResponse.status_code, rioRequestUrl))

    return rioResponse.json()['mythic_plus_weekly_highest_level_runs']

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
        try:
            character = API.get_character_equipment_summary('us', 'profile-us', raider['realm'], raider['name'])
        except Exception as err:
            print(err)
            print("{} not found. skipping.".format(raider['name']))
            continue

        raiderPvpBrackets = dict()
        for bracket in PVP_BRACKET_TO_ID.keys():
            apiRes = None
            try:
                apiRes = API.get_character_pvp_bracket_stats('us', 'profile-us', raider['realm'], raider['name'], bracket)
            except Exception as err:
                continue

            if apiRes is not None:
                raiderPvpBrackets[bracket] = apiRes

        charName = character["character"]["name"]
        charId = character["character"]["id"]

        # 10 highest weekly keys (from r.io)
        highest10Keystones = getWeeklyKeysForPlayer(raider['name'], raider['realm'])
        query = "DELETE FROM raider_key_history WHERE timestamp >= %s AND raider_id = %s"
        values = (getLastWeeklyResetDateTime(), charId)
        DB.execute(query, values)
        for key in highest10Keystones:
            query = "INSERT INTO raider_key_history (raider_id, key_level, dungeon) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE key_level=%s"
            values = (charId, key['mythic_level'], key['zone_id'], key['mythic_level'])
            DB.execute(query, values)

        # rated PvP wins
        today = datetime.datetime.now()
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)
        query = "DELETE FROM raider_pvp_history WHERE timestamp >= %s AND raider_id = %s"
        values = (str(today), charId)
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
                query = """INSERT INTO raider_pvp_history (raider_id, bracket, win_count, loss_count, rating)
                            VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE win_count=%s, loss_count=%s, rating=%s"""
                values = (charId, bracket_id, wins, losses, rating, wins, losses, rating)
                DB.execute(query, values)


    DBCON.commit()


if __name__ == '__main__':
  main()