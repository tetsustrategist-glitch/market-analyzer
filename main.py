import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime
import os
import json

# === 1. 設定: 監視リスト ===
tickers = {
    'S&P500': '^GSPC',
    'VIX指数': '^VIX',
    'FANG+': 'FNGS',
    '2244(US Tech)': '2244.T',
    '米国10年債利回り': '^TNX',
    'HYG(ハイ債)': 'HYG',
    'LQD(適格債)': 'LQD',
    'ゴールド(GLDM)': 'GLDM',
    'ドル円': 'JPY=X',
    'ドル指数': 'DX-Y.NYB'
}

print(f"--- [V4.0] RSI & Drawdown 分析開始: {datetime.now().strftime('%H:%M:%S')} ---")

# === 関数: RSI計算 ===
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# === 2. データ収集・計算 ===
current_results = {}
history_file = "market_history.csv"

# 履歴読み込み
if os.path.exists(history_file):
    try:
        history_df = pd.read_csv(history_file, index_col=0)
    except:
        history_df = pd.DataFrame()
else:
    history_df = pd.DataFrame()

timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
new_row = {'Date': timestamp}
results_list = []

for name, ticker in tickers.items():
    try:
        # データ取得 (RSI用に少し長めに確保)
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty:
            print(f"Skip (No Data): {name}")
            continue
            
        # --- 基本データ ---
        current = df['Close'].iloc[-1]
        if len(df) > 1:
            change = current - df['Close'].iloc[-2]
            pct = (change / df['Close'].iloc[-2]) * 100
        else:
            change, pct = 0, 0
        
        # --- 1. 統計的異常度 (Z-Score) ---
        if df['Close'].std() != 0:
            z_score = (current - df['Close'].mean()) / df['Close'].std()
        else:
            z_score = 0
        # 50%を基準に補正はせず、素直な確率を表示
        prob = norm.cdf(abs(z_score)) * 100
        
        # --- 2. テクニカル指標 (RSI) ---
        rsi_series = calculate_rsi(df['Close'])
        rsi_val = rsi_series.iloc[-1]
        
        # --- 3. 実利指標 (3ヶ月高値からの下落率) ---
        # 過去63営業日（約3ヶ月）の最高値を探す
        high_3m = df['Close'].tail(63).max()
        drawdown = ((current - high_3m) / high_3m) * 100
        
        # リスク判定ロジック (複合判定)
        risk, color = "通常", "green"
        # Zスコアが異常、かつRSIも過熱している場合に警告
        if abs(z_score) > 1.5: risk, color = "注意", "#ffcc00"
        if abs(z_score) > 2.0: risk, color = "危険", "red"
        
        results_list.append({
            'name': name, 'price': current, 'change': change, 'pct': pct,
            'z': z_score, 'prob': prob, 'risk': risk, 'color': color,
            'rsi': rsi_val, 'drawdown': drawdown,
            'ticker_key': name
        })
        new_row[name] = current

    except Exception as e:
        print(f"Error processing {name}: {e}")

# HYG/LQD比率
hyg = next((x for x in results_list if 'HYG' in x['name']), None)
lqd = next((x for x in results_list if 'LQD' in x['name']), None)
ratio_val = hyg['price'] / lqd['price'] if (hyg and lqd and lqd['price']!=0) else 0
new_row['HYG/LQD'] = ratio_val

# === 3. 履歴保存 ===
try:
    new_df = pd.DataFrame([new_row]).set_index('Date')
    history_df = pd.concat([history_df, new_df])
    history_df = history_df[~history_df.index.duplicated(keep='last')]
    history_df.to_csv(history_file)
except Exception as e:
    print(f"History Save Error: {e}")

# === 4. グラフデータ ===
chart_json = "[]"
try:
    chart_data = history_df.tail(30).reset_index()
    chart_json = chart_data.to_json(orient='records')
except: pass

# === 5. HTML生成 (デザイン強化版) ===
def create_html(mode="light"):
    if mode == "light":
        bg, text, card, header_bg = "#f4f4f9", "#333", "white", "#e8f5e9"
        btn_text, link_target = "🌑 ダークモード", "report_dark.html"
        sub_text = "#666"
    else:
        bg, text, card, header_bg = "#121212", "#e0e0e0", "#2d2d2d", "#333"
        btn_text, link_target = "☀️ ライトモード", "report_light.html"
        sub_text = "#aaa"

    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Market Sniper V4 ({mode})</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: sans-serif; background-color: {bg}; color: {text}; margin: 0; padding: 20px; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 15px; max-width: 1400px; margin: 0 auto; }}
            .card {{ background: {card}; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); padding: 15px; }}
            .header {{ display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 5px; }}
            .price {{ font-size: 1.6em; font-weight: bold; margin-bottom: 5px;}}
            .main-stats {{ display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid {sub_text}; padding-bottom: 8px; margin-bottom: 8px; }}
            .sub-stats {{ display: flex; justify-content: space-between; font-size: 0.9em; color: {sub_text}; }}
            .badge {{ padding: 3px 10px; border-radius: 10px; color: white; font-size: 0.8em; }}
            canvas {{ max-height: 80px; width: 100%; margin-top: 5px; }}
            a.button {{ display: inline-block; padding: 8px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 20px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div style="display: flex; justify-content: space-between; margin-bottom: 20px; max-width: 1400px; margin: 0 auto;">
            <h1>🎯 Market Sniper V4</h1>
            <div>
                <a href="{history_file}" download class="button" style="background:#28a745;">💾 CSV</a>
                <a href="{link_target}" class="button">{btn_text}</a>
            </div>
        </div>
        <div style="text-align:center; margin-bottom: 20px;">
            <h3>HYG/LQD 比率: {ratio_val:.4f}</h3>
        </div>
        <div class="container">
    """
    
    for r in results_list:
        canvas_id = f"chart_{results_list.index(r)}"
        diff_color = "#4caf50" if r['change'] >= 0 else "#ff5252"
        sign = "+" if r['change'] >= 0 else ""
        
        # ドローダウンの色分け（-5%超えたら青＝買い場シグナル）
        dd_color = sub_text
        if r['drawdown'] < -5: dd_color = "#007bff" 
        if r['drawdown'] < -10: dd_color = "#ff5252" # 暴落警戒
        
        html += f"""
            <div class="card">
                <div class="header">
                    <span>{r['name']}</span>
                    <span class="badge" style="background:{r['color']}">{r['risk']}</span>
                </div>
                
                <div class="main-stats">
                    <div>
                        <div class="price">{r['price']:.2f}</div>
                        <div style="color:{diff_color}; font-weight:bold;">{sign}{r['change']:.2f} ({sign}{r['pct']:.2f}%)</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.8em; opacity:0.8;">転換確率</div>
                        <div style="font-size:1.4em; font-weight:bold; color:{r['color']}">{r['prob']:.0f}%</div>
                    </div>
                </div>

                <div class="sub-stats">
                    <div>
                        RSI(14): <strong>{r['rsi']:.1f}</strong>
                    </div>
                    <div style="color:{dd_color}; font-weight:bold;">
                        3ヶ月高値比: {r['drawdown']:.2f}%
                    </div>
                </div>
                
                <canvas id="{canvas_id}"></canvas>
            </div>
        """

    html += f"""
        </div>
        <script>
            const historyData = {chart_json};
            const labels = historyData.map(d => d.Date.split(' ')[0]);
            const commonOptions = {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ x: {{ display: false }}, y: {{ display: false }} }},
                elements: {{ point: {{ radius: 0 }} }}
            }};
    """
    
    for r in results_list:
        canvas_id = f"chart_{results_list.index(r)}"
        color = r['color'] if r['color'] != 'green' else '#4caf50'
        html += f"""
            new Chart(document.getElementById('{canvas_id}'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: historyData.map(d => d['{r['name']}']),
                        borderColor: '{color}', borderWidth: 2, tension: 0.1, fill: false
                    }}]
                }},
                options: commonOptions
            }});
        """

    html += "</script></body></html>"
    return html

with open("report_light.html", "w", encoding="utf-8") as f: f.write(create_html("light"))
with open("report_dark.html", "w", encoding="utf-8") as f: f.write(create_html("dark"))
print("✅ V4.0 (RSI/Drawdown) 分析完了")
