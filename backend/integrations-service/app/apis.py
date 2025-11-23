"""
Generic Integration Service APIs
For integration management (list, get, update, delete)
Specific integrations are in app/integrations/ folder
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import uuid

from app.database import get_db
from app.models import Integration
from app.security import get_current_user, get_current_user_flexible
from app.schemas import (
    IntegrationResponse,
    ListIntegrationsResponse,
    IntegrationListItem,
    UpdateIntegrationRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# GENERIC INTEGRATION MANAGEMENT APIs
# ============================================================================

async def _list_integrations_impl(
    type: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """Internal implementation for listing integrations"""
    try:
        organization_id = current_user["organization_id"]

        # Base query
        query = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id)
        )

        # Apply type filter if provided
        if type:
            query = query.filter(Integration.type == type)

        # Get all integrations
        integrations = query.order_by(Integration.created_at.desc()).all()

        # Convert to response format
        integration_list = [
            IntegrationListItem(
                id=str(integration.id),
                name=integration.name,
                type=integration.type,
                provider=integration.provider,
                is_active=integration.is_active,
                is_connected=integration.is_connected,
                created_at=integration.created_at.isoformat()
            )
            for integration in integrations
        ]

        return ListIntegrationsResponse(integrations=integration_list)

    except Exception as e:
        logger.error(f"Error listing integrations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list integrations: {str(e)}")


@router.get("/integrations/list", response_model=ListIntegrationsResponse)
async def list_integrations(
    type: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """
    List all integrations for the organization

    **Query parameters:**
    - type (optional): Filter by integration type (crm, sms, messaging, etc.)
    """
    return await _list_integrations_impl(type=type, db=db, current_user=current_user)


@router.get("/integrations", response_model=ListIntegrationsResponse)
async def list_integrations_alias(
    type: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """
    List all integrations for the organization (alias route for backward compatibility)

    **Query parameters:**
    - type (optional): Filter by integration type (crm, sms, messaging, etc.)
    """
    return await _list_integrations_impl(type=type, db=db, current_user=current_user)


@router.get("/integrations/get/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """
    Get a specific integration by ID
    """
    try:
        organization_id = current_user["organization_id"]

        # Find integration
        integration = db.query(Integration).filter(
            Integration.id == uuid.UUID(integration_id),
            Integration.organization_id == uuid.UUID(organization_id)
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        return IntegrationResponse(
            id=str(integration.id),
            name=integration.name,
            type=integration.type,
            provider=integration.provider,
            is_active=integration.is_active,
            is_connected=integration.is_connected,
            created_at=integration.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get integration: {str(e)}")


@router.put("/integrations/update/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: str,
    request: UpdateIntegrationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update integration details (name, is_active status)

    **Request body:**
    - name (optional): Update integration name
    - is_active (optional): Enable/disable integration
    """
    try:
        organization_id = current_user["organization_id"]

        # Find integration
        integration = db.query(Integration).filter(
            Integration.id == uuid.UUID(integration_id),
            Integration.organization_id == uuid.UUID(organization_id)
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Update fields if provided
        if request.name is not None:
            integration.name = request.name

        if request.is_active is not None:
            integration.is_active = request.is_active

        db.commit()
        db.refresh(integration)

        logger.info(f"Updated integration: {integration_id}")

        return IntegrationResponse(
            id=str(integration.id),
            name=integration.name,
            type=integration.type,
            provider=integration.provider,
            is_active=integration.is_active,
            is_connected=integration.is_connected,
            created_at=integration.created_at.isoformat(),
            message="Integration updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating integration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update integration: {str(e)}")


async def _delete_integration_impl(
    integration_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Internal implementation for deleting integrations"""
    try:
        alsatalk_org_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== DELETE INTEGRATION ===")
        logger.info(f"Integration ID: {integration_id}")
        logger.info(f"Organization: {alsatalk_org_id}")

        # Find integration
        integration = db.query(Integration).filter(
            Integration.id == uuid.UUID(integration_id),
            Integration.organization_id == alsatalk_org_id
        ).first()

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        # Store info before deletion
        provider_name = f"{integration.provider} {integration.type}".title()

        # Delete integration
        db.delete(integration)
        db.commit()

        logger.info(f"✅ Deleted integration: {integration_id}")

        return {
            "success": True,
            "message": f"{provider_name} integration deleted successfully",
            "integration_id": integration_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting integration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete integration: {str(e)}"
        )


@router.delete("/integrations/delete/{integration_id}")
async def delete_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🗑️ Delete Integration

    **Authentication:** JWT Required

    **URL:** DELETE /integrations/delete/{integration_id}

    **Response:**
    ```json
    {
        "success": true,
        "message": "Integration deleted successfully",
        "integration_id": "uuid"
    }
    ```
    """
    return await _delete_integration_impl(integration_id=integration_id, current_user=current_user, db=db)


@router.delete("/integrations/{integration_id}")
async def delete_integration_alias(
    integration_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🗑️ Delete Integration (alias route for backward compatibility)

    **Authentication:** JWT Required

    **URL:** DELETE /integrations/{integration_id}

    **Response:**
    ```json
    {
        "success": true,
        "message": "Integration deleted successfully",
        "integration_id": "uuid"
    }
    ```
    """
    return await _delete_integration_impl(integration_id=integration_id, current_user=current_user, db=db)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/integrations/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "integrations-service",
        "message": "All integration endpoints available",
        "integrations": {
            "zoho": "app/integrations/zoho.py",
            "twilio": "app/integrations/twilio.py",
            "gmail": "app/integrations/gmail.py",
            "zoom": "app/integrations/zoom.py"
        }
    }
