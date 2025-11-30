import discord
from discord.ext import commands, tasks
import json
import aiohttp
import random
from datetime import datetime, timedelta
import sqlite3
import asyncio

# اقرأ الإعدادات
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# إنشاء البوت
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

CHAT_CHANNEL_ID = config.get("CHAT_CHANNEL_ID")
PERPLEXITY_API_KEY = config.get("PERPLEXITY_API_KEY")

# ========== معلومات لعبة Fate/War ==========

FATE_WAR_DATABASE = {
    "أبطال": {
        "أرتوريا": {
            "الرتبة": "SSR",
            "النوع": "Saber",
            "الدول": "بريطانيا",
            "الوصف": "ملكة بريطانيا الأسطورية، قوية جداً في الدفاع والهجوم"
        },
        "جيل": {
            "الرتبة": "SR",
            "النوع": "Archer",
            "الدول": "بابل",
            "الوصف": "ملك بابل، ماهر بالرماية والسحر"
        },
        "إيسكندر": {
            "الرتبة": "SSR",
            "النوع": "Rider",
            "الدول": "مقدونيا",
            "الوصف": "الإسكندر الأكبر، أسطوري في الحروب"
        }
    },
    "طرق اللعب": {
        "البطل": "اختر 3 أبطال من طاقمك واقتل فريق الخصم",
        "المحاربات": "شارك في بطولات يومية واحصل على جوائز",
        "المراحل": "أكمل السيناريو الرئيسي لفتح محتوى جديد"
    },
    "نظام الرتب": {
        "SSR": "أفضل رتبة - نادرة جداً",
        "SR": "رتبة عالية - نادرة",
        "R": "رتبة متوسطة",
        "N": "رتبة عادية"
    },
    "نصائح": [
        "اجمع الأبطال القويين لفريق متوازن",
        "استخدم الحجارة الكريمة بحكمة في التطور",
        "شارك في الأحداث الخاصة للحصول على مكافآت",
        "طور أبطالك بالخبرة والمواد",
        "اتحد مع لاعبين آخرين في الحملات الجماعية"
    ]
}

# ========== إعداد قاعدة البيانات ==========

def init_database():
    """إنشاء قاعدة البيانات"""
    conn = sqlite3.connect('fate_war_bot.db')
    cursor = conn.cursor()
    
    # جدول السياق المحادثات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    ''')
    
    # جدول معلومات الأبطال المفضلة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            hero_name TEXT,
            created_at TEXT
        )
    ''')
    
    # جدول الأسئلة الشائعة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# ========== دوال السياق ==========

def add_conversation(user_id, guild_id, role, content):
    """حفظ محادثة"""
    conn = sqlite3.connect('fate_war_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversation_history (user_id, guild_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, guild_id, role, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, guild_id, limit=10):
    """جلب سياق المحادثة"""
    conn = sqlite3.connect('fate_war_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, content FROM conversation_history 
        WHERE user_id = ? AND guild_id = ?
        ORDER BY id DESC LIMIT ?
    ''', (user_id, guild_id, limit))
    
    history = cursor.fetchall()
    conn.close()
    
    # قلب الترتيب ليكون الأقدم أولاً
    return [(role, content) for role, content in reversed(history)]

# ========== الأحداث الرئيسية ==========

@bot.event
async def on_ready():
    print(f"✅ البوت متصل: {bot.user}")
    print(f"🎮 وضع Fate/War - بوت ذكي عن اللعبة")
    print(f"📝 القناة: {CHAT_CHANNEL_ID}")

# ========== أوامر معلومات اللعبة ==========

@bot.command(name="فايت")
async def fate_info(ctx):
    """معلومات عن لعبة Fate/War"""
    embed = discord.Embed(
        title="🎮 لعبة Fate/War",
        description="لعبة RPG من IGG - استراتيجية وأساطير",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🎯 طريقة اللعب",
        value="اختر 3 أبطال أساطير وقاتل فرق أخرى",
        inline=False
    )
    
    embed.add_field(
        name="⭐ رتب الأبطال",
        value="N (عادي) → R → SR → SSR (أفضل)",
        inline=False
    )
    
    embed.add_field(
        name="💎 الأبطال الرئيسيين",
        value="أرتوريا، إيسكندر، جيل وغيرهم",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="أبطال")
