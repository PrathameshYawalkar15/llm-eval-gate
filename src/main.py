import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from src.db import EvalRun, get_db, init_db
from src.guardrails import run_all_guardrails
from src.schemas import EvaluateRequest, EvaluateResponse, GuardrailCheckResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LLM Guard API",
    description="Automated guardrail and evaluation release-gate microservice for LLM outputs.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate_llm_output(
    request: EvaluateRequest,
    db: Session = Depends(get_db),
) -> EvaluateResponse:
    overall_passed, checks = run_all_guardrails(request)

    db_run = EvalRun(
        model_name=request.model_name,
        overall_passed=overall_passed,
        checks_json=json.dumps([c.model_dump() for c in checks]),
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)

    return EvaluateResponse(
        run_id=db_run.id,
        model_name=db_run.model_name,
        overall_passed=db_run.overall_passed,
        checks=checks,
    )


@app.get("/runs", response_model=list[EvaluateResponse])
def list_eval_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[EvaluateResponse]:
    runs = db.query(EvalRun).order_by(EvalRun.id.desc()).limit(limit).all()
    return [
        EvaluateResponse(
            run_id=run.id,
            model_name=run.model_name,
            overall_passed=run.overall_passed,
            checks=[GuardrailCheckResult(**c) for c in json.loads(run.checks_json)],
        )
        for run in runs
    ]


@app.get("/runs/{run_id}", response_model=EvaluateResponse)
def get_eval_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> EvaluateResponse:
    run = db.query(EvalRun).filter(EvalRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return EvaluateResponse(
        run_id=run.id,
        model_name=run.model_name,
        overall_passed=run.overall_passed,
        checks=[GuardrailCheckResult(**c) for c in json.loads(run.checks_json)],
    )