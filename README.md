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









# KANIA.AI | AI Study Assistant

**Learn smarter. Practice with purpose.**

KANIA.AI is an AI-powered learning platform developed as an AI Engineering graduation project. It combines artificial intelligence, document processing, retrieval-augmented generation (RAG), flashcards, quizzes, learning progress tracking, and online examination workflows in one web application.

The platform is designed to help students study using their own learning materials while providing teachers and administrators with tools to manage learning activities, assessments, and student workflows.

**Project repository:** https://github.com/gedaMi6/ai-study-assistant

**Project type:** AI Engineering Graduation Project  
**Application:** Full-stack web application  
**Backend:** Python and FastAPI  
**Frontend:** HTML, CSS, and JavaScript  
**Database:** SQLite  
**AI provider:** Google Gemini  

---

## Table of Contents

1. Project Overview
2. Problem Statement
3. Project Objectives
4. Key Features
5. User Roles
6. Technology Stack
7. System Architecture
8. AI and RAG Workflow
9. Flashcards and Spaced Repetition
10. Examination Management
11. Database and Data Management
12. Project Structure
13. Installation and Setup
14. Environment Configuration
15. Running the Application
16. Testing and Quality Assurance
17. Security Considerations
18. Current Limitations
19. Project Roadmap
20. Future Enhancements
21. Contribution and Development
22. License
23. Author

---

## 1. Project Overview

KANIA.AI is a web-based study assistant that integrates AI-assisted learning with student progress tracking and structured assessment workflows.

Students can upload supported study documents, ask questions about their learning materials, generate study resources, review flashcards, complete quizzes, monitor their learning progress, and participate in assigned examinations.

The application uses a retrieval-augmented generation architecture to retrieve relevant passages from indexed study materials and provide context-aware responses through a language model.

In addition to the AI learning features, KANIA.AI provides authentication, role-based workflows, teacher-managed examinations, student submissions, result handling, and notifications.

The project demonstrates the practical application of AI engineering, backend development, frontend development, information retrieval, database design, application security, and automated testing.

## 2. Problem Statement

Students often study using multiple documents, applications, and resources without a centralized way to ask questions about their materials, organize revision, or monitor their learning progress.

Traditional study methods can also make it difficult to identify knowledge gaps, practise consistently, and connect learning materials with assessment activities.

KANIA.AI addresses these challenges by combining document-based AI assistance, automated study-resource generation, flashcard review, progress tracking, and examination management in one platform.

## 3. Project Objectives

The main objectives of KANIA.AI are to:

- Develop an AI-powered study assistant for students.
- Enable students to ask questions about their uploaded learning materials.
- Apply document processing, text embeddings, vector search, and RAG.
- Generate summaries, quizzes, and flashcards from study content.
- Support structured flashcard review and learning-progress tracking.
- Provide user authentication and role-based access.
- Support teacher-managed examinations and student submissions.
- Improve examination data integrity and result handling.
- Apply automated tests to critical application workflows.
- Demonstrate practical AI Engineering concepts through a working web application.

## 4. Key Features

### AI-Powered Study Assistance

- Ask questions about uploaded study materials.
- Retrieve relevant passages from indexed documents.
- Generate context-aware responses using Google Gemini.
- Support document-based learning and revision.

### Document Processing

- Upload supported study documents.
- Extract text from supported file formats.
- Divide extracted content into smaller passages.
- Generate embeddings for document chunks.
- Store and retrieve indexed content through ChromaDB.

### Summaries and Quizzes

- Generate study resources from learning materials.
- Create quizzes for revision and practice.
- Support learning activities associated with uploaded documents.

### Flashcards and Review

- Generate flashcards from study content.
- Save flashcard sets for later review.
- Track review ratings and learning status.
- Schedule future reviews using spaced-repetition logic.
- Update review intervals based on learner feedback.

### Learning Progress

- Record supported study activity.
- Track flashcard review progress.
- Provide progress information through the application interface.
- Support learning-related records used by dashboard and progress features.

### Authentication and Account Management

- User registration and login.
- Email verification workflows.
- Password-reset workflows.
- Session-based authentication.
- Student, teacher, and administrator roles.
- Profile-related functionality.

### Examination Management

