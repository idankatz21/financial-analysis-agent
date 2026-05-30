import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agent import run_agent

router = APIRouter()


async def _event_stream(ticker: str):
    async for event in run_agent(ticker):
        yield f"data: {json.dumps(event)}\n\n"


@router.get("/analyze/{ticker}")
async def analyze(ticker: str):
    return StreamingResponse(
        _event_stream(ticker),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
