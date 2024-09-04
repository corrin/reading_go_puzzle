import click
import json
import logging
import os
import shlex
import subprocess
import time
import traceback

from datetime import datetime
from sgfmill import sgf
from threading import Thread
from tqdm import tqdm
from typing import Tuple, List, Union, Literal

Color = Union[Literal["B"], Literal["W"]]
Move = Union[None, Literal["pass"], Tuple[int, int]]

KATAGO_DIR = r'C:\Users\User\.katrain'
KATAGO_EXECUTABLE = 'katago-v1.13.0-opencl-windows-x64.exe'
KATAGO_MODEL = r'kata1-b18c384nbt-s9131461376-d4087399203.bin.gz'
KATAGO_CONFIG = 'analysis_config.cfg'


def setup_logger():
    log_filename = f"katago_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    logging.debug("Logger setup complete")


def sgfmill_to_gtp(move: Move, board_size: int) -> str:
    if move is None or move == "pass":
        return "pass"
    y, x = move
    return "ABCDEFGHJKLMNOPQRSTUVWXYZ"[x] + str(y + 1)


class KataGo:
    def __init__(self, katago_path: str, config_path: str, model_path: str):
        self.katago_path = katago_path
        self.config_path = config_path
        self.model_path = model_path
        self.query_counter = 0
        self.katago = None
        self.stderrthread = None

        # Run tuning if it hasn't been done before
        self.run_tuning_if_needed()

        # Initialize KataGo
        self.initialize_katago()

    def run_tuning_if_needed(self):
        # Check if tuning file exists
        tuning_file = os.path.join(os.path.dirname(self.katago_path), "KataGoData", "opencltuning", "tune_results.bin")

        if os.path.exists(tuning_file):
            logging.info("Tuning file already exists. Skipping tuning.")
            return

        logging.info("Tuning file not found. Running KataGo tuner...")

        tuning_command = [
            self.katago_path,
            "tuner",
            "-config", self.config_path,
            "-model", self.model_path
        ]

        # Log the command being run
        command_str = ' '.join(shlex.quote(str(arg)) for arg in tuning_command)
        logging.info(f"Executing command: {command_str}")

        result = subprocess.run(tuning_command, capture_output=False)

        if result.returncode != 0:
            raise Exception(f"KataGo tuning failed: {result.stderr}")

        # Log the output of the tuning process
        logging.info("Tuning process output:")
        logging.info(result.stdout)
        if result.stderr:
            logging.warning("Tuning process stderr:")
            logging.warning(result.stderr)

        # Create the tuning file to mark that tuning has been done
        os.makedirs(os.path.dirname(tuning_file), exist_ok=True)
        with open(tuning_file, 'w') as f:
            f.write("Tuning completed")

        logging.info("Tuning completed and marker file created.")

    def initialize_katago(self):
        katago_command = [
            self.katago_path,
            "analysis",
            "-model", self.model_path,
            "-config", self.config_path
        ]

        self.katago = subprocess.Popen(
            katago_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        logging.info("KataGo process initialized")
        self.stderrthread = Thread(target=self.printforever)
        self.stderrthread.start()

    def printforever(self):
        while self.katago and self.katago.poll() is None:
            data = self.katago.stderr.readline()
            if data:
                print("KataGo: ", data.strip())
            time.sleep(0.1)  # Small sleep to prevent busy-waiting
        if self.katago:
            data = self.katago.stderr.read()
            if data:
                print("KataGo: ", data.strip())

    def close(self):
        if self.katago:
            self.katago.terminate()
            try:
                self.katago.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.katago.kill()
                self.katago.wait()
            self.katago.stdin.close()
            self.katago.stdout.close()
            self.katago.stderr.close()
            self.katago = None
        logging.info("Closed KataGo instance")


def parse_sgf_file(file_path: str) -> Tuple[List[Tuple[Color, Move]], int, float, str]:
    with open(file_path, 'rb') as f:
        sgf_content = f.read()
    game = sgf.Sgf_game.from_bytes(sgf_content)

    root = game.get_root()
    board_size = game.get_size()
    komi = float(game.get_komi())
    try:
        rules = root.get("RU")
    except KeyError:
        rules = "Tromp-Taylor"
    if rules.lower() == 'ogs':
        rules = "Japanese"

    main_sequence = game.get_main_sequence()
    moves = []

    for node in main_sequence:
        color, move = node.get_move()
        if move is not None:
            moves.append((color.upper(), move))

    return moves, board_size, komi, rules


def process_single_move_response(katago_result):
    move_infos = katago_result.get('moveInfos', [])
    if not move_infos:
        return None
    move_data = move_infos[0]
    return {
        'scoreLead': move_data.get('scoreLead', 0),
        'scoreStdev': move_data.get('scoreStdev', 0),
        'lcb': move_data.get('lcb', 0),
        'utility': move_data.get('utility', 0),
        'utilityLcb': move_data.get('utilityLcb', 0),
        'visits': move_data.get('visits', 0),
        'winrate': move_data.get('winrate', 0)
    }


def analyze_moves(katago, moves, rules, komi, board_size, move_limit=None):
    results = []

    # Convert moves to GTP format
    move_list = [[color, sgfmill_to_gtp(move, board_size)] for color, move in moves]
    total_moves = len(move_list) if move_limit is None else min(len(move_list), move_limit)

    # Analyze each move, including the initial empty board state
    with tqdm(total=total_moves, desc="Analyzing moves") as pbar:
        for move_number, move in enumerate(move_list[:total_moves]):
            current_moves = move_list[:move_number]
            result = analyze_board_state(katago, current_moves, rules, komi, board_size, move_number)
            results.extend(result)
            pbar.update(1)

    return results


def analyze_board_state(katago, move_list, rules, komi, board_size, move_number):
    results = []
    for perspective in ['play', 'pass']:
        query_moves = move_list.copy()
        if perspective == 'pass':
            current_player = 'W' if len(move_list) % 2 == 1 else 'B'
            query_moves.append([current_player, 'pass'])

        query = {
            "id": str(katago.query_counter),
            "initialStones": [],
            "moves": query_moves,
            "rules": rules,
            "komi": komi,
            "boardXSize": board_size,
            "boardYSize": board_size,
            "includePolicy": False,
            "analyzeTurns": [len(query_moves)]
        }

        query_json = json.dumps(query)
        logging.debug(f"Sending query to KataGo: {query_json}")
        katago.katago.stdin.write(query_json + "\n")
        katago.katago.stdin.flush()

        line = katago.katago.stdout.readline().strip()
        logging.debug(f"Raw response from KataGo: {line}")

        try:
            katago_result = json.loads(line)
            results.append((move_number, perspective, query_moves, katago_result))
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse KataGo response: {e}")
            logging.error(f"Raw response: {line}")
            raise Exception(f"KataGo returned invalid JSON: {line}")

        katago.query_counter += 1

    return results


def generate_sgf_output(output_file, moves, board_size, komi, rules, results):
    game = sgf.Sgf_game(size=board_size)
    root = game.get_root()

    # Set game info
    root.set("KM", komi)
    root.set("RU", rules)

    # if results:
    #     pass_move = results.pop(0)

    # We silently discard the first position.  No point analyzing an empty board

    # Create the main line with moves and analysis
    for move_number, (color, move) in enumerate(moves):
        color = color.lower()
        logging.debug(f"Processing move {move_number}: color={color}, move={move}")
        node = game.extend_main_sequence()
        node.set_move(color, move)

        # Find analysis results for this move
        play_result = next((r for r in results if r[0] == move_number and r[1] == 'play'), None)
        pass_result = next((r for r in results if r[0] == move_number and r[1] == 'pass'), None)

        if play_result and pass_result:
            play_data = process_single_move_response(play_result[3])
            pass_data = process_single_move_response(pass_result[3])

            if play_data and pass_data:
                move_str = sgfmill_to_gtp(move, board_size) if move else "pass"
                comment = f"Move {move_number + 1} ({move_str}) analysis:\n"
                comment += f"Play: Score: {play_data['scoreLead']:.4f} ±{play_data['scoreStdev']:.4f}\n"
                comment += f"      LCB: {play_data['lcb']:.4f}, Utility: {play_data['utility']:.4f}, UtilityLCB: {play_data['utilityLcb']:.4f}\n"
                comment += f"      Visits: {play_data['visits']}, Winrate: {play_data['winrate']:.4f}\n"
                comment += f"Pass: Score: {pass_data['scoreLead']:.4f} ±{pass_data['scoreStdev']:.4f}\n"
                comment += f"      LCB: {pass_data['lcb']:.4f}, Utility: {pass_data['utility']:.4f}, UtilityLCB: {pass_data['utilityLcb']:.4f}\n"
                comment += f"      Visits: {pass_data['visits']}, Winrate: {pass_data['winrate']:.4f}\n"
                node.set("C", comment)

    # Write the SGF to the output file
    with open(output_file, "wb") as f:
        f.write(game.serialise())

    logging.info(f"Analysis results written to SGF file: {output_file}")

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--verbose/--no-verbose', default=True, show_default=True, help="Increase output verbosity")
def add_passes_to_kifu(input_file, output_file, verbose):
    """Add KataGo analysis to a kifu file."""
    setup_logger()

    logging.info(f"Processing {input_file}...")

    try:
        moves, board_size, komi, rules = parse_sgf_file(input_file)

        # Initialize KataGo instance
        katago_path = os.path.join(KATAGO_DIR, KATAGO_EXECUTABLE)
        katago_model = os.path.join(KATAGO_DIR, KATAGO_MODEL)
        katago_config = os.path.join(KATAGO_DIR, KATAGO_CONFIG)
        katago = KataGo(katago_path, katago_config, katago_model)

        results = analyze_moves(katago, moves, rules, komi, board_size)

        # Write results directly to the output file (SGF)
        generate_sgf_output(output_file, moves, board_size, komi, rules, results)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        logging.error(traceback.format_exc())
    finally:
        if 'katago' in locals():
            katago.close()
            logging.info("Closed KataGo instance")

if __name__ == "__main__":
    add_passes_to_kifu()