from typing import Annotated
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from app.core.config import settings
from agent.tools.flight_tools import (
    search_flights_tool,
    hold_seat_tool,
    confirm_booking_tool,
    cancel_booking_tool,
    policy_rag_tool
)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

tools = [
    search_flights_tool,
    hold_seat_tool,
    confirm_booking_tool,
    cancel_booking_tool,
    policy_rag_tool
]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.2
).bind_tools(tools)

def call_model(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

builder = StateGraph(AgentState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, ["tools", END])
builder.add_edge("tools", "agent")

agent_graph = builder.compile()