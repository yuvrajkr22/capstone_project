# main.py
from fastapi import FastAPI, HTTPException
from core.llm_client import LLMClient
from core.memory_bank import MemoryBank
from core.session_service import InMemorySessionService
from core.observability import ObservabilityManager
from tools.search_tool import SearchTool
from tools.save_json_tool import save_to_file
from agents.planner_agent import PlannerAgent
from agents.progress_agent import ProgressAgent
from agents.optimizer_agent import OptimizerAgent
from agents.resource_agent import ResourceAgent
from agents.motivation_agent import MotivationAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.loop_supervisor import LoopSupervisor
from agents.context_compactor import ContextCompactor
from loguru import logger
import uvicorn
import time

app = FastAPI(title="Smart Project Workflow Manager", version="2.0")

# Core services
llm = LLMClient()
memory = MemoryBank()
sessions = InMemorySessionService()
search_tool = SearchTool()
observability = ObservabilityManager()
context_compactor = ContextCompactor()

# Agents
planner = PlannerAgent(llm, memory)
progress = ProgressAgent(save_to_file)
optimizer = OptimizerAgent(llm)
resource_agent = ResourceAgent(search_tool)
motivation = MotivationAgent(llm)
evaluator = EvaluatorAgent()

# Wrap functions for observability
def _wrap_with_observability(agent_name, agent_method):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = agent_method(*args, **kwargs)
            duration = time.time() - start_time
            observability.record_trace(agent_name, {"args": args, "kwargs": kwargs}, {"result": result}, duration, True)
            return result
        except Exception as e:
            duration = time.time() - start_time
            observability.record_trace(agent_name, {"args": args, "kwargs": kwargs}, {"error": str(e)}, duration, False)
            raise e
    return wrapper

planner.create_plan = _wrap_with_observability("PlannerAgent", planner.create_plan)
optimizer.optimize = _wrap_with_observability("OptimizerAgent", optimizer.optimize)
resource_agent.fetch_resources = _wrap_with_observability("ResourceAgent", resource_agent.fetch_resources)
motivation.send_nudge = _wrap_with_observability("MotivationAgent", motivation.send_nudge)
evaluator.evaluate = _wrap_with_observability("EvaluatorAgent", evaluator.evaluate)

@app.post("/create_session")
def create_session(user_id: str):
    sid = sessions.create_session(user_id)
    logger.info(f"Created session {sid} for user {user_id}")
    return {"session_id": sid}

@app.post("/create_plan")
def create_plan(session_id: str, profile: dict):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    current_memory = memory.get_user_memory(s["user_id"])
    current_memory["profile"] = profile
    compacted_memory = context_compactor.compact_memory(current_memory)
    memory.update_user_memory(s["user_id"], compacted_memory)
    plan_meta = planner.create_plan(s["user_id"], profile)
    if "plan" in plan_meta:
        plan_meta = context_compactor.compact_plan(plan_meta)
    sessions.update_state(session_id, "plan", plan_meta)
    return {"plan": plan_meta}

@app.post("/record_progress")
def record_progress(session_id: str, completed_tasks: list):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    ok = progress.record_progress(s["user_id"], session_id, completed_tasks)
    if len(completed_tasks) >= 3:
        summary = {"completion_rate": 75, "recent_tasks": len(completed_tasks)}
        motivation.send_nudge(s["user_id"], summary)
    return {"saved": ok}

@app.post("/adjust")
def adjust(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    plan = s["state"].get("plan", {}).get("plan", {})
    records = progress.load_records()
    user_records = [r for r in records if r.get("user_id") == s["user_id"]]
    metrics = progress.compute_metrics(user_records)
    adjusted = optimizer.optimize(s["user_id"], plan, metrics)
    sessions.update_state(session_id, "plan", adjusted)
    return {"adjusted_plan": adjusted}

@app.get("/resources")
def resources(q: str):
    res = resource_agent.fetch_resources(q)
    return {"results": res}

@app.get("/nudge")
def nudge(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    records = progress.load_records()
    user_records = [r for r in records if r.get("user_id") == s["user_id"]]
    metrics = progress.compute_metrics(user_records)
    msg = motivation.send_nudge(s["user_id"], metrics)
    return msg

@app.get("/evaluate")
def evaluate(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    plan = s["state"].get("plan", {}).get("plan", {})
    records = progress.load_records()
    user_records = [r for r in records if r.get("user_id") == s["user_id"]]
    metrics = progress.compute_metrics(user_records)
    res = evaluator.evaluate(plan, metrics)
    return res

@app.get("/observability")
def get_observability():
    return {
        "metrics": observability.metrics,
        "agent_performance": observability.get_agent_performance(),
        "recent_traces": [trace.__dict__ for trace in observability.traces[-10:]]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "active_sessions": len(sessions.sessions)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
