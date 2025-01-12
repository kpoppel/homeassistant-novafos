import json

def load_data(data_file_name):
    with open(f"tests/data/{data_file_name}") as f:
        response_data = json.load(f)
    return json.dumps(response_data).encode("utf-8")

def load_data_structure(data_file_name):
    with open(f"tests/data/{data_file_name}") as f:
        response_data = json.load(f)
    return response_data
