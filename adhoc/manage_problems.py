import os
import click
import logging
from enum import Enum
from sgfmill import sgf, sgf_moves

INPUT_DIR = 'sgf/raw'
OUTPUT_DIR = 'sgf/processed'


class VerbosityLevel(Enum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3


logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def log_message(msg, level=VerbosityLevel.WARNING):
    if level.value <= VerbosityLevel.current.value:
        if level == VerbosityLevel.DEBUG:
            logger.debug(msg)
        elif level == VerbosityLevel.INFO:
            logger.info(msg)
        elif level == VerbosityLevel.WARNING:
            logger.warning(msg)
        elif level == VerbosityLevel.ERROR:
            logger.error(msg)


def read_sgf(file_path):
    with open(file_path, 'rb') as f:
        return sgf.Sgf_game.from_bytes(f.read())


def find_solution_path(node, path=None):
    if path is None:
        path = []

    current_path = path + [node]

    log_message(f"Checking node: {node.get_move()}", VerbosityLevel.DEBUG)

    if node.has_property('C'):
        comment = ''.join(node.get('C'))
        log_message(f"Comment found: {comment}", VerbosityLevel.DEBUG)
        if 'Correct' in comment:
            log_message(f"Correct solution found at move {node.get_move()}", VerbosityLevel.INFO)
            return current_path

    for child in node:
        solution = find_solution_path(child, current_path)
        if solution:
            return solution

    return None


def has_tenuki_paths(node):
    log_message(f"Checking for tenuki paths in node: {node.get_move()}", VerbosityLevel.DEBUG)

    for child in node:
        if not find_solution_path(child):
            log_message(f"Tenuki path found at move: {child.get_move()}", VerbosityLevel.DEBUG)
            return True

    log_message("No tenuki paths found", VerbosityLevel.DEBUG)
    return False


def determine_problem_type(solution_path):
    log_message("Entering determine_problem_type function", VerbosityLevel.DEBUG)

    is_kill_problem = False
    for node in solution_path:
        if node.has_property('C'):
            comment = ''.join(node.get('C'))
            log_message(f"Checking comment: {comment}", VerbosityLevel.DEBUG)
            if 'killed' in comment.lower() or 'dead' in comment.lower():
                is_kill_problem = True
                break

    problem_type = 'kill' if is_kill_problem else 'save'

    log_message(f"Determined problem type: {problem_type}", VerbosityLevel.DEBUG)
    log_message("Exiting determine_problem_type function", VerbosityLevel.DEBUG)

    return problem_type


def create_output_sgf_string(input_game, solution_path, is_tenuki=False):
    log_message("Entering create_output_sgf_string function", VerbosityLevel.DEBUG)

    size = input_game.get_size()
    root = input_game.get_root()
    log_message(f"Game size: {size}, Root node: {root}", VerbosityLevel.DEBUG)

    def to_sgf_coord(row, col):
        return f"{chr(97 + col)}{chr(97 + row)}"

    # Get the board state from SGFMill
    board, plays = sgf_moves.get_setup_and_moves(input_game)

    ko_point = None
    if is_tenuki and plays:
        color, move = plays[0]
        row, col = move
        ko_point = board.play(row, col, color)
        log_message(f"Played tenuki move: {color} at {to_sgf_coord(row, col)}", VerbosityLevel.DEBUG)

    # Get stones from the board
    black_stones = []
    white_stones = []
    for row in range(size):
        for col in range(size):
            color = board.get(row, col)
            if color == 'b':
                black_stones.append(to_sgf_coord(row, col))
            elif color == 'w':
                white_stones.append(to_sgf_coord(row, col))

    log_message(f"Black stones: {black_stones}", VerbosityLevel.DEBUG)
    log_message(f"White stones: {white_stones}", VerbosityLevel.DEBUG)

    # Check if we have a valid problem (stones on the board)
    if not black_stones or not white_stones:
        error_msg = "Invalid problem: There must be both black and white stones on the board."
        log_message(error_msg, VerbosityLevel.ERROR)
        raise ValueError(error_msg)

    # Start building the SGF string
    sgf_string = "(;FF[4]GM[1]CA[UTF-8]AP[Tsumego Solver:1.0]ST[2]RU[Japanese]"
    sgf_string += f"SZ[{size}]KM[0.00]"

    # Determine color to play and problem type
    color_to_play = 'W' if is_tenuki else 'B'
    problem_type = determine_problem_type(solution_path)
    if is_tenuki:
        problem_type = 'save' if problem_type == 'kill' else 'kill'

    log_message(f"Color to play: {color_to_play}, Problem type: {problem_type}", VerbosityLevel.DEBUG)

    # Add PL for player to move
    sgf_string += f"PL[{color_to_play}]"

    # Add SO if present in the original SGF
    if root.has_property('SO'):
        source = ''.join(root.get('SO'))
        log_message(f"Source property found: {source}", VerbosityLevel.DEBUG)
        sgf_string += f"SO[{source}]"

    # Add comment with problem description, correct answer, and ko information
    comment = f"Can {color_to_play} {problem_type} the marked stone? "
    comment += "Correct answer: NO" if is_tenuki else "Correct answer: YES"
    if ko_point:
        ko_coord = to_sgf_coord(*ko_point)
        comment += f"\nKo point: {ko_coord}"
    sgf_string += f"C[{comment}]"
    log_message(f"Added comment: {comment}", VerbosityLevel.DEBUG)

    # Add stones to the SGF string
    sgf_string += "AB" + "".join(f"[{stone}]" for stone in black_stones)
    sgf_string += "AW" + "".join(f"[{stone}]" for stone in white_stones)

    # Mark ko point
    if ko_point:
        ko_coord = to_sgf_coord(*ko_point)
        sgf_string += f"MA[{ko_coord}]"

    sgf_string += ")"

    log_message(f"Final SGF string: {sgf_string}", VerbosityLevel.DEBUG)
    log_message("Exiting create_output_sgf_string function", VerbosityLevel.DEBUG)

    return sgf_string


def process_sgf(file_path):
    try:
        log_message(f"Processing {file_path}", VerbosityLevel.INFO)
        input_game = read_sgf(file_path)

        log_message(f"Searching for solution path", VerbosityLevel.INFO)
        solution_path = find_solution_path(input_game.get_root())
        if not solution_path:
            raise ValueError("No solution found in the SGF")

        log_message(f"Checking for tenuki paths", VerbosityLevel.INFO)
        if not has_tenuki_paths(input_game.get_root()):
            raise ValueError("No tenuki paths found in the SGF")

        # Create main problem
        output_sgf = create_output_sgf_string(input_game, solution_path, is_tenuki=False)
        output_file_name = os.path.splitext(os.path.basename(file_path))[0] + '_main.sgf'
        output_file_path = os.path.join(OUTPUT_DIR, output_file_name)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(output_sgf)
        log_message(f"Generated main problem SGF: {output_file_path}", VerbosityLevel.INFO)

        # Create tenuki problems
        tenuki_count = 0
        for child in input_game.get_root():
            if child not in solution_path:
                log_message(f"Processing tenuki path: {child.get_move()}", VerbosityLevel.INFO)
                tenuki_solution_path = [input_game.get_root(), child]
                tenuki_sgf = create_output_sgf_string(input_game, tenuki_solution_path, is_tenuki=True)
                tenuki_file_name = f"{os.path.splitext(os.path.basename(file_path))[0]}_tenuki_{tenuki_count}.sgf"
                tenuki_file_path = os.path.join(OUTPUT_DIR, tenuki_file_name)
                with open(tenuki_file_path, 'w', encoding='utf-8') as f:
                    f.write(tenuki_sgf)
                log_message(f"Generated tenuki problem SGF: {tenuki_file_path}", VerbosityLevel.INFO)
                tenuki_count += 1

        log_message(f"Successfully processed {file_path}. Generated {tenuki_count + 1} problem(s).",
                    VerbosityLevel.INFO)
        return True, tenuki_count + 1  # +1 for the main problem
    except Exception as e:
        log_message(f"Error processing SGF file: {file_path}. Error: {str(e)}", VerbosityLevel.ERROR)
        return False, 0


@click.command()
@click.option('--one', type=click.Path(exists=True), help="Process a single SGF file")
@click.option('--all', is_flag=True, help="Process all SGF files in the input directory")
@click.option('--verbosity', type=click.Choice(['error', 'warning', 'info', 'debug']), default='warning',
              help="Set the verbosity level")
def manage_problems(one, all, verbosity):
    global VerbosityLevel
    VerbosityLevel.current = VerbosityLevel[verbosity.upper()]

    logger.setLevel(getattr(logging, verbosity.upper()))

    log_message(f"Verbosity level set to: {VerbosityLevel.current.name}", VerbosityLevel.INFO)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        log_message(f"Created output directory: {OUTPUT_DIR}", VerbosityLevel.INFO)

    if one:
        log_message(f"Processing single file: {one}", VerbosityLevel.INFO)
        result, problem_count = process_sgf(one)
        if result:
            log_message(f"Successfully processed {one}. Generated {problem_count} problem(s).", VerbosityLevel.INFO)
        else:
            log_message(f"Failed to process {one}", VerbosityLevel.ERROR)
    elif all:
        log_message("Processing all SGF files in the input directory", VerbosityLevel.INFO)
        successful = 0
        failed = 0
        total_problems = 0
        failed_files = []
        for filename in os.listdir(INPUT_DIR):
            if filename.endswith('.sgf'):
                file_path = os.path.join(INPUT_DIR, filename)
                log_message(f"Processing file: {file_path}", VerbosityLevel.INFO)
                result, problem_count = process_sgf(file_path)
                if result:
                    successful += 1
                    total_problems += problem_count
                    log_message(f"Successfully processed {filename}. Generated {problem_count} problem(s).",
                                VerbosityLevel.INFO)
                else:
                    failed += 1
                    failed_files.append(filename)
                    log_message(f"Failed to process {filename}", VerbosityLevel.ERROR)
        log_message(f"\nSummary: Processed {successful + failed} files.", VerbosityLevel.INFO)
        log_message(f"Successful: {successful}", VerbosityLevel.INFO)
        log_message(f"Failed: {failed}", VerbosityLevel.INFO)
        log_message(f"Total problems generated: {total_problems}", VerbosityLevel.INFO)
        if failed_files:
            log_message("Failed files:", VerbosityLevel.ERROR)
            for file in failed_files:
                log_message(file, VerbosityLevel.ERROR)
    else:
        log_message("Please provide either --one <filename> or --all option.", VerbosityLevel.ERROR)

if __name__ == "__main__":
    manage_problems()