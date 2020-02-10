#!/usr/bin/python3

import Config
import mysql.connector as mariadb
from wowapi import WowApi
from wowapi.mixins.game_data import GameDataMixin

# connect to DB
dbCon = mariadb.connect(
    host=Config.mysqlHost,
    user=Config.mysqlUser,
    passwd=Config.mysqlPasswd,
    database=Config.mysqlDb
)
db = dbCon.cursor()

api = WowApi(Config.blizzApiClientId, Config.blizzApiClientSecret)
guild = GameDataMixin.get_guild_roster_data(api, 'us', 'profile-us', Config.guildRealmSlug, Config.guildNameSlug)
for member in guild["members"]:
    if member["rank"] in Config.guildTrackRanks:
        char = member["character"]

        # confirm that raider is already in the DB
        query = "SELECT name FROM raider WHERE blizz_id = {}".format(char["id"])
        db.execute(query)

        # raider isn't in DB yet
        if not db.fetchall():
            query = "INSERT INTO raider (blizz_id, name, playerClass, playerRoles) VALUES (%s, %s, %s, %s)"
            values = (char["id"], char["name"], char["playable_class"]["id"], 0)
            db.execute(query, values)

# commit all inserts at once
dbCon.commit()

roster = []
query = "SELECT name FROM raider"
db.execute(query)
for name in db:
    roster.append(name[0].lower())

for raider in roster:
    try:
        character = api.get_character_equipment_summary('us', 'profile-us', 'bleeding-hollow', raider)
    except:
        print("{} not found. skipping".format(raider))
        continue

    charName = character["character"]["name"]
    charId = character["character"]["id"]
    neckLevel = 0.0
    neckLevelPercentage = 0.0
    capeLevel = 0

    print(charName)

    for item in character["equipped_items"]:
        if item["slot"]["type"] == "NECK":
            neckLevel = item["azerite_details"]["level"]["value"]
            neckLevelPercentage = item["azerite_details"]["percentage_to_next_level"]

            neckLevel += round(neckLevelPercentage, 2)

        if item["slot"]["type"] == "BACK":
            # not wearing legendary cape
            if item["item"]["id"] != 169223:
                break
            capeLevel = int(((item["level"]["value"] - 470) / 2) + 1)
            break

    query = "INSERT INTO raider_history (raider_id, neck_level, cape_level) VALUES (%s, %s, %s)"
    values = (charId, neckLevel, capeLevel)
    db.execute(query, values)

dbCon.commit()
