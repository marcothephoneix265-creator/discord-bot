# تعديل جدول الأحداث لإضافة عمود voice_channel_id

# في دالة init_database() - عدّل جدول events ليصير:

    # جدول الأحداث (محدّث مع الصوت)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            times TEXT NOT NULL,
            reminder_minutes INTEGER DEFAULT 30,
            message TEXT,
            days TEXT,
            channel_id INTEGER,
            voice_channel_id INTEGER,
            created_at TEXT,
            guild_id INTEGER
        )
    ''')

# ========== تحديث دوال الأحداث ==========

# عدّل دالة add_event():

def add_event(event_name, times, reminder_minutes, message, days, channel_id, guild_id, voice_channel_id=None):
    conn = sqlite3.connect('alliance_events.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (event_name, times, reminder_minutes, message, days, channel_id, voice_channel_id, created_at, guild_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (event_name, times, reminder_minutes, message, days, channel_id, voice_channel_id, datetime.now().isoformat(), guild_id))
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id

# ========== تحديث أمر addevent ==========

# عدّل أمر addevent ليطلب قناة صوتية:

@bot.command(name="addevent")
@commands.has_permissions(administrator=True)
async def addevent(ctx):
    """إضافة حدث جديد مع قناة صوتية"""
    embed = discord.Embed(
        title="📝 إضافة حدث جديد متقدم",
        description="الرجاء الإجابة على الأسئلة التالية:",
        color=discord.Color.blue()
    )
    embed.add_field(name="1️⃣ اسم الحدث", value="أرسل اسم الحدث (مثال: حرب التحالف)", inline=False)
    await ctx.send(embed=embed)
    
    try:
        # اسم الحدث
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        event_name = msg.content
        
        await ctx.send("⏰ أوقات الحدث (اكتب المرات بـ comma مثال: 14:30,18:00,22:00)")
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        times = msg.content
        
        await ctx.send("🔔 التذكير قبل كم دقيقة؟ (مثال: 30)")
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        reminder_minutes = int(msg.content)
        
        await ctx.send("📢 الرسالة (الرسالة اللي البوت سيقولها في الصوتي)")
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        message = msg.content if msg.content else "الحدث بدأ الآن!"
        
        await ctx.send("📅 الأيام (مثال: Monday,Wednesday,Friday أو Daily لكل يوم)")
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        days = msg.content
        
        await ctx.send("📍 اكتب رقم القناة النصية أو 'default' للقناة الافتراضية")
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        if msg.content.lower() == "default":
            channel_id = CHAT_CHANNEL_ID
        else:
            channel_id = int(msg.content)
        
        await ctx.send("🎤 اكتب رقم القناة الصوتية (أو 'skip' إذا ما في قناة صوتية)")
        msg = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        if msg.content.lower() == "skip":
            voice_channel_id = None
        else:
            try:
                voice_channel_id = int(msg.content)
            except:
                voice_channel_id = None
        
        # إضافة الحدث
        event_id = add_event(event_name, times, reminder_minutes, message, days, channel_id, ctx.guild.id, voice_channel_id)
        
        times_count = len([t.strip() for t in times.split(",")])
        voice_info = f"🎤 القناة الصوتية: {voice_channel_id}" if voice_channel_id else "❌ بدون قناة صوتية"
        
        embed = discord.Embed(
            title="✅ تم إضافة الحدث",
            description=f"**اسم الحدث:** {event_name}\n**عدد المرات:** {times_count} مرات\n**الأوقات:** {times}\n**التذكير:** {reminder_minutes} دقيقة\n**الأيام:** {days}\n**القناة النصية:** {channel_id}\n{voice_info}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"معرف الحدث: {event_id}")
        await ctx.send(embed=embed)
    
    except asyncio.TimeoutError:
        await ctx.send("❌ انتهت المهلة الزمنية، حاول مرة أخرى")
    except ValueError:
        await ctx.send("❌ خطأ في الإدخال، تأكد من الصيغة الصحيحة")
    except Exception as e:
        await ctx.send(f"❌ خطأ: {e}")

# ========== تحديث أمر events ==========

# عدّل أمر events ليعرض القناة الصوتية:

@bot.command(name="events")
async def events(ctx):
    """عرض جميع الأحداث"""
    events_list = get_all_events(ctx.guild.id)
    
    if not events_list:
        await ctx.send("❌ لا توجد أحداث حالياً")
        return
    
    embed = discord.Embed(title="📅 الأحداث المجدولة", color=discord.Color.blue())
    
    for event in events_list:
        event_id, event_name, times, reminder_minutes, message, days, channel_id, voice_channel_id, created_at, guild_id = event
        times_list = [t.strip() for t in times.split(",")]
        voice_info = f"🎤 {voice_channel_id}" if voice_channel_id else "❌ بدون صوت"
        embed.add_field(
            name=f"#{event_id} - {event_name}",
            value=f"⏰ {len(times_list)} مرات: {', '.join(times_list)}\n📅 {days}\n🔔 تذكير: {reminder_minutes} دقيقة\n📝 الرسالة: {message}\n{voice_info}",
            inline=False
        )
    
    await ctx.send(embed=embed)

# ========== تحديث check_events لتفعيل الصوت ==========

# عدّل مهمة check_events ليدخل الصوتي:

@tasks.loop(minutes=1)
async def check_events():
    try:
        current_time = datetime.now().strftime("%H:%M")
        current_day = datetime.now().strftime("%A")
        for guild in bot.guilds:
            events = get_all_events(guild.id)
            for event in events:
                event_id, event_name, times, reminder_minutes, message, days, channel_id, voice_channel_id, created_at, guild_id = event
                if days and current_day not in days:
                    continue
                times_list = [t.strip() for t in times.split(",")]
                channel = bot.get_channel(channel_id)
                if not channel:
                    channel = bot.get_channel(CHAT_CHANNEL_ID)
                for event_time in times_list:
                    if current_time == event_time:
                        embed = discord.Embed(
                            title=f"🎉 بدء الحدث: {event_name}",
                            description=message or "الحدث بدأ الآن!",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="⏰ وقت البدء", value=event_time, inline=True)
                        embed.add_field(name="📅 اليوم", value=current_day, inline=True)
                        embed.add_field(name="🔔 التذكير", value=f"{reminder_minutes} دقيقة", inline=True)
                        if channel:
                            await channel.send(embed=embed)
                        print(f"✅ إرسال إشعار حدث: {event_name} في {event_time}")
                        
                        # دخول القناة الصوتية وتشغيل الرسالة
                        if voice_channel_id:
                            try:
                                voice_channel = bot.get_channel(voice_channel_id)
                                if voice_channel and isinstance(voice_channel, discord.VoiceChannel):
                                    # الاتصال بالقناة الصوتية
                                    vc = await voice_channel.connect()
                                    
                                    # استخدام discord TTS (Text-to-Speech)
                                    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                                        f'echo "{message}"',
                                        executable="ffmpeg"
                                    ))
                                    
                                    vc.play(source, after=lambda e: print(f"✅ انتهى التشغيل: {e}") if e else None)
                                    
                                    # انتظر قليل ثم افصل
                                    await asyncio.sleep(3)
                                    await vc.disconnect()
                                    print(f"✅ تم تشغيل الإعلان الصوتي للحدث: {event_name}")
                            except Exception as e:
                                print(f"❌ خطأ في تشغيل الصوت: {e}")
                    
                    try:
                        reminder_time = (datetime.strptime(event_time, "%H:%M") - timedelta(minutes=reminder_minutes)).strftime("%H:%M")
                        if current_time == reminder_time:
                            embed = discord.Embed(
                                title=f"⏰ تذكير: {event_name}",
                                description=f"الحدث سيبدأ بعد {reminder_minutes} دقيقة!",
                                color=discord.Color.orange()
                            )
                            embed.add_field(name="📝 الرسالة", value=message or "لا توجد رسالة", inline=False)
                            embed.add_field(name="⏰ وقت البدء", value=event_time, inline=True)
                            if channel:
                                await channel.send(embed=embed)
                            print(f"✅ إرسال تذكير للحدث: {event_name}")
                    except:
                        pass
    except Exception as e:
        print(f"❌ خطأ في التحقق من الأحداث: {e}")
