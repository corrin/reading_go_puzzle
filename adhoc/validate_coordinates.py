from sgfmill import sgf
from sgfmill.common import format_vertex

def validate_sgf_coordinates(file_path):
    """Reads an SGF file and prints SGF and numeric coordinates for validation."""
    with open(file_path, 'rb') as f:
        sgf_content = f.read()

    # Parse the SGF file
    game = sgf.Sgf_game.from_bytes(sgf_content)
    board_size = game.get_size()

    # Get the main sequence of nodes
    main_sequence = game.get_main_sequence()
    moves = []

    for node in main_sequence:
        color, move = node.get_move()
        if move is not None:  # Exclude pass moves
            moves.append((color, move))

    print("SGF Coordinates -> Numeric Coordinates")
    for color, move in moves:
        # Convert numeric (row, col) back to conventional notation if needed
        sgf_coords = format_vertex(move)
        print(f"SGF move {move} ({color}) -> SGF notation {sgf_coords}")

if __name__ == "__main__":
    sgf_file_path = "/Users/User/Downloads/251520.sgf"
    validate_sgf_coordinates(sgf_file_path)