- Teacher-managed exam creation and publication.
- Student access to assigned examinations.
- Password-protected exam workflows.
- Exam session management and answer autosaving.
- Student exam submissions.
- Result handling and score release.
- Notifications related to examination activity.
- Handling of expired sessions and duplicate submissions.

### Administration and Teacher Workflows

- Role-specific application interfaces.
- Student and teacher management functionality.
- Examination administration and monitoring.
- Support for assignment, submission, and result workflows.

Feature availability depends on the relevant application configuration, user permissions, and completed verification.

## 5. User Roles

### Student

Students can access supported learning features, upload study materials, use AI-assisted learning, generate and review flashcards, complete quizzes, monitor learning activity, and participate in assigned examinations.

### Teacher

Teachers can access supported teacher workflows, manage examinations, publish assessments, review submissions, release results, and use related student-management and monitoring functionality.

### Administrator

Administrators have access to supported administrative workflows for account and application management.

Role permissions are enforced through backend authentication and authorization logic. Comprehensive verification of every protected endpoint remains part of the security roadmap.

## 6. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Backend framework | FastAPI |
| ASGI server | Uvicorn |
| Frontend structure | HTML |
| Frontend styling | CSS |
| Frontend behavior | JavaScript |
| Language model | Google Gemini |
| AI integration | Google Gen AI SDK |
| Text embeddings | Sentence Transformers |
| Vector database | ChromaDB |
| Application database | SQLite |
| Data validation | Pydantic |
| Document processing | PyMuPDF, python-pptx, and other supported libraries |
| Email integration | aiosmtplib |
| Automated testing | Python unittest |
| Version control | Git |
| Repository hosting | GitHub |
| Development environment | Python virtual environment and WSL |

The project uses a Python-based backend with a browser-based frontend. The AI, document-processing, database, and authentication components are integrated through the FastAPI application.

## 7. System Architecture

KANIA.AI follows a modular architecture that connects the frontend, backend API, AI services, document retrieval system, and application database.

### High-Level Architecture

User
↓
HTML, CSS, and JavaScript Frontend
↓
FastAPI Backend
↓
Authentication and Authorization
↓
Application Services and API Routes
├── Document Processing
├── AI Question Answering
├── Quiz Generation
├── Flashcard Generation and Review
├── Learning Progress
├── Student Examination Workflows
├── Teacher Examination Workflows
├── Notifications
└── Administration and User Management
↓
Data and AI Services
├── SQLite Application Database
├── ChromaDB Vector Database
├── Sentence Transformers Embeddings
└── Google Gemini Language Model

### Architectural Responsibilities

**Frontend:** Presents the user interface and communicates with backend endpoints.

**FastAPI backend:** Handles requests, validates data, applies business rules, and coordinates application services.

**Authentication layer:** Identifies users and supports access control for protected workflows.

**SQLite:** Stores structured application records, including accounts and supported learning and examination data.

**ChromaDB:** Stores and retrieves indexed document content and vector representations.

**Sentence Transformers:** Generates embeddings used for semantic retrieval.

**Google Gemini:** Generates AI responses and study resources using the configured model.

## 8. AI and RAG Workflow

KANIA.AI uses retrieval-augmented generation to support questions about uploaded learning materials.

The general workflow is:

1. The student uploads a supported document.
2. The application extracts readable text from the document.
3. The extracted text is divided into manageable chunks.
4. An embedding model converts the chunks into vector representations.
5. The indexed content is stored in the vector database, with related document records maintained by the application.
6. When a student asks a question, the application retrieves relevant passages.
7. The retrieved context is provided to the configured language model.
8. Google Gemini generates a response informed by the retrieved material.
9. The application returns the response to the frontend.

### Why RAG Is Used

RAG helps the application connect AI-generated answers to relevant passages from the student's own materials instead of relying exclusively on the language model's general knowledge.

However, retrieval does not guarantee factual correctness. Retrieval quality, answer accuracy, unsupported claims, and behavior when relevant passages are missing must be evaluated through dedicated testing.

## 9. Flashcards and Spaced Repetition

KANIA.AI includes a flashcard workflow designed to support active recall and repeated revision.

### Flashcard Generation

Students can generate flashcards from indexed study documents. The generation workflow supports a configurable card count, optional topic focus, and a title for the saved set.

The current generation endpoint accepts between 1 and 30 cards per request, with a default of 10.

### Review Process

The review workflow records learner ratings and updates scheduling information, including:

