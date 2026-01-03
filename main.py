import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime

# === 1. 設定: プロ仕様の監視リスト ===
tickers = {
    # --- 市場の王道 ---
    'S&P500': '^GSPC',
    'VIX指数': '^VIX',
    
    # --- グロース・先導株 (牽引役) ---
    'FANG+ (米ハイテク)': 'FNGS',  # ETNを代用
    '2244 (US Tech 20)': '2244.T', # 東証ETF
    
    # --- 債券・金利 (炭鉱のカナリア) ---
    '米国10年債利回り': '^TNX',
    'HYG (ハイイールド債)': 'HYG',
    'LQD (投資適格債)': 'LQD',
    
    # --- 通貨・コモディティ (真実の鏡) ---
    'ゴールド (GLDM)': 'GLDM',
    'ドル円 (USD/JPY)': 'JPY=X',
    'ドル指数 (DXY)': 'DX-Y.NYB'
}

# 銘柄ごとの閾値調整（オプション）
# VIXやDXYは動きが激しいので、少し緩めに見るなどの調整も可能
custom_thresholds = {
    'VIX指数': 2.0, # VIXは2σ超えで危険判定
}

print(f"--- [プロ仕様] 分析開始: {datetime.now().strftime('%H:%M:%S')} ---")

# === 2. データ収集・計算 ===
results = []
for name, ticker in tickers.items():
    try:
        # 日本株(2244.T)などはタイムゾーンが違うので注意が必要だが、今回は終値ベースで簡易処理
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty:
            print(f"Skip: {name}")
            continue
            
        current = df['Close'].iloc[-1]
        change = current - df['Close'].iloc[-2]
        pct = (change / df['Close'].iloc[-2]) * 100
        
        # Zスコア計算
        mean = df['Close'].mean()
        std = df['Close'].std()
        z_score = (current - mean) / std
        prob = norm.cdf(abs(z_score)) * 100
        
        # リスク判定
        threshold_caution = 1.5
        threshold_danger = 2.0
        
        risk, color = "通常", "green"
        if abs(z_score) > threshold_caution: risk, color = "注意", "#ffcc00"
        if abs(z_score) > threshold_danger: risk, color = "危険", "red"
        
        # 逆相関の指標（VIX, 利回り, ドル円）は「上がる＝危険」だが、
        # 統計的異常値という意味では同じロジックでOK。
        # ただし、VIXが「低すぎる(楽観)」のもリスクなので、絶対値で判定。

        results.append({
            'name': name, 'price': current, 'change': change, 'pct': pct,
            'z': z_score, 'prob': prob, 'risk': risk, 'color': color
        })
    except Exception as e:
        print(f"Error {name}: {e}")

# HYG/LQD比率
hyg = next((x for x in results if 'HYG' in x['name']), None)
lqd = next((x for x in results if 'LQD' in x['name']), None)
ratio_val = hyg['price'] / lqd['price'] if hyg and lqd else 0

# === 3. HTML生成関数 ===
def create_html(mode="light"):
    if mode == "light":
        bg_color, text_color, card_bg, header_bg, btn_text, link_target = "#f4f4f9", "#333", "white", "#e8f5e9", "🌑 ダークモードへ", "report_dark.html"
    else:
        bg_color, text_color, card_bg, header_bg, btn_text, link_target = "#121212", "#e0e0e0", "#2d2d2d", "#333", "☀️ ライトモードへ", "report_light.html"

    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>市場AI分析 ({mode})</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background-color: {bg_color}; color: {text_color}; margin: 0; padding: 20px; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
            .card {{ background: {card_bg}; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); overflow: hidden; }}
            .header {{ background: {header_bg}; padding: 12px 20px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; color: {text_color}; border-bottom: 1px solid rgba(0,0,0,0.05); }}
            .content {{ padding: 20px; }}
            .row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }}
            .price {{ font-size: 1.8em; font-weight: bold; letter-spacing: -0.5px; }}
            .change {{ font-weight: bold; font-size: 1.0em; }}
            .prob-label {{ font-size: 0.8em; opacity: 0.7; }}
            .prob-val {{ font-size: 2.0em; font-weight: bold; }}
            .badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.75em; font-weight: bold; color: white; letter-spacing: 0.5px; }}
            a.button {{ display: inline-block; padding: 8px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 20px; font-size: 0.9em; font-weight: bold; transition: opacity 0.2s; }}
            a.button:hover {{ opacity: 0.8; }}
        </style>
    </head>
    <body>
        <div style="max-width: 1200px; margin: 0 auto 20px; display: flex; justify-content: space-between; align-items: center;">
            <h1 style="margin: 0; font-size: 1.5em;">📈 Market AI Dashboard</h1>
            <a href="{link_target}" class="button">{btn_text}</a>
        </div>
        
        <div style="max-width: 1200px; margin: 0 auto 30px; text-align: center; padding: 20px; background: {card_bg}; border-radius: 12px; border-left: 6px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="font-size: 0.9em; opacity: 0.7; margin-bottom: 5px;">Risk Sentiment Indicator</div>
            <div style="font-size: 1.2em; font-weight: bold;">HYG/LQD 比率: <span style="font-size: 1.5em;">{ratio_val:.4f}</span></div>
            <div style="font-size: 0.8em; margin-top: 5px; opacity: 0.6;">更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}</div>
        </div>

        <div class="container">
    """
    
    for r in results:
        diff_color = "#4caf50" if r['change'] >= 0 else "#ff5252"
        sign = "+" if r['change'] >= 0 else ""
        
        html += f"""
            <div class="card">
                <div class="header">
                    <span>{r['name']}</span>
                    <span class="badge" style="background:{r['color']}">{r['risk']}</span>
                </div>
                <div class="content">
                    <div class="row">
                        <div class="price">{r['price']:.2f}</div>
                        <div class="prob-val" style="color:{r['color']}">{r['prob']:.0f}%</div>
                    </div>
                    <div class="row">
                        <div class="change" style="color:{diff_color}">{sign}{r['change']:.2f} ({sign}{r['pct']:.2f}%)</div>
                        <div class="prob-label">転換確率(Z-Score)</div>
                    </div>
                </div>
            </div>
        """
    
    html += "</div></body></html>"
    return html

# === 4. ファイル書き出し ===
with open("report_light.html", "w", encoding="utf-8") as f: f.write(create_html("light"))
with open("report_dark.html", "w", encoding="utf-8") as f: f.write(create_html("dark"))

print("✅ アップグレード完了！最強の市場分析セットを出力しました。")
