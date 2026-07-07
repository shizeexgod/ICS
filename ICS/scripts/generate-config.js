/**
 * Генерирует js/config.js из переменной окружения ICS_API_BASE.
 * На Vercel: Project Settings -> Environment Variables -> ICS_API_BASE.
 * Локально: ICS_API_BASE=http://localhost:8000 npm run build
 */
const fs = require("fs");
const path = require("path");

const apiBase = (process.env.ICS_API_BASE || "").trim().replace(/\/$/, "");
const isVercel = Boolean(process.env.VERCEL);

// Локально без env — localhost. На Vercel без env — пусто (напоминание настроить переменную).
const resolved = apiBase || (isVercel ? "" : "http://localhost:8000");
const outPath = path.join(__dirname, "..", "js", "config.js");
const content = `// Auto-generated — do not edit. Set ICS_API_BASE in Vercel / .env.local
window.ICS_API_BASE = ${JSON.stringify(resolved)};
`;

fs.writeFileSync(outPath, content, "utf8");
console.log(`Wrote ${outPath} (ICS_API_BASE=${resolved || "(empty — set env on Vercel!)"})`);
