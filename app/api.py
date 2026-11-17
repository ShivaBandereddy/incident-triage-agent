# app/api.py (Day 18): FastAPI wrapper. Demo, not production security (see README limitations).
import hmac
import logging
import os
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.graph import build_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('triage-api')

app = FastAPI(title='Incident Triage Agent')
graph = build_graph(checkpointer=MemorySaver())  # in-memory: restart loses pending approvals


def check_key(x_api_key: str = Header(default='')):
    # single shared key: thread_id is not bound to any user (see README limitations)
    expected = os.getenv('TRIAGE_API_KEY', '')
    if not expected or not hmac.compare_digest(x_api_key, expected):  # key unset: deny all
        raise HTTPException(status_code=401, detail='invalid or missing API key')


class TriageRequest(BaseModel):
    alert_text: str = Field(max_length=2000)
    log_snippet: str = Field(max_length=200_000)


class Decision(BaseModel):
    thread_id: str = Field(max_length=64)
    approved: bool
    feedback: str = Field(default='', max_length=1000)


@app.middleware('http')
async def log_requests(request: Request, call_next):
    start = time.time()
    resp = await call_next(request)
    log.info('%s %s %s %.2fs', request.method, request.url.path, resp.status_code,
             time.time() - start)
    return resp  # request bodies and logs are never logged


def pack(out):
    pending = out['__interrupt__'][0].value if '__interrupt__' in out else None
    return {'pending': pending, 'report': out.get('report')}


@app.post('/triage', dependencies=[Depends(check_key)])
def triage(req: TriageRequest):
    tid = str(uuid.uuid4())
    out = graph.invoke({'alert_text': req.alert_text, 'log_snippet': req.log_snippet},
                       {'configurable': {'thread_id': tid}})
    return {'thread_id': tid, **pack(out)}


@app.post('/approve', dependencies=[Depends(check_key)])
def approve(d: Decision):
    cfg = {'configurable': {'thread_id': d.thread_id}}
    if not graph.get_state(cfg).next:
        raise HTTPException(status_code=404, detail='no pending approval for this thread_id')
    out = graph.invoke(Command(resume={'approved': d.approved, 'feedback': d.feedback}), cfg)
    return pack(out)
