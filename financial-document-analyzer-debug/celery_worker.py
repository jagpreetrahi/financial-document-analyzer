from celery import Celery
import os
from dotenv import load_dotenv
load_dotenv()

##initialize celery app with Redis as broker 
celery_app = Celery(
    "financial_analyzer",
    broker=os.getenv("REDIS_URL", "redis://locahost:6379/0"),
    backend=os.getenv("REDIS_URL", "rediss://localhost:6379/0")
)

##celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,         
    result_expires=3600,               
    worker_prefetch_multiplier=1,      
    task_acks_late=True, 
)

@celery_app.task(bind=True, name="analyze_document_task")
def analyze_document_task(self, query: str, file_path: str):
    """
    Celery task to run the CrewAI financial analysis pipeline.
    """
    try:
        ## Update task state to show it has started
        self.update_state(
            state="STARTED",
            meta={"status": "Analysis started", "progress": "0%"}
        )
        
        ## Import here to avoid circular imports
        from crewai import Crew, Process
        from agents import financial_analyst, verifier, investment_advisor, risk_assessor
        from task import verification, analyze_financial_document, investment_analysis, risk_assessment

        ## Update progress
        self.update_state(
            state="PROGRESS",
            meta={"status": "Running document verification", "progress": "25%"}
        )

        ## Build and run the crew
        financial_crew = Crew(
            agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
            tasks=[verification, analyze_financial_document, investment_analysis, risk_assessment],
            process=Process.sequential,
        )

        self.update_state(
            state="PROGRESS",
            meta={"status": "Running financial analysis", "progress": "50%"}
        )

        result = financial_crew.kickoff({
            "query": query,
            "file_path": file_path
        })

        self.update_state(
            state="PROGRESS",
            meta={"status": "Finalizing results", "progress": "90%"}
        )

        return {
            "status": "success",
            "query": query,
            "analysis": str(result),
            "file_processed": os.path.basename(file_path)
        }

    except Exception as e:
        ## Return failure info
        return {
            "status": "failed",
            "error": str(e),
            "query": query,
            "file_processed": os.path.basename(file_path)
        }

    finally:
        ## Clean up uploaded file after processing
        if os.path.exists(file_path) and "sample" not in file_path:
            try:
                os.remove(file_path)
            except:
                pass