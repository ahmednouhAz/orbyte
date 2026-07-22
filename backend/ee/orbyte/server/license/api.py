"""License API endpoints for self-hosted deployments.

These endpoints allow self-hosted Orbyte instances to:
1. Claim a license after Stripe checkout (via cloud data plane proxy)
2. Upload a license file manually (for air-gapped deployments)
3. View license status and seat usage
4. Refresh/delete the local license

NOTE: Cloud (MULTI_TENANT) deployments do NOT use these endpoints.
Cloud licensing is managed via the control plane and gated_tenants Redis key.
"""

import requests
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import UploadFile
from sqlalchemy.orm import Session

from ee.orbyte.configs.app_configs import CLOUD_DATA_PLANE_URL
from ee.orbyte.db.license import delete_license as db_delete_license
from ee.orbyte.db.license import get_license
from ee.orbyte.db.license import get_license_metadata
from ee.orbyte.db.license import invalidate_license_cache
from ee.orbyte.db.license import refresh_license_cache
from ee.orbyte.db.license import update_license_cache
from ee.orbyte.db.license import upsert_license
from ee.orbyte.server.license.models import LicenseResponse
from ee.orbyte.server.license.models import LicenseSource
from ee.orbyte.server.license.models import LicenseStatusResponse
from ee.orbyte.server.license.models import LicenseUploadResponse
from ee.orbyte.server.license.models import SeatUsageResponse
from ee.orbyte.utils.license import verify_license_signature
from orbyte.auth.permissions import require_permission
from orbyte.auth.users import User
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.enums import Permission
from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError
from orbyte.utils.logger import setup_logger
from shared_configs.configs import MULTI_TENANT

logger = setup_logger()

router = APIRouter(prefix="/license")

# PEM-style delimiters used in license file format
_PEM_BEGIN = "-----BEGIN ORBYTE LICENSE-----"
_PEM_END = "-----END ORBYTE LICENSE-----"


def _strip_pem_delimiters(content: str) -> str:
    """Strip PEM-style delimiters from license content if present."""
    content = content.strip()
    if content.startswith(_PEM_BEGIN) and content.endswith(_PEM_END):
        # Remove first and last lines (the delimiters)
        lines = content.split("\n")
        return "\n".join(lines[1:-1]).strip()
    return content


