# 🌊 OceanTrace AI
### AI-Powered Maritime Oil Spill Detection, Tracking & Investigation Platform

<p align="center">
  <strong>Turning Satellite Intelligence into Maritime Environmental Protection.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Project-OceanTrace%20AI-00B8D9?style=for-the-badge" />
  <img src="https://img.shields.io/badge/AI-PyTorch%20U--Net-EE4C2C?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Frontend-Next.js-black?style=for-the-badge&logo=next.js" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/Database-MySQL%208.0-4479A1?style=for-the-badge&logo=mysql" />
</p>

<p align="center">
  <a href="https://github.com/MUNEESHKUMARM/oceantrace">Repository</a> •
  <a href="https://github.com/MUNEESHKUMARM/oceantrace/issues">Report an Issue</a> •
  <a href="https://github.com/MUNEESHKUMARM/oceantrace/issues">Request a Feature</a>
</p>

---

## 🌍 Overview

**OceanTrace AI** is an AI-powered maritime intelligence platform designed to detect potential marine oil spills, analyse their geographical distribution, simulate environmental drift patterns, and investigate potentially associated vessels using Automatic Identification System (AIS) data.

The platform combines **Sentinel-1 Synthetic Aperture Radar (SAR)** satellite imagery, deep learning-based image segmentation, geospatial processing, environmental intelligence, drift modelling, and vessel correlation into an integrated investigation workflow.

Unlike conventional monitoring systems that focus only on identifying visible pollution, OceanTrace AI aims to support a broader investigation process — from satellite image acquisition to potential vessel-origin analysis.

### 🎯 Mission

To strengthen marine environmental monitoring through artificial intelligence, satellite remote sensing, geospatial analytics, and explainable maritime intelligence.

---

## ✨ Key Capabilities

| Capability | Description |
|---|---|
| 🛰️ Satellite Intelligence | Sentinel-1 SAR scene discovery and acquisition |
| 🧹 SAR Preprocessing | Calibration, Lee speckle filtering and dB scaling |
| 🧠 AI Oil Spill Detection | PyTorch U-Net-based image segmentation |
| 🗺️ Spill Mapping | Geospatial spill boundary extraction and polygonization |
| 🌦️ Environmental Analysis | Wind and ocean-current analysis |
| 🌊 Drift Modelling | Forward and backward particle drift simulation |
| 🚢 Live AIS Intelligence | Real-time vessel position collection through AISStream |
| 🔍 AIS Correlation | Spatial and temporal vessel correlation |
| 📊 Vessel Ranking | Explainable, weighted candidate ranking |
| 📑 Investigation Reports | Structured investigation output and evidence summaries |

---

## 🏗️ System Architecture

```text
                 OCEANTRACE AI PLATFORM
                          |
          +---------------+---------------+
          |                               |
     NEXT.JS FRONTEND                FASTAPI BACKEND
          |                               |
    Interactive Dashboard          REST API Services
          |                               |
    Geospatial Map UI              Phase 1: SAR Acquisition
          |                               |
    Analysis Pipeline              Phase 2: AI Detection
          |                               |
    Vessel Intelligence            Phase 3: Spill Mapping
          |                               |
    Investigation Reports          Phase 4: Environment
                                          |
                                    Phase 5: Drift Modelling
                                          |
                                    Phase 6: AIS Intelligence
                                          |
                                    Phase 7: Investigation
                                          |
                               +----------+----------+
                               |                     |
                         PyTorch U-Net          MySQL 8.0
                               |                     |
                         Model Checkpoints     AIS Position Data
```

---

## 🔬 Seven-Phase Intelligence Workflow

OceanTrace AI is organised into a multi-stage maritime investigation pipeline.

### Phase 1 — Sentinel-1 SAR Acquisition & Preprocessing

**Objective:** Acquire and prepare satellite radar imagery for AI-based analysis.

Key operations:

- Copernicus Data Space Ecosystem (CDSE) authentication.
- Sentinel-1 GRD scene discovery.
- SAR image acquisition through Sentinel Hub.
- Radiometric calibration / intensity scaling.
- Lee speckle noise filtering.
- Decibel-scale transformation.
- GeoTIFF generation with spatial metadata.
- SAR preview and thumbnail generation.
- Raster validation and pixel statistics.

**Output:** Processed SAR GeoTIFF, preview imagery and raster metadata.

### Phase 2 — AI-Based Oil Spill Detection

**Objective:** Identify potential oil spill regions using deep learning.

Technology:

- PyTorch
- U-Net architecture
- Binary semantic segmentation
- SAR image preprocessing
- Dice and Binary Cross-Entropy-based loss

