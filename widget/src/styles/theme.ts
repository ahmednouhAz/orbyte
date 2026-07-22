import { css } from "lit";
import { colors } from "./colors";

/**
 * Orbyte Design System - Theme
 * Typography, spacing, and layout tokens from Figma
 */
export const theme = css`
  ${colors}

  :host {
    /* Typography - Hanken Grotesk */
    --orbyte-font-family:
      "Hanken Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI",
      sans-serif;
    --orbyte-font-family-mono: "DM Mono", "Monaco", "Menlo", monospace;

    /* Font Sizes */
    --orbyte-font-size-small: 10px;
    --orbyte-font-size-secondary: 12px;
    --orbyte-font-size-sm: 13px;
    --orbyte-font-size-main: 14px;
    --orbyte-font-size-label: 16px;

    /* Line Heights */
    --orbyte-line-height-small: 12px;
    --orbyte-line-height-secondary: 16px;
    --orbyte-line-height-main: 20px;
    --orbyte-line-height-label: 24px;
    --orbyte-line-height-section: 28px;
    --orbyte-line-height-headline: 36px;

    /* Font Weights */
    --orbyte-weight-regular: 400;
    --orbyte-weight-medium: 500;
    --orbyte-weight-semibold: 600;

    /* Content Heights */
    --orbyte-height-content-secondary: 12px;
    --orbyte-height-content-main: 16px;
    --orbyte-height-content-label: 18px;
    --orbyte-height-content-section: 24px;

    /* Border Radius - from Figma */
    --orbyte-radius-04: 4px;
    --orbyte-radius-08: 8px;
    --orbyte-radius-12: 12px;
    --orbyte-radius-16: 16px;
    --orbyte-radius-round: 1000px;

    /* Spacing - Block */
    --orbyte-space-block-1x: 4px;
    --orbyte-space-block-2x: 8px;
    --orbyte-space-block-3x: 12px;
    --orbyte-space-block-4x: 16px;
    --orbyte-space-block-6x: 24px;

    /* Spacing - Inline */
    --orbyte-space-inline-0: 0px;
    --orbyte-space-inline-0_5x: 2px;
    --orbyte-space-inline-1x: 4px;

    /* Legacy spacing aliases (for compatibility) */
    --orbyte-space-2xs: var(--orbyte-space-block-1x);
    --orbyte-space-xs: var(--orbyte-space-block-2x);
    --orbyte-space-sm: var(--orbyte-space-block-3x);
    --orbyte-space-md: var(--orbyte-space-block-4x);
    --orbyte-space-lg: var(--orbyte-space-block-6x);

    /* Padding */
    --orbyte-padding-icon-0: 0px;
    --orbyte-padding-icon-0_5x: 2px;
    --orbyte-padding-text-0_5x: 2px;
    --orbyte-padding-text-1x: 4px;

    /* Icon Weights (stroke-width) */
    --orbyte-icon-weight-secondary: 1px;
    --orbyte-icon-weight-main: 1.5px;
    --orbyte-icon-weight-section: 2px;

    /* Z-index */
    --orbyte-z-launcher: 9999;
    --orbyte-z-widget: 10000;

    /* Transitions */
    --orbyte-transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --orbyte-transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  * {
    box-sizing: border-box;
  }
`;
