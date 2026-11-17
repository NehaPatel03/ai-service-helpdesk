"""
Multi-Step Tool-Using Agent Loop for Incident Investigation.

Orchestrates Google Gemini function-calling, tool validation, multi-turn reasoning,
Pydantic output schema validation with retry, grounding verification, and telemetry logging.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types as genai_types
from pydantic import ValidationError

from app.agent.grounding import (
    extract_tool_grounded_ids,
    sanitize_grounded_analysis,
    verify_grounding,
)
from app.agent.logger import log_agent_run
from app.agent.memory import (
    compose_rolling_summary,
    get_ticket_memory,
    update_ticket_memory,
)
from app.agent.schemas import (
    AgentExecutionTrace,
    Analysis,
    GroundingResult,
    ToolCallRecord,
)
from app.agent.tools import ALL_TOOLS, TOOL_REGISTRY
from app.config import settings
from app.schemas import TicketInput

logger = logging.getLogger(__name__)

# Load prompt templates
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


SYSTEM_PROMPT_TEMPLATE = _load_prompt("system.txt")
RETRY_PROMPT_TEMPLATE = _load_prompt("retry.txt")


def _clean_json_text(text: str) -> str:
    """Strips markdown code blocks and whitespace from JSON response strings."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    return cleaned


def generate_fallback_analysis_pydantic(ticket: TicketInput) -> Analysis:
    """
    Generates a deterministic baseline Analysis model when external Gemini API is unreachable.
    """
    title_lower = f"{ticket.title} {ticket.description}".lower()

    if "vpn" in title_lower or "anyconnect" in title_lower or "globalprotect" in title_lower:
        return Analysis(
            root_cause="SSL/TLS VPN gateway timeout, MTU fragmentation mismatch, or stale client authentication tokens.",
            confidence="high",
            suggested_steps=[
                "Check %LOCALAPPDATA%\\Palo Alto Networks\\GlobalProtect\\PanGPS.log for handshake timeouts",
                "Disable IPv6 on active Wi-Fi adapter via PowerShell: Disable-NetAdapterBinding -ComponentID ms_tcpip6",
                "Reset tunnel MTU to 1360 and clear saved credentials in client preferences",
            ],
            related_ticket_ids=[],
            kb_sources=[],
        )
    elif "postgres" in title_lower or "rds" in title_lower or "connection pool" in title_lower:
        return Analysis(
            root_cause="PostgreSQL client connection pool saturation (max_connections exhausted) caused by unclosed transaction leaks.",
            confidence="high",
            suggested_steps=[
                "Query pg_stat_activity for idle-in-transaction connections exceeding 60s",
                "Terminate locking backend queries via pg_terminate_backend(pid)",
                "Increase PgBouncer pool ceiling and verify application connection pooling",
            ],
            related_ticket_ids=[],
            kb_sources=[],
        )
    elif "dns" in title_lower or "nxdomain" in title_lower:
        return Analysis(
            root_cause="DNS forwarder resolution failure, internal resolver cache corruption, or root hints timeout.",
            confidence="medium",
            suggested_steps=[
                "Execute nslookup against authoritative domain controller",
                "Flush client resolver cache via ipconfig /flushdns",
                "Restart DNS server service and verify forward lookup zones",
            ],
            related_ticket_ids=[],
            kb_sources=[],
        )
    else:
        return Analysis(
            root_cause="Service configuration constraint or unhandled exception in backend application component.",
            confidence="medium",
            suggested_steps=[
                "Inspect error logs in system event viewer or container stdout",
                "Verify service resource consumption (CPU/Memory/Disk)",
                "Restart affected service and confirm operational status",
            ],
            related_ticket_ids=[],
            kb_sources=[],
        )


