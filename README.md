# EC528 Event-Driven Image Annotation and Retrieval System

This repository is an event-driven image pipeline built around Redis message passing.
It lets a user:

1. Upload an image into the system
2. Run automatic object annotation with YOLO
3. Store annotation records in MongoDB
4. Generate CLIP embeddings for stored images
5. Index embeddings with FAISS
6. Query images by text topic
7. Query top-k similar images by example image

The project is organized as small services that communicate through Redis channels instead of one large monolithic script.

## What This Repo Does

At a high level, the system takes an uploaded image and pushes it through a pipeline:

`CLI -> image_uploader -> annotation -> document_db_service -> embedding_service -> vector_index_service`

The services are loosely coupled:

- `cli.py`
  - The user-facing entrypoint
  - Publishes upload requests and retrieval queries
- `app/services/image_uploader.py`
  - Copies uploaded images into the project image database
  - Deduplicates identical files by hashing file content
  - Publishes annotation requests
- `app/services/annotation.py`
  - Runs YOLO object detection
  - Publishes structured annotation records
- `app/services/document_db_service.py`
  - Stores annotation records in MongoDB
  - Publishes embedding requests
- `app/services/embedding_service.py`
  - Uses CLIP to generate image embeddings
  - Publishes embedding index requests
- `app/services/vector_index_service.py`
  - Stores embeddings in FAISS
  - Answers text-to-image and image-to-image retrieval queries

## Main Technologies

- Python
- Redis
- MongoDB
- YOLO via `ultralytics`
- CLIP via `transformers` + `torch`
- FAISS for vector search

## Project Structure

```text
.
├── cli.py
├── app
│   ├── services
│   │   ├── annotation.py
│   │   ├── document_db_service.py
│   │   ├── embedding_service.py
│   │   ├── event_generator.py
│   │   ├── image_uploader.py
│   │   └── vector_index_service.py
│   └── storage
│       ├── document_db.py
│       ├── image_db/
│       ├── vector_index.py
│       └── vector_index_data/
└── tests
```

## Requirements

Before running the system, make sure you have:

- Python 3.11+ or similar recent version
- Redis running on `localhost:6379`
- MongoDB running on `mongodb://localhost:27017`

The default Redis and MongoDB configuration is defined in:

- [app/services/event_generator.py](/mnt/c/Projects/EC528_Event-Driven_Image_Annotation_and_Retrieval_System/app/services/event_generator.py)

## Installation

From the project root:

```powershell
py -3 -m pip install -r requirements.txt
```

If you use `python` instead of `py`, this is equivalent:

```bash
python -m pip install -r requirements.txt
```

### Important First-Run Note

The first time you run YOLO or CLIP, model weights may need to be downloaded.
That means your machine needs internet access the first time these models are used.

## Start Required Services

Make sure Redis and MongoDB are both running before you start the application services.

### Check MongoDB

In PowerShell:

```powershell
Get-Service *mongo*
```

If it shows `Running`, MongoDB is already available.

### Check Redis

You need a Redis server listening on `localhost:6379`.
How you start Redis depends on how you installed it.

## How to Run the System

Open multiple terminals from the project root and start each service.

### Terminal 1: Document DB service

```powershell
py -3 -m app.services.document_db_service
```

### Terminal 2: Annotation service

```powershell
py -3 -m app.services.annotation
```

### Terminal 3: Embedding service

```powershell
py -3 -m app.services.embedding_service
```

### Terminal 4: Vector index service

```powershell
py -3 -m app.services.vector_index_service
```

### Terminal 5: Image uploader service

```powershell
py -3 -m app.services.image_uploader
```

### Terminal 6: CLI

```powershell
py -3 cli.py
```

## Supported User Cases

Once the CLI is running, it supports these flows:

### 1. Upload image

In the CLI:

```text
1
```

Then enter a local image path, for example:

```text
"C:\Users\YourName\Desktop\example.png"
```

What happens next:

- The image is copied into `app/storage/image_db/`
- The image gets a stable content-based `image_id`
- YOLO annotations are generated
- The annotation document is written into MongoDB
- A CLIP embedding is generated
- The embedding is stored in FAISS

### 2. Query images by topic

In the CLI:

```text
2
```

