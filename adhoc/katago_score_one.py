import json
import subprocess
import logging
from sgfmill import sgf, sgf_moves


def run_katago_analysis(moves, board_size, komi, katago_path, analysis_type="scoreLead"):
    """Runs KataGo analysis for given moves and returns the analysis results."""
    katago_command = [
        katago_path,
        "gtp",
        "-model",
        "default_model",
        "-config",
        "default_config.cfg"
    ]

    # Initialize KataGo subprocess
    katago_process = subprocess.Popen(katago_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)

    results = []

    # Prepare query commands for KataGo
    for turn, move in enumerate(moves):
        color, coords = move
        coords_sgf = f"{chr(coords[1] + ord('a'))}{chr(coords[0] + ord('a'))}"

        # Build GTP command
        play_command = f"{color} {coords_sgf}"
        katago_process.stdin.write(f"play {play_command}\n")
        katago_process.stdin.flush()

        # Build analysis command
        query = {
            "id": analysis_type,
            "moves": moves[:turn + 1],
            "rules": "chinese",
            "komi": komi,
            "boardXSize": board_size,
            "boardYSize": board_size,
            "analyzeTurns": [turn + 1]
        }
        katago_process.stdin.write(json.dumps(query) + "\n")
        katago_process.stdin.flush()

        response = katago_process.stdout.readline().strip()
        result = json.loads(response)

        results.append(result)

    katago_process.terminate()
    return results


def parse_sgf_file(file_path):
    """Parses an SGF file and returns the game moves and metadata."""
    with open(file_path, 'rb') as f:
        sgf_content = f.read()
    game = sgf.Sgf_game.from_bytes(sgf_content)
    board_size = game.get_size()
    komi = float(game.get_komi())

    moves = sgf_moves.get_main_moves(game)
    return moves, board_size, komi


def compare_with_katrain_results(katago_results, katrain_results):
    """Compares KataGo analysis results with those obtained from KaTrain."""
    for i, (katago_result, katrain_result) in enumerate(zip(katago_results, katrain_results)):
        katago_score = katago_result.get('rootInfo', {}).get('scoreLead')
        katrain_score = katrain_result.get('scoreLead')
        katago_pass_value = katago_result.get('rootInfo', {}).get('passValue')
        katrain_pass_value = katrain_result.get('passValue')

        logging.debug(f"Move {i + 1}: KataGo score: {katago_score}, KaTrain score: {katrain_score}")
        logging.debug(f"Move {i + 1}: KataGo pass value: {katago_pass_value}, KaTrain pass value: {katrain_pass_value}")

        if abs(katago_score - katrain_score) > 0.5 or abs(katago_pass_value - katrain_pass_value) > 0.5:
            logging.warning(f"Significant difference detected at move {i + 1}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load SGF file and parse moves
    sgf_file_path = "/mnt/data/251520.sgf"
    moves, board_size, komi = parse_sgf_file(sgf_file_path)

    # Run KataGo analysis
    katago_path = "/path/to/katago"  # Update with your KataGo executable path
    katago_results = run_katago_analysis(moves, board_size, komi, katago_path)

    # Load KaTrain results (example)
    katrain_results = [...]  # Load your KaTrain results here, format as list of dicts

    # Compare results
    compare_with_katrain_results(katago_results, katrain_results)
