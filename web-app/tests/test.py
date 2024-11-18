"""Test code for web-app"""
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
from bson import ObjectId
from app import (
    app,
    search_exercise,
    get_exercise,
    get_todo,
    delete_todo,
    add_todo,
    get_exercise_in_todo,
    edit_exercise,
    get_instruction,
    search_exercise_rigid,
    get_matching_exercises_from_history,
    add_search_history,
    get_search_history,
)

# @pytest.fixture
# def client():
#     with app.test_client() as client:
#         yield client

@pytest.fixture
def client():
    """client fixture"""
    app.config["LOGIN_DISABLED"] = True
    return app.test_client()

### Test edit function ###
@patch("app.get_exercise_in_todo")
def test_edit_get_route(mock_get_exercise_in_todo):
    """Test edit get route"""
    with app.app_context():
        mock_get_exercise_in_todo.return_value = {
            "exercise_todo_id": "123",
            "name": "Test Exercise",
            "reps": 10,
            "weight": 50,
        }

        response = client.get("/edit?exercise_todo_id=123")
        assert response.status_code == 200
        mock_get_exercise_in_todo.assert_called_once_with("123")


@patch("app.edit_exercise")
@patch("app.get_exercise_in_todo")
def test_edit_route(mock_get_exercise_in_todo, mock_edit_exercise):
    """Test edit route"""
    with app.app_context():
        mock_get_exercise_in_todo.return_value = {
            "exercise_todo_id": "123",
            "name": "Test Exercise",
            "reps": "10",
            "weight": "50",
        }

        mock_edit_exercise.return_value = True
        # post request successful
        response = client.post(
            "/edit?exercise_todo_id=123",
            data={"working_time": "30", "weight": "70", "reps": "15"},
        )

        assert response.status_code == 200
        assert b"Edited successfully" in response.data
        mock_edit_exercise.assert_called_once_with("123", "30", "70", "15")

        # post request fail
        mock_edit_exercise.reset_mock()
        mock_edit_exercise.return_value = False

        response = client.post(
            "/edit?exercise_todo_id=123",
            data={"working_time": "30", "weight": "70", "reps": "15"},
        )

        assert response.status_code == 400
        assert b"Failed to edit" in response.data
        mock_edit_exercise.assert_called_once_with("123", "30", "70", "15")


### Test search function ###
@patch("app.search_exercise")
@patch("app.add_search_history")
@patch("app.get_matching_exercises_from_history")
def test_search_route(mock_get_history, mock_add_history, mock_search_exercise):
    """Test search route"""
    with app.app_context():
        mock_get_history.return_value = [
            {"_id": "1", "name": "Push Up"},
            {"_id": "2", "name": "Squats"},
        ]
        response = client.get("/search")

        # valid check
        mock_search_exercise.return_value = [{"_id": "1", "name": "Push Up"}]
        response = client.post("/search", data={"query": "push"})

        # redirect check
        assert response.status_code == 302
        mock_search_exercise.assert_called_once_with("push")
        mock_add_history.assert_called_once_with("push")

        # empty search query
        response = client.post("/search", data={"query": ""})
        assert response.status_code == 400
        assert b"Search content cannot be empty." in response.data

        # non-existent search query
        mock_search_exercise.reset_mock()
        mock_search_exercise.return_value = []
        response = client.post("/search", data={"query": "nonexistent"})

        # fail search
        assert response.status_code == 404
        assert b"Exercise was not found." in response.data
        mock_search_exercise.assert_called_once_with("nonexistent")


### Test add function ###
@patch("app.add_todo")
def test_add_exercise_route(mock_add_todo):
    """Test add exercise route"""
    with app.app_context():
        # add successful
        mock_add_todo.return_value = True
        response = client.post("/add_exercise?exercise_id=123")
        assert response.status_code == 200
        assert b"Added successfully" in response.data
        mock_add_todo.assert_called_once_with("123")

        # miss exercise id to add
        mock_add_todo.reset_mock()
        response = client.post("/add_exercise")
        assert response.status_code == 400
        assert b"Exercise ID is required" in response.data
        mock_add_todo.assert_not_called()

        # add exercise fail
        mock_add_todo.reset_mock()
        mock_add_todo.return_value = False
        response = client.post("/add_exercise?exercise_id=456")

        # add exercise fail
        assert response.status_code == 400
        assert b"Failed to add" in response.data
        mock_add_todo.assert_called_once_with("456")


