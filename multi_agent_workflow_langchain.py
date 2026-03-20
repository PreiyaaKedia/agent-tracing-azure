"""
Multi-Agent LangChain Workflow with Application Insights

This script demonstrates LangChain Agents (using create_agent) multi-agent workflow with
the native langchain-azure-ai integration for Application Insights telemetry.

Modern pattern:
- Uses create_agent (LangChain's modern agent creation function)
- Returns LangGraph-based agents under the hood
- Simpler than old AgentExecutor/ReAct pattern
- Sequential agent execution (researcher completes → writer starts)

Difference from LangGraph version:
- No explicit StateGraph - create_agent handles it internally
- Simpler API with system_prompt parameter
- Sequential execution pattern still maintained
- All the LangGraph benefits without manual graph construction

Architecture:
  User Query
      │
      ▼
  ┌─────────────┐  Tools:
  │  Researcher │  - search_web
  │   Agent     │  - gather_statistics
  │             │  - verify_facts
  └─────────────┘
      │ (passes research to)
      ▼
  ┌─────────────┐  Tools:
  │  Writer     │  - format_article
  │   Agent     │  - add_citations
  └─────────────┘
      │
      └─── Traces ───┘
              │
              ▼
      Application Insights

Observability Approach:
- AzureAIOpenTelemetryTracer: Automatic tracing via LangChain callbacks
- enable_content_recording controls message content in traces
- Callback-based instrumentation automatically creates spans for:
  * Agent execution (invoke_agent spans)
  * Each LLM call (chat spans with GenAI semantic conventions)
  * Each tool execution (execute_tool spans)
  
Expected trace hierarchy:
    invoke_agent ResearchAgent
    ├── chat (LLM call - tool planning)
    ├── execute_tool search_web
    ├── execute_tool gather_statistics
    └── chat (final research summary)
    invoke_agent WriterAgent
    ├── chat (LLM call - article creation)
    ├── execute_tool format_article
    └── chat (final formatted article)
"""

import os
import time
from typing import Annotated, List
from random import randint

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# ── OpenTelemetry for parent span ────────────────────────────────────────────
from opentelemetry import trace

# ── LangChain Azure AI Tracer ────────────────────────────────────────────────
from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer

# ── LangChain Agents ─────────────────────────────────────────────────────────
from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool

# Load environment variables
load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL: Initialize tracer at module level (not inside a function)
# This ensures OpenTelemetry hooks are set up before any agent operations
# ─────────────────────────────────────────────────────────────────────────────

connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
if not connection_string:
    raise ValueError("APPLICATION_INSIGHTS_CONNECTION_STRING must be set in environment variables")

print(f"[✓] Initializing tracer with Application Insights connection string")
azure_tracer = AzureAIOpenTelemetryTracer(
    connection_string=connection_string,
    enable_content_recording=True,  # Set False in production
    trace_all_langgraph_nodes=True,  # CRITICAL - create_agent uses LangGraph internally
)
print(f"[✓] Tracer configured for Application Insights (with LangGraph node tracing)\n")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Custom Tools (automatically traced by AzureAIOpenTelemetryTracer)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def search_web(query: Annotated[str, "The search query to find information"]) -> str:
    """Search the web for information on a given topic."""
    # Simulate web search with delay
    time.sleep(randint(5, 15) / 10.0)
    
    # Simulate search results
    results = {
        "quantum computing": "Recent breakthroughs include Google's quantum supremacy demonstration, "
                            "IBM's 433-qubit Osprey processor, and advances in error correction codes. "
                            "Quantum computers are now solving problems classical computers cannot.",
        "photosynthesis": "Photosynthesis converts light energy into chemical energy through chlorophyll. "
                         "The process involves light-dependent and light-independent reactions, producing "
                         "glucose and oxygen from CO2 and water.",
        "climate change": "Global temperatures have risen 1.1°C since pre-industrial times. "
                         "The IPCC reports urgent action needed to limit warming to 1.5°C.",
        "artificial intelligence": "AI has advanced significantly with large language models, computer vision, "
                                  "and robotics. Applications span healthcare, autonomous vehicles, and more.",
    }
    
    for key in results:
        if key in query.lower():
            return f"🔍 Search results for '{query}':\n{results[key]}"
    
    return f"🔍 Search results for '{query}':\nGeneral information found. Multiple sources indicate growing interest in this area."


