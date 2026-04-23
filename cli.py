from pathlib import Path
import json
import redis

def main():
    exist = True

    while exist:
        user_choice = input(
            "1 Upload image\n" \
            "2 Exit\n" \
            "Please choose the option: "
            )

        if user_choice == "1":
            legal = False

            while not legal:
                user_input = input("Please type the address of the pic: ")
                legal = is_legal_path(user_input)
                if not legal:
                    print("The path not legal.")
            
            message = package_upload_message(user_input)

            publish_upload_message(message)

        elif user_choice == "2":
            exist = False

    

def is_legal_path(user_input):

    path = Path(user_input)

    if not path.exists():
        return False
    
    if not path.is_file():
        return False
    
    if path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".bmp"]:
        return False

    return True
    
def package_upload_message(path):
    message = {
        "event_name": "upload_image",
        "image_path": path
    }
    return message

def publish_upload_message(message):
    client = redis.Redis(host="localhost", port=6379, db=0)
    json_message = json.dumps(message)
    client.publish("image_upload_channel", json_message)
    print("Upload message published")

if __name__ == "__main__":
    main()