def test_add_route_with_results_in_session():
    """Test add route with results"""
    with app.app_context():
        with client.session_transaction() as session:
            session["results"] = [
                {"_id": "1", "name": "Push Up"},
                {"_id": "2", "name": "Squats"},
            ]

        response = client.get("/add")
        assert response.status_code == 200
        assert b"exercise_id=1" in response.data
        assert b"exercise_id=2" in response.data
        assert b"const exercisesLength = 2" in response.data


def test_add_route_empty_session():
    """Test add route with empty session"""
    with app.app_context():
        with client.session_transaction() as session:
            session.pop("results", None)

        response = client.get("/add")

        assert response.status_code == 200
        assert b"const exercisesLength = 0" in response.data


### Test delete route ###
@patch("app.get_todo")
def test_delete_exercise_route(mock_get_todo):
    """Test delete exercise route"""
    with app.app_context():
        mock_get_todo.return_value = [
            {"_id": "1", "name": "Push Up"},
            {"_id": "2", "name": "Squats"},
        ]

        response = client.get("/delete_exercise")
        assert response.status_code == 200
        assert b"exercise-" in response.data
        mock_get_todo.assert_called_once()


### Test delete exercise id function ###
@patch("app.delete_todo")
def test_delete_exercise_id_success(mock_delete_todo):
    """Test delete exercise id"""
    mock_delete_todo.return_value = True

    response = client.delete("/delete_exercise/123")

    assert response.status_code == 204
    assert response.data == b""
    mock_delete_todo.assert_called_once_with(123)


@patch("app.delete_todo")
def test_delete_exercise_id_failure(mock_delete_todo):
    """Test delete exercise id fail"""
    mock_delete_todo.return_value = False

    response = client.delete("/delete_exercise/456")
    assert response.status_code == 404
    assert b"Failed to delete" in response.data
    mock_delete_todo.assert_called_once_with(456)


### Test search_exercise function ###
@patch("app.exercises_collection")
def test_search_exercise(mock_exercises_collection):
    """Test search exercise"""
    mock_exercises = [
        {"workout_name": "Push Up"},
        {"workout_name": "Pull Up"},
        {"workout_name": "Sit Up"},
    ]
    mock_exercises_collection.find.return_value = mock_exercises

    query = "up"
    result = search_exercise(query)

    assert result == mock_exercises
    mock_exercises_collection.find.assert_called_once_with(
        {"workout_name": {"$regex": query, "$options": "i"}}
    )


### Test search_exercise_rigid function ###
@patch("app.exercises_collection")
def test_search_exercise_rigid(mock_exercises_collection):
    """Test search exercise rigid"""
    mock_exercises_collection.find.return_value = [
        {"workout_name": "Push Up"},
        {"workout_name": "push up"},
        {"workout_name": "PUSH UP"},
    ]

    result = search_exercise_rigid("Push Up")
    assert result == [
        {"workout_name": "Push Up"},
        {"workout_name": "push up"},
        {"workout_name": "PUSH UP"},
    ]

    mock_exercises_collection.find.assert_called_once_with(
        {"workout_name": {"$regex": "^Push Up$", "$options": "i"}}
    )


### Test get_exercise function ###
@patch("app.exercises_collection")
def test_get_exercise(mock_exercises_collection):
    """Test get exercise"""
    random_object_id = ObjectId()
    mock_exercise = {"_id": random_object_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_object_id)
    result = get_exercise(exercise_id)

    assert result == mock_exercise
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}
    )

### Test get_todo function ###
@patch("app.current_user")
@patch("app.todo_collection")
def test_get_todo_with_todo_list(mock_todo_collection, mock_current_user):
    """Test get todo from the todo list"""
    mock_current_user.id = "user123"

    mock_todo_list = {"user_id": "user123", "todo": ["task1", "task2", "task3"]}
    mock_todo_collection.find_one.return_value = mock_todo_list

    result = get_todo()

    assert result == ["task1", "task2", "task3"]
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_todo_without_todo_list(mock_todo_collection, mock_current_user):
    """Test get todo without todo list"""
    mock_current_user.id = "user123"
    mock_todo_collection.find_one.return_value = None
    result = get_todo()
    assert result == []
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_todo_with_empty_todo_list(mock_todo_collection, mock_current_user):
    """Test get todo with empty todo list"""
    mock_current_user.id = "user123"

    mock_todo_list = {"user_id": "user123"}
    mock_todo_collection.find_one.return_value = mock_todo_list

    result = get_todo()

    assert result == []
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})