- Next review time.
- Review interval.
- Ease factor.
- Number of repetitions.
- Last review timestamp.
- Learning status.

The scheduling logic adjusts future review times according to the learner's rating and previous review history.

### Testing

Automated tests cover review scheduling, review progression, invalid ratings, card ownership, missing cards, and persistence of review information.

The flashcard interface and review behavior continue to be refined as part of the project roadmap.

## 10. Examination Management

KANIA.AI includes student and teacher examination workflows.

### Teacher Workflow

The supported teacher workflow includes exam creation, publication, student assignment, submission review, result handling, and score release.

### Student Workflow

The supported student workflow includes accessing assigned examinations, working with exam sessions, saving answers, submitting examinations, and viewing released results through the relevant interfaces.

### Examination Integrity

Recent development has focused on:

- Preventing unauthorized access to unassigned examinations.
- Restricting access to unpublished examinations.
- Protecting password-protected examinations.
- Handling expired examination sessions.
- Preserving saved answers during autosave and submission.
- Preventing duplicate submissions.
- Avoiding duplicate result notifications.
- Maintaining consistency between examination records and related data.
- Enforcing SQLite foreign-key constraints.

Automated tests cover important examination-integrity and score-release scenarios. Full end-to-end verification across all roles, browsers, and production deployment conditions remains necessary.

## 11. Database and Data Management

KANIA.AI uses SQLite for structured application data and ChromaDB for vector-based document retrieval.

### SQLite

SQLite is used for application records associated with supported workflows, including authentication, documents, flashcards, learning progress, examinations, submissions, and notifications.

### ChromaDB

ChromaDB stores vector-indexed document content to support semantic retrieval.

### Data Integrity

The application enables SQLite foreign-key enforcement on database connections. Related records are managed according to the database schema and application transaction logic.

Database integrity tests verify foreign-key behavior, while examination tests cover important cases involving dependent records and data consistency.

### Local Data

Local databases, uploaded documents, vector-store data, profile images, and backups may contain private or sensitive information. These files should remain excluded from version control unless there is an explicit, safe reason to publish them.

## 12. Project Structure

The following is a high-level representation of the repository. The exact directory contents may change during development.

ai-study-assistant/
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   ├── ask.py
│   │   ├── quiz.py
│   │   ├── flashcards.py
│   │   ├── progress.py
│   │   ├── profile.py
│   │   ├── chat_sessions.py
│   │   ├── student_exams.py
│   │   ├── teacher_exams.py
│   │   ├── teacher_management.py
│   │   ├── teacher_monitoring.py
│   │   ├── student_tasks.py
│   │   ├── teacher_tasks.py
│   │   ├── notifications.py
│   │   ├── student_status.py
│   │   └── admin.py
│   ├── database/
│   │   └── database.py
│   └── main.py
├── frontend/
│   ├── css/
│   ├── js/
│   ├── icons/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── reset-password.html
│   ├── dashboard.html
│   ├── chat.html
│   ├── flashcards.html
│   ├── quiz.html
│   ├── exams.html
│   ├── exam.html
│   ├── progress.html
│   └── admin.html
├── data/
│   ├── study_assistant.db
│   ├── chroma/
│   ├── uploads/
│   └── profile_images/
├── tests/
│   ├── test_dashboard_notification_security.py
│   ├── test_database_foreign_keys.py
│   ├── test_flashcards_review.py
│   ├── test_score_release_migration.py
│   ├── test_student_exam_integrity.py
│   ├── test_student_released_grades.py
│   ├── test_teacher_exam_delete_integrity.py
│   └── test_teacher_exam_score_release.py
├── requirements.txt
├── .gitignore
├── .env
└── README.md

Note: Local runtime data and `.env` configuration should not be committed to GitHub. The structure above illustrates the main application areas; it is not a guarantee that every listed local data file is present in a fresh clone.

## 13. Installation and Setup

### Prerequisites

- Python 3.12 or a compatible version supported by the installed dependencies.
- Git.
- A terminal such as Linux shell or WSL.
- Internet access for dependency installation and AI/model services.
- A Google Gemini API key for AI-powered features.
- A compatible Python environment for the project's machine-learning dependencies.

Some AI and machine-learning dependencies can be large. Installation time and hardware requirements may vary depending on the operating system, Python version, and available CPU/GPU support.

