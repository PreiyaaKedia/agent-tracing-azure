# Copyright (c) Microsoft. All rights reserved.

"""
Sequential Workflow with SequentialBuilder

This script demonstrates multi-agent orchestration using the official 
SequentialBuilder from the Microsoft Agent Framework. The Agent Framework 
automatically handles all GenAI semantic convention attributes.

Features:
- Researcher Agent: Gathers information on topics
- Writer Agent: Creates content based on research
- Sequential workflow orchestration using SequentialBuilder
- Shared conversation context flows through each agent
- Automatic GenAI instrumentation by Agent Framework
- Application Insights integration for telemetry collection
"""

import asyncio
from random import randint
from typing import Annotated, cast

from agent_framework import Agent, Message, tool
from agent_framework.observability import (
    configure_otel_providers,
    get_tracer,
    create_resource,
    enable_instrumentation,
    logger
)
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import SequentialBuilder
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects.aio import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import format_trace_id
from pydantic import Field
import os
import uuid

# Load environment variables from .env file
load_dotenv()


# Research-related tools
@tool(approval_mode="never_require")
async def search_web(
    query: Annotated[str, Field(description="The search query to find information.")],
) -> str:
    """Search the web for information on a given topic."""
    await asyncio.sleep(randint(5, 15) / 10.0)  # Simulate web search
    
    # Simulate search results
    results = {
        "climate change": "Recent studies show that global temperatures have risen by 1.1°C since pre-industrial times. "
                         "The IPCC reports indicate urgent action is needed to limit warming to 1.5°C.",
        "artificial intelligence": "AI technology has advanced significantly with large language models, computer vision, "
                                  "and robotics. Applications span from healthcare to autonomous vehicles.",
        "renewable energy": "Solar and wind power costs have dropped by over 80% in the last decade. "
                           "Many countries are transitioning to clean energy sources to combat climate change.",
    }
    
    for key in results:
        if key in query.lower():
            return f"Search results for '{query}':\n{results[key]}"
    
    return f"Search results for '{query}':\nGeneral information found on the topic. Multiple sources indicate growing interest and research in this area."


@tool(approval_mode="never_require")
async def gather_statistics(
    topic: Annotated[str, Field(description="The topic to gather statistics about.")],
) -> str:
    """Gather statistical data and facts about a topic."""
    await asyncio.sleep(randint(3, 10) / 10.0)  # Simulate data gathering
    
    stats = {
        "climate change": "- Global CO2 levels: 420 ppm\n- Sea level rise: 3.4mm/year\n- Arctic ice decline: 13% per decade",
        "artificial intelligence": "- Global AI market: $136B in 2024\n- Expected growth: 37% CAGR\n- AI startups: 12,000+",
        "renewable energy": "- Solar capacity: 1,185 GW globally\n- Wind capacity: 906 GW globally\n- Clean energy jobs: 12.7M worldwide",
    }
    
    for key in stats:
        if key in topic.lower():
            return f"Statistics for '{topic}':\n{stats[key]}"
    
    return f"Statistics for '{topic}':\nVarious metrics and data points available. Growing trend observed in recent years."


@tool(approval_mode="never_require")
async def format_article(
    content: Annotated[str, Field(description="The content to format as an article.")],
    style: Annotated[str, Field(description="The writing style (e.g., formal, casual, technical).")] = "formal",
) -> str:
    """Format content as a well-structured article."""
    await asyncio.sleep(randint(2, 8) / 10.0)  # Simulate formatting
    
    formatted = f"""
{'='*60}
FORMATTED ARTICLE ({style.upper()} STYLE)
{'='*60}

{content}

{'='*60}
Article formatted and ready for publication.
{'='*60}
"""
    return formatted


