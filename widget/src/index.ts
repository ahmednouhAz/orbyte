/**
 * Orbyte Chat Widget - Entry Point
 * Exports the main web component
 */

import { OrbyteChatWidget } from "./widget";

// Define the custom element
if (
  typeof customElements !== "undefined" &&
  !customElements.get("orbyte-chat-widget")
) {
  customElements.define("orbyte-chat-widget", OrbyteChatWidget);
}

// Export for use in other modules
export { OrbyteChatWidget };
export * from "./types/api-types";
export * from "./types/widget-types";
