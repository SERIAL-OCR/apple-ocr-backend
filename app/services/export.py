import os
from typing import List, Tuple
from openpyxl import Workbook

from app.db import fetch_serials


def generate_excel(file_path: str) -> str:
    rows = fetch_serials()

    wb = Workbook()
    ws = wb.active
    ws.title = "Serials"

    ws.append(["ID", "Timestamp (UTC)", "Serial", "Device Type", "Confidence"]) 
    for row in rows:
        ws.append(list(row))

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    wb.save(file_path)
    return file_path
