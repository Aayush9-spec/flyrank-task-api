from database import init_db, get_all_tasks, get_task_by_id, create_task
from fastapi import FastAPI, Body, Request
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from typing import Any

app = FastAPI(
    title="Task Management API",
    description="A simple CRUD API built for FlyRank Internship BE-01",
    version="1.0"
)

@app.on_event("startup")
def startup_event():
    init_db()


# Temporary in-memory storage for POST, PUT and DELETE
tasks = [
    {"id": 1, "title": "Learn Python", "done": True},
    {"id": 2, "title": "Learn FastAPI", "done": False},
    {"id": 3, "title": "Build CRUD API", "done": False}
]



# Return 400 for invalid request bodies
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body or parameters"}
    )


# Stage 1: Root endpoint
@app.get("/")
def home():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }


# Health check
@app.get("/health")
def health():
    return {"status": "ok"}


# Stage 2: Get all tasks
# Stage 1: Get all tasks from SQLite
@app.get("/tasks")
def get_tasks():
    return get_all_tasks()


# Get one task from SQLite
@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = get_task_by_id(task_id)

    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return task


# Stage 3: Create a task
@app.post("/tasks", status_code=201)
def create_new_task(payload: dict = Body(...)):
    if (
        not isinstance(payload, dict)
        or set(payload.keys()) != {"title"}
        or not isinstance(payload["title"], str)
        or not payload["title"].strip()
    ):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request body"}
        )

    return create_task(payload["title"].strip())


# Stage 4: Update a task
@app.put("/tasks/{task_id}")
def update_task(task_id: int, data: dict[str, Any] = Body(...)):
    task = next((t for t in tasks if t["id"] == task_id), None)

    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    if not data or not set(data.keys()).issubset({"title", "done"}):
        return JSONResponse(
            status_code=400,
            content={"error": "Provide title and/or done"}
        )

    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Title cannot be empty"}
            )
        task["title"] = data["title"].strip()

    if "done" in data:
        if not isinstance(data["done"], bool):
            return JSONResponse(
                status_code=400,
                content={"error": "Done must be true or false"}
            )
        task["done"] = data["done"]

    return task


# Stage 4: Delete a task
@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(index)
            return Response(status_code=204)

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )
