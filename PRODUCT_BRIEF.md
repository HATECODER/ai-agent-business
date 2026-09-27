# AI Business OS — Canonical Product Brief

## Product definition

Build an **AI Business Operating System for Bangladeshi and South Asian SMEs**, starting with commerce. It is not primarily a multi-agent chatbot. The core value is the combination of:

- unified customer, conversation, product, inventory, order, payment, and task data;
- durable Business Memory;
- native Bangla, Banglish, English, code-switching, typo, emoji, and voice understanding;
- safe business actions through validated backend tools;
- Next-Action recommendations with evidence and priority;
- automation across Facebook, WhatsApp, web, and eventually offline/POS channels.

The long-term vision includes specialist capabilities across business intelligence, revenue, growth, operations, finance, and people. Do not implement the vision as roughly 30 independent LLM agents. Begin with five logical agents over a shared business core and tool layer.

## Initial five agents

### 1. Customer & Sales Agent

Combines lead generation, sales, customer service, and upselling.

Responsibilities:

- understand customer intent in Bangla, Banglish, or English;
- identify or create the customer/lead;
- search the real product catalog and check live inventory;
- answer product, availability, price, delivery, and FAQ questions;
- recommend relevant products;
- create a draft lead or order;
- escalate uncertain, sensitive, or exceptional cases.

This is the first production agent.

### 2. Follow-up & Retention Agent

Combines follow-up, retention, re-engagement, abandoned leads, and existing-customer follow-up. It is primarily event-driven: it watches quotations, abandoned conversations/checkouts, inactivity, failed payments, and order outcomes.

V1 flow: recommendation → merchant approval → send. Automatic sending comes later and requires confidence thresholds plus explicit business rules.

### 3. Business Analyst & Problem Detection Agent

Combines business analysis, problem detection, reporting, and insights. Traditional backend code or SQL computes revenue, orders, conversion, average order value, stockouts, and other metrics. The LLM interprets the verified results, explains contributing signals, and communicates them clearly; it must not invent or independently calculate business truth.

### 4. Decision / Next-Action Agent

Uses customer history, conversation state, lead/order/payment status, inventory, prior follow-ups, and business rules to rank recommended actions.

Each recommendation should include:

- entity/customer;
- action;
- priority;
- evidence-based reason;
- recommended time;
- confidence;
- approval requirement;
- optional suggested message.

Architecture: business data → candidate actions → deterministic business rules → AI ranking/explanation → permission/approval → action.

### 5. Business Advisor / AI Employee Agent

The owner's general interface. It composes sales analytics, Next Actions, inventory, customer history, tasks, and reports to answer questions such as “আজকে কী কী করা দরকার?” and execute approved workflows through the shared tool layer.

## Platform capabilities (not separate agents)

### Business Memory

Use four complementary layers:

1. **Structured memory (source of truth):** PostgreSQL records for tenants, users, customers, products, variants, inventory, conversations, messages, leads, orders, order items, payments, complaints, tasks, follow-ups, campaigns, and preferences.
2. **Conversation memory:** channel messages and voice transcripts plus extracted intent, entities, quantity, sentiment/negotiation signals, and links to business records.
3. **Semantic memory:** embeddings for fuzzy recall, initially with pgvector beside relational data.
4. **Derived memory:** inferred preferences and customer traits. Every important derived fact must include its source, timestamp, confidence, and a way to supersede or expire it.

Business Memory must never be reduced to “put all messages in a vector database.”

### Bangla Business AI

Support formal Bangla, colloquial Bangla, Banglish/Romanized Bangla, English, code-switching, local commerce phrasing, typos, emoji, and voice. Build an evaluation dataset before fine-tuning:

- about 500 representative examples for the MVP;
- about 2,000 for a strong internal benchmark;
- 10,000+ real, consented/anonymized interactions as a long-term proprietary evaluation asset.

Examples must label intent, entities, expected tools/arguments, allowed actions, and forbidden actions. Fine-tune only when evaluation demonstrates a persistent failure that prompting, retrieval, tool design, or better data cannot solve.

### Voice → Business Action

Flow: speech-to-text → language/intent understanding → structured command → entity resolution → validation → permission check → explicit confirmation when needed → backend function → audit event.

The LLM never modifies database state directly.

### AI Employee Mode

Provide a unified owner experience for reports, prioritized work, customer follow-ups, inventory warnings, and approved actions. This is orchestration and UI over the agents and tools, not an unconstrained autonomous employee.

## Architecture principles

### Division of responsibility

