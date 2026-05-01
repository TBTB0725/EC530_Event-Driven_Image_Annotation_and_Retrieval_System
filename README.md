# EC528 Event-Driven Image Annotation and Retrieval System

This repo is an event-driven image annotation and retrieval prototype. A user
can upload local images, let the system detect objects in them, store the
annotation metadata, generate CLIP embeddings, and retrieve images by text or
by a similar image.

The project is designed as several small Python services connected through
Redis channels:

```text
CLI
 -> image_uploader
 -> annotation
 -> document_db_service
 -> embedding_service
 -> vector_index_service
 -> CLI query results
```

## What You Can Do With This Repo

- Upload an image from your local machine.
- Automatically annotate objects in the image using YOLO.
- Store image metadata and object annotations in MongoDB.
- Generate normalized CLIP image embeddings.
- Store and update embeddings in a local FAISS vector index.
- Search indexed images by a text topic, such as `car` or `person`.
- Search indexed images by giving another image as the query.

## Repository Layout

```text
.
├── cli.py                         # Interactive user CLI
├── requirements.txt               # Python dependencies
├── yolov8n.pt                     # YOLO model weights used by annotation
├── app/
│   ├── services/
│   │   ├── event_generator.py      # Shared event/channel constants + test publisher
│   │   ├── image_uploader.py       # Copies uploaded images into local storage
│   │   ├── annotation.py           # Runs YOLO detection
│   │   ├── document_db_service.py  # Writes annotation records to MongoDB
│   │   ├── embedding_service.py    # Generates CLIP image embeddings
│   │   └── vector_index_service.py # Indexes/searches embeddings with FAISS
│   └── storage/
│       ├── document_db.py          # MongoDB helper functions
│       ├── vector_index.py         # FAISS helper functions
│       ├── image_db/               # Created at runtime for uploaded images
│       └── vector_index_data/      # Created at runtime for FAISS files
└── tests/                          # Unit tests
```

## Prerequisites

Install or have access to:

- Python 3.11 or a recent Python 3 version
- Redis running on `localhost:6379`
- MongoDB running on `mongodb://localhost:27017`
- Internet access for the first CLIP model download, unless it is already
  cached locally

The default Redis and MongoDB settings are defined in
[`app/services/event_generator.py`](app/services/event_generator.py).

## Setup

From the repo root, create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

If your system does not have a `python` command, use `python3` instead:

```bash
python3 -m pip install -r requirements.txt
```

On Windows PowerShell, this is also fine:

```powershell
py -3 -m pip install -r requirements.txt
```

The first time the embedding service runs, `transformers` may download
`openai/clip-vit-base-patch32` from Hugging Face.

## Run The System

Start Redis and MongoDB first. Then open separate terminals from the repo root
and run the services below.

Terminal 1:

```bash
python -m app.services.document_db_service
```

Terminal 2:

```bash
python -m app.services.annotation
```

Terminal 3:

```bash
python -m app.services.embedding_service
```

Terminal 4:

```bash
python -m app.services.vector_index_service
```

Terminal 5:

```bash
python -m app.services.image_uploader
```

Terminal 6:

```bash
python cli.py
```

On Windows, replace `python` with `py -3` if that is how your Python is
installed. On Linux or WSL, replace `python` with `python3` if needed.

## Use The CLI

After running `python cli.py`, the menu shows:

```text
1 Upload image
2 Query images by topic
3 Query similar images
4 Exit
```

### 1. Upload An Image

Choose option `1`, then enter a local image path.

Supported extensions:

- `.jpg`
- `.jpeg`
- `.png`
- `.bmp`

Example:

```text
C:\Users\YourName\Desktop\example.png
```

What happens:

1. The uploader copies the image into `app/storage/image_db/`.
2. The image gets a stable SHA-256 `image_id` based on file content.
3. YOLO detects objects in the stored image.
4. MongoDB stores the annotation record.
5. CLIP generates an image embedding.
6. FAISS stores the embedding for retrieval.

### 2. Query Images By Topic

Choose option `2`, then enter:

- a topic, for example `car`
- a top-k value, for example `5`

The system encodes the text with CLIP and searches the FAISS index for the
closest image embeddings.

### 3. Query Similar Images

Choose option `3`, then enter:

- a local query image path
- a top-k value

The system encodes the query image with CLIP and searches for visually similar
indexed images.

## Data Locations

Uploaded image copies:

```text
app/storage/image_db/
```

MongoDB annotation documents:

```text
Database:   image_annotation_system
Collection: image_records
```

FAISS vector index files:

```text
app/storage/vector_index_data/image_vectors.faiss
app/storage/vector_index_data/image_vectors.json
```

Each MongoDB image record contains fields like:

- `image_id`
- `image_path`
- `objects`
- `review`

## Inspect MongoDB Data

Count stored image records:

```bash
python -c "from pymongo import MongoClient; c = MongoClient('mongodb://localhost:27017'); print(c['image_annotation_system']['image_records'].count_documents({}))"
```

Print stored records without MongoDB `_id`:

```bash
python -c "from pymongo import MongoClient; c = MongoClient('mongodb://localhost:27017'); print(list(c['image_annotation_system']['image_records'].find({}, {'_id': 0})))"
```

If you use `mongosh`:

```javascript
use image_annotation_system
db.image_records.find().pretty()
```

## Publish Sample Events Manually

`app.services.event_generator` can publish sample Redis events for testing one
stage at a time.

Print an example upload event without publishing:

```bash
python -m app.services.event_generator upload_image --print-only
```

Publish a sample topic query:

```bash
python -m app.services.event_generator query_by_topic --topic car --top-k 5
```

Supported event names are defined in
[`app/services/event_generator.py`](app/services/event_generator.py).

## Run Tests

```bash
python -m unittest discover -s tests -v
```

On Windows:

```powershell
py -3 -m unittest discover -s tests -v
```

## Reset Local Data

Clear MongoDB annotation records:

```bash
python -c "from pymongo import MongoClient; c = MongoClient('mongodb://localhost:27017'); result = c['image_annotation_system']['image_records'].delete_many({}); print(result.deleted_count)"
```

Remove FAISS index files:

```text
app/storage/vector_index_data/image_vectors.faiss
app/storage/vector_index_data/image_vectors.json
```

Remove uploaded image copies:

```text
app/storage/image_db/
```

For a fully clean reset, clear all three: MongoDB records, FAISS index files,
and stored image files.

## Current Limitations

- Services are started manually in separate terminals.
- There is no user-facing delete workflow yet.