Binary classification:

| Class | Meaning |
|---|---|
| 0 | Background / Non-oil |
| 1 | Potential Oil Spill |

The model generates segmentation masks, confidence outputs and visual overlays.

**Output:** Detection mask, confidence map, overlay and detection statistics.

### Phase 3 — Geospatial Spill Mapping

**Objective:** Convert segmentation results into geographically meaningful spill regions.

Key operations:

- Segmentation mask processing.
- Spill region extraction.
- Polygonization.
- Geographic boundary calculation.
- Spill centroid estimation.
- Area calculation.
- GeoJSON generation.
- Spill visualization.

**Output:** Spill polygons, GeoJSON, centroid, geographic bounds and area statistics.

### Phase 4 — Environmental Intelligence

**Objective:** Analyse environmental conditions around the detected spill region.

Key operations:

- Wind data analysis.
- Ocean-current analysis.
- Environmental vector field processing.
- Geographic context analysis.

**Output:** Environmental conditions and vector-field information for drift modelling.

### Phase 5 — Oil Spill Drift Modelling

**Objective:** Estimate possible spill movement and investigate potential origin areas.

Key operations:

- Lagrangian particle simulation.
- Wind-driven movement analysis.
- Ocean-current influence analysis.
- Forward drift simulation.
- Backward drift simulation.
- Probable origin-zone estimation.

**Output:** Drift trajectories, origin-zone information, GeoJSON and map visualizations.

### Phase 6 — AIS Vessel Intelligence

This phase connects vessel tracking information with the environmental investigation.

**Phase 6.1 — Live AIS Data Collection**

- AISStream WebSocket integration.
- Live vessel position collection.
- AIS message processing.
- Normalized vessel-position records.
- MySQL persistence.

**Phase 6.2 — Spatial & Temporal Correlation**

- Vessel-position analysis.
- Probable origin-zone comparison.
- Spatial correlation.
- Temporal correlation.
- Candidate vessel identification.

**Phase 6.3 — Explainable Vessel Ranking**

Candidate vessels are evaluated using configurable evidence weights.

| Evidence factor | Default weight |
|---|---:|
| Spatial proximity | 0.40 |
| Trajectory intersection | 0.35 |
| Temporal relevance | 0.15 |
| Observation evidence | 0.10 |

The ranking represents investigative prioritization, not proof of responsibility.

**Output:** Correlated vessel candidates, evidence scores and ranked results.

### Phase 7 — Investigation & Decision Support

**Objective:** Consolidate analytical results into an investigation-oriented report.

The workflow combines available evidence from:

- Satellite acquisition.
- AI detection.
- Spill mapping.
- Environmental analysis.
- Drift modelling.
- AIS correlation.
- Vessel candidate ranking.

**Output:** Structured investigation report and operational attention indicators.

---

## 🖥️ Dashboard & User Interface

The frontend provides an integrated maritime intelligence dashboard.

Main interface components:

- Top navigation panel.
- KPI monitoring bar.
- Analysis pipeline panel.
- Interactive geographic map.
- Vessel intelligence panel.
- Map layer controls.
- Bottom analysis strip.
- Processing status and error notifications.
- Demo mode for workflow demonstration.

### Map Layers

The dashboard includes layer controls for:

- Oil spill regions.
- Vessel tracks.
- Wind information.
- Ocean currents.
- Drift simulation.
- Coastal risk.
- Ports.
- Fishing zones.

---

## 🛠️ Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| Next.js | React application framework |
| React | User interface |
| TypeScript | Type-safe development |
| Tailwind CSS | Styling |
| Leaflet | Interactive maps |
| React Leaflet | React map integration |
| Recharts | Data visualization |
| Lucide React | Interface icons |

### Backend

| Technology | Purpose |
|---|---|
| Python | Core backend language |
| FastAPI | REST API framework |
| Uvicorn | ASGI application server |
| Pydantic | Request and response validation |
| SQLAlchemy | Database ORM |
| PyTorch | Deep learning |
| Rasterio | Geospatial raster processing |
| NumPy | Numerical computing |
| SciPy | Scientific processing |
| Shapely | Geospatial geometry |
| PyProj | Coordinate transformations |
| Pillow | Image processing |
| WebSockets | Real-time communication |

### Data & Intelligence

- Sentinel-1 GRD SAR imagery.
- Copernicus Data Space Ecosystem.
- Sentinel Hub.
- AISStream.
- MySQL 8.0.
- GeoTIFF.
- GeoJSON.
- PyTorch model checkpoints.

---

## 📁 Project Structure

