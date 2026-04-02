import express from "express";
const app = express();
app.get("/", (_req, res) => res.json({ status: "ok" }));
app.get("/health", (_req, res) => res.json({ healthy: true }));
app.listen(3000, () => console.log("Server running on port 3000"));
