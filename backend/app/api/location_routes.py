"""Metadata routes for Indian locations."""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.citizen import SuccessResponse
from app.services.india_location_service import get_india_locations

logger = get_logger(__name__)
router = APIRouter(prefix="/meta", tags=["Metadata"])


@router.get(
    "/india-locations",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get Indian states and districts",
    description="Return the canonical list of Indian states/union territories and their districts.",
)
async def india_locations():
    """Get the state and district master data used by the frontend."""

    location_data = get_india_locations()
    logger.info(
        "Returning Indian location metadata: %s states, %s districts",
        location_data["state_count"],
        location_data["district_count"],
    )

    return SuccessResponse(
        success=True,
        message="Indian location metadata retrieved successfully",
        data=location_data,
    )
