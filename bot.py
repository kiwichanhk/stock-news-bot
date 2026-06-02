import discord
from discord.ext import commands
import os
import requests
from dotenv import load_dotenv
from longport.openapi import QuoteContext, Config
from flask import Flask
from threading import Thread

load_dotenv()

# --- 虛擬網頁防護罩 (給 Render 伺服器健康檢查用的) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "股市情報員正在監視市場中！"

def run_server():
    # Render 會動態分配 Port，我們必須這樣抓取
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_server, daemon=True).start()
# -----------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LB_CLIENT_ID = os.getenv("LONGBRIDGE_CLIENT_ID")
LB_APP_SECRET = os.getenv("LONGBRIDGE_APP_SECRET") # 補回缺少的 Secret
LB_ACCESS_TOKEN = os.getenv("LONGBRIDGE_ACCESS_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

try:
    # 補上 app_secret 來滿足套件的要求
    lb_config = Config(app_key=LB_CLIENT_ID, app_secret=LB_APP_SECRET, access_token=LB_ACCESS_TOKEN)
    ctx = QuoteContext(lb_config)
    print("✅ 長橋 OpenAPI 連線設定完成")
except Exception as e:
    print(f"❌ 長橋 API 設定失敗: {e}")

def get_realtime_price(symbol):
    try:
        formatted_symbol = f"{symbol.upper()}.US" if not symbol.endswith('.US') else symbol.upper()
        quote = ctx.quote([formatted_symbol])
        if quote:
            return quote[0].last_done
        return "無法獲取報價"
    except Exception as e:
        print(f"報價錯誤: {e}")
        return "報價連線異常"

def generate_ai_report(symbol, current_price):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    你是華爾街頂級分析師。請針對美股代碼 {symbol.upper()} 撰寫深度的專業分析報告。
    目前長橋即時報價為：${current_price}。
    請直接輸出報告，使用 Markdown 排版，包含：操作建議、公司動態、業務預測、利好利空、短期與長期趨勢、各階段目標價、阻力與支持位、建倉策略。
    """
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload).json()
        return response['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"AI 分析生成失敗: {e}"

@bot.event
async def on_ready():
    print(f'✅ 機器人 {bot.user} 已成功上線！')

@bot.command()
async def analyze(ctx_cmd, symbol: str):
    await ctx_cmd.send(f"🔍 正在啟動分析模組，抓取 **{symbol.upper()}** 最新數據與 AI 推理中，請稍候...")
    price = get_realtime_price(symbol)
    report = generate_ai_report(symbol, price)
    
    if len(report) > 1900:
        for i in range(0, len(report), 1900):
            await ctx_cmd.send(report[i:i+1900])
    else:
        await ctx_cmd.send(report)

bot.run(DISCORD_TOKEN)
