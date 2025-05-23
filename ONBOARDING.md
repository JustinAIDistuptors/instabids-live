# InstaBids Live Project Onboarding

Welcome to the `instabids-live` project! This document provides an overview to help you (and your AI assistant, Cascade) navigate and develop this application.

## 1. Project Goal

InstaBids aims to be a multi-agent system connecting homeowners with contractors, facilitating the process of getting bids for home improvement projects. This `instabids-live` project is built upon the Google Agent Development Kit (ADK) `agent-starter-pack`.

## 2. Core Technologies

*   **Google Agent Development Kit (ADK):** Version 1.0.0 (installed from GitHub main branch for latest features).
*   **AI Models:** Google Gemini models (e.g., `gemini-2.0-pro` for the HomeownerAgent, with plans to explore live/multimodal models like `gemini-2.5-flash-preview-native-audio-dialog`).
*   **Web Framework:** FastAPI (used by ADK).
*   **Dependency Management:** Poetry.
*   **Planned Data Layer:** Supabase (for session management, facts, bid cards).
*   **Agent-to-Agent (A2A) Communication:** Using ADK's A2A protocol.

## 3. Project Structure (`instabids-live`)

```
instabids-live/
├── .git/                     # Git repository files
├── .github/                  # GitHub specific workflows, issue templates etc.
├── docs/                     # Project documentation
├── src/                      # Main source code
│   ├── agents/               # ADK Agent modules
│   │   ├── __init__.py       # Makes 'agents' a package
│   │   └── homeowner/        # Example: Homeowner agent
│   │       ├── __init__.py   # Makes 'homeowner' a package, exports root_agent
│   │       ├── agent.py      # HomeownerAgent class definition & root_agent instance
│   │       └── instruction.py# Instructions for the HomeownerAgent
│   ├── cli/                  # Command-line interface components (from starter-pack)
│   ├── frontends/            # Frontend components (from starter-pack)
│   └── utils/                # Utility scripts (from starter-pack)
├── tests/                    # Unit and integration tests
├── .gitignore
├── Makefile                  # Build/test automation tasks
├── README.md                 # Main project README (from agent-starter-pack)
├── poetry.lock
├── pyproject.toml            # Poetry project configuration and dependencies
├── uv.lock                   # uv lock file (alternative by starter-pack)
└── ONBOARDING.md             # This file!
```

## 4. Key Files & Roles

*   `pyproject.toml`: Defines project metadata, dependencies (managed by Poetry), and tool configurations.
*   `src/agents/<agent_name>/agent.py`: Contains the main `Agent` class definition and an instance (e.g., `root_agent`).
*   `src/agents/<agent_name>/instruction.py`: Contains the natural language instructions for the agent.
*   `src/agents/<agent_name>/__init__.py`: Makes the agent directory a Python package and exports `root_agent`.

## 5. Running the ADK Web Server

From the root of the `instabids-live` project (`c:\Users\Not John Or Justin\Documents\GitHub\instabids-live`):

```bash
poetry run adk web src/agents --port 8079
```
*   The ADK Development UI should be at `http://localhost:8079`.

## 6. Environment Variables

*   Manage API keys (`GOOGLE_API_KEY`) via environment variables.
*   The `agent-starter-pack` may use a `.env` file (check project root or `src/` for an example).

## 7. Best Practices for Working with Cascade

*   **Specify Full Paths:** Always provide full absolute paths for file operations.
*   **Research First:** Enforce the "Research-First Protocol" (memory `e82ea7a8-5559-4d52-848d-190e9b8259d7`) for errors/new features.
*   **Iterative Debugging:** When the server runs, check browser UI first. If issues, ask Cascade to check server logs (`command_status`), then review agent files (`view_file`).
*   **Clarify Ambiguity:** Ask for clarification if Cascade's plans are unclear or seem to be moving too fast.
*   **Workspace Sync:** Keep your IDE focused on the `instabids-live` project directory to avoid confusion.

## 8. Original `agent-starter-pack`

Refer to its original `README.md` for general information about the starter pack's features and structure.

---
This document will evolve as the project progresses.
