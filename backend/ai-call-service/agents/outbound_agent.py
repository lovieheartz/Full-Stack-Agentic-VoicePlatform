import logging
import json
import asyncio
import os
from dotenv import load_dotenv
from livekit import agents, api
from livekit.agents import AgentSession, Agent, mcp
from livekit.plugins import openai

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")


class OutboundAssistant(Agent):
    def __init__(self, instructions: str, opening_message: str = None) -> None:
        super().__init__(instructions=instructions)
        self.opening_message = opening_message


async def entrypoint(ctx: agents.JobContext):
    # Get call details from job metadata
    call_info = json.loads(ctx.job.metadata)

    phone_number = call_info.get("phone_number")
    sip_trunk_id = call_info.get("sip_trunk_id")
    # Use instructions from metadata (built by build_instructions_outbound)
    instructions = call_info.get("instructions")
    opening_message = call_info.get("opening_message")
    organization_id = call_info.get("organization_id")
    jwt_token = call_info.get("jwt_token")  # JWT token for calling integrations-service

    # Connect to LiveKit room
    await ctx.connect()

    try:
        # Create SIP participant
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone_number,
                participant_identity=phone_number,
                wait_until_answered=False,
            )
        )
    except api.TwirpError as e:
        logger.error(f"Error creating SIP participant: {e.message}")
        ctx.shutdown()
        return

    # Connect to MCP server with JWT token in headers
    logger.info(f"🔌 Connecting to MCP server: {MCP_SERVER_URL}/sse")
    mcp_client = mcp.MCPServerHTTP(
        url=f"{MCP_SERVER_URL}/sse",
        headers={"Authorization": f"Bearer {jwt_token}"},
        timeout=30.0,  # 30 seconds for tool calls (Zoom can take 5-10 seconds)
        client_session_timeout_seconds=30.0  # 30 seconds for session operations
    )
    logger.info("✅ MCP client initialized with auth token (30s timeout)")

    # Create agent session with MCP tools
    llm_model = openai.realtime.RealtimeModel()

    session = AgentSession(llm=llm_model, mcp_servers=[mcp_client])

    logger.info("🔧 MCP tools loaded and ready")

    # Real-time transcript logging
    # @session.on("conversation_item_added")
    # def log_conversation(event):
    #     try:
    #         item = event.item
    #         role = "🤖 AI" if item.role == "assistant" else "👤 USER"
    #         if hasattr(item, 'content') and item.content:
    #             content_text = item.content
    #             if isinstance(content_text, list):
    #                 content_text = ' '.join(str(c) for c in content_text)

    #             logger.info(f"{role}: {content_text}")
    #     except Exception as e:
    #         logger.error(f"Error in conversation logging: {e}")

    # Start agent session
    await session.start(
        room=ctx.room,
        agent=OutboundAssistant(instructions=instructions),
    )

    # Trigger AI greeting - use opening_message or default greeting
    if opening_message and opening_message.strip():
        await session.generate_reply(
            instructions=f"Start the conversation by saying: {opening_message}"
        )
        logger.info("✅ Greeting triggered successfully")
    else:
        # Default greeting if no opening message configured
        logger.info("📞 No opening message configured - using default greeting")
        await session.generate_reply(
            instructions="Start the conversation by greeting the caller warmly. Say something like: 'Hello! How can I help you today?'"
        )
        logger.info("✅ Default greeting triggered successfully")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="AlsaTalkOutboundAgent",
            num_idle_processes=2,
            initialize_process_timeout=10.0,
        )
    )