- **AI handles:** language, intent, classification, reasoning, recommendation, ranking, summarization, personalization, and conversation.
- **Traditional software handles:** authentication, authorization, money, inventory, orders, payment state, database mutations, scheduling, transactions, permissions, calculations, and business constraints.
- **Humans approve:** high-impact, irreversible, financially risky, uncertain, or policy-sensitive actions.

### Shared tool layer

Agents operate through schema-validated tools such as:

- customer lookup/update;
- product search;
- inventory lookup/reservation;
- lead and draft-order creation;
- order/payment lookup;
- follow-up/task creation;
- messaging;
- verified analytics/report retrieval.

Every tool call carries tenant context, authenticated user identity, permissions, validation, idempotency where relevant, and an audit trail.

### Multi-tenancy and security

- Every tenant-owned record is scoped by `tenant_id`.
- Enforce isolation in application queries and preferably PostgreSQL row-level security.
- Treat customer/channel content as untrusted input.
- Put authorization, business rules, risk checks, and optional human approval between an LLM tool request and execution.
- Never let a model declare a payment successful; only verified provider/backend state can do that.

### Events and durable work

Use domain events such as `message.received`, `lead.created`, `quotation.sent`, `order.created`, `order.paid`, `inventory.low`, `customer.inactive`, and `payment.failed`.

Consumers update inventory, CRM, analytics, follow-ups, finance, and reporting independently. Use durable background jobs for scheduled follow-ups, reminders, reports, synchronization, retries, dead-letter handling, and reconciliation. Do not depend on a chat session remaining alive.

Webhook handling must support signature/HMAC verification, idempotency, duplicate delivery, retry, out-of-order events, and reconciliation.

## Human approval policy

Normally safe without approval (subject to tenant policy):

- read availability or order status;
- answer approved FAQs;
- show prior purchases;
- create a draft lead/order;
- create an internal reminder.

Approval required:

- unusual discounts;
- cancellations or refunds;
- price changes;
- bulk campaigns;
- supplier/procurement changes;
- financial transfers;
- consequential HR actions;
- any low-confidence or high-risk mutation.

## MVP scope

### V0 — prove the commerce loop

One merchant workspace with:

- Facebook or web chat (one channel first);
- Customer & Sales Agent;
- Bangla, Banglish, and English;
- Business Memory;
- product catalog and inventory;
- lead management and draft orders;
- merchant-approved follow-ups;
- owner dashboard with recommended Next Actions.

Definition of success: a customer can message naturally, the system identifies/remembers them, checks real product and stock data, answers accurately, saves the lead, schedules a follow-up, and gives the owner an evidence-backed next action.

### V1

- Business Analyst & Problem Detection Agent;
- Decision / Next-Action engine;
- Voice → Action;
- WhatsApp or a second channel;
- reports and AI Employee owner interface.

### V2

- retention and upselling;
- campaigns/marketing automation;
- inventory forecasting;
- payment and courier integrations.

Only after proving these stages should the product expand deeply into operations, finance, HR, recruitment, and employee performance.

## Recommended initial stack

- Frontend: Next.js, TypeScript, Tailwind CSS.
- Backend: Python, FastAPI, Pydantic.
- AI orchestration: OpenAI Agents SDK; consider LangGraph later if durable graph workflows justify it.
- Data: PostgreSQL and pgvector.
- Cache/jobs: Redis and Celery initially.
- Storage: S3-compatible object storage.
- Realtime: WebSocket or Server-Sent Events.
- Operations: Docker, GitHub Actions, and a simple cloud VM/managed service initially.
- Observability: agent/tool traces plus structured audit logs; OpenTelemetry/Prometheus/Grafana later.

Do not introduce Kubernetes for the first MVP without a demonstrated operational need.

## Evaluation and release gates

Maintain evaluation suites for Bangla, Banglish, customer service, sales, lead capture, inventory, follow-up, tool selection/arguments, memory, prompt injection, hallucination, and Next Actions.

Measure at least:

- intent/entity accuracy;
- correct tool and argument selection;
- grounded response accuracy;
- cross-tenant leakage rate (must be zero);
- unsafe/unauthorized action rate;
- follow-up recommendation acceptance and conversion;
- latency, failure rate, and cost per resolved conversation.

No agent receives mutation authority merely because its conversational quality is good.

## Near-term learning/build order

1. Agent engineering, structured outputs, tool calling, guardrails, approvals, tracing, and evaluation.
2. PostgreSQL/data modeling, FastAPI, Redis, multi-tenancy, auth/RBAC, and events.
3. One messaging integration plus webhook reliability.
4. Bangla/Banglish evaluation data and reliability work.
5. SQL analytics and the Next-Action ranking pipeline.
6. Voice commands and the AI Employee experience.

Fine-tuning and Kubernetes are later priorities.

