// Run-plan Worker: serves the static app from ./public and a small JSON API.
//
//   GET  /api/health                → { ok, sharedChat, inviteRequired }
//   POST /api/user                  → create a user, returns { code }
//   GET  /api/user/:code            → { code, name, profile, log, updated_at }
//   PUT  /api/user/:code            → save { name, profile, log }
//   POST /api/chat                  → { code, system, messages } → Gemini with the server key
//   GET  /api/coach                 → all users (Authorization: Bearer <COACH_PASSWORD>)
//
// Bindings / settings (wrangler.toml + dashboard secrets):
//   DB                  D1 database
//   GEMINI_API_KEY      secret – shared Gemini key (optional; without it users must bring their own)
//   COACH_PASSWORD      secret – password for /coach (optional; without it the coach view is off)
//   INVITE_CODE         secret/var – optional; if set, new users must enter it
//   DAILY_LIMIT         chat messages per user per day on the shared key (default 40)
//   GLOBAL_DAILY_LIMIT  chat messages per day across everyone on the shared key (default 1000)
//   GEMINI_MODEL        default "gemini-flash-latest"

const ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const CODE_RE = /^[A-HJ-NP-Z2-9]{8}$/;
const MAX_BODY = 300_000;
const FALLBACK_MODELS = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash"];

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
const err = (status, message) => json({ error: message }, status);

