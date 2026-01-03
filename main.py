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

print(f"--- [V3.0] データ蓄積＆グラフ化開始: {datetime.now().strftime('%H:%M:%S')} ---")

# === 2. データ収集・計算 ===
current_results = {}
history_file = "market_history.csv"

# 既存の履歴があれば読み込む、なければ空の箱を用意
if os.path.exists(history_file):
    history_df = pd.read_csv(history_file, index_col=0)
else:
    history_df = pd.DataFrame()

timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
new_row = {'Date': timestamp}

results_list = []

for name, ticker in tickers.items():
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty: continue
            
        current = df['Close'].iloc[-1]
        change = current - df['Close'].iloc[-2]
        pct = (change / df['Close'].iloc[-2]) * 100
        
        # Zスコア計算
        z_score = (current - df['Close'].mean()) / df['Close'].std()
        prob = norm.cdf(abs(z_score)) * 100
        
        # リスク判定
        risk, color = "通常", "green"
        if abs(z_score) > 1.5: risk, color = "注意", "#ffcc00"
        if abs(z_score) > 2.0: risk, color = "危険", "red"
        
        # 結果リスト格納
        results_list.append({
            'name': name, 'price': current, 'change': change, 'pct': pct,
            'z': z_score, 'prob': prob, 'risk': risk, 'color': color,
            'ticker_key': name # グラフ用キー
        })
        
        # 履歴用データに追加
        new_row[name] = current

    except Exception as e:
        print(f"Error {name}: {e}")

# HYG/LQD比率計算
hyg = next((x for x in results_list if 'HYG' in x['name']), None)
lqd = next((x for x in results_list if 'LQD' in x['name']), None)
ratio_val = hyg['price'] / lqd['price'] if hyg and lqd else 0
new_row['HYG/LQD'] = ratio_val

# === 3. 履歴の保存 (CSV) ===
# 新しい行をDataFrameにして結合
new_df = pd.DataFrame([new_row]).set_index('Date')
history_df = pd.concat([history_df, new_df])

# 重複削除（念のため）と保存
history_df = history_df[~history_df.index.duplicated(keep='last')]
history_df.to_csv(history_file)
print("✅ 履歴データをCSVに追記しました。")

# === 4. グラフ用データの作成 (JSON化) ===
# 直近30回分のみ抽出してグラフにする
chart_data = history_df.tail(30).reset_index()
chart_json = chart_data.to_json(orient='records')

# === 5. HTML生成 (Chart.js付き) ===
def create_html(mode="light"):
    if mode == "light":
        bg, text, card, header_bg = "#f4f4f9", "#333", "white", "#e8f5e9"
        btn_text, link_target = "🌑 ダークモード", "report_dark.html"
    else:
        bg, text, card, header_bg = "#121212", "#e0e0e0", "#2d2d2d", "#333"
        btn_text, link_target = "☀️ ライトモード", "report_light.html"

    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>市場AI分析 ({mode})</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background-color: {bg}; color: {text}; margin: 0; padding: 20px; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; max-width: 1400px; margin: 0 auto; }}
            .card {{ background: {card}; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); overflow: hidden; padding-bottom: 10px; }}
            .header {{ background: {header_bg}; padding: 12px 20px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; color: {text}; }}
            .content {{ padding: 15px 20px; }}
            .row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }}
            .price {{ font-size: 1.6em; font-weight: bold; }}
            .badge {{ padding: 4px 10px; border-radius: 20px; font-size: 0.75em; color: white; }}
            canvas {{ max-height: 150px; width: 100%; margin-top: 10px; }}
            a.button {{ display: inline-block; padding: 8px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 20px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div style="max-width: 1400px; margin: 0 auto 20px; display: flex; justify-content: space-between; align-items: center;">
            <h1 style="margin: 0; font-size: 1.5em;">📈 Market AI V3</h1>
            <div>
                <a href="{history_file}" download class="button" style="background:#28a745; margin-right:10px;">💾 CSVDL</a>
                <a href="{link_target}" class="button">{btn_text}</a>
            </div>
        </div>

        <div style="max-width: 1400px; margin: 0 auto 20px; text-align: center; padding: 15px; background: {card}; border-radius: 12px; border-left: 6px solid #007bff;">
            <div style="font-size: 1.2em; font-weight: bold;">HYG/LQD 比率: {ratio_val:.4f}</div>
            <canvas id="chart_ratio"></canvas>
        </div>

        <div class="container">
    """
    
    for r in results_list:
        diff_color = "#4caf50" if r['change'] >= 0 else "#ff5252"
        sign = "+" if r['change'] >= 0 else ""
        canvas_id = f"chart_{results_list.index(r)}"
        
        html += f"""
            <div class="card">
                <div class="header">
                    <span>{r['name']}</span>
                    <span class="badge" style="background:{r['color']}">{r['risk']}</span>
                </div>
                <div class="content">
                    <div class="row">
                        <div class="price">{r['price']:.2f}</div>
                        <div style="font-size:1.5em; font-weight:bold; color:{r['color']}">{r['prob']:.0f}%</div>
                    </div>
                    <div class="row">
                        <div style="color:{diff_color}; font-weight:bold;">{sign}{r['change']:.2f} ({sign}{r['pct']:.2f}%)</div>
                        <div style="font-size:0.8em; opacity:0.7;">異常検知率</div>
                    </div>
                    <canvas id="{canvas_id}"></canvas>
                </div>
            </div>
        """

    # JavaScriptでグラフを描画
    html += f"""
        </div>
        <script>
            const historyData = {chart_json};
            const labels = historyData.map(d => d.Date.split(' ')[0]); // 日付だけ抽出
            
            // 共通グラフ設定
            const commonOptions = {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ x: {{ display: false }}, y: {{ display: false }} }},
                elements: {{ point: {{ radius: 0 }} }} // 点を消して線だけにする
            }};

            // HYG/LQD比率グラフ
            new Chart(document.getElementById('chart_ratio'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: historyData.map(d => d['HYG/LQD']),
                        borderColor: '#007bff', borderWidth: 2, tension: 0.1, fill: false
                    }}]
                }},
                options: {{...commonOptions, scales: {{ y: {{ display: true }} }} }}
            }});

            // 各銘柄のグラフ生成
    """
    
    for r in results_list:
        canvas_id = f"chart_{results_list.index(r)}"
        color = r['color'] if r['color'] != 'green' else '#4caf50' # 緑は見やすく調整
        
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

    html += """
        </script>
    </body>
    </html>
    """
    return html

# === 6. 書き出し ===
with open("report_light.html", "w", encoding="utf-8") as f: f.write(create_html("light"))
with open("report_dark.html", "w", encoding="utf-8") as f: f.write(create_html("dark"))
print("✅ V3分析完了！CSV蓄積＆グラフ描画を含めて更新しました。")
