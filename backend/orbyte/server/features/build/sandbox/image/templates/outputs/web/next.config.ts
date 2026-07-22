import type { NextConfig } from "next";

const webappBasePath = process.env.ORBYTE_WEBAPP_BASE_PATH || undefined;
const allowedDevOrigins = (process.env.ORBYTE_WEBAPP_ALLOWED_DEV_ORIGINS || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {};

if (webappBasePath) {
  nextConfig.basePath = webappBasePath;
  nextConfig.assetPrefix = webappBasePath;
}

if (allowedDevOrigins.length > 0) {
  nextConfig.allowedDevOrigins = allowedDevOrigins;
}

export default nextConfig;
