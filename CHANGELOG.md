# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-07

### Added
- **Open-Source Infrastructure**:
  - Standardized modern `pyproject.toml` packaging and metadata.
  - Multi-version GitHub Actions CI matrix running on Python 3.10, 3.11, 3.12, and 3.13.
  - Comprehensive pytest automated test suite with unit tests, config validation, and AI service mocks.
  - High-speed linting and formatting configuration via `Ruff`.
  - Contributor guides: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `ROADMAP.md`.
  - GitHub issue templates for bug reports and feature requests, pull request template, and `CODEOWNERS`.
- **Security Hardening**:
  - Removed all hardcoded fallback API keys from code and replaced with strict environment variable resolution.
  - Enhanced `.gitignore` covering caches, coverage outputs, and temporary video artifacts.
  - Safe `.env.example` template with clear setup instructions.
- **Developer Experience**:
  - Resilient offline fallback script generator enabling testing without active paid credentials.
  - Type hints and `__init__.py` module packaging across `backend`, `pipeline`, and `tests`.
  - Modernized UTC datetime calls to prevent Python 3.12+ deprecation warnings.

### Core Features Preserved
- 5-Step Studio Creator Wizard with glassmorphic React/Vite interface.
- 8 Curated viral content niches with tested hook formulas and art styles.
- Studio audio synthesis with broadcast EBU R128 (-14 LUFS) loudness normalization.
- Dynamic ASS word-by-word animated captions (MrBeast Gold, Neon Emerald, Cyberpunk Cyan, Fire Ruby).
- 9:16 vertical video compositing with multi-preset Ken Burns cinematic motion.
- Deterministic QA Gatekeeper validating video, audio, and subtitle synchronization.
- Automated YouTube metadata compiler and resumable chunked uploader.
