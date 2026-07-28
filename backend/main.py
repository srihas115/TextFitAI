from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from ai_fitter import FitConstraints, fit_text
from counters import char_count, word_count

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
RESOURCES_DIR = BASE_DIR.parent / "resources"

app = FastAPI(title="TextFitAI", description="AI-powered text fitting for exact word and character targets.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FitRequest(BaseModel):
    text: str = Field(..., min_length=1)
    min_words: Optional[int] = Field(default=None, ge=0)
    max_words: Optional[int] = Field(default=None, ge=0)
    min_chars: Optional[int] = Field(default=None, ge=0)
    max_chars: Optional[int] = Field(default=None, ge=0)
    direction_override: Optional[str] = Field(default=None, pattern="^(shorten|lengthen)$")
    expansion_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ranges(self) -> "FitRequest":
        if self.min_words is not None and self.max_words is not None and self.min_words > self.max_words:
            raise ValueError("min_words cannot be greater than max_words")
        if self.min_chars is not None and self.max_chars is not None and self.min_chars > self.max_chars:
            raise ValueError("min_chars cannot be greater than max_chars")
        return self


class FitResponse(BaseModel):
    result: str
    word_count: int
    char_count: int
    attempts: int
    met_target: bool
    revision_summary: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fit", response_model=FitResponse)
def fit(payload: FitRequest) -> FitResponse:
    constraints = FitConstraints(
        min_words=payload.min_words,
        max_words=payload.max_words,
        min_chars=payload.min_chars,
        max_chars=payload.max_chars,
    )

    try:
        fitted = fit_text(
            payload.text,
            constraints,
            direction_override=payload.direction_override,
            expansion_notes=payload.expansion_notes,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI fitting failed: {exc}") from exc

    return FitResponse(
        result=fitted.result,
        word_count=fitted.word_count,
        char_count=fitted.char_count,
        attempts=fitted.attempt,
        met_target=fitted.met_target,
        revision_summary=fitted.revision_summary,
    )


@app.get("/counts")
def get_counts(text: str) -> dict[str, int]:
    return {"word_count": word_count(text), "char_count": char_count(text)}


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/resources", StaticFiles(directory=RESOURCES_DIR), name="resources")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