async def run_sequential_workflow(client: AzureOpenAIResponsesClient, topic: str) -> list[Message]:
    """
    Execute a sequential workflow using SequentialBuilder.
    
    The workflow:
    1. Researcher agent gathers information
    2. Writer agent creates an article based on the research
    
    The conversation context flows through each agent automatically.
    """
    
    tracer = get_tracer()
    conversation_id = str(uuid.uuid4())
    
    # Create a custom span for tracking this workflow run
    with tracer.start_as_current_span(
        "sequential_workflow_orchestration",
        kind=SpanKind.CLIENT
    ) as span:
        
        # Set custom workflow attributes
        span.set_attribute("workflow.type", "sequential_builder")
        span.set_attribute("workflow.topic", topic)
        span.set_attribute("workflow.conversation_id", conversation_id)
        span.set_attribute("workflow.agents_count", 2)
        
        trace_id = format_trace_id(span.get_span_context().trace_id)
        
        print(f"\n{'='*80}")
        print(f"SEQUENTIAL WORKFLOW - Trace ID: {trace_id}")
        print(f"Conversation ID: {conversation_id}")
        print(f"Topic: {topic}")
        print(f"{'='*80}\n")
        
        # 1) Create agents using the client.as_agent() pattern
        # Note: We use Agent() directly with tools instead of as_agent() for tool support
        researcher = Agent(
            client=client,
            tools=[search_web, gather_statistics],
            name="researcher",
            instructions="""You are a thorough research assistant. Your role is to:
1. Search for relevant information on the given topic
2. Gather statistics and factual data
3. Provide comprehensive summaries with key findings
4. Always cite your sources clearly

Be thorough and fact-based in your research. Use the available tools to gather information.""",
            id="researcher-agent-001",
        )
        
        writer = Agent(
            client=client,
            tools=[format_article],
            name="writer",
            instructions="""You are a skilled content writer. Your role is to:
1. Review the research provided by the researcher
2. Create engaging and informative content
3. Structure information clearly with proper flow
4. Use appropriate tone and style
5. Format the content professionally

Transform research into compelling, well-structured articles. Use the format_article tool to polish your final output.""",
            id="writer-agent-002",
        )
        
        # 2) Build sequential workflow: researcher -> writer
        logger.info("Building sequential workflow with researcher -> writer")
        workflow = SequentialBuilder(participants=[researcher, writer]).build()
        
        # 3) Run the workflow and collect outputs
        print(f"{'─'*80}")
        print("WORKFLOW EXECUTION")
        print(f"{'─'*80}\n")
        
        # The initial prompt/task for the workflow
        initial_prompt = f"Research the topic '{topic}' and provide comprehensive information including statistics and recent developments."
        
        outputs: list[list[Message]] = []
        
        logger.info(f"Starting workflow with prompt: {initial_prompt}")
        
        # Stream events from the workflow
        async for event in workflow.run(initial_prompt, stream=True):
            # Track different event types
            if event.type == "executor.invoke":
                agent_name = event.data.get("executor_name", "unknown")
                logger.info(f"Invoking agent: {agent_name}")
                print(f"\n🔄 Agent '{agent_name}' started...")
                
            elif event.type == "executor.completed":
                agent_name = event.data.get("executor_name", "unknown")
                logger.info(f"Agent completed: {agent_name}")
                print(f"✓ Agent '{agent_name}' completed\n")
                
            elif event.type == "output":
                # Collect the output (conversation history)
                outputs.append(cast(list[Message], event.data))
        
        # Mark workflow as complete
        span.set_attribute("workflow.status", "completed")
        span.set_attribute("workflow.messages_count", len(outputs[-1]) if outputs else 0)
        
        print(f"{'─'*80}")
        print("WORKFLOW COMPLETED")
        print(f"{'─'*80}\n")
        
        # Return the final conversation
        return outputs[-1] if outputs else []


def print_conversation(messages: list[Message]) -> None:
    """Print the conversation in a readable format."""
    print(f"\n{'='*80}")
    print("FINAL CONVERSATION HISTORY")
    print(f"{'='*80}\n")
    
    for i, msg in enumerate(messages, start=1):
        # Determine the display name
        if msg.author_name:
            name = msg.author_name
        elif msg.role == "assistant":
            name = "assistant"
        elif msg.role == "user":
            name = "user"
        else:
            name = msg.role
        
        print(f"{'-'*80}")
        print(f"{i:02d} [{name.upper()}]")
        print(f"{'-'*80}")
        print(f"{msg.text}\n")


async def main():
    """Main execution function with Application Insights integration"""
    
    # Configure OpenTelemetry providers
    configure_otel_providers(enable_sensitive_data=True)
    
    async with AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], 
        credential=DefaultAzureCredential()
    ) as project_client:
        
        # Configure Azure Monitor (Application Insights)
        try:
            conn_string = await project_client.telemetry.get_application_insights_connection_string()
            print(f"Connection String : {conn_string}")
        except Exception:
            logger.warning(
                "No Application Insights connection string found for the Azure AI Project. "
                "Please ensure Application Insights is configured in your Azure AI project, "
                "or call configure_otel_providers() manually with custom exporters."
            )
            return
        
        configure_azure_monitor(
            connection_string=conn_string,
            enable_live_metrics=True,
            resource=create_resource(),
            enable_performance_counters=False,
        )
        
        # Enable instrumentation
        enable_instrumentation(enable_sensitive_data=True)
        
        print("\n" + "="*80)
        print("SEQUENTIAL WORKFLOW WITH SEQUENTIALBUILDER")
        print("="*80)
        print("Observability configured with Application Insights")
        print("Agent Framework handles GenAI semantic conventions automatically")
        print("Using SequentialBuilder for workflow orchestration")
        print("="*80)
        
        # Initialize the OpenAI client
        client = AzureOpenAIResponsesClient(credential=DefaultAzureCredential())
        
        # Define research topics
        topics = [
            "climate change",
            "artificial intelligence",
        ]
        
        # Process each topic with the sequential workflow
        for topic in topics:
            try:
                conversation = await run_sequential_workflow(client, topic)
                
                # Display the conversation
                print_conversation(conversation)
                
                print(f"\n{'='*80}")
                print(f"WORKFLOW SUMMARY FOR: {topic.upper()}")
                print(f"{'='*80}")
                print(f"Total messages in conversation: {len(conversation)}")
                print(f"Agents involved: researcher → writer")
                print(f"Status: ✓ Completed")
                print(f"{'='*80}\n")
                
                # Wait a bit between topics
                if topic != topics[-1]:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"Failed to process topic '{topic}': {e}")
                continue
        
        print("\n" + "="*80)
        print("ALL WORKFLOWS COMPLETED")
        print("Check Application Insights for detailed telemetry data")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
