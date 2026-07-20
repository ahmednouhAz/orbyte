"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useSettings } from "@/lib/settings/hooks";
import { SidebarLayouts, useSidebarState } from "@opal/layouts";
import { useUser } from "@/providers/UserProvider";
import { UserRole } from "@/lib/types";
import { Settings, Tier } from "@/lib/settings/types";
import { Divider, InputTypeIn, SidebarTab } from "@opal/components";
import { SvgSearch, SvgX } from "@opal/icons";
import { ADMIN_ROUTES, sidebarItem } from "@/lib/admin-routes";
import { NEXT_PUBLIC_CLOUD_ENABLED } from "@/lib/constants";
import useFilter from "@/hooks/useFilter";
import { IconFunctionComponent } from "@opal/types";
import AccountPopover from "@/sections/sidebar/AccountPopover";
import { renderSidebarLogo } from "@/lib/sidebar/utils";
import { useShowLogoWhenFolded } from "@/lib/sidebar/hooks";
import { markdown } from "@opal/utils";

const SECTIONS = {
  UNLABELED: null,
  CRAFT: "Craft",
  AGENTS_AND_ACTIONS: "Agents & Actions",
  DOCUMENTS_AND_KNOWLEDGE: "Documents & Knowledge",
  INTEGRATIONS: "Integrations",
  PERMISSIONS: "Permissions",
  ORGANIZATION: "Organization",
  USAGE: "Usage",
} as const;

interface SidebarItemEntry {
  section: string | null;
  name: string;
  icon: IconFunctionComponent;
  link: string;
  error?: boolean;
  disabled?: boolean;
  requiredTier?: Tier;
}

function buildItems(
  isCurator: boolean,
  enableCloud: boolean,
  tier: Tier | undefined,
  settings: Settings | null
): SidebarItemEntry[] {
  const items: SidebarItemEntry[] = [];

  const add = (
    section: string | null,
    route: Parameters<typeof sidebarItem>[0]
  ) => {
    items.push({ ...sidebarItem(route), section });
  };

  // 1. Core Configuration (unlabeled, admin only)
  if (!isCurator) {
    add(SECTIONS.UNLABELED, ADMIN_ROUTES.LLM_MODELS);
    add(SECTIONS.UNLABELED, ADMIN_ROUTES.WEB_SEARCH);
    add(SECTIONS.UNLABELED, ADMIN_ROUTES.CHAT_PREFERENCES);
  }

  // 2. Agents & Actions
  add(SECTIONS.AGENTS_AND_ACTIONS, ADMIN_ROUTES.AGENTS);
  // OpenAPI Actions: disconnected from UI per STRIPPING_METHODOLOGY.md Phase 2.

  // 3. Documents & Knowledge
  add(SECTIONS.DOCUMENTS_AND_KNOWLEDGE, ADMIN_ROUTES.INDEXING_STATUS);
  add(SECTIONS.DOCUMENTS_AND_KNOWLEDGE, ADMIN_ROUTES.ADD_CONNECTOR);
  add(SECTIONS.DOCUMENTS_AND_KNOWLEDGE, ADMIN_ROUTES.DOCUMENT_SETS);
  if (!isCurator) {
    items.push({
      ...sidebarItem(ADMIN_ROUTES.INDEX_SETTINGS),
      section: SECTIONS.DOCUMENTS_AND_KNOWLEDGE,
      error: settings?.needs_reindexing,
    });
  }

  // 4. Integrations (admin only)
  // Service Accounts: disconnected from UI per STRIPPING_METHODOLOGY.md Phase 2.

  // 5. Permissions
  if (!isCurator) {
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.USERS);
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.GROUPS);
  } else {
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.GROUPS);
  }

  // 6. Usage: Query History disconnected from UI per STRIPPING_METHODOLOGY.md Phase 2.

  return items;
}

/** Preserve section ordering while grouping consecutive items by section. */
function groupBySection(items: SidebarItemEntry[]) {
  const groups: { section: string | null; items: SidebarItemEntry[] }[] = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.section === item.section) {
      last.items.push(item);
    } else {
      groups.push({ section: item.section, items: [item] });
    }
  }
  return groups;
}

