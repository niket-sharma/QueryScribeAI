# QueryScribe AI 📝

QueryScribe AI is a production-ready, multi-agent system that translates natural language questions into executable SQL queries with detailed explanations. Built with enterprise-grade features including comprehensive error handling, async operations, and security validation.

## 🚀 Key Features

- **Multi-Agent Architecture**: Specialized agents for analysis, generation, and explanation
- **Multiple LLM Providers**: Support for Google Gemini, OpenAI GPT-4, and Anthropic Claude
- **Async Processing**: Parallel execution for improved performance
- **Comprehensive Validation**: SQL safety checks and syntax validation
- **Enterprise Ready**: Structured logging, error handling, and monitoring endpoints
- **Type Safety**: Full type hints throughout the codebase
- **Configurable**: Environment-based configuration with validation

## 🏗️ Architecture

### Multi-Agent Pipeline

1. **Schema & Intent Analyzer** → Analyzes database schema and user intent
2. **SQL Generator** → Creates optimized SQL queries from structured plans
3. **Explainer** → Provides business-friendly explanations
4. **Validator** → Ensures query safety and syntax correctness

### Project Structure
```
QueryScribeAI/
├── app/                    # FastAPI application
│   ├── main.py            # API endpoints and middleware
│   └── models.py          # Pydantic data models
├── agents/                # LLM agent implementations
│   ├── analyzer_agent.py  # Schema & intent analysis
│   ├── generator_agent.py # SQL generation
│   └── explainer_agent.py # Query explanation
├── core/                  # Core utilities
│   ├── config.py          # Configuration management
│   └── llm.py             # LLM initialization
├── db/                    # Database utilities
│   └── validator.py       # SQL validation
├── data/                  # Sample data
│   └── sample_schema.sql  # Example database schema
└── main.py               # Application entry point
```

## 🛠️ Tech Stack

- **Backend**: FastAPI with async support
- **LLM Integration**: LangChain with multiple provider support
- **Database**: SQLAlchemy with connection pooling
- **Configuration**: Pydantic Settings with validation
- **Type Safety**: Full type hints with mypy support

## 📦 Installation & Setup

### 1. Clone and Setup Environment

```bash
git clone <your-repo-url>
cd QueryScribeAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
```

### 3. Environment Configuration

Configure your `.env` file with the following settings:

```env
# Choose your LLM provider
LLM_PROVIDER=google  # Options: google, openai, anthropic

# Add your API key (only one required)
GOOGLE_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Optional: Database for validation
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Model configuration (optional)
GOOGLE_MODEL=gemini-pro
OPENAI_MODEL=gpt-4-turbo-preview
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Application settings
LLM_TEMPERATURE=0.0
MAX_RETRIES=3
REQUEST_TIMEOUT=120
```

### 4. Run the Application

```bash
# Start the server
python main.py

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Core Endpoints

#### Generate SQL Query
```http
POST /generate-sql
Content-Type: application/json

{
  "question": "Show me all customers who made orders in the last 30 days",
  "db_schema": "CREATE TABLE customers (...)"  // Optional
}
```

**Response:**
```json
{
  "natural_language_question": "Show me all customers...",
  "sql_query": "SELECT DISTINCT c.* FROM customers c...",
  "explanation": "This query finds all customers who...",
  "validation_status": "Success",
  "validation_message": "SQL syntax validation successful",
  "execution_time_ms": 1234.56,
  "plan": {
    "tables": ["customers", "orders"],
    "joins": ["customers.id = orders.customer_id"]
  }
}
```

#### Health Check
```http
GET /health
```

#### Configuration Info
```http
GET /config
GET /llm-info
```

## 🎯 Usage Examples

### Basic Usage
```python
import requests

response = requests.post('http://localhost:8000/generate-sql', json={
    'question': 'What are the top 5 products by sales?'
})

result = response.json()
print(f"SQL: {result['sql_query']}")
print(f"Explanation: {result['explanation']}")
```

### With Custom Schema
```python
schema = """
CREATE TABLE products (id INT, name VARCHAR, price DECIMAL);
CREATE TABLE sales (id INT, product_id INT, quantity INT);
"""

response = requests.post('http://localhost:8000/generate-sql', json={
    'question': 'Which products have sold more than 100 units?',
    'db_schema': schema
})
```

## 🔧 Configuration

### LLM Providers

#### Google Gemini (Default)
```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your_key
GOOGLE_MODEL=gemini-pro
```

#### OpenAI GPT-4
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4-turbo-preview
```

#### Anthropic Claude
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

### Database Validation
Configure `DATABASE_URL` for SQL validation:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

## 🔒 Security Features

- **SQL Injection Protection**: Pattern-based dangerous query detection
- **Read-Only Validation**: Transactions are always rolled back
- **Input Validation**: Comprehensive request validation with Pydantic
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Request Timeouts**: Configurable timeouts for LLM calls

## 📊 Monitoring & Observability

- **Structured Logging**: JSON-formatted logs with request tracking
- **Performance Metrics**: Execution time tracking
- **Health Endpoints**: `/health` for service monitoring
- **Configuration Endpoints**: `/config` and `/llm-info` for debugging

## 🧪 Development

### Code Quality Tools
```bash
# Type checking
mypy .

# Code formatting
black .

# Linting
flake8 .

# Testing
pytest tests/
```

### Development Mode
```bash
# Run with auto-reload
python main.py

# Or with custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## 🚀 Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables for Production
```env
LLM_PROVIDER=your_provider
YOUR_PROVIDER_API_KEY=your_production_key
DATABASE_URL=your_production_db_url
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with proper type hints and tests
4. Run quality checks: `black .`, `mypy .`, `flake8 .`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and feature requests, please create an issue in the GitHub repository.

---

**QueryScribe AI** - Transforming natural language into SQL with confidence and clarity.