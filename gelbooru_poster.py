# Script to take a random image with certain tags from Gelbooru and post it to Misskey

import os
import sys
import copy
import requests
import random
import json
import time
import traceback

class BotInstance:
    # Gelbooru API URL
    gelbooru_url = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags="
    # Misskey API URL
    misskey_url = "https://fediverse.dotnet00.dev/api/"
    # Misskey API token
    misskey_token = "NONE"
    # Bot message
    bot_message = "Random image from Gelbooru"
    # Gelbooru tags
    gelbooru_tags = ""
    # Gelbooru tags to exclude
    gelbooru_tags_exclude = ""
    
    def __init__(self, cfg_name, config):
        self.cfg_name = cfg_name
        self.gelbooru_tags = config["gelbooru_tags"]
        self.gelbooru_tags_exclude = config["gelbooru_tags_exclude"]
        self.bot_message = config["bot_message"]
        self.misskey_url = config["misskey_url"]
        self.misskey_token = config["misskey_token"]
        self.saved_images = config["saved_images"]
        self.max_page_number = config["max_page_number"]

    # Get a random image from Gelbooru
    def get_random_image(self, max_page_number = 100):
        # Get a random page number
        page_number = random.randint(0, max_page_number)
        # Get a random image from the page
        image_number = random.randint(0, 100)
        # Get the JSON data from the API
        if self.gelbooru_tags_exclude != "":
            gelbooru_tags_exclude = "+" + self.gelbooru_tags_exclude
        else:
            gelbooru_tags_exclude = ""
        gelbooru_json = requests.get(self.gelbooru_url + self.gelbooru_tags + gelbooru_tags_exclude + "&pid=" + str(page_number)).json()
        max_pages = gelbooru_json['@attributes']['count'] // 100 + (1 if gelbooru_json['@attributes']['count'] % 100 != 0 else 0)
        # Make sure there are images on the page
        if 'post' not in gelbooru_json:
            return None, None, max_pages
        # Make sure the image number is valid
        if image_number > len(gelbooru_json['post']):
            image_number = random.randint(0, len(gelbooru_json['post']))

        # Save json to file for debugging
        #with open("gelbooru.json", "w") as gelbooru_json_file:
        #    gelbooru_json_file.write(str(gelbooru_json))

        # Get the image URL
        image_url = gelbooru_json['post'][image_number]["file_url"]
        # Get the image rating
        image_rating = gelbooru_json['post'][image_number]["rating"]
        
        return image_url, image_rating, max_pages

    # Download and post the image to Misskey
    def post_image(self, image_url, image_rating, log_file):
        if image_url not in self.saved_images:
            # Submit a /drive/files/upload-from-url request to Misskey
            upload_from_url_request = requests.post(self.misskey_url + "drive/files/upload-from-url", json = {"url": image_url, "isSensitive": image_rating != 'general', "i": self.misskey_token})
            # If error, print error and exit
            if upload_from_url_request.status_code != 204 and upload_from_url_request.status_code != 200:
                print("Error: " + upload_from_url_request.json()["error"]["message"], file=log_file)
                return False
            # Wait for the image to be uploaded
            time.sleep(1)
        
        attempts = 0
        while True:
            # Get the file ID using the /drive/files/find request
            file_id_request = requests.post(self.misskey_url + "drive/files/find", json = {"name": os.path.split(image_url)[-1], "i": self.misskey_token})
            # If error, print error and exit
            if file_id_request.status_code != 200:
                print("Error: " + file_id_request.json()["error"]["message"], file=log_file)
                return False
            file_id_json = file_id_request.json()
            if len(file_id_json) > 0:
                file_id = file_id_json[0]["id"]
                break
            
            if attempts > 10:
                print("Error: Image not uploaded", file=log_file)
                return False
                
            # If the image hasn't been uploaded after 10 attempts, exit
            attempts += 1
            # Wait and try again
            time.sleep(min(30, (attempts ** 2) / 2))

        # Submit a /notes/create request to Misskey
        create_note_request = requests.post(self.misskey_url + "notes/create", json = {"fileIds": [file_id], "text": "%s\nURL: %s\n" % (self.bot_message, image_url), "i": self.misskey_token})
        # If error, print error and exit
        if create_note_request.status_code != 200:
            print("Error: " + create_note_request.json()["error"]["message"], file=log_file)
        return True

    def bot_process(self, log_file):
        # Get a random image making sure it's not in the saved image list
        while True:
            image_url, image_rating, cur_page_number = self.get_random_image(max_page_number=self.max_page_number)
            if cur_page_number < self.max_page_number:
                self.max_page_number = cur_page_number
            if image_url is None:
                continue
            break
        # Download and post the image to Misskey
        if self.post_image(image_url, image_rating, log_file):
            # Add the image to the saved image list
            self.saved_images.append(image_url)

def generate_config(defaults):
    if os.path.exists("config.json"):
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
    else:
        config = {}
    config['bot_name'] = {
        'gelbooru_tags': defaults['gelbooru_tags'],
        'gelbooru_tags_exclude': defaults['gelbooru_tags_exclude'],
        'bot_message': defaults['bot_message'],
        'misskey_url': defaults['misskey_url'],
        'misskey_token': defaults['misskey_token'],
        'saved_images': [],
        'max_page_number': defaults['max_page_number']
    }

    with open("config.json", "w") as config_file:
        json.dump(config, config_file, indent=4)

def generate_defaults():
    if os.path.exists("defaults.json"):
        with open("defaults.json", "r") as config_file:
            config = json.load(config_file)
    else:
        config = {}

    config['gelbooru_tags'] = 'rating:safe'
    config['gelbooru_tags_exclude'] = ''
    config['bot_message'] = 'Random image from Gelbooru'
    config['misskey_url'] = 'https://misskey.example.com/'
    config['misskey_token'] = ''
    config['max_page_number'] = 1000
    
    with open("defaults.json", "w") as config_file:
        json.dump(config, config_file, indent=4)

# Main function
def main():
    if not os.path.exists("defaults.json"):
        generate_defaults()
    with open("defaults.json", "r") as config_file:
        defaults = json.load(config_file)

    if not os.path.exists("config.json"):
        generate_config(defaults)

    # If first argument is '--gen-config', generate config.json:
    if len(sys.argv) > 1 and sys.argv[1] == "--gen-config":
        # Generate a config.json entry
        generate_config(defaults)
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python3 gelbooru-bot.py [--gen-config] [--help]")
        print("  --gen-config: Add a new bot to the config.json file")
        print("  --help: Show this help message")
        print("  No arguments: Run the bot")
        print("  Note: The values in defaults.json will be used if the values are not set in config.json")
    else:
        # Load set of configs to run from json config
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        # Create and run bot instances for each config in config.json
        with open('log.txt', 'a') as log_file:
            for cfg_name in config:

                # Set missing config values to defaults
                cfg_tmp = copy.deepcopy(config[cfg_name])
                for key in defaults:
                    if key not in cfg_tmp:
                        cfg_tmp[key] = defaults[key]

                try:
                    bot_instance = BotInstance(cfg_name, cfg_tmp)
                    bot_instance.bot_process(log_file)
                    # Save the saved image list to config.json
                    config[cfg_name]["saved_images"] = bot_instance.saved_images
                    config[cfg_name]["max_page_number"] = bot_instance.max_page_number
                
                # If error, print error and continue
                except Exception as e:
                    traceback.print_exc(file=log_file)
                    continue

        # Save the saved image list to config.json
        with open("config.json", "w") as config_file:
            json.dump(config, config_file, indent=4)

# Run main function
if __name__ == "__main__":
    main()
