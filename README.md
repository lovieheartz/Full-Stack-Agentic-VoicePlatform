# 🚀 Full-Stack Agentic Voice Platform

<div align="center">

![Platform Banner](https://img.shields.io/badge/AI-Powered-blue?style=for-the-badge&logo=openai)
![Microservices](https://img.shields.io/badge/Architecture-Microservices-green?style=for-the-badge&logo=kubernetes)
![Real-time](https://img.shields.io/badge/Communication-Real--time-orange?style=for-the-badge&logo=socket.io)
![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)

**An enterprise-grade AI-powered voice platform with seamless CRM integrations, intelligent call management, and unified meeting scheduling capabilities.**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Integrations](#-integrations) • [Documentation](#-documentation)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Integrations](#-integrations)
  - [CRM Systems](#-crm-integrations)
  - [Meeting Platforms](#-meeting--scheduling-integrations)
  - [Communication Services](#-communication-integrations)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [API Documentation](#-api-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

The **Full-Stack Agentic Voice Platform** is a cutting-edge, microservices-based solution that revolutionizes customer engagement through AI-powered voice interactions. Built with scalability and enterprise needs in mind, it seamlessly integrates with leading CRM systems, meeting platforms, and communication services.

### Why This Platform?

- **🤖 AI-Powered Conversations**: Leverage advanced AI agents for natural, context-aware voice interactions
- **🔗 Universal Integration**: Connect with Zoho CRM, Salesforce, HubSpot, and more
- **📅 Smart Scheduling**: Unified booking system across Calendly, Zoom, Google Calendar, and Zoho Bookings
- **📊 Real-time Analytics**: Track campaigns, leads, and call performance in real-time
- **🏢 Enterprise-Ready**: Built with microservices architecture for maximum scalability
- **🔒 Secure & Compliant**: Industry-standard security practices and OAuth 2.0 authentication

---

## ✨ Features

### Core Capabilities

- **🎙️ AI Voice Calling**
  - Intelligent conversation flows
  - Real-time transcription and sentiment analysis
  - Multi-language support
  - Custom voice personas

- **👥 Lead & Campaign Management**
  - Automated lead capture and qualification
  - Multi-channel campaign orchestration
  - Advanced lead scoring and prioritization
  - Campaign performance analytics

- **📞 Call Management**
  - Outbound and inbound call handling
  - Call recording and playback
  - Real-time call monitoring
  - Call queue management
  - DTMF and IVR support

- **🔄 Unified Integrations**
  - Bidirectional CRM synchronization
  - Automated meeting scheduling
  - Contact and lead management
  - Activity logging and tracking

- **📈 Analytics & Reporting**
  - Real-time dashboards
  - Custom report generation
  - Conversion funnel analysis
  - ROI tracking

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  • Dashboard • Campaign Manager • Call Interface • Analytics    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                  ┌───────▼───────┐
                  │  API Gateway  │
                  │    (Nginx)    │
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐ ┌─────▼──────┐ ┌───────▼────────┐
│   Auth/User    │ │  AI Call   │ │   Campaign/    │
│    Service     │ │  Service   │ │ Leads Service  │
└───────┬────────┘ └─────┬──────┘ └───────┬────────┘
        │                 │                 │
        └────────┬────────┴────────┬────────┘
                 │                 │
        ┌────────▼────────┐ ┌──────▼───────┐
        │  Integrations   │ │  MCP Server  │
        │     Service     │ │   (Agent)    │
        └────────┬────────┘ └──────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐ ┌─────▼─────┐ ┌───▼────┐
│ Zoho  │ │Salesforce │ │HubSpot │
│  CRM  │ │    CRM    │ │  CRM   │
└───────┘ └───────────┘ └────────┘
```

### Microservices Breakdown

| Service | Port | Description |
|---------|------|-------------|
| **Auth/User Service** | 8001 | User authentication, authorization, and profile management |
| **AI Call Service** | 8002 | AI-powered voice call handling and management |
| **Campaign/Leads Service** | 8003 | Campaign orchestration and lead management |
| **Integrations Service** | 8004 | Unified integration layer for external services |
| **MCP Server** | 8005 | AI agent orchestration and Model Context Protocol |
| **Frontend** | 5173 | React-based user interface |
| **API Gateway** | 80/443 | Nginx reverse proxy and load balancer |

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL, MongoDB
- **Caching**: Redis
- **Message Queue**: RabbitMQ / Kafka
- **Authentication**: JWT, OAuth 2.0
- **API Documentation**: OpenAPI/Swagger

### Frontend
- **Framework**: React 18+ with TypeScript
- **State Management**: Redux Toolkit / Zustand
- **UI Library**: Tailwind CSS, Shadcn UI
- **Build Tool**: Vite
- **API Client**: Axios / React Query

### DevOps & Infrastructure
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (v20.10+)
- **Node.js** (v18+) & **npm/pnpm**
- **Python** (v3.11+)
- **PostgreSQL** (v14+)
- **Redis** (v7+)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/lovieheartz/Full-Stack-Agentic-VoicePlatform.git
   cd Full-Stack-Agentic-VoicePlatform
   ```

2. **Set up Backend Services**
   ```bash
   cd backend

   # Copy environment variables
   cp .env.example .env

   # Update .env with your credentials
   nano .env

   # Start services with Docker Compose
   docker-compose up -d
   ```

3. **Set up Frontend**
   ```bash
   cd ../frontend

   # Copy environment variables
   cp .env.example .env

   # Update .env with backend URLs
   nano .env

   # Install dependencies
   npm install

   # Start development server
   npm run dev
   ```

4. **Access the Platform**
   - **Frontend**: http://localhost:5173
   - **API Gateway**: http://localhost:80
   - **API Documentation**: http://localhost:8001/docs

### Docker Compose Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

---

## 🔗 Integrations

### 📊 CRM Integrations

#### **Zoho CRM**
- ✅ Contact and lead management
- ✅ Real-time data synchronization
- ✅ Custom field mapping
- ✅ Automated workflow triggers
- ✅ Deal and pipeline tracking
- ✅ Activity logging (calls, meetings, notes)
- ✅ Webhook support for real-time updates

**Configuration:**
```env
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REDIRECT_URI=your_redirect_uri
ZOHO_REFRESH_TOKEN=your_refresh_token
```

#### **Salesforce**
- ✅ Lead and opportunity management
- ✅ Account and contact synchronization
- ✅ Custom object support
- ✅ Apex trigger integration
- ✅ Real-time event streaming
- ✅ Einstein AI integration
- ✅ Salesforce Flow automation

**Configuration:**
```env
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret
SALESFORCE_USERNAME=your_username
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token
SALESFORCE_DOMAIN=login.salesforce.com
```

#### **HubSpot**
- ✅ Contact and company management
- ✅ Deal pipeline synchronization
- ✅ Email tracking and engagement
- ✅ Marketing automation integration
- ✅ Custom property mapping
- ✅ Workflow and sequence automation
- ✅ Webhooks for real-time updates

**Configuration:**
```env
HUBSPOT_API_KEY=your_api_key
HUBSPOT_ACCESS_TOKEN=your_access_token
HUBSPOT_PORTAL_ID=your_portal_id
```

---

### 📅 Meeting & Scheduling Integrations

#### **Calendly**
- ✅ Automated meeting scheduling
- ✅ Calendar availability sync
- ✅ Custom booking links
- ✅ Event type management
- ✅ Invitee tracking and notifications
- ✅ Cancellation and rescheduling
- ✅ Webhook events for real-time updates
- ✅ Team scheduling and routing

**Configuration:**
```env
CALENDLY_API_KEY=your_api_key
CALENDLY_WEBHOOK_SIGNING_KEY=your_signing_key
CALENDLY_ORGANIZATION_URI=your_org_uri
```

**Features:**
- Create and manage event types
- Schedule meetings programmatically
- Retrieve invitee information
- Handle cancellations and reschedules
- Sync with Google Calendar, Outlook, iCloud

#### **Zoom**
- ✅ Instant meeting creation
- ✅ Scheduled meeting management
- ✅ Webinar hosting
- ✅ Recording management
- ✅ Participant tracking
- ✅ Meeting analytics and reports
- ✅ Breakout room management
- ✅ Waiting room control
- ✅ Live streaming integration

**Configuration:**
```env
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_WEBHOOK_SECRET_TOKEN=your_webhook_token
```

**Features:**
- Create instant and scheduled meetings
- Generate meeting links and passwords
- Manage recordings and transcripts
- Access participant reports
- Control meeting settings (waiting room, recording, etc.)

#### **Google Calendar**
- ✅ Calendar event management
- ✅ Multi-calendar support
- ✅ Availability checking
- ✅ Recurring event handling
- ✅ Attendee management
- ✅ Reminder and notification control
- ✅ Time zone intelligence
- ✅ Free/busy information

**Configuration:**
```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=your_redirect_uri
GOOGLE_REFRESH_TOKEN=your_refresh_token
```

**Features:**
- Create, update, and delete events
- Check calendar availability
- Manage multiple calendars
- Handle recurring events
- Send meeting invitations
- Sync with other calendar services

#### **Zoho Bookings**
- ✅ Service-based appointment scheduling
- ✅ Multi-staff availability management
- ✅ Custom booking fields
- ✅ Payment integration
- ✅ Automated reminders and confirmations
- ✅ Resource allocation
- ✅ Customer management
- ✅ Analytics and reporting

**Configuration:**
```env
ZOHO_BOOKINGS_CLIENT_ID=your_client_id
ZOHO_BOOKINGS_CLIENT_SECRET=your_client_secret
ZOHO_BOOKINGS_REFRESH_TOKEN=your_refresh_token
```

**Features:**
- Create and manage services
- Book appointments programmatically
- Manage staff availability
- Handle customer information
- Process payments and invoicing
- Send automated notifications

#### **Unified Booking System**
Our platform includes a **unified booking engine** that aggregates availability across all connected meeting platforms:

- 🔄 **Cross-platform availability**: Check availability across Calendly, Zoom, Google Calendar, and Zoho Bookings simultaneously
- 📊 **Smart scheduling**: Automatically find the best meeting times based on participant availability
- 🎯 **Platform routing**: Route meetings to the appropriate platform based on meeting type
- ⚡ **Real-time sync**: Instant updates across all platforms when meetings are booked or modified
- 🌐 **Time zone intelligence**: Automatic time zone detection and conversion

---

### 📞 Communication Integrations

#### **Twilio**
- ✅ Voice calls (inbound/outbound)
- ✅ SMS messaging
- ✅ Call recording and transcription
- ✅ IVR and call routing
- ✅ Conference calling
- ✅ SIP trunking
- ✅ Programmable voice APIs

**Configuration:**
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_phone_number
```

#### **Gmail**
- ✅ Email sending and receiving
- ✅ Thread management
- ✅ Label and filter automation
- ✅ Attachment handling
- ✅ Email templates
- ✅ Bulk email operations
- ✅ SMTP integration

**Configuration:**
```env
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
```

---

## 📁 Project Structure

```
Full-Stack-Agentic-VoicePlatform/
│
├── backend/                          # Backend microservices
│   ├── auth-user-service/            # Authentication & user management
│   │   ├── app/
│   │   │   ├── models/               # Database models
│   │   │   ├── routes/               # API endpoints
│   │   │   ├── services/             # Business logic
│   │   │   └── utils/                # Utilities
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── ai-call-service/              # AI voice call handling
│   │   ├── app/
│   │   │   ├── agents/               # AI agents
│   │   │   ├── models/
│   │   │   ├── routes/
│   │   │   └── services/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── campaign-leads-service/       # Campaign & lead management
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── routes/
│   │   │   └── services/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── integrations-service/         # External integrations
│   │   ├── app/
│   │   │   ├── integrations/
│   │   │   │   ├── calendly.py       # Calendly integration
│   │   │   │   ├── gmail.py          # Gmail integration
│   │   │   │   ├── google_calendar.py # Google Calendar
│   │   │   │   ├── twilio.py         # Twilio integration
│   │   │   │   ├── unified_booking.py # Unified booking system
│   │   │   │   ├── zoho.py           # Zoho CRM integration
│   │   │   │   ├── zoho_bookings.py  # Zoho Bookings
│   │   │   │   └── zoom.py           # Zoom integration
│   │   │   ├── routes/
│   │   │   └── services/
│   │   ├── CALENDLY_FLOW.md          # Calendly flow documentation
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── mcp-server/                   # Model Context Protocol server
│   │   ├── app/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── nginx/                        # API Gateway configuration
│   │   ├── nginx.conf
│   │   └── Dockerfile
│   │
│   ├── k8s/                          # Kubernetes manifests
│   │   ├── 01-namespace.yaml
│   │   ├── 02-auth-deployment.yaml
│   │   ├── 03-ai-call-deployment.yaml
│   │   ├── 04-campaign-deployment.yaml
│   │   ├── 05-mcp-deployment.yaml
│   │   ├── 06-integrations-deployment.yaml
│   │   ├── 07-nginx-deployment.yaml
│   │   └── README.md
│   │
│   ├── docker-compose.yml            # Docker Compose configuration
│   ├── .gitignore
│   └── .env.example
│
├── frontend/                         # React frontend application
│   ├── src/
│   │   ├── components/               # React components
│   │   │   ├── common/               # Reusable components
│   │   │   ├── dashboard/            # Dashboard components
│   │   │   ├── campaigns/            # Campaign management
│   │   │   ├── calls/                # Call interface
│   │   │   └── integrations/         # Integration settings
│   │   │
│   │   ├── pages/                    # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Campaigns.tsx
│   │   │   ├── Calls.tsx
│   │   │   ├── Leads.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Integrations.tsx
│   │   │   └── Settings.tsx
│   │   │
│   │   ├── services/                 # API services
│   │   │   ├── api.ts                # API client
│   │   │   ├── auth.ts               # Auth service
│   │   │   ├── campaigns.ts          # Campaign service
│   │   │   └── integrations.ts       # Integration service
│   │   │
│   │   ├── store/                    # State management
│   │   │   ├── slices/
│   │   │   └── store.ts
│   │   │
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── utils/                    # Utility functions
│   │   ├── types/                    # TypeScript types
│   │   ├── App.tsx                   # Main App component
│   │   └── main.tsx                  # Entry point
│   │
│   ├── public/                       # Static assets
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── .env.example
│   └── README.md
│
├── .gitignore
├── LICENSE
└── README.md                         # This file
```

---

## ⚙️ Configuration

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/voice_platform
MONGO_URL=mongodb://localhost:27017/voice_platform
REDIS_URL=redis://localhost:6379

# JWT Authentication
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION=86400

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Zoho CRM
ZOHO_CLIENT_ID=your_zoho_client_id
ZOHO_CLIENT_SECRET=your_zoho_client_secret
ZOHO_REFRESH_TOKEN=your_zoho_refresh_token

# Salesforce
SALESFORCE_CLIENT_ID=your_sf_client_id
SALESFORCE_CLIENT_SECRET=your_sf_client_secret
SALESFORCE_USERNAME=your_sf_username
SALESFORCE_PASSWORD=your_sf_password
SALESFORCE_SECURITY_TOKEN=your_sf_token

# HubSpot
HUBSPOT_API_KEY=your_hubspot_api_key
HUBSPOT_ACCESS_TOKEN=your_hubspot_token

# Calendly
CALENDLY_API_KEY=your_calendly_api_key
CALENDLY_WEBHOOK_SIGNING_KEY=your_calendly_signing_key

# Zoom
ZOOM_ACCOUNT_ID=your_zoom_account_id
ZOOM_CLIENT_ID=your_zoom_client_id
ZOOM_CLIENT_SECRET=your_zoom_client_secret

# Google Calendar
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token

# Zoho Bookings
ZOHO_BOOKINGS_CLIENT_ID=your_bookings_client_id
ZOHO_BOOKINGS_CLIENT_SECRET=your_bookings_client_secret
ZOHO_BOOKINGS_REFRESH_TOKEN=your_bookings_refresh_token

# Gmail
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token

# AI Services
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Environment
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
```

### Frontend Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
# API URLs
VITE_API_BASE_URL=http://localhost:80/api
VITE_WS_URL=ws://localhost:80/ws

# Authentication
VITE_JWT_STORAGE_KEY=voice_platform_token

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_INTEGRATIONS=true

# Environment
VITE_ENVIRONMENT=production
```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# Scale specific services
docker-compose up -d --scale ai-call-service=3

# View logs
docker-compose logs -f [service-name]

# Stop all services
docker-compose down
```

### Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f backend/k8s/

# Check deployment status
kubectl get pods -n voice-platform

# Scale deployments
kubectl scale deployment ai-call-service --replicas=3 -n voice-platform

# View logs
kubectl logs -f deployment/ai-call-service -n voice-platform

# Delete all resources
kubectl delete namespace voice-platform
```

### Production Checklist

- [ ] Update all environment variables with production credentials
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure database backups
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Implement rate limiting
- [ ] Set up CI/CD pipelines
- [ ] Configure auto-scaling policies
- [ ] Enable database connection pooling
- [ ] Implement health checks
- [ ] Set up disaster recovery procedures

---

## 📚 API Documentation

### Authentication

All API requests require a JWT token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Endpoints

| Service | Endpoint | Description |
|---------|----------|-------------|
| Auth | `POST /api/auth/login` | User login |
| Auth | `POST /api/auth/register` | User registration |
| Auth | `GET /api/auth/me` | Get current user |
| Calls | `POST /api/calls/initiate` | Initiate a call |
| Calls | `GET /api/calls/{call_id}` | Get call details |
| Campaigns | `POST /api/campaigns` | Create campaign |
| Campaigns | `GET /api/campaigns` | List campaigns |
| Leads | `POST /api/leads` | Create lead |
| Leads | `GET /api/leads` | List leads |
| Integrations | `GET /api/integrations/crm/contacts` | Get CRM contacts |
| Integrations | `POST /api/integrations/meetings/schedule` | Schedule meeting |

### Interactive API Docs

Visit the following URLs when services are running:

- Auth Service: http://localhost:8001/docs
- AI Call Service: http://localhost:8002/docs
- Campaign Service: http://localhost:8003/docs
- Integrations Service: http://localhost:8004/docs

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific service tests
pytest auth-user-service/tests/

# Run integration tests
pytest -m integration
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint and Prettier for TypeScript/React code
- Write unit tests for new features
- Update documentation for API changes
- Keep commit messages clear and descriptive

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: Services fail to start with Docker Compose
```bash
# Check logs
docker-compose logs [service-name]

# Rebuild containers
docker-compose down && docker-compose up -d --build
```

**Issue**: Database connection errors
```bash
# Check database is running
docker-compose ps

# Verify environment variables
cat .env | grep DATABASE_URL
```

**Issue**: Integration authentication fails
- Verify API credentials in `.env`
- Check token expiration
- Ensure correct redirect URIs are configured

---

## 📊 Monitoring & Observability

### Metrics

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

### Logging

- **Kibana**: http://localhost:5601

### Health Checks

```bash
# Check service health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

---

## 📖 Additional Resources

- [Architecture Deep Dive](./backend/docs/ARCHITECTURE.md)
- [API Reference](./backend/docs/API.md)
- [Integration Guides](./backend/integrations-service/CALENDLY_FLOW.md)
- [Deployment Guide](./backend/k8s/README.md)
- [Security Best Practices](./docs/SECURITY.md)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 💬 Support

For support, please:
- Open an issue on [GitHub Issues](https://github.com/lovieheartz/Full-Stack-Agentic-VoicePlatform/issues)
- Contact us at support@voiceplatform.com
- Join our [Discord community](https://discord.gg/voiceplatform)

---

## 🙏 Acknowledgments

- Built with FastAPI, React, and modern microservices architecture
- Integrated with leading CRM and meeting platforms
- Powered by AI for intelligent voice interactions

---

<div align="center">

**Built with ❤️ by the Voice Platform Team**

[⭐ Star us on GitHub](https://github.com/lovieheartz/Full-Stack-Agentic-VoicePlatform) • [🐛 Report Bug](https://github.com/lovieheartz/Full-Stack-Agentic-VoicePlatform/issues) • [💡 Request Feature](https://github.com/lovieheartz/Full-Stack-Agentic-VoicePlatform/issues)

</div>
