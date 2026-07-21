"use client";

import { MCPServersResponse } from "@/lib/tools/interfaces";

/**
 * MCP (Model Context Protocol) server support was removed from the backend.
 * This stub keeps the return shape stable for existing consumers (which
 * already treat an empty server list as a normal state) without hitting a
 * route that no longer exists.
 */
export default function useMcpServers() {
  return {
    mcpData: null as MCPServersResponse | null,
    isLoading: false,
    error: undefined,
    mutateMcpServers: () => {},
  };
}
