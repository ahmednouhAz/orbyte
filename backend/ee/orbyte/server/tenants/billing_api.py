"""Billing API endpoints for cloud multi-tenant deployments.

DEPRECATED: These /tenants/* billing endpoints are being replaced by /admin/billing/*
which provides a unified API for both self-hosted and cloud deployments.

TODO(ENG-3533): Migrate frontend to use /admin/billing/* endpoints and remove this file.
https://linear.app/orbyte-app/issue/ENG-3533/migrate-tenantsbilling-adminbilling

Current endpoints to migrate:
- GET  /tenants/billing-information     -> GET  /admin/billing/information
- POST /tenants/create-customer-portal-session -> POST /admin/billing/portal-session
- POST /tenants/create-subscription-session    -> POST /admin/billing/checkout-session
- GET  /tenants/stripe-publishable-key  -> (keep as-is, shared endpoint)

Note: /tenants/product-gating/* endpoints are control-plane-to-data-plane calls
and are NOT part of this migration - they stay here.
"""

import asyncio

import httpx
from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from ee.orbyte.server.billing.api import update_seats as _admin_update_seats
from ee.orbyte.server.billing.models import SeatUpdateRequest
from ee.orbyte.server.billing.models import SeatUpdateResponse
from ee.orbyte.server.tenants.access import control_plane_dep
from ee.orbyte.server.tenants.billing import fetch_billing_information
from ee.orbyte.server.tenants.billing import fetch_customer_portal_session
from ee.orbyte.server.tenants.billing import fetch_stripe_checkout_session
from ee.orbyte.server.tenants.models import BillingInformation
from ee.orbyte.server.tenants.models import CreateCheckoutSessionRequest
from ee.orbyte.server.tenants.models import CreateSubscriptionSessionRequest
from ee.orbyte.server.tenants.models import ProductGatingFullSyncRequest
from ee.orbyte.server.tenants.models import ProductGatingRequest
from ee.orbyte.server.tenants.models import ProductGatingResponse
from ee.orbyte.server.tenants.models import StripePublishableKeyResponse
from ee.orbyte.server.tenants.models import SubscriptionSessionResponse
from ee.orbyte.server.tenants.models import SubscriptionStatusResponse
from ee.orbyte.server.tenants.models import TierUpdateRequest
from ee.orbyte.server.tenants.models import TierUpdateResponse
from ee.orbyte.server.tenants.product_gating import overwrite_full_gated_set
from ee.orbyte.server.tenants.product_gating import store_product_gating
from ee.orbyte.server.tenants.tier_management import update_tenant_tier
from orbyte.auth.permissions import require_permission
from orbyte.auth.users import User
from orbyte.configs.app_configs import STRIPE_PUBLISHABLE_KEY_OVERRIDE
from orbyte.configs.app_configs import STRIPE_PUBLISHABLE_KEY_URL
from orbyte.configs.app_configs import WEB_DOMAIN
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.enums import Permission
from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError
from orbyte.utils.logger import setup_logger
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

router = APIRouter(prefix="/tenants")

# Cache for Stripe publishable key to avoid hitting S3 on every request
_stripe_publishable_key_cache: str | None = None
_stripe_key_lock = asyncio.Lock()


@router.post("/product-gating")
def gate_product(
    product_gating_request: ProductGatingRequest, _: None = Depends(control_plane_dep)
) -> ProductGatingResponse:
    """
    Gating the product means that the product is not available to the tenant.
    They will be directed to the billing page.
    We gate the product when their subscription has ended.
    """
    try:
        store_product_gating(
            product_gating_request.tenant_id, product_gating_request.application_status
        )
        return ProductGatingResponse(updated=True, error=None)

    except Exception as e:
        logger.exception("Failed to gate product")
        return ProductGatingResponse(updated=False, error=str(e))


@router.post("/product-gating/full-sync")
def gate_product_full_sync(
    product_gating_request: ProductGatingFullSyncRequest,
    _: None = Depends(control_plane_dep),
) -> ProductGatingResponse:
    """
    Bulk operation to overwrite the entire gated tenant set.
    This replaces all currently gated tenants with the provided list.
    Gated tenants are not available to access the product and will be
    directed to the billing page when their subscription has ended.
    """
    try:
        overwrite_full_gated_set(product_gating_request.gated_tenant_ids)
        return ProductGatingResponse(updated=True, error=None)

    except Exception as e:
        logger.exception("Failed to gate products during full sync")
        return ProductGatingResponse(updated=False, error=str(e))


@router.post("/tier-update")
def update_tier(
    tier_update_request: TierUpdateRequest,
    _: None = Depends(control_plane_dep),
) -> TierUpdateResponse:
    try:
        update_tenant_tier(
            tier_update_request.tenant_id,
            tier_update_request.customer_tier,
            tier_update_request.trial_end,
        )
        return TierUpdateResponse(updated=True, error=None)
    except Exception as e:
        logger.exception("Failed to update tenant tier")
        return TierUpdateResponse(updated=False, error=str(e))


