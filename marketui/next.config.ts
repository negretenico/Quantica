import type { NextConfig } from "next";

const output = process.env.NEXT_OUTPUT === "standalone" ? "standalone" : "export";

const nextConfig: NextConfig = {
  output,
  basePath: output === "export" ? process.env.NEXT_PUBLIC_BASE_PATH || "" : "",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