```text
oceantrace/
│
├── app/                         # Next.js application routes
├── components/                  # Reusable UI components
│   ├── layout/                  # Dashboard layout components
│   └── map/                     # Map and visualization components
│
├── context/                     # Application state management
├── data/                        # Frontend data and mock scenarios
├── frontend/                    # Additional frontend resources
├── lib/                         # API integration and utilities
├── public/                      # Static assets
├── types/                       # TypeScript definitions
│
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI route modules
│   │   ├── core/                # Configuration and database
│   │   ├── models/              # Database models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business and AI services
│   │   └── main.py              # FastAPI application entry
│   │
│   ├── models/
│   │   └── checkpoints/         # Trained model checkpoints
│   │
│   ├── data/                    # Runtime data directories
│   ├── requirements.txt         # Python dependencies
│   ├── train_unet.py            # Model training script
│   └── test_phase*.py           # Phase verification tests
│
├── .gitignore
├── next.config.ts
├── package.json
├── README.md
└── tsconfig.json
```

*Note: Runtime datasets, generated outputs, local environments and other large files are not necessarily included in the Git repository.*

---

## ⚙️ Installation & Setup

### Prerequisites

Install the following tools before running the project:

- Node.js and npm
- Python 3.10 or compatible Python version
- MySQL Server 8.0
- Git
- Copernicus Data Space account
- AISStream API key (for live AIS collection)

### 1. Clone the Repository

```bash
git clone https://github.com/MUNEESHKUMARM/oceantrace.git
cd oceantrace
```

### 2. Configure the Frontend

Install dependencies:

```bash
npm install
```

Create a root-level `.env.local` file:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

Start the development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:3000
```

### 3. Configure the Backend

Open the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` directory:

```env
CDSE_CLIENT_ID=your_cdse_client_id
CDSE_CLIENT_SECRET=your_cdse_client_secret

CDSE_TOKEN_URL=https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
CDSE_BASE_URL=https://sh.dataspace.eu

AISSTREAM_API_KEY=your_aisstream_api_key

DATABASE_URL=mysql+pymysql://username:password@localhost:3306/oceantrace

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

Replace the example credentials with your actual credentials. Never commit your real `.env` file.

**Important:** The database must be created and configured before using database-dependent AIS features. The backend configuration defaults to a local MySQL database if no database URL is provided.

### 4. Start the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/api/docs
```

Health check:

```text
http://localhost:8000/api/health
```

### 5. Run the Complete Application

Run the frontend and backend in separate terminals.

| Service | Local URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API Documentation | http://localhost:8000/api/docs |
| Health Check | http://localhost:8000/api/health |

---

## 🔐 Environment Variables

### Backend Configuration

| Variable | Description |
|---|---|
| `CDSE_CLIENT_ID` | Copernicus OAuth client ID |
| `CDSE_CLIENT_SECRET` | Copernicus OAuth client secret |
| `CDSE_TOKEN_URL` | CDSE OAuth token endpoint |
| `CDSE_BASE_URL` | Sentinel Hub service URL |
| `CDSE_STAC_URL` | STAC catalogue URL |
| `AISSTREAM_API_KEY` | AISStream authentication key |
| `DATABASE_URL` | MySQL database connection URL |
| `MYSQL_URL` | Alternative database URL |
| `SENTINEL_SEARCH_DAYS` | Default Sentinel search window |
| `AIS_CORRELATION_SEARCH_RADIUS_KM` | Vessel correlation search radius |
| `AIS_RANKING_SPATIAL_WEIGHT` | Spatial ranking weight |
| `AIS_RANKING_INTERSECTION_WEIGHT` | Intersection ranking weight |
| `AIS_RANKING_TEMPORAL_WEIGHT` | Temporal ranking weight |
| `AIS_RANKING_OBSERVATION_WEIGHT` | Observation ranking weight |

### Frontend Configuration

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Public backend API base URL |
| `NEXT_PUBLIC_API_URL` | Alternative API URL variable |

---

## 🧠 AI Model Information

OceanTrace AI uses a PyTorch U-Net architecture for binary oil spill segmentation.

Model characteristics documented in the training implementation:

- Architecture: U-Net
- Framework: PyTorch
- Segmentation: Binary
- Input: Preprocessed SAR imagery
- Output: Oil spill probability / segmentation mask
- Loss: Combined BCE and Dice loss
- Optimizer: AdamW

The repository contains model checkpoint files under:

```text
backend/models/checkpoints/
```

Ensure that the inference service is configured to load the intended trained checkpoint.

**Dataset note:** The original satellite training dataset is not included in the repository. Obtain the appropriate dataset and configure its local path if you intend to retrain the model.

