# Secure Data Pipeline

A comprehensive secure data processing pipeline with React frontend and Flask backend, featuring compliance monitoring, data integrity checks, and multi-processing capabilities.

## 📁 Project Structure

```
practicum/
├── frontend/          # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── node_modules/
│   └── package.json
├── backend/           # Flask Python backend
│   ├── src/
│   ├── app.py
│   ├── requirements.txt
│   ├── venv/
│   └── tests/
├── docs/             # Documentation
└── start-setup.sh    # Setup script
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm 9+
- Python 3.8+
- PostgreSQL (via Docker)

### Installation

1. **Run setup script:**

   ```bash
   ./start-setup.sh
   ```

2. **Start PostgreSQL:**

   ```bash
   docker-compose up -d postgres
   ```

3. **Setup database:**

   ```bash
   cd backend && python setup/setup_database.py
   ```

4. **Start development servers (in separate terminals):**

   ```bash
   # Terminal 1: Frontend
   cd frontend && npm run dev

   # Terminal 2: Backend
   cd backend && ./start_dashboard.sh
   ```

This will start:

- Frontend: http://localhost:3007
- Backend: http://localhost:5001

## 🏗️ Architecture

### Frontend (React + TypeScript)

- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: TanStack Query
- **Routing**: React Router
- **Build Tool**: Vite

### Backend (Flask + Python)

- **Framework**: Flask with PostgreSQL
- **Processing**: Spark, Storm, Flink
- **Monitoring**: Data integrity monitoring
- **Compliance**: GDPR/HIPAA compliance rules

## 📝 Available Scripts

### Frontend

- `cd frontend && npm run dev` - Start React dev server
- `cd frontend && npm run build` - Build for production
- `cd frontend && npm run lint` - Run ESLint

### Backend

- `cd backend && ./start_dashboard.sh` - Start Flask server with dashboard
- `cd backend && python app.py` - Start Flask server (alternative)
- `cd backend && python -m pytest` - Run Python tests

## 🔒 Security & Compliance

- **Data Encryption**: End-to-end encryption for sensitive data
- **Compliance Rules**: GDPR and HIPAA compliance monitoring
- **Audit Logging**: Complete audit trail for all operations
- **Role-based Access**: Multi-level user permissions

## 📊 Features

### Data Processing

- **Batch Processing**: Large dataset processing with Apache Spark
- **Stream Processing**: Real-time data with Apache Storm
- **Hybrid Processing**: Combined batch and stream with Apache Flink

### Monitoring & Reports

- **Real-time Dashboard**: Live system status and metrics
- **Data Integrity**: Automated integrity checks and alerts
- **Compliance Reports**: Detailed compliance violation reports
- **Audit Trail**: Complete operation history

### File Management

- **Secure Upload**: Encrypted file upload with validation
- **Processing Queue**: Async job processing with status tracking
- **Data Validation**: Schema validation and compliance checking

## 🛠️ Development

### Adding New Features

1. **Frontend**: Add components in `frontend/src/components/`
2. **Backend**: Add routes in `backend/app.py` or create new modules
3. **API**: Update types in `frontend/src/types/index.ts`
4. **Database**: Add migrations in `backend/sql/`

### Environment Variables

Create `.env` files in both frontend and backend directories:

**Backend (.env):**

```
DATABASE_URL=postgresql://admin:password@localhost:5433/compliance_db
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

**Frontend (.env):**

```
VITE_API_URL=http://localhost:5000
```

## 📚 Documentation

- [Architecture Diagrams](docs/architecture_diagrams.md)
- [Implementation Setup](docs/implementation_setup.md)
- [Compliance Framework](docs/research_evaluation_framework.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
