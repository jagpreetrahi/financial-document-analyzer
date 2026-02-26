import os
import uuid
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import verification, analyze_financial_document, investment_analysis, risk_assessment
from celery_worker import analyze_document_task
from celery.result import AsyncResult

app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis using CrewAI with async queue processing",
    version="2.0.0"
)


## Synchronous crew runner (used as fallback)
def run_crew(query: str, file_path: str = "data/TSLA-Q2-2025-Update.pdf"):
    """Run the CrewAI pipeline synchronously"""
    financial_crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[verification, analyze_financial_document, investment_analysis, risk_assessment],
        process=Process.sequential,
    )
    result = financial_crew.kickoff({"query": query, "file_path": file_path})
    return result



## Health Check
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Financial Document Analyzer API is running", "version": "2.0.0"}



## Async Analysis Endpoint (Queue-based)
@app.post("/analyze/async", summary="Queue document for async analysis")
async def analyze_document_async(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights")
):
    """
    Queue a financial document for async analysis via Redis.
    Returns a task_id immediately — use GET /result/{task_id} to poll for results.
    Supports concurrent requests without blocking.
    """
    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    try:
        os.makedirs("data", exist_ok=True)

        ## Save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        ## Validate file is a PDF
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        ## Validate query
        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        ## Push task to Redis queue — returns immediately
        task = analyze_document_task.delay(query.strip(), file_path)

        return JSONResponse(
            status_code=202,  ## 202 Accepted — processing has started
            content={
                "status": "queued",
                "task_id": task.id,
                "message": "Document queued for analysis. Poll /result/{task_id} for results.",
                "poll_url": f"/result/{task.id}",
                "file_queued": file.filename
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        ## Clean up file if queuing failed
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error queuing document: {str(e)}")



##  Task Result
@app.get("/result/{task_id}", summary="Get analysis result by task ID")
async def get_result(task_id: str):
    """
    Poll for the result of a queued analysis task.
    
    Returns task status:
    - PENDING   → task is waiting in queue
    - STARTED   → task has been picked up by a worker
    - PROGRESS  → task is actively running (includes progress %)
    - SUCCESS   → task completed — result is included
    - FAILURE   → task failed — error is included
    """
    try:
        task_result = AsyncResult(task_id)
        state = task_result.state

        if state == "PENDING":
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is waiting in queue"
            }

        elif state == "STARTED":
            return {
                "task_id": task_id,
                "status": "started",
                "message": "Task has been picked up and is starting"
            }

        elif state == "PROGRESS":
            meta = task_result.info or {}
            return {
                "task_id": task_id,
                "status": "processing",
                "message": meta.get("status", "Processing..."),
                "progress": meta.get("progress", "unknown")
            }

        elif state == "SUCCESS":
            result = task_result.result
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result
            }

        elif state == "FAILURE":
            return JSONResponse(
                status_code=500,
                content={
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(task_result.result)
                }
            )

        else:
            return {
                "task_id": task_id,
                "status": state.lower(),
                "message": "Unknown state"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching result: {str(e)}")



## Queue Status Endpoint
@app.get("/queue/status", summary="Check Redis queue status")
async def queue_status():
    """Check how many tasks are active, pending, and completed in the queue"""
    try:
        from celery_worker import celery_app
        inspect = celery_app.control.inspect()

        active = inspect.active() or {}
        reserved = inspect.reserved() or {}

        active_count = sum(len(tasks) for tasks in active.values())
        pending_count = sum(len(tasks) for tasks in reserved.values())

        return {
            "status": "redis_connected",
            "active_tasks": active_count,
            "queued_tasks": pending_count,
            "workers": list(active.keys())
        }
    except Exception as e:
        return {
            "status": "redis_unavailable",
            "error": str(e),
            "message": "Make sure Redis is running: docker run -d -p 6379:6379 redis:alpine"
        }



## Synchronous Endpoint (original, kept as fallback)
@app.post("/analyze", summary="Analyze document synchronously (blocking)")
async def analyze_document(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights")
):
    """
    Synchronous analysis — waits for full result before returning.
    Use /analyze/async for concurrent or long-running requests.
    """
    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    try:
        os.makedirs("data", exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        response = run_crew(query=query.strip(), file_path=file_path)

        return {
            "status": "success",
            "query": query,
            "analysis": str(response),
            "file_processed": file.filename
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing financial document: {str(e)}")

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)