import os
import shutil
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def copy_and_rename_sgfs(source_directory, destination_directory):
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)
        logging.info(f"Created directory: {destination_directory}")

    logging.info(f"Searching for SGF files in {source_directory}")

    for root, _, files in os.walk(source_directory):
        for file in files:
            if file.endswith('.sgf'):
                source_file_path = os.path.join(root, file)
                destination_file_name = f"{uuid.uuid4()}.sgf"
                destination_file_path = os.path.join(destination_directory, destination_file_name)
                shutil.copy2(source_file_path, destination_file_path)
                logging.info(f"Copied {source_file_path} to {destination_file_path}")

# Directory containing the downloaded SGF files
source_dir = 'downloaded'

# Directory to save the renamed SGF files
destination_dir = 'sgf/raw'

copy_and_rename_sgfs(source_dir, destination_dir)
