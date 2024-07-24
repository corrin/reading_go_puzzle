import click
import os
import shutil

# Define the directories for each stage
directories = {
    1: ('sgf/inbound', 'sgf/error_sanity', 'sgf/contain_solution'),
    2: ('sgf/contain_solution', 'sgf/error_add_border', 'sgf/with_outer_edge'),
    3: ('sgf/with_outer_edge', 'sgf/error_validate_solution', 'sgf/solution_validated'),
    4: ('sgf/solution_validated', 'sgf/error_validate_pass', 'sgf/tenuki_validated'),
    5: ('sgf/tenuki_validated', 'sgf/error_ingest_database', 'sgf/ingested'),
}

# Mapping of stage names to numbers
stage_mapping = {
    'sanity': 1,
    'add_border': 2,
    'validate_solution': 3,
    'validate_pass': 4,
    'ingest_database': 5,
}


# Define the processing logic for each stage
def process_stage_sanity(file_path):
    # Placeholder for sanity check logic
    with open(file_path, 'r') as file:
        content = file.read()
    return "C[solution]" in content


def process_stage_add_border(file_path):
    # Placeholder for adding border logic
    return True  # Assume always passes for demonstration


def process_stage_validate_solution(file_path):
    # Placeholder for validate solution logic
    return True  # Assume always passes for demonstration


def process_stage_validate_pass(file_path):
    # Placeholder for validate pass logic
    return True  # Assume always passes for demonstration


def process_stage_ingest_database(file_path):
    # Placeholder for ingest to database logic
    return True  # Assume always passes for demonstration


# Mapping of stages to their processing functions
stage_processors = {
    1: process_stage_sanity,
    2: process_stage_add_border,
    3: process_stage_validate_solution,
    4: process_stage_validate_pass,
    5: process_stage_ingest_database,
}


def process_files(stage, file_path):
    inbound_dir, error_dir, next_inbound_dir = directories[stage]
    if not os.path.exists(next_inbound_dir):
        os.makedirs(next_inbound_dir)
    if not os.path.exists(error_dir):
        os.makedirs(error_dir)

    if stage_processors[stage](file_path):
        shutil.move(file_path, next_inbound_dir)
        return f"File {file_path} passed stage {stage} and moved to {next_inbound_dir}."
    else:
        shutil.move(file_path, error_dir)
        return f"File {file_path} failed stage {stage} and moved to {error_dir}."


@click.command()
@click.option('--one', type=click.Path(exists=True), help="Process a single SGF file")
@click.option('--all', is_flag=True, help="Process all SGF files in the current stage's inbound directory")
@click.option('--stage', type=str, required=True, help="Specify the stage(s) to process")
def manage_problems(one, all, stage):
    stages = []
    if stage == 'all':
        stages = [1, 2, 3, 4, 5]
    else:
        stage_list = stage.split(',')
        for s in stage_list:
            if s.isdigit():
                stages.append(int(s))
            elif s in stage_mapping:
                stages.append(stage_mapping[s])

    for stage in stages:
        inbound_dir, error_dir, next_inbound_dir = directories[stage]
        if one:
            result = process_files(stage, one)
            click.echo(result)
        elif all:
            for filename in os.listdir(inbound_dir):
                file_path = os.path.join(inbound_dir, filename)
                if os.path.isfile(file_path) and file_path.endswith('.sgf'):
                    result = process_files(stage, file_path)
                    click.echo(result)
        else:
            click.echo("Please provide either --one <filename> or --all option.")


if __name__ == "__main__":
    manage_problems()