### Test delete_todo function ###
@patch("app.current_user")
@patch("app.todo_collection")
def test_delete_todo_success(mock_todo_collection, mock_current_user):
    """Test delete todo successful"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.modified_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = ObjectId()
    result = delete_todo(exercise_todo_id)

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}},
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_delete_todo_failure(mock_todo_collection, mock_current_user):
    """Test delete todo fail"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.modified_count = 0
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = ObjectId()
    result = delete_todo(exercise_todo_id)

    assert result is False
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}},
    )


### Test add_todo function ###
@patch("app.current_user")
@patch("app.exercises_collection")
@patch("app.todo_collection")
def test_add_todo_success(
    mock_todo_collection, mock_exercises_collection, mock_current_user
):
    """Test add todo successful"""
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
        {
            "$push": {
                "todo": {
                    "exercise_todo_id": 1001,
                    "exercise_id": mock_exercise["_id"],
                    "workout_name": mock_exercise["workout_name"],
                    "working_time": None,
                    "reps": None,
                    "weight": None,
                }
            }
        },
    )


@patch("app.current_user")
@patch("app.exercises_collection")
@patch("app.todo_collection")
def test_add_todo_failure(
    mock_todo_collection, mock_exercises_collection, mock_current_user
):
    """Test add todo fail"""
    mock_current_user.id = "user123"

    mock_exercises_collection.find_one.return_value = None

    random_object_id = ObjectId()
    result = add_todo(str(random_object_id))

    assert result is False
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": random_object_id}
    )
    mock_todo_collection.update_one.assert_not_called()
    mock_todo_collection.insert_one.assert_not_called()


@patch("app.current_user")
@patch("app.todo_collection")
def test_edit_exercise_success(mock_todo_collection, mock_current_user):
    """Test edit exercise successful"""
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
        {
            "$set": {
                "todo.$.working_time": working_time,
                "todo.$.weight": weight,
                "todo.$.reps": reps,
            }
        },
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_edit_exercise_no_fields_to_update(mock_todo_collection, mock_current_user):
    """Test edit exercise with no update"""
    mock_current_user.id = "user123"

    exercise_todo_id = 1001
    working_time = None
    weight = None
    reps = None
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is False
    mock_todo_collection.update_one.assert_not_called()


