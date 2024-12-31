from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    try:
        # Perform a basic database operation to check connectivity
        client.admin.command('ping')
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "UNAVAILABLE"}), 500

@app.route('/count', methods=['GET'])
def count():
    """
    Count endpoint
    """
    try:
        # Get the count of documents in the songs collection
        songs_count = db.songs.count_documents({})
        return jsonify({"count": songs_count}), 200
    except Exception as e:
        app.logger.error(f"Error fetching count: {str(e)}")
        return jsonify({"error": "Unable to fetch count"}), 500

from bson.json_util import dumps

@app.route('/song', methods=['GET'])
def songs():
    """
    Find songs in the database
    """
    try:
        # Retrieve all songs from the database
        songs_cursor = db.songs.find({})
        # Convert the cursor to a list and serialize it to JSON
        songs_list = list(songs_cursor)
        return jsonify({"songs": json.loads(dumps(songs_list))}), 200
    except Exception as e:
        app.logger.error(f"Error fetching songs: {str(e)}")
        return jsonify({"error": "Unable to fetch songs"}), 500

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    """
    Fetch a song by its integer ID from the database
    """
    try:
        song = db.songs.find_one({"id": id})
        if not song:
            return jsonify({"message": f"Song with ID {id} not found"}), 404
        return jsonify(json.loads(json_util.dumps(song))), 200
    except Exception as e:
        app.logger.error(f"Error fetching song by ID: {str(e)}")
        return jsonify({"error": "Unable to fetch song"}), 500

@app.route('/song', methods=['POST'])
def create_song():
    """
    Create a new song in the database
    """
    try:
        # Parse the request data
        song = request.get_json()

        if not song or 'id' not in song or 'lyrics' not in song or 'title' not in song:
            return jsonify({"error": "Invalid request format"}), 400

        # Check if a song with the same ID already exists
        existing_song = db.songs.find_one({"id": song['id']})
        if existing_song:
            return jsonify({"message": f"Song with id {song['id']} already present"}), 302

        # Insert the new song
        result = db.songs.insert_one(song)
        return jsonify({"inserted_id": str(result.inserted_id)}), 201
    except Exception as e:
        app.logger.error(f"Error creating song: {str(e)}")
        return jsonify({"error": "Unable to create song"}), 500

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    """
    Update an existing song by its ID
    """
    try:
        # Parse the request data
        song_data = request.get_json()

        if not song_data or 'lyrics' not in song_data or 'title' not in song_data:
            return jsonify({"error": "Invalid request format"}), 400

        # Find the song by ID
        existing_song = db.songs.find_one({"id": id})
        if not existing_song:
            return jsonify({"message": "Song not found"}), 404

        # Update the song
        update_result: UpdateResult = db.songs.update_one(
            {"id": id}, {"$set": {"lyrics": song_data["lyrics"], "title": song_data["title"]}}
        )

        if update_result.modified_count > 0:
            # Fetch the updated song and return it
            updated_song = db.songs.find_one({"id": id})
            return jsonify(json.loads(json_util.dumps(updated_song))), 201
        else:
            return jsonify({"message": "song found, but nothing updated"}), 200
    except Exception as e:
        app.logger.error(f"Error updating song: {str(e)}")
        return jsonify({"error": "Unable to update song"}), 500

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    """
    Delete a song by its ID
    """
    try:
        # Attempt to delete the song by its ID
        delete_result: DeleteResult = db.songs.delete_one({"id": id})

        if delete_result.deleted_count == 0:
            # If no song was deleted, return 404
            return jsonify({"message": "song not found"}), 404

        # Return 204 No Content for successful deletion
        return '', 204
    except Exception as e:
        app.logger.error(f"Error deleting song: {str(e)}")
        return jsonify({"error": "Unable to delete song"}), 500