### Step 1: Clone the Repository

Clone the project from GitHub and enter the project directory.

Repository:

https://github.com/gedaMi6/ai-study-assistant

### Step 2: Create a Virtual Environment

Create an isolated Python environment for the project and activate it before installing dependencies.

For Linux or WSL, the activation command is:

source venv/bin/activate

If the virtual environment does not exist yet, create it with:

python3 -m venv venv

### Step 3: Install Dependencies

Install the dependencies specified by the repository:

pip install -r requirements.txt

If installation fails because of operating-system, Python-version, or machine-learning compatibility issues, resolve the relevant dependency compatibility issue rather than assuming every environment supports the same packages.

### Step 4: Configure Environment Variables

Create a `.env` file in the project root and configure the values required by the application.

The core AI configuration includes:

GEMINI_API_KEY=your_gemini_api_key
MODEL_NAME=gemini-3.6-flash

The model name must match a model supported by the current application configuration and provider account.

Do not use the example API key as a real credential. Never publish actual API keys, email credentials, passwords, session secrets, or other sensitive configuration.

Check the application's configuration and authentication modules for any additional environment variables needed for email delivery or deployment.

### Step 5: Start the Application

From the project root, activate the virtual environment and start the FastAPI application with Uvicorn:

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

### Step 6: Open the Application

Open the application in your browser:

http://127.0.0.1:8000

The terminal running Uvicorn must remain active while using the local application.

The `/health` endpoint can be used to check whether the application is responding:

http://127.0.0.1:8000/health

The local application address is intended for development. A fresh installation may require environment configuration, database initialization, and model downloads before all features are usable.

## 14. Environment Configuration

KANIA.AI depends on configuration values for AI services and potentially other integrations.

### Required for AI Features

- `GEMINI_API_KEY`: API key used to authenticate with Google Gemini.
- `MODEL_NAME`: Configured language-model name used by the application.

### Additional Configuration

Email verification, password reset, cookie security, and other features may depend on additional settings defined in the application.

The exact variable names and defaults should be taken from the current source code rather than guessed.

### Configuration Safety

- Keep `.env` files out of version control.
- Use separate credentials for development and production.
- Never hard-code real API keys or passwords in source files.
- Rotate any credential that is accidentally exposed.
- Avoid sharing database files that contain personal information.
- Use HTTPS and secure cookie settings when deploying outside a local development environment.

## 15. Running and Developing the Application

The main FastAPI application is defined in `app/main.py`.

It initializes the database, mounts frontend assets, registers API routers, serves application pages, and starts a background worker for processing expired examination sessions.

### Development Mode

Uvicorn's reload mode is useful during development because it restarts the application when watched source files change.

Development mode should not be treated as a production deployment configuration.

### API Documentation

FastAPI normally provides interactive API documentation at:

http://127.0.0.1:8000/docs

The API documentation can be used to inspect registered endpoints and understand request and response schemas. Protected endpoints may require an authenticated session.

## 16. Testing and Quality Assurance

KANIA.AI includes automated tests written with Python's built-in `unittest` framework.

The test suite covers important application behaviors, including:

- Dashboard notification security and HTML escaping.
- SQLite foreign-key enforcement.
- Flashcard review scheduling and persistence.
- Score-release migration behavior.
- Student examination-session integrity.
- Handling of expired sessions and autosave.
- Protection against duplicate submissions.
- Student access restrictions for examinations.
- Released-grade behavior.
- Examination deletion and related-record integrity.
- Teacher authorization for score release.
- Prevention of duplicate notifications.

### Run the Tests

From the project root, activate the virtual environment and run:

python -m unittest discover -s tests -v

### Current Test Status

As of October 25, 2026, the test run reported:

- Tests executed: 42
- Passed: 42
- Failed: 0
- Errors: 0

Runtime: approximately 3.9 seconds in the tested development environment.

These results apply to the automated test suite that was executed. They do not establish complete coverage of every endpoint, all user journeys, production deployment, or all security requirements.

### Additional Quality Checks

The following commands can help check Python syntax, whitespace problems, and repository status:

python -m compileall -q app

git diff --check

git status --short

These checks supplement functional tests; they do not replace them.

## 17. Security Considerations

Security is an ongoing development responsibility for KANIA.AI.

