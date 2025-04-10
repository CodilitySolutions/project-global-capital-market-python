# 🌍 Project: Global Capital Market Property Analyzer (Python)

This project analyzes real estate property cost trends using web scraping, Google Street View imagery, and OpenAI-powered socioeconomic analysis. It fetches property listings from top real estate platforms and generates insights including average cost per square meter, neighborhood classification, and socio-economic demographics.

---

## 📦 Tech Stack

- Python 3.10+
- OpenAI Assistant API
- Google Maps / Street View API
- SERP API (for scraping search results)
- BeautifulSoup & Requests (for HTML parsing)
- MSSQL (via `pymssql`)
- Docker-compatible

---

## 🛠 Installation (Local)

### 1. Clone the Repo

```bash
git clone https://github.com/your-username/project-global-capital-market-python.git
cd project-global-capital-market-python
```

### 2. Set Environment Variables

Copy the sample file to a new `.env` file:

```bash
cp .env.sample .env
```

Then update the values in `.env` with your actual credentials:

```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=eu-west-1
S3_BUCKET_NAME=your-bucket-name

DB_HOST=your-db-host
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASS=your-db-password

OPENAI_API_KEY=your-openai-key
CHATGPT_MODEL=gpt-4o

GOOGLE_MAP_API_KEY=your-google-maps-key
CARD_API_KEY=your-card-api-key

SERP_API_KEY=your-serpapi-key
```

### 3. Install Dependencies

```bash
pip3 install -r requirements.txt
```

---

## ▶️ Run the Project

```bash
python3 main.py
```

---

## 🐳 Docker Support (Recommended for Production)

### 1. Build Docker Image

```bash
docker build -t property-analyzer .
```

### 2. Run Container

```bash
docker run --env-file .env property-analyzer
```

---

## 📁 Output & Logs

All logs and scraped data are stored in the `/log/` directory:

- `app.log`: Application logs
- `scraped_*.html`: Raw scraped HTML pages
- `openai_*.txt`: Processed results from OpenAI

---

## ✅ Features

- Intelligent property listing scraping from trusted sources
- Smart filtering for Flats, Apartments, Houses, and Commercial properties
- OpenAI-powered cost + people type + neighborhood classification
- Google Street View integration for visual property analysis
- MSSQL database support for result storage
- Lightweight & Docker-optimized

---

## 🩹 Cleanup

To reduce Docker image size:
- Remove unused dependencies from `requirements.txt`
- Use `python:3.10-slim` base image
- Use `--no-cache-dir` during pip install

---

## 📬 Questions?

Feel free to reach out or create an issue if you need help with deployment, Docker, or extending functionality!

---
