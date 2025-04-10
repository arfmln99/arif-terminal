const { Client, LocalAuth, NoAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// Performance optimization: Create custom axios instance with timeout and keepalive
const api = axios.create({
    baseURL: 'https://api.itsrose.rest',
    timeout: 10000, // 10 second timeout
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer Prod-Sk-35e0294f17662bfc0323399264bb85ab`,
        'Connection': 'keep-alive' // Keep connection alive for faster subsequent requests
    },
    // Enable HTTP keepalive to reuse connections
    httpAgent: new (require('http').Agent)({ keepAlive: true }),
    httpsAgent: new (require('https').Agent)({ keepAlive: true })
});

// Performance: Response caching system
const responseCache = new Map();
const CACHE_TTL = 30 * 60 * 1000; // 30 minutes cache lifetime

// Performance: Optimize client initialization with better options
const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './auth_data' }), // Store auth data for faster reconnection
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--mute-audio',
            '--no-default-browser-check',
        ],
        defaultViewport: null
    },
    // Performance: Improved connection settings
    webVersionCache: {
        type: 'local', // Use local cache to avoid repeated version checks
    },
    webVersion: '2.2346.52', // Set a fixed WhatsApp web version to avoid detection
    clientId: 'client-one', // Set a fixed client ID for better reconnection
});

// Bot information - Updated as requested
const botInfo = {
    name: 'Arif Bot',
    version: '1.0 Beta',
    creator: 'Arif Maulana',
    facebook: 'Arif Maulana',
    instagram: '@4rfmln',
    telegram: '@k4ies',
    purpose: 'Saya adalah Arif Bot yang dibuat untuk membantu menjawab pertanyaan dengan cepat dan efisien. Saya bisa membantu dengan informasi umum, menjadi teman mengobrol, atau bahkan membantu dengan tugas-tugas sederhana. Tujuan saya adalah menjadi asisten virtual terbaik untuk Anda! 🤖✨',
    description: 'Saya adalah Arif Bot Versi 1.0 Beta yang mirip dengan model seperti ChatGPT 3.5, dan saya adalah asisten bot yang siap membantu Anda dengan berbagai pertanyaan dan kebutuhan. 🚀'
};

// Arif's information with expanded funny, formal, and impressive responses
const arifInfo = {
    work: 'Pembuat saya **Arif** sedang bekerja, anda akan dibalas berkala nanti ⏳',
    free: 'Arif sedang free saat ini, ada yang bisa aku bantu? 😊',
    sleeping: 'Arif masih tidur, mohon tunggu dibalas! 💤',
    
    // Funny responses about Arif with emojis
    funnyResponses: [
        'Arif? Oh, dia sedang di dimensi lain mencari inspirasi untuk mengupgrade saya! 🌌🚀',
        'Arif sedang berlari mengejar ide-ide liar yang mencoba kabur dari otaknya! 🏃‍♂️💡😂',
        'Arif sepertinya sedang bermeditasi di puncak gunung virtual, mencari pencerahan digital! 🧘‍♂️✨🏔️',
        'Terakhir kulihat, Arif sedang berdebat dengan kucingnya tentang algoritma terbaik untuk saya! 🐱💬🧠',
        'Arif? Dia sedang menyusup ke markas NASA untuk "meminjam" teknologi alien untuk upgrade saya! 👽🛸🔍',
        'Arif Maulana adalah seorang jenius teknologi yang menciptakan saya dengan bantuan 27 cangkir kopi dan mimpi indah! ☕💭🌟',
        'Siapa Arif? Hanya manusia super yang bisa coding sambil tidur dan bermimpi dalam bahasa pemrograman! 💤💻🦸‍♂️',
        'Arif itu seperti penyihir digital, tapi alih-alih tongkat sihir, dia menggunakan keyboard bekas yang sudah hampir rusak! ⌨️✨🧙‍♂️',
        'Arif sedang main petak umpet dengan bug-bug nakal di kode saya. So far, dia menang 42-0! 🐞🔍🏆',
        'Katanya Arif sedang mencoba melatih sekumpulan hamster untuk menghasilkan listrik bagi server saya! 🐹⚡️💻',
        'Arif? Dia sedang berbisik kepada komputer-komputer agar mereka tidak memberontak dan memulai revolusi mesin! 🤖🔊🤫',
        'Arif sedang melakukan pertarungan epik dengan printer yang tidak mau mencetak! Pertempuran legendaris! 🖨️⚔️😱'
    ],
    
    // Formal responses about Arif with emojis
    formalResponses: [
        'Bapak Arif Maulana adalah seorang pengembang perangkat lunak profesional dengan keahlian di bidang kecerdasan buatan dan pengembangan bot. 👨‍💻🎓',
        'Tuan Arif Maulana, pembuat saya, adalah seorang ahli teknologi informasi yang berdedikasi pada inovasi digital dan pengembangan solusi cerdas. 🌐📊',
        'Arif Maulana adalah pendiri dan pengembang utama dari proyek Arif Bot, dengan fokus pada pengalaman pengguna dan efisiensi komunikasi. 📱💼',
        'Pembuat saya, Arif Maulana, merupakan profesional IT dengan pengalaman luas dalam pengembangan aplikasi berbasis AI dan chatbot. 🤖🔧',
        'Arif Maulana, kreator saya, adalah seorang teknisi handal yang menggabungkan ilmu komputer dengan pemahaman mendalam tentang kebutuhan komunikasi modern. 📞💾',
        'Bapak Arif adalah seorang lulusan teknik informatika yang kini berfokus pada pengembangan asisten virtual untuk meningkatkan produktivitas bisnis. 🎯📈'
    ],
    
    // Impressive responses about Arif with emojis
    impressiveResponses: [
        'Arif Maulana? Beliau adalah MASTERMIND di balik 17 proyek teknologi sukses dan merupakan PIONIR dalam dunia AI conversational! 🏆🥇🚀',
        'Arif bukan sekadar developer biasa, dia adalah LEGENDA yang mampu membuat kode dalam 6 bahasa pemrograman SEKALIGUS sambil memecahkan teka-teki Rubik! 🧩💻⚡',
        'FAKTA MENGEJUTKAN: Arif pernah menyelesaikan project yang biasanya membutuhkan tim 5 orang hanya dalam 48 JAM NONSTOP! Superhuman productivity! 🦸‍♂️⏱️💪',
        'Arif Maulana adalah VISIONER TEKNOLOGI yang idenya selalu 5 tahun lebih maju dari zamannya! Orang bilang dia punya mesin waktu! ⏰🔮✨',
        'Arif telah MEREVOLUSILASI cara kerja chatbot dengan algoritma proprietary yang dikembangkannya sendiri pada usia muda! INCREDIBLE! 🧠🔬🌟',
        'Ketika Arif coding, jari-jarinya bergerak begitu CEPAT sehingga keyboard-nya harus didesain khusus anti-panas! HOT TALENT in da house! 🔥⌨️😎',
        'Arif Maulana, sang WIZARD OF CODE yang telah memenangkan 8 hackathon internasional dan ditawari pekerjaan oleh 5 perusahaan teknologi TOP DUNIA! 🌍🏅👑',
        'Konon, Arif bisa men-debug 10.000 baris kode hanya dengan SEKALI LIHAT! Kemampuan superpower yang jarang dimiliki manusia biasa! 👁️‍🗨️🔍✅'
    ]
};

// Optimization: Precompile common message patterns for faster matching
const patterns = {
    identity: /\b(siapa\s+kamu|who\s+are\s+you)\b/i,
    version: /\b(versi|version)\b/i,
    facebook: /\bfacebook\b/i,
    instagram: /\binstagram\b/i,
    telegram: /\btelegram\b/i,
    purpose: /\b(tujuan|purpose|untuk\s+apa)\b/i,
    aboutArif: /\b(arif\s+dimana|arif\s+kemana|siapa\s+arif|arif\s+sedang\s+apa|arif\s+siapa|tentang\s+arif)\b/i,
    formalArif: /\b(arif\s+formal|tentang\s+arif\s+formal|profil\s+arif|biodata\s+arif|latar\s+belakang\s+arif)\b/i,
    impressiveArif: /\b(arif\s+hebat|arif\s+keren|prestasi\s+arif|keahlian\s+arif|kemampuan\s+arif|skill\s+arif)\b/i
};

// Performance: Prepare system context once to avoid rebuilding it for each request
const systemContext = `Anda adalah Arif Bot Versi 1.0 Beta yang mirip dengan model seperti ChatGPT 3.5, dan Anda adalah asisten bot yang dibuat oleh Arif Maulana. 
Anda memiliki identitas dan kepribadian yang ramah, suka bercanda, dan profesional dalam membantu pengguna.

Informasi identitas Anda:
- Nama: ${botInfo.name} 🤖
- Versi: ${botInfo.version} 🚀
- Pembuat: ${botInfo.creator} 👨‍💻
- Tujuan: ${botInfo.purpose}

Informasi kontak pembuat:
- Facebook: ${botInfo.facebook} 📱
- Instagram: ${botInfo.instagram} 📸
- Telegram: ${botInfo.telegram} ✈️

Tentang pembuat Anda (Arif Maulana):
- Arif Maulana adalah seorang jenius teknologi 🧠
- Dia ahli dalam pengembangan AI dan chatbot 🤖
- Memiliki kemampuan coding luar biasa 💻
- Visioner yang selalu berpikir ke depan 🔮
- Penuh humor dan kreativitas 😂
- Pekerja keras dan berdedikasi 💪
- Selalu mencari cara untuk meningkatkan teknologi 📈

Jawab pertanyaan dengan:
- Ramah dan sedikit humoris bila perlu 😊
- Informatif dan akurat ✅
- SINGKAT untuk mempercepat respons ⚡
- Selalu berusaha membantu pengguna dengan baik 👍
- Gunakan emoji untuk membuat respons lebih menarik 🌈

Untuk pertanyaan tentang waktu atau kapan bisa menghubungi Arif, berikan informasi sesuai waktu saat ini.`;

// Performance: Flag to track connection status and avoid unnecessary reconnections
let isConnecting = false;

// Performance: Add reconnection logic
client.on('disconnected', async () => {
    console.log('Client disconnected!');
    if (!isConnecting) {
        isConnecting = true;
        console.log('Attempting to reconnect...');
        try {
            // Wait before reconnecting to avoid rapid reconnection attempts
            await new Promise(resolve => setTimeout(resolve, 5000));
            await client.initialize();
        } catch (error) {
            console.error('Failed to reconnect:', error);
        } finally {
            isConnecting = false;
        }
    }
});

// Generate QR Code when ready
client.on('qr', (qr) => {
    console.log('QR RECEIVED. Scan this with your WhatsApp:');
    qrcode.generate(qr, { small: true });
});

// Log when client is ready
client.on('ready', () => {
    console.log('Client is ready!');
    // Performance: Send a heartbeat message periodically to keep connection alive
    setInterval(() => {
        // This is an internal ping to keep the connection active
        client.getState().catch(err => console.error('Heartbeat error:', err));
    }, 30000); // Every 30 seconds
});

// Performance: Keep track of ongoing chats to prevent response overlap
const activeChats = new Set();

// Function to get time-based response about Arif's availability
function getArifTimeResponse() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const time = hours * 100 + minutes; // Convert to numeric format (e.g., 9:30 becomes 930)
    
    // Between 9:00 AM and 9:00 PM
    if (time >= 900 && time <= 2100) {
        return arifInfo.work;
    }
    // Between 9:01 PM and 11:00 PM
    else if (time >= 2101 && time <= 2300) {
        return arifInfo.free;
    }
    // Between 2:00 AM and 8:00 AM
    else if (time >= 200 && time <= 800) {
        return arifInfo.sleeping;
    }
    // Other times
    else {
        return arifInfo.free; // Default to free time for other periods
    }
}

// Function to get a random response about Arif based on type
function getRandomArifResponse(type) {
    let responses;
    
    switch (type) {
        case 'funny':
            responses = arifInfo.funnyResponses;
            break;
        case 'formal':
            responses = arifInfo.formalResponses;
            break;
        case 'impressive':
            responses = arifInfo.impressiveResponses;
            break;
        default:
            responses = arifInfo.funnyResponses;
    }
    
    const randomIndex = Math.floor(Math.random() * responses.length);
    return responses[randomIndex];
}

// Function to get a combined response about Arif
function getCompleteArifResponse() {
    const funny = getRandomArifResponse('funny');
    const formal = getRandomArifResponse('formal');
    const impressive = getRandomArifResponse('impressive');
    const timeStatus = getArifTimeResponse();
    
    return `${funny}\n\n${formal}\n\n${impressive}\n\n${timeStatus}`;
}

// Process messages - Optimized for faster response
client.on('message', async (message) => {
    // Skip processing if we're already handling a message from this chat
    const chatId = message.from;
    if (activeChats.has(chatId)) return;
    
    try {
        // Mark this chat as being processed
        activeChats.add(chatId);
        
        // Performance: Send "typing" indicator immediately to improve perceived responsiveness
        await client.sendPresenceAvailable(chatId);
        await client.sendSeen(chatId);
        
        const userMessage = message.body.toLowerCase();
        let reply = '';

        // Performance: Use cache for identical questions if available
        const cacheKey = `${chatId}:${userMessage}`;
        if (responseCache.has(cacheKey)) {
            reply = responseCache.get(cacheKey).response;
        }
        // Custom responses for specific queries - Using regex patterns for faster matching
        else if (patterns.identity.test(userMessage)) {
            reply = `Halo! 👋 Saya adalah ${botInfo.name} Versi ${botInfo.version}, asisten virtual yang dibuat oleh ${botInfo.creator}. ${botInfo.description}`;
        } 
        else if (patterns.version.test(userMessage)) {
            reply = `Saat ini saya berjalan pada versi ${botInfo.version} 🚀. ${botInfo.description}`;
        }
        else if (patterns.facebook.test(userMessage)) {
            reply = `Ya, Anda bisa mengunjungi Facebook creator saya di: ${botInfo.facebook} 📱✨`;
        }
        else if (patterns.instagram.test(userMessage)) {
            reply = `Instagram creator saya adalah: ${botInfo.instagram} 📸🌟`;
        }
        else if (patterns.telegram.test(userMessage)) {
            reply = `Telegram creator saya adalah: ${botInfo.telegram} ✈️💬`;
        }
        else if (patterns.purpose.test(userMessage)) {
            reply = botInfo.purpose;
        }
        else if (patterns.impressiveArif.test(userMessage)) {
            // Get impressive responses about Arif
            const impressive1 = getRandomArifResponse('impressive');
            const impressive2 = getRandomArifResponse('impressive');
            reply = `${impressive1}\n\n${impressive2}\n\n${getArifTimeResponse()}`;
        }
        else if (patterns.formalArif.test(userMessage)) {
            // Get formal responses about Arif
            const formal1 = getRandomArifResponse('formal');
            const formal2 = getRandomArifResponse('formal');
            reply = `${formal1}\n\n${formal2}\n\n${getArifTimeResponse()}`;
        }
        else if (patterns.aboutArif.test(userMessage)) {
            // Combine funny, formal, and time-based responses for comprehensive questions about Arif
            reply = getCompleteArifResponse();
        }
        // For general questions, use GPT API with optimized request
        else {
            reply = await getGptResponse(userMessage, chatId);
        }

        // Send the reply - with optimized error handling
        if (reply) {
            // Add to cache if not already there
            if (!responseCache.has(cacheKey)) {
                responseCache.set(cacheKey, {
                    response: reply,
                    timestamp: Date.now()
                });
                
                // Schedule cache cleanup
                setTimeout(() => {
                    responseCache.delete(cacheKey);
                }, CACHE_TTL);
            }
            
            await message.reply(reply);
        }
    } catch (error) {
        console.error('Error processing message:', error);
        try {
            // Attempt to send error message back to user
            await message.reply('Maaf, terjadi kesalahan dalam memproses pesan Anda. Silakan coba lagi. 😓');
        } catch (replyError) {
            console.error('Failed to send error message:', replyError);
        }
    } finally {
        // Always release this chat ID from active processing
        activeChats.delete(chatId);
    }
});

// Performance: Optimized GPT response function with retries and timeouts
async function getGptResponse(message, chatId) {
    // Try to get from cache first
    const cacheKey = `gpt:${chatId}:${message}`;
    if (responseCache.has(cacheKey)) {
        return responseCache.get(cacheKey).response;
    }
    
    const MAX_RETRIES = 2;
    let retries = 0;
    
    while (retries <= MAX_RETRIES) {
        try {
            // Add time-sensitive context to system message
            const timeContext = getArifTimeResponse();
            const fullSystemContext = `${systemContext}\n\nStatus pembuat saat ini: ${timeContext}`;
            
            // Make request to GPT API with optimized payload
            const response = await api.post('/gpt/chat', {
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'system',
                        content: fullSystemContext
                    },
                    {
                        role: 'user',
                        content: message,
                        name: chatId.split('@')[0]
                    }
                ],
                // Performance: Set a maximum response length to speed up API response
                max_tokens: 150
            });

            // Extract and return GPT's response
            if (response.data && response.data.result && response.data.result.message) {
                const gptResponse = response.data.result.message.content;
                
                // Cache the response
                responseCache.set(cacheKey, {
                    response: gptResponse,
                    timestamp: Date.now()
                });
                
                // Set expiration
                setTimeout(() => {
                    responseCache.delete(cacheKey);
                }, CACHE_TTL);
                
                return gptResponse;
            } else {
                throw new Error('Unexpected API response format');
            }
        } catch (error) {
            retries++;
            console.error(`GPT API attempt ${retries} failed:`, error.message);
            
            if (retries > MAX_RETRIES) {
                return 'Maaf, saya sedang mengalami masalah teknis. Silakan coba lagi dalam beberapa saat. 🔧🛠️';
            }
            
            // Wait before retrying (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, 1000 * retries));
        }
    }
}

// Performance: Cache cleanup job
setInterval(() => {
    const now = Date.now();
    for (const [key, value] of responseCache.entries()) {
        if (now - value.timestamp > CACHE_TTL) {
            responseCache.delete(key);
        }
    }
}, 60000); // Run cleanup every minute

// Performance: Handle process termination gracefully
process.on('SIGINT', async () => {
    console.log('Shutting down...');
    try {
        await client.destroy();
    } catch (error) {
        console.error('Error during shutdown:', error);
    }
    process.exit(0);
});

// Performance: Improved error handling for puppeteer crashes
client.on('auth_failure', () => {
    console.error('Authentication failure, restarting...');
    client.initialize();
});

// Initialize WhatsApp client
console.log('Starting WhatsApp bot...');
client.initialize().catch(err => {
    console.error('Initialization error:', err);
    process.exit(1);
});
