"""
start.py — Điểm entry đơn giản để chạy FastAPI với đúng sys.path.
Chạy: python start.py
"""
import sys
import os

# Thêm backend-python vào sys.path để tất cả modules tìm thấy nhau
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
