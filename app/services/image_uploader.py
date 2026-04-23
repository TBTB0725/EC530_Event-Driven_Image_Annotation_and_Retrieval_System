from pathlib import Path
import redis
import json
import shutil

def main():
    client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    pubsub = client.pubsub()
    pubsub.subscribe("image_upload_channel")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        
        data = json.loads(message["data"])

        if data["event_name"] == "upload_image":
            image_path = Path(data["image_path"])
            base_path = Path(__file__).resolve().parent.parent
            image_db_path = base_path/"storage"/"image_db"
            destination_path = image_db_path / image_path.name
            shutil.copy2(image_path, destination_path)
        else:
            continue

if __name__ == "__main__":
    main()

            

