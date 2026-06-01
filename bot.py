import discord
from discord.ext import commands
import os
import requests
from dotenv import load_dotenv
from longport.openapi import QuoteContext, Config

# 載入 .env 檔案中的環境變數
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LB_APP_KEY = os.getenv("LONGBRIDGE_APP_KEY")
LB_APP_SECRET = os.getenv("LONGBRIDGE_APP_SECRET")
LB_TOKEN = os.getenv("LONGBRIDGE_ACCESS_TOKEN")

# 設定 Discord 機器人權限 (Intents)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 設定長橋連線
try:
    lb_config = Config(app_key=LB_APP_KEY, app_secret=LB_APP_SECRET, access_token=LB_TOKEN)
    ctx = QuoteContext(lb_config)
    print("✅ 長橋 API 連線設定完成")
except Exception as e:
    print(f"❌ 長橋 API 設定失敗: {e}")

def get_realtime_price(symbol):
    """透過長橋 API 獲取即時報價"""
    try:
        # 長橋美股代碼通常需要加上 .US，例如 AAPL.US
        formatted_symbol = f"{symbol.upper()}.US" if not symbol.endswith('.US') else symbol.upper()
        quote = ctx.quote([formatted_symbol])
        if quote:
            return quote[0].last_done
        return "無法獲取報價"
    except Exception as e:
        print(f"獲取報價失敗: {e}")
        return "報價連線異常"

def generate_ai_report(symbol, current_price):
    """調用 Gemini 產生結構化分析報告"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    你是華爾街頂級分析師。請針對美股代碼 {symbol.upper()} 撰寫一份深度的專業分析報告。
    目前長橋即時報價為：${current_price}。
    
    請務必嚴格遵循以下格式輸出，不需額外廢話，直接輸出報告內容，並使用 Markdown 排版：
    
    **操作建議**：[買入 / 賣出 / 持有 / 觀望]
    
    **公司最新動態**
    * **近期關注**：(說明最近已公佈及未公佈需重點關注的消息)
    
    **公司業務情況**
    * **財報預測**：(下次財務報表的日期和業績預測)
    
    **最新市場消息**
    * 🟢 **利好消息**：(列出 1-2 點)
    * 🔴 **利空消息**：(列出 1-2 點)
    
    **趨勢方向**
    * **短期方向**：(說明方向及原因)
    * **長期方向**：(說明方向及原因)
    
    **目標建議**
    * **短期 (1-3個月)**：$
    * **中期 (3-12個月)**：$
    * **長期 (1年以上)**：$
    
    **技術點位**
    * **阻力位**：(最少提供3個)
    * **支持位**：(最少提供3個)
    
    **執行策略**
    * **建倉位**：(建議具體價位)
    * **資金比例**：(建議百分比與資金控管說明)
    """

    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload).json()
        return response['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"AI 分析生成失敗，請稍後再試。錯誤訊息：{e}"

@bot.event
async def on_ready():
    print(f'✅ 機器人 {bot.user} 已成功上線！')

@bot.command()
async def analyze(ctx, symbol: str):
    """Discord 指令：!analyze <股票代碼>"""
    await ctx.send(f"🔍 正在啟動分析模組，抓取 **{symbol.upper()}** 最新數據與 AI 推理中，請稍候...")
    
    # 1. 抓取即時報價
    price = get_realtime_price(symbol)
    
    # 2. 生成 AI 報告
    report = generate_ai_report(symbol, price)
    
    # 3. 發送到 Discord (如果報告太長，超過 Discord 的 2000 字元限制，需要分段)
    if len(report) > 1900:
        chunks = [report[i:i+1900] for i in range(0, len(report), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(report)

# 啟動機器人
bot.run(DISCORD_TOKEN)
