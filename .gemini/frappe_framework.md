## Frappe LMS – Coding Rules & Instructions

### 1. Core Mental Model

- The system uses the **Frappe Framework**.  
- Frappe **apps** (including this LMS) live in the app repo; **sites** (data, files, config) live under the bench `sites/` directory.  
- Treat this repo as the **LMS app codebase**, not as the entire Frappe installation.

When you need framework details, prefer these Context7 IDs:

- `/websites/frappe_io-framework-user-en` – User manual (how to use Frappe features)  
- `/websites/frappe_io-framework` – Official framework docs  
- `/websites/frappe_io_framework` – Technical/architecture docs  
- `/frappe/frappe` – Frappe core repo & code reference  
- `/websites/frappe_io` – General Frappe apps documentation  

Official site: `https://frappeframework.com/docs`.

Also see .gemini/frappe_framework.md for more Frappe specific rules 

### 2. Do Not Break These Invariants

1. **Do NOT modify Frappe core** (`frappe` app) unless explicitly asked and unavoidable.  
2. **Do NOT rename or delete core DocTypes or their critical fields** that belong to Frappe LMS or Frappe itself.  
   - Prefer adding new fields, child tables, or related DocTypes.  
3. **Do NOT move, rename, or restructure site directories**:
   - `sites/`  
   - `sites/<site_name>/public/files`  
   - `sites/<site_name>/private/files`  
4. Avoid changing global bench configuration or process management (supervisor, nginx, etc.) unless explicitly requested.

If a change would alter any of the above, stop and explain the risk instead of applying it.

### 3. Where to Put Custom Code

- Put new LMS behaviour in **this LMS app** (or in a separate app if the user requests that), not in Frappe core.  
- For new features (AI tools, neurodiversity adaptations, UX changes), prefer:
  - New Python modules under the app (e.g. `lms/neuro/`, `lms/api/ai_helpers.py`).  
  - New DocTypes or extensions of existing DocTypes (via custom fields / child tables).  
  - New front‑end components/pages inside the app’s front‑end structure.

When you need patterns or examples for custom apps and hooks, consult:

- `/websites/frappe_io-framework-user-en`  
- `/websites/frappe_io-framework`  
- `/websites/frappe_io_framework`  
- `/frappe/frappe`

### 4. Extension Patterns to Prefer

When extending behaviour:

- Use Frappe’s **extension mechanisms** instead of editing existing logic inline, where possible:
  - Hooks (`doc_events`, `override_whitelisted_methods`, etc.).  
  - Server Scripts and whitelisted methods for custom server logic.  
  - Custom fields and Customize Form for light schema changes.  
- Only consider monkey‑patching or overriding core functions as a **last resort**, and isolate those changes clearly.

Before implementing a pattern, look for recommended approaches in:

- `/websites/frappe_io-framework-user-en`  
- `/websites/frappe_io_framework`  
- `/frappe/frappe`

### 5. LMS‑Specific Behaviour

- Reuse existing LMS DocTypes for courses, lessons, quizzes, and enrolments when adding features (e.g. AI assistance, accessibility metadata).  
- Attach additional data to these structures instead of inventing parallel, disconnected DocTypes unless there is a clear design reason.  
- For analytics, tracking, or adaptive behaviour, store metadata cleanly and avoid opaque JSON blobs where a structured DocType would work better.

### 6. Front‑End & UX Guidance

- The Frappe “Desk” UI is primarily for admin/author workflows.  
- For learner‑facing experiences:
  - You may add custom pages/views inside the LMS app, **or**  
  - Build a separate front‑end that talks to the LMS via Frappe’s REST APIs, if a radically different UX is desired.
- When working on Desk pages, follow the existing patterns used in this LMS app and Frappe docs.

### 7. Git & Branching Expectations

- Assume this repo is a **fork** used for local experimentation.  
- Make changes on feature branches rather than directly on `main`/`develop` unless instructed otherwise.  
- Do not introduce hard‑coded paths or credentials tied to a specific local machine; use configuration patterns recommended in the Frappe docs.

### 8. When Unsure

If a task touches:

- Core Frappe behaviour,  
- Multi‑tenant/site handling, or  
- File storage/layout under `sites/`,

then:

1. First, consult the appropriate documentation via the Context7 sources above.  
2. Prefer a minimal, reversible change.  
3. If multiple approaches exist, choose the one that:
   - Keeps Frappe and LMS upgradable,  
   - Minimises coupling to internals,  
   - And uses documented extension points.

