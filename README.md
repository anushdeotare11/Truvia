<div align="center">

# 🛡️ Truvia — Autonomous Digital Public Safety Platform

  <p align="center">
    <strong>AI-Powered Incident Response, Automated Scam Intelligence, and Multi-Agent Cybercrime Investigation</strong>
  </p>

  <p align="center">
    <a href="#-demo">View Demo</a> •
    <a href="#-installation-guide">Get Started</a> •
    <a href="#-key-features">Features</a> •
    <a href="#-system-architecture">Architecture</a> •
    <a href="#-api-documentation">API Docs</a>
  </p>

  <!-- Badges -->
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/FastAPI-0.110.0-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/Next.js-14.2.35-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js">
    <img src="https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
    <img src="https://img.shields.io/badge/PostgreSQL-NeonDB-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
    <img src="https://img.shields.io/badge/Neo4j-GraphDB-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j">
    <img src="https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge" alt="Build Status">
  </p>

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Solution](#-solution)
- [Key Features](#-key-features)
- [AI Capabilities](#-ai-capabilities)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation Guide](#-installation-guide)
- [Environment Variables](#-environment-variables)
- [Running the Project](#-running-the-project)
- [Workflow](#-workflow)
- [Demo](#-demo)
- [API Documentation](#-api-documentation)
- [Future Roadmap](#-future-roadmap)
- [Performance & Scalability](#-performance--scalability)
- [Security](#-security)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [Contributors](#-contributors)
- [Acknowledgements](#-acknowledgements)

---

## 🌐 Overview

**Truvia** is an autonomous, end-to-end digital public safety platform designed to modernize citizen cybercrime reporting and police investigation workflows. Built using modern multi-agent artificial intelligence, Truvia ingests, standardizes, enriches, and analyzes citizen incident reports—ranging from WhatsApp phishing screenshots and call recordings to text transcripts—in real time.

By utilizing multimodal AI, graph intelligence (Neo4j), vector similarity search (pgvector), and automated threat intelligence aggregation, Truvia enables law enforcement officers to detect cybercrime rings, track recurring malicious entities (UPI IDs, phone numbers, crypto wallets), and coordinate proactive interventions before financial or physical harm escalates.

---

## ❓ Problem Statement

Digital financial scams, phishing attacks, and online fraud are growing exponentially. However, existing public safety and law enforcement reporting infrastructure suffers from severe systemic bottlenecks:

1. **Unstructured & Fragmented Data**: Victims submit evidence as disparate WhatsApp screenshots, voice notes, transaction receipts, or unstructured text complaints.
2. **Manual Processing Backlog**: Cybercrime officers must manually transcribe, verify, and cross-reference thousands of daily complaints across disconnected databases.
3. **Siloed Incident Tracking**: Individual reports involving the *same* scammer or UPI ID are treated as separate isolated cases, failing to expose coordinated fraud rings.
4. **Delayed Escalation**: High-severity, high-value financial fraud incidents are delayed in queues alongside low-priority inquiries, leaving financial institutions unable to freeze stolen funds in time.

---

## 💡 Solution

Truvia solves these challenges through an **Autonomous Multi-Agent AI Pipeline**:

- **Multimodal Instant OCR & STT**: Automatically transcribes evidence images, audio recordings, and text submissions using vision and speech AI.
- **Explainable Threat Evaluation**: Computes real-time threat scores (0–100), scam taxonomy categorization, and actionable guidance for citizens within seconds.
- **Automated Entity Extraction & Linking**: Extracts entity spans (phone numbers, UPI IDs, bank accounts, phishing URLs) and cross-links them in a Graph Database (Neo4j).
- **Fraud Ring Clustering**: Automatically clusters related cases into organized fraud rings, providing cybercrime investigators with court-admissible evidence trees.
- **Officer & Admin Workspaces**: Empowers law enforcement officers with interactive intelligence maps, heatmaps, case assignment tools, and AI copilot investigation summaries.

---

## ✨ Key Features

### 👤 Citizen Features
- **Fraud Shield Portal**: Simple intake for SMS, WhatsApp screenshots, call recordings, or text descriptions.
- **Instant Risk Breakdown**: Real-time 0–100 Threat Score, Scam Category classification, and personalized protective actions.
- **One-Click Police Escalation**: Citizens can escalate high-risk incidents directly to the official police complaint queue.
- **My Cases & Trackers**: Citizen portal to view historical submissions, status updates, and download official PDF complaint reports.
- **Live Scam Interceptor**: Real-time transcript scanner for active phone calls or chat sessions to alert users during live phishing attempts.

### 🤖 AI Pipeline Features
- **Multimodal Optical Character Recognition (OCR)**: Rapid text extraction from screenshots (JPEG/PNG/WEBP) using Gemini Vision API & RapidOCR.
- **Speech-to-Text (STT) Transcription**: Audio file transcription (MP3/WAV/M4A) using Whisper models.
- **Explainable RAG Threat Scoring**: Contextual threat analysis grounded in law enforcement knowledge base guidelines.
- **Entity Extraction Ledger**: Automatic normalization of phone numbers, UPI handles, bank accounts, URLs, and IP addresses.

### 🛡️ Authority & Officer Features
- **Command & Control Dashboard**: Live operational overview of active complaints, high-priority threats, and pending investigations.
- **Intelligence Graph Explorer**: Interactive network graph visualizing connected scam entities, shared bank accounts, and linked reports.
- **Fraud Ring Clustering**: Automated discovery of coordinated cybercrime rings operating across multiple jurisdictions.
- **Geo-Priority Map**: Heatmap visualization of incident density across cities and states to optimize officer resource allocation.
- **AI Investigation Copilot**: Dynamic case background summarization and automated court-admissible evidence package generation.

### ⚙️ Admin Features
- **System Health Telemetry**: Live monitoring of agent latencies, API quotas, system memory, database pools, and error rates.
- **Knowledge Base RAG Ingestion**: Ingest, chunk, and index law enforcement operating manuals and legal protocols into vector storage.
- **User & Role Governance**: Manage permissions and credentials across Citizen, Officer, and Administrator roles.

---

## 🧠 AI Capabilities

Truvia integrates multi-agent AI architecture:

| Capability | Engine / Technology | Description |
| :--- | :--- | :--- |
| **Optical Character Recognition (OCR)** | Google Gemini Vision API / RapidOCR | Extracts text from screenshots, transaction receipts, and digital chats. |
| **Speech-to-Text (STT)** | OpenAI Whisper / Faster-Whisper | Transcribes audio recordings of scam phone calls and voice notes. |
| **Multimodal Threat Scoring** | Gemini 2.5 Flash | Evaluates composite evidence to generate threat scores (0–100) & risk reasoning. |
| **Grounded RAG System** | pgvector / Cosine Similarity | Retrieves law enforcement guidelines to ground threat scores and prevention steps. |
| **Entity Extraction & Extraction** | Regex + LLM Entity Normalizer | Identifies and normalizes phone numbers, UPI IDs, Bank Accounts, and URLs. |
| **Threat Graph Indexing** | Neo4j Cypher Graph Engine | Builds relationship graph between reports, victims, entities, and scam rings. |
| **Dynamic Case Summarization** | Investigation Agent (LLM) | Generates executive case summaries and timelines for assigned officers. |

---

## 🏗️ System Architecture

```
                                 +-----------------------------------+
                                 |          Citizen / User           |
                                 +-----------------------------------+
                                                   |
                                     (HTTP REST / Next.js Client)
                                                   v
                                 +-----------------------------------+
                                 |      Next.js Frontend Portal      |
                                 |         (React / Tailwind)        |
                                 +-----------------------------------+
                                                   |
                                         (API Proxy / JSON)
                                                   v
                                 +-----------------------------------+
                                 |       FastAPI Backend Engine      |
                                 +-----------------------------------+
                                                   |
         +-----------------------------------------+-----------------------------------------+
         |                                         |                                         |
         v                                         v                                         v
+------------------+                    +---------------------+                    +-------------------+
|  Neon PostgreSQL |                    | Multi-Agent Pipeline|                    | Neo4j Graph Database|
| (Relational Data |                    |  - Agent 1: OCR/STT |                    | (Entity Links &   |
|   & pgvector)    |                    |  - Agent 2: Threat  |                    |   Scam Rings)     |
+------------------+                    |  - Agent 4: Entities|                    +-------------------+
                                        |  - Agent 5: Graph   |
                                        +---------------------+
                                                   |
                                                   v
                                        +---------------------+
                                        |  Google Gemini API  |
                                        +---------------------+
```

---

## 🛠️ Tech Stack

### Frontend
| Technology | Description |
| :--- | :--- |
| **Next.js 14** | React Framework (App Router) |
| **TypeScript** | Type-safe development |
| **Vanilla CSS / Modern Typography** | Modern dark-mode UI design |
| **Lucide Icons / Material Symbols** | UI icon sets |

### Backend
| Technology | Description |
| :--- | :--- |
| **FastAPI** | High-performance Python async REST web framework |
| **Python 3.11+** | Core programming language |
| **SQLAlchemy 2.0 (Async)** | Async ORM for database operations |
| **Alembic** | Database migration management |
| **Pydantic v2** | Request validation & response schemas |

### AI & Data Storage
| Technology | Description |
| :--- | :--- |
| **Google Gemini API (2.5 Flash)** | Primary Multimodal LLM & Vision engine |
| **pgvector** | PostgreSQL vector extension for similarity search |
| **Neo4j** | Graph database for network threat analysis |
| **RapidOCR / PIL** | Local fallback OCR engines |
| **Cloudinary** | Cloud media & evidence asset storage |

---

## 📁 Project Structure

```
Truvia/
├── truvia-backend/                   # FastAPI Backend Application
│   ├── app/
│   │   ├── agents/                   # Autonomous Multi-Agent AI Handlers
│   │   │   ├── input_processor.py    # Agent 1: OCR & STT Transcription
│   │   │   ├── threat_evaluator.py   # Agent 2: RAG Threat Scoring & Reasoner
│   │   │   ├── entity_extractor.py   # Agent 4: Entity Recognition & Ledger
│   │   │   ├── threat_intel.py       # Agent 5: Neo4j Graph Indexing
│   │   │   └── investigation.py      # Agent 6: Dynamic Case Summarizer
│   │   ├── api/                      # REST API Endpoints (v1)
│   │   │   ├── v1/                   # Auth, Reports, Graph, Admin, Cases, Alerts
│   │   │   └── deps.py               # Dependency Injection & Security
│   │   ├── core/                     # Configuration, Security, & Metrics
│   │   ├── data/                     # Database Clients (Postgres, Neo4j, Vector)
│   │   ├── models/                   # SQLAlchemy Database Models
│   │   ├── orchestration/            # Pipeline Execution & Event Handlers
│   │   └── main.py                   # FastAPI Application Entry Point
│   ├── alembic/                      # Migration Scripts
│   ├── requirements.txt              # Python Dependencies
│   └── alembic.ini                   # Migration Config
│
├── truvia-frontend/                  # Next.js Frontend Application
│   ├── src/
│   │   ├── app/                      # Next.js App Router Pages & Layouts
│   │   │   ├── (app)/                # Authenticated App Routes (Dashboard, Shield, etc.)
│   │   │   ├── auth/                 # Login & Registration Pages
│   │   │   └── page.tsx              # Landing Page
│   │   ├── components/               # UI Components & Navigation
│   │   └── lib/                      # API Client, Types, & Coordinates
│   ├── package.json                  # Node.js Dependencies
│   └── next.config.mjs               # Next.js Build & Proxy Config
│
├── README.md                         # Project Documentation
└── LICENSE                           # MIT License
```

---

## 📥 Installation Guide

### Prerequisites
- **Node.js**: v18.0.0 or higher
- **Python**: v3.11 or higher
- **Git**

### Step 1: Clone Repository
```bash
git clone https://github.com/anushdeotare11/Truvia.git
cd Truvia
```

### Step 2: Set Up Backend Environment
```bash
cd truvia-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### Step 3: Set Up Frontend Environment
```bash
cd ../truvia-frontend

# Install frontend dependencies
npm install
```

---

## 🔑 Environment Variables

> ⚠️ **CRITICAL SECURITY NOTE**: Never commit real environment variables or credentials to version control.

Create `.env` in `truvia-backend/`:

```env
# Server Configuration
APP_NAME="Truvia Digital Public Safety Platform"
DEBUG=True
PORT=8000
HOST="127.0.0.1"

# Database Configuration (Neon PostgreSQL)
DATABASE_URL="postgresql+asyncpg://<username>:<password>@<host>/<dbname>?sslmode=require"

# AI Credentials
GOOGLE_API_KEY="your_google_gemini_api_key_here"

# Cloud Storage (Cloudinary)
CLOUDINARY_URL="cloudinary://<api_key>:<api_secret>@<cloud_name>"
CLOUDINARY_CLOUD_NAME="your_cloud_name"
CLOUDINARY_API_KEY="your_api_key"
CLOUDINARY_API_SECRET="your_api_secret"

# Graph Database (Neo4j)
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="your_neo4j_password_here"

# Security
JWT_SECRET="your_jwt_secret_key_change_in_production"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## 🚀 Running the Project

### Running Backend Server
```bash
cd truvia-backend

# Ensure virtual environment is active
python -m uvicorn app.main:app --port 8000 --host 127.0.0.1 --reload
```
*Backend API will run at `http://127.0.0.1:8000`*

### Running Frontend Server
```bash
cd truvia-frontend

npm run dev
```
*Frontend application will run at `http://localhost:3000`*

---

## 🎬 Demo

- **Live Application**: [https://truvia.vercel.app](https://truvia.vercel.app)
- **Demo Video**: [Watch Truvia Demonstration Video Placeholder](https://youtube.com)

---

## 📖 API Documentation

FastAPI automatically generates interactive API documentation. Start the backend server and open:

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## 🔄 Workflow

```
[Citizen Submits Report] ──> [Cloud Storage / DB]
                                    │
                                    ▼
                        [Agent 1: OCR / STT Ingestion]
                                    │
                                    ▼
                        [Agent 2: RAG Threat Evaluation]
                                    │
                                    ▼
                        [Agent 4: Entity Extraction]
                                    │
                                    ▼
                        [Agent 5: Neo4j Graph Indexer]
                                    │
                                    ▼
                       [Officer Command Dashboard]
```

---

## 🔒 Security

- **Authentication**: Stateful & stateless JWT Bearer token authentication.
- **RBAC**: Strict Role-Based Access Control enforcing `Citizen`, `Officer`, and `Admin` route guards.
- **Sanitization**: Input validation via Pydantic schemas preventing SQL Injection & Cross-Site Scripting (XSS).
- **Environment Isolation**: Zero hardcoded secrets; strictly loaded via `.env` configuration.

---

## 🤝 Contributors

<a href="https://github.com/anushdeotare11/Truvia/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=anushdeotare11/Truvia" />
</a>

<div align="center">
  <br />
  <sub>Built with ❤️ for Digital Public Safety.</sub>
</div>
