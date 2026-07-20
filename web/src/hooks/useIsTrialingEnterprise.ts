"use client";

/**
 * True when the current tenant is on a Business subscription but is being
 * shown Enterprise features for the duration of their trial.
 *
 * Billing has been removed from this deployment, so there is no trial
 * concept anymore — always returns false.
 */
export function useIsTrialingEnterprise(): boolean {
  return false;
}