@patch("app.current_user")
@patch("app.todo_collection")
def test_edit_exercise_not_found(mock_todo_collection, mock_current_user):
    """Test edit exercise with no result found"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.matched_count = 0
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = 1001
    working_time = 20
    weight = 60
    reps = 5
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is False
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id, "todo.exercise_todo_id": exercise_todo_id},
        {
            "$set": {
                "todo.$.working_time": working_time,
                "todo.$.weight": weight,
                "todo.$.reps": reps,
            }
        },
    )


### Test get_exercise_in_todo function ###
@patch("app.current_user")
@patch("app.todo_collection")
def test_get_exercise_in_todo_found(mock_todo_collection, mock_current_user):
    """Test get exercise in todo"""
    mock_current_user.id = "user123"

    random_exercise_id_1 = ObjectId()
    random_exercise_id_2 = ObjectId()

    mock_todo_item = {
        "user_id": "user123",
        "todo": [
            {
                "exercise_todo_id": 1001,
                "exercise_id": random_exercise_id_1,
                "workout_name": "Push Up",
            },
            {
                "exercise_todo_id": 1002,
                "exercise_id": random_exercise_id_2,
                "workout_name": "Pull Up",
            },
        ],
    }
    mock_todo_collection.find_one.return_value = mock_todo_item

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result == {
        "exercise_todo_id": 1001,
        "exercise_id": random_exercise_id_1,
        "workout_name": "Push Up",
    }
    mock_todo_collection.find_one.assert_called_once_with(
        {"user_id": mock_current_user.id}
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_exercise_in_todo_not_found(mock_todo_collection, mock_current_user):
    """Test get exercise in todo with no results found"""
    mock_current_user.id = "user123"

    random_exercise_id_1 = ObjectId()
    mock_todo_item = {
        "user_id": "user123",
        "todo": [
            {
                "exercise_todo_id": 1002,
                "exercise_id": random_exercise_id_1,
                "workout_name": "Pull Up",
            }
        ],
    }
    mock_todo_collection.find_one.return_value = mock_todo_item

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result is None
    mock_todo_collection.find_one.assert_called_once_with(
        {"user_id": mock_current_user.id}
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_exercise_in_todo_no_todo_item(mock_todo_collection, mock_current_user):
    """Test get exercise in todo with no todo item"""
    mock_current_user.id = "user123"

    mock_todo_collection.find_one.return_value = None

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result is None
    mock_todo_collection.find_one.assert_called_once_with(
        {"user_id": mock_current_user.id}
    )


### Test get_instruction function ###
@patch("app.exercises_collection")
def test_get_instruction_with_instruction(mock_exercises_collection):
    """Test get instructions with instruction"""
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")
    mock_exercise = {
        "_id": random_exercise_id,
        "workout_name": "Push Up",
        "instruction": "Slowly lower your body to the ground, then push back up.",
    }
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "workout_name": "Push Up",
        "instruction": "Slowly lower your body to the ground, then push back up.",
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )


@patch("app.exercises_collection")
def test_get_instruction_without_instruction(mock_exercises_collection):
    """Test get instruction without instruction"""
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")
    mock_exercise = {"_id": random_exercise_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "workout_name": "Push Up",
        "instruction": "No instructions available for this exercise.",
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )


@patch("app.exercises_collection")
def test_get_instruction_not_found(mock_exercises_collection):
    """Test get instruction with no result found"""
    mock_exercises_collection.find_one.return_value = None
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {"error": f"Exercise with ID {exercise_id} not found."}
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )


### Test get_matching_exercises_from_history function ###
@patch("app.get_search_history")
@patch("app.search_exercise_rigid")
def test_get_matching_exercises_from_history_empty_history(
    mock_search_exercise_rigid, mock_get_search_history
):
    """Test get matching exercise from history"""
    mock_get_search_history.return_value=[]
    result = get_matching_exercises_from_history()
    assert not result, "Expected an empty list when search history is empty"
    mock_search_exercise_rigid.assert_not_called()  # search_exercise_rigid should not be called


@patch(
    "app.get_search_history",
)
@patch("app.search_exercise_rigid")
def test_get_matching_exercises_from_history_with_matches(
    mock_search_exercise_rigid, mock_get_search_history
):
    """Test get matching exercise from history"""
    mock_get_search_history.return_value=[{"content": "exercise1"}, {"content": "exercise2"}]
    # search_exercise_rigid to return specific results for each content name
    mock_search_exercise_rigid.side_effect = lambda name: [{"name": f"matching_{name}"}]
    result = get_matching_exercises_from_history()

    expected_result = [{"name": "matching_exercise1"}, {"name": "matching_exercise2"}]
    assert (
        result == expected_result
    ), "Expected list of matching exercises based on search history content"
    mock_search_exercise_rigid.assert_any_call("exercise1")
    mock_search_exercise_rigid.assert_any_call("exercise2")


@patch(
    "app.get_search_history"
)
@patch("app.search_exercise_rigid")
def test_get_matching_exercises_from_history_with_partial_matches(
    mock_search_exercise_rigid, mock_get_search_history
):
    """Test get matching exercise from history with partial match"""
    mock_get_search_history.return_value=[{"content": "exercise1"}, {"content": "exercise2"}]
    # Mock search_exercise_rigid to return an empty list
    mock_search_exercise_rigid.side_effect = lambda name: (
        [{"name": "matching_exercise1"}] if name == "exercise1" else []
    )
    result = get_matching_exercises_from_history()

    expected_result = [{"name": "matching_exercise1"}]
    assert (
        result == expected_result
    ), "Expected list with only matching exercises where results were found"
    mock_search_exercise_rigid.assert_any_call("exercise1")
    mock_search_exercise_rigid.assert_any_call("exercise2")


### Test register function ###
def test_register_missing_username_password():
    """Test register with missing username password"""
    # missing username
    response = client.post("/register", data={"password": "testpassword"})
    assert response.status_code == 400
    assert response.json["message"] == "Username and password are required!"

    # missing password
    response = client.post("/register", data={"username": "testuser"})
    assert response.status_code == 400
    assert response.json["message"] == "Username and password are required!"


# existing username
@patch("app.users_collection.find_one")
def test_register_existing_username(mock_find_one):
    """Test register with existing usernamepy"""
    mock_find_one.return_value = {"username": "testuser"}

    response = client.post(
        "/register", data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 400
    assert response.json["message"] == "Username already exists!"


# successful registration
@patch("app.users_collection.find_one")
@patch("app.users_collection.insert_one")
@patch("app.todo_collection.insert_one")
@patch("app.generate_password_hash")
def test_register_successful(
    mock_generate_password_hash,
    mock_insert_todo,
    mock_insert_user,
    mock_find_one
):
    """Test register successful"""
    mock_find_one.return_value = None
    mock_generate_password_hash.return_value = "hashed_password"
    mock_insert_user.return_value.inserted_id = "mock_user_id"
    mock_insert_todo.return_value = MagicMock()

    response = client.post(
        "/register", data={"username": "newuser", "password": "newpassword"}
    )
    response_datetime = datetime.utcnow()

    assert response.status_code == 200
    assert response.json["message"] == "Registration successful! Please log in."
    assert response.json["success"] is True
    mock_generate_password_hash.assert_called_once_with(
        "newpassword", method="pbkdf2:sha256"
    )
    mock_insert_user.assert_called_once_with(
        {"username": "newuser", "password": "hashed_password"}
    )

    # ignore tiny time differences
    actual_call_args = mock_insert_todo.call_args[0][0]
    assert actual_call_args["user_id"] == "mock_user_id"
    assert actual_call_args["date"].replace(microsecond=0) == response_datetime.replace(
        microsecond=0
    )
    assert actual_call_args["todo"] == []


### Test login page function ###
def test_login_page():
    """Test login page"""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


# sign up page
def test_signup_page():
    """Test signup page"""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Sign Up" in response.data


### Test login function ###
@patch("app.users_collection.find_one")
@patch("app.check_password_hash")
@patch("app.login_user")
def test_login_success(
    mock_login_user, mock_check_password_hash, mock_find_one
):
    """Test login successful"""
    mock_find_one.return_value = {
        "_id": "mock_user_id",
        "username": "testuser",
        "password": "hashed_password",
    }
    mock_check_password_hash.return_value = True
    response = client.post(
        "/login", data={"username": "testuser", "password": "testpassword"}
    )

    assert response.status_code == 200
    assert response.json == {"message": "Login successful!", "success": True}
    mock_login_user.assert_called_once()


# Invalid username
@patch("app.users_collection.find_one")
def test_login_invalid_username(mock_find_one):
    """Test login with invalid username"""
    # user not found in the database
    mock_find_one.return_value = None
    response = client.post(
        "/login", data={"username": "unknownuser", "password": "testpassword"}
    )

    assert response.status_code == 401
    assert response.json == {
        "message": "Invalid username or password!",
        "success": False,
    }


# Invalid password
@patch("app.users_collection.find_one")
@patch("app.check_password_hash")
def test_login_invalid_password(mock_check_password_hash, mock_find_one):
    """Test login with invalid password"""
    mock_find_one.return_value = {
        "_id": "mock_user_id",
        "username": "testuser",
        "password": "hashed_password",
    }
    mock_check_password_hash.return_value = False

    response = client.post(
        "/login", data={"username": "testuser", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert response.json == {
        "message": "Invalid username or password!",
        "success": False,
    }


@patch("app.current_user")
@patch("app.search_history_collection")
def test_add_search_history(mock_search_history_collection, mock_current_user):
    """Test adding search history."""
    mock_current_user.id = "user123"

    content = "Test Search Content"
    add_search_history(content)
    mock_search_history_collection.insert_one.assert_called_once()

    inserted_entry = mock_search_history_collection.insert_one.call_args[0][0]

    assert inserted_entry["user_id"] == "user123"
    assert inserted_entry["content"] == content
    assert isinstance(inserted_entry["time"], datetime)


@patch("app.current_user")
@patch("app.search_history_collection")
def test_get_search_history(mock_search_history_collection, mock_current_user):
    """Test getting search history"""
    mock_current_user.id = "user123"
    mock_results = [
        {
            "user_id": "user123",
            "content": "Test Content 1",
            "time": datetime(2024, 11, 12, 12, 0, 0),
        },
        {
            "user_id": "user123",
            "content": "Test Content 2",
            "time": datetime(2024, 11, 12, 11, 0, 0),
        },
    ]
    mock_search_history_collection.find.return_value.sort.return_value = mock_results

    history = get_search_history()

    assert len(history) == 2
    assert history[0]["content"] == "Test Content 1"
    assert history[1]["content"] == "Test Content 2"
    mock_search_history_collection.find.assert_called_once_with(
        {"user_id": "user123"}, {"_id": 0, "user_id": 1, "content": 1, "time": 1}
    )


@patch("app.get_exercise")
def test_instructions_route(mock_get_exercise):
    """Test instruction route."""
    mock_exercise = {
        "_id": "exercise123",
        "workout_name": "Push Up",
        "description": "A great upper body workout.",
        "instruction": "Make sure to keep your back straight while performing this exercise.",
    }
    mock_get_exercise.return_value = mock_exercise

    response = client.get("/instructions?exercise_id=exercise123")

    assert response.status_code == 200

    assert b"A great upper body workout." in response.data
    assert (
        b"Make sure to keep your back straight while performing this exercise."
        in response.data
    )


if __name__ == "__main__":
    pytest.main()