# AntigravityBestFriend (`antigravity-bestfriend`)

> **Native Google Antigravity CLI Plugin & Agentic Runtime Ecosystem**
> Complete semantic port of ClaudeBestFriend / GrokBestFriend into a first-class Google Antigravity CLI (`agy`) native plugin.

---

## 🌟 Key Capabilities

1. **Native Antigravity Integration**: Runs directly on top of `agy` (v1.1.17+) with Google authentication. Zero 9router, zero foreign model gateways.
2. **Native `agy --yolo` Mode**: Execute `agy --yolo` (or `agy -y`) anywhere to immediately launch in full bypass-permissions mode (`--dangerously-skip-permissions`) with all BestFriend skills active.
3. **All 40 Specialized Skills**: Complete preservation of 24 model-routed and 16 manual-only skills with progressive disclosure (no token explosion).
4. **Exactly 4 MCP Servers**: `codebase-memory-mcp` (v0.9.0), `context7` (HTTP documentation), `shadcn` (pinned 4.18.0 UI registry), and `serena` (semantic code intelligence). **Exa is strictly omitted** in favor of native Google search capabilities.
5. **Full Design Ecosystem**: End-to-end integration of Design Bank (`Refero` + `motionsites`), Design Intelligence ranking engine, and UI specialists (`found-this-design`, `impeccable`, `emil-design-eng`, `visual-studio`, `scroll-world`).
6. **Context Guard Lifecycle Hooks**: Native Antigravity lifecycle hook adapter for image budgeting, output reduction, and circuit breaking.
7. **Isolated Chromium CDP**: Headless Chromium runner on `http://127.0.0.1:9223` with isolated sandbox profile (strictly rejecting personal Google Chrome).
8. **Transactional Reliability**: Fail-closed transactional installer with atomic snapshotting, idempotency, backup, and rollback.

---

## 🏗 Architecture & Workflow

```text
                     NATIVE ANTIGRAVITY (`agy`)
                      Google Authentication
                               │
                               ▼
                       Thin Global Router
                       (~/.gemini/GEMINI.md)
                               │
             ┌─────────────────┼──────────────────┐
             │                 │                  │
             ▼                 ▼                  ▼
       Repository          40 Skills            4 MCP
        Evidence          (Lazy Load)        (Lazy Load)
             │                 │                  │
             └─────────────────┼──────────────────┘
                               │
                               ▼
                      Specialist Selection
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
             Coding          Design        Research
                               │
                               ▼
                          Design Bank
                 (~/Downloads/LAB GITHUB/Design)
                               │
                               ▼
                      Design Intelligence
                               │
                               ▼
                       found-this-design
                               │
                               ▼
                           impeccable
                               │
                      ┌────────┴─────────┐
                      ▼                  ▼
                emil-design-eng     UI Implementation
                                         │
                                         ▼
                                  browser verification
                                         │
                                         ▼
                                   Context Guard
                                         │
                                         ▼
                                    Verification
                                         │
                                         ▼
                                Evidence-backed DONE
```

---

## 🚀 Quick Start

### Installation

```bash
# Run transactional installer
./install.sh

# Or test in dry-run mode
./install.sh --dry-run
```

### Verification

```bash
# Run full system health check
agy-bestfriend doctor --strict
```

### Launching `agy` in YOLO mode

```bash
# Direct native YOLO execution
agy --yolo

# With prompt
agy --yolo -p "Implement feature X with TDD"
```

---

## 📦 40 Specialized Skills

### Model-Routed (24 Skills)

| Skill | Purpose |
| :--- | :--- |
| `adhd` | High-impact divergent decisions & trap detection |
| `ask-matt` | Workflow choice and procedural routing |
| `browser-act` | Exploratory browser QA and end-user flows |
| `chrome-devtools-axi` | Deep Chromium CDP diagnostics on port 9223 |
| `codebase-design` | Module interfaces, seams, and abstractions |
| `diagnosing-bugs` | Root-cause diagnosis of complex bugs |
| `domain-modeling` | Ubiquitous language, ADRs, domain glossaries |
| `emil-design-eng` | Microinteractions, motion, animation feel |
| `found-this-design` | Local Design Bank catalog search (`Refero` + `motionsites`) |
| `full-audit-keamanan` | Security auditing (auth, secrets, payments, APIs) |
| `full-performance-audit` | Measured Web Vitals & performance regressions |
| `gh-axi` | GitHub issues, PRs, and Actions automation |
| `grill-with-docs` | Interactive interview & requirement grilling |
| `grilling` | Socratic questioning for design decisions |
| `impeccable` | Design execution, polish, and layout adaptation |
| `matt-code-review` | Two-axis Standards + Spec diff review |
| `prototype` | Rapid throwaway implementation for evidence |
| `research` | Deep codebase & documentation research |
| `scroll-world` | 3D web worlds and cinematic scroll experiences |
| `tdd` | Strict test-first implementation loop |
| `to-spec` | Product & technical specification writer |
| `to-tickets` | Spec ticket decomposition |
| `visual-studio` | Visual media, stills, and creative direction |
| `writing-for-agents` | Authoring AGENTS.md, rules, and skill docs |

### Manual-Only (16 Skills)

`architect`, `arena`, `blast-radius`, `create-verification-skill`, `decision-log`, `figure-it-out`, `improve-codebase-architecture`, `interrogate`, `maintain-verification-skill`, `matt-implement`, `reflect`, `technical-writing`, `unslop`, `wait-what`, `why`, `wizard`.

---

## 🔌 Configured MCP Servers (Exact 4)

1. **`codebase-memory-mcp`**: High-performance repository structure intelligence.
2. **`context7`**: Real-time framework & library documentation provider.
3. **`shadcn`**: Pinned `@4.18.0` UI component registry inspector.
4. **`serena`**: Semantic cross-file symbol & refactoring brain (on-demand).

> *Note: Exa MCP is strictly absent.*

---

## 🛠 Management CLI (`agy-bestfriend`)

```bash
agy-bestfriend doctor [--repair] [--strict]
agy-bestfriend skills list | verify
agy-bestfriend mcp status | add <name> | remove <name>
agy-bestfriend design-bank status | rediscover
agy-bestfriend design-intelligence doctor | search | shortlist
agy-bestfriend serena enable | disable
agy-bestfriend chromium start | status | stop | resolve
agy-bestfriend context-guard status | self-test | cache | prune
agy-bestfriend restore [--list | STAMP]
agy-bestfriend uninstall
```

---

## 🛡 Safety & Rollback

AntigravityBestFriend marks every owned asset with `.gbf-agy-owned.json`. It never mutates user authentication tokens or foreign MCP servers. 

To revert to a previous snapshot at any time:

```bash
./restore.sh
```
