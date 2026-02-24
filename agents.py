# agents.py
import json
import os
from typing import Any, Dict, List

from groq import Groq

# Re-use your MCP tool implementations directly
from server import (
    flights_list_region_snapshot,
    flights_get_by_callsign,
    alerts_list_active,
)

# ---------- Groq client ----------

def get_groq_client():
    """Get or create Groq client. Raises error if API key is not set."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is not set. "
            "Please set it using: $env:GROQ_API_KEY = 'your-key' (PowerShell) "
            "or set GROQ_API_KEY=your-key (CMD)"
        )
    return Groq(api_key=api_key)

# Lazy client - will be created when needed
_client = None

def client():
    """Get the Groq client instance (lazy initialization)."""
    global _client
    if _client is None:
        _client = get_groq_client()
    return _client

MODEL_NAME = "llama-3.3-70b-versatile"  # or any Groq model that supports tools


# ---------- Tool registry used by Groq ----------

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "flights_list_region_snapshot",
            "description": "Get the latest cached snapshot of all flights for a region.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region identifier, e.g. 'region1'.",
                        "default": "region1",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flights_get_by_callsign",
            "description": "Look up a single flight by callsign in the latest snapshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "callsign": {
                        "type": "string",
                        "description": "Flight callsign, e.g. 'PIA293'.",
                    },
                    "region": {
                        "type": "string",
                        "description": "Region identifier, default 'region1'.",
                        "default": "region1",
                    },
                },
                "required": ["callsign"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alerts_list_active",
            "description": "List flights in a region that look anomalous (low speed at cruise altitude, very high climb/descent rate).",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region identifier, default 'region1'.",
                        "default": "region1",
                    }
                },
                "required": [],
            },
        },
    },
]


# Map tool name -> actual Python implementation
def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "flights_list_region_snapshot":
        return flights_list_region_snapshot(**arguments)
    if name == "flights_get_by_callsign":
        return flights_get_by_callsign(**arguments)
    if name == "alerts_list_active":
        return alerts_list_active(**arguments)
    raise ValueError(f"Unknown tool: {name}")


# ---------- Generic tool-calling loop ----------

def run_tool_calling_chat(
    system_prompt: str,
    user_query: str,
    allowed_tools: List[str] | None = None,
) -> str:
    """
    Single-agent loop:
    1. Ask Groq with tool definitions.
    2. If model returns tool_calls, execute them locally and send results back.
    3. Return the final natural-language answer.
    """
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
    ]

    # Filter tool list if a subset is allowed for this agent
    if allowed_tools is None:
        tools = TOOLS
    else:
        tools = [
            t
            for t in TOOLS
            if t["function"]["name"] in allowed_tools
        ]

    # First call: model decides whether to use tools
    first = client().chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    message = first.choices[0].message
    messages.append(message)

    tool_calls = getattr(message, "tool_calls", None)

    if not tool_calls:
        # Model answered directly
        return message.content or ""

    # Execute each tool call and append results
    for call in tool_calls:
        fn = call.function
        tool_name = fn.name
        args = json.loads(fn.arguments or "{}")

        if allowed_tools is not None and tool_name not in allowed_tools:
            tool_result = {
                "error": f"Tool {tool_name} is not allowed for this agent."
            }
        else:
            try:
                tool_payload = execute_tool(tool_name, args)
                tool_result = tool_payload
            except Exception as e:
                tool_result = {"error": str(e)}

        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "name": tool_name,
                "content": json.dumps(tool_result),
            }
        )

    # Second call: give the tool outputs back to the model
    final = client().chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    return final.choices[0].message.content or ""


# ---------- Concrete agents ----------

def traveler_agent(question: str) -> str:
    """
    Traveler-facing agent.
    - Specializes in questions about a specific flight.
    - Mainly uses flights_get_by_callsign.
    """
    system = (
        "You are a traveler support assistant. "
        "Help passengers understand where their flight is, "
        "its altitude, speed, and whether anything looks unusual. "
        "Use the flights_get_by_callsign tool when needed."
    )
    return run_tool_calling_chat(
        system_prompt=system,
        user_query=question,
        allowed_tools=["flights_get_by_callsign"],
    )


def ops_agent(question: str) -> str:
    """
    Operations agent.
    - Oversees the whole region.
    - Can call snapshot + alerts tools.
    """
    system = (
        "You are an airline operations specialist monitoring airspace safety. "
        "Use flights_list_region_snapshot and alerts_list_active to analyze "
        "current traffic, highlight anomalies, and propose actions."
    )
    return run_tool_calling_chat(
        system_prompt=system,
        user_query=question,
        allowed_tools=[
            "flights_list_region_snapshot",
            "alerts_list_active",
        ],
    )

def traveler_with_ops(callsign: str, passenger_question: str) -> str:
    """
    Multi-agent orchestration:
    1) Traveler agent answers passenger's question about a specific flight.
    2) Ops agent is asked for a regional/anomaly view around that flight.
    3) We ask the model to synthesize a final passenger-friendly answer
       combining both perspectives.
    """

    base_question = (
        f"My flight {callsign} is in region1. {passenger_question} "
        f"Please use tools to check this specific flight."
    )

    # Step 1: Traveler agent reply (focused on that flight)
    traveler_reply = traveler_agent(base_question)

    # Step 2: Ops agent reply (regional view + anomalies)
    ops_prompt = (
        f"Consider flight {callsign} in region1. "
        f"Give a short situation report focusing on nearby anomalies "
        f"and anything that could worry the passenger."
    )
    ops_reply = ops_agent(ops_prompt)

    # Step 3: Final synthesis – another Groq call, no extra tools
    system = (
        "You are a coordinator between a traveler support agent and "
        "an operations agent. You will see both of their messages and "
        "must produce ONE clear answer for the passenger. "
        "Reassure them when appropriate, but do not hide serious issues."
    )

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Passenger question: {passenger_question}\n"
                f"Flight: {callsign}\n\n"
                f"Traveler agent said:\n{traveler_reply}\n\n"
                f"Ops agent said:\n{ops_reply}\n\n"
                "Now give a final answer for the passenger."
            ),
        },
    ]

    final = client().chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    return final.choices[0].message.content or ""


if __name__ == "__main__":
    # Example 1: traveler asks about their flight
    print("=== Traveler agent ===")
    ans1 = traveler_agent(
        "My flight PIA293 is going from Pakistan. "
        "Where is it roughly now and is everything normal?"
    )
    print(ans1)

    # Example 2: ops agent scans the whole region
    print("\n=== Ops agent ===")
    ans2 = ops_agent(
        "Give me a concise situation report for region1. "
        "How many flights, any anomalies, and which one should I worry about first?"
    )
    print(ans2)
