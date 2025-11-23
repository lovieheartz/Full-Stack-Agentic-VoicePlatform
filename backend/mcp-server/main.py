import logging
from fastapi import FastAPI, Request, Header
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount
from typing import Optional
from app.config import settings
from app.mcp_server import mcp_server, set_jwt_token
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# Create SSE transport
sse_transport = SseServerTransport("/messages")


@app.get("/")
async def root():
    return {"message": settings.PROJECT_NAME, "status": "running", "transport": "SSE"}


@app.get("/sse")
async def sse_endpoint(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_organization_id: Optional[str] = Header(None)
):
    """SSE endpoint for MCP communication

    Supports two authentication methods:
    1. JWT token in Authorization header (for outbound agents)
    2. Organization-ID in X-Organization-ID header (for inbound agents)
    """
    logger.info("📡 SSE connection established")

    # Extract JWT token from Authorization header
    jwt_token = None
    organization_id = None

    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]  # Remove "Bearer " prefix
        logger.info(f"🔑 JWT token received: {jwt_token[:20]}...")
    elif x_organization_id:
        organization_id = x_organization_id
        logger.info(f"🏢 Organization-ID received: {organization_id}")
    else:
        logger.warning("⚠️ No authentication provided (neither JWT nor Organization-ID)")

    # Store JWT token for this session (organization_id will be extracted from JWT in mcp_server)
    # For inbound agents without JWT, we'll pass organization_id directly
    set_jwt_token(jwt_token if jwt_token else organization_id)

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name="alsatalk-integrations",
                server_version="1.0.0",
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


# Mount the message handler for POST requests with trailing slash
app.mount("/messages/", sse_transport.handle_post_message)


if __name__ == "__main__":
    logger.info(f"🚀 Starting {settings.PROJECT_NAME} on port {settings.PORT}")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
