
# Task Management CRUD API

## About
A simple REST API developed using Python and FastAPI
for the FlyRank Backend AI Engineering Internship.

## Technologies
- Python
- FastAPI
- Uvicorn
- Swagger UI

## Installation

Clone the repository:

git clone https://github.com/YOUR_USERNAME/flyrank-task-api.git

Navigate to the project:

cd flyrank-task-api

Create virtual environment:

python3 -m venv venv

Activate environment:

source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Run the application:

uvicorn main:app --reload

## API Documentation

Swagger UI:
http://localhost:8000/docs

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | / | API information |
| GET | /health | Health check |
| GET | /tasks | Get all tasks |
| GET | /tasks/{id} | Get one task |
| POST | /tasks | Create task |
| PUT | /tasks/{id} | Update task |
| DELETE | /tasks/{id} | Delete task |

## Status Codes

- 200: Successful request
- 201: Task created
- 204: Task deleted
- 400: Invalid input
- 404: Task not found

## Storage

Tasks are stored in an in-memory Python list.
Data resets when the server restarts.

## Screenshots

Add your Swagger UI screenshots here.
