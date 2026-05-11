import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  turbopack: {
    root: __dirname,
  },
  reactCompiler: true,
  async headers() {
    return [
      {
        source: "/(.*)", // Apply to all routes
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self' https://login.microsoftonline.com *.microsoftonline.com;",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval';",
              "style-src 'self' 'unsafe-inline';",
              "connect-src 'self' http://localhost:3000 http://localhost:8000 https://*.rd-iase-devtest-us6.appserviceenvironment.net https://*.rd-iase-uat-us6.appserviceenvironment.net https://*.rd-iase-prod-us6.appserviceenvironment.net https://login.microsoftonline.com *.microsoftonline.com https://pyxis.gsk.com;",
              "img-src 'self';",
              "form-action 'self' https://login.microsoftonline.com *.microsoftonline.com;",
              "frame-src https://login.microsoftonline.com *.microsoftonline.com;",
              "frame-ancestors 'self' https://gsk.ai https://www.gsk.ai;",
              "object-src 'none';",
              "report-to csp-endpoint;",
            ].join(" "),
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=()",
          },
          {
            key: "X-Powered-By",
            value: "Pyxis, GSK (AIML)",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
