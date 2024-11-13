import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId
from datetime import datetime
from flask import Flask
from flask_login import FlaskLoginClient, login_user
from app import User, app, search_exercise, get_exercise, get_todo, delete_todo, add_todo, get_exercise_in_todo, edit_exercise, get_instruction, add_search_history, get_search_history

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

### Test search_exercise function ###
@patch('app.exercises_collection')
def test_search_exercise(mock_exercises_collection):
    mock_exercises = [
        {"workout_name": "Push Up"},
        {"workout_name": "Pull Up"},
        {"workout_name": "Sit Up"}
    ]
    mock_exercises_collection.find.return_value = mock_exercises

    query = "up"
    result = search_exercise(query)

    assert result == mock_exercises
    mock_exercises_collection.find.assert_called_once_with({
        "workout_name": {
            "$regex": query,
            "$options": "i"
        }
    })

### Test get_exercise function ###
@patch('app.exercises_collection')
def test_get_exercise(mock_exercises_collection):
    random_object_id = ObjectId()
    mock_exercise = {"_id": random_object_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_object_id)
    result = get_exercise(exercise_id)

    assert result == mock_exercise
    mock_exercises_collection.find_one.assert_called_once_with({"_id": ObjectId(exercise_id)})

### Test get_todo function ###
@patch('app.current_user')
@patch('app.todo_collection')
def test_get_todo_with_todo_list(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_todo_list = {"user_id": "user123", "todo": ["task1", "task2", "task3"]}
    mock_todo_collection.find_one.return_value = mock_todo_list

    result = get_todo()

    assert result == ["task1", "task2", "task3"]
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})

@patch('app.current_user')
@patch('app.todo_collection')
def test_get_todo_without_todo_list(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"
    mock_todo_collection.find_one.return_value = None
    result = get_todo()
    assert result == []
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})

@patch('app.current_user')
@patch('app.todo_collection')
def test_get_todo_with_empty_todo_list(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_todo_list = {"user_id": "user123"}
    mock_todo_collection.find_one.return_value = mock_todo_list

    result = get_todo()

    assert result == []
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})

### Test delete_todo function ###
@patch('app.current_user')
@patch('app.todo_collection')
def test_delete_todo_success(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.modified_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = ObjectId()
    result = delete_todo(exercise_todo_id)

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}}
    )

@patch('app.current_user')
@patch('app.todo_collection')
def test_delete_todo_failure(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.modified_count = 0
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = ObjectId()
    result = delete_todo(exercise_todo_id)

    assert result is False
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}}
    )

### Test add_todo function ###
@patch('app.current_user')
@patch('app.exercises_collection')
@patch('app.todo_collection')
def test_add_todo_success(mock_todo_collection, mock_exercises_collection, mock_current_user):
    mock_current_user.id = "user123"

    random_object_id = ObjectId()
    mock_exercise = {"_id": random_object_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    mock_todo = {"user_id": "user123", "todo": [{"exercise_todo_id": 1000}]}
    mock_todo_collection.find_one.return_value = mock_todo

    mock_result = MagicMock()
    mock_result.modified_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    result = add_todo(str(random_object_id))

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": "user123"},
        {"$push": {"todo": {
            "exercise_todo_id": 1001,
            "exercise_id": mock_exercise['_id'],
            "workout_name": mock_exercise["workout_name"],
            "working_time": None,
            "reps": None,
            "weight": None
        }}}
    )

