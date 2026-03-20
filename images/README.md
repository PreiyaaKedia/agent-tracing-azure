# Images Directory

This directory contains screenshots and visualizations referenced in the main README.md.

## Required Images

| Filename | Description | Source |
|----------|-------------|--------|
| `azure-monitor-agents-preview.png` | Azure Application Insights - Agents (Preview) dashboard showing agent runs | Capture from Azure Portal > Application Insights > Investigate > Agents (Preview) |
| `azure-monitor-trace-details.png` | Detailed trace view in Agents (Preview) showing span hierarchy | Capture from Azure Portal > Application Insights > Agents (Preview) > View Traces |
| `foundry-control-plane-agent.png` | Registered agent in Foundry Control Plane with trace entries | Capture from [ai.azure.com](https://ai.azure.com) > Operate > Assets |
| `aspire-dashboard.png` | Aspire Dashboard showing local development traces | Capture from http://localhost:18888 |

## Capturing Your Own Screenshots

### Azure Monitor - Agents (Preview)

1. Open [Azure Portal](https://portal.azure.com/)
2. Navigate to your **Application Insights** resource
3. Select **Investigate > Agents (Preview)** from the left navigation
4. Run one of the sample agents to generate traces
5. Wait 2-5 minutes for traces to appear
6. **For dashboard view** (`azure-monitor-agents-preview.png`):
   - Take a full screenshot showing:
     - Agent runs list with multiple executions
     - Model usage statistics
     - Tool execution summary
     - Overall activity dashboard
7. **For trace details** (`azure-monitor-trace-details.png`):
   - Click **View Traces with Agent Runs**
   - Select one trace from the side panel
   - Capture screenshot showing:
     - Span hierarchy (parent-child relationships)
     - Individual span details (duration, attributes)
     - Timeline view
     - Any visible content or metadata

### Foundry Control Plane

1. Deploy your agent to an accessible endpoint (public or network-reachable)
2. Register the agent in Foundry Control Plane:
   - Navigate to [Azure AI Foundry](https://ai.azure.com/)
   - Select **Operate** from toolbar
   - Click **Register agent**
   - Complete the registration wizard (agent URL, protocol, agent_id, etc.)
3. Invoke the agent to generate traces
4. Go to **Operate > Assets**
5. Select your registered agent
6. Capture screenshot showing:
   - Agent name and details
   - **Traces** section with multiple HTTP call entries
   - Request/response metadata
   - Execution status and duration

### Aspire Dashboard

1. Start Aspire Dashboard with Docker:
   ```bash
   docker run --rm -it -d -p 18888:18888 -p 4317:18889 --name aspire-dashboard mcr.microsoft.com/dotnet/aspire-dashboard:latest
   ```
2. Configure your agent to send traces to http://localhost:4317
3. Run one of the sample agents
4. Open http://localhost:18888 in your browser
5. Navigate to **Traces** view
6. Capture screenshot showing:
   - Trace list or detailed trace view
   - Timeline visualization
   - Span hierarchy with agent/LLM/tool spans

## Screenshot Specifications

- **Format**: PNG for static images
- **Resolution**: Minimum 1280x720, recommended 1920x1080
- **Quality**: High quality, no compression artifacts
- **Annotations**: Optional - add arrows or highlights to emphasize key features
- **Content**: Ensure no sensitive data (API keys, connection strings, customer data, etc.) is visible

## Tools

- **Windows**: Snipping Tool (Win + Shift + S), ShareX
- **macOS**: Screenshot (Cmd + Shift + 4), CleanShot X
- **Linux**: Flameshot, Spectacle
- **Browser Extensions**: 
  - Awesome Screenshot
  - Fireshot
  - GoFullPage

