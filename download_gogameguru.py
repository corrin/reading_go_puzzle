import os
import shutil
import uuid
import logging
from sgfmill import sgf

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://gogameguru.com/"


def add_source_url_to_sgf(source_file_path, destination_file_path, relative_path):
    try:
        with open(source_file_path, 'rb') as f:
            game = sgf.Sgf_game.from_bytes(f.read())

        root = game.get_root()
        source_url = BASE_URL + relative_path.replace('\\', '/').replace('.sgf', '')
        root.set('SO', source_url)  # Set the 'SO' (Source) property

        with open(destination_file_path, 'wb') as f:
            f.write(game.serialise())

        logging.info(f"Added source URL to {destination_file_path}")
    except Exception as e:
        logging.error(f"Error processing {source_file_path}: {str(e)}")
        # If there's an error, just copy the original file without modification
        shutil.copy2(source_file_path, destination_file_path)
        logging.info(f"Copied original file {source_file_path} to {destination_file_path}")


def copy_and_rename_sgfs(source_directory, destination_directory):
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)
        logging.info(f"Created directory: {destination_directory}")

    logging.info(f"Searching for SGF files in {source_directory}")

    for root, _, files in os.walk(source_directory):
        for file in files:
            if file.endswith('.sgf'):
                source_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_file_path, source_directory)
                destination_file_name = f"{uuid.uuid4()}.sgf"
                destination_file_path = os.path.join(destination_directory, destination_file_name)
                add_source_url_to_sgf(source_file_path, destination_file_path, relative_path)


# Directory containing the downloaded SGF files
source_dir = 'downloaded'

# Directory to save the renamed SGF files
destination_dir = 'sgf/raw'

copy_and_rename_sgfs(source_dir, destination_dir)