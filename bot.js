// Discord Bot - Advanced System
// بوت ديسكورد متقدم مع نظام الأدوار، التصويت، والألعاب

const Discord = require('discord.js');
const sqlite3 = require('sqlite3').verbose();
const client = new Discord.Client({
    intents: [
        Discord.GatewayIntentBits.Guilds,
        Discord.GatewayIntentBits.GuildMessages,
        Discord.GatewayIntentBits.MessageContent,
        Discord.GatewayIntentBits.GuildMembers
    ]
});

// Database Setup
const db = new sqlite3.Database('bot.db');

// Initialize Database Tables
db.serialize(() => {
    // Roles table
    db.run(`CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        role_id TEXT NOT NULL,
        guild_id TEXT NOT NULL,
        assigned_by TEXT,
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
    
    // Polls table
    db.run(`CREATE TABLE IF NOT EXISTS polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        message_id TEXT,
        question TEXT NOT NULL,
        options TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
    
    // Poll votes table
    db.run(`CREATE TABLE IF NOT EXISTS poll_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        poll_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        option_index INTEGER NOT NULL,
        voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (poll_id) REFERENCES polls(id)
    )`);
    
    // Games statistics table
    db.run(`CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        guild_id TEXT NOT NULL,
        game_type TEXT NOT NULL,
        result TEXT,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
});

// 8Ball responses
const eightBallResponses = [
    '✅ نعم بالتأكيد!',
    '🎯 بلا شك!',
    '💯 حتماً!',
    '🤔 ربما...',
    '❌ لا أعتقد ذلك',
    '🚫 بالتأكيد لا',
    '⏳ اسأل لاحقاً',
    '🔮 المستقبل غير واضح',
    '💫 النجوم تقول نعم',
    '🌟 الحظ معك اليوم'
];

// Word game words
const wordGameWords = [
    'برمجة', 'حاسوب', 'ديسكورد', 'لعبة', 'تطوير',
    'تصميم', 'خوارزمية', 'قاعدة', 'بيانات', 'شبكة'
];

// Active games
const activeGames = new Map();

client.on('ready', () => {
    console.log(`✅ تم تسجيل الدخول باسم ${client.user.tag}`);
    client.user.setActivity('!help للمساعدة', { type: Discord.ActivityType.Playing });
});

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    if (!message.content.startsWith('!')) return;
    
    const args = message.content.slice(1).trim().split(/ +/);
    const command = args.shift().toLowerCase();
    
    try {
        // === ROLES SYSTEM === 👑
        if (command === 'role') {
            if (!message.member.permissions.has(Discord.PermissionFlagsBits.ManageRoles)) {
                return message.reply('❌ ليس لديك صلاحية لإدارة الأدوار!');
            }
            
            const subCommand = args[0];
            
            if (subCommand === 'add') {
                const member = message.mentions.members.first();
                const roleName = args.slice(2).join(' ');
                
                if (!member || !roleName) {
                    return message.reply('❌ الاستخدام: `!role add @user role_name`');
                }
                
                const role = message.guild.roles.cache.find(r => r.name === roleName);
                if (!role) {
                    return message.reply('❌ الدور غير موجود!');
                }
                
                await member.roles.add(role);
                
                db.run(
                    'INSERT INTO roles (user_id, role_id, guild_id, assigned_by) VALUES (?, ?, ?, ?)',
                    [member.id, role.id, message.guild.id, message.author.id]
                );
                
                const embed = new Discord.EmbedBuilder()
                    .setColor('#32B8C6')
                    .setTitle('✅ تم إضافة الدور')
                    .setDescription(`تم إضافة دور **${roleName}** إلى ${member}`)
                    .setTimestamp();
                    
                message.reply({ embeds: [embed] });
                
            } else if (subCommand === 'remove') {
                const member = message.mentions.members.first();
                const roleName = args.slice(2).join(' ');
                
                if (!member || !roleName) {
                    return message.reply('❌ الاستخدام: `!role remove @user role_name`');
                }
                
                const role = message.guild.roles.cache.find(r => r.name === roleName);
                if (!role) {
                    return message.reply('❌ الدور غير موجود!');
                }
                
                await member.roles.remove(role);
                
                const embed = new Discord.EmbedBuilder()
                    .setColor('#FF5459')
                    .setTitle('✅ تم إزالة الدور')
                    .setDescription(`تم إزالة دور **${roleName}** من ${member}`)
                    .setTimestamp();
                    
                message.reply({ embeds: [embed] });
            }
        }
        
        if (command === 'roles') {
            const roles = message.guild.roles.cache
                .filter(role => role.name !== '@everyone')
                .map(role => `• ${role.name}`)
                .join('\n');
                
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('👑 الأدوار المتاحة')
                .setDescription(roles || 'لا توجد أدوار')
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
        }
        
        if (command === 'myroles') {
            const userRoles = message.member.roles.cache
                .filter(role => role.name !== '@everyone')
                .map(role => `• ${role.name}`)
                .join('\n');
                
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('👤 أدوارك')
                .setDescription(userRoles || 'ليس لديك أدوار')
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
        }
        
        // === POLL SYSTEM === 🗳️
        if (command === 'poll') {
            const pollData = message.content.match(/"([^"]+)"/g);
            
            if (!pollData || pollData.length < 3) {
                return message.reply('❌ الاستخدام: `!poll "السؤال" "خيار1" "خيار2" "خيار3"`');
            }
            
            const question = pollData[0].replace(/"/g, '');
            const options = pollData.slice(1).map(opt => opt.replace(/"/g, ''));
            
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('🗳️ ' + question)
                .setDescription(options.map((opt, i) => `${i + 1}️⃣ ${opt}`).join('\n\n'))
                .setFooter({ text: 'اضغط على الرقم للتصويت' })
                .setTimestamp();
                
            const pollMessage = await message.reply({ embeds: [embed] });
            
            // Add reactions
            const emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];
            for (let i = 0; i < Math.min(options.length, 10); i++) {
                await pollMessage.react(emojis[i]);
            }
            
            // Save to database
            db.run(
                'INSERT INTO polls (guild_id, channel_id, message_id, question, options, created_by) VALUES (?, ?, ?, ?, ?, ?)',
                [message.guild.id, message.channel.id, pollMessage.id, question, JSON.stringify(options), message.author.id]
            );
        }
        
        if (command === 'pollresults') {
            const pollId = args[0];
            if (!pollId) {
                return message.reply('❌ الاستخدام: `!pollresults [poll_id]`');
            }
            
            db.get('SELECT * FROM polls WHERE id = ?', [pollId], (err, poll) => {
                if (err || !poll) {
                    return message.reply('❌ لم يتم العثور على التصويت!');
                }
                
                db.all('SELECT option_index, COUNT(*) as count FROM poll_votes WHERE poll_id = ? GROUP BY option_index', [pollId], (err, votes) => {
                    const options = JSON.parse(poll.options);
                    const results = options.map((opt, i) => {
                        const voteCount = votes.find(v => v.option_index === i)?.count || 0;
                        return `${i + 1}. ${opt}: **${voteCount}** صوت`;
                    }).join('\n');
                    
                    const embed = new Discord.EmbedBuilder()
                        .setColor('#32B8C6')
                        .setTitle('📊 نتائج التصويت')
                        .setDescription(`**${poll.question}**\n\n${results}`)
                        .setTimestamp();
                        
                    message.reply({ embeds: [embed] });
                });
            });
        }
        
        // === GAMES SYSTEM === 🎮
        if (command === '8ball') {
            const question = args.join(' ');
            if (!question) {
                return message.reply('❌ اسأل سؤالاً!');
            }
            
            const response = eightBallResponses[Math.floor(Math.random() * eightBallResponses.length)];
            
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('🎱 الكرة السحرية')
                .addFields(
                    { name: 'سؤالك', value: question },
                    { name: 'الجواب', value: response }
                )
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
            
            db.run(
                'INSERT INTO games (user_id, guild_id, game_type, result) VALUES (?, ?, ?, ?)',
                [message.author.id, message.guild.id, '8ball', response]
            );
        }
        
        if (command === 'dice' || command === 'roll') {
            const result = Math.floor(Math.random() * 6) + 1;
            const diceEmojis = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];
            
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('🎲 رمي النرد')
                .setDescription(`${diceEmojis[result - 1]} حصلت على: **${result}**`)
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
            
            db.run(
                'INSERT INTO games (user_id, guild_id, game_type, result) VALUES (?, ?, ?, ?)',
                [message.author.id, message.guild.id, 'dice', result.toString()]
            );
        }
        
        if (command === 'coin' || command === 'flip') {
            const result = Math.random() < 0.5 ? 'صورة' : 'كتابة';
            const emoji = result === 'صورة' ? '🪙' : '📄';
            
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('🪙 رمي العملة')
                .setDescription(`${emoji} النتيجة: **${result}**`)
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
            
            db.run(
                'INSERT INTO games (user_id, guild_id, game_type, result) VALUES (?, ?, ?, ?)',
                [message.author.id, message.guild.id, 'coin', result]
            );
        }
        
        if (command === 'wordgame') {
            const word = wordGameWords[Math.floor(Math.random() * wordGameWords.length)];
            const scrambled = word.split('').sort(() => Math.random() - 0.5).join('');
            
            activeGames.set(message.author.id, {
                type: 'word',
                answer: word,
                channel: message.channel.id
            });
            
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('📝 لعبة الكلمات')
                .setDescription(`رتّب الأحرف: **${scrambled}**\nاكتب الكلمة الصحيحة!`)
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
        }
        
        if (command === 'guess') {
            if (!activeGames.has(message.author.id) || activeGames.get(message.author.id).type !== 'guess') {
                const number = Math.floor(Math.random() * 100) + 1;
                activeGames.set(message.author.id, {
                    type: 'guess',
                    answer: number,
                    attempts: 0
                });
                
                return message.reply('🔢 لعبة تخمين الأرقام بدأت! خمّن رقماً من 1 إلى 100');
            }
            
            const guess = parseInt(args[0]);
            if (isNaN(guess)) {
                return message.reply('❌ أدخل رقماً صحيحاً!');
            }
            
            const game = activeGames.get(message.author.id);
            game.attempts++;
            
            if (guess === game.answer) {
                activeGames.delete(message.author.id);
                
                const embed = new Discord.EmbedBuilder()
                    .setColor('#32B8C6')
                    .setTitle('🎉 تهانينا!')
                    .setDescription(`الرقم الصحيح هو **${game.answer}**\nعدد المحاولات: **${game.attempts}**`)
                    .setTimestamp();
                    
                message.reply({ embeds: [embed] });
                
                db.run(
                    'INSERT INTO games (user_id, guild_id, game_type, result) VALUES (?, ?, ?, ?)',
                    [message.author.id, message.guild.id, 'guess', `${game.attempts} attempts`]
                );
            } else if (guess < game.answer) {
                message.reply('📈 الرقم أكبر!');
            } else {
                message.reply('📉 الرقم أصغر!');
            }
        }
        
        // Help command
        if (command === 'help') {
            const embed = new Discord.EmbedBuilder()
                .setColor('#32B8C6')
                .setTitle('📚 قائمة الأوامر')
                .addFields(
                    { name: '👑 الأدوار', value: '`!roles` `!myroles` `!role add` `!role remove`' },
                    { name: '🗳️ التصويت', value: '`!poll` `!pollresults`' },
                    { name: '🎮 الألعاب', value: '`!8ball` `!dice` `!coin` `!wordgame` `!guess`' }
                )
                .setTimestamp();
                
            message.reply({ embeds: [embed] });
        }
        
        // Check for word game answers
        if (activeGames.has(message.author.id) && activeGames.get(message.author.id).type === 'word') {
            const game = activeGames.get(message.author.id);
            if (message.content.toLowerCase() === game.answer) {
                activeGames.delete(message.author.id);
                message.reply('🎉 إجابة صحيحة!');
                
                db.run(
                    'INSERT INTO games (user_id, guild_id, game_type, result) VALUES (?, ?, ?, ?)',
                    [message.author.id, message.guild.id, 'word', 'win']
                );
            }
        }
        
    } catch (error) {
        console.error('Error:', error);
        message.reply('❌ حدث خطأ أثناء تنفيذ الأمر!');
    }
});

// React to poll votes
client.on('messageReactionAdd', async (reaction, user) => {
    if (user.bot) return;
    
    const emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];
    const optionIndex = emojis.indexOf(reaction.emoji.name);
    
    if (optionIndex !== -1) {
        db.get(
            'SELECT id FROM polls WHERE message_id = ?',
            [reaction.message.id],
            (err, poll) => {
                if (poll) {
                    db.run(
                        'INSERT INTO poll_votes (poll_id, user_id, option_index) VALUES (?, ?, ?)',
                        [poll.id, user.id, optionIndex]
                    );
                }
            }
        );
    }
});

// Login
client.login('YOUR_BOT_TOKEN_HERE');
