"""
Zoho CRM Integration Module
Contains all Zoho-specific functions and API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import secrets
import httpx

from app.database import get_db
from app.models import Integration, Lead
from app.encryption import encryption_service
from app.security import get_current_user
from app.schemas import SaveZohoCredentialsRequest, CompleteOAuthRequest
from app.config import settings

logger = logging.getLogger(__name__)

# Create router for Zoho endpoints
router = APIRouter()


# ============================================================================
# HELPER FUNCTION - Token Refresh
# ============================================================================

async def refresh_zoho_token(integration: Integration, db: Session) -> dict:
    """
    Refresh expired Zoho access token using refresh token
    Returns updated credentials dict with new access token
    """
    credentials = encryption_service.decrypt_credentials(integration.config)
    refresh_token = credentials.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token available. Please re-authorize."
        )

    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")
    zoho_accounts_server = credentials.get("zoho_accounts_server", "accounts.zoho.com")
    token_url = f"https://{zoho_accounts_server}/oauth/v2/token"

    logger.info("Refreshing Zoho access token...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            token_data = response.json()

        if "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to refresh token: missing access_token"
            )

        # Update credentials with new access token
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        credentials["access_token"] = token_data["access_token"]
        credentials["token_expires_at"] = expires_at.isoformat()

        # Save to database
        integration.config = encryption_service.encrypt_credentials(credentials)
        db.commit()

        logger.info("✅ Token refreshed successfully")
        return credentials

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response else str(e)
        logger.error(f"Token refresh failed: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to refresh token: {error_detail}"
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


# ============================================================================
# ZOHO CRM API ENDPOINTS
# ============================================================================

@router.post("/integrations/zoho/connect")
async def connect_zoho_crm(
    request: SaveZohoCredentialsRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 Connect Zoho CRM - Save credentials and get OAuth authorization URL

    **Request:**
    ```json
    {
        "zoho_organization_id": "60057943135",
        "client_id": "1000.XXXX",
        "client_secret": "xxxx",
        "zoho_region": "in"
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "message": "Credentials saved. Please authorize.",
        "authorization_url": "https://accounts.zoho.in/oauth/v2/auth?...",
        "state": "csrf_token",
        "integration_id": "uuid"
    }
    ```

    **Flow:**
    1. Frontend sends credentials
    2. Backend saves and returns OAuth URL
    3. Frontend opens OAuth URL in popup
    4. User authorizes
    5. Frontend calls /oauth/complete with code
    """
    try:
        alsatalk_org_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CONNECT ZOHO CRM ===")
        logger.info(f"AlsaTalk Org: {alsatalk_org_id}")
        logger.info(f"Zoho Org: {request.zoho_organization_id}")
        logger.info(f"Region: {request.zoho_region}")

        # Determine Zoho servers based on region
        zoho_accounts_server = f"accounts.zoho.{request.zoho_region}"
        zoho_api_domain = f"zohoapis.{request.zoho_region}"

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)

        # Prepare encrypted credentials
        credentials_data = {
            "zoho_organization_id": request.zoho_organization_id,
            "client_id": request.client_id,
            "client_secret": request.client_secret,
            "zoho_region": request.zoho_region,
            "zoho_accounts_server": zoho_accounts_server,
            "zoho_api_domain": zoho_api_domain,
            "oauth_state": state,
            "oauth_user_id": current_user.get("sub"),
            "oauth_initiated_at": datetime.utcnow().isoformat()
        }

        encrypted_config = encryption_service.encrypt_credentials(credentials_data)

        # Check if integration exists
        existing = db.query(Integration).filter(
            Integration.organization_id == alsatalk_org_id,
            Integration.type == "crm",
            Integration.provider == "zoho"
        ).first()

        if existing:
            existing.config = encrypted_config
            existing.is_active = True
            existing.is_connected = False
            integration_id = str(existing.id)
            logger.info(f"Updated integration: {integration_id}")
        else:
            new_integration = Integration(
                organization_id=alsatalk_org_id,
                name="Zoho CRM",
                type="crm",
                provider="zoho",
                config=encrypted_config,
                is_active=True,
                is_connected=False
            )
            db.add(new_integration)
            db.flush()
            integration_id = str(new_integration.id)
            logger.info(f"Created integration: {integration_id}")

        db.commit()

        # Build OAuth URL
        redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
        scope = "ZohoCRM.modules.leads.READ,ZohoCRM.modules.leads.ALL,ZohoCRM.modules.contacts.READ,ZohoCRM.modules.contacts.ALL,ZohoCRM.users.READ"

        auth_url = (
            f"https://{zoho_accounts_server}/oauth/v2/auth"
            f"?scope={scope}"
            f"&client_id={request.client_id}"
            f"&response_type=code"
            f"&access_type=offline"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&prompt=consent"
        )

        logger.info(f"✅ OAuth URL generated")

        return {
            "success": True,
            "message": "Zoho CRM credentials saved. Please authorize in popup.",
            "authorization_url": auth_url,
            "state": state,
            "integration_id": integration_id,
            "provider": "zoho"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Zoho CRM: {str(e)}"
        )