Current work includes improvements to examination authorization, session handling, answer persistence, duplicate-submission protection, notification handling, HTML escaping, and database foreign-key enforcement.

Important security practices include:

- Keep API keys and passwords out of source control.
- Enforce authentication on protected API endpoints.
- Validate user permissions on every protected resource.
- Prevent students from accessing unassigned or unpublished examinations.
- Validate document uploads and user-provided input.
- Escape untrusted content before rendering it as HTML.
- Protect session cookies and authentication state.
- Use transactions where related database changes must succeed or fail together.
- Keep local databases, uploads, profile images, and backups private.
- Avoid logging credentials, session tokens, or unnecessary personal information.
- Review error handling so internal details are not exposed to users.
- Use HTTPS and secure cookie settings in production.

Security verification remains incomplete until all protected routes, authentication workflows, upload paths, and deployment settings have been systematically reviewed.

## 18. Current Limitations

The current project is a developing AI Engineering application rather than a fully verified production service.

Known areas requiring further work include:

- Comprehensive end-to-end testing across all user roles.
- Evaluation of retrieval quality and AI-generated answer accuracy.
- Testing behavior when AI providers return errors or exhaust quotas.
- Complete authorization review across protected endpoints.
- Verification of authentication, email delivery, and account recovery.
- Broader validation of document uploads and file-processing edge cases.
- Additional testing of examination workflows and notifications.
- Responsive design and accessibility review.
- Reproducible setup verification on a clean machine.
- Full technical documentation and demonstration preparation.

AI-generated answers can be incomplete or incorrect. Users should verify important information against their original learning materials.

Performance and installation requirements may vary according to the configured AI model, embedding model, machine-learning dependencies, hardware, and available API quota.

## 19. Project Roadmap

The roadmap distinguishes implemented capabilities from tasks that still need verification or completion. Checkmarks reflect development progress and should not be interpreted as proof of comprehensive production readiness.

### Phase 1: Project Foundation

- [x] Establish the AI Study Assistant project.
- [x] Create the FastAPI application structure.
- [x] Develop the browser-based frontend.
- [x] Establish the Python development environment.
- [x] Set up Git and GitHub version control.
- [x] Introduce KANIA.AI branding.

### Phase 2: AI Learning Engine

- [x] Implement document processing and text extraction.
- [x] Implement document chunking.
- [x] Integrate sentence embeddings.
- [x] Store and retrieve document passages using ChromaDB.
- [x] Integrate Google Gemini.
- [x] Implement retrieval-augmented question answering.
- [x] Implement study summaries and quizzes.
- [x] Implement flashcard generation.
- [x] Implement flashcard review scheduling.
- [x] Introduce learning-progress tracking.
- [ ] Evaluate retrieval relevance and answer accuracy.
- [ ] Test AI failure handling and quota behavior.
- [ ] Evaluate answer quality across different study documents.

### Phase 3: Authentication and User Roles

- [x] Implement registration and login workflows.
- [x] Implement email verification workflows.
- [x] Implement password-reset workflows.
- [x] Develop student, teacher, and administrator interfaces.
- [x] Implement role-specific application workflows.
- [ ] Verify authorization across all protected API endpoints.
- [ ] Test authentication and account-recovery edge cases.
- [ ] Review session expiration and cookie security.
- [ ] Verify email delivery and notification behavior.

### Phase 4: Examinations and Data Integrity

- [x] Implement teacher examination workflows.
- [x] Implement examination publication and student access.
- [x] Implement student submissions.
- [x] Implement score release and result notifications.
- [x] Add tests for examination-session integrity.
- [x] Improve autosave and expired-session handling.
- [x] Add protection against duplicate submissions.
- [x] Enable SQLite foreign-key enforcement.
- [x] Add tests for exam deletion and dependent records.
- [ ] Verify all examination workflows end to end.
- [ ] Test concurrency and recovery from unexpected failures.
- [ ] Verify monitoring, notification delivery, and result consistency.

### Phase 5: Flashcards and User Experience

- [x] Implement flashcard generation.
- [x] Implement flashcard review ratings.
- [x] Implement spaced-repetition scheduling.
- [x] Add automated tests for flashcard review behavior.
- [x] Improve dashboard notification rendering security.
- [x] Develop a redesigned flashcard interface.
- [ ] Refine the flashcard interface further.
- [ ] Improve loading, empty, and error states.
- [ ] Improve dashboard and progress presentation.
- [ ] Polish teacher and administrator interfaces.
- [ ] Test responsive layouts on different screen sizes.
- [ ] Review keyboard navigation and accessibility.
- [ ] Verify that UI changes do not break existing workflows.

