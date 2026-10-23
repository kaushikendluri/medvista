const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname),
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // @cornerstonejs/dicom-image-loader's WASM codec glue (Emscripten
      // output) is isomorphic and references Node's `fs`/`path` behind a
      // runtime `typeof window === 'undefined'` guard for a Node fallback
      // path we never execute in the browser. Webpack still statically
      // resolves the `require(...)` regardless of the guard, so these
      // built-ins must be stubbed out for the client bundle.
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        crypto: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
// @cornerstonejs/dicom-image-loader's WASM codec glue (Emscripten
// output) is isomorphic and references Node's `fs`/`path` behind a
// runtime `typeof window === 'undefined'` guard for a Node fallback
// path we never execute in the browser. Webpack still statically
// resolves the `require(...)` regardless of the guard, so these
// built-ins must be stubbed out for the client bundle.