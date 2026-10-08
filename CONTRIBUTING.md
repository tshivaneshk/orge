# Contributing to ORGE

Thank you for your interest in contributing to **ORGE**! As an open-source project, we welcome contributions of all kinds, including bug reports, documentation enhancements, feature proposals, and code contributions.

## Code of Conduct

Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions within this project.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/<your-username>/orge.git
   cd orge
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install in editable development mode:
   ```bash
   pip install -e .
   ```

## Running Tests

All tests should pass prior to submitting a pull request:
```bash
python -m unittest discover -v -s tests
```

## Architectural Guidelines (ORGE)

When modifying the engine, preserve the separation of concerns:
- **CLI/UI** (`orge.cli`, `orge.ui`): Handles presentation, terminal output, and arguments. Never move files directly here.
- **Planner** (`orge.planner`): Pre-calculates exact paths and deterministic collisions.
- **Classifier** (`orge.classifier`): Pure decision logic using regex, glob, extension, and metadata heuristics.
- **Safety Validator** (`orge.safety`): Reject any operation escaping boundaries, tampering with system directories, or targeting symlinks.
- **Executor & History** (`orge.executor`, `orge.history`): Manages moves, journals, and atomic rollback state.

## Submitting Pull Requests

- Keep PRs focused on a single issue or feature.
- Include unit tests covering new functionality or edge cases.
- Update documentation and `CHANGELOG.md` where appropriate.
