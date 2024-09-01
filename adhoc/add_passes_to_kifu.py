from tabnanny import verbose

import click
import os
import subprocess
import json
import logging
from sgfmill import sgf
import sys

KATAGO_DIR = r'C:\Users\User\.katrain'
KATAGO_EXECUTABLE = 'katago-v1.13.0-opencl-windows-x64.exe'
KATAGO_MODEL = r'kata1-b18c384nbt-s9131461376-d4087399203.bin.gz'
KATAGO_CONFIG = 'analysis_config.cfg'


def check_katago_tuning():
    tuning_file = os.path.join(KATAGO_DIR, 'KataGoData', 'opencltuning',
                               'tune11_gpuNVIDIAGeForceRTX3070LaptopGPU_x19_y19_c384_mv14.txt')
    return os.path.exists(tuning_file)


def get_tuning_command():
    return f'{os.path.join(KATAGO_DIR, KATAGO_EXECUTABLE)} benchmark -model {os.path.join(KATAGO_DIR, KATAGO_MODEL)} -config {os.path.join(KATAGO_DIR, KATAGO_CONFIG)} -tune'


class KataGoAnalyzer:
    def __init__(self):
        logging.debug("Initializing KataGoAnalyzer")
        self.process = subprocess.Popen(
            [os.path.join(KATAGO_DIR, KATAGO_EXECUTABLE), "analysis", "-model", os.path.join(KATAGO_DIR, KATAGO_MODEL),
             "-config", os.path.join(KATAGO_DIR, KATAGO_CONFIG)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        logging.debug("KataGoAnalyzer initialized")

    def analyze(self, query):
        logging.debug(f"Analyzing query: {query}")
        self.process.stdin.write(json.dumps(query) + "\n")
        self.process.stdin.flush()
        response = self.process.stdout.readline().strip()
        logging.debug(f"Received response (truncated): {response[:200]}")
        return response

    def close(self):
        logging.debug("Closing KataGoAnalyzer")
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait(timeout=0.2)
        logging.debug("KataGoAnalyzer closed")


def setup_logger(verbose=True):
    """Sets up logging to both console and file."""
    # Create a logger object
    logger = logging.getLogger()

    # Set the logging level based on the verbose flag
    logger.setLevel(logging.DEBUG if verbose else logging.WARNING)

    # Create handlers: one for console (stderr) and one for file
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('analysis.log', mode='w')  # Log file will be named 'analysis.log'

    # Set the logging level for handlers
    console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    file_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add both handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logging.debug("Logger initialized")


def process_sgf(file_path):
    logging.info(f"Processing SGF file: {file_path}")
    with open(file_path, 'rb') as f:
        game = sgf.Sgf_game.from_bytes(f.read())

    logging.debug(f"SGF file content: {game.serialise()}")  # Log the SGF content after reading it

    board_size = game.get_size()
    komi = game.get_komi() or 7.5
    logging.debug(f"Board size: {board_size}, Komi: {komi}")

    analyzer = KataGoAnalyzer()

    try:
        moves = []
        for node in game.get_main_sequence():
            color, move = node.get_move()
            move_number = len(moves) + 1
            logging.debug(f"Processing move {move_number}: {color} {move}")
            logging.debug(f"Processing node: {node}")
            logging.debug(f"Extracted move: color={color}, move={move}")

            if color is None or move is None:
                logging.warning(f"Skipping node with no color or move: {node}")
                continue

            moves.append([color.upper(), f"{chr(65 + move[1])}{board_size - move[0]}"])

            current_query = {
                "id": "current",
                "moves": moves,
                "rules": "tromp-taylor",
                "komi": komi,
                "boardXSize": board_size,
                "boardYSize": board_size,
                "analyzeTurns": [len(moves)]
            }

            logging.debug(f"Sending query to KataGo: {current_query}")  # Added debug statement
            current_analysis = analyzer.analyze(current_query)

            pass_query = current_query.copy()
            pass_query["id"] = "pass"
            pass_query["initialPlayer"] = "W" if color.upper() == "B" else "B"

            logging.debug(f"Sending pass query to KataGo: {pass_query}")  # Added debug statement
            pass_analysis = analyzer.analyze(pass_query)

            if current_analysis and pass_analysis:
                logging.debug(f"Raw current_analysis response (truncated): {current_analysis[:100]}")
                logging.debug(f"Raw pass_analysis response (truncated): {pass_analysis[:100]}")

                try:
                    current_data = json.loads(current_analysis)
                    pass_data = json.loads(pass_analysis)
                    current_score = current_data['rootInfo']['scoreLead']
                    pass_score = pass_data['rootInfo']['scoreLead']
                    comment = (f"Current Score: {'B' if current_score > 0 else 'W'}+{abs(current_score):.1f}\n"
                               f"Pass Score: {'B' if pass_score > 0 else 'W'}+{abs(pass_score):.1f}")
                    node.set("C", comment)
                    logging.debug(f"Added comment to node: {comment}")
                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Error processing KataGo analysis: {str(e)}")
            else:
                logging.warning(f"No analysis received for move: {move}")
    finally:
        analyzer.close()

    logging.info("SGF processing completed")
    return game


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--verbose/--no-verbose', default=True, show_default=True, help="Increase output verbosity")
def add_passes_to_kifu(input_file, output_file, verbose):
    """Add KataGo analysis to a kifu file."""
    setup_logger(verbose)

    if not check_katago_tuning():
        click.echo("It appears this is the first time running KataGo on this system.")
        click.echo("KataGo needs to be tuned for your GPU before it can be used.")
        click.echo("Please run the following command in your terminal:")
        click.echo("\n" + get_tuning_command() + "\n")
        click.echo("This process may take several minutes. Once completed, run this script again.")
        return

    logging.info(f"Processing {input_file}...")

    processed_game = process_sgf(input_file)
    with open(output_file, 'wb') as f:
        f.write(processed_game.serialise())

    logging.info(f"Processed SGF written to {output_file}")


if __name__ == "__main__":
    add_passes_to_kifu()