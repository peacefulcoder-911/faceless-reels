# FacelessReels Engineering Roadmap

This roadmap outlines the planned technical milestones for **FacelessReels** as an open-source AI video automation framework.

---

## 🎯 Current Milestone: v1.0 — Open-Source Foundation (Completed)
- [x] Standardize Python packaging with `pyproject.toml` and clean dependencies.
- [x] Establish comprehensive test suite (`pytest`) with 100% offline mocks.
- [x] Integrate `Ruff` linter and formatter.
- [x] Multi-version GitHub Actions CI pipeline (Python 3.10–3.13 + Node 20).
- [x] Complete security remediation (eliminate all hardcoded fallback tokens).
- [x] Open-source documentation suite (`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`).

---

## 🚀 Near-Term Milestone: v1.1 — Modular Provider Integrations
- [ ] **Pluggable LLM Provider Interface**:
  - Abstract script generation behind a unified `ScriptProvider` interface (`GeminiProvider`, `ClaudeProvider`, `OpenAIProvider`, `OllamaProvider` for local LLMs).
- [ ] **Pluggable TTS Architecture**:
  - Modular voice engines (`ElevenLabs`, `Gemini TTS`, `Kokoro-TTS`, `Edge-TTS` for 100% free voiceovers).
- [ ] **Pluggable Visual Synthesis**:
  - Direct local Stable Diffusion / ComfyUI integration alongside cloud image APIs.
- [ ] **Dynamic Subtitle Preview in Browser**:
  - In-browser WebAssembly subtitle renderer to preview word-level karaoke animations before final FFmpeg render.

---

## 🏗️ Medium-Term Milestone: v1.2 — Production Scaling & Orchestration
- [ ] **Job Queue Decoupling**:
  - Option to back `BackgroundTasks` with Redis + Celery or SQLite queue for multi-worker parallel rendering.
- [ ] **Containerization**:
  - Official multi-stage `Dockerfile` with GPU-accelerated FFmpeg (NVENC / QuickSync).
  - `docker-compose.yml` for instant zero-dependency local spinning of backend + frontend.
- [ ] **Enhanced Social Publishing**:
  - Instagram Graph API and TikTok Content Posting API integrations for true cross-platform auto-posting.

---

## 🔮 Long-Term Milestone: v2.0 — Interactive Timeline & Autonomous Agent
- [ ] **Interactive Web Timeline Editor**:
  - Multi-track timeline in the web studio for trimming scene cuts, nudging subtitle start times, and swapping BGM tracks.
- [ ] **Autonomous Content Agent**:
  - Performance feedback loop that fetches view and retention analytics from YouTube Studio API to fine-tune future script hooks.
- [ ] **Multi-Language Dubbing Engine**:
  - Automated translation and voice re-synthesis with lip-sync / pacing adjustment for global localized reels.

