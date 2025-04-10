const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// Initialize the WhatsApp client
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
    }
});

// API configuration
const API_KEY = 'Prod-Sk-35e0294f17662bfc0323399264bb85ab';
const BASE_URL = 'https://api.itsrose.rest';

// Bot information - Customize these details
const botInfo = {
    name: 'SmartShopBot',
    creator: 'Arif Maulana',
    version: 'Beta 1.0',
    facebook: 'Arif Maulana',
    instagram: '@4rfmln',
    telegram: '@k4ies',
    description: 'Bot ini gratis, tapi hanya bisa menjawab dengan teks saja. Saat ini versi saya adalah Beta 1.0, saya sudah seperti Chat GPT Model 3.5.'
};

// Generate QR Code when ready
client.on('qr', (qr) => {
    console.log('QR RECEIVED. Scan this with your WhatsApp:');
    qrcode.generate(qr, { small: true });
});

// Log when client is ready
client.on('ready', () => {
    console.log('Client is ready!');
});

// Process messages
client.on('message', async (message) => {
    const userMessage = message.body.toLowerCase();
    let reply = '';

    // Custom responses for specific queries
    if (userMessage.includes('siapa kamu') || userMessage.includes('who are you')) {
        reply = `Saya adalah ${botInfo.name}, bot yang dibuat oleh ${botInfo.creator}. Saya adalah bot yang dibuat untuk membantu anda.`;
    } 
    else if (userMessage.includes('versi') || userMessage.includes('version')) {
        reply = `Saat ini saya berjalan pada versi ${botInfo.version}. Saya sudah seperti Chat GPT Model 3.5.`;
    }
    else if (userMessage.includes('facebook')) {
        reply = `Ya, Anda bisa mengunjungi Facebook creator saya di: ${botInfo.facebook}`;
    }
    else if (userMessage.includes('instagram')) {
        reply = `Instagram creator saya adalah: ${botInfo.instagram}`;
    }
    else if (userMessage.includes('telegram')) {
        reply = `Telegram creator saya adalah: ${botInfo.telegram}`;
    }
    // For general questions, use GPT API
    else {
        try {
            reply = await getGptResponse(userMessage, message.from);
        } catch (error) {
            console.error('Error getting GPT response:', error);
            reply = 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda. Silakan coba lagi nanti.';
        }
    }

    // Send the reply
    message.reply(reply);
});

// Function to get response from GPT API
async function getGptResponse(message, sender) {
    try {
        // Prepare context for bot - Customize this for your specific use case
        const botContext = `Anda adalah asisten virtual bernama ${botInfo.name} yang dibuat oleh ${botInfo.creator}.
        Anda selalu ramah, informatif, dan berusaha memberikan informasi yang akurat.
        Jika ditanya tentang diri Anda, beritahu bahwa Anda adalah bot yang dibuat oleh ${botInfo.creator}.
        Jika ditanya tentang versi, beritahu bahwa versi Anda adalah ${botInfo.version}.
        
        Jika ditanya tentang informasi kontak:
        - Facebook: ${botInfo.facebook}
        - Instagram: ${botInfo.instagram}
        - Telegram: ${botInfo.telegram}
        
        Jawab pertanyaan berikut ini dengan ramah dan informatif:`;

        // Make request to GPT API
        const response = await axios.post(`${BASE_URL}/gpt/chat`, {
            model: 'gpt-3.5-turbo',
            messages: [
                {
                    role: 'system',
                    content: botContext
                },
                {
                    role: 'user',
                    content: message,
                    name: sender.split('@')[0]
                }
            ]
        }, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${API_KEY}`
            }
        });

        // Extract and return GPT's response
        if (response.data && response.data.result && response.data.result.message) {
            return response.data.result.message.content;
        } else {
            return 'Maaf, saya tidak bisa mendapatkan informasi yang tepat saat ini. Silakan coba lagi nanti.';
        }
    } catch (error) {
        console.error('Error in GPT API call:', error.response ? error.response.data : error.message);
        throw error;
    }
}

// Initialize WhatsApp client
client.initialize();
