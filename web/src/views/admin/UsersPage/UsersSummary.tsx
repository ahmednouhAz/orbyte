import { SvgFilterPlus } from "@opal/icons";
import { Hoverable } from "@opal/core";
import { Section } from "@/layouts/general-layouts";
import Card from "@/refresh-components/cards/Card";
import IconButton from "@/refresh-components/buttons/IconButton";
import Text from "@/refresh-components/texts/Text";
import { useAuthTypeMetadata } from "@/lib/auth/hooks";
import { AuthType } from "@/lib/auth/types";
import InviteOnlyCard from "./InviteOnlyCard";

// ---------------------------------------------------------------------------
// Stats cell — number + label + hover filter icon
// ---------------------------------------------------------------------------

type StatCellProps = {
  value: number | null;
  label: string;
  onFilter?: () => void;
};

function StatCell({ value, label, onFilter }: StatCellProps) {
  const display = value === null ? "\u2014" : value.toLocaleString();

  return (
    <Hoverable.Root group="stat" width="full">
      <div
        className={`relative flex flex-col items-start gap-0.5 w-full p-2 rounded-08 transition-colors ${
          onFilter ? "cursor-pointer hover:bg-background-tint-02" : ""
        }`}
        onClick={onFilter}
      >
        <Text as="span" mainUiAction text04>
          {display}
        </Text>
        <Text as="span" secondaryBody text03>
          {label}
        </Text>
        {onFilter && (
          <div className="absolute right-1 top-1">
            <Hoverable.Item group="stat" variant="appear-on-hover">
              <IconButton
                tertiary
                icon={SvgFilterPlus}
                tooltip="Add Filter"
                toolTipPosition="left"
                onClick={(e) => {
                  e.stopPropagation();
                  onFilter();
                }}
              />
            </Hoverable.Item>
          </div>
        )}
      </div>
    </Hoverable.Root>
  );
}

// ---------------------------------------------------------------------------
// Stats bar — layout varies by invite-only status
// ---------------------------------------------------------------------------

type UsersSummaryProps = {
  activeUsers: number | null;
  pendingInvites: number | null;
  requests: number | null;
  onFilterActive?: () => void;
  onFilterInvites?: () => void;
  onFilterRequests?: () => void;
};

export default function UsersSummary({
  activeUsers,
  pendingInvites,
  requests,
  onFilterActive,
  onFilterInvites,
  onFilterRequests,
}: UsersSummaryProps) {
  const { authTypeMetadata } = useAuthTypeMetadata();
  const showInviteOnly = authTypeMetadata?.authType === AuthType.BASIC;
  const showRequests = requests !== null && requests > 0;

  const statsCard = (
    <Card padding={0.5}>
      <Section flexDirection="row" gap={0}>
        <StatCell
          value={activeUsers}
          label="active users"
          onFilter={onFilterActive}
        />
        <StatCell
          value={pendingInvites}
          label="pending invites"
          onFilter={onFilterInvites}
        />
        {showRequests && (
          <StatCell
            value={requests}
            label="requests to join"
            onFilter={onFilterRequests}
          />
        )}
      </Section>
    </Card>
  );

  const rightCard = showInviteOnly ? <InviteOnlyCard /> : null;

  if (rightCard) {
    return (
      <Section
        flexDirection="row"
        justifyContent="start"
        alignItems="stretch"
        gap={0.5}
      >
        {statsCard}
        {rightCard}
      </Section>
    );
  }

  return statsCard;
}
