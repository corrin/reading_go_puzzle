import json
import logging
import os
import signal
import subprocess
import sys
import time
import traceback

from datetime import datetime
from threading import Thread
from sgfmill import sgf
from sgfmill.boards import Board
from typing import Tuple, List, Union, Literal, Any, Dict

Color = Union[Literal["B"], Literal["W"]]
Move = Union[None, Literal["pass"], Tuple[int, int]]

KATAGO_DIR = r'C:\Users\User\.katrain'
KATAGO_EXECUTABLE = 'katago-v1.13.0-opencl-windows-x64.exe'
KATAGO_MODEL = r'kata1-b18c384nbt-s9131461376-d4087399203.bin.gz'
KATAGO_CONFIG = 'analysis_config.cfg'


def setup_logger():
    # Create a filename with a timestamp for the log file
    log_filename = f"katago_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Create a file handler to log all messages (DEBUG and above)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)  # Log all levels to the file

    # Create a stream handler to log only warnings and above to the console
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)  # Log only WARNING and above to the console

    # Set the same format for both handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # Get the root logger and set the level
    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, stream_handler])
    return


#
# def sgfmill_to_gtp(move: Move, board_size: int) -> str:
#     """Convert sgfmill move to GTP format (e.g., 'D4') for KataGo."""
#     if move is None or move == "pass":
#         return "pass"
#     y, x = move
#     return "ABCDEFGHJKLMNOPQRSTUVWXYZ"[x] + str(board_size - y)

def sgfmill_to_gtp(move: Move, board_size: int) -> str:
    """Convert sgfmill move to GTP format (e.g., 'D4') for KataGo."""
    if move is None or move == "pass":
        return "pass"
    y, x = move
    # Add 1 because SGF coordinates are 0-indexed, but GTP are 1-indexed
    return "ABCDEFGHJKLMNOPQRSTUVWXYZ"[x] + str(y + 1)


def katago_to_correct_gtp(move: str, board_size: int) -> str:
    """Convert KataGo's GTP format to correct GTP format."""
    if move.lower() == 'pass':
        return 'pass'

    # Convert column to the correct format
    col = move[0]
    row = int(move[1:])

    # Board columns in GTP format without 'I'
    columns = 'ABCDEFGHJKLMNOPQRST'[:board_size]
    col_index = columns.index(col)
    correct_col = columns[board_size - col_index - 1]  # Convert column

    # Convert row to the correct format
    correct_row = board_size - row + 1

    return f"{correct_col}{correct_row}"