def run_incident_agent(
    ticket: TicketInput,
    max_steps: int = 5,
    client: Optional[genai.Client] = None,
) -> Tuple[Analysis, AgentExecutionTrace]:
    """
    Executes the multi-step tool-using Gemini Agent loop to investigate an incident ticket.

    Args:
        ticket: TicketInput incident details.
        max_steps: Maximum reasoning and tool-calling turns allowed (default 5).
        client: Optional pre-configured Google GenAI client (for testing/dependency injection).

    Returns:
        Tuple of (Analysis, AgentExecutionTrace).
    """
    start_time = time.time()
    trace = AgentExecutionTrace(
        ticket_id=ticket.id,
        steps_count=0,
        tool_calls=[],
        status="success",
        used_fallback=False,
    )

    # 1. Check for conversation memory
    previous_memory = get_ticket_memory(ticket.id)
    memory_section = ""
    if previous_memory:
        memory_section = f"\n\nPrior Investigation Context for Ticket #{ticket.id}:\n{previous_memory}\n"

    system_prompt = SYSTEM_PROMPT_TEMPLATE or "You are a Senior IT Service Desk AI Troubleshooting Agent."
    user_prompt = f"""Investigate Incident Ticket #{ticket.id}:
- Title: {ticket.title}
- Description: {ticket.description}
- Category: {ticket.category}
- Priority: {ticket.priority}{memory_section}

Please perform 1-2 targeted diagnostic tool queries to gather evidence, then provide your final Analysis JSON response. Do not repeat tool queries."""

    # 2. Check API key availability
    api_key = settings.GEMINI_API_KEY
    if not api_key and client is None:
        logger.info("No GEMINI_API_KEY configured; using heuristic fallback analysis.")
        fallback = generate_fallback_analysis_pydantic(ticket)
        trace.final_analysis = fallback
        trace.status = "fallback"
        trace.used_fallback = True
        trace.latency_ms = int((time.time() - start_time) * 1000)
        log_agent_run(trace, ticket.model_dump())
        return fallback, trace

    try:
        if client is None:
            client = genai.Client(api_key=api_key)

        models_to_try = [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]

        # Prepare messages history for multi-turn function calling
        contents: List[genai_types.Content] = [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=user_prompt)],
            )
        ]

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=ALL_TOOLS,
            temperature=0.2,
            automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )

        steps = 0
        final_analysis: Optional[Analysis] = None
        valid_schema = False

        while steps < max_steps:
            steps += 1
            trace.steps_count = steps
            logger.info("Agent Step %d for Ticket #%d", steps, ticket.id)

            response = None
            last_err = None
            for m in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=contents,
                        config=config,
                    )
                    break
                except Exception as call_err:
                    last_err = call_err
                    logger.warning("Agent call with model %s failed: %s", m, call_err)

            if response is None:
                raise RuntimeError(f"All model calls failed: {last_err}")

            # Capture token usage metrics where available
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                meta = response.usage_metadata
                trace.tokens_in += getattr(meta, "prompt_token_count", 0) or 0
                trace.tokens_out += getattr(meta, "candidates_token_count", 0) or 0

            # Inspect if model requested function calls
            function_calls = getattr(response, "function_calls", None)
            if function_calls:
                # Add model's function-calling turn to history
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                tool_response_parts = []
                for func_call in function_calls:
                    fname = func_call.name
                    fargs = func_call.args or {}
                    logger.info("Agent requested tool: %s with args: %s", fname, fargs)

                    tool_start = time.time()
                    tool_func = TOOL_REGISTRY.get(fname)

                    if not tool_func:
                        err_msg = f"Tool '{fname}' is not recognized."
                        logger.warning(err_msg)
                        call_rec = ToolCallRecord(
                            step=steps,
                            tool_name=fname,
                            args=fargs,
                            result=None,
                            latency_ms=0,
                            error=err_msg,
                        )
                        trace.tool_calls.append(call_rec)
                        tool_response_parts.append(
                            genai_types.Part.from_function_response(
                                name=fname,
                                response={"error": err_msg},
                            )
                        )
                        continue

                    # Execute the tool
                    try:
                        tool_result = tool_func(**fargs)
                        latency_ms = int((time.time() - tool_start) * 1000)
                        call_rec = ToolCallRecord(
                            step=steps,
                            tool_name=fname,
                            args=fargs,
                            result=tool_result,
                            latency_ms=latency_ms,
                        )
                        trace.tool_calls.append(call_rec)
                        tool_response_parts.append(
                            genai_types.Part.from_function_response(
                                name=fname,
                                response={"result": tool_result},
                            )
                        )
                    except Exception as exec_err:
                        err_str = str(exec_err)
                        logger.error("Error executing %s: %s", fname, err_str)
                        call_rec = ToolCallRecord(
                            step=steps,
                            tool_name=fname,
                            args=fargs,
                            result=None,
                            latency_ms=int((time.time() - tool_start) * 1000),
                            error=err_str,
                        )
                        trace.tool_calls.append(call_rec)
                        tool_response_parts.append(
                            genai_types.Part.from_function_response(
                                name=fname,
                                response={"error": err_str},
                            )
                        )

                # Feed tool responses back to model in next iteration (using role='user')
                contents.append(
                    genai_types.Content(role="user", parts=tool_response_parts)
                )
                continue

            # Model did not call any tools: examine text output
            raw_text = response.text or ""
            cleaned = _clean_json_text(raw_text)

            try:
                final_analysis = Analysis.model_validate_json(cleaned)
                valid_schema = True
                trace.status = "success"
                break
            except (ValidationError, json.JSONDecodeError) as val_err:
                logger.warning("Pydantic validation failed on agent response: %s", val_err)
                trace.valid_schema = False

                # Retry once by sending validation error back to Gemini
                retry_prompt = (
                    RETRY_PROMPT_TEMPLATE
                    .replace("{error_message}", str(val_err))
                    .replace("{previous_response}", raw_text[:400])
                )
                contents.append(
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part.from_text(text=retry_prompt)],
                    )
                )

                retry_response = None
                for m in models_to_try:
                    try:
                        retry_response = client.models.generate_content(
                            model=m,
                            contents=contents,
                            config=config,
                        )
                        break
                    except Exception:
                        pass

                if retry_response and retry_response.text:
                    cleaned_retry = _clean_json_text(retry_response.text)
                    try:
                        final_analysis = Analysis.model_validate_json(cleaned_retry)
                        trace.valid_schema = True
                        trace.status = "success"
                        break
                    except Exception as retry_err:
                        logger.error("Validation retry also failed: %s", retry_err)
                        trace.status = "validation_failed"
                        trace.valid_schema = False
                        break
                else:
                    trace.status = "validation_failed"
                    break

        if final_analysis is None:
            if steps >= max_steps:
                logger.warning("Agent reached maximum step limit (%d)", max_steps)
                trace.status = "max_steps_reached"
            trace.used_fallback = True
            final_analysis = generate_fallback_analysis_pydantic(ticket)

    except Exception as agent_err:
        logger.error("Unhandled exception during agent loop: %s", agent_err, exc_info=True)
        trace.status = "api_error"
        trace.error = str(agent_err)
        trace.used_fallback = True
        trace.valid_schema = False
        final_analysis = generate_fallback_analysis_pydantic(ticket)

    # 3. Grounding Verification
    grounded_tickets, grounded_kb = extract_tool_grounded_ids(trace.tool_calls)
    grounding_result = verify_grounding(final_analysis, grounded_tickets, grounded_kb)
    trace.grounding = grounding_result

    # Sanitize invalid IDs to avoid presenting ungrounded sources
    sanitized_analysis = sanitize_grounded_analysis(final_analysis, grounding_result)
    trace.final_analysis = sanitized_analysis
    trace.latency_ms = int((time.time() - start_time) * 1000)

    # 4. Conversation Memory Persistence
    if not trace.used_fallback and trace.status == "success":
        new_summary = compose_rolling_summary(previous_memory, sanitized_analysis)
        update_ticket_memory(ticket.id, new_summary)

    # 5. Persist Agent Run Log in PostgreSQL
    log_agent_run(trace, ticket.model_dump())

    return sanitized_analysis, trace
