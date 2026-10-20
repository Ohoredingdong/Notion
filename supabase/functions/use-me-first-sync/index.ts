import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const concurrency = "updated_at-v1";
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-sync-code",
  "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: cors });
const stringArray = (value: unknown) => Array.isArray(value) && value.every(x => typeof x === "string" && x.trim());
function validPayload(payload: any) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload) || ![undefined, 1, 2].includes(payload.version)) return false;
  if (!["season", "pantry", "customSeason", "customPantry"].every(k => stringArray(payload[k]))) return false;
  if (!Array.isArray(payload.items) || !payload.items.every((x: any) => x && typeof x === "object" && typeof x.name === "string" && x.name.trim())) return false;
  if (payload.version !== 2) return true;
  return payload.items.every((x: any) => typeof x.id === "string" && x.id && typeof x.expiry === "string" && typeof x.quantity === "string") &&
    stringArray(payload.favorites) && Array.isArray(payload.meals) && payload.meals.every((x: any) => x &&
      typeof x.id === "string" && x.id && typeof x.name === "string" && x.name.trim() &&
      typeof x.ts === "number" && Number.isFinite(x.ts) && x.ts > 0 && !Number.isNaN(new Date(x.ts).getTime()) &&
      typeof x.day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(x.day));
}
async function hashCode(code: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(code.trim()));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (!["GET", "PUT"].includes(req.method)) return json({ error: "method_not_allowed" }, 405);
  const code = req.headers.get("x-sync-code")?.trim() || "";
  if (code.length < 20 || code.length > 120) return json({ error: "invalid_sync_code" }, 400);
  const supabaseUrl = Deno.env.get("SUPABASE_URL"), serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceRole) return json({ error: "configuration_unavailable" }, 503);
  const supabase = createClient(supabaseUrl, serviceRole, { auth: { persistSession: false } });
  const syncHash = await hashCode(code);

  if (req.method === "GET") {
    const { data, error } = await supabase.from("use_me_first_sync").select("payload, updated_at").eq("sync_hash", syncHash).maybeSingle();
    if (error) return json({ error: "read_failed" }, 500);
    return json({ payload: data?.payload ?? null, updated_at: data?.updated_at ?? null, concurrency });
  }

  let body: any;
  try { body = await req.json(); } catch { return json({ error: "invalid_json" }, 400); }
  const payload = body?.payload;
  if (!validPayload(payload)) return json({ error: "invalid_payload" }, 400);
  if (new TextEncoder().encode(JSON.stringify(payload)).length > 200000) return json({ error: "payload_too_large" }, 413);
  const supplied = Object.prototype.hasOwnProperty.call(body, "expected_updated_at"), expected = body.expected_updated_at;
  if (supplied && expected !== null && (typeof expected !== "string" || !/^\d{4}-\d{2}-\d{2}T/.test(expected) || !Number.isFinite(Date.parse(expected)))) {
    return json({ error: "invalid_expected_updated_at" }, 400);
  }

  // A missing expectation is accepted only for a brand-new code. Existing legacy
  // clients must reload; allowing their old unconditional upsert would defeat CAS.
  if (!supplied || expected === null) {
    const updatedAt = new Date().toISOString();
    const { data, error } = await supabase.from("use_me_first_sync").insert({ sync_hash: syncHash, payload, updated_at: updatedAt }).select("updated_at").maybeSingle();
    if (error?.code === "23505") return json({ error: supplied ? "conflict" : "reload_required", concurrency }, supplied ? 409 : 428);
    if (error || !data) return json({ error: "write_failed" }, 500);
    return json({ ok: true, updated_at: data.updated_at, concurrency });
  }

  // One conditional SQL UPDATE: PostgreSQL rechecks the timestamp predicate when
  // another update wins the row lock. The losing client receives a conflict.
  const updatedAt = new Date(Math.max(Date.now(), Date.parse(expected) + 1)).toISOString();
  const { data, error } = await supabase.from("use_me_first_sync")
    .update({ payload, updated_at: updatedAt })
    .eq("sync_hash", syncHash).eq("updated_at", expected).select("updated_at").maybeSingle();
  if (error) return json({ error: "write_failed" }, 500);
  if (!data) return json({ error: "conflict", concurrency }, 409);
  return json({ ok: true, updated_at: data.updated_at, concurrency });
});
