import os
from flask import Flask, request, redirect, url_for, flash, render_template, jsonify, session
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import certifi
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import re

load_dotenv()

mongo_uri = os.getenv('MONGO_URI')

app = Flask(__name__)
app.secret_key = os.urandom(13)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())

try:
    client.admin.command('ping')  
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

db = client['fitness_db']
todo_collection = db['todo']
exercises_collection = db['exercises']
users_collection = db['users']
search_history_collection = db['search_history']

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, username, password):
        self.id = user_id
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        user_data = users_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(str(user_data['_id']), user_data['username'], user_data['password'])
        return None


def normalize_text(text: str) -> str:

    text = re.sub(r'[\s\-]', '', text) 
    return text.lower()  

def search_exercise(query: str):

    normalized_query = normalize_text(query)  

    exercises = exercises_collection.find({
        "$expr": {
            "$regexMatch": {
                "input": {
                    "$replaceAll": {
                        "input": {"$replaceAll": {"input": "$workout_name", "find": "-", "replacement": ""}},
                        "find": " ",
                        "replacement": ""
                    }
                },
                "regex": normalized_query,
                "options": "i"  
            }
        }
    })

    exercises_list = list(exercises)
    return exercises_list

def search_exercise_rigid(query: str):

    normalized_query = normalize_text(query) 

    exercises = exercises_collection.find({
        "$expr": {
            "$eq": [
                {
                    "$toLower": {
                        "$replaceAll": {
                            "input": {
                                "$replaceAll": {"input": "$workout_name", "find": "-", "replacement": ""}
                            },
                            "find": " ",
                            "replacement": ""
                        }
                    }
                },
                normalized_query
            ]
        }
    })

    exercises_list = list(exercises)
    return exercises_list

def get_exercise(exercise_id: str):
    return exercises_collection.find_one({"_id": ObjectId(exercise_id)})


def get_todo():
    todo_list = todo_collection.find_one({"user_id": current_user.id})
    if todo_list and "todo" in todo_list:
        return todo_list['todo']
    return []


def delete_todo(exercise_todo_id: int):
    result = todo_collection.update_one(
        {"user_id": current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}}
    )
    
    if result.modified_count > 0:
        # print(f"Exercise with To-Do ID {exercise_todo_id} deleted from To-Do List.")
        return True
    else:
        # print(f"Exercise with To-Do ID {exercise_todo_id} not found.")
        return False


def add_todo(exercise_id: str, working_time=None, reps=None, weight=None):
    exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})

    if exercise:

        todo = todo_collection.find_one({"user_id": current_user.id})

        if todo and "todo" in todo:
            max_id = max([item.get("exercise_todo_id", 999) for item in todo["todo"]], default=999)
            next_exercise_todo_id = max_id + 1  
        else:
            next_exercise_todo_id = 1000  

        exercise_item = {
            "exercise_todo_id": next_exercise_todo_id,  
            "exercise_id": exercise['_id'], 
            "workout_name": exercise["workout_name"],
            "working_time": working_time,
            "reps": reps,
            "weight": weight
        }

        if todo:
            result = todo_collection.update_one(
                {"user_id": current_user.id},
                {"$push": {"todo": exercise_item}}
            )
            success = result.modified_count > 0
        else:
            result = todo_collection.insert_one({
                "user_id": current_user.id,
                "todo": [exercise_item]
            })
            success = result.inserted_id is not None

        if success:
            return True
        else:
            return False
    else:
        return False


def edit_exercise(exercise_todo_id, working_time, weight, reps):
    exercise_todo_id = int(exercise_todo_id)
    update_fields = {}
    
    if working_time is not None:
        update_fields["todo.$.working_time"] = working_time
    if reps is not None:
        update_fields["todo.$.reps"] = reps
    if weight is not None:
        update_fields["todo.$.weight"] = weight
    
    if not update_fields:
        # print("No fields to update.")
        return False  

    result = todo_collection.update_one(
        {"user_id": current_user.id, "todo.exercise_todo_id": exercise_todo_id},
        {"$set": update_fields}
    )
    
    if result.matched_count > 0:  
        return True
    else:
        # print(f"Exercise with To-Do ID {exercise_todo_id} not found.")
        return False

def add_search_history(content):
    search_entry = {
        "user_id": current_user.id,
        "content": content,
        "time": datetime.utcnow()
    }
    result = search_history_collection.insert_one(search_entry)

# test function needed #
def get_search_history():
    results = search_history_collection.find(
        {"user_id": current_user.id}, 
        {"_id": 0, "user_id": 1, "content": 1, "time": 1}
    ).sort("time", -1)

    history = list(results)
    return history
  
