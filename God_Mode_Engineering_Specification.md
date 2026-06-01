# AURA GOD MODE: Complete Engineering Specification

*A comprehensive system design document for evolving AURA into an autonomous AI Operator.*

---

## PART 1: CORE ARCHITECTURE DESIGNS

### 1. Multi-Agent Architecture Design
AURA will utilize a **Hierarchical Supervisor Agent** model.
- **Supervisor (Planner):** Receives the user goal, maintains the global state machine (Task Queue), and delegates sub-tasks to specialized worker agents.
- **Workers (Coder, Terminal, Vision, Researcher):** Narrowly scoped agents that only understand their specific domain. They execute tasks and return results (Success, Failure, or Output) back to the Supervisor.
- **Communication:** Agents do not call each other directly. They emit `AgentEvent` payloads to the `EventBus`. The Supervisor subscribes to these events to monitor progress.

### 2. Planner Design
- **State Machine:** Uses a ReAct (Reason + Act) loop. State is tracked via a JSON object containing `goal`, `completed_steps`, `current_step`, `failed_attempts`, and `context`.
- **Logic:** Prompted to emit JSON specifying `{"thought": "...", "action": {"tool": "...", "args": {...}}}`.
- **Error Recovery:** If a worker fails 3 times on the same step, the Planner triggers a `fallback_strategy` or asks the user for help.

### 3. Tool Calling Design
- **Registry:** Leverages the existing `ActionRegistry`. Each Python action script exposes a JSON Schema defining its inputs.
- **Execution:** When the Planner outputs a tool call, the `ActionDispatcher` parses the arguments, executes the physical Python function, and returns the string output (e.g., terminal stdout or browser status) back into the Planner's context window.

### 4. Vision Architecture
- **Capture:** `mss` (already implemented) captures the screen.
- **Perception:** Base64 JPEGs are sent to Groq's multimodal LLaMA or GPT-4o.
- **Grounding (Future):** The VLM will be prompted to return `[x, y]` bounding box coordinates for UI elements (like "Submit Button") so the Computer-Use agent knows exactly where to click.

### 5. Computer-Use Architecture
- **Actuation:** Uses `pyautogui` for cross-platform mouse/keyboard control.
- **Safety:** Implements a strict `FAILSAFE=True` (moving mouse to the corner of the screen aborts the agent).
- **Workflow:** Vision Agent identifies coordinates -> Computer-Use Agent moves cursor smoothly -> Performs click/type -> Vision Agent verifies screen changed.

### 6. Memory Architecture
- **Vector DB:** Uses `ChromaDB` running locally.
- **Semantic Chunking:** Documents, terminal outputs, and chat histories are chunked (500 tokens) and embedded using a fast local model like `all-MiniLM-L6-v2`.
- **Retrieval:** The Planner automatically performs a similarity search against the user's goal before creating a plan, ensuring past context (like preferred file paths or previous bugs) is injected into the prompt.

### 7. Coding Agent Architecture
- **Capabilities:** Can read directories, read files, write files, and apply diffs (regex search/replace).
- **Verification:** After writing code, it always delegates to the Terminal Agent to run syntax checks (e.g., `python -m py_compile`) or tests before reporting success to the Planner.

### 8. Terminal Agent Architecture
- **Execution:** Uses `subprocess.Popen` with non-blocking stdout/stderr reading.
- **Statefulness:** Maintains a persistent background shell session so environment variables and working directories (`cd`) persist across commands.
- **Safety:** Wraps execution in a timeout (e.g., 60 seconds) to prevent infinite hanging. Filters dangerous commands like `rm -rf /` or formatting disks.

### 9. Research Agent Architecture
- **Workflow:** Uses `browser_control.py` coupled with a headless scraper (like `Playwright` or `BeautifulSoup`).
- **Synthesis:** Downloads raw HTML, converts to Markdown, chunks it, and uses a cheap LLM to extract relevance before passing the final summary back to the Planner.

---

## PART 2: PHASE-BY-PHASE ENGINEERING SPECIFICATION

### Phase 1: The "Eyes" (Vision Integration)
1. **Purpose:** Give AURA the ability to perceive the GUI visually.
2. **Architecture:** Synchronous capture -> Base64 Encode -> VLM API Request.
3. **Folder Structure:** `/vision/screen_capture.py`, `/vision/vlm_client.py`.
4. **Components:** `mss` screenshot utility, `Groq` VLM Client.
5. **EventBus events:** `vision.capture_requested`, `vision.analysis_complete`.
6. **Data flow:** IntentEngine requests vision -> screen_capture grabs image -> vlm_client analyzes -> Result spoken to user.
7. **Database changes:** None.
8. **Dependencies:** `mss`, `Pillow`, `groq`.
9. **Security considerations:** Screenshots may contain sensitive passwords or PII. Images are sent only to trusted LLM APIs and never stored to disk permanently.
10. **Failure handling:** Network timeouts fallback to "I couldn't analyze the screen due to a network error."
11. **Example user workflows:** "What error is on my screen right now?"
12. **Integration:** Plugs directly into `actions/vision_control.py`.

### Phase 2: The "Brain" (Planner & ReAct Loop)
1. **Purpose:** Replace single-shot intent routing with a multi-step Planner capable of holding state.
2. **Architecture:** `while not task_complete:` loop that queries the LLM, executes the requested tool, and appends the result to the message history.
3. **Folder Structure:** `/agents/planner.py`, `/agents/base_agent.py`.
4. **Components:** ReAct Orchestrator, Tool Registry synchronizer, State Manager.
5. **EventBus events:** `agent.plan.started`, `agent.step.executed`, `agent.plan.completed`.
6. **Data flow:** User Goal -> Planner Context -> LLM Tool Request -> ActionDispatcher -> Tool Result -> Planner Context.
7. **Database changes:** Add `active_plans` table to SQLite to recover plans if the app crashes mid-execution.
8. **Dependencies:** `pydantic` for strict JSON schema enforcement.
9. **Security considerations:** Infinite loops. Must implement a `max_iterations=15` hard stop.
10. **Failure handling:** If a tool fails, the error string is fed back to the LLM so it can try an alternative approach.
11. **Example user workflows:** "Analyze this folder, find the python scripts, and summarize them."
12. **Integration:** Replaces `brain/llm_intent_brain.py` as the primary fallback when `FastRuleMatcher` misses.

### Phase 3: The "Hands" (Computer Control)
1. **Purpose:** Allow autonomous manipulation of the OS GUI.
2. **Architecture:** Coordinate mapping from Vision Agent translated into X/Y screen manipulations.
3. **Folder Structure:** `/actions/computer_use.py`.
4. **Components:** Mouse Controller, Keyboard Controller.
5. **EventBus events:** `system.mouse.moved`, `system.keyboard.typed`.
6. **Data flow:** Planner requests `click_element(name)` -> Vision finds coordinates -> Computer-Use executes `pyautogui.click(x,y)`.
7. **Database changes:** None.
8. **Dependencies:** `pyautogui`.
9. **Security considerations:** The agent could accidentally click "Delete" or "Send" on sensitive data. Requires user supervision or a physical kill-switch shortcut (e.g., `CTRL+ALT+ESC`).
10. **Failure handling:** Screen resolution changes or multi-monitor setups handled gracefully by recalculating relative bounding boxes.
11. **Example user workflows:** "Save this document and close the window."
12. **Integration:** Registered as tools in the `ActionRegistry`.

### Phase 4: The "Developer" (Coding & Terminal)
1. **Purpose:** Autonomous software engineering and OS-level file manipulation.
2. **Architecture:** Sandboxed `subprocess` shell manager and File I/O manager.
3. **Folder Structure:** `/agents/coder.py`, `/agents/terminal.py`.
4. **Components:** Persistent Shell Session, Diff Applier, Git Manager.
5. **EventBus events:** `terminal.command.executing`, `file.modified`.
6. **Data flow:** Planner delegates coding task -> Coder writes `main.py` -> Coder asks Terminal to run `python main.py` -> Terminal returns Traceback -> Coder fixes bug.
7. **Database changes:** None.
8. **Dependencies:** `subprocess`, standard lib `os`, `shutil`.
9. **Security considerations:** High risk. Terminal agent must run in a restricted user mode or prompt the user via PySide6 GUI (`ConfirmationService`) before executing `pip install` or `git push`.
10. **Failure handling:** Commands that hang (e.g., starting a web server) must be detached or timed out so they don't block the agent loop.
11. **Example user workflows:** "Create a React app called Portfolio, install Tailwind, and start the dev server."
12. **Integration:** The Coder agent operates entirely independently but reports status back to the Planner via EventBus.

### Phase 5: The "Hippocampus" (Long-Term Memory)
1. **Purpose:** Give AURA persistent, cross-session semantic knowledge.
2. **Architecture:** Local Vector Database sitting parallel to the existing SQLite DB.
3. **Folder Structure:** `/memory/vector_store.py`, `/memory/embeddings.py`.
4. **Components:** ChromaDB Client, SentenceTransformers.
5. **EventBus events:** `memory.stored`, `memory.retrieved`.
6. **Data flow:** After task completion -> Planner summarizes task -> Summary is embedded and saved. On new task -> Planner queries DB -> Similar past tasks injected into prompt.
7. **Database changes:** New `ChromaDB` local persistence directory created in app root.
8. **Dependencies:** `chromadb`, `sentence-transformers` or `fastembed`.
9. **Security considerations:** Vectorizing sensitive local files. Ensure a `.auraignore` file exists so users can block specific directories from being memorized.
10. **Failure handling:** If the VectorDB corrupts, it can be wiped; the agent will just lose long-term context but maintain core functionality.
11. **Example user workflows:** "Fix this bug. Remember how we solved the API routing issue last week? Do it like that."
12. **Integration:** Wraps around the existing `context_memory.py` module to augment the LLM's system prompt before reasoning begins.
