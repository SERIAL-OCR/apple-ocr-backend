import os
import cv2
import csv
import pytesseract
import re
import random
import datetime
import winsound
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from time import sleep

# Set the maximum number of threads
max_threads = 8  # Adjust this value as per your system capabilities

# Camera Index
camera_index = 1

# Set initial values
previous_status = 1 # Set the initial previous status value
previous_school = 11  # Set the initial previous school value

# Specify the folder path where the CSV files are located
folder_path = "./agreements"

# Initialize an empty list to store the CSV files
serial_numbers = []

# Initialize an empty set to store invalid serial number reads.
invalid_serial_numbers = set()

# Initialize an empty set to store the matched serial numbers
matched_serial_numbers = set()

# Lock to synchronize access to the CSV files
csv_lock = Lock()

# Counter for Found serialnumbers
serial_count = 0

# Function to load the serial numbers from the CSV files
def load_serial_numbers():
    global serial_count

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".csv"):  # Check if the file is a CSV file
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, 'r') as csv_file:
                reader = csv.reader(csv_file)
                next(reader)  # Skip the header row if it exists
                for row in reader:
                    serial_number = row[0]
                    serial_numbers.append(f"{file_name}, {serial_number}")

                    if "Ja" in row:
                        serial_count += 1

    print(f"Lastet {len(serial_numbers)} serienummer, hvorav {serial_count} er funnet")

# Function to extract the serial number from the recognized text
def extract_serial_number(text):
    global invalid_serial_numbers
    # Define a regular expression pattern to match the serial number
    pattern = r'Serial([:,.])?\s?([A-Z0-9]{12})'

    # Search for the pattern in the recognized text
    match = re.search(pattern, text)

    if match:
        # Extract the serial number from the matched group
        serial_number = match.group(2)

        serial_number = serial_number.replace('O', random.choice(['0', '9', 'O', 'Q']))
        serial_number = serial_number.replace('I', random.choice(['1', 'I']))
        serial_number = serial_number.replace('G', random.choice(['G', '6']))
        serial_number = serial_number.replace('S', random.choice(['5', '3', 'S', '8', '9']))

        print(f"Recognized pattern: {serial_number}")

        # Check if the recognized serial number matches against the CSV files
        for entry in serial_numbers:
            file_name, entry_serial_number = entry.split(", ")
            if serial_number == entry_serial_number:
                print(f"\033[1;32mSerienummer funnet: {serial_number} i filen {file_name}\033[0m")
                file_path = os.path.join(folder_path, file_name)

                if serial_number not in invalid_serial_numbers:
                    confirm_serial = input(f"Stemmer \033[1;32m{serial_number}\033[0m med serienummeret på enheten? [y/n]: ")
                    if confirm_serial.lower() == 'y':
                        invalid_serial_numbers = set()
                        # Check if the serial number already has a school and a status
                        existing_status, existing_school = get_existing_school_and_status(file_path, serial_number)

                        if existing_school and existing_status:
                            print(f"Serienummer \033[1;32m{serial_number}\033[0m finnes allerede med følgende verdier:")
                            print(f"Skole: \033[1;32m{existing_school}\033[0m")
                            print(f"Status: \033[1;32m{existing_status}\033[0m")

                            update_choice = input("Ønsker du å oppdatere verdiene? [y/n] (Standard: n): ")
                            if update_choice.lower() == "y":
                                status = input_status()
                                school = input_school()
                                
                                update_csv_file(file_path, serial_number, status, school)
                                #matched_serial_numbers.add(serial_number)
                                winsound.Beep(1000, 100)  # Play a beep sound (1000 Hz for 100 ms)
                                sleep(2)
                                return
                            else:
                                update_csv_file(file_path, serial_number, existing_status, existing_school)
                                winsound.Beep(1000, 100)  # Play a beep sound (1000 Hz for 100 ms)
                                sleep(2)
                                return
                        else:
                            # Prompt the user for the status value
                            status = input_status()
                            school = input_school()
                        
                            
                            update_csv_file(file_path, serial_number, status, school)
                            #matched_serial_numbers.add(serial_number)
                            winsound.Beep(1000, 100)  # Play a beep sound (1000 Hz for 100 ms)
                            sleep(2)

                    else:
                        print(f"{serial_number} lagt til midlertidig karanteneliste")
                        invalid_serial_numbers.add(serial_number)

def get_existing_school_and_status(file_path, serial_number):
    with csv_lock:
        with open(file_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            next(reader)  # Skip the header row if it exists
            for row in reader:
                if row[0] == serial_number:
                    if len(row) >= 4:  # Check if the row has school and status values
                        return row[2], row[3]  # Return the school and status
                    else:
                        return None, None  # No school and status found for the serial number

    return None, None  # Serial number not found in the file


# Function to update the CSV file with the "Ja" value
def update_csv_file(file_path, serial_number, status, school):
    global serial_count

    with csv_lock:
        with open(file_path, 'r') as csv_file:
            rows = list(csv.reader(csv_file))
            for row in rows[1:]:
                if row[0] == serial_number:
                    
                    if "Ja" not in row:
                        serial_count += 1
                        print(f"{serial_count}/{len(serial_numbers)} funnet totalt.")
                        row.append("Ja")

                    if len(row) >= 3 and row[2]:
                        row[2] = status
                    else:
                        row.append(status)

                    if len(row) >= 4 and row[3]:
                        row[3] = school
                    else:
                        row.append(school)

                    if len(row) >= 5 and row[4]:
                        if row[4] != "Ja":
                            row[4] = "Ja"
                    elif len(row) < 5:
                        row.append("Ja")
                    
                    
                                        
                    # Extract the date from the filename
                    date_match = re.search(r"_(\d{2}-\d{2}-\d{2})\.csv", file_path)
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            expiry_date = datetime.datetime.strptime(date_str, "%d-%m-%y")
                        except ValueError:
                            print(f"Invalid date format in filename: {file_path}")
                            continue
                    else:
                        print(f"No date found in filename: {file_path}")
                        continue

                    if expiry_date:
                        print(f"\033[33mSerienummer {serial_number} skal returneres {expiry_date.strftime('%d-%m-%Y')}\033[0m")

                    break

        with open(file_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(rows)

# Function to handle user input for the status column
def input_status():
    global previous_status

    status_mapping = {
        1: "Visuelt ok",
        2: "Knust"
    }

    status_input = input(f"Angi status (1 for Visuelt ok, 2 for Knust) [Standard: {status_mapping[previous_status]}]: ")

    # Validate the input
    status_number = int(status_input) if status_input.isdigit() else previous_status
    if status_number and status_number in status_mapping:
        status = status_mapping[status_number]

    # Update previous_status with the user input
    previous_status = status_number

    return status

# Function to handle user input for the school column
def input_school():
    global previous_school

    schools = {
        1: "Akkarfjord",
        2: "Baksalen",
        3: "Breilia",
        4: "Fjordtun",
        5: "Forsøl",
        6: "Fuglenes",
        7: "Kvalsund",
        8: "Kokelv",
        9: "Reindalen",
        10: "VO",
        11: "Ukjent"
    }

    # Display the school options
    print("Velg skole:")
    for number, school in schools.items():
        print(f"{number}: {school}")

    # Prompt for user input
    school_prompt = f"Angi skole (1-{len(schools)}) [Standard: {schools[previous_school]}]: "
    school_input = input(school_prompt)

    # Validate the input
    school_number = int(school_input) if school_input.isdigit() else previous_school
    if school_number and school_number in schools:
        school = schools[school_number]

    # Update previous_school with the selected school
    previous_school = school_number

    return school


# Function to process a single frame from the webcam feed
def process_frame(frame):
    try:
        # Convert the frame to grayscale for OCR processing
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # Perform OCR on the captured frame
        text = pytesseract.image_to_string(frame_bgr)

        # Extract the serial number from the recognized text
        extract_serial_number(text)

        # Display the frame
        cv2.imshow('Webcam OCR', frame)
    except Exception as e:
        print("An exception occured: ", e)

# Function to capture frames from the webcam feed and process them
def capture_and_process_frames():
    camera = cv2.VideoCapture(camera_index)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    try:
        while True:
            # Capture frame-by-frame
            ret, frame = camera.read()

            # Process the frame
            process_frame(frame)

            # delay
            sleep(0.1)

            # Exit the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print("An exception occurred:", e)

    # Release the webcam and destroy windows
    camera.release()
    cv2.destroyAllWindows()

# Load the serial numbers from the CSV files
load_serial_numbers()

# Create a ThreadPoolExecutor with the specified maximum number of threads
executor = ThreadPoolExecutor(max_workers=max_threads)

# Start capturing and processing frames in a separate thread
executor.submit(capture_and_process_frames)

# Shutdown the executor
executor.shutdown()