@router.get("/billing-information")
async def billing_information(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> BillingInformation | SubscriptionStatusResponse:
    logger.info("Fetching billing information")
    tenant_id = get_current_tenant_id()
    return fetch_billing_information(tenant_id)


@router.post("/seats/update")
async def update_seats(
    request: SeatUpdateRequest,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> SeatUpdateResponse:
    """Cloud alias for /admin/billing/seats/update (ENG-3533 migration)."""
    return await _admin_update_seats(request, user, db_session)


@router.post("/create-customer-portal-session")
async def create_customer_portal_session(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> dict:
    """Create a Stripe customer portal session via the control plane."""
    tenant_id = get_current_tenant_id()
    return_url = f"{WEB_DOMAIN}/admin/billing"

    try:
        portal_url = fetch_customer_portal_session(tenant_id, return_url)
        return {"stripe_customer_portal_url": portal_url}
    except OrbyteError:
        raise
    except Exception:
        logger.exception("Failed to create customer portal session")
        raise OrbyteError(
            OrbyteErrorCode.INTERNAL_ERROR,
            "Failed to create customer portal session",
        )


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest | None = None,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> dict:
    """Create a Stripe checkout session via the control plane."""
    tenant_id = get_current_tenant_id()
    billing_period = request.billing_period if request else "monthly"
    seats = request.seats if request else None

    try:
        result = fetch_stripe_checkout_session(tenant_id, billing_period, seats)
        return {"stripe_checkout_url": result.url}
    except OrbyteError:
        raise
    except Exception:
        logger.exception("Failed to create checkout session")
        raise OrbyteError(
            OrbyteErrorCode.INTERNAL_ERROR,
            "Failed to create checkout session",
        )


@router.post("/create-subscription-session")
async def create_subscription_session(
    request: CreateSubscriptionSessionRequest | None = None,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> SubscriptionSessionResponse:
    try:
        tenant_id = CURRENT_TENANT_ID_CONTEXTVAR.get()
        if not tenant_id:
            raise OrbyteError(OrbyteErrorCode.VALIDATION_ERROR, "Tenant ID not found")

        billing_period = request.billing_period if request else "monthly"
        result = fetch_stripe_checkout_session(tenant_id, billing_period)
        return SubscriptionSessionResponse(
            sessionId=result.session_id,
            url=result.url,
            requires_payment_method_update=result.requires_payment_method_update,
        )

    except OrbyteError:
        raise
    except Exception:
        logger.exception("Failed to create subscription session")
        raise OrbyteError(
            OrbyteErrorCode.INTERNAL_ERROR,
            "Failed to create subscription session",
        )


@router.get("/stripe-publishable-key")
async def get_stripe_publishable_key() -> StripePublishableKeyResponse:
    """
    Fetch the Stripe publishable key.
    Priority: env var override (for testing) > S3 bucket (production).
    This endpoint is public (no auth required) since publishable keys are safe to expose.
    The key is cached in memory to avoid hitting S3 on every request.
    """
    global _stripe_publishable_key_cache

    # Fast path: return cached value without lock
    if _stripe_publishable_key_cache:
        return StripePublishableKeyResponse(
            publishable_key=_stripe_publishable_key_cache
        )

    # Use lock to prevent concurrent S3 requests
    async with _stripe_key_lock:
        # Double-check after acquiring lock (another request may have populated cache)
        if _stripe_publishable_key_cache:
            return StripePublishableKeyResponse(
                publishable_key=_stripe_publishable_key_cache
            )

        # Check for env var override first (for local testing with pk_test_* keys)
        if STRIPE_PUBLISHABLE_KEY_OVERRIDE:
            key = STRIPE_PUBLISHABLE_KEY_OVERRIDE.strip()
            if not key.startswith("pk_"):
                raise OrbyteError(
                    OrbyteErrorCode.INTERNAL_ERROR,
                    "Invalid Stripe publishable key format",
                )
            _stripe_publishable_key_cache = key
            return StripePublishableKeyResponse(publishable_key=key)

        # Fall back to S3 bucket
        if not STRIPE_PUBLISHABLE_KEY_URL:
            raise OrbyteError(
                OrbyteErrorCode.INTERNAL_ERROR,
                "Stripe publishable key is not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(STRIPE_PUBLISHABLE_KEY_URL)
                response.raise_for_status()
                key = response.text.strip()

                # Validate key format
                if not key.startswith("pk_"):
                    raise OrbyteError(
                        OrbyteErrorCode.INTERNAL_ERROR,
                        "Invalid Stripe publishable key format",
                    )

                _stripe_publishable_key_cache = key
                return StripePublishableKeyResponse(publishable_key=key)
        except httpx.HTTPError:
            raise OrbyteError(
                OrbyteErrorCode.INTERNAL_ERROR,
                "Failed to fetch Stripe publishable key",
            )
