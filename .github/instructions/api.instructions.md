# GitHub Copilot Guide for Node.js API Orchestrator

```yaml
applyTo: '**'
```

---

## 📉 Project Context

This Node.js service lives under `apps/api/` in the monorepo and acts as the **only public-facing API**. It does **not run any AI logic** directly. Instead, it securely delegates all AI-related tasks to the local Python backend (`apps/ai/`).

It is responsible for:

- Receiving requests from the frontend
- Authenticating and securing all endpoints
- Forwarding requests to the Python AI engine via `http://localhost:8001`
- Streaming responses back to the client
- Enforcing API rate limits or auth middleware (if needed)
- Logging, tracing, and metrics

---

## ⚖️ Stack

- Node.js (TypeScript)
- Express or Fastify
- PostgreSQL (for pgvector, accessed via Python only)
- Axios or native `fetch()` for calling Python services
- Optional: WebSocket or SSE support for streaming

---

## ✅ Coding Guidelines for Copilot & Contributors

### General Rules
- Keep logic stateless and request-driven
- API should only coordinate, not process AI logic
- Forward full user input (text, image, audio flag) to Python `/message`
- Stream output from Python directly to frontend
- Sanitize inputs and secure routes

### File Naming Convention
- `routes/` - HTTP route definitions (e.g. `message.ts`)
- `services/` - Python call logic (e.g. `aiClient.ts`)
- `lib/` - Common helpers (e.g. `validate.ts`, `logger.ts`)
- `types/` - Shared TypeScript interfaces

### Testing
- Unit test all middleware and route-level logic
- Mock Python calls in integration tests
- Don’t test AI logic here — that’s handled in `/apps/ai`

### Code Style
- Use `eslint` + `prettier`
- Type-safe with strict `tsconfig`
- `async/await` only — no raw promises or callbacks

---

## 🤖 Copilot Prompt Patterns

### Message Forwarding
```ts
// Forward message to Python AI service via /message
```

### Streaming Response
```ts
// Pipe streamed response from Python to frontend using fetch or Axios
```

### API Security
```ts
// Validate user input and enforce authentication token
```

---

## 📂 Folder Layout

```bash
apps/api/
├── src/
│   ├── routes/
│   ├── services/
│   ├── lib/
│   ├── types/
│   └── main.ts
├── package.json
├── tsconfig.json
└── README.md
```

---

## 🚀 Goal

Enable GitHub Copilot (and contributors) to generate secure, well-structured orchestration logic for a Node.js API that delegates all AI decisions to a local Python service.

