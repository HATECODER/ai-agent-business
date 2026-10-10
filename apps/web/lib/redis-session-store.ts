import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";

import type { LogoutToken, SessionData, SessionDataStore } from "@auth0/nextjs-auth0/types";
import { createClient, type RedisClientType } from "redis";


const SESSION_TTL_SECONDS = 8 * 60 * 60;
const PREFIX = "bizpilot:auth0:v1";

function digest(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function sessionKey(id: string): string {
  return `${PREFIX}:session:${digest(id)}`;
}

function subjectIndexKey(issuer: string, subject: string): string {
  return `${PREFIX}:sub:${digest(`${issuer}\0${subject}`)}`;
}

function sidIndexKey(issuer: string, sid: string): string {
  return `${PREFIX}:sid:${digest(`${issuer}\0${sid}`)}`;
}

function sessionIndexes(issuer: string, session: SessionData): string[] {
  const keys = [subjectIndexKey(issuer, session.user.sub)];
  if (session.internal.sid) keys.push(sidIndexKey(issuer, session.internal.sid));
  return keys;
}

function ttlFor(session: SessionData): number {
  const ceiling = session.internal.sessionExpiresAt;
  if (!ceiling) return SESSION_TTL_SECONDS;
  return Math.max(1, Math.min(SESSION_TTL_SECONDS, ceiling - Math.floor(Date.now() / 1000)));
}

function encryptSession(session: SessionData, key: Buffer): string {
  const nonce = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, nonce);
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(session), "utf8"), cipher.final()]);
  return ["v1", nonce.toString("base64url"), cipher.getAuthTag().toString("base64url"), ciphertext.toString("base64url")].join(".");
}

function decryptSession(payload: string, key: Buffer): SessionData {
  const [version, nonceText, tagText, ciphertextText, extra] = payload.split(".");
  if (version !== "v1" || !nonceText || !tagText || !ciphertextText || extra) throw new Error("Invalid session payload.");
  const decipher = createDecipheriv("aes-256-gcm", key, Buffer.from(nonceText, "base64url"));
  decipher.setAuthTag(Buffer.from(tagText, "base64url"));
  const plaintext = Buffer.concat([
    decipher.update(Buffer.from(ciphertextText, "base64url")),
    decipher.final(),
  ]).toString("utf8");
  const session = JSON.parse(plaintext) as SessionData;
  if (!session?.user?.sub || !session?.internal?.sid || !session?.tokenSet?.accessToken) {
    throw new Error("Invalid session data.");
  }
  return session;
}

export class RedisSessionStore implements SessionDataStore {
  private connectPromise: Promise<unknown> | null = null;
  private readonly client: RedisClientType;
  private readonly encryptionKey: Buffer;
  private readonly issuer: string;

  constructor(
    client: RedisClientType,
    encryptionKey: Buffer,
    issuer: string,
  ) {
    this.client = client;
    this.encryptionKey = encryptionKey;
    this.issuer = issuer;
    if (encryptionKey.length !== 32) throw new Error("Session encryption key must be 32 bytes.");
    client.on("error", () => console.error("Auth session store unavailable."));
  }

  private async ready(): Promise<void> {
    if (this.client.isReady) return;
    this.connectPromise ??= this.client.connect().finally(() => { this.connectPromise = null; });
    await this.connectPromise;
  }

  async get(id: string): Promise<SessionData | null> {
    await this.ready();
    const payload = await this.client.get(sessionKey(id));
    return payload ? decryptSession(payload, this.encryptionKey) : null;
  }

  async set(id: string, session: SessionData): Promise<void> {
    await this.ready();
    const key = sessionKey(id);
    const existingPayload = await this.client.get(key);
    const existing = existingPayload ? decryptSession(existingPayload, this.encryptionKey) : null;
    const ttl = ttlFor(session);
    const transaction = this.client.multi();
    for (const index of existing ? sessionIndexes(this.issuer, existing) : []) transaction.sRem(index, key);
    transaction.set(key, encryptSession(session, this.encryptionKey), { EX: ttl });
    for (const index of sessionIndexes(this.issuer, session)) {
      transaction.sAdd(index, key);
      transaction.expire(index, ttl);
    }
    await transaction.exec();
  }

  async update(id: string, session: SessionData): Promise<boolean> {
    await this.ready();
    if (!(await this.client.exists(sessionKey(id)))) return false;
    await this.set(id, session);
    return true;
  }

  async delete(id: string): Promise<void> {
    await this.ready();
    const key = sessionKey(id);
    const payload = await this.client.get(key);
    if (!payload) return;
    const session = decryptSession(payload, this.encryptionKey);
    const transaction = this.client.multi();
    transaction.del(key);
    for (const index of sessionIndexes(this.issuer, session)) transaction.sRem(index, key);
    await transaction.exec();
  }

  async deleteByLogoutToken(token: LogoutToken): Promise<void> {
    await this.ready();
    if (token.iss && token.iss !== this.issuer) return;
    const indexes = [
      ...(token.sid ? [sidIndexKey(this.issuer, token.sid)] : []),
      ...(token.sub ? [subjectIndexKey(this.issuer, token.sub)] : []),
    ];
    const keys = new Set<string>();
    for (const index of indexes) {
      for (const key of await this.client.sMembers(index)) keys.add(key);
    }
    for (const key of keys) {
      const payload = await this.client.get(key);
      if (!payload) continue;
      const session = decryptSession(payload, this.encryptionKey);
      if (token.sid && session.internal.sid !== token.sid) continue;
      if (token.sub && session.user.sub !== token.sub) continue;
      const transaction = this.client.multi();
      transaction.del(key);
      for (const index of sessionIndexes(this.issuer, session)) transaction.sRem(index, key);
      await transaction.exec();
    }
  }
}

export function createRedisSessionStore(redisUrl: string, encryptionKeyHex: string, issuer: string): RedisSessionStore {
  const client = createClient({ url: redisUrl });
  return new RedisSessionStore(client, Buffer.from(encryptionKeyHex, "hex"), issuer);
}
