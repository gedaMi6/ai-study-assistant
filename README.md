# KANIA.AI | AI Study Assistant

**Learn smarter. Practice with purpose.**

KANIA.AI is an AI-powered study platform developed as an AI Engineering graduation project. It helps students learn from their own materials, practise concepts, track progress, and participate in structured assessments.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Getting Started](#getting-started)
- [Project Roadmap](#project-roadmap)
- [Project Structure](#project-structure)
- [Security](#security)
- [Testing and Quality Assurance](#testing-and-quality-assurance)
- [Future Enhancements](#future-enhancements)

## Project Overview

KANIA.AI combines AI-assisted learning with document retrieval, study resources, learning progress, and examination workflows.

The system uses retrieval-augmented generation (RAG) to retrieve relevant passages from uploaded study materials and provide context-aware answers using a language model.

The project aims to make studying more organized, interactive, and accessible while demonstrating practical AI Engineering concepts.

## Features

### AI-Powered Learning
- Upload and process supported study documents.
- Extract text and divide it into manageable chunks.
- Generate embeddings and index document passages.
- Retrieve relevant content using ChromaDB.
- Ask questions about learning materials using RAG.
- Generate study summaries and quizzes.

### Flashcards and Progress
- Generate flashcards from study content.
- Save flashcard sets for review.
- Track flashcard review activity.
- Monitor learning progress and study performance.

### Authentication and User Roles
- User registration and login.
- Email verification and password-reset workflows.
- Student, teacher, and administrator functionality.
- Role-based access to supported features.

### Examination Workflows
- Exam creation and management.
- Exam publishing and student access.
- Student exam submissions.
- Result handling and notifications.

*Feature availability and behavior should be verified through end-to-end testing before final release.*

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Language model | Google Gemini |
| Embeddings | Sentence Transformers |
| Vector database | ChromaDB |
| Application database | SQLite |
| Development environment | Python, WSL, virtual environment |
| Version control | Git and GitHub |

## System Architecture

KANIA.AI follows a document-processing and retrieval pipeline.

1. **Document upload:** The user provides study material.
2. **Text extraction:** The application extracts text from supported files.
3. **Chunking:** Extracted text is divided into smaller passages.
4. **Embedding:** Text passages are converted into vector representations.
5. **Indexing:** Embeddings and associated content are stored in ChromaDB.
6. **Retrieval:** Relevant passages are retrieved for a user's question.
7. **Response generation:** Gemini generates an answer using the retrieved context.
8. **Learning support:** The platform provides study resources and records supported learning activity.

Authentication, role-based access, examination workflows, and application data are managed through the backend and database layer.

## Getting Started

### Prerequisites

- Python 3.12 or a compatible version supported by the project dependencies.
- Git.
- A configured Python virtual environment.
- A Google Gemini API key for AI features.
- WSL on Windows, or another compatible Python environment.

### 1. Clone the repository

```bash
git clone https://github.com/gedaMi6/ai-study-assistant.git
cd ai-study-assistant
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and add your own configuration:

```env
GEMINI_API_KEY=your_gemini_api_key
MODEL_NAME=gemini-3.6-flash
```

Use the model name configured and supported by your current application. Never commit actual API keys or other secrets.

### 5. Start the application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the application in your browser:

`http://127.0.0.1:8000`

Keep the terminal running while using the local application.

## Project Roadmap

The roadmap separates implemented capabilities from tasks that still require verification or completion.

### Phase 1: Project Foundation

- [x] Define the AI Study Assistant project.
- [x] Establish the Python development environment.
- [x] Create the FastAPI application structure.
- [x] Develop the frontend structure.
- [x] Establish Git version control.
- [x] Introduce KANIA.AI branding.

### Phase 2: Core AI Learning Engine

- [x] Implement document processing and text extraction.
- [x] Implement document chunking.
- [x] Integrate text embeddings.
- [x] Store and retrieve document passages using ChromaDB.
- [x] Integrate Gemini for AI-generated responses.
- [x] Implement retrieval-augmented question answering.
- [x] Implement summaries and quizzes.
- [x] Implement flashcard generation and review workflows.
- [x] Introduce learning progress tracking.
- [ ] Evaluate retrieval quality and answer accuracy.
- [ ] Test AI failure handling and quota limits.

### Phase 3: Authentication and Assessments

- [x] Implement registration and login workflows.
- [x] Implement email verification and password reset.
- [x] Develop student, teacher, and administrator workflows.
- [x] Implement exam management and publishing.
- [x] Implement student exam submissions.
- [x] Implement result and notification workflows.
- [ ] Verify role permissions across all protected endpoints.
- [ ] Test exam edge cases and duplicate submissions.
- [ ] Verify notification persistence and delivery.

### Phase 4: Reliability and Security

- [ ] Create a comprehensive testing plan.
- [ ] Test authentication and account recovery.
- [ ] Test document upload and processing.
- [ ] Test RAG responses and learning-resource generation.
- [ ] Test flashcard review and progress persistence.
- [ ] Test exam creation, access, submission, and results.
- [ ] Audit authorization, sessions, and cookies.
- [ ] Validate file uploads and input handling.
- [ ] Verify database consistency and error handling.
- [ ] Fix confirmed defects and run regression tests.

### Phase 5: User Interface and Experience

- [ ] Refine the flashcard interface.
- [ ] Improve student dashboard and progress presentation.
- [ ] Polish teacher and administrator dashboards.
- [ ] Improve loading, empty, and error states.
- [ ] Standardize typography, spacing, and visual components.
- [ ] Test responsive layouts and accessibility.
- [ ] Verify that interface changes do not break existing workflows.

### Phase 6: Technical Documentation

- [ ] Document the problem statement and project objectives.
- [ ] Document functional and non-functional requirements.
- [ ] Prepare the system architecture diagram.
- [ ] Prepare the database schema and relationship diagrams.
- [ ] Document the AI and RAG pipeline.
- [ ] Document important API endpoints and role permissions.
- [ ] Prepare use-case and workflow diagrams.
- [ ] Record test cases, results, and supporting screenshots.
- [ ] Document limitations and known issues.
- [ ] Prepare the technical report using university guidelines.

### Phase 7: Final Evaluation and Demonstration

- [ ] Prepare demonstration accounts and sample documents.
- [ ] Prepare a reproducible demonstration script.
- [ ] Demonstrate the AI learning pipeline.
- [ ] Demonstrate flashcards, quizzes, and learning progress.
- [ ] Demonstrate teacher/admin exam management.
- [ ] Demonstrate student submissions and results.
- [ ] Verify the application starts from a clean environment.
- [ ] Check that the repository contains no secrets or private user data.
- [ ] Complete final regression testing.
- [ ] Prepare presentation slides.
- [ ] Submit the project deliverables.
- [ ] Deliver the final graduation-project presentation.

### Phase 8: Future Enhancements

- [ ] Improve personalized study recommendations.
- [ ] Expand supported document formats.
- [ ] Evaluate alternative language models.
- [ ] Improve learning analytics.
- [ ] Explore deployment and monitoring.
- [ ] Evaluate scalability and performance.

**Roadmap note:** A checked item indicates that the capability has been implemented during development. It does not necessarily mean every related test has passed. Testing and verification remain separate tasks.

## Project Structure

The following is a simplified overview. Actual files and directories may vary as the project evolves.

```text
ai-study-assistant/
├── app/                 # FastAPI backend and application modules
├── frontend/            # HTML, CSS, JavaScript, and assets
├── data/                # Local databases and application data
├── requirements.txt     # Python dependencies
├── .env                 # Local environment configuration
└── README.md            # Project documentation and roadmap
```

## Security

- Keep API keys and credentials out of source control.
- Keep local databases, uploaded documents, and personal information private.
- Enforce authorization on protected API endpoints.
- Validate user input and uploaded files.
- Avoid exposing sensitive information in logs or error responses.
- Configure secure cookies and HTTPS for production deployment.
- Back up important project data securely.

## Testing and Quality Assurance

Basic development checks can be run from the project root:

```bash
python -m compileall -q app
git diff --check
git status --short
```

These checks help identify Python compilation errors and whitespace problems. They do not replace functional, integration, or security testing.

The final release should be evaluated using reproducible test cases covering authentication, document processing, AI responses, flashcards, examinations, authorization, and data persistence.

## Future Vision

KANIA.AI aims to develop into a reliable AI learning companion that helps students study from their own materials, practise important concepts, understand their progress, and prepare more effectively for assessments.

The priority is to complete and verify the core workflows before expanding the system with optional features.

## Repository

[View KANIA.AI on GitHub](https://github.com/gedaMi6/ai-study-assistant)

---

**KANIA.AI**  
*An AI-powered learning companion built to make studying more effective.*