@tool
def gather_statistics(topic: Annotated[str, "The topic to gather statistics about"]) -> str:
    """Gather statistical data and facts about a topic."""
    # Simulate data gathering
    time.sleep(randint(3, 10) / 10.0)
    
    stats = {
        "quantum computing": "📊 Statistics:\n- Global quantum computing market: $1.3B (2024)\n"
                            "- Expected to reach $7.6B by 2030\n- 100+ quantum computers worldwide",
        "photosynthesis": "📊 Statistics:\n- Converts ~100 billion tons of CO2 annually\n"
                         "- Efficiency: 3-6% of sunlight energy captured\n- Produces ~170 billion tons O2/year",
        "climate change": "📊 Statistics:\n- Global CO2: 420 ppm\n- Sea level rise: 3.4mm/year\n"
                         "- Arctic ice decline: 13% per decade",
        "artificial intelligence": "📊 Statistics:\n- Global AI market: $136B (2024)\n"
                                  "- Expected growth: 37% CAGR\n- AI startups: 12,000+",
    }
    
    for key in stats:
        if key in topic.lower():
            return stats[key]
    
    return f"📊 Statistics for '{topic}':\nVarious metrics available. Growing trend observed."


@tool
def verify_facts(claim: Annotated[str, "The claim to verify"]) -> str:
    """Verify the accuracy of a claim or statement."""
    # Simulate fact-checking
    time.sleep(randint(2, 8) / 10.0)
    
    return f"✓ Fact-check: The claim '{claim[:50]}...' has been cross-referenced with reliable sources. Confidence: High."


@tool
def format_article(
    content: Annotated[str, "The content to format"],
    style: Annotated[str, "The writing style (formal, casual, technical)"] = "formal"
) -> str:
    """Format content as a well-structured article."""
    # Simulate formatting
    time.sleep(randint(2, 6) / 10.0)
    
    formatted = f"""
{'='*70}
FORMATTED ARTICLE ({style.upper()} STYLE)
{'='*70}

{content}

{'='*70}
Article formatted and ready for publication.
{'='*70}
"""
    return formatted


@tool
def add_citations(text: Annotated[str, "The text to add citations to"]) -> str:
    """Add proper citations and references to the text."""
    # Simulate citation formatting
    time.sleep(randint(1, 4) / 10.0)
    
    return f"{text}\n\n📚 References:\n[1] Academic Journal of Research (2024)\n[2] Scientific Studies Database\n[3] Expert Review Publications"


# Tool lists for each agent
research_tools = [search_web, gather_statistics, verify_facts]
writing_tools = [format_article, add_citations]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Create the tracer
# ─────────────────────────────────────────────────────────────────────────────

def create_tracer() -> AzureAIOpenTelemetryTracer:
    """
    Return the global tracer instance.
    
    NOTE: Tracer is initialized at module level to ensure OpenTelemetry hooks
    are set up before any agent operations.
    """
    return azure_tracer


# ─────────────────────────────────────────────────────────────────────────────
# 3. Create LangChain Agents
# ─────────────────────────────────────────────────────────────────────────────

def create_researcher_agent(llm: AzureChatOpenAI):
    """
    Create a research agent using LangChain's create_agent with AzureChatOpenAI.
    """
    
    system_prompt = """You are a thorough research assistant with access to powerful research tools.

Your task: Conduct comprehensive research on the given topic.

Instructions:
1. ALWAYS use the search_web tool first to gather primary information
2. Use gather_statistics to get quantitative data
3. Use verify_facts to confirm key claims
4. Provide a comprehensive research summary with 3-5 key findings

Be thorough and fact-based in your research."""
    
    # Create agent using the LLM instance directly
    agent = create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=research_tools,
    )
    
    return agent


def create_writer_agent(llm: AzureChatOpenAI):
    """
    Create a writer agent using LangChain's create_agent with AzureChatOpenAI.
    """
    
    system_prompt = """You are a skilled content writer who transforms research into compelling articles.

Your task: Create a well-structured, engaging article from the research provided.

Instructions:
1. Review the research provided in the input
2. Use format_article to structure the content professionally
3. Use add_citations to include proper references
4. Create an engaging, informative article

Transform research into polished, well-formatted content."""
    
    # Create agent using the LLM instance directly
    agent = create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=writing_tools,
    )
    
    return agent


# ─────────────────────────────────────────────────────────────────────────────
# 4. Run multi-agent workflow
# ─────────────────────────────────────────────────────────────────────────────