@router.post("/integrations/zoho/oauth/complete")
async def complete_zoho_oauth(
    request: CompleteOAuthRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Complete OAuth - Exchange authorization code for tokens

    **Request:**
    ```json
    {
        "code": "authorization_code_from_zoho",
        "state": "csrf_token"
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "message": "Zoho CRM connected successfully!",
        "expires_at": "2025-01-18T12:00:00",
        "integration_id": "uuid"
    }
    ```

    **What happens:**
    1. Validates CSRF state token
    2. Exchanges code for access_token + refresh_token
    3. **Saves tokens encrypted in database**
    4. Sets is_connected = true
    """
    logger.info(f"=== COMPLETE OAUTH ===")
    logger.info(f"Organization: {current_user['organization_id']}")

    # Get integration
    integration = db.query(Integration).filter(
        Integration.organization_id == uuid.UUID(current_user["organization_id"]),
        Integration.type == "crm",
        Integration.provider == "zoho",
        Integration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zoho integration not found. Please connect first."
        )

    # Decrypt credentials
    credentials = encryption_service.decrypt_credentials(integration.config)

    # Verify CSRF state
    stored_state = credentials.get("oauth_state")
    if not stored_state or stored_state != request.state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Possible CSRF attack."
        )

    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")
    zoho_accounts_server = credentials.get("zoho_accounts_server", "accounts.zoho.com")

    # Exchange code for tokens
    redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
    token_url = f"https://{zoho_accounts_server}/oauth/v2/token"

    logger.info("Exchanging code for tokens...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "code": request.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            token_data = response.json()

        # Validate response
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Zoho OAuth error: {token_data.get('error')}"
            )

        if "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing access_token in response"
            )

        # Calculate expiration
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Extract API domain
        api_domain_full = token_data.get("api_domain", "https://www.zohoapis.com")
        api_domain = api_domain_full.replace("https://www.", "").replace("http://www.", "")

        # Update credentials with tokens
        credentials["access_token"] = token_data["access_token"]
        credentials["refresh_token"] = token_data.get("refresh_token", "")
        credentials["token_expires_at"] = expires_at.isoformat()
        credentials["zoho_api_domain"] = api_domain
        credentials["oauth_completed"] = True
        credentials["oauth_completed_at"] = datetime.utcnow().isoformat()

        # Remove temporary OAuth state
        credentials.pop("oauth_state", None)
        credentials.pop("oauth_user_id", None)
        credentials.pop("oauth_initiated_at", None)

        # Save encrypted credentials with tokens
        integration.config = encryption_service.encrypt_credentials(credentials)
        integration.is_connected = True
        integration.last_sync_at = datetime.utcnow()
        db.commit()

        logger.info(f"✅ OAuth completed! Tokens saved in database.")

        return {
            "success": True,
            "message": "Zoho CRM connected successfully! You can now import leads.",
            "expires_at": expires_at.isoformat(),
            "integration_id": str(integration.id)
        }

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response else str(e)
        logger.error(f"❌ Token exchange failed: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code: {error_detail}"
        )
    except Exception as e:
        logger.error(f"❌ OAuth error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth failed: {str(e)}"
        )


@router.get("/integrations/zoho/webhook/import-selected-leads/{ids:path}")
async def import_leads_from_zoho_button(
    ids: str,
    zoho_organization_id: str,
    db: Session = Depends(get_db)
):
    """
    📥 Import Selected Leads from Zoho Custom Button

    **Called by:** Zoho CRM Custom Button (No JWT required)

    **URL Format (Path Parameter):**
    ```
    GET /integrations/zoho/webhook/import-selected-leads/1234,5678?zoho_organization_id=60057943135
    ```

    **Parameters:**
    - ids: Comma-separated Zoho lead IDs in path (e.g., "1234,5678")
    - zoho_organization_id: Zoho's organization ID (query parameter)

    **Response:**
    ```json
    {
        "success": true,
        "message": "Imported 3 of 3 leads",
        "successful": 3,
        "failed": 0,
        "results": [...]
    }
    ```

    **What it does:**
    1. Finds AlsaTalk org by matching Zoho org ID
    2. Fetches lead details from Zoho API
    3. Auto-refreshes token if expired
    4. Saves leads to database
    5. Prevents duplicates by checking crm_id
    """
    logger.info(f"=== IMPORT LEADS FROM ZOHO BUTTON ===")

    if not ids:
        return {
            "success": False,
            "message": "No lead IDs provided",
            "successful": 0,
            "failed": 0
        }

    # Parse lead IDs
    id_list = [lead_id.strip() for lead_id in ids.split(",") if lead_id.strip()]

    if not id_list:
        return {
            "success": False,
            "message": "No valid lead IDs provided",
            "successful": 0,
            "failed": 0
        }

    logger.info(f"Lead IDs: {id_list}")
    logger.info(f"Zoho Org ID: {zoho_organization_id}")

    # Find integration by Zoho org ID
    all_integrations = db.query(Integration).filter(
        Integration.type == "crm",
        Integration.provider == "zoho",
        Integration.is_active == True
    ).all()

    integration = None
    alsatalk_org_id = None

    for integ in all_integrations:
        if integ.config:
            try:
                credentials = encryption_service.decrypt_credentials(integ.config)
                if credentials.get("zoho_organization_id") == zoho_organization_id:
                    integration = integ
                    alsatalk_org_id = integ.organization_id
                    logger.info(f"✅ Found integration for AlsaTalk org: {alsatalk_org_id}")
                    break
            except Exception as e:
                logger.warning(f"Could not decrypt integration {integ.id}: {e}")
                continue

    if not integration or not integration.config:
        logger.warning("❌ No integration found")
        return {
            "success": False,
            "message": f"OAuth not configured for Zoho org {zoho_organization_id}",
            "successful": 0,
            "failed": len(id_list)
        }

    # Get access token
    credentials = encryption_service.decrypt_credentials(integration.config)
    access_token = credentials.get("access_token")
    api_domain = credentials.get("zoho_api_domain", "zohoapis.com")

    if not access_token:
        logger.warning("❌ No access token")
        return {
            "success": False,
            "message": "OAuth not completed. Please authorize first.",
            "successful": 0,
            "failed": len(id_list)
        }

    results = []
    successful = 0
    failed = 0

    # Import each lead
    for lead_id in id_list:
        try:
            logger.info(f"Fetching lead {lead_id}...")

            # Fetch lead from Zoho
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://www.{api_domain}/crm/v2/Leads/{lead_id}",
                    headers={"Authorization": f"Zoho-oauthtoken {access_token}"}
                )

                # Auto-refresh token if expired
                if response.status_code == 401:
                    logger.info("Token expired, refreshing...")
                    credentials = await refresh_zoho_token(integration, db)
                    access_token = credentials.get("access_token")
                    api_domain = credentials.get("zoho_api_domain", "zohoapis.com")

                    # Retry with new token
                    response = await client.get(
                        f"https://www.{api_domain}/crm/v2/Leads/{lead_id}",
                        headers={"Authorization": f"Zoho-oauthtoken {access_token}"}
                    )

                response.raise_for_status()
                lead_response = response.json()

                if "data" not in lead_response or not lead_response["data"]:
                    raise Exception(f"No data returned for lead {lead_id}")

                lead_data = lead_response["data"][0]

            # Validate phone number
            phone = lead_data.get("Phone") or lead_data.get("Mobile")
            if not phone:
                results.append({
                    "zoho_id": lead_id,
                    "success": False,
                    "error": "No phone number"
                })
                failed += 1
                logger.warning(f"⚠️ Lead {lead_id}: No phone number")
                continue

            # Check for duplicate
            existing_lead = db.query(Lead).filter(
                Lead.organization_id == alsatalk_org_id,
                Lead.crm_id == lead_id
            ).first()

            if existing_lead:
                results.append({
                    "zoho_id": lead_id,
                    "success": False,
                    "error": "Already imported",
                    "existing_lead_id": str(existing_lead.id)
                })
                failed += 1
                logger.info(f"⚠️ Lead {lead_id}: Already exists")
                continue

            # Create new lead
            new_lead = Lead(
                organization_id=alsatalk_org_id,
                first_name=lead_data.get("First_Name"),
                last_name=lead_data.get("Last_Name"),
                email=lead_data.get("Email"),
                phone=phone,
                company=lead_data.get("Company"),
                status=lead_data.get("Lead_Status", "new"),
                source="zoho_crm",
                crm_id=lead_id,
                extra_data={
                    "Full_Name": lead_data.get("Full_Name"),
                    "Mobile": lead_data.get("Mobile"),
                    "Title": lead_data.get("Title"),
                    "Lead_Source": lead_data.get("Lead_Source"),
                    "Description": lead_data.get("Description"),
                    "zoho_modified_time": lead_data.get("Modified_Time"),
                    "zoho_created_time": lead_data.get("Created_Time")
                }
            )
            db.add(new_lead)
            db.commit()
            db.refresh(new_lead)

            full_name = lead_data.get("Full_Name") or f"{lead_data.get('First_Name', '')} {lead_data.get('Last_Name', '')}".strip()

            results.append({
                "zoho_id": lead_id,
                "success": True,
                "lead_id": str(new_lead.id),
                "name": full_name
            })
            successful += 1
            logger.info(f"✅ Lead {lead_id}: Imported successfully")

        except Exception as e:
            logger.error(f"❌ Lead {lead_id}: {str(e)}")
            results.append({
                "zoho_id": lead_id,
                "success": False,
                "error": str(e)
            })
            failed += 1

    logger.info(f"=== IMPORT COMPLETE: {successful} success, {failed} failed ===")

    return {
        "success": True,
        "message": f"Imported {successful} of {len(id_list)} selected leads",
        "successful": successful,
        "failed": failed,
        "results": results
    }
