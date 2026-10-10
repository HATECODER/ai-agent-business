import assert from "node:assert/strict";
import test from "node:test";

import type { SessionData } from "@auth0/nextjs-auth0/types";
import type { RedisClientType } from "redis";

import { RedisSessionStore } from "./redis-session-store.ts";


class FakeMulti {
  private readonly redis: FakeRedis;
  constructor(redis: FakeRedis) { this.redis = redis; }
  set(key: string, value: string, options: { EX: number }) { this.redis.operations.push(() => this.redis.set(key, value, options)); return this; }
  sAdd(key: string, value: string) { this.redis.operations.push(() => this.redis.sAdd(key, value)); return this; }
  sRem(key: string, value: string) { this.redis.operations.push(() => this.redis.sRem(key, value)); return this; }
  expire(key: string, seconds: number) { this.redis.operations.push(() => this.redis.expire(key, seconds)); return this; }
  del(key: string) { this.redis.operations.push(() => this.redis.del(key)); return this; }
  async exec() { const queued = this.redis.operations.splice(0); for (const operation of queued) await operation(); return []; }
}

class FakeRedis {
  isReady = true;
  values = new Map<string, string>();
  sets = new Map<string, Set<string>>();
  expiries = new Map<string, number>();
  operations: Array<() => Promise<unknown>> = [];
  on() { return this; }
  async connect() { this.isReady = true; return this; }
  async get(key: string) { return this.values.get(key) ?? null; }
  async set(key: string, value: string, options: { EX: number }) { this.values.set(key, value); this.expiries.set(key, options.EX); return "OK"; }
  async exists(key: string) { return this.values.has(key) ? 1 : 0; }
  async sAdd(key: string, value: string) { const values = this.sets.get(key) ?? new Set<string>(); values.add(value); this.sets.set(key, values); return 1; }
  async sRem(key: string, value: string) { return this.sets.get(key)?.delete(value) ? 1 : 0; }
  async sMembers(key: string) { return [...(this.sets.get(key) ?? [])]; }
  async expire(key: string, seconds: number) { this.expiries.set(key, seconds); return true; }
  async del(key: string) { return this.values.delete(key) ? 1 : 0; }
  multi() { return new FakeMulti(this); }
}

function session(subject = "auth0|owner", sid = "provider-session"): SessionData {
  return {
    user: { sub: subject },
    tokenSet: { accessToken: "sensitive-access-token", expiresAt: 2_000_000_000 },
    internal: { sid, createdAt: Math.floor(Date.now() / 1000) },
  };
}

function store(redis: FakeRedis) {
  return new RedisSessionStore(
    redis as unknown as RedisClientType,
    Buffer.from("11".repeat(32), "hex"),
    "https://tenant.auth0.com/",
  );
}

test("sessions are encrypted at rest and receive the bounded TTL", async () => {
  const redis = new FakeRedis();
  const sessions = store(redis);
  await sessions.set("browser-session", session());
  assert.equal(redis.values.size, 1);
  const encrypted = [...redis.values.values()][0];
  assert.equal(encrypted.includes("sensitive-access-token"), false);
  assert.deepEqual(await sessions.get("browser-session"), session());
  assert.equal([...redis.expiries.values()].every((ttl) => ttl === 8 * 60 * 60), true);
});

test("update is conditional and delete removes the stored session", async () => {
  const redis = new FakeRedis();
  const sessions = store(redis);
  assert.equal(await sessions.update("missing", session()), false);
  await sessions.set("browser-session", session());
  assert.equal(await sessions.update("browser-session", session("auth0|owner", "new-sid")), true);
  await sessions.delete("browser-session");
  assert.equal(await sessions.get("browser-session"), null);
});

test("verified logout claims delete only matching issuer sessions", async () => {
  const redis = new FakeRedis();
  const sessions = store(redis);
  await sessions.set("one", session("auth0|owner", "sid-one"));
  await sessions.deleteByLogoutToken({ iss: "https://other.auth0.com/", sub: "auth0|owner" });
  assert.notEqual(await sessions.get("one"), null);
  await sessions.deleteByLogoutToken({ iss: "https://tenant.auth0.com/", sid: "sid-one" });
  assert.equal(await sessions.get("one"), null);
});

test("subject logout deletes all sessions for that configured issuer", async () => {
  const redis = new FakeRedis();
  const sessions = store(redis);
  await sessions.set("one", session("auth0|owner", "sid-one"));
  await sessions.set("two", session("auth0|owner", "sid-two"));
  await sessions.set("three", session("auth0|other", "sid-three"));
  await sessions.deleteByLogoutToken({ sub: "auth0|owner" });
  assert.equal(await sessions.get("one"), null);
  assert.equal(await sessions.get("two"), null);
  assert.notEqual(await sessions.get("three"), null);
});
