# NavigAI API

NavigAI API is a backend service for AI-powered job search and roadmap generation. This project is organized into modular components for easy extension and contribution.

## Table of Contents

- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Routes](#routes)
- [Services](#services)
- [Agents](#agents)
- [License](#license)

---

## Project Structure

```
├── src/
│   ├── server.py              # Main server entry point
│   ├── routes/                # API route definitions
│   ├── services/              # Business logic and service layer
│   ├── agents/                # AI agent logic
│   ├── core/                  # Core utilities (logging, settings)
│   ├── db/                    # Database integrations
│   └── models/                # Data models
├── logs/                      # Log files
├── pyproject.toml             # Poetry configuration
├── poetry.lock                # Poetry lock file
├── README.md                  # Project documentation
```

## Getting Started

1. **Clone the repository:**

   ```sh
   git clone https://github.com/shashiKundur1/NavigAI-api.git
   cd NavigAI-api
   ```

2. **Install dependencies:**

   ```sh
   pip install poetry
   poetry install
   ```

3. **Run the server:**
   ```sh
   poetry run python src/server.py
   ```

---

## How to Contribute

1. **Fork the repository** on GitHub.
2. **Clone your fork:**
   ```sh
   git clone https://github.com/<your-username>/NavigAI-api.git
   cd NavigAI-api
   ```
3. **Create a new branch:**
   ```sh
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes and commit:**
   ```sh
   git add .
   git commit -m "Describe your changes"
   ```
5. **Push your branch:**
   ```sh
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** on GitHub to the `main` branch.

---

## Routes

All API routes are defined in `src/routes/`:

- `health.py`: Health check endpoint.
- `job_search.py`: Endpoints for job search features.
- `roadmap.py`: Endpoints for roadmap generation.

Each route file defines FastAPI endpoints and delegates business logic to the corresponding service.

## Services

Service files in `src/services/` contain the core business logic:

- `job_search_service.py`: Handles job search logic.
- `roadmap_service.py`: Handles roadmap generation logic.

Services are called by route handlers and may interact with agents or the database.

## Agents

Agent files in `src/agents/` encapsulate AI logic:

- `job_search_agent.py`: Implements job search agent logic.
- `roadmap_agent.py`: Implements roadmap agent logic.

Agents are used by services to perform AI-driven tasks.

---

## License

This project is licensed under the MIT License.