export default function AdminSidebar() {
  const { folded, setFolded } = useSidebarState();
  const showLogoWhenFolded = useShowLogoWhenFolded();
  const searchRef = useRef<HTMLInputElement>(null);
  const [focusSearch, setFocusSearch] = useState(false);

  useEffect(() => {
    if (focusSearch && !folded && searchRef.current) {
      searchRef.current.focus();
      setFocusSearch(false);
    }
  }, [focusSearch, folded]);
  const pathname = usePathname();
  const { user } = useUser();
  const settings = useSettings();
  const tier = settings?.tier;
  const isCurator =
    user?.role === UserRole.CURATOR || user?.role === UserRole.GLOBAL_CURATOR;

  const allItems = buildItems(isCurator, NEXT_PUBLIC_CLOUD_ENABLED, tier, settings);

  const itemExtractor = useCallback((item: SidebarItemEntry) => item.name, []);

  const { query, setQuery, filtered } = useFilter(allItems, itemExtractor);

  const enabled = filtered.filter((item) => !item.disabled);
  const disabled = filtered.filter((item) => item.disabled);
  const enabledGroups = groupBySection(enabled);
  const disabledGroups = groupBySection(disabled);

  return (
    <SidebarLayouts.Root>
      <SidebarLayouts.Header
        renderAppLogo={renderSidebarLogo}
        showLogoWhenFolded={showLogoWhenFolded}
      >
        {folded ? (
          <SidebarTab
            icon={SvgSearch}
            folded
            onClick={() => {
              setFolded(false);
              setFocusSearch(true);
            }}
          >
            Search
          </SidebarTab>
        ) : (
          <InputTypeIn
            ref={searchRef}
            variant="internal"
            searchIcon
            placeholder="Search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            clearButton
          />
        )}
      </SidebarLayouts.Header>

      <SidebarLayouts.Body scrollKey="admin-sidebar">
        {enabledGroups.map((group, groupIndex) => (
          <React.Fragment key={groupIndex}>
            <SidebarLayouts.Section title={group.section ?? undefined}>
              {group.items.map(({ link, icon, name }) => (
                <SidebarTab
                  key={link}
                  icon={icon}
                  href={link}
                  selected={pathname.startsWith(link)}
                >
                  {name}
                </SidebarTab>
              ))}
            </SidebarLayouts.Section>
          </React.Fragment>
        ))}

        {disabledGroups.length > 0 && (
          <>
            <Divider paddingPerpendicular="fit" />
            {/* Empty div here just to add spacing (via the `gap` property on `SidebarLayouts.Body`) */}
            <div />
          </>
        )}
        {disabledGroups.map((group, groupIndex) => (
          <React.Fragment key={`disabled-${groupIndex}`}>
            <SidebarLayouts.Section title={group.section ?? undefined} disabled>
              {group.items.map(({ link, icon, name, requiredTier }) => (
                <SidebarTab
                  key={link}
                  disabled
                  icon={icon}
                  tooltip={markdown(
                    requiredTier === Tier.ENTERPRISE
                      ? "This feature is available on the [Enterprise version of Orbyte](/admin/billing) only."
                      : "This feature is available on the [Business or Enterprise version of Orbyte](/admin/billing) only."
                  )}
                >
                  {name}
                </SidebarTab>
              ))}
            </SidebarLayouts.Section>
          </React.Fragment>
        ))}
      </SidebarLayouts.Body>

      <SidebarLayouts.Footer>
        {!folded && <Divider paddingPerpendicular="sm" />}
        <SidebarTab
          icon={SvgX}
          href={pathname?.startsWith("/admin/craft") ? "/craft/v1" : "/app"}
          variant="sidebar-light"
          folded={folded}
        >
          Exit Admin Panel
        </SidebarTab>
        <AccountPopover folded={folded} />
      </SidebarLayouts.Footer>
    </SidebarLayouts.Root>
  );
}
