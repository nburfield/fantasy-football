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
import requests


SCORE_FORMATS = ["ppr", "half-ppr", "standard"]
TEAMS = ["8", "10", "12", "14"]


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
                key = player["name"].replace(' ', '_').lower()
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
                key = player["Name"].replace(' ', '_').lower()

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

    args = parser.parse_args()

    # setup the ff config data
    datamap = {
        "adp_base_url": "https://fantasyfootballcalculator.com/api/v1/adp",
        "scoring_format": args.scoring_format,
        "player_count": args.player_count,
        "year": datetime.now().year
    }

    # Get the ADP data to dict
    adp_data = get_adp_data(datamap)

    # Merge in Player Rankings
    add_player_rankings(datamap, adp_data)

    # Save out the data to file
    with open("files/draft_board_data.json", "w", encoding="utf-8") as db_f:
        db_f.write(json.dumps(adp_data))


if __name__ == "__main__":
    main()
