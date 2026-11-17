# app/graph.py (Day 10: optional RAG step; approval flag comes on Day 11)
from langgraph.graph import END, START, StateGraph

from app.nodes import analyze_logs, hypothesize, intake, search_runbooks
from app.state import IncidentState


def build_graph(use_rag=True):
    b = StateGraph(IncidentState)
    b.add_node('intake', intake)
    b.add_node('analyze_logs', analyze_logs)
    b.add_node('hypothesize', hypothesize)
    b.add_edge(START, 'intake')
    b.add_edge('intake', 'analyze_logs')
    if use_rag:
        b.add_node('search_runbooks', search_runbooks)
        b.add_edge('analyze_logs', 'search_runbooks')
        b.add_edge('search_runbooks', 'hypothesize')
    else:
        b.add_edge('analyze_logs', 'hypothesize')
    b.add_edge('hypothesize', END)
    return b.compile()
