"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button, CopyButton, Switch } from "@opal/components";
import { toast } from "@opal/layouts";
import { SvgLink, SvgPlusCircle, SvgTrash, SvgKey } from "@opal/icons";
import Modal from "@/refresh-components/Modal";
import Card from "@/refresh-components/cards/Card";
import IconButton from "@/refresh-components/buttons/IconButton";
import Text from "@/refresh-components/texts/Text";
import SimpleCollapsible from "@/refresh-components/SimpleCollapsible";
import { Section } from "@/layouts/general-layouts";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { SWR_KEYS } from "@/lib/swr-keys";
import {
  createJoinLink,
  revokeJoinLink,
  type JoinLinkCreateResponse,
  type JoinLinkSnapshot,
} from "./joinLinkSvc";

const EXPIRY_OPTIONS: { label: string; hours: number | null }[] = [
  { label: "Never", hours: null },
  { label: "24 hours", hours: 24 },
  { label: "7 days", hours: 24 * 7 },
  { label: "30 days", hours: 24 * 30 },
];

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface JoinLinksSectionProps {
  groupId: number;
}

function JoinLinksSection({ groupId }: JoinLinksSectionProps) {
  const {
    data: links,
    isLoading,
    mutate,
  } = useSWR<JoinLinkSnapshot[]>(
    SWR_KEYS.groupJoinLinks(groupId),
    errorHandlingFetcher
  );

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isReusable, setIsReusable] = useState(true);
  const [expiryHours, setExpiryHours] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createdLink, setCreatedLink] = useState<JoinLinkCreateResponse | null>(
    null
  );
  const [revokingId, setRevokingId] = useState<number | null>(null);

  async function handleCreate() {
    setIsCreating(true);
    try {
      const result = await createJoinLink(groupId, isReusable, expiryHours);
      setCreatedLink(result);
      setShowCreateModal(false);
      mutate();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to create join link"
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleRevoke(linkId: number) {
    setRevokingId(linkId);
    try {
      await revokeJoinLink(groupId, linkId);
      mutate();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to revoke join link"
      );
    } finally {
      setRevokingId(null);
    }
  }

  const joinUrl = createdLink
    ? `${window.location.origin}/join/${createdLink.token}`
    : "";

  return (
    <SimpleCollapsible>
      <SimpleCollapsible.Header
        title="Join Links"
        description="Shareable links that let new members self-register directly into this group — no email required."
      />
      <SimpleCollapsible.Content>
        <Card>
          <Section gap={0.5} alignItems="stretch" width="full">
            {!isLoading && (links?.length ?? 0) === 0 && (
              <Text text03 mainUiBody>
                No join links yet.
              </Text>
            )}

            {links?.map((link) => {
              const isRevoked = link.revoked_at !== null;
              return (
                <div
                  key={link.id}
                  className="flex items-center justify-between gap-2"
                >
                  <div className="flex flex-col">
                    <Text
                      mainUiAction
                      text04={!isRevoked}
                      text02={isRevoked}
                    >
                      {link.is_reusable ? "Reusable" : "Single-use"} ·{" "}
                      {link.use_count} use{link.use_count === 1 ? "" : "s"}
                      {isRevoked ? " · Revoked" : ""}
                    </Text>
                    <Text mainUiMuted text03>
                      Expires: {formatDate(link.expires_at)}
                    </Text>
                  </div>
                  {!isRevoked && (
                    <IconButton
                      small
                      icon={SvgTrash}
                      onClick={() => handleRevoke(link.id)}
                      disabled={revokingId === link.id}
                    />
                  )}
                </div>
              );
            })}

            <Button
              icon={SvgPlusCircle}
              prominence="secondary"
              size="md"
              onClick={() => setShowCreateModal(true)}
            >
              Create Join Link
            </Button>
          </Section>
        </Card>
      </SimpleCollapsible.Content>

      {/* Create link modal */}
      <Modal open={showCreateModal}>
        <Modal.Content width="sm">
          <Modal.Header
            icon={SvgLink}
            title="Create Join Link"
            onClose={() => setShowCreateModal(false)}
          />
          <Modal.Body>
            <Section gap={0.75} alignItems="stretch" width="full">
              <div className="flex items-center justify-between">
                <Text text04 mainUiBody>
                  Reusable (unlimited uses until revoked)
                </Text>
                <Switch checked={isReusable} onCheckedChange={setIsReusable} />
              </div>
              <Text text04 mainUiBody>
                Expires
              </Text>
              <div className="flex flex-wrap gap-1">
                {EXPIRY_OPTIONS.map((opt) => (
                  <Button
                    key={opt.label}
                    size="sm"
                    prominence={
                      expiryHours === opt.hours ? "primary" : "secondary"
                    }
                    onClick={() => setExpiryHours(opt.hours)}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </Section>
          </Modal.Body>
          <Modal.Footer>
            <Button
              prominence="primary"
              onClick={handleCreate}
              disabled={isCreating}
            >
              {isCreating ? "Generating..." : "Generate Link"}
            </Button>
          </Modal.Footer>
        </Modal.Content>
      </Modal>

      {/* Reveal-once created link modal */}
      <Modal open={!!createdLink}>
        <Modal.Content width="sm">
          <Modal.Header
            icon={SvgKey}
            title="Join Link Created"
            onClose={() => setCreatedLink(null)}
            description="Copy this link now — it won't be shown again. Share it with the person you want to add to this group."
          />
          <Modal.Body>
            <Card variant="secondary">
              <Section
                flexDirection="row"
                justifyContent="between"
                alignItems="center"
              >
                <Text text03 secondaryMono className="break-all">
                  {joinUrl}
                </Text>
                <CopyButton getCopyText={() => joinUrl} />
              </Section>
            </Card>
          </Modal.Body>
        </Modal.Content>
      </Modal>
    </SimpleCollapsible>
  );
}

export default JoinLinksSection;
