/** API helpers for group join links. */

import { SWR_KEYS } from "@/lib/swr-keys";

export interface JoinLinkSnapshot {
  id: number;
  is_reusable: boolean;
  use_count: number;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface JoinLinkCreateResponse {
  id: number;
  token: string;
  is_reusable: boolean;
  expires_at: string | null;
}

async function createJoinLink(
  groupId: number,
  isReusable: boolean,
  expiresInHours: number | null
): Promise<JoinLinkCreateResponse> {
  const res = await fetch(SWR_KEYS.groupJoinLinks(groupId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      is_reusable: isReusable,
      expires_in_hours: expiresInHours,
    }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(
      detail?.detail ?? `Failed to create join link: ${res.statusText}`
    );
  }
  return res.json();
}

async function revokeJoinLink(groupId: number, linkId: number): Promise<void> {
  const res = await fetch(`${SWR_KEYS.groupJoinLinks(groupId)}/${linkId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(
      detail?.detail ?? `Failed to revoke join link: ${res.statusText}`
    );
  }
}

export { createJoinLink, revokeJoinLink };
