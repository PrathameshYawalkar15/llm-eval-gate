from pydantic import BaseModel, Field


class GuardrailCheckResult(BaseModel):
    check_name: str
    passed: bool
    details: str


class EvaluateRequest(BaseModel):
    model_name: str = Field(default="default", description="Model or prompt version being tested")
    prompt: str = Field(..., min_length=1, description="User or system prompt sent to the LLM")
    response_text: str = Field(..., min_length=1, description="Raw text returned by the LLM")
    expected_json_keys: list[str] | None = Field(
        default=None,
        description="Optional list of required keys if response_text must be valid JSON",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Observed response latency in milliseconds",
    )
    max_latency_ms: float = Field(
        default=2000.0,
        gt=0,
        description="Maximum allowed latency threshold in milliseconds",
    )


class EvaluateResponse(BaseModel):
    run_id: int | None = None
    model_name: str
    overall_passed: bool
    checks: list[GuardrailCheckResult]