@patch('app.current_user')
@patch('app.exercises_collection')
@patch('app.todo_collection')
def test_add_todo_failure(mock_todo_collection, mock_exercises_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_exercises_collection.find_one.return_value = None

    random_object_id = ObjectId()
    result = add_todo(str(random_object_id))

    assert result is False
    mock_exercises_collection.find_one.assert_called_once_with({"_id": random_object_id})
    mock_todo_collection.update_one.assert_not_called()
    mock_todo_collection.insert_one.assert_not_called()

@patch('app.current_user')
@patch('app.todo_collection')
def test_edit_exercise_success(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.matched_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = 1001
    working_time = 30
    weight = 50
    reps = 10
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": "user123", "todo.exercise_todo_id": exercise_todo_id},
        {"$set": {
            "todo.$.working_time": working_time,
            "todo.$.weight": weight,
            "todo.$.reps": reps
        }}
    )

@patch('app.current_user')
@patch('app.todo_collection')
def test_edit_exercise_no_fields_to_update(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    exercise_todo_id = 1001
    working_time = None
    weight = None
    reps = None
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is False
    mock_todo_collection.update_one.assert_not_called()

@patch('app.current_user')
@patch('app.todo_collection')
def test_edit_exercise_not_found(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.matched_count = 0
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = 1001
    working_time = 30
    weight = 50
    reps = 10
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is False
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id, "todo.exercise_todo_id": exercise_todo_id},
        {"$set": {
            "todo.$.working_time": working_time,
            "todo.$.weight": weight,
            "todo.$.reps": reps
        }}
    )

### Test get_exercise_in_todo function ###
@patch('app.current_user')
@patch('app.todo_collection')
def test_get_exercise_in_todo_found(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    random_exercise_id_1 = ObjectId()
    random_exercise_id_2 = ObjectId()

    mock_todo_item = {
        "user_id": "user123",
        "todo": [
            {"exercise_todo_id": 1001, "exercise_id": random_exercise_id_1, "workout_name": "Push Up"},
            {"exercise_todo_id": 1002, "exercise_id": random_exercise_id_2, "workout_name": "Pull Up"}
        ]
    }
    mock_todo_collection.find_one.return_value = mock_todo_item

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result == {"exercise_todo_id": 1001, "exercise_id": random_exercise_id_1, "workout_name": "Push Up"}
    mock_todo_collection.find_one.assert_called_once_with({"user_id": mock_current_user.id})

@patch('app.current_user')
@patch('app.todo_collection')
def test_get_exercise_in_todo_not_found(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    random_exercise_id_1 = ObjectId()
    mock_todo_item = {
        "user_id": "user123",
        "todo": [
            {"exercise_todo_id": 1002, "exercise_id": random_exercise_id_1, "workout_name": "Pull Up"}
        ]
    }
    mock_todo_collection.find_one.return_value = mock_todo_item

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result is None
    mock_todo_collection.find_one.assert_called_once_with({"user_id": mock_current_user.id})

@patch('app.current_user')
@patch('app.todo_collection')
def test_get_exercise_in_todo_no_todo_item(mock_todo_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_todo_collection.find_one.return_value = None

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result is None
    mock_todo_collection.find_one.assert_called_once_with({"user_id": mock_current_user.id})

### Test get_instruction function ###
@patch('app.exercises_collection')
def test_get_instruction_with_instruction(mock_exercises_collection):
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")
    mock_exercise = {
        "_id": random_exercise_id,
        "workout_name": "Push Up",
        "instruction": "Slowly lower your body to the ground, then push back up."
    }
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "workout_name": "Push Up",
        "instruction": "Slowly lower your body to the ground, then push back up."
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)},
        {"instruction": 1, "workout_name": 1}
    )

@patch('app.exercises_collection')
def test_get_instruction_without_instruction(mock_exercises_collection):
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")
    mock_exercise = {
        "_id": random_exercise_id,
        "workout_name": "Push Up"
    }
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "workout_name": "Push Up",
        "instruction": "No instructions available for this exercise."
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)},
        {"instruction": 1, "workout_name": 1}
    )

@patch('app.exercises_collection')
def test_get_instruction_not_found(mock_exercises_collection):
    mock_exercises_collection.find_one.return_value = None
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "error": f"Exercise with ID {exercise_id} not found."
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)},
        {"instruction": 1, "workout_name": 1}
    )

@patch('app.current_user')
@patch('app.search_history_collection')
def test_add_search_history(mock_search_history_collection, mock_current_user):
    mock_current_user.id = "user123"

    content = "Test Search Content"
    add_search_history(content)
    mock_search_history_collection.insert_one.assert_called_once()

    inserted_entry = mock_search_history_collection.insert_one.call_args[0][0]
    
    assert inserted_entry["user_id"] == "user123"
    assert inserted_entry["content"] == content
    assert isinstance(inserted_entry["time"], datetime)

@patch('app.current_user')
@patch('app.search_history_collection')
def test_get_search_history(mock_search_history_collection, mock_current_user):
    mock_current_user.id = "user123"

    mock_results = [
        {"user_id": "user123", "content": "Test Content 1", "time": datetime(2024, 11, 12, 12, 0, 0)},
        {"user_id": "user123", "content": "Test Content 2", "time": datetime(2024, 11, 12, 11, 0, 0)},
    ]
    mock_search_history_collection.find.return_value.sort.return_value = mock_results

    history = get_search_history()

    assert len(history) == 2
    assert history[0]["content"] == "Test Content 1"
    assert history[1]["content"] == "Test Content 2"
    mock_search_history_collection.find.assert_called_once_with(
        {"user_id": "user123"}, 
        {"_id": 0, "user_id": 1, "content": 1, "time": 1}
    )

@patch('app.get_exercise')
def test_instructions_route(mock_get_exercise, client):
    mock_exercise = {
        "_id": "exercise123",
        "workout_name": "Push Up",
        "description": "A great upper body workout.",
        "instruction": "Make sure to keep your back straight while performing this exercise."
    }
    mock_get_exercise.return_value = mock_exercise

    response = client.get('/instructions?exercise_id=exercise123')

    assert response.status_code == 200

    assert b'A great upper body workout.' in response.data
    assert b'Make sure to keep your back straight while performing this exercise.' in response.data

if __name__ == "__main__":
    pytest.main()
