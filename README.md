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

## Summary

I have successfully implemented a comprehensive AI Mock Interview System for your NavigAI project. Here's what has been created:

### 📁 Files Created:

1. **`src/models/mock_interview.py`** - Data models for the interview system

   - Question, Answer, InterviewSession models
   - Performance metrics and report structures
   - Thompson sampling parameters

2. **`src/services/mock_interview_service.py`** - Core service logic

   - Multi-armed bandit with Thompson sampling
   - Real-time audio processing with Whisper
   - Multi-modal analysis system
   - PDF report generation
   - Adaptive learning engine

3. **`src/agents/mock_interview_agent.py`** - Interview coordination agent

   - Session management
   - Question selection logic
   - Response analysis coordination
   - GUI integration

4. **`src/routes/mock_interview.py`** - API endpoints

   - Complete REST API for all interview functions
   - Session management endpoints
   - Analytics and reporting endpoints
   - Health check and monitoring

5. **`src/main.py`** - Enhanced GUI application

   - Professional interface with CustomTkinter
   - Tabbed interface (Interview, History, Analytics, Settings)
   - Real-time audio recording and analysis
   - Comprehensive reporting features

6. **Updated `pyproject.toml`** - Dependencies and configuration

   - All required packages for AI, audio, GUI, and reporting
   - Development tools and testing frameworks
   - Build and packaging configuration

7. **`README.md`** - Comprehensive documentation
   - Installation and usage instructions
   - Architecture overview
   - Feature descriptions
   - Contributing guidelines

### 🎯 Key Features Implemented:

1. **Adaptive Question Selection**: Uses Thompson Sampling to intelligently select questions based on candidate performance
2. **Real-time Speech Processing**: Integrates OpenAI Whisper for accurate speech-to-text transcription
3. **Multi-modal Analysis**: Analyzes voice tone, sentiment, confidence, and technical accuracy
4. **AI-powered Feedback**: Uses Google Gemini for intelligent response analysis and scoring
5. **Comprehensive Reports**: Generates detailed PDF reports with performance metrics and recommendations
6. **Modern GUI**: Professional interface with real-time feedback and analytics
7. **Scalable Architecture**: Modular design supporting easy extension and customization

### 🚀 How to Use:

1. **Install dependencies**:
   ```bash
   pip install poetry
   poetry install
   ```
