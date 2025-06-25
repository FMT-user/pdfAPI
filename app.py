# requirements.txt
# fastapi
# uvicorn
# pdfminer.six
# pandas
# python-multipart
# requests

# app.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pdfminer.high_level import extract_text
from pathlib import Path
import pandas as pd
import os
import requests
import logging

app = FastAPI()

# ✅ Correct GitHub API and raw content URLs
GITHUB_API_URL = 'https://api.github.com/repos/FMT-user/pdfparser/contents/pdfFiles?ref=pdfFiles'
RAW_GITHUB_URL_BASE = 'https://raw.githubusercontent.com/FMT-user/pdfparser/pdfFiles/pdfFiles/'

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this env var if repo is private

def list_pdfs_from_github():
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    response = requests.get(GITHUB_API_URL, headers=headers)
    if response.status_code == 200:
        files = response.json()
        pdf_files = [file['name'] for file in files if file['name'].endswith('.pdf')]
        return pdf_files
    else:
        # Log the response content for debugging
        logging.error(f"GitHub API response: {response.text}")
        raise Exception(f"Failed to fetch file list from GitHub. Status: {response.status_code}, Response: {response.text}")

def download_pdf_from_github(filename):
    url = f"{RAW_GITHUB_URL_BASE}{filename}"
    headers = {"Accept": "application/pdf"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("application/pdf"):
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    else:
        raise Exception(f"Failed to download {filename} from GitHub. Status code: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")

def parse_pdf(filename):
    """Extract text from a PDF and return as string."""
    try:
        text = extract_text(filename)
        return text
    except Exception as e:
        raise Exception(f"Failed to parse PDF {filename}: {str(e)}")

@app.get("/parse_github_pdfs/")
def parse_github_pdfs():
    consolidated_data = []
    results = []
    try:
        pdf_files = list_pdfs_from_github()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    for filename in pdf_files:
        try:
            downloaded_path = download_pdf_from_github(filename)
            text = parse_pdf(downloaded_path)
            consolidated_data.append({
                "file": filename,
                "text": text
            })
            results.append({
                "file": filename,
                "status": "parsed"
            })
        except Exception as e:
            results.append({"file": filename, "error": str(e)})

    # Save consolidated data to a single JSON file
    consolidated_json_path = "consolidated_parsed_data.json"
    try:
        pd.DataFrame(consolidated_data).to_json(consolidated_json_path, orient="records", indent=2)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to save consolidated JSON: {str(e)}"})

    return {
        "parsed_files": results,
        "consolidated_json": consolidated_json_path
    }

# Dockerfile
# ---------------------------
# FROM python:3.11-slim
# WORKDIR /app
# COPY . .
# RUN pip install --no-cache-dir -r requirements.txt
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]