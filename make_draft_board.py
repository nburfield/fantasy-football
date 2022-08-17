#!/usr/bin/env python3

"""
Fantasy Football ADP data draftboard builder.
"""

import argparse
import logging
import os
import csv
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import requests


# Used for ARGS validation
SCORE_FORMATS = ["ppr", "half-ppr", "standard"]
TEAMS = ["8", "10", "12", "14"]

# Used to map player names for consistency among platforms
PLAYER_NAME_MAP = {"Travis Etienne Jr.": "travis_etienne",
                   "Travis Etienne": "travis_etienne",
                   "Melvin Gordon III": "melvin_gordon",
                   "Melvin Gordon": "melvin_gordon",
                   "Ronald Jones II": "ronald_jones",
                   "Ronald Jones": "ronald_jones",
                   "Darrell Henderson": "darrell_henderson",
                   "Darrell Henderson Jr.": "darrell_henderson",
                   "Mark Ingram": "mark_ingram",
                   "Mark Ingram II": "mark_ingram",
                   "Isaih Pacheco": "isiah_pacheco",
                   "Isiah Pacheco": "isiah_pacheco",
                   "Brian Robinson Jr.": "brian_robinson",
                   "Brian Robinson": "brian_robinson",
                   "Jeffery Wilson": "jeffery_wilson",
                   "Jeff Wilson Jr.": "jeffery_wilson",
                   "Allen Robinson": "allen_robinson",
                   "Allen Robinson II": "allen_robinson",
                   "Gabriel Davis": "gabe_davis",
                   "Gabe Davis": "gabe_davis",
                   "Josh Palmer": "josh_palmer",
                   "Joshua Palmer": "josh_palmer",
                   "Robby Anderson": "robbie_anderson",
                   "Robbie Anderson": "robbie_anderson",
                   "Marvin Jones": "marvin_jones",
                   "Marvin Jones Jr.": "marvin_jones",
                   "Robert Tonyan Jr.": "robert_tonyan",
                   "Robert Tonyan": "robert_tonyan"
                  }


def get_adp_data(datamap):
    """
    get_adp_data Makes a call to the ADP data source and build Dict of ADP data

    :param datamap: The values to build the API call
    :return A dict of the ADP data
    """

    # Build the request URL
    try:
        adp_base_url = datamap["adp_base_url"]
        scoring_format = datamap["scoring_format"]
        player_count = datamap["player_count"]
        year = datamap["year"]
    except Exception as ex: # pylint: disable=broad-except
        logging.error("datamap Dict must have all Keys: %s", str(ex))

    # Build and call ADP URL
    url = f"{adp_base_url}/{scoring_format}?position=all&teams={player_count}&year={year}"
    logging.info("Calling ADP URL %s", url)
    adp_r = requests.get(url)

    # Validata success and get values
    adp_data = {}
    if adp_r.ok:
        adp_r_json = adp_r.json()
        if adp_r_json.get("status", "bad") == "Success":
            for player in adp_r_json["players"]:
                # Make the Dict key from player name
                key = player["name"].replace(' ', '_').replace('.', '').lower()

                # Check for a key mapping with this player
                if player["name"] in PLAYER_NAME_MAP:
                    key = PLAYER_NAME_MAP[player["name"]]

                # Log when duplicate players are found
                if key in adp_data:
                    logging.error("%s has duplicate hits.", player["name"])

                # Set the player key/value
                adp_data[key] = player
        else:
            logging.error("Bad API call with Status: %s", adp_r_json.get("status"))
            raise Exception("Bad ADP API Call Status")
    else:
        logging.error("Bad API call: %s", adp_r.text)
        raise Exception("Bad ADP API Call")

    return adp_data


def add_player_rankings(datamap, adp_data):
    """
    add_player_rankings Pull the player ranking CSVs and add that to ADP data.
    Attempts to match the names as the key. Will log failed Attempts.

    :param datamap: The values to build the dataset
    :param adp_data: A Dict of the current ADP data w/ Key being the player names
    """

    position_files = ["qb.csv", "rb.csv", "wr.csv", "te.csv"]
    scoring_format = datamap["scoring_format"]
    for position in position_files:
        file_path = f"./ffrd/{scoring_format}/{position}"

        # Check if the file exists
        if not os.path.isfile(file_path):
            logging.error("Ranking File %s Does Not Exist", file_path)
            continue

        # Open CSV and parse data
        with open(file_path, "r", encoding="utf-8") as pr_f:
            player_list = csv.DictReader(pr_f)
            for player in player_list:
                # Get the Data key and verify it exists
                key = player["Name"].replace(' ', '_').replace('.', '').lower()

                # Check for a key mapping with this player
                if player["Name"] in PLAYER_NAME_MAP:
                    key = PLAYER_NAME_MAP[player["Name"]]

                # Log and skip on error
                if not key in adp_data:
                    logging.error("ADP Data for Player %s Not Found", player["Name"])
                    continue

                # Set the Rankings in ADP
                try:
                    adp_data[key]["rank"] = int(player["Rank"])
                    adp_data[key]["andy"] = int(player["Andy"])
                    adp_data[key]["mike"] = int(player["Mike"])
                    adp_data[key]["jason"] = int(player["Jason"])
                except Exception as ex: # pylint: disable=broad-except
                    logging.error("Bad Values for %s : %s", player["Name"], str(ex))


def organize_db_data(adp_data):
    """
    organize_db_data Sorts and Categorize ADP data for draft board.

    :param adp_data: The dict with ADP and rankings
    :return A dict of key positions with sorted lists
    """

    # Init the return data
    db_data = {"qb": [], "rb": [], "wr": [], "te": []}

    # Build the position lists
    for player_k in adp_data:
        position_k = adp_data[player_k]["position"].lower()

        # Check the position is valid. Skips Kickers and Defense
        if position_k in {'def', 'pk'}:
            continue

        # Postion in Draft Board Dict
        if position_k in db_data:
            db_data[position_k].append(adp_data[player_k])
        else:
            logging.error("Position %s not found", position_k)

    # Sork the position lists
    for position_k in db_data:
        db_data[position_k] = sorted(db_data[position_k], key=lambda d: d["adp"])

    return db_data


def generate_html_v1(datamap, draft_board_data):
    """
    generate_html_v1 Version 1 of the HTML draftboard file
    """

    # Setup the jinja2 Environment
    environment = Environment(loader=FileSystemLoader("./templates/"))
    template = environment.get_template("draftboard.html")

    content = template.render(datamap=datamap, draft_board_data=draft_board_data)
    file_name = "./files/"
    file_name += f"db_{datamap['year']}_{datamap['scoring_format']}_{datamap['player_count']}.html"
    with open(file_name, mode="w", encoding="utf-8") as message:
        message.write(content)


def main():
    """
    main The Main function of the script
    """

    # set the logging output
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    # load the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-sf', '--scoring_format', help="the scoring format of ADP data",
                        choices=SCORE_FORMATS, required=True, metavar="<scoring_format>")
    parser.add_argument('-pc', '--player_count', help="the fantasy players of ADP data",
                        choices=TEAMS, required=True, metavar="<player_count>")
    parser.add_argument('-cc', '--clear_cache', help="clears the cached data", action='store_true')

    args = parser.parse_args()

    # setup the ff config data
    datamap = {
        "adp_base_url": "https://fantasyfootballcalculator.com/api/v1/adp",
        "scoring_format": args.scoring_format,
        "player_count": args.player_count,
        "year": datetime.now().year
    }

    run_info = f"{datamap['scoring_format']}_{datamap['player_count']}_{datamap['year']}"
    export_json = f"./files/draft_board_data_{run_info}.json"
    adp_data = {}

    # Check for the Cache file to exist. Load if so.
    if os.path.isfile(export_json) and args.clear_cache is False:
        logging.error("======= LOADING DATA FROM CACHE (clear with flag -cc) =======")
        with open(export_json, "r", encoding="utf-8") as db_f:
            adp_data = json.load(db_f)
    else:
        # Get the ADP data to dict
        adp_data = get_adp_data(datamap)

        # Merge in Player Rankings
        add_player_rankings(datamap, adp_data)

        # Save out the data to file
        with open(export_json, "w", encoding="utf-8") as db_f:
            db_f.write(json.dumps(adp_data, indent=4))

    # Build the draft board data
    draft_board_data = organize_db_data(adp_data)

    # Generate the HTML output
    generate_html_v1(datamap, draft_board_data)


if __name__ == "__main__":
    main()