let schemaReady = false;
async function ensureSchema(db) {
  if (schemaReady) return;
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS users (code TEXT PRIMARY KEY, name TEXT, profile TEXT, log TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)`),
    db.prepare(`CREATE TABLE IF NOT EXISTS usage (code TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (code, day))`),
  ]);
  schemaReady = true;
}

function newCode() {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return Array.from(bytes, (b) => ALPHABET[b % ALPHABET.length]).join("");
}
const normCode = (c) => String(c || "").toUpperCase().replace(/[^A-Z0-9]/g, "");

async function readJson(request) {
  const text = await request.text();
  if (text.length > MAX_BODY) throw Object.assign(new Error("payload too large"), { status: 413 });
  try { return text ? JSON.parse(text) : {}; }
  catch { throw Object.assign(new Error("invalid JSON"), { status: 400 }); }
}

function safeEqual(a, b) {
  a = String(a || ""); b = String(b || "");
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}

async function bumpUsage(db, code, day) {
  const row = await db
    .prepare(`INSERT INTO usage (code, day, count) VALUES (?1, ?2, 1)
              ON CONFLICT(code, day) DO UPDATE SET count = count + 1 RETURNING count`)
    .bind(code, day).first();
  return row ? row.count : 1;
}

async function callGemini(env, system, messages, apiKey) {
  const models = env.GEMINI_MODEL ? [env.GEMINI_MODEL, ...FALLBACK_MODELS.filter((m) => m !== env.GEMINI_MODEL)] : FALLBACK_MODELS;
  let last = { status: 502, message: "no model answered" };
  for (const model of models) {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents: messages.map((m) => ({ role: m.role === "user" ? "user" : "model", parts: [{ text: String(m.content) }] })),
      }),
    });
    let j = {};
    try { j = await r.json(); } catch {}
    if (r.ok) {
      const text = j.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "(אין תשובה)";
      return { text, model };
    }
    last = { status: r.status, message: j?.error?.message || `HTTP ${r.status}` };
    if (r.status === 400 || r.status === 403) last.message = "Google דחה את הבקשה – בדוק שמפתח ה-Gemini נכון ופעיל. (" + last.message + ")";
    if (r.status !== 404) break; // only try the next model when this one doesn't exist
  }
  throw Object.assign(new Error(last.status === 429 ? "Google הגביל זמנית את מספר הבקשות למפתח הזה. נסה שוב בעוד דקה." : last.message), { status: last.status === 429 ? 429 : 502 });
}

async function api(request, env, url) {
  const path = url.pathname.replace(/\/+$/, "");
  const method = request.method;
  const db = env.DB;

  if (path === "/api/health") {
    return json({ ok: true, sharedChat: !!env.GEMINI_API_KEY, inviteRequired: !!env.INVITE_CODE, coach: !!env.COACH_PASSWORD });
  }
  if (!db) return err(500, "D1 binding DB is missing");
  await ensureSchema(db);
  const now = new Date().toISOString();

  // create user
  if (path === "/api/user" && method === "POST") {
    const body = await readJson(request);
    if (env.INVITE_CODE && !safeEqual(String(body.invite || "").trim(), env.INVITE_CODE)) return err(403, "קוד ההזמנה שגוי");
    for (let i = 0; i < 5; i++) {
      const code = newCode();
      const res = await db
        .prepare(`INSERT OR IGNORE INTO users (code, name, profile, log, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?5)`)
        .bind(code, String(body.name || "").slice(0, 60), JSON.stringify(body.profile ?? null), JSON.stringify(body.log ?? {}), now)
        .run();
      if (res.meta.changes === 1) return json({ code, updated_at: now }, 201);
    }
    return err(500, "could not allocate a code");
  }

  // read / save user
  const m = path.match(/^\/api\/user\/([A-Za-z0-9-]+)$/);
  if (m) {
    const code = normCode(m[1]);
    if (!CODE_RE.test(code)) return err(400, "קוד לא תקין");
    if (method === "GET") {
      const row = await db.prepare(`SELECT code, name, profile, log, updated_at FROM users WHERE code = ?1`).bind(code).first();
      if (!row) return err(404, "הקוד לא נמצא");
      return json({ code: row.code, name: row.name, profile: JSON.parse(row.profile || "null"), log: JSON.parse(row.log || "{}"), updated_at: row.updated_at });
    }
    if (method === "PUT") {
      const body = await readJson(request);
      if (body.log && typeof body.log !== "object") return err(400, "log must be an object");
      const res = await db
        .prepare(`UPDATE users SET name = ?2, profile = ?3, log = ?4, updated_at = ?5 WHERE code = ?1`)
        .bind(code, String(body.name || "").slice(0, 60), JSON.stringify(body.profile ?? null), JSON.stringify(body.log ?? {}), now)
        .run();
      if (res.meta.changes !== 1) return err(404, "הקוד לא נמצא");
      return json({ ok: true, updated_at: now });
    }
    return err(405, "method not allowed");
  }

  // chat via the shared key
  if (path === "/api/chat" && method === "POST") {
    // A personal key (header x-gemini-key) is passed through to Google and never stored or counted.
    const userKey = (request.headers.get("x-gemini-key") || "").trim();
    if (!userKey && !env.GEMINI_API_KEY) return err(503, "אין מפתח משותף בשרת – הזן מפתח Gemini אישי בהגדרות.");
    const body = await readJson(request);
    if (userKey) {
      const msgs = Array.isArray(body.messages) ? body.messages.slice(-12) : [];
      if (!msgs.length || msgs[msgs.length - 1].role !== "user") return err(400, "no question");
      return json(await callGemini(env, String(body.system || "").slice(0, 120_000), msgs, userKey));
    }
    const code = normCode(body.code);
    if (!CODE_RE.test(code)) return err(400, "קוד לא תקין");
    const user = await db.prepare(`SELECT code FROM users WHERE code = ?1`).bind(code).first();
    if (!user) return err(403, "משתמש לא מוכר");
    const messages = Array.isArray(body.messages) ? body.messages.slice(-12) : [];
    if (!messages.length || messages[messages.length - 1].role !== "user") return err(400, "no question");
    const system = String(body.system || "").slice(0, 120_000);
    const day = now.slice(0, 10);
    const perUser = Number(env.DAILY_LIMIT || 40), global = Number(env.GLOBAL_DAILY_LIMIT || 1000);
    const [u, g] = await Promise.all([bumpUsage(db, code, day), bumpUsage(db, "*", day)]);
    if (u > perUser) return err(429, `הגעת למכסה היומית (${perUser} שאלות). אפשר להמשיך מחר, או להזין מפתח Gemini אישי בהגדרות.`);
    if (g > global) return err(429, "המכסה היומית המשותפת נגמרה. אפשר להזין מפתח Gemini אישי בהגדרות.");
    const result = await callGemini(env, system, messages, env.GEMINI_API_KEY);
    return json({ ...result, used: u, limit: perUser });
  }

  // coach overview
  if (path === "/api/coach" && method === "GET") {
    if (!env.COACH_PASSWORD) return err(503, "מסך המאמן לא הוגדר (חסר COACH_PASSWORD).");
    const auth = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
    if (!safeEqual(auth, env.COACH_PASSWORD)) return err(401, "סיסמה שגויה");
    const { results } = await db.prepare(`SELECT code, name, profile, log, created_at, updated_at FROM users ORDER BY updated_at DESC LIMIT 500`).all();
    const usage = await db.prepare(`SELECT code, count FROM usage WHERE day = ?1`).bind(now.slice(0, 10)).all();
    const used = Object.fromEntries((usage.results || []).map((r) => [r.code, r.count]));
    return json({
      users: results.map((r) => ({ code: r.code, name: r.name, profile: JSON.parse(r.profile || "null"), log: JSON.parse(r.log || "{}"),
        created_at: r.created_at, updated_at: r.updated_at, chatToday: used[r.code] || 0 })),
      chatTodayTotal: used["*"] || 0,
    });
  }

  return err(404, "not found");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      try { return await api(request, env, url); }
      catch (e) { return err(e.status || 500, e.message || "server error"); }
    }
    if (env.ASSETS) {
      if (url.pathname === "/coach") return env.ASSETS.fetch(new Request(new URL("/coach.html", url), request));
      return env.ASSETS.fetch(request);
    }
    return serveFromGitHub(url, env);
  },
};

// Without a static-assets binding (deployed straight through the API), the pages are read from the
// GitHub repo's public/ folder and cached at the edge – a push to main updates the site within minutes.
const PAGES = { "/": "index.html", "/index.html": "index.html", "/coach": "coach.html", "/coach.html": "coach.html" };
async function serveFromGitHub(url, env) {
  const file = PAGES[url.pathname];
  if (!file) return new Response("not found", { status: 404 });
  const base = env.ASSET_BASE || "https://raw.githubusercontent.com/avishaydmalka/run-plan/main/public/";
  const ttl = Number(env.ASSET_TTL || 60);
  // the minute-bucket query bypasses GitHub's own 5-minute CDN cache, so a push shows up within ~1-2 minutes
  const bucket = Math.floor(Date.now() / (ttl * 1000));
  const r = await fetch(base + file + "?v=" + bucket, { cf: { cacheTtl: ttl, cacheEverything: true } });
  if (!r.ok) return new Response("page unavailable", { status: 502 });
  return new Response(r.body, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-cache",
      "x-content-type-options": "nosniff",
      "referrer-policy": "same-origin",
    },
  });
}
