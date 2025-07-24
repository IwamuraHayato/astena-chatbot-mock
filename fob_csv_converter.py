#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定資産奉行インポート用CSV変換モジュール
"""

import pandas as pd
import re
from datetime import datetime
from typing import Dict, Any, Optional

# マスタデータ辞書
ACCOUNT_MASTER = {
    # 勘定科目 → (資産種別コード, 償却方法CD)
    "建物": ("1", "1"),  # 建物、定額法
    "建物附属設備": ("2", "1"),  # 建物附属設備、定額法
    "構築物": ("3", "1"),  # 構築物、定額法
    "機械装置": ("4", "2"),  # 機械装置、定率法
    "車両運搬具": ("5", "2"),  # 車両運搬具、定率法
    "工具器具備品": ("6", "2"),  # 工具器具備品、定率法
    "器具備品": ("6", "2"),  # 器具備品、定率法
    "備品": ("6", "2"),  # 備品、定率法
    "ソフトウェア": ("7", "1"),  # ソフトウェア、定額法
    "リース資産": ("8", "1"),  # リース資産、定額法
    "その他": ("9", "2"),  # その他、定率法
}

DEPARTMENT_MASTER = {
    # 部門名 → 部門コード
    "本社": "1000",
    "営業部": "2000", 
    "開発部": "3000",
    "総務部": "4000",
    "経理部": "5000",
    "人事部": "6000",
    "情報システム部": "7000",
    "その他": "9999",
}

LOCATION_MASTER = {
    # 設置場所 → 設置場所コード
    "本社": "1000",
    "東京オフィス": "1001",
    "大阪オフィス": "1002", 
    "名古屋オフィス": "1003",
    "福岡オフィス": "1004",
    "在宅勤務": "9000",
    "その他": "9999",
}

COST_CATEGORY_MASTER = {
    # 費目区分
    "本社": "1000",
    "営業": "2000",
    "開発": "3000",
    "その他": "9999",
}


def extract_numeric_value(amount_str: str) -> int:
    """
    金額文字列から数値を抽出
    例: "1,680,000円" → 1680000
    """
    if not amount_str:
        return 0
    
    # 数字とカンマのみを抽出
    numeric_str = re.sub(r'[^\d,]', '', str(amount_str))
    numeric_str = numeric_str.replace(',', '')
    
    try:
        return int(numeric_str)
    except ValueError:
        return 0


def extract_useful_life(life_str: str) -> int:
    """
    耐用年数文字列から数値を抽出
    例: "5年" → 5
    """
    if not life_str:
        return 0
    
    # 数字のみを抽出
    numeric_str = re.sub(r'[^\d]', '', str(life_str))
    
    try:
        return int(numeric_str)
    except ValueError:
        return 0


def get_account_info(account_name: str) -> tuple[str, str]:
    """
    勘定科目名から資産種別コードと償却方法CDを取得
    """
    if not account_name:
        return ("9", "2")  # デフォルト: その他、定率法
    
    # 完全一致を優先
    if account_name in ACCOUNT_MASTER:
        return ACCOUNT_MASTER[account_name]
    
    # 部分一致での検索
    for key, value in ACCOUNT_MASTER.items():
        if key in account_name or account_name in key:
            return value
    
    # マッチしない場合のデフォルト
    return ("9", "2")


def get_department_code(department_name: str = "本社") -> str:
    """部門コードを取得"""
    return DEPARTMENT_MASTER.get(department_name, "1000")


def get_location_code(location_name: str = "本社") -> str:
    """設置場所コードを取得"""
    return LOCATION_MASTER.get(location_name, "1000")


def generate_asset_code(index: int, prefix: str = "FA") -> str:
    """
    資産コードを生成
    例: FA-001, FA-002, ...
    """
    return f"{prefix}-{index:03d}"


def convert_to_fob_csv(df: pd.DataFrame, 
                      department: str = "本社",
                      location: str = "本社",
                      acquisition_date: Optional[str] = None) -> pd.DataFrame:
    """
    固定資産判定結果のDataFrameを固定資産奉行インポート用CSVフォーマットに変換
    
    Parameters:
    - df: 固定資産判定結果のDataFrame
    - department: 部門名（デフォルト: "本社"）
    - location: 設置場所名（デフォルト: "本社"）
    - acquisition_date: 取得日（YYYY-MM-DD形式、デフォルト: 今日の日付）
    
    Returns:
    - pd.DataFrame: 固定資産奉行インポート用フォーマットのDataFrame
    """
    
    if acquisition_date is None:
        acquisition_date = datetime.now().strftime("%Y-%m-%d")
    
    # 固定資産奉行用の列名
    fob_columns = [
        "FAFA001", "FAFA002", "FAFA003", "FAFA004", "FAFA005", "FAFA006",
        "FAFA043", "FAFA007", "FAFA014", "FAFA008", "FAFA010", "FAFA011", 
        "FAFA012", "FAFA013", "FAFA030", "FAFA031", "FAFA032", "FAFA100",
        "FAFA101", "FAFA350", "FAFA363", "FAFA352"
    ]
    
    fob_data = []
    
    for index, row in df.iterrows():
        # 各項目を取得（存在しない場合は空文字）
        asset_name = str(row.get("品目名", ""))
        amount_str = str(row.get("金額", ""))
        account_name = str(row.get("勘定科目", ""))
        useful_life_str = str(row.get("法定耐用年数", ""))
        basis = str(row.get("根拠", ""))
        
        # 数値変換
        amount = extract_numeric_value(amount_str)
        useful_life = extract_useful_life(useful_life_str)
        
        # マスタ情報取得
        asset_type_code, depreciation_method = get_account_info(account_name)
        department_code = get_department_code(department)
        location_code = get_location_code(location)
        
        # 資産コード生成
        asset_code = generate_asset_code(index + 1)
        
        # 摘要は根拠を3つの項目に分割（最大40文字ずつ）
        basis_parts = []
        if basis:
            basis_clean = basis.replace('\n', ' ').replace('\r', ' ')
            # 40文字ずつに分割
            for i in range(0, min(len(basis_clean), 120), 40):
                basis_parts.append(basis_clean[i:i+40])
        
        # 不足分は空文字で埋める
        while len(basis_parts) < 3:
            basis_parts.append("")
        
        # 固定資産奉行用レコード作成
        fob_record = {
            "FAFA001": asset_code,          # 資産コード
            "FAFA002": "",                  # 資産コード（枝番）
            "FAFA003": asset_name,          # 資産名
            "FAFA004": acquisition_date,    # 取得日
            "FAFA005": acquisition_date,    # 供用日
            "FAFA006": "1",                 # 数量
            "FAFA043": "",                  # 空欄
            "FAFA007": str(amount),         # 取得価額
            "FAFA014": "",                  # 空欄
            "FAFA008": asset_type_code,     # 資産種別コード
            "FAFA010": department_code,     # 部門コード
            "FAFA011": location_code,       # 設置場所コード
            "FAFA012": "",                  # 空欄
            "FAFA013": "",                  # 空欄
            "FAFA030": basis_parts[0],      # 摘要1
            "FAFA031": basis_parts[1],      # 摘要2
            "FAFA032": basis_parts[2],      # 摘要3
            "FAFA100": depreciation_method, # 償却方法CD
            "FAFA101": str(useful_life),    # 耐用年数
            "FAFA350": "",                  # 空欄
            "FAFA363": "",                  # 空欄
            "FAFA352": "",                  # 空欄
        }
        
        fob_data.append(fob_record)
    
    return pd.DataFrame(fob_data, columns=fob_columns)


def preview_fob_conversion(df: pd.DataFrame) -> str:
    """
    変換結果のプレビューテキストを生成
    """
    if df.empty:
        return "変換対象のデータがありません。"
    
    preview_text = f"固定資産奉行インポート用CSV変換結果\n"
    preview_text += f"=" * 50 + "\n"
    preview_text += f"総件数: {len(df)}件\n\n"
    
    for index, row in df.iterrows():
        preview_text += f"【{index + 1}】\n"
        preview_text += f"  資産コード: {row.get('FAFA001', '')}\n"
        preview_text += f"  資産名: {row.get('FAFA003', '')}\n"
        preview_text += f"  取得価額: {row.get('FAFA007', '')}円\n"
        preview_text += f"  資産種別: {row.get('FAFA008', '')}\n"
        preview_text += f"  償却方法: {row.get('FAFA100', '')}\n"
        preview_text += f"  耐用年数: {row.get('FAFA101', '')}年\n"
        preview_text += f"  摘要: {row.get('FAFA030', '')}\n"
        preview_text += "\n"
    
    return preview_text