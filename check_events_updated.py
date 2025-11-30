# الجزء المعدّل من check_events مع @everyone

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
                            await channel.send(f"@everyone 📣", embed=embed)
                        print(f"✅ إرسال إشعار حدث: {event_name} في {event_time}")
                        
                        # دخول القناة الصوتية
                        if voice_channel_id:
                            try:
                                voice_channel = bot.get_channel(voice_channel_id)
                                if voice_channel and isinstance(voice_channel, discord.VoiceChannel):
                                    vc = await voice_channel.connect()
                                    print(f"✅ تم الدخول للقناة الصوتية: {voice_channel.name}")
                                    
                                    # إرسال رسالة نصية بدلاً من الصوت (أكثر استقراراً)
                                    if channel:
                                        await channel.send(f"🔊 **الإعلان الصوتي:** {message}")
                                    
                                    # انتظر قليل ثم افصل
                                    await asyncio.sleep(2)
                                    await vc.disconnect()
                                    print(f"✅ تم الانقطاع من الصوتي")
                            except Exception as e:
                                print(f"❌ خطأ في الاتصال الصوتي: {e}")
                    
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
                                await channel.send(f"@everyone ⏰", embed=embed)
                            print(f"✅ إرسال تذكير للحدث: {event_name}")
                    except:
                        pass
    except Exception as e:
        print(f"❌ خطأ في التحقق من الأحداث: {e}")
