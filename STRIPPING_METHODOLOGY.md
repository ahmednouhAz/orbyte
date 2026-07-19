# Onyx Codebase Safe Stripping Methodology

**Goal:** Strip down the Onyx codebase to its core features (Chat, File/Basic Connectors, RAG, Access-controls) while minimizing token usage and ensuring 0% risk of breaking the core architecture.

**Rule of Thumb:** We prune from the "outside-in". We start with Configs, move to the UI, cleanly sever isolated backend leaf-nodes (Tools/Connectors), and finally clean up the Docker infrastructure. We do **not** write Alembic schema downgrade migrations.

---

## Phase 1: Configuration Lock-down (The Safety Net)
*Instead of deleting code immediately, we hardcode environment variables and Python constants to definitively turn off background listeners and enterprise features.*

- [x] **Task 1.1:** Modify `backend/onyx/configs/app_configs.py`
  - Hardcode `AUTH_TYPE` to Basic (email/password).
  - Disable Slack bot, Discord bot, and MCP flags.
  - Disable image generation and voice/audio toggles.
- [x] **Task 1.2:** Modify Celery Beat Schedules
  - Stop tasks related to unused enterprise syncs or analytics.
- **🧪 VALIDATION TEST 1:** 
  - `docker compose down && docker compose up -d --build api_server web_server`
  - Open UI. Ensure backend boots and `http://localhost:8080/health` returns OK. (PASSED)

---

## Phase 2: Frontend / UI Pruning
*We remove the buttons and pages for features we disabled in Phase 1. If a user can't click it, it essentially doesn't exist.*

- [x] **Task 2.1:** Clean the Admin Sidebar (`web/src/sections/sidebar/AdminSidebar.tsx`)
  - Removed Service Accounts, Query History, and OpenAPI Actions from `buildItems()`. Routes/pages/components left intact, just unreachable from the UI.
- [ ] **Task 2.2:** Clean the Add Connectors View (`web/src/app/admin/connectors/page.tsx`)
  - Hide the icons/links for the 45 connectors we will delete.
- [ ] **Task 2.3:** Clean the Chat Interface
  - Remove the UI toggles for Tools like "Deep Research" or "Draw Image".
- **🧪 VALIDATION TEST 2:** 
  - Restart frontend container.
  - Navigate through the Admin Panel. Verify no React `undefined` crashes from missing components.

---

## Phase 3: AI Tools Disconnection (Backend Leaf Nodes)
*We do NOT delete the files. We simply untie them from the Engine so the LLM cannot use them.*

- [ ] **Task 3.1:** Unregister the Tools
  - Edit `backend/onyx/tools/tool_constructor.py` and `constants.py`.
  - Remove all tools except `Search` and `WebSearch` from the active arrays/dropdowns.
- **🧪 VALIDATION TEST 3:** 
  - Restart API container.
  - Start a chat. Ask a question. Ensure the agent defaults to normal `Search`.

---

## Phase 4: Connectors Disconnection (The Big Prune)
*We do NOT delete the 45 integrations. We just hide them from the Engine to save loading/sync memory.*

- [ ] **Task 4.1:** Unregister Connectors
  - Modify `DocumentSource` Enum in `backend/onyx/configs/constants.py` to only expose: `file`, `web`, `google_drive`, `confluence`, `slack`.
  - Disable their routing endpoints if necessary in `backend/onyx/server/manage/connector.py`.
- **🧪 VALIDATION TEST 4:**
  - Restart API container.
  - Go to "Add Connector" UI page. Ensure only the target connectors appear.
  - Perform a manual file upload (PDF/Word) via the UI.
  - *Success criteria:* File chunks successfully, goes through RAG pipeline, and can be queried in chat.

---

## Phase 5: Infrastructure Polish
*Now that Python code points no longer need them, we delete Docker containers to save PC memory.*

- [ ] **Task 5.1:** Update `docker-compose.yml`
  - Delete `code-interpreter` service (Python execution container).
  - Delete `mcp_server` service.
  - Validate MinIO and cache requirements based on final architecture.
- **🧪 VALIDATION TEST 5 (FINAL END-TO-END):**
  - Run `docker compose down -v` to wipe all previous state.
  - Run `docker compose up -d --build`.
  - Create admin user account.
  - Upload a test document. Ask a RAG question. Verify citations work.

---
*Created per request. We are currently at: **Waiting to start Phase 1**.*
