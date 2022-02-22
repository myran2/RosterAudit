#!/usr/bin/python3

import datetime
import requests
from ratelimit import limits, sleep_and_retry
import mysql.connector as mariadb
from wowapi import WowApi
import Config

WOW_WEEKLY_RESET_TIME_UTC = 15

def getLastWeeklyResetDateTime():
    curTime = datetime.datetime.utcnow()
    # it's a tuesday but before reset, so we want last tuesday
    if curTime.hour < WOW_WEEKLY_RESET_TIME_UTC:
        addlWeekOffset = 7
    # go back to monday of last week
    lastReset = curTime - datetime.timedelta(days=curTime.weekday()+addlWeekOffset)
    # add a whole day, becoming tuesday
    lastReset += datetime.timedelta(days=1)
    lastReset = lastReset.replace(hour=WOW_WEEKLY_RESET_TIME_UTC, minute=0, second=0, microsecond=0)

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

def main():
    # connect to DB
    DBCON = mariadb.connect(
        host=Config.mysqlHost,
        user=Config.mysqlUser,
        passwd=Config.mysqlPasswd,
        database=Config.mysqlDb
    )
    DB = DBCON.cursor()

    API = WowApi(Config.blizzApiClientId, Config.blizzApiClientSecret)

    roster = []
    DB.execute("SELECT name FROM raider")
    for name in DB:
        roster.append(name[0].lower())

    for raider in roster:
        try:
            character = API.get_character_equipment_summary('us', 'profile-us', Config.guildRealmSlug, raider)

            # grab weekly pvp wins: bnet /profile/wow/character/{realmSlug}/{characterName}/pvp-bracket/{pvpBracket}
            pvpBrackets = {
                "2v2": API.get_character_pvp_bracket_stats('us', 'profile-us', Config.guildRealmSlug, raider, '2v2')['weekly_match_statistics'],
                "3v3": API.get_character_pvp_bracket_stats('us', 'profile-us', Config.guildRealmSlug, raider, '3v3')['weekly_match_statistics'],
                "rbg": API.get_character_pvp_bracket_stats('us', 'profile-us', Config.guildRealmSlug, raider, 'rbg')['weekly_match_statistics']
            }

        except Exception as err:
            print(err)
            print("{} not found. skipping.".format(raider))
            continue

        charName = character["character"]["name"]
        charId = character["character"]["id"]

        highest10Keystones = getWeeklyKeysForPlayer(raider, Config.guildRealmSlug)
        for key in highest10Keystones:
            query = "DELETE FROM raider_key_history WHERE timestamp >= '%s'"
            values = (getLastWeeklyResetDateTime())
            DB.execute(query, values)

            query = "INSERT INTO raider_key_history (raider_id, key_level, dungeon) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE key_level=%s"
            values = (charId, key['mythic_level'], key['zone_id'], key['mythic_level'])
            DB.execute(query, values)

    DBCON.commit()


if __name__ == '__main__':
  main()