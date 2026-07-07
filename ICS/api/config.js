/** Vercel serverless: отдаёт window.ICS_API_BASE из переменной ICS_API_BASE */
module.exports = (req, res) => {
  const apiBase = (process.env.ICS_API_BASE || "").trim().replace(/\/$/, "");
  res.setHeader("Content-Type", "application/javascript; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=60");
  res.status(200).send(`window.ICS_API_BASE=${JSON.stringify(apiBase)};`);
};
