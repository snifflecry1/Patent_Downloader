# Patent Fetcher – Docker Usage Guide

## 🚀 Running the Main Application

### 1. Build the main container

```bash
docker build --target final -t patent_fetcher .
```
### 2. Add .env file with variables:
    BASE_URL=<url>
    TOKEN=<token to access endpoint>

### 2. Run the main container

```bash
docker run --rm --env-file .env patent_fetcher 2001-04-25 2001-04-28
```

## 🧪 Running Tests

### 1. Build the test container

```bash
docker build --target test -t patent_test .
```

### 2. Run the tests

```bash
docker run --rm patent_test python -m pytest tests/ -v
```