class KataGo:
    def __init__(self, katago_path: str, config_path: str, model_path: str, additional_args: List[str] = []):
        self.query_counter = 0
        katago = subprocess.Popen(
            [katago_path, "analysis", "-config", config_path, "-model", model_path, *additional_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.katago = katago

        def printforever():
            while katago.poll() is None:
                data = katago.stderr.readline()
                time.sleep(0)
                if data:
                    print("KataGo: ", data.strip())
            data = katago.stderr.read()
            if data:
                print("KataGo: ", data.strip())

        self.stderrthread = Thread(target=printforever)
        self.stderrthread.start()

    def close(self):
        if self.katago:
            # Try to terminate gracefully
            self.katago.terminate()
            try:
                # Wait for up to 5 seconds for the process to terminate
                self.katago.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If it doesn't terminate within 5 seconds, force kill
                self.katago.kill()
                self.katago.wait()  # Ensure the process is fully closed

            # Close all pipes
            self.katago.stdin.close()
            self.katago.stdout.close()
            self.katago.stderr.close()

            self.katago = None
        logging.info("Closed KataGo instance")


def parse_sgf_file(file_path: str) -> Tuple[List[Tuple[Color, Move]], int, float, str]:
    """Parses an SGF file and returns the game moves, board size, komi, and rules."""
    with open(file_path, 'rb') as f:
        sgf_content = f.read()
    game = sgf.Sgf_game.from_bytes(sgf_content)

    root = game.get_root()
    board_size = game.get_size()
    komi = float(game.get_komi())
    try:
        rules = root.get("RU")
    except KeyError:
        rules = "Tromp-Taylor"  # Default to "Tromp-Taylor" if the property is not found
    if rules.lower() == 'ogs':
        rules = "Japanese"

    main_sequence = game.get_main_sequence()
    moves = []

    for node in main_sequence:
        color, move = node.get_move()
        if move is not None:
            moves.append((color.upper(), move))

    return moves, board_size, komi, rules


def run_katago_analysis(katago: KataGo, board_size: int, komi: float, moves: List[Tuple[Color, Move]],
                        rules: str) -> Dict:
    """Run KataGo analysis by sending a single query with all moves and return the raw response."""
    board = Board(board_size)

    # Initialize the board with all initial stones
    initial_stones = []
    for y in range(board_size):
        for x in range(board_size):
            color = board.get(y, x)
            if color:
                initial_stones.append((color.upper(), sgfmill_to_gtp((y, x), board_size)))

    # Prepare the full moves list for the query
    move_list = [(color, sgfmill_to_gtp(move, board_size)) for color, move in moves]

    # Construct the single query to KataGo with all moves
    query = {
        "id": str(katago.query_counter),
        "initialStones": initial_stones,
        "moves": move_list,
        "rules": rules,
        "komi": komi,
        "boardXSize": board_size,
        "boardYSize": board_size,
        "includePolicy": True,
        "minVisits": 2500,
        "maxVisits": 5000,
        "analyzeTurns": list(range(len(moves)))  # Analyze all turns
    }

    # Serialize the query to a single-line JSON string
    query_json = json.dumps(query, ensure_ascii=False)

    # Debug: Print the single-line query
    logging.info("Single-line Query to KataGo:")
    logging.info(query_json)
    # sys.exit(0) # temporarily quit here

    # Send the single-line query to KataGo
    katago.katago.stdin.write(query_json + "\n")
    katago.katago.stdin.flush()

    # Read and parse the response from KataGo
    line = katago.katago.stdout.readline().strip()
    katago_result = json.loads(line)

    # Debug: Print the response from KataGo
#    logging.debug(f"KataGo response: {katago_result}")

    return katago_result

def process_katago_response(raw_katago_results, moves, board_size):
    results = []

    try:
        logging.info("Starting to process KataGo response")
        logging.debug(f"Moves: {moves}")
        logging.debug(f"Board size: {board_size}")

        katago_data = raw_katago_results
        logging.debug(f"Parsed KataGo data: {katago_data}")

        if not isinstance(katago_data, dict):
            logging.error(f"KataGo data is not a dictionary. Type: {type(katago_data)}")
            return results

        move_infos = katago_data.get('moveInfos')
        logging.debug(f"Move infos: {move_infos}")

        if not isinstance(move_infos, list):
            logging.error(f"moveInfos is not a list. Type: {type(move_infos)}")
            return results

        for move_index, move_data in enumerate(move_infos):
            logging.debug(f"Processing move index {move_index}: {move_data}")

            katago_move = move_data.get('move')
            score = move_data.get('scoreLead')
            score_stdev = move_data.get('scoreStdev')
            move = katago_to_correct_gtp(katago_move, board_size)

            logging.debug(f"Move: {move}, Kata: {katago_move}, Score: {score}, Score StDev: {score_stdev}")

            if move:
                formatted_move = move
                move_number = move_index + 1  # Move numbers typically start from 1
                score_accuracy = score_stdev if score_stdev is not None else float('nan')
                result = (move_number, formatted_move, score, score_accuracy)
                results.append(result)
                logging.debug(f"Appended result: {result}")
            else:
                logging.warning(f"Move data missing 'move' key: {move_data}")

    except Exception as e:
        logging.error(f"An unexpected error occurred while processing KataGo response: {e}")
        logging.error(traceback.format_exc())

    logging.debug(f"Final results: {results}")
    return results


if __name__ == "__main__":
    # Setup code, parse SGF, etc.
#    sgf_file_path = "/Users/User/Downloads/251520.sgf"
    sgf_file_path = "/Users/User/Downloads/12691-topazg-fingolfin.sgf"
    moves, board_size, komi, rules = parse_sgf_file(sgf_file_path)  # Now returns rules as well

    katago_path = os.path.join(KATAGO_DIR, KATAGO_EXECUTABLE)
    katago_model = os.path.join(KATAGO_DIR, KATAGO_MODEL)
    katago_config = os.path.join(KATAGO_DIR, KATAGO_CONFIG)
    katago = KataGo(katago_path, katago_config, katago_model)
    setup_logger()

    try:
        # Run analysis and get the raw response
        raw_katago_results = run_katago_analysis(katago, board_size, komi, moves, rules)
        logging.debug("Raw katago results")
        logging.debug(raw_katago_results)

        # Process the response to get formatted results
        processed_results = process_katago_response(raw_katago_results, moves, board_size)

        logging.debug("Processed katago results")
        logging.debug(processed_results)
        # Print or further process katago_results
        for move_number, move, score, score_sd in processed_results:
            leader = 'W' if score > 0 else 'B'
            abs_score = abs(score)
            print(f"{move_number}. {move}: {leader}+{abs_score:.1f} ±{score_sd:.1f}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    finally:
        if katago:
            katago.close()
