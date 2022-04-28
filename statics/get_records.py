from __future__ import print_function
import pymongo

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_map_records = mousebot_db['map_records']
mousebot_map_records.delete_many({})


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of the spreadsheet.
SPREADSHEET_ID = '1l3D-tmUAgwqNPjR3qa1rKqNkNYImPLC3dhgHUD3gLjo'


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('../config/token.json'):
        creds = Credentials.from_authorized_user_file('../config/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../config/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('../config/token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        spreadsheet = service.spreadsheets()
        sheets = spreadsheet.get(spreadsheetId=SPREADSHEET_ID).execute()

        # Get all sheets, discarding Welcome, BL, Parkour Help
        for s in sheets['sheets'][1:-3]:
            title = s['properties']['title']
            results = spreadsheet.values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{title}'").execute()
            for i, row in enumerate(results['values']):
                if (i + 7) % 8 == 0:
                    try:
                        if len(row) > 0:
                            code = row[1].strip()
                            for j in range(1, 6):
                                name = results['values'][i + j][2].strip()
                                time = results['values'][i + j][3].strip()
                                if len(name) > 0:
                                    mousebot_map_records.insert_one({"category": title, "code": code, "name": name, "time": time})
                    except IndexError:
                        pass

    except HttpError as err:
        print(err)


if __name__ == '__main__':
    main()
