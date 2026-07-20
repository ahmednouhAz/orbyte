/**
 * Returns whether the current tenant has an active paid subscription on cloud.
 *
 * Billing has been removed from this deployment (self-hosted only), so
 * there is no billing gate — always returns true.
 */
export function useCloudSubscription(): boolean {
  return true;
}
