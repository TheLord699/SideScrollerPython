import os
import json

class DataManager:
    def __init__(self):
        self.filename = "assets/settings/game_data.json"
        self.data = {}

    def load_data(self):
        try:
            with open(self.filename, 'r') as file:
                self.data = json.load(file)
                
        except FileNotFoundError:
            self.data = {}
            
        except json.JSONDecodeError:
            print("Error decoding JSON from the data file.")
            self.data = {}

    def save_data(self):
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            with open(self.filename, 'w') as file:
                json.dump(self.data, file, indent=4)
                
        except IOError as e:
            print(f"Error saving data to file: {e}")

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value
        self.save_data()

# example usage
"""""
data_manager.load_data()

# Save some data
data_manager.set_setting("player_name", "Alex")
data_manager.set_setting("high_score", 1200)
data_manager.set_setting("level", 3)
data_manager.set_setting("volume", 0.8)
"""