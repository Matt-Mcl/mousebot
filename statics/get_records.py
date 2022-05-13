import sys
import json
import pymongo
import requests

mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_map_records = mousebot_db['map_records']
mousebot_map_records.delete_many({})

# The ID of the spreadsheet.
SPREADSHEET_ID = '1l3D-tmUAgwqNPjR3qa1rKqNkNYImPLC3dhgHUD3gLjo'

directory = sys.argv[1]

with open(f"{directory}/config/config.json") as f:
    api_key = json.load(f)['GOOGLE_API_KEY']

sheets = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?key={api_key}").json()['sheets']

# Get all sheets, discarding Welcome, BL, Parkour Help
for s in sheets[1:-3]:
    title = s['properties']['title']
    results = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{title}'?key={api_key}").json()

    for i, row in enumerate(results['values']):
        try:
            code = row[1].strip()
            # If it is a code
            if code[0] == "@":
                if len(row) > 0:
                    for j in range(1, 6):
                        name = results['values'][i + j][2].strip()
                        time = results['values'][i + j][3].strip()
                        if len(name) > 0:
                            mousebot_map_records.insert_one({"category": title, "code": code, "name": name, "time": time[:-1]})
        except IndexError:
            pass
