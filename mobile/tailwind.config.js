// Semantic colors map to `var(--name)`, resolved/flipped at runtime by the vars() provider in _layout.tsx.
const sharedTheme = require("@orbyte-ai/shared/nativewind-theme");
const typographyUtilities = require("@orbyte-ai/shared/nativewind-typography");
const plugin = require("tailwindcss/plugin");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: { extend: sharedTheme },
  plugins: [
    plugin(({ addUtilities }) => {
      addUtilities(typographyUtilities);
    }),
  ],
};
