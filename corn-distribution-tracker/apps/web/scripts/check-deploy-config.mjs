import { readFileSync } from "node:fs";

const configUrl = new URL("../vercel.json", import.meta.url);
const config = readFileSync(configUrl, "utf8");

if (process.env.VERCEL && config.includes("your-service.up.railway.app")) {
  console.error(
    "apps/web/vercel.json still points at the Railway placeholder. " +
      "Replace it with the real API origin before deploying.",
  );
  process.exit(1);
}
