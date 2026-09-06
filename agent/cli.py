from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from langchain_core.messages import HumanMessage, SystemMessage
from agent.graph import agent_graph

console = Console()

SYSTEM_PROMPT = """You are the FlightOps Terminal Assistant.
Help users search flights, make atomic holds, confirm tickets, process cancellations, and verify fare rules via RAG.
Always provide clear details and ask for explicit confirmation before booking or cancelling."""


def _renderable_text(content: Any) -> str:
    """Extract display text from plain or provider-structured message content."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "\n".join(text_parts) or "No displayable response was returned."
    return str(content)


def start_cli():
    console.print(Panel(
        Text("✈️  FLIGHTOPS TERMINAL AGENT SYSTEM ACTIVE\nType 'exit' or 'quit' to end session.", style="bold cyan"),
        subtitle="Connected to Neon DB & Pinecone"
    ))

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]User[/bold green]")
            if user_input.strip().lower() in ("exit", "quit"):
                console.print("[yellow]Exiting FlightOps CLI. Goodbye![/yellow]")
                break
            if not user_input.strip():
                continue

            messages.append(HumanMessage(content=user_input))

            with console.status("[bold magenta]Processing via LangGraph agent...", spinner="dots"):
                result = agent_graph.invoke({"messages": messages})

            messages = result["messages"]
            assistant_reply = _renderable_text(messages[-1].content)
            console.print(Panel(assistant_reply, title="[bold blue]FlightOps Agent[/bold blue]", border_style="blue"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    start_cli()
