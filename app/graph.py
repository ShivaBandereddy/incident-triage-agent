# app/graph.py (Day 9 v1: no RAG, no approval yet)
from langgraph.graph import END, START, StateGraph

from app.nodes import analyze_logs, hypothesize, intake
from app.state import IncidentState


def build_graph():
    b = StateGraph(IncidentState)
    b.add_node('intake', intake)
    b.add_node('analyze_logs', analyze_logs)
    b.add_node('hypothesize', hypothesize)
    b.add_edge(START, 'intake')
    b.add_edge('intake', 'analyze_logs')
    b.add_edge('analyze_logs', 'hypothesize')
    b.add_edge('hypothesize', END)
    return b.compile()