def get_exercise_in_todo(exercise_todo_id: int):
    todo_item = todo_collection.find_one({"user_id": current_user.id})
    
    if not todo_item:
        # print(f"Document with _id 1 not found.")
        return None
    
    # print(f"todo_item found: {todo_item}")
    
    for item in todo_item.get('todo', []):
        # print(f"Checking item: {item}")
        if item.get('exercise_todo_id') == int(exercise_todo_id):
            return item

    # print(f"Exercise with To-Do ID {exercise_todo_id} not found in the list.")
    return None


def get_instruction(exercise_id: str):
    exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1})
    
    if exercise:
        if "instruction" in exercise:
            return {
                "workout_name": exercise.get("workout_name", "Unknown Workout"),
                "instruction": exercise["instruction"]
            }
        else:
            return {
                "workout_name": exercise.get("workout_name", "Unknown Workout"),
                "instruction": "No instructions available for this exercise."
            }
    else:
        return {
            "error": f"Exercise with ID {exercise_id} not found."
        }

# test function needed #
def get_matching_exercises_from_history():
    history = get_search_history()
    #print('history is: ', history)

    content_names = [entry['content'] for entry in history]
    #print('content name is:', content_names)

    matching_exercises_list = []
    for name in content_names:
        matching_exercises = search_exercise_rigid(name)
        matching_exercises_list.extend(matching_exercises)

    #print('matching exercises are:', matching_exercises_list)
    return matching_exercises_list 

@app.route('/')
def home():
    return redirect(url_for('todo'))

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required!'}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({'message': 'Username already exists!'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    user_id = users_collection.insert_one({"username": username, "password": hashed_password}).inserted_id

    todo_collection.insert_one({
        "user_id": str(user_id), 
        "date": datetime.utcnow(),
        "todo": []
    })

    return jsonify({'message': 'Registration successful! Please log in.', 'success': True}), 200


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def signup_page():
    return render_template('signup.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user_data = users_collection.find_one({"username": username})
    
    if user_data and check_password_hash(user_data['password'], password):
        user = User(str(user_data['_id']), user_data['username'], user_data['password'])
        login_user(user)
        return jsonify({'message': 'Login successful!', 'success': True}), 200  
    else:
        return jsonify({'message': 'Invalid username or password!', 'success': False}), 401


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == 'POST':
        query = request.form.get("query")
        if not query:
            return jsonify({'message': 'Search content cannot be empty.'}), 400
        results = search_exercise(query)
        #printf('results are', results)
        if len(results) == 0:
            return jsonify({'message': 'Exercise was not found.'}), 404
        
        for result in results:
            result['_id'] = str(result['_id'])
        session['results'] = results
        add_search_history(query)
        return redirect(url_for('add'))

    exercises = get_matching_exercises_from_history()
    #print('current result should be: ', exercises)

    return render_template('search.html', exercises=exercises)


@app.route('/todo')
@login_required
def todo():
    exercises = get_todo()
    return render_template('todo.html', exercises=exercises)


@app.route('/delete_exercise')
@login_required
def delete_exercise():
    exercises = get_todo()
    return render_template('delete.html', exercises=exercises)


@app.route('/delete_exercise/<int:exercise_todo_id>', methods=['DELETE'])
def delete_exercise_id(exercise_todo_id):
    success = delete_todo(exercise_todo_id)
    if success:
        return jsonify({'message': 'Deleted successfully'}), 204
    else:
        return jsonify({'message': 'Failed to delete'}), 404


@app.route('/add')
@login_required
def add():
    if 'results' in session:
        exercises = session['results']
    else:
        exercises = [] 

    return render_template('add.html', exercises=exercises, exercises_length=len(exercises))


@app.route('/add_exercise', methods=['POST'])
@login_required
def add_exercise():
    exercise_id = request.args.get('exercise_id')
    
    #print(f"Received request to add exercise with ID: {exercise_id}")
    
    if not exercise_id:
        print("No exercise ID provided")
        return jsonify({'message': 'Exercise ID is required'}), 400

    success = add_todo(exercise_id)  

    if success:
        print(f"Successfully added exercise with ID: {exercise_id}")
        return jsonify({'message': 'Added successfully'}), 200
    else:
        print(f"Failed to add exercise with ID: {exercise_id}")
        return jsonify({'message': 'Failed to add'}), 400


@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    exercise_todo_id = request.args.get('exercise_todo_id')  
    exercise_in_todo = get_exercise_in_todo(exercise_todo_id)
    
    if request.method == 'POST':
        working_time = request.form.get('working_time')
        weight = request.form.get('weight')
        reps = request.form.get('reps')
        success = edit_exercise(exercise_todo_id, working_time, weight, reps)
        if success:
            return jsonify({'message': 'Edited successfully'}), 200
        else:
            return jsonify({'message': 'Failed to edit'}), 400

    return render_template('edit.html', exercise_todo_id=exercise_todo_id, exercise=exercise_in_todo)


@app.route('/instructions', methods=['GET'])
def instructions():
    exercise_id = request.args.get('exercise_id')  
    exercise = get_exercise(exercise_id)

    return render_template('instructions.html', exercise=exercise)

'''@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    # Save the uploaded audio file
    audio = request.files['audio']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], audio.filename)
    audio.save(file_path)

    # Call the Speech-to-Text container
    transcription = call_speech_to_text_service(file_path)

    return jsonify({"transcription": transcription})

def call_speech_to_text_service(file_path):
    url = 'http://machine-learning-client:8080/transcribe'  
    print(f"Sending request to {url} with file: {file_path}")
    with open(file_path, 'rb') as audio_file:
        files = {'audio': (file_path, audio_file, 'audio/wav')}
        try:
            response = requests.post(url, files=files)
            print(f"Received response status: {response.status_code}, body: {response.text}")
            response.raise_for_status()
            return response.json().get('transcript', 'No transcription returned')
        except requests.RequestException as e:
            print(f"Error communicating with the Speech-to-Text service: {e}")
            return "Error during transcription"
'''
import subprocess
import os

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    # Save the uploaded audio file
    audio = request.files['audio']
    original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], audio.filename)
    audio.save(original_file_path)

    # Convert the audio file to WAV using ffmpeg
    wav_file_path = os.path.splitext(original_file_path)[0] + '_converted.wav'
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', original_file_path, '-ar', '16000', '-ac', '1', wav_file_path],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error converting audio to WAV: {e}")
        return jsonify({"error": "Failed to convert audio file"}), 500

    # Call the Speech-to-Text container with the converted WAV file
    transcription = call_speech_to_text_service(wav_file_path)

    return jsonify({"transcription": transcription})

