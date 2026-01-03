import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime

# === 1. データ取得・計算（ここは共通） ===
tickers = {
    'S&P500': '^GSPC', 'VIX指数': '^VIX', '米国10年債利回り': '^TNX',
    'HYG (ハイイールド債)': 'HYG', 'LQD (投資適格債)': 'LQD'
}

print(f"--- 2つのレポートを作成中: {datetime.now().strftime('%H:%M:%S')} ---")

results = []
for name, ticker in tickers.items():
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty: continue
        current = df['Close'].iloc[-1]
        change = current - df['Close'].iloc[-2]
        pct = (change / df['Close'].iloc[-2]) * 100
        z_score = (current - df['Close'].mean()) / df['Close'].std()
        prob = norm.cdf(abs(z_score)) * 100
        risk, color = "通常", "green"
        if abs(z_score) > 1.5: risk, color = "注意", "#ffcc00"
        if abs(z_score) > 2.0: risk, color = "危険", "red"
        results.append({
            'name': name, 'price': current, 'change': change, 'pct': pct,
            'z': z_score, 'prob': prob, 'risk': risk, 'color': color
        })
    except: pass

# HYG/LQD比率
hyg = next((x for x in results if 'HYG' in x['name']), None)
lqd = next((x for x in results if 'LQD' in x['name']), None)
ratio_val = hyg['price'] / lqd['price'] if hyg and lqd else 0


# === 2. HTML生成関数（色設定を変えて2回使う） ===
def create_html(mode="light"):
    # 色設定の定義
    if mode == "light":
        bg_color = "#f4f4f9"
        text_color = "#333"
        card_bg = "white"
        header_bg = "#e8f5e9"
        btn_text = "🌑 ダークモードへ"
        link_target = "report_dark.html"
    else: # dark
        bg_color = "#121212"
        text_color = "#e0e0e0"
        card_bg = "#2d2d2d"
        header_bg = "#333"
        btn_text = "☀️ ライトモードへ"
        link_target = "report_light.html"

    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>市場AI分析 ({mode})</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: {bg_color}; color: {text_color}; margin: 0; padding: 20px; }}
            .container {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }}
            .card {{ background: {card_bg}; width: 100%; max-width: 450px; border-radius: 10px; margin-bottom: 10px; padding-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .header {{ background: {header_bg}; padding: 15px; font-weight: bold; display: flex; justify-content: space-between; color: {text_color}; }}
            .content {{ padding: 15px; display: flex; justify-content: space-between; }}
            .price {{ font-size: 1.8em; font-weight: bold; }}
            a.button {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 20px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div style="text-align: right; margin-bottom: 20px;">
            <a href="{link_target}" class="button">{btn_text}</a>
        </div>
        <h1 style="text-align:center">📈 市場動向AI分析 ({mode})</h1>
        <div style="text-align:center; margin-bottom: 20px; padding: 10px; background: {card_bg}; border-radius: 10px;">
            <h3>HYG/LQD 比率: {ratio_val:.4f}</h3>
        </div>
        <div class="container">
    """
    
    for r in results:
        diff_color = "#4caf50" if r['change'] >= 0 else "#ff5252"
        html += f"""
            <div class="card">
                <div class="header">
                    <span>{r['name']}</span>
                    <span style="background:{r['color']}; color:white; padding:2px 10px; border-radius:10px; font-size:0.8em;">{r['risk']}</span>
                </div>
                <div class="content">
                    <div>
                        <div class="price">{r['price']:.2f}</div>
                        <div style="color:{diff_color}">{r['change']:.2f} ({r['pct']:.2f}%)</div>
                    </div>
                    <div style="text-align:right">
                        <div>転換確率</div>
                        <div style="font-size:2em; font-weight:bold; color:{r['color']}">{r['prob']:.0f}%</div>
                    </div>
                </div>
            </div>
        """
    
    html += "</div></body></html>"
    return html

# === 3. ファイル書き出し ===
# ライト版を作成
with open("report_light.html", "w", encoding="utf-8") as f:
    f.write(create_html("light"))

# ダーク版を作成
with open("report_dark.html", "w", encoding="utf-8") as f:
    f.write(create_html("dark"))

print("✅ 完了！ 'report_light.html' と 'report_dark.html' の2つが作成されました。")
print("ライト版を開いて、右上のボタンを押して移動できるか確認してください。")
