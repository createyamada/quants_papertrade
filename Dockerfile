# FastAPI の Dockerfile
FROM python:3.9

WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt .
COPY main.py .

# 必要なライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI を実行
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