async def heroes(ctx):
    """عرض الأبطال المشهورين"""
    embed = discord.Embed(
        title="🗡️ أبطال Fate/War",
        color=discord.Color.purple()
    )
    
    for hero, info in FATE_WAR_DATABASE["أبطال"].items():
        embed.add_field(
            name=f"{hero} ⭐{info['الرتبة']}",
            value=f"**النوع:** {info['النوع']}\n**الدول:** {info['الدول']}\n{info['الوصف']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="نصائح")
async def tips(ctx):
    """نصائح للعبة"""
    embed = discord.Embed(
        title="💡 نصائح للعبة",
        color=discord.Color.green()
    )
    
    for i, tip in enumerate(FATE_WAR_DATABASE["نصائح"], 1):
        embed.add_field(
            name=f"💭 نصيحة {i}",
            value=tip,
            inline=False
        )
    
    await ctx.send(embed=embed)

# ========== معالج الرسائل - AI ذكي بدون ليمت ==========

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # فقط في قناة الشات المحددة
    if message.channel.id != CHAT_CHANNEL_ID:
        return
    
    # حفظ الرسالة في السياق
    add_conversation(
        message.author.id,
        message.guild.id,
        "user",
        message.content
    )
    
    # الرد الذكي
    async with message.channel.typing():
        response = await get_smart_response(
            message.content,
            message.author.id,
            message.guild.id,
            message.author.name
        )
        
        # تقسيم الرسالة إذا كانت طويلة
        if len(response) > 2000:
            parts = [response[i:i+1990] for i in range(0, len(response), 1990)]
            for part in parts:
                await message.reply(part)
        else:
            await message.reply(response)
        
        # حفظ الرد في السياق
        add_conversation(
            message.author.id,
            message.guild.id,
            "assistant",
            response
        )
    
    await bot.process_commands(message)

async def get_smart_response(user_message: str, user_id: int, guild_id: int, username: str) -> str:
    """رد ذكي عن لعبة Fate/War"""
    
    try:
        # جلب السياق السابق
        history = get_conversation_history(user_id, guild_id, limit=8)
        
        # بناء رسائل السياق
        messages = []
        for role, content in history:
            messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": content
            })
        
        # إضافة الرسالة الجديدة
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # نص النظام المتقدم
        system_prompt = f"""أنت بوت مرح وودود متخصص في لعبة Fate/War من IGG.
        
المتطلبات:
1. أجب على أسئلة اللعبة بشكل فودود ومرح مع الابتسامات والإيموجيهات
2. استخدم معلومات هذه القاعدة عن اللعبة:
   - الأبطال الرئيسيين: أرتوريا (SSR Saber)، إيسكندر (SSR Rider)، جيل (SR Archer)
   - الرتب: N → R → SR → SSR
   - طريقة اللعب: اختر 3 أبطال وقاتل فرقاً أخرى
   - شارك في الأحداث للحصول على جوائز

3. إذا لم تعرف معلومة محددة، قل "مش متأكد من دي بس الغالب أن..."
4. ادعم اللاعب الجديد بنصائح مفيدة
5. حافظ على الشخصية المرحة والودية دائماً
6. لا تضع حد أقصى للرسائل - رد طبيعي حسب السؤال

اسم المستخدم: {username}"""
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": system_prompt}
            ] + messages,
            "max_tokens": 200,
            "temperature": 0.9
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.perplexity.ai/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_message = result["choices"][0]["message"]["content"]
                    return ai_message
                else:
                    return "😅 عذراً، في مشكلة تقنية صغيرة! جرب مرة تانية بس 🎮"
    
    except Exception as e:
        print(f"❌ خطأ: {e}")
        responses = [
            "🤔 آسف، ما فهمت قصدك بالكامل! أعد الصيغة برجاء؟",
            "😅 ماعندي معلومة عن دي الحاجة بالضبط! سؤال آخر؟",
            "🎮 حصلت مشكلة صغيرة! حاول بعدين! ⚔️"
        ]
        return random.choice(responses)

# ========== أوامر عامة ==========

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! {latency}ms")

if __name__ == "__main__":
    bot.run(config["DISCORD_TOKEN"])