Then enter:

- a topic, for example `car`
- a top-k number, for example `5`

What happens next:

- CLIP encodes the text query
- FAISS searches the image embedding index
- The CLI prints the top-k matching images

### 3. Query similar images

In the CLI:

```text
3
```

Then enter:

- a local query image path
- a top-k number

What happens next:

- CLIP encodes the query image
- FAISS searches the indexed image embeddings
- The CLI prints the top-k most similar images

## How to View Annotation Data in MongoDB

The annotation records are stored in:

- Database: `image_annotation_system`
- Collection: `image_records`

### Option 1: Query with Python

Count records:

```powershell
py -3 -c "from pymongo import MongoClient; c = MongoClient('mongodb://localhost:27017'); print(c['image_annotation_system']['image_records'].count_documents({}))"
```

Print all records without Mongo `_id`:

```powershell
py -3 -c "from pymongo import MongoClient; c = MongoClient('mongodb://localhost:27017'); docs = list(c['image_annotation_system']['image_records'].find({}, {'_id': 0})); print(docs)"
```

### Option 2: Query with mongosh

If `mongosh` is installed:

```javascript
mongosh
use image_annotation_system
db.image_records.find().pretty()
```

### Option 3: Use MongoDB Compass

If you prefer a GUI, connect MongoDB Compass to:

```text
mongodb://localhost:27017
```

Then open:

- Database: `image_annotation_system`
- Collection: `image_records`

## Where Data Is Stored

### Uploaded images

Stored here:

- [app/storage/image_db](/mnt/c/Projects/EC528_Event-Driven_Image_Annotation_and_Retrieval_System/app/storage/image_db)

These files are content-addressed using SHA-256, so uploading the exact same image again does not store another duplicate copy.

### MongoDB documents

Stored in MongoDB:

- Database: `image_annotation_system`
- Collection: `image_records`

Each record currently contains fields such as:

- `image_id`
- `image_path`
- `objects`
- `review`

### Vector index

Stored here:

- [app/storage/vector_index_data](/mnt/c/Projects/EC528_Event-Driven_Image_Annotation_and_Retrieval_System/app/storage/vector_index_data)

This directory contains:

- `image_vectors.faiss`
  - the FAISS index itself
- `image_vectors.json`
  - metadata aligned with the FAISS vector positions

## How Retrieval Works

### Topic query

- CLIP converts the topic text into a text embedding
- The text embedding is compared against stored image embeddings in FAISS
- Similarity is based on normalized vector inner product, which behaves like cosine similarity

### Similar image query

- CLIP converts the query image into an image embedding
- The query embedding is compared against stored image embeddings in FAISS
- The system returns the top-k nearest indexed images

## Running Tests

From the project root:

```bash
python3 -m unittest discover -s tests -v
```

Or on Windows:

```powershell
py -3 -m unittest discover -s tests -v
```

## Common Reset / Cleanup Tasks

### Clear MongoDB annotation records

```powershell
py -3 -c "from pymongo import MongoClient; c = MongoClient('mongodb://localhost:27017'); result = c['image_annotation_system']['image_records'].delete_many({}); print(result.deleted_count)"
```

### Remove FAISS vector index files

Delete:

- `app/storage/vector_index_data/image_vectors.faiss`
- `app/storage/vector_index_data/image_vectors.json`

### Remove stored uploaded images

Delete files under:

- `app/storage/image_db/`

Note:

If you manually delete images from `image_db`, MongoDB records and FAISS entries are not automatically deleted. If you want a truly clean reset, clear all three:

- MongoDB documents
- FAISS index files
- Stored image files

## Current Limitations

- Services are run manually in separate terminals
- There is no end-user delete workflow yet
- MongoDB and Redis must already be running locally
- CLIP and YOLO model downloads may happen on first run
- FAISS index metadata is stored in a JSON sidecar file rather than a dedicated metadata database

## Summary

This repository is a full event-driven prototype for:

- image upload
- automatic object annotation
- document database storage
- image embedding
- vector indexing
- text-to-image retrieval
- image-to-image retrieval

If someone new clones this repo, installs the dependencies, starts Redis and MongoDB, and launches the listed services, they should be able to run all three user cases end-to-end.
