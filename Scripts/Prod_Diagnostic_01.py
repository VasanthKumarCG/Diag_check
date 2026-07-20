import csv
import re

def parse_log_file(log_file_path, output_csv_path):
    """
    Parses a diagnostic log file and extracts DTC information, saving it to a CSV file.

    Args:
        log_file_path (str): The path to the input log file.
        output_csv_path (str): The path where the output CSV file will be saved.
    """
    # This list will store all the extracted DTC data. Each item will be a dictionary.
    all_dtc_data = []
    # This set will store all unique environment data keys found across all DTCs.
    all_env_data_keys = set()

    # Variables to store the current ECU and DTC being processed.
    current_ecu = None
    current_dtc_info = {}

    # Regex patterns to extract information from log lines.
    # Matches lines like "ECU - TCU"
    ecu_pattern = re.compile(r"^ECU - (\w+)")
    # Matches lines like "DTC - 0x9026 - Sensor range fault"
    dtc_pattern = re.compile(r"^DTC - (0x[0-9A-Fa-f]+) - (.*)")
    # Matches lines with key-value pairs, like "Status - Active"
    kv_pattern = re.compile(r"^(.*?)\s*-\s*(.*)$")
    # Matches environment data lines, like "  Timestamp - 2026-05-27 20:32:00"
    env_data_pattern = re.compile(r"^\s{2}(.*?)\s*-\s*(.*)$")

    try:
        # Open the log file for reading.
        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            # Iterate over each line in the log file.
            for line in log_file:
                line = line.strip() # Remove leading/trailing whitespace

                # Check if the line defines an ECU.
                ecu_match = ecu_pattern.match(line)
                if ecu_match:
                    current_ecu = ecu_match.group(1)
                    # If we were processing a DTC, finalize it before moving to a new ECU.
                    if current_dtc_info:
                        all_dtc_data.append(current_dtc_info)
                    current_dtc_info = {"ECU Name": current_ecu} # Reset for new ECU
                    continue

                # Check if the line defines a DTC.
                dtc_match = dtc_pattern.match(line)
                if dtc_match:
                    # If we were processing a DTC, finalize it before starting a new one.
                    if current_dtc_info and "DTC Code" in current_dtc_info:
                        all_dtc_data.append(current_dtc_info)
                    # Start a new DTC entry.
                    current_dtc_info = {
                        "ECU Name": current_ecu,
                        "DTC Code": dtc_match.group(1),
                        "DTC Description": dtc_match.group(2)
                    }
                    continue

                # If we are currently processing a DTC, check for other key-value pairs.
                if current_dtc_info:
                    # Check for standard DTC details (Status, Occurrence, Aging, Priority).
                    kv_match = kv_pattern.match(line)
                    if kv_match:
                        key = kv_match.group(1).strip()
                        value = kv_match.group(2).strip()

                        # Map keys to consistent names for the CSV.
                        if key == "Status":
                            current_dtc_info["Status"] = value
                        elif key == "Occurrence Counter":
                            current_dtc_info["Occurrence Counter"] = value
                        elif key == "Aging Counter":
                            current_dtc_info["Aging Counter"] = value
                        elif key == "Priority":
                            current_dtc_info["Priority"] = value
                        # Check for Environment Data.
                        elif key == "Environment Data":
                            # Initialize an empty dictionary for environment data if it doesn't exist.
                            if "Environment Data" not in current_dtc_info:
                                current_dtc_info["Environment Data"] = {}
                        else:
                            # If it's an environment data field.
                            env_data_match = env_data_pattern.match(line)
                            if env_data_match:
                                env_key = env_data_match.group(1).strip()
                                env_value = env_data_match.group(2).strip()
                                current_dtc_info["Environment Data"][env_key] = env_value
                                # Add the environment data key to our set of all keys.
                                all_env_data_keys.add(env_key)


            # Add the last processed DTC if it exists.
            if current_dtc_info and "DTC Code" in current_dtc_info:
                all_dtc_data.append(current_dtc_info)

        # Define the standard headers.
        headers = ["ECU Name", "DTC Code", "DTC Description", "Status", "Occurrence Counter", "Aging Counter", "Priority"]
        # Add all unique environment data keys found to the headers.
        headers.extend(sorted(list(all_env_data_keys)))

        # Write the extracted data to a CSV file.
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            # Create a CSV writer object.
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            # Write the header row.
            writer.writeheader()
            # Write the data rows.
            for dtc_entry in all_dtc_data:
                # Prepare a row dictionary, ensuring all header fields are present.
                row_data = {header: "" for header in headers} # Initialize with empty strings
                row_data.update(dtc_entry) # Update with actual data

                # Handle nested Environment Data dictionary.
                env_data = dtc_entry.get("Environment Data", {})
                for env_key, env_value in env_data.items():
                    if env_key in headers: # Ensure the key is actually in our headers
                        row_data[env_key] = env_value
                
                # Remove the nested 'Environment Data' key itself from the row_data if it exists.
                row_data.pop("Environment Data", None)

                writer.writerow(row_data)

        print(f"Successfully parsed log file and saved data to {output_csv_path}")

    except FileNotFoundError:
        print(f"Error: The file {log_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- Script Execution ---
# Define the input log file path.
input_log_file = "Prod_Diagnostic_01.txt"
# Define the output CSV file path.
output_csv_file = "diagnostic_report.csv"

# Call the function to parse the log and generate the CSV.
parse_log_file(input_log_file, output_csv_file)