@router.get("")
async def get_license_status(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> LicenseStatusResponse:
    """Get current license status and seat usage."""
    metadata = get_license_metadata(db_session)

    if not metadata:
        return LicenseStatusResponse(has_license=False)

    return LicenseStatusResponse(
        has_license=True,
        seats=metadata.seats,
        used_seats=metadata.used_seats,
        plan_type=metadata.plan_type,
        issued_at=metadata.issued_at,
        expires_at=metadata.expires_at,
        grace_period_end=metadata.grace_period_end,
        status=metadata.status,
        expiry_warning_stage=metadata.expiry_warning_stage,
        source=metadata.source,
    )


@router.get("/seats")
async def get_seat_usage(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> SeatUsageResponse:
    """Get detailed seat usage information."""
    metadata = get_license_metadata(db_session)

    if not metadata:
        return SeatUsageResponse(
            total_seats=0,
            used_seats=0,
            available_seats=0,
        )

    return SeatUsageResponse(
        total_seats=metadata.seats,
        used_seats=metadata.used_seats,
        available_seats=max(0, metadata.seats - metadata.used_seats),
    )


@router.post("/claim")
async def claim_license(
    session_id: str | None = None,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> LicenseResponse:
    """
    Claim a license from the control plane (self-hosted only).

    Two modes:
    1. With session_id: After Stripe checkout, exchange session_id for license
    2. Without session_id: Re-claim using existing license for auth

    Use without session_id after:
    - Updating seats via the billing API
    - Returning from the Stripe customer portal
    - Any operation that regenerates the license on control plane
    Claim a license from the control plane (self-hosted only).

    Two modes:
    1. With session_id: After Stripe checkout, exchange session_id for license
    2. Without session_id: Re-claim using existing license for auth
    """
    if MULTI_TENANT:
        raise OrbyteError(
            OrbyteErrorCode.VALIDATION_ERROR,
            "License claiming is only available for self-hosted deployments",
        )

    try:
        if session_id:
            # Claim license after checkout using session_id
            url = f"{CLOUD_DATA_PLANE_URL}/proxy/claim-license"
            response = requests.post(
                url,
                json={"session_id": session_id},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
        else:
            # Re-claim using existing license for auth
            metadata = get_license_metadata(db_session)
            if not metadata or not metadata.tenant_id:
                raise OrbyteError(
                    OrbyteErrorCode.VALIDATION_ERROR,
                    "No license found. Provide session_id after checkout.",
                )

            license_row = get_license(db_session)
            if not license_row or not license_row.license_data:
                raise OrbyteError(
                    OrbyteErrorCode.VALIDATION_ERROR,
                    "No license found in database",
                )

            url = f"{CLOUD_DATA_PLANE_URL}/proxy/license/{metadata.tenant_id}"
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {license_row.license_data}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

        response.raise_for_status()

        data = response.json()
        license_data = data.get("license")

        if not license_data:
            raise OrbyteError(OrbyteErrorCode.NOT_FOUND, "No license in response")

        # Verify signature before persisting
        payload = verify_license_signature(license_data)

        # Store in DB
        upsert_license(db_session, license_data)

        try:
            update_license_cache(payload, source=LicenseSource.AUTO_FETCH)
        except Exception as cache_error:
            logger.warning("Failed to update license cache: %s", cache_error)

        logger.info(
            "License claimed: seats=%s, expires=%s",
            payload.seats,
            payload.expires_at.date(),
        )
        return LicenseResponse(success=True, license=payload)

    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 502
        detail = "Failed to claim license"
        try:
            error_data = e.response.json() if e.response is not None else {}
            detail = error_data.get("detail", detail)
        except Exception:
            pass
        raise OrbyteError(
            OrbyteErrorCode.BAD_GATEWAY, detail, status_code_override=status_code
        )
    except ValueError as e:
        raise OrbyteError(OrbyteErrorCode.VALIDATION_ERROR, str(e))
    except requests.RequestException:
        raise OrbyteError(
            OrbyteErrorCode.BAD_GATEWAY, "Failed to connect to license server"
        )


@router.post("/upload")
async def upload_license(
    license_file: UploadFile = File(...),
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> LicenseUploadResponse:
    """
    Upload a license file manually (self-hosted only).

    Used for air-gapped deployments where the cloud data plane is not accessible.
    The license file must be cryptographically signed by Orbyte.
    """
    if MULTI_TENANT:
        raise OrbyteError(
            OrbyteErrorCode.VALIDATION_ERROR,
            "License upload is only available for self-hosted deployments",
        )

    try:
        content = await license_file.read()
        license_data = content.decode("utf-8").strip()
        # Strip PEM-style delimiters if present (used in .lic file format)
        license_data = _strip_pem_delimiters(license_data)
        # Remove any stray whitespace/newlines from user input
        license_data = license_data.strip()
    except UnicodeDecodeError:
        raise OrbyteError(OrbyteErrorCode.INVALID_INPUT, "Invalid license file format")

    # Verify cryptographic signature - this is the only validation needed
    # The license's tenant_id identifies the customer in control plane, not locally
    try:
        payload = verify_license_signature(license_data)
    except ValueError as e:
        raise OrbyteError(OrbyteErrorCode.VALIDATION_ERROR, str(e))

    # Persist to DB and update cache
    upsert_license(db_session, license_data)

    try:
        update_license_cache(payload, source=LicenseSource.MANUAL_UPLOAD)
    except Exception as cache_error:
        logger.warning("Failed to update license cache: %s", cache_error)

    return LicenseUploadResponse(
        success=True,
        message=f"License uploaded successfully. {payload.seats} seats, expires {payload.expires_at.date()}",
    )


@router.post("/refresh")
async def refresh_license_cache_endpoint(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> LicenseStatusResponse:
    """
    Force refresh the license cache from the local database.

    Useful after manual database changes or to verify license validity.
    Does NOT fetch from control plane - use /claim for that.
    """
    metadata = refresh_license_cache(db_session)

    if not metadata:
        return LicenseStatusResponse(has_license=False)

    return LicenseStatusResponse(
        has_license=True,
        seats=metadata.seats,
        used_seats=metadata.used_seats,
        plan_type=metadata.plan_type,
        issued_at=metadata.issued_at,
        expires_at=metadata.expires_at,
        grace_period_end=metadata.grace_period_end,
        status=metadata.status,
        expiry_warning_stage=metadata.expiry_warning_stage,
        source=metadata.source,
    )


@router.delete("")
async def delete_license(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> dict[str, bool]:
    """
    Delete the current license.

    Admin only - removes license from database and invalidates cache.
    """
    if MULTI_TENANT:
        raise OrbyteError(
            OrbyteErrorCode.VALIDATION_ERROR,
            "License deletion is only available for self-hosted deployments",
        )

    try:
        invalidate_license_cache()
    except Exception as cache_error:
        logger.warning("Failed to invalidate license cache: %s", cache_error)

    deleted = db_delete_license(db_session)

    return {"deleted": deleted}