def call_speech_to_text_service(file_path):
    url = 'http://machine-learning-client:8080/transcribe'
    data = {"audio_file": file_path}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get('transcript', 'No transcription returned')
    except requests.RequestException as e:
        print(f"Error communicating with the Speech-to-Text service: {e}")
        return "Error during transcription"
def parse_voice_command(transcription):

    exercise_match = re.search(r"exercise\s+['\"](.+?)['\"]", transcription, re.IGNORECASE)
    exercise_name = exercise_match.group(1) if exercise_match else None

    time_match = re.search(r"(\d+)\s*minutes?\s*(\d+)?\s*seconds?", transcription, re.IGNORECASE)
    time_params = {
        "minutes": int(time_match.group(1)) if time_match else 0,
        "seconds": int(time_match.group(2)) if time_match and time_match.group(2) else 0,
    } if time_match else None

    if not exercise_name:
        print("Failed to parse exercise name from transcription.")
        return None

    return {
        "exercise": exercise_name,
        "time": time_params
    }

def get_latest_todo_id():

    todo_list = get_todo()
    if not todo_list:
        return None
    return max(item["exercise_todo_id"] for item in todo_list if "exercise_todo_id" in item)


@app.route('/add_with_voice', methods=['POST'])
@login_required
def add_with_voice():
    if 'audio' not in request.files:
        return jsonify({'message': 'No audio file provided!'}), 400

    audio_file = request.files['audio']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], audio_file.filename)
    audio_file.save(filepath)


    transcription = call_speech_to_text_service(filepath)
    if not transcription:
        return jsonify({'message': 'Failed to transcribe audio!'}), 500


    parsed_data = parse_voice_command(transcription)
    if not parsed_data:
        return jsonify({'message': 'Failed to parse voice command!'}), 400

    exercise_name = parsed_data.get("exercise")
    time_params = parsed_data.get("time")


    exercises = search_exercise(exercise_name)
    if not exercises:
        return jsonify({'message': f'Exercise "{exercise_name}" not found!'}), 404


    exercise_id = str(exercises[0]["_id"])

    success = add_todo(exercise_id)
    if not success:
        return jsonify({'message': 'Failed to add exercise to To-Do list!'}), 500


    if time_params:
        exercise_todo_id = get_latest_todo_id()
        if not exercise_todo_id:
            return jsonify({'message': 'Failed to retrieve latest To-Do item!'}), 500

        edit_success = edit_exercise(
            exercise_todo_id,
            working_time=f"{time_params['minutes']}:{time_params['seconds']}",
            weight=None,
            reps=None
        )
        if not edit_success:
            return jsonify({'message': 'Failed to update exercise time!'}), 500

    return jsonify({
        'message': 'Exercise added and updated successfully!',
        'exercise': exercise_name,
        'time': time_params
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
