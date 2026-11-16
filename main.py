from database import (
    init_db,
    get_all_tasks,
    get_task_by_id,
    create_task,
    update_task,
    delete_task
)
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



@app.put("/tasks/{task_id}")
def update_existing_task(task_id: int, data: dict = Body(...)):
    if not isinstance(data, dict) or not data:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request body"}
        )

    if not set(data.keys()).issubset({"title", "done"}):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request body"}
        )

    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid request body"}
            )
        data["title"] = data["title"].strip()

    if "done" in data and not isinstance(data["done"], bool):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request body"}
        )

    task = update_task(task_id, data)

    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return task



@app.delete("/tasks/{task_id}", status_code=204)
def delete_existing_task(task_id: int):
    deleted = delete_task(task_id)

    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return Response(status_code=204)
