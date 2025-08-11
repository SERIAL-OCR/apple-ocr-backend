# iPad Serial Number Matcher

The iPad Serial Number Matcher is a Python script that reads serial numbers from iPad devices and matches them against leasing agreements. It helps in tracking and managing iPads by associating them with their respective schools and statuses.

## Features

- OCR-based serial number extraction: The script uses Optical Character Recognition (OCR) to extract serial numbers from images of iPad devices.
- Matching against leasing agreements: It matches the extracted serial numbers against a list of serial numbers from leasing agreements stored in CSV files.
- Updating CSV files: If a match is found, the script allows updating the status and school associated with the serial number in the corresponding CSV file.
- Duplication check: It checks if a serial number already has a school and status, and prompts the user to update the values if desired.
- Serial number obfuscation: Before matching, the script replaces characters in the extracted serial numbers with similar-looking characters to handle OCR errors.

## Prerequisites

Make sure you have the following prerequisites installed on your system:

- Python (version 3.6 or higher)
- OpenCV (opencv-python)
- Tesseract OCR (pytesseract)
- Numpy (numpy)

## Installation

1. Clone this repository to your local machine.
2. Install the required Python packages by running the following command:
   `pip install -r requirements.txt`
3. Make sure Tesseract OCR is installed and set up correctly.
4. Install the OpenCV library using the command mentioned in the prerequisites.


## Usage

1. Clone the repository or download the script.
2. Install the required dependencies using `pip install -r requirements.txt`.
3. Place the CSV files containing the serial numbers in the `agreements` folder. The CSV filenames should be in the following format: `{agreement_number}_{date}.csv`. For example, `12345-001_31-07-23.csv` or `23456-001_31-08-23.csv`. The date in the filename represents the expiry of the agreement.
4. Run the script using the command: `python main.py`.
5. A webcam feed window will open, and the script will start capturing frames.
6. When a serial number is recognized and matched against the CSV files, the script will prompt you to input the status and school information for that serial number.
7. Enter the corresponding values and press Enter.
8. If the expiry date of the agreement is read correctly, a yellow message will be printed indicating that the serial number needs to be returned by that date.
9.  The script will continue capturing and processing frames until you press 'q' to quit.

Note: Make sure the webcam is properly configured and accessible by OpenCV. Adjust the `camera_index` variable in the script if necessary.

## Usage

1. Prepare the leasing agreement CSV files:
- Create CSV files containing the serial numbers, schools, and statuses of leased iPads. The files should have the following format:

  ```
  Serial Number, Returned, School, Status
  ABC123456789, Returned, School A, Working
  DEF987654321, Returned, School B, Broken
  ```

- Place the CSV files in a folder and note down the folder path.

2. Update the script:
- Open the script file (`main.py`) in a text editor.
- Modify the script variables as per your requirements:
  - `camera_index`: Set the camera index for capturing frames from the webcam feed. The default value is `1`, which corresponds to the second camera connected to your system.
  - `folder_path`: Set the folder path where the leasing agreement CSV files are located.
  - Adjust any other variables or functionality in the script as needed.

3. Run the script:
- Open a terminal and navigate to the project directory.
- Run the following command:

  ```
  python main.py
  ```

- The script will start capturing frames from the webcam feed and perform OCR on those frames to extract serial numbers.
- It will match the extracted serial numbers against the leasing agreement CSV files and prompt for updates if a match is found.

4. Follow the on-screen prompts:
- When a serial number is found and matched against a leasing agreement, the script will display the details of the matched serial number and prompt for further actions.
- You can choose to update the status and school associated with the serial number, or skip the update.
- After the prompt, enter the corresponding option (`y` or `n`) and press Enter.

5. Exit the script:
- To exit the script, press `q` on the keyboard.
- The script will release the webcam and close all windows.

## Customization

- You can modify the number of threads by updating the `max_threads` variable in the script to match your system capabilities.
- Adjust the camera index (`camera_index`) if you're using a different webcam.
- Customize the initial values for `previous_status` and `previous_school` in the script.
- Customize the list of school names by updating the `schools` list in the script.

## Notes

- Ensure that the webcam is connected and working properly before running the script.
- Make sure the lighting conditions and camera focus are suitable for capturing clear images of the iPad serial numbers.
- Adjust the `max_threads` variable in the script to set the maximum number of threads used for processing frames. Increase the value if you have a more powerful system capable of handling more threads.


## Limitations

- The accuracy of serial number extraction depends on the quality of the captured frames and the performance of the OCR engine. Ensure clear and well-lit images for better results.
- OCR errors can occur due to various factors, such as image quality, font variations, or noise. The script tries to handle some common OCR errors by replacing characters with similar-looking characters before matching them against the leasing agreements.
- The script assumes that the leasing agreement CSV files are in the specified format. Make sure the CSV files are correctly formatted with the required columns.
- The script uses multi-threading to improve performance by processing frames concurrently. The `max_threads` variable controls the maximum number of threads used. Adjust this value according to your system capabilities.

## Acknowledgements

The script was developed based on the OpenAI ChatGPT language model and utilizes the following libraries:

- OpenCV: https://opencv.org
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract

## Troubleshooting

- If the script encounters any issues or errors, please make sure you have the necessary dependencies installed correctly and that your webcam is functioning properly.
- Ensure that the correct camera index is specified (`camera_index`) if you have multiple cameras connected to your system.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
