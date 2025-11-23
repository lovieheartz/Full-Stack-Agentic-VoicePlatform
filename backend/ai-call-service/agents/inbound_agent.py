import json
import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, mcp
from livekit.plugins import openai
import uuid

# Add parent directory to path to import from app
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_db
from app.models import Agent as AgentModel, AgentType
from app.instructions.inbound_instructions import build_instructions_inbound

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")


class InboundAssistant(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(instructions=instructions)


async def entrypoint(ctx: agents.JobContext):
    # Get call info from metadata first
    call_info = {}
    if ctx.job.metadata and ctx.job.metadata.strip():
        try:
            call_info = json.loads(ctx.job.metadata)
        except json.JSONDecodeError:
            pass

    # METHOD 1: Get agent by ID from metadata
    agent_id = call_info.get("agent_id")
    organization_id = call_info.get("organization_id")

    if not agent_id or not organization_id:
        return

    # Load agent configuration from database
    try:
        db = next(get_db())

        agent = db.query(AgentModel).filter(
            AgentModel.id == uuid.UUID(agent_id),
            AgentModel.organization_id == uuid.UUID(organization_id),
            AgentModel.type == AgentType.INBOUND
        ).first()

        if not agent:
            db.close()
            return

        db.close()

    except Exception as e:
        if 'db' in locals():
            db.close()
        return

    # Build instructions using build_instructions helper
    final_instructions = build_instructions_inbound(
        agent_prompt=agent.system_prompt,
        lead_data={},
        opening_message=agent.opening_message,
        capabilities=agent.capabilities if agent.capabilities else {}
    )

    # Connect to room - this triggers the call to be answered
    await ctx.connect()

    # Connect to MCP server with organization_id in headers
    logger.info(f"🔌 Connecting to MCP server: {MCP_SERVER_URL}/sse")
    mcp_client = mcp.MCPServerHTTP(
        url=f"{MCP_SERVER_URL}/sse",
        headers={"X-Organization-ID": organization_id},
        timeout=30.0,  # 30 seconds for tool calls
        client_session_timeout_seconds=30.0
    )
    logger.info(f"✅ MCP client initialized with organization_id: {organization_id}")

    # Create agent session with configured voice and MCP tools
    llm_model = openai.realtime.RealtimeModel()
    session = AgentSession(llm=llm_model, mcp_servers=[mcp_client])

    logger.info("🔧 MCP tools loaded and ready")

    # Start agent session - this answers the call
    await session.start(
        room=ctx.room,
        agent=InboundAssistant(instructions=final_instructions),
    )

    # Trigger greeting if configured
    if agent.opening_message:
        await session.generate_reply(
            instructions=f"Start the conversation by saying: {agent.opening_message}"
        )
        logger.info("✅ Greeting triggered successfully")
    else:
        logger.info("📞 No opening message - AI will wait for user to speak first")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="AlsaTalkInboundAgent",
        )
    )