def run_multi_agent_workflow(query: str, researcher, writer):
    """
    Run the multi-agent workflow: researcher → writer
    
    The global azure_tracer automatically captures:
    - Each agent execution as invoke_agent spans
    - LLM calls as chat spans
    - Tool executions as execute_tool spans
    
    IMPORTANT: Wraps entire workflow in a parent span to ensure single trace_id
    """
    
    # Get OpenTelemetry tracer to create parent span
    otel_tracer = trace.get_tracer(__name__)
    
    # Wrap entire workflow in parent span for unified trace_id
    with otel_tracer.start_as_current_span("Multi-Agent Workflow") as parent_span:
        parent_span.set_attribute("workflow.type", "langchain_agents")
        parent_span.set_attribute("workflow.query", query)
        
        print(f"\n{'═'*80}")
        print(f" LANGCHAIN MULTI-AGENT WORKFLOW")
        print(f"{'═'*80}")
        print(f" Query: {query}")
        print(f"{'═'*80}\n")
        
        # Use global azure_tracer via config (same pattern as working langchain_single_agent_tracing.py)
        config = {"callbacks": [azure_tracer]}
        
        # Step 1: Researcher agent conducts research
        print(f"\n{'─'*80}")
        print("[STEP 1] Researcher Agent - Conducting Research")
        print(f"{'─'*80}\n")
        
        start = time.monotonic()
        research_result = researcher.invoke(
            {"messages": [f"Research this topic thoroughly: {query}"]},
            config=config
        )
        research_time = time.monotonic() - start
        
        # Extract the final message
        research_output = research_result["messages"][-1].content
        print(f"\n{'─'*80}")
        print("[RESEARCH COMPLETE]")
        print(f"{'─'*80}")
        print(research_output)
        print(f"\n⏱️  Research time: {research_time:.2f}s")
        print(f"{'─'*80}\n")
        
        # Step 2: Writer agent creates article from research
        print(f"\n{'─'*80}")
        print("[STEP 2] Writer Agent - Creating Article")
        print(f"{'─'*80}\n")
        
        start = time.monotonic()
        writer_result = writer.invoke(
            {
                "messages": [
                    f"Create a well-formatted article based on this research:\n\n{research_output}\n\n"
                    f"Original topic: {query}"
                ]
            },
            config=config
        )
        writer_time = time.monotonic() - start
        
        final_article = writer_result["messages"][-1].content
        print(f"\n{'─'*80}")
        print("[ARTICLE COMPLETE]")
        print(f"{'─'*80}")
        print(final_article)
        print(f"\n⏱️  Writing time: {writer_time:.2f}s")
        print(f"{'─'*80}\n")
        
        # Summary
        total_time = research_time + writer_time
        print(f"\n{'═'*80}")
        print(" WORKFLOW SUMMARY")
        print(f"{'═'*80}")
        print(f" Total time: {total_time:.2f}s")
        print(f" Research time: {research_time:.2f}s")
        print(f" Writing time: {writer_time:.2f}s")
        print(f"{'═'*80}\n")
        
        parent_span.set_attribute("workflow.research_time", research_time)
        parent_span.set_attribute("workflow.writing_time", writer_time)
        parent_span.set_attribute("workflow.total_time", total_time)
        
        return {
            "research": research_output,
            "article": final_article,
            "times": {
                "research": research_time,
                "writing": writer_time,
                "total": total_time
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main execution
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Main execution function"""
    
    print("\n" + "="*80)
    print("LANGCHAIN AGENTS MULTI-AGENT WORKFLOW")
    print("="*80)
    print("Using langchain-azure-ai native Application Insights integration")
    print("Pattern: create_agent (modern LangChain pattern)")
    print("Tracer: Global azure_tracer (initialized at module level)")
    print("="*80 + "\n")
    
    # Initialize Azure OpenAI LLM with token provider for authentication
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-08-01-preview"),
        azure_ad_token_provider=token_provider,
        temperature=0.3,
    )
    
    # Create agents
    print("[✓] Creating researcher agent...")
    researcher = create_researcher_agent(llm)
    
    print("[✓] Creating writer agent...")
    writer = create_writer_agent(llm)
    
    print("[✓] Agents ready\n")
    
    # Run workflow
    queries = [
        "quantum computing",
    ]
    
    for query in queries:
        try:
            result = run_multi_agent_workflow(query, researcher, writer)
        except Exception as e:
            print(f"\n[!] Error processing query '{query}': {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("Check Application Insights for detailed telemetry data")
    print("Compare with multi_agent_workflow_langchain.py (LangGraph version)")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
