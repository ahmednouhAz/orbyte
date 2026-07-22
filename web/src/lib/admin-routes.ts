import { IconFunctionComponent } from "@opal/types";
import {
  SvgActivity,
  SvgBarChart,
  SvgBookOpen,
  SvgBubbleText,
  SvgClipboard,
  SvgCpu,
  SvgDevKit,
  SvgDownload,
  SvgEmpty,
  SvgFileText,
  SvgFiles,
  SvgGlobe,
  SvgHistory,
  SvgOrbyteOctagon,
  SvgPlug,
  SvgProgressBars,
  SvgSearchMenu,
  SvgShield,
  SvgTerminal,
  SvgThumbsUp,
  SvgUploadCloud,
  SvgUser,
  SvgUserCheck,
  SvgUserKey,
  SvgUsers,
  SvgZoomIn,
  SvgDiscord,
  SvgSlack,
} from "@opal/icons";

export interface AdminRouteEntry {
  path: string;
  icon: IconFunctionComponent;
  title: string;
  sidebarLabel: string;
}

/**
 * Single source of truth for every admin route: path, icon, page-header
 * title, and sidebar label.
 */
export const ADMIN_ROUTES = {
  INDEXING_STATUS: {
    path: "/admin/indexing/status",
    icon: SvgBookOpen,
    title: "Existing Connectors",
    sidebarLabel: "Existing Connectors",
  },
  ADD_CONNECTOR: {
    path: "/admin/add-connector",
    icon: SvgUploadCloud,
    title: "Add Connector",
    sidebarLabel: "Add Connector",
  },
  DOCUMENT_SETS: {
    path: "/admin/documents/sets",
    icon: SvgFiles,
    title: "Document Sets",
    sidebarLabel: "Document Sets",
  },
  DOCUMENT_EXPLORER: {
    path: "/admin/documents/explorer",
    icon: SvgZoomIn,
    title: "Document Explorer",
    sidebarLabel: "Explorer",
  },
  DOCUMENT_FEEDBACK: {
    path: "/admin/documents/feedback",
    icon: SvgThumbsUp,
    title: "Document Feedback",
    sidebarLabel: "Feedback",
  },
  AGENTS: {
    path: "/admin/agents",
    icon: SvgOrbyteOctagon,
    title: "Agents",
    sidebarLabel: "Agents",
  },
  SLACK_BOTS: {
    path: "/admin/bots",
    icon: SvgSlack,
    title: "Slack Integration",
    sidebarLabel: "Slack Integration",
  },
  DISCORD_BOTS: {
    path: "/admin/discord-bot",
    icon: SvgDiscord,
    title: "Discord Integration",
    sidebarLabel: "Discord Integration",
  },
  STANDARD_ANSWERS: {
    path: "/admin/standard-answer",
    icon: SvgClipboard,
    title: "Standard Answers",
    sidebarLabel: "Standard Answers",
  },
  GROUPS: {
    path: "/admin/groups",
    icon: SvgUsers,
    title: "Manage User Groups",
    sidebarLabel: "Groups",
  },
  CHAT_PREFERENCES: {
    path: "/admin/configuration/chat-preferences",
    icon: SvgBubbleText,
    title: "Chat Preferences",
    sidebarLabel: "Chat Preferences",
  },
  LLM_MODELS: {
    path: "/admin/configuration/language-models",
    icon: SvgCpu,
    title: "Language Models",
    sidebarLabel: "Language Models",
  },
  WEB_SEARCH: {
    path: "/admin/configuration/web-search",
    icon: SvgGlobe,
    title: "Web Search",
    sidebarLabel: "Web Search",
  },
  CODE_INTERPRETER: {
    path: "/admin/configuration/code-interpreter",
    icon: SvgTerminal,
    title: "Code Interpreter",
    sidebarLabel: "Code Interpreter",
  },
  CRAFT_ACCESS: {
    path: "/admin/craft/access",
    icon: SvgUserCheck,
    title: "Access",
    sidebarLabel: "Access",
  },
  CRAFT_APPS: {
    path: "/admin/craft/apps",
    icon: SvgPlug,
    title: "Apps",
    sidebarLabel: "Apps",
  },
  CRAFT_INSTRUCTIONS: {
    path: "/admin/craft/instructions",
    icon: SvgDevKit,
    title: "Instructions",
    sidebarLabel: "Instructions",
  },
  INDEX_SETTINGS: {
    path: "/admin/configuration/index-settings",
    icon: SvgSearchMenu,
    title: "Index Settings",
    sidebarLabel: "Index Settings",
  },
  DOCUMENT_PROCESSING: {
    path: "/admin/configuration/document-processing",
    icon: SvgFileText,
    title: "Document Processing",
    sidebarLabel: "Document Processing",
  },
  USERS: {
    path: "/admin/users",
    icon: SvgUser,
    title: "Users & Requests",
    sidebarLabel: "Users",
  },
  TOKEN_RATE_LIMITS: {
    path: "/admin/token-rate-limits",
    icon: SvgProgressBars,
    title: "Spending Limits",
    sidebarLabel: "Spending Limits",
  },
  TRACING: {
    path: "/admin/tracing",
    icon: SvgBarChart,
    title: "Tracing",
    sidebarLabel: "Tracing",
  },
  USAGE: {
    path: "/admin/performance/usage",
    icon: SvgActivity,
    title: "Usage Statistics",
    sidebarLabel: "Usage Statistics",
  },
  QUERY_HISTORY: {
    path: "/admin/performance/query-history",
    icon: SvgHistory,
    title: "Query History",
    sidebarLabel: "Query History",
  },
  OAUTH_TEST: {
    path: "/admin/oauth-test",
    icon: SvgUserKey,
    title: "OAuth Test",
    sidebarLabel: "OAuth Test",
  },
  DEBUG: {
    path: "/admin/debug",
    icon: SvgDownload,
    title: "Debug Logs",
    sidebarLabel: "Debug Logs",
  },
  SECURITY_HARDENING: {
    path: "/admin/security",
    icon: SvgShield,
    title: "Security & Hardening",
    sidebarLabel: "Security & Hardening",
  },
  // Prefix-only entries used for layout matching — not rendered as sidebar
  // items or page headers.
  DOCUMENTS: {
    path: "/admin/documents",
    icon: SvgEmpty,
    title: "",
    sidebarLabel: "",
  },
  PERFORMANCE: {
    path: "/admin/performance",
    icon: SvgEmpty,
    title: "",
    sidebarLabel: "",
  },
} as const satisfies Record<string, AdminRouteEntry>;

/**
 * Helper that converts a route entry into the `{ name, icon, link }`
 * shape expected by the sidebar.
 */
export function sidebarItem(route: AdminRouteEntry) {
  return { name: route.sidebarLabel, icon: route.icon, link: route.path };
}

/**
 * Connector/indexing admin route prefixes that need a vector DB. In Lite mode
 * these render an informational notice instead of their normal content.
 */
export const VECTOR_DB_REQUIRED_ROUTE_PREFIXES: readonly string[] = [
  ADMIN_ROUTES.INDEXING_STATUS.path,
  ADMIN_ROUTES.ADD_CONNECTOR.path,
  // Covers /sets, /explorer, and /feedback — all require a vector DB.
  ADMIN_ROUTES.DOCUMENTS.path,
  ADMIN_ROUTES.INDEX_SETTINGS.path,
  "/admin/connector",
  "/admin/federated",
];

export function isVectorDbRequiredRoute(pathname: string): boolean {
  return VECTOR_DB_REQUIRED_ROUTE_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix)
  );
}
