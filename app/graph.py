# app/graph.py (Day 11: final graph with use_rag / use_approval flags)
from langgraph.graph import END, START, StateGraph

from app.nodes import (analyze_logs, human_approval, hypothesize, intake, report,
                       route_after_approval, search_runbooks)
from app.state import IncidentState


def build_graph(use_rag=True, use_approval=True, checkpointer=None):
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
    if use_approval:
        b.add_node('human_approval', human_approval)
        b.add_node('report', report)
        b.add_edge('hypothesize', 'human_approval')
        b.add_conditional_edges('human_approval', route_after_approval,
                                {'report': 'report', 'hypothesize': 'hypothesize'})
        b.add_edge('report', END)
    else:
        b.add_edge('hypothesize', END)
    return b.compile(checkpointer=checkpointer)
