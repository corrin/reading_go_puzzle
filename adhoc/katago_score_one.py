import os
import json
import subprocess
import logging
import time
from threading import Thread
from sgfmill import sgf
from sgfmill.boards import Board
from typing import Tuple, List, Union, Literal, Any, Dict

Color = Union[Literal["b"], Literal["w"]]
Move = Union[None, Literal["pass"], Tuple[int, int]]

KATAGO_DIR = r'C:\Users\User\.katrain'
KATAGO_EXECUTABLE = 'katago-v1.13.0-opencl-windows-x64.exe'
KATAGO_MODEL = r'kata1-b18c384nbt-s9131461376-d4087399203.bin.gz'
KATAGO_CONFIG = 'analysis_config.cfg'

# Updated function name to sgfmill_to_xy
def sgfmill_to_xy(move: Move) -> str:
    """Convert sgfmill move to explicit integer coordinate string (x, y) for KataGo."""
    if move is None:
        return "pass"
    if move == "pass":
        return "pass"
    (y, x) = move
    return f"({x},{y})"

class KataGo:
    def __init__(self, katago_path: str, config_path: str, model_path: str, additional_args: List[str] = []):
        self.query_counter = 0
        katago = subprocess.Popen(
            [katago_path, "analysis", "-config", config_path, "-model", model_path, *additional_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.katago = katago

        def printforever():
            while katago.poll() is None:
                data = katago.stderr.readline()
                time.sleep(0)
                if data:
                    print("KataGo: ", data.decode(), end="")
            data = katago.stderr.read()
            if data:
                print("KataGo: ", data.decode(), end="")

        self.stderrthread = Thread(target=printforever)
        self.stderrthread.start()

    def close(self):
        self.katago.stdin.close()

    def query_raw(self, query: Dict[str, Any]):
        logging.debug(f"Query before sending to KataGo: {json.dumps(query)}")

        self.katago.stdin.write((json.dumps(query) + "\n").encode())
        self.katago.stdin.flush()

        line = ""
        while line == "":
            if self.katago.poll():
                time.sleep(1)
                raise Exception("Unexpected katago exit")
            line = self.katago.stdout.readline()
            line = line.decode().strip()

        logging.debug(f"Response from KataGo: {line}")
        response = json.loads(line)

        return response

    def query(self, initial_board: Board, moves: List[Tuple[Color, Move]], komi: float, max_visits=None):
        query = {}
        query["id"] = str(self.query_counter)
        self.query_counter += 1

        # Use explicit integer coordinates for KataGo
        formatted_moves = [(color.upper(), sgfmill_to_xy(move)) for color, move in moves]
        query["moves"] = formatted_moves
        logging.debug(f"Formatted moves for KataGo: {formatted_moves}")

        query["initialStones"] = []
        for y in range(initial_board.side):
            for x in range(initial_board.side):
                color = initial_board.get(y, x)
                if color:
                    query["initialStones"].append((color, sgfmill_to_xy((y, x))))

        query["rules"] = "Chinese"
        query["komi"] = komi
        query["boardXSize"] = initial_board.side
        query["boardYSize"] = initial_board.side
        query["includePolicy"] = True
        if max_visits is not None:
            query["maxVisits"] = max_visits
        return self.query_raw(query)

def parse_sgf_file(file_path):
    """Parses an SGF file and returns the game moves and metadata."""
    with open(file_path, 'rb') as f:
        sgf_content = f.read()
    game = sgf.Sgf_game.from_bytes(sgf_content)
    board_size = game.get_size()
    komi = float(game.get_komi())

    # Get the main sequence of nodes and extract moves
    main_sequence = game.get_main_sequence()
    moves = []

    for node in main_sequence:
        color, move = node.get_move()
        if move is not None:  # Exclude pass moves
            moves.append((color, move))

    return moves, board_size, komi

def run_katago_analysis(katago, board_size, komi, moves):
    """Run KataGo analysis on the moves."""
    # Initialize the board
    board = Board(board_size)
    results = []

    # Simulate moves on the board and query KataGo
    for color, move in moves:
        if move != "pass":
            board.play(move[0], move[1], color)
        katago_result = katago.query(board, [(color, move)], komi)
        results.append(katago_result)

    return results

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load SGF file and parse moves
    sgf_file_path = "/Users/User/Downloads/251520.sgf"
    moves, board_size, komi = parse_sgf_file(sgf_file_path)

    # Run KataGo analysis with the provided configuration
    katago_path = os.path.join(KATAGO_DIR, KATAGO_EXECUTABLE)
    katago_model = os.path.join(KATAGO_DIR, KATAGO_MODEL)
    katago_config = os.path.join(KATAGO_DIR, KATAGO_CONFIG)
    katago = KataGo(katago_path, katago_config, katago_model)

    katago_results = run_katago_analysis(katago, board_size, komi, moves)

    # (Optional) Load KaTrain results and compare them (not implemented here)
    # katrain_results = [...]  # Load your KaTrain results here, format as list of dicts
    katago.close()
