# Copyright (c) Microsoft. All rights reserved.

"""
Multi-Agent Orchestration with OpenTelemetry

This script demonstrates a multi-agent workflow where the Agent Framework 
automatically handles all GenAI semantic convention attributes. We only add 
custom orchestration-level tracking for business workflows.

Features:
- Researcher Agent: Gathers information on topics
- Writer Agent: Creates content based on research
- Automatic GenAI instrumentation by Agent Framework
- Custom orchestration tracking for workflow coordination
- Application Insights integration for telemetry collection
"""

import asyncio
from random import randint
from typing import Annotated, List, Dict

from agent_framework import Agent, tool
from agent_framework.observability import (
    configure_otel_providers, 
    get_tracer, 
    create_resource, 
    enable_instrumentation, 
    logger
)
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects.aio import AIProjectClient
from agent_framework.azure import AzureOpenAIResponsesClient
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


# Writing tools
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


class MultiAgentOrchestrator:
    """Orchestrates a multi-agent workflow with proper observability"""
    
    def __init__(self, client: AzureOpenAIResponsesClient):
        self.client = client
        self.tracer = get_tracer()
        self.conversation_id = str(uuid.uuid4())
        
        # Initialize agents with proper metadata
        self.researcher = self._create_researcher_agent()
        self.writer = self._create_writer_agent()
        
    def _create_researcher_agent(self) -> Agent:
        """Create the Researcher agent with proper instrumentation"""
        
        agent = Agent(
            client=self.client,
            tools=[search_web, gather_statistics],
            name="ResearchAgent",
            instructions="""You are a thorough research assistant. Your role is to:
1. Search for relevant information on topics
2. Gather statistics and factual data
3. Provide comprehensive summaries
4. Always cite your findings clearly
Be thorough and fact-based in your research.""",
            id="researcher-agent-001",
        )
        
        return agent
    
    def _create_writer_agent(self) -> Agent:
        """Create the Writer agent with proper instrumentation"""
        
        agent = Agent(
            client=self.client,
            tools=[format_article],
            name="WriterAgent",
            instructions="""You are a skilled content writer. Your role is to:
1. Create engaging and informative content
2. Structure information clearly
3. Use appropriate tone and style
4. Format content professionally
Transform research into compelling articles.""",
            id="writer-agent-002",
        )
        
        return agent
    
    async def invoke_agent_with_custom_tracking(
        self, 
        agent: Agent, 
        session,
        query: str, 
        role: str
    ) -> str:
        """
        Invoke an agent with custom orchestration tracking.
        
        The Agent Framework automatically handles all GenAI semantic convention attributes.
        We only add custom business-level attributes for our orchestration workflow.
        
        Args:
            agent: The agent to invoke
            session: The agent session
            query: The query/task for the agent
            role: The role of this agent in the workflow (e.g., "researcher", "writer")
            
        Returns:
            The agent's response
        """
        
        # Optional: Add a custom span for orchestration-level tracking
        # The agent.run() already creates spans with GenAI semantic conventions
        with self.tracer.start_as_current_span(
            f"{role}_phase",
            kind=SpanKind.INTERNAL,
        ) as span:
            
            # Add custom orchestration attributes (not GenAI semantic conventions)
            span.set_attribute("workflow.role", role)
            span.set_attribute("workflow.conversation_id", self.conversation_id)
            span.set_attribute("workflow.task", query[:100])  # Truncate for brevity
            
            logger.info(f"Invoking {role} agent")
            logger.info(f"Task: {query}")
            
            response_parts = []
            
            # Agent Framework handles all GenAI tracing automatically!
            async for update in agent.run(query, session=session, stream=True):
                if update.text:
                    response_parts.append(update.text)
            
            full_response = "".join(response_parts)
            
            # Add custom business metrics
            span.set_attribute("workflow.response_length", len(full_response))
            
            logger.info(f"{role.capitalize()} agent completed successfully")
            
            return full_response
    
    async def process_research_and_write(self, topic: str) -> Dict[str, str]:
        """
        Execute a multi-agent workflow: Research -> Write
        
        The Agent Framework automatically instruments all agent calls with GenAI semantic conventions.
        We only add custom orchestration-level tracking.
        """
        
        with self.tracer.start_as_current_span(
            "multi_agent_orchestration",
            kind=SpanKind.CLIENT
        ) as root_span:
            
            # Set custom orchestration-level attributes
            root_span.set_attribute("workflow.type", "sequential")
            root_span.set_attribute("workflow.agents_count", 2)
            root_span.set_attribute("workflow.topic", topic)
            root_span.set_attribute("workflow.conversation_id", self.conversation_id)
            
            print(f"\n{'='*80}")
            print(f"MULTI-AGENT ORCHESTRATION - Trace ID: {format_trace_id(root_span.get_span_context().trace_id)}")
            print(f"Conversation ID: {self.conversation_id}")
            print(f"Topic: {topic}")
            print(f"{'='*80}\n")
            
            # Step 1: Research Phase
            print(f"\n{'─'*80}")
            print("PHASE 1: RESEARCH")
            print(f"{'─'*80}")
            
            researcher_session = self.researcher.create_session()
            research_query = f"Research the topic '{topic}'. Provide comprehensive information including statistics and recent developments."
            
            print(f"\nResearcher Agent: ", end="")
            research_results = await self.invoke_agent_with_custom_tracking(
                agent=self.researcher,
                session=researcher_session,
                query=research_query,
                role="researcher"
            )
            print(research_results)
            
            # Step 2: Writing Phase
            print(f"\n{'─'*80}")
            print("PHASE 2: WRITING")
            print(f"{'─'*80}")
            
            writer_session = self.writer.create_session()
            writing_query = f"Based on this research:\n\n{research_results}\n\nWrite a well-structured article about '{topic}' in a formal style."
            
            print(f"\nWriter Agent: ", end="")
            article = await self.invoke_agent_with_custom_tracking(
                agent=self.writer,
                session=writer_session,
                query=writing_query,
                role="writer"
            )
            print(article)
            
            # Mark orchestration as complete
            root_span.set_attribute("workflow.status", "completed")
            root_span.set_attribute("workflow.phases_completed", 2)
            
            print(f"\n{'='*80}")
            print("MULTI-AGENT ORCHESTRATION COMPLETED")
            print(f"{'='*80}\n")
            
            return {
                "topic": topic,
                "research": research_results,
                "article": article,
                "conversation_id": self.conversation_id
            }


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
        print("MULTI-AGENT ORCHESTRATION WITH OPENTELEMETRY")
        print("="*80)
        print("Observability configured with Application Insights")
        print("Agent Framework handles GenAI semantic conventions automatically")
        print("Custom orchestration tracking for workflow coordination")
        print("="*80)
        
        # Initialize the orchestrator
        orchestrator = MultiAgentOrchestrator(
            client=AzureOpenAIResponsesClient(credential=DefaultAzureCredential())
        )
        
        # Define research topics
        topics = [
            "climate change",
            "artificial intelligence",
        ]
        
        # Process each topic with the multi-agent workflow
        for topic in topics:
            try:
                results = await orchestrator.process_research_and_write(topic)
                
                print(f"\n{'='*80}")
                print(f"WORKFLOW SUMMARY FOR: {topic.upper()}")
                print(f"{'='*80}")
                print(f"Conversation ID: {results['conversation_id']}")
                print(f"Research completed: ✓")
                print(f"Article written: ✓")
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