---

## 🔌 API Overview

The FastAPI backend exposes modular REST API routes.

| Module | Base route | Purpose |
|---|---|---|
| Health | `/api/health` | Backend health |
| Sentinel-1 | `/api/sentinel1` | SAR authentication, search and processing |
| Detection | `/api/detection` | AI inference and full pipeline |
| Spill Mapping | `/api/spill-mapping` | Geospatial spill mapping |
| Environment | `/api/environment` | Wind and ocean-current analysis |
| Drift | `/api/drift` | Particle drift modelling |
| AIS | `/api/ais` | Live AIS, correlation and ranking |
| Investigation | `/api/investigation` | Investigation reporting |

The API also provides `/api/v1` compatibility routes.

Explore the interactive API documentation at:

```text
http://localhost:8000/api/docs
```

---

## 🚀 Deployment Guide

OceanTrace AI has two separately deployable applications:

1. Next.js frontend.
2. FastAPI backend.

### Frontend Deployment — Vercel

1. Push the project to GitHub.
2. Import the repository into Vercel.
3. Set the project root to the repository root.
4. Configure the frontend environment variable:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain/api
```

5. Deploy the application.

### Backend Deployment — Render or Another Python Host

Configure a Python web service using:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Configure the required backend environment variables in the hosting platform.

### Deployment Considerations

- Use a managed MySQL 8.0 database for persistent AIS data.
- Configure valid CDSE credentials.
- Configure the AISStream API key if live AIS collection is required.
- Ensure model checkpoints are available to the backend.
- Provide persistent storage for generated GeoTIFF, PNG and GeoJSON files.
- Configure frontend-to-backend CORS for the production frontend domain.
- Verify memory, CPU and storage capacity before deploying PyTorch and Rasterio workloads.

**Important:** A successful frontend deployment does not automatically deploy the backend, database, model files or external data services. Each component must be configured independently.

---

## 🧪 Testing & Verification

The backend repository includes phase-oriented test scripts.

Examples:

```bash
python test_phase1.py
python test_phase2.py
python test_phase3.py
python test_phase4.py
python test_phase5.py
python test_phase7.py
```

Additional Phase 6 verification scripts are also included.

Run tests from the `backend` directory after installing dependencies and configuring the required services.

Some integration tests may require external credentials, model checkpoints, datasets or a running database.

---

## 📊 Project Goals

OceanTrace AI aims to support:

- Faster identification of potential marine oil spills.
- Satellite-based environmental monitoring.
- Geospatial spill visualization.
- Environmental drift analysis.
- Vessel activity correlation.
- Evidence-based investigation prioritization.
- Maritime environmental decision support.

---

## ⚠️ Limitations & Responsible Use

OceanTrace AI is an investigative and decision-support platform.

- AI segmentation results require validation.
- Satellite observations may contain noise, ambiguity and look-alike features.
- Drift simulations depend on the quality of environmental input data.
- AIS data may be incomplete, delayed or unavailable.
- Vessel ranking is a prioritization mechanism, not proof of causation.
- Investigation outputs should be reviewed by qualified personnel before operational or legal decisions.

The platform should not be used as the sole basis for accusing a vessel or determining legal responsibility.

---

## 🔮 Future Enhancements

Potential future development directions include:

- Multi-polarization SAR analysis.
- Improved oil spill and look-alike discrimination.
- Enhanced model validation and uncertainty estimation.
- Larger-scale Sentinel-1 scene processing.
- Advanced ocean circulation modelling.
- Historical AIS trajectory analysis.
- Automated evidence timelines.
- Model monitoring and performance evaluation.
- Scalable geospatial data storage.
- Production authentication and role-based access control.

---

## 🤝 Contributing

Contributions, ideas and technical feedback are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Test your implementation.
5. Submit a pull request.

```bash
git checkout -b feature/your-feature
git add .
git commit -m "Add: your feature"
git push origin feature/your-feature
```

---

## 📜 License

A license has not yet been specified for this repository. Until one is added, all rights remain with the copyright holder. Do not assume that the source code is available for unrestricted reuse.

---

## 👨‍💻 Project

**OceanTrace AI — AI-Powered Maritime Oil Spill Intelligence**

Developed as an AI and geospatial technology project focused on marine environmental monitoring and maritime investigation support.

<p align="center">
  <strong>🌊 Protecting Our Oceans Through Artificial Intelligence.</strong>
</p>

<p align="center">
  <a href="https://github.com/MUNEESHKUMARM/oceantrace">View OceanTrace AI on GitHub</a>
</p>
