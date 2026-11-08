# Contributing to FacelessReels

Thank you for your interest in contributing to **FacelessReels**! We are building an open, modular, developer-friendly framework for AI-powered vertical video and short-form content creation.

Whether you are fixing a typo, adding a new subtitle preset, integrating an alternative voice engine, or improving rendering speed, your contributions are warmly welcomed.

---

## Code of Conduct

All contributors and participants agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat everyone with empathy and respect.

---

## Getting Started

### 1. Prerequisites
- **Python 3.10 to 3.13**
- **Node.js 18+ & npm** (for the Vite frontend studio)
- **FFmpeg & ffprobe** (essential for audio/video processing):
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install -y ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` or install via Scoop/Chocolatey

### 2. Fork and Clone
```bash
git clone https://github.com/<your-username>/faceless-reels.git
cd faceless-reels
```

### 3. Set Up Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables
Copy the template and add your API keys:
```bash
cp .env.example .env
```
*(Tests do not make paid API calls; an empty or mock key is sufficient for local test execution).*

### 5. Set Up Frontend (Optional for backend work)
```bash
cd frontend
npm install
npm run dev
```

---

## Development Workflow

### Branching Convention
Create a dedicated topic branch from `main`:
```bash
git checkout -b feature/my-cool-feature
# or
git checkout -b fix/issue-123-bug
```

### Running Tests
We enforce strict automated test coverage. Verify all tests pass before opening a PR:
```bash
pytest tests/ backend/
```

### Running Linting & Quality Checks
We use [Ruff](https://docs.astral.sh/ruff/) for high-speed Python linting and formatting:
```bash
ruff check .
```
To automatically apply safe fixes:
```bash
ruff check --fix .
```

### Testing the Frontend Build
```bash
npm --prefix frontend run build
```

---

## Contribution Guidelines

1. **Keep Existing Pipelines Working**: Do not break existing video compositing, Ken Burns motion, or audio mastering logic without discussion and test proof.
2. **Never Commit Secrets**: Never commit `.env` files, API keys, OAuth client secrets, or private tokens. All credentials must come from environment variables.
3. **No Paid Network Calls in Automated Tests**: Always use mocks or unit-level test cases in `tests/` so CI executes cleanly without billing charges.
4. **Meaningful Commit Messages**: Follow the Conventional Commits specification (e.g., `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`).

---

## Submitting a Pull Request

1. Push your branch to your GitHub fork:
   ```bash
   git push origin feature/my-cool-feature
   ```
2. Open a Pull Request against the `main` branch of `peacefulcoder-911/faceless-reels`.
3. Fill out the PR template completely.
4. Ensure CI checks pass on GitHub Actions.
5. Address any review feedback with additional commits.

---

## Finding Something to Work On
Check out issues labeled:
- [`good first issue`](https://github.com/peacefulcoder-911/faceless-reels/labels/good%20first%20issue): Great entry points for new contributors.
- [`help wanted`](https://github.com/peacefulcoder-911/faceless-reels/labels/help%20wanted): High-impact tasks ready for community collaboration.

