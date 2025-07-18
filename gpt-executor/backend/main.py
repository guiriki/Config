from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import subprocess
import os
import uuid
import re
from datetime import datetime
import pandas as pd
import fitz  # PyMuPDF
import json
import yaml
import xml.etree.ElementTree as ET
import docx

app = FastAPI()

# Diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.environ.get("VIRTUAL_ENV", "/opt/venv") + "/bin/python"
CODE_DIR = os.path.join(BASE_DIR, "executions")
LOG_DIR = os.path.join(BASE_DIR, "logs")
WORKSPACE_DIR = "/mnt/workspace"

# Garantir que diretórios existam
os.makedirs(CODE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(WORKSPACE_DIR, exist_ok=True)

if not os.path.exists(VENV_PYTHON):
    raise RuntimeError(f"[ERRO] Python virtualenv não encontrado em: {VENV_PYTHON}")

# Models
class CodeRequest(BaseModel):
    language: str
    code: str

class FileAnalysisRequest(BaseModel):
    filename: str

# Logging
def log_execution(language: str, code: str, result: dict, installed_packages=None):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_DIR, f"exec_{timestamp}.{language}.log")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"# Language: {language}\n\n# Code:\n{code}\n")
        if installed_packages:
            f.write(f"\n# Installed Packages:\n{installed_packages}\n")
        f.write(f"\n# Result:\n{result}\n")
    return log_file

# Instalação automática de pacotes Python
def install_missing_packages(code: str):
    matches = re.findall(r'^\s*(?:import|from)\s+([a-zA-Z0-9_]+)', code, re.MULTILINE)
    required_packages = set(matches)
    installed = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            subprocess.run([VENV_PYTHON, "-m", "pip", "install", pkg], check=True)
            installed.append(pkg)
    return installed

# Execução de código externo
@app.post("/execute")
async def execute_code(req: CodeRequest):
    file_id = str(uuid.uuid4())
    filename = os.path.join(CODE_DIR, f"{file_id}.{req.language}")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(req.code)

    installed_packages = []

    if req.language == "py":
        try:
            installed_packages = install_missing_packages(req.code)
        except subprocess.CalledProcessError as e:
            error = {"error": f"Erro ao instalar pacotes: {e.stderr}"}
            log_path = log_execution(req.language, req.code, error, installed_packages)
            return JSONResponse(status_code=500, content={**error, "log_path": log_path})
        cmd = [VENV_PYTHON, filename]

    elif req.language == "js":
        cmd = ["node", filename]
    elif req.language == "sh":
        cmd = ["bash", filename]
    elif req.language == "php":
        cmd = ["php", filename]
    elif req.language == "java":
        class_name = file_id
        java_file = filename.replace(".java", "")
        compile_cmd = ["javac", filename]
        run_cmd = ["java", "-cp", CODE_DIR, class_name]
        try:
            subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
            result = subprocess.run(run_cmd, capture_output=True, text=True)
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "packages_installed": installed_packages
            }
            log_path = log_execution(req.language, req.code, output, installed_packages)
            output["log_path"] = log_path
            return output
        except Exception as e:
            error = {"error": str(e)}
            log_path = log_execution(req.language, req.code, error, installed_packages)
            return JSONResponse(status_code=500, content={**error, "log_path": log_path})

    else:
        raise HTTPException(status_code=400, detail="Unsupported language")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "packages_installed": installed_packages
        }
        log_path = log_execution(req.language, req.code, output, installed_packages)
        output["log_path"] = log_path
        return output
    except Exception as e:
        error = {"error": str(e)}
        log_path = log_execution(req.language, req.code, error, installed_packages)
        return JSONResponse(status_code=500, content={**error, "log_path": log_path})

# Listagem de arquivos
@app.get("/files")
def list_workspace_files():
    try:
        return {"files": os.listdir(WORKSPACE_DIR)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Leitura de conteúdo de arquivos
@app.get("/files/{filename}")
def read_workspace_file(filename: str):
    filepath = os.path.join(WORKSPACE_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[-1].lower()

    try:
        if ext in [".txt", ".csv"]:
            with open(filepath, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        elif ext == ".xlsx":
            df = pd.read_excel(filepath)
            return {"columns": df.columns.tolist(), "preview": df.head(10).to_dict(orient="records")}
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                return {"data": json.load(f)}
        elif ext in [".yaml", ".yml"]:
            with open(filepath, "r", encoding="utf-8") as f:
                return {"data": yaml.safe_load(f)}
        elif ext == ".xml":
            tree = ET.parse(filepath)
            root = tree.getroot()
            return {"root_tag": root.tag, "children": [child.tag for child in root]}
        elif ext == ".docx":
            doc = docx.Document(filepath)
            text = "\n".join([p.text for p in doc.paragraphs])
            return {"text": text[:2000]}
        elif ext == ".pdf":
            text = ""
            with fitz.open(filepath) as pdf:
                for page in pdf:
                    text += page.get_text()
            return {"text": text[:2000]}
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Análise básica de arquivos
@app.post("/analyze")
def analyze_workspace_file(req: FileAnalysisRequest):
    filepath = os.path.join(WORKSPACE_DIR, req.filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(req.filename)[-1].lower()
    try:
        if ext == ".xlsx":
            df = pd.read_excel(filepath)
            return {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "describe": df.describe().to_dict()
            }
        elif ext == ".pdf":
            text = ""
            with fitz.open(filepath) as pdf:
                for page in pdf:
                    text += page.get_text()
            return {"characters": len(text), "preview": text[:1000]}
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload de arquivos
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    destination = os.path.join(WORKSPACE_DIR, file.filename)
    with open(destination, "wb") as buffer:
        buffer.write(await file.read())
    return {"filename": file.filename, "path": destination}
