"""
Export routes — generate MoneyForward CSV exports.
"""

import csv
from datetime import datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from ..database import get_session
from ..models import Receipt

router = APIRouter()

# MoneyForward スモールビジネス import column mapping
# 計算対象,日付,内容,金額（円）,内税／外税,税率,勘定科目,税区分,補助科目,部門,メモ,仕訳メモ,管理番号

CATEGORY_TO_MONEYFORWARD = {
    "SHO": "消耗品費",
    "KTL": "接待交際費",
    "RND": "研究開発費",
    "TRS": "旅費交通費",
    "LOC": "旅費交通費",
    "ACC": "旅費交通費",
    "WEL": "福利厚生費",
    "COM": "通信費",
    "MTG": "会議費",
    "EQP": "工具器具備品",
    "ADV": "広告宣伝費",
    "FEE": "支払手数料",
}


@router.get("/export/moneyforward")
def export_moneyforward(
    fy: str,
    month: Optional[int] = None,
    session: Session = Depends(get_session),
):
    """
    Export receipts as MoneyForward スモールビジネス CSV.

    Args:
        fy: Fiscal year (e.g., "FY2027")
        month: Optional month (1-12) to filter

    Returns CSV file with proper MoneyForward column format.
    """
    # Normalize FY format
    fy_value = fy if fy.startswith("FY") else f"FY{fy}"

    # Build query
    query = select(Receipt).where(Receipt.fiscal_year == fy_value)

    # Filter by month if provided
    if month:
        if not 1 <= month <= 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        # Filter by receipt_date month
        # This is a simplified filter - SQLite strftime might be needed
        results = session.exec(query).all()
        results = [r for r in results if r.receipt_date.month == month]
    else:
        results = session.exec(query).all()

    if not results:
        raise HTTPException(status_code=404, detail="No receipts found for specified period")

    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write header row (MoneyForward format)
    header = [
        "計算対象",
        "日付",
        "内容",
        "金額（円）",
        "内税／外税",
        "税率",
        "勘定科目",
        "税区分",
        "補助科目",
        "部門",
        "メモ",
        "仕訳メモ",
        "管理番号",
    ]
    writer.writerow(header)

    # Write data rows
    for receipt in results:
        row = [
            "1",  # 計算対象 - always 1 (include in calculation)
            receipt.receipt_date.strftime("%Y/%m/%d"),  # 日付
            receipt.vendor_name,  # 内容
            receipt.amount_jpy,  # 金額（円）
            "外税",  # 内税／外税
            "10%",  # 税率 - TODO: detect 8% for food items
            CATEGORY_TO_MONEYFORWARD.get(receipt.category_code, "その他"),  # 勘定科目
            "課税仕入",  # 税区分
            "",  # 補助科目
            "",  # 部門
            receipt.registration_number or "",  # メモ (registration number)
            receipt.notes or "",  # 仕訳メモ
            receipt.filename.replace(".pdf", ""),  # 管理番号 (filename without extension)
        ]
        writer.writerow(row)

    # Prepare response
    csv_data = output.getvalue()
    filename = f"MF_{fy_value}_{month:02d}_Month.csv" if month else f"MF_{fy_value}_All.csv"

    return StreamingResponse(
        iter([csv_data.encode("utf-8")]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/export/summary")
def export_summary(
    fy: str,
    session: Session = Depends(get_session),
):
    """
    Get summary statistics for a fiscal year.
    """
    fy_value = fy if fy.startswith("FY") else f"FY{fy}"

    query = select(Receipt).where(Receipt.fiscal_year == fy_value)
    results = session.exec(query).all()

    # Calculate totals by category
    category_totals = {}
    total_amount = 0

    for receipt in results:
        cat = receipt.category_code
        category_totals[cat] = category_totals.get(cat, 0) + receipt.amount_jpy
        total_amount += receipt.amount_jpy

    return {
        "fiscal_year": fy_value,
        "total_receipts": len(results),
        "total_amount": total_amount,
        "category_breakdown": category_totals,
    }
