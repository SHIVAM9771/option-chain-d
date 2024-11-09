import gridfs
import json
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId to handle the conversion
from gridfs.errors import NoFile

# Assuming you've already set up the connection and fs (GridFS)
client = MongoClient("mongodb://localhost:27017/")
db = client["Percentage"]
collection = db["oc_data"]
fs = gridfs.GridFS(db)  # Initialize GridFS

# Sample query to fetch data by expiry and date
expiry = 1415989800  # Example expiry timestamp
date = 1731004200  # Example date to query for


# Function to process the data
def process_data(expiry, date):
    try:
        # Fetch data for the specified expiry
        data = collection.find_one(
            {
                "expiry": expiry,
                f"day.{date}": {
                    "$exists": True
                },  # Ensure that the date exists in the 'day' field
            },
            {
                "_id": 1,  # Include the document ID
                "expiry": 1,  # Include expiry
                "dateList": 1,  # Include date list
                f"day.{date}": 1,  # Include the specific day's data
            },
        )

        if not data:
            print(f"No data found for expiry: {expiry}")
            return

        # Check if the date exists in the 'day' field
        if str(date) not in data["day"]:
            print(
                f"Error: Date {date} not found in the 'day' field under expiry {expiry}."
            )
            print(f"Available keys in 'day' are: {list(data['day'].keys())}")
            return

        retrieved_data = {}

        # Iterate over the day data for the specified date
        day_data = data["day"][str(date)]

        for timestamp, file_id in day_data.items():
            # print(f"Processing timestamp: {timestamp}")

            # Ensure the file_id is in the correct format (ObjectId)
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)  # Convert string file_id to ObjectId
            elif isinstance(file_id, bytes):
                file_id = ObjectId(file_id.decode("utf-8"))  # Convert bytes to ObjectId

            try:
                # Attempt to retrieve the file data from GridFS
                file_data = fs.get(file_id).read()

                # Process file data (e.g., convert it to JSON)
                json_data = json.loads(file_data.decode("utf-8"))
                retrieved_data[timestamp] = json_data
                print(f"Data for timestamp {timestamp} successfully loaded.")

            except NoFile:
                print(f"Error: File with ID {file_id} not found in GridFS.")
                continue  # Skip this timestamp
            except Exception as e:
                print(f"Error processing file for timestamp {timestamp}: {str(e)}")
                continue  # Skip to the next timestamp

        new_data = {
            "expiry": data["expiry"],
            "dateList": data["dateList"],
            "day": {date: retrieved_data},
        }

        with open("data.json", "w") as file:
            json.dump(new_data, file, indent=4)

    except Exception as e:
        print(f"An error occurred: {str(e)}")


# Call the function to process data for the specified expiry and date
process_data(expiry, date)