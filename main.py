from fastapi import FastAPI, Request
from dotenv import load_dotenv
import logging
import pandas as pd
import io
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account

app = FastAPI()

# 環境変数をロード
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive"]
CSV_FILE_ID = "1-9-rvj5DDcYdRFZP1_2Iequ7db2kb0neNBnpOeIU4Eo"

def get_drive_service():
    """Google Drive API のサービスオブジェクトを取得"""
    # 環境変数から JSON キーファイルの内容を取得
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
    
    # 一時ファイルに書き出してから Credentials を生成する方法も可能ですが、
    # 直接 dictionary から生成できます
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)

def download_csv():
    """Google Drive から CSV ファイルをダウンロード"""
    service = get_drive_service()
    
    # Google Sheets などの場合は、export メソッドを使ってCSVとして取得する
    request = service.files().export_media(fileId=CSV_FILE_ID, mimeType="text/csv")
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file.seek(0)

    # CSV を pandas データフレームに変換
    df = pd.read_csv(file)
    return df

def upload_csv(df):
    """CSV ファイルを Google Drive にアップロード（上書き）"""
    service = get_drive_service()
    
    # DataFrame を CSV に変換（まず文字列として）
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    
    # 文字列をバイト列に変換
    csv_bytes = csv_data.encode("utf-8")
    
    # バイト列を io.BytesIO に渡す
    bytes_buffer = io.BytesIO(csv_bytes)
    
    # MediaIoBaseUpload を使用してメモリ上のデータをアップロード
    media = MediaIoBaseUpload(bytes_buffer, mimetype="text/csv", resumable=True)
    service.files().update(
        fileId=CSV_FILE_ID,
        media_body=media,
        body={"name": "trades.csv"},
        supportsAllDrives=True
    ).execute()


@app.post("/endpoint")
async def webhook_endpoint(request: Request):
    """TradingView からのリクエストを受信し、Google Drive の CSV にデータを追加"""
    params = request.query_params
    req_type = params.get("type", "N/A")
    price = params.get("price", "N/A")
    timestamp = params.get("time", "N/A")
    code = params.get("code", "N/A")

    # 受信データをログに出力
    logging.info(f"Received data: Type={req_type}, Price={price}, Time={timestamp},Code={code}")

    # Google Drive の CSV を取得
    df = download_csv()

    # 新しいデータを追加
    new_data = pd.DataFrame([[timestamp, req_type, price, code]], columns=["timestamp", "type", "price", "code"])
    df = pd.concat([df, new_data], ignore_index=True)

    # Google Drive にアップロード
    upload_csv(df)

    return {"status": "received", "type": req_type, "price": price, "time": timestamp, "code": code}
