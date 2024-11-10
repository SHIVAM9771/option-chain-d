import json
import time
import os
from datetime import datetime
from Urls import Urls  # Import the module for fetching data (assuming Urls.py exists)
from pymongo import MongoClient
import gridfs

import os
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("MONGO_URI")
client = MongoClient(connection_string)
# MongoDB setup
# client = MongoClient("mongodb://localhost:27017/")
db = client["Percentage"]
collection = db["oc_data"]
fs = gridfs.GridFS(db)  # Initialize GridFS


def save_data(expiry, data, timestamp, current_date):
    if data:
        data_bytes = json.dumps(data).encode("utf-8")

        file_id = fs.put(data_bytes)

        # Find an existing document by expiry
        existing_doc = collection.find_one({"expiry": expiry})

        if existing_doc:
            # Add the current_date to dateList if it's not already present
            if current_date not in existing_doc.get("dateList", []):
                collection.update_one(
                    {"expiry": expiry},
                    {
                        "$addToSet": {"dateList": current_date}
                    },  # Add the new date to the array
                )

            # Update or set the file_id for the specific timestamp under the current date
            collection.update_one(
                {"expiry": expiry},
                {"$set": {f"day.{str(current_date)}.{str(timestamp)}": file_id}},
            )
        else:
            # Insert a new document if expiry doesn't exist
            collection.insert_one(
                {
                    "expiry": expiry,
                    "dateList": [current_date],
                    "day": {str(current_date): {str(timestamp): file_id}},
                }
            )
    else:
        print("No data to save.")


def get_current_timestamp():
    """
    Get the current date and time as UNIX timestamps.
    """
    current_date = int(
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    )
    current_time = int(datetime.now().timestamp())
    return current_date, current_time


def get_data(expiry, symbol=13, seg=0):
    """
    Fetch data for the given expiry and save it to MongoDB at specified intervals.
    """
    # Load any existing data from the JSON file (optional for additional local storage)
    data = {}

    while True:
        now = datetime.now()
        curr_time = now.strftime("%H:%M")

        # Operational hours check
        if "00:00" <= curr_time <= "24:00":
            if "09:07" <= curr_time <= "09:15":
                print("Waiting for 10 seconds before the next fetch...")
                time.sleep(10)
                continue

            try:
                # Fetch data from URL using parameters
                fetched_data = Urls.fetch_data(symbol=symbol, seg=seg, exp=expiry)

                if (
                    not fetched_data
                    or "data" not in fetched_data[0]
                    or "oc" not in fetched_data[0]["data"]
                ):
                    print("Invalid data structure received.")
                    continue

                # Get the current date and time as UNIX timestamps
                current_date, current_time = get_current_timestamp()

                # Initialize the data structure for the current expiry if not present
                if str(expiry) not in data:
                    data[str(expiry)] = {}

                if str(current_date) not in data[str(expiry)]:
                    data[str(expiry)][str(current_date)] = {}

                # Prepare the structure for the current time entry
                data[str(expiry)][str(current_date)][str(current_time)] = {
                    "ce_data": {},
                    "pe_data": {},
                }

                # Define the keys of interest
                keys_of_interest = [
                    "OI_percentage",
                    "oichng_percentage",
                    "vol_percentage",
                ]

                # Extract relevant data for CE and PE
                for key, value in fetched_data[0]["data"]["oc"].items():
                    ce_data = value.get("ce", {})
                    pe_data = value.get("pe", {})

                    # Filter only the keys of interest from CE and PE data
                    data[str(expiry)][str(current_date)][str(current_time)]["ce_data"][
                        key
                    ] = {k: ce_data.get(k) for k in keys_of_interest}
                    data[str(expiry)][str(current_date)][str(current_time)]["pe_data"][
                        key
                    ] = {k: pe_data.get(k) for k in keys_of_interest}

                # Save the updated data back to MongoDB
                save_data(
                    expiry,
                    data[str(expiry)][str(current_date)][str(current_time)],
                    current_time,
                    current_date,
                )

                print(
                    f"Data successfully saved to MongoDB at timestamp {current_time} for Modals"
                )

                # Exit conditions
                # if curr_time == "15:35" or curr_time == "19:01":
                #     print("Ending data fetching process.")
                #     break

            except Exception as e:
                print(f"An error occurred: {e}")

            # Sleep for 3 seconds before the next fetch
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                print("Process interrupted by user.")
                break


# Main execution
if __name__ == "__main__":
    get_data(1416076200, 294, 5)  # Replace with actual expiry timestamp as needed
