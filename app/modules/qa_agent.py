"""
DAY 4 — Settlement Q&A agent.

Reads data/reconciliation_output.csv and data/exceptions.csv (no new data
model). Answers questions like "why wasn't order X settled?" using a local
Ollama model's tool-calling, backed by pandas lookups — so answers are
grounded in the actual reconciliation output, not invented.

Requires a tool-calling-capable model pulled locally, e.g.:
    ollama pull qwen2.5:7b

Run:
    python -m app.modules.qa_agent "why wasn't order ORD-1001 settled?"

TODO — implement the loop below. Structure:
  1. Define tool schemas for `lookup_by_order_id` and `search_exceptions`.
  2. Send the user's question + tool schemas to the local model.
  3. If the model requests a tool call, execute it against the dataframes
     and send the result back as a "tool" role message.
  4. Loop until the model returns a final text answer (no tool_calls).
  5. Print the answer.

Starter skeleton:
"""
import sys
import json
import pandas as pd
import ollama

from app import config

client = ollama.Client(host=config.OLLAMA_HOST)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_by_order_id",
            "description": "Look up the reconciliation status and reason for a specific order_id.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_exceptions",
            "description": "Search the exceptions list by a keyword in the reason or record_ref.",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string"}},
                "required": ["keyword"],
            },
        },
    },
]


def lookup_by_order_id(order_id: str) -> dict:
    df = pd.read_csv("data/reconciliation_output.csv")
    match = df[df.order_id == order_id]
    if match.empty:
        return {"found": False, "message": f"No reconciliation record for {order_id}."}
    return {"found": True, "records": match.to_dict(orient="records")}


def search_exceptions(keyword: str) -> dict:
    df = pd.read_csv("data/exceptions.csv")
    hits = df[df.reason.str.contains(keyword, case=False, na=False) |
              df.record_ref.str.contains(keyword, case=False, na=False)]
    return {"count": len(hits), "records": hits.to_dict(orient="records")}


def run_tool(name: str, tool_input: dict) -> dict:
    if name == "lookup_by_order_id":
        return lookup_by_order_id(**tool_input)
    if name == "search_exceptions":
        return search_exceptions(**tool_input)
    return {"error": f"unknown tool {name}"}


def ask(question: str) -> str:
    """Tool-calling loop: let the model call lookup tools until it has
    enough to answer, then return its final text answer."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a settlement Q&A assistant. Always use the "
                "provided tools to look up facts before answering — never "
                "guess or invent transaction details. If a tool returns "
                "no record, say plainly that you don't have that record "
                "rather than speculating."
            ),
        },
        {"role": "user", "content": question},
    ]

    max_turns = 5  # guard against a runaway tool-call loop
    for _ in range(max_turns):
        resp = client.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            tools=TOOLS,
        )
        msg = resp["message"]
        calls = msg.get("tool_calls")

        if not calls:
            return msg["content"]  # final answer, no more tools requested

        messages.append(msg)
        for call in calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]  # already a dict
            result = run_tool(name, args)
            messages.append({
                "role": "tool",
                "content": json.dumps(result),
            })

    return "I wasn't able to resolve this after several tool calls — try rephrasing the question."


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What exceptions do we have today?"
    print(ask(q))