### Phase 6: Reliability and Security

- [x] Add automated tests for critical workflows.
- [x] Test database foreign-key enforcement.
- [x] Test important examination-integrity rules.
- [x] Test dashboard notification escaping.
- [x] Run the current automated test suite successfully.
- [ ] Establish a comprehensive testing plan.
- [ ] Audit authentication and authorization.
- [ ] Review file-upload validation and sensitive-data handling.
- [ ] Test API error handling and rate-limit behavior.
- [ ] Evaluate database consistency across all workflows.
- [ ] Complete a broader secret and dependency review.
- [ ] Perform final regression testing.

### Phase 7: Technical Documentation

- [ ] Finalize the README and setup instructions.
- [ ] Document functional and non-functional requirements.
- [ ] Prepare the system architecture diagram.
- [ ] Prepare the database schema and relationship diagrams.
- [ ] Document the AI and RAG pipeline.
- [ ] Document important API endpoints and permissions.
- [ ] Prepare use-case and workflow diagrams.
- [ ] Document testing procedures and results.
- [ ] Record known limitations and design decisions.
- [ ] Prepare the technical report according to university guidelines.

### Phase 8: Final Evaluation and Demonstration

- [ ] Prepare safe demonstration accounts and sample documents.
- [ ] Create a reproducible demonstration script.
- [ ] Demonstrate document upload and AI question answering.
- [ ] Demonstrate summaries, quizzes, and flashcards.
- [ ] Demonstrate learning-progress functionality.
- [ ] Demonstrate teacher examination management.
- [ ] Demonstrate student submissions and released results.
- [ ] Verify installation from a clean environment.
- [ ] Verify repository contents and secret exclusions.
- [ ] Complete final regression testing.
- [ ] Prepare presentation slides.
- [ ] Prepare final project deliverables.
- [ ] Deliver the graduation-project presentation.

### Phase 9: Future Enhancements

- [ ] Improve personalized study recommendations.
- [ ] Expand supported document formats.
- [ ] Improve learning analytics.
- [ ] Evaluate alternative language models and embedding models.
- [ ] Improve retrieval evaluation and response quality.
- [ ] Explore production deployment and monitoring.
- [ ] Evaluate scalability and performance.
- [ ] Consider additional learning tools based on user feedback.

## 20. Future Enhancements

Potential future improvements include more personalized revision recommendations, stronger retrieval evaluation, broader document support, richer learning analytics, improved accessibility, and deployment options for wider use.

These enhancements should be prioritized according to user feedback, project requirements, technical feasibility, and the objectives of the graduation project.

## 21. Contribution and Development

KANIA.AI is being developed as an AI Engineering graduation project.

Development work includes backend implementation, frontend development, AI integration, database management, security improvements, automated testing, documentation, and interface refinement.

Contributions should preserve existing functionality, respect user-data privacy, and include appropriate tests for changes affecting application behavior.

For development changes:

1. Understand the relevant module and its dependencies.
2. Make focused changes.
3. Run the relevant automated tests.
4. Review error handling and authorization.
5. Verify database consistency where applicable.
6. Review the Git diff before committing changes.

## 22. License

No explicit open-source license has been confirmed for this repository.

Unless a license is added, the repository should not be assumed to grant permission to reuse, redistribute, or modify its contents beyond rights provided by applicable law.

A suitable license should be selected and added only after the project owner determines how the project should be shared.

## 23. Author

**Geda Mulatu**  
AI Engineering Student  
Developer of KANIA.AI | AI Study Assistant

GitHub: https://github.com/gedaMi6

Repository: https://github.com/gedaMi6/ai-study-assistant

---

## Final Note

KANIA.AI demonstrates the integration of artificial intelligence, document retrieval, learning tools, database-backed application workflows, and examination management within a full-stack web application.

The project is under active development. Its current automated test results demonstrate that the tested workflows are functioning as expected in the development environment, while broader system verification, documentation, security review, and final demonstration preparation remain ongoing.

**KANIA.AI — Learn smarter. Practice with purpose.**

