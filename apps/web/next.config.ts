import type { NextConfig } from "next";

const isGitHubPages = process.env.GITHUB_PAGES === "true";

const config: NextConfig = {
  transpilePackages: ["@travel-universe/viewer"],
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  ...(isGitHubPages ? { basePath: "/Travel-universe" } : {}),
};

export default config;
