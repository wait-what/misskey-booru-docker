# Script to take a random image with certain tags from Gelbooru and post it to Misskey

import os
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
        self.bot_hashtags = config["bot_hashtags"]
        self.misskey_url = config["misskey_url"]
        self.misskey_token = config["misskey_token"]
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
        gelbooru_json = requests.get(self.gelbooru_url + self.gelbooru_tags + '+' + gelbooru_tags_exclude + "&pid=" + str(page_number)).json()
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
    def post_image(self, image_url, image_rating):
        image_found = False
        file_presence_check = requests.post(self.misskey_url + "drive/files/find", json = {"name": os.path.split(image_url)[-1], "i": self.misskey_token})
        if file_presence_check.status_code != 200:
            image_found = False
        else:
            file_presence_json = file_presence_check.json()
            image_found = len(file_presence_json) > 0

        if not image_found:
            # Submit a /drive/files/upload-from-url request to Misskey
            upload_from_url_request = requests.post(self.misskey_url + "drive/files/upload-from-url", json = {"url": image_url, "isSensitive": image_rating != 'general', "i": self.misskey_token})
            # If error, print error and exit
            if upload_from_url_request.status_code != 204 and upload_from_url_request.status_code != 200:
                print("Error: " + upload_from_url_request.json()["error"]["message"])
                return False
            # Wait for the image to be uploaded
            time.sleep(1)
        
        attempts = 0
        while True:
            # Get the file ID using the /drive/files/find request
            file_id_request = requests.post(self.misskey_url + "drive/files/find", json = {"name": os.path.split(image_url)[-1], "i": self.misskey_token})
            # If error, print error and exit
            if file_id_request.status_code != 200:
                print("Error: " + file_id_request.json()["error"]["message"])
                return False
            file_id_json = file_id_request.json()
            if len(file_id_json) > 0:
                file_id = file_id_json[0]["id"]
                break
            
            if attempts > 10:
                print("Error: Image not uploaded")
                return False
                
            # If the image hasn't been uploaded after 10 attempts, exit
            attempts += 1
            # Wait and try again
            time.sleep(min(30, (attempts ** 2) / 2))

        # Submit a /notes/create request to Misskey
        msg = self.bot_message
        if random.randint(0, 100) < 5:
            msg += " " + self.bot_hashtags
        create_note_request = requests.post(self.misskey_url + "notes/create", json = {"fileIds": [file_id], "text": "%s\nURL: %s\n" % (msg, image_url), "i": self.misskey_token})
        # If error, print error and exit
        if create_note_request.status_code != 200:
            print("Error: " + create_note_request.json()["error"]["message"])
        return True

    def bot_process(self):
        # Get a random image making sure it's not in the saved image list
        while True:
            image_url, image_rating, cur_page_number = self.get_random_image(max_page_number=self.max_page_number)
            if cur_page_number < self.max_page_number:
                self.max_page_number = cur_page_number
            if image_url is None:
                continue
            break
        # Download and post the image to Misskey
        self.post_image(image_url, image_rating)


# Main function
def main():
    # Load set of configs to run from json config
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    # Create and run bot instances for each config in config.json
    for cfg_name in config:
        cfg_tmp = copy.deepcopy(config[cfg_name])

        try:
            bot_instance = BotInstance(cfg_name, cfg_tmp)
            bot_instance.bot_process()
            # Save the saved image list to config.json
            config[cfg_name]["max_page_number"] = bot_instance.max_page_number

        # If error, print error and continue
        except Exception as e:
            traceback.print_exc()
            continue

# Run main function
if __name__ == "__main__":
    main()