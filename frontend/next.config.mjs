/** Static export: deploy to Vercel/any static host, or let the FastAPI backend serve `out/`. */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};
export default nextConfig;
