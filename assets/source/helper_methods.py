def load_json(filepath):
    import json
    import os

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"The file {filepath} does not exist.")

    with open(filepath, "r") as file:
        try:
            data = json.load(file)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON from the file {filepath}: {e}")

    return data