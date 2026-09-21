# SEMPL-IT V4 backend

This is the backend of SEMPL-IT, a web application designed to simplify and analyze Italian administrative documents.

The simplification pipeline uses GPT-5 mini through the OpenAI API and is orchestrated using LangChain and LangGraph.

## WebApp

The SEMPL-IT web app consists of the following repositories:

- Frontend: https://github.com/VerbACxSS/sempl-it-v4-frontend
- Backend: https://github.com/VerbACxSS/sempl-it-v4-backend
- Monitoring Module: https://github.com/VerbACxSS/sempl-it-v4-monitoring

## Getting Started

### Pre-requisites

This web application is developed using the FastAPI framework, LangChain, and LangGraph.

To run the application locally, the following software is required:

- Python 3.12

Alternatively, the application can be run using Docker. The current setup has been tested with:

- Python 3.12.12 (`python:3.12.12-slim-trixie`)
- Docker 29.8.0
- Docker Compose v5.5.1

### Configuration

The application can be configured using the following environment variables:

```text
PYTHONUNBUFFERED=1
OPENAI_API_KEY=...
MONITORING_ENDPOINT=...
MONITORING_API_KEY=...
```

`OPENAI_API_KEY` is used to access GPT-5 mini through the OpenAI API.

### Using `python` and `pip`

Create a Python virtual environment:

```shell
python3 -m venv venv
```

Activate the virtual environment:

```shell
source venv/bin/activate    # Linux/macOS
./venv/Scripts/activate     # Windows
```

Install all dependencies from `requirements.txt`:

```shell
pip install -r requirements.txt
```

Start the server:

```shell
python -m uvicorn app.app:app --host=0.0.0.0 --port=30010 --log-level=info --timeout-keep-alive=180
```

### Using `docker`

Run the application using `docker compose`:

```shell
docker compose up --build -d
```

## Usage

The web application will be running at `http://localhost:30010` by default.

Simplify and Analyze accept input texts up to 4,000 characters. Compare accepts up to 4,000 characters for each input text.

### Simplify a text

Make a POST request to the following endpoint:

```shell
curl -X POST "http://localhost:30010/api/v1/simplify/" \
-H "Content-Type: application/json" \
-d '{
    "text": "Nella fattispecie, il presente documento ha lo scopo di fornire indicazioni operative per la gestione del personale.",
    "target": "common",
    "consent": false
}'
```

### Analyze a text

Make a POST request to the following endpoint:

```shell
curl -X POST "http://localhost:30010/api/v1/analyze/text" \
-H "Content-Type: application/json" \
-d '{
    "text": "Nella fattispecie, il presente documento ha lo scopo di fornire indicazioni operative per la gestione del personale.",
    "consent": false
}'
```

### Compare two texts

Make a POST request to the following endpoint:

```shell
curl -X POST "http://localhost:30010/api/v1/analyze/comparison" \
-H "Content-Type: application/json" \
-d '{
    "text1": "Nella fattispecie, il presente documento ha lo scopo di fornire indicazioni operative per la gestione del personale.",
    "text2": "Nello specifico, questo documento descrive indicazioni operative per la gestione del personale.",
    "consent": false
}'
```

The `consent` field controls optional storage of processing results for research purposes. The service remains available when consent is set to `false`.

## Performance testing

Stress-test utilities for Simplify, Analyze, Compare, heterogeneous CSV inputs, and mixed traffic simulations are available in the backend utilities. See the dedicated stress-test README for usage details.

## Built with

- FastAPI
- LangChain / LangChain OpenAI
- LangGraph
- OpenAI API
- italian-ats-evaluator

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This contribution is a result of the research conducted within the framework of the PRIN 2020 (Progetti di Rilevante Interesse Nazionale) "VerbACxSS: on analytic verbs, complexity, synthetic verbs, and simplification. For accessibility" (Prot. 2020BJKB9M), funded by the Italian Ministero dell'Università e della Ricerca.
