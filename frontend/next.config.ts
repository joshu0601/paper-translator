import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Let other devices on the LAN use the dev server (http://192.168.x.x:3000).
  // Without this Next.js blocks its dev assets for non-localhost hosts and the
  // page never hydrates there. Each `*` matches one hostname label.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.*.*.*", "*.local"],
};

export default nextConfig;
