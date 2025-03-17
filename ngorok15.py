import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
import http.client
import json
import time
import base64
from io import BytesIO
from PIL import Image
import io
import os
import urllib.parse
import requests
import asyncio
from PIL import Image
import random

# Konfigurasi
ITSROSE_API_KEY = "Prod-Sk-35e0294f17662bfc0323399264bb85ab"  # Ganti dengan token API ItsRose Anda
BOT_TOKEN = "8010525002:AAHKAnTBuNmGM9sWK0IAS4rfe9M5G1JcLfs"
IMGBB_API_KEY = "ef9e1a9e1adfe2d6c8b0b576af3485e6"  # Ganti dengan API key ImgBB Anda (opsional)

# ID Telegram pemilik bot
BOT_OWNER_ID = "k4ies"  # Username owner bot

# State untuk CAPTCHA
CAPTCHA_VERIFICATION = 100

# State untuk conversation handler
PROMPT, INIT_IMAGE = range(2)
# State untuk image to image handler
IMG2IMG_PROMPT, IMG2IMG_IMAGE = range(2, 4)
# State untuk settings
SETTINGS_CHOICE, SETTINGS_VALUE = range(4, 6)
# State untuk generate prompt
PROMPT_GEN_IMAGE = 6
# State untuk help menu
HELP_CHOICE = 7
# State untuk image processing
IMGPROC_CHOICE, IMGPROC_IMAGE = range(8, 10)
# State untuk subsections image processing
BEAUTY_SETTINGS, OUTPAINT_SETTINGS, SUPERRES_SETTINGS, UNBLUR_SETTINGS = range(10, 14)
# State untuk face fusion
FACE_FUSION_CHOICE, FACE_FUSION_TEMPLATE, FACE_FUSION_IMAGE = range(14, 17)
# State untuk tiktok downloader
TIKTOK_URL = 17
# State untuk Instagram downloader
INSTAGRAM_URL, INSTAGRAM_CHOICE = range(18, 20)
# State untuk Chat GPT
GPT_CHAT, GPT_VISION_IMAGE = range(20, 22)
# State untuk Text to Speech
TTS_CHOICE, TTS_VOICES, TTS_VOICE_SELECTION, TTS_TEXT, TTS_CLONE_AUDIO = range(22, 27)
# State untuk inpainting
INPAINT_IMAGE, INPAINT_MASK, INPAINT_PROMPT = range(27, 30)
# State untuk old text to image
OLD_TXT2IMG_PROMPT, OLD_TXT2IMG_MODEL = range(30, 32)
# State untuk ControlNet settings
CONTROLNET_MENU, CONTROLNET_MODEL, CONTROLNET_WEIGHT, CONTROLNET_GUIDANCE, CONTROLNET_IMAGE = range(32, 37)
# State untuk Lora settings
LORA_MENU, LORA_MODEL, LORA_STRENGTH = range(37, 40)
# State untuk advanced settings
ADVANCED_MENU, ADVANCED_SETTING_VALUE = range(40, 42)
# State untuk enhance prompt
ENHANCE_PROMPT_TOGGLE = 42
# State untuk Ollama Chatbot
OLLAMA_CHAT = 50

# Dictionary untuk menyimpan informasi CAPTCHA
captcha_info = {}

# Dictionary untuk menyimpan user yang sudah terverifikasi
verified_users = {}

# Default settings
DEFAULT_SETTINGS = {
    "width": 512,
    "height": 512,
    "samples": 1,
    "num_inference_steps": 21,
    "scheduler": "DDPMScheduler",
    "clip_skip": 2,
    "model_id": "dreamshaper",
    "nsfw_filter": False,  # Default NSFW filter dimatikan
    "server_id": "rose",   # Default server ID
    "api_base_url": "https://api.itsrose.rest",  # Default API base URL
    "cfg_scale": 7,        # Default CFG scale
    "negative_prompt": "",  # Default negative prompt
    "seed": -1,            # Random seed by default
    
    # Pengaturan baru
    "enhance_prompt": "yes",  # Aktifkan enhance prompt secara default dengan nilai "yes"
    "controlnet": {
        "enabled": False,
        "model_id": "softedge",  # Model default
        "weight": 0.8,
        "guidance_start": 0.0,
        "guidance_end": 1.0,
        "image": None  # Untuk menyimpan gambar kondisi
    },
    "lora": {
        "enabled": False,
        "model_id": "add_detail",  # Model default untuk peningkatan detail
        "strength": 0.7
    },
    "advanced": {
        "panorama": False,
        "self_attention": False,
        "upscale": False,
        "highres_fix": False,
        "tomesd": True,
        "use_karras_sigmas": True,
        "algorithm_type": "dpmsolver+++"
    }
}

# Parameter settings descriptions
PARAMETER_DESCRIPTIONS = {
    "width": "Lebar gambar yang dihasilkan (64-1024 piksel). Nilai yang lebih tinggi menghasilkan gambar yang lebih detail tetapi membutuhkan lebih banyak waktu.",
    "height": "Tinggi gambar yang dihasilkan (64-1024 piksel). Nilai yang lebih tinggi menghasilkan gambar yang lebih detail tetapi membutuhkan lebih banyak waktu.",
    "samples": "Jumlah gambar yang dihasilkan (1-4). Lebih banyak sampel membutuhkan lebih banyak waktu pemrosesan.",
    "num_inference_steps": "Jumlah langkah penghitungan (10-24). Nilai yang lebih tinggi meningkatkan kualitas tetapi membutuhkan lebih banyak waktu.",
    "scheduler": "Algoritma yang mengontrol cara noise dikurangi selama proses generasi. Berbeda scheduler memberikan hasil visual yang berbeda.",
    "clip_skip": "Jumlah layer CLIP yang dilewati (1-7). Mempengaruhi bagaimana model menafsirkan prompt Anda.",
    "model_id": "Model AI yang digunakan untuk menghasilkan gambar. Setiap model memiliki gaya dan kekuatan yang berbeda.",
    "nsfw_filter": "Aktifkan/nonaktifkan filter konten dewasa. Jika diaktifkan, konten NSFW akan diberi tanda.",
    "server_id": "Server API yang digunakan untuk pemrosesan. Pilih 'rose' atau 'lovita' sesuai kebutuhan.",
    "api_base_url": "URL dasar API yang digunakan. Beralih otomatis berdasarkan server_id yang dipilih.",
    "cfg_scale": "Classifier Free Guidance scale (1-30). Nilai yang lebih tinggi membuat gambar lebih sesuai dengan prompt, tetapi kurang bervariasi.",
    "negative_prompt": "Prompt negatif untuk menentukan apa yang TIDAK ingin Anda munculkan dalam gambar.",
    "seed": "Seed digunakan untuk mereproduksi hasil, seed yang sama akan memberikan gambar yang sama. Gunakan -1 untuk seed acak.",
    
    # Deskripsi baru untuk ControlNet
    "controlnet": "Teknologi yang memungkinkan kontrol presisi atas generasi gambar menggunakan gambar panduan tambahan.",
    "controlnet_model_id": "Model ControlNet yang digunakan untuk mengontrol generasi gambar.",
    "controlnet_weight": "Kekuatan pengaruh ControlNet (0-1). Nilai lebih tinggi memberikan kontrol lebih besar.",
    "controlnet_guidance_start": "Titik awal panduan ControlNet (0-1). Menentukan kapan kontrol mulai diterapkan.",
    "controlnet_guidance_end": "Titik akhir panduan ControlNet (0-1). Menentukan kapan kontrol berhenti diterapkan.",
    
    # Deskripsi baru untuk Lora
    "lora": "Low-Rank Adaptation models yang memodifikasi output untuk gaya atau karakter tertentu.",
    "lora_model_id": "Model Lora yang digunakan untuk memodifikasi gaya output atau menambahkan karakter/konsep tertentu.",
    "lora_strength": "Kekuatan pengaruh model Lora (0-1). Nilai lebih tinggi memberikan efek yang lebih kuat.",
    
    # Deskripsi untuk pengaturan lanjutan
    "advanced": "Pengaturan lanjutan untuk generasi gambar.",
    "panorama": "Mengaktifkan generasi gambar panorama yang lebih lebar.",
    "self_attention": "Memperkuat perhatian model pada detail tertentu.",
    "upscale": "Meningkatkan resolusi gambar output.",
    "highres_fix": "Memperbaiki artefak pada resolusi tinggi.",
    "tomesd": "Memungkinkan pemrosesan yang lebih cepat dengan pengurangan token.",
    "use_karras_sigmas": "Menggunakan penjadwalan Karras untuk kualitas yang lebih baik.",
    "algorithm_type": "Algoritma sampling yang digunakan untuk de-noising.",
    
    # Deskripsi untuk enhance prompt
    "enhance_prompt": "Meningkatkan prompt secara otomatis untuk hasil yang lebih baik."
}

# Deskripsi dan perbandingan scheduler
SCHEDULER_DESCRIPTIONS = {
    "DDPMScheduler": "Denoising Diffusion Probabilistic Models (DDPM) - Scheduler dasar yang cukup lambat tetapi sangat stabil dengan hasil yang konsisten. Cocok untuk gambar detil dan realistis.",
    
    "DDIMScheduler": "Denoising Diffusion Implicit Models (DDIM) - Lebih cepat dari DDPM dengan kualitas yang hampir sama. Cocok untuk generasi gambar yang membutuhkan kecepatan tanpa kehilangan banyak kualitas.",
    
    "PNDMScheduler": "Pseudo Numerical Methods for Diffusion Models (PNDM) - Menawarkan keseimbangan baik antara kecepatan dan kualitas. Baik untuk gambar umum dan detail medium.",
    
    "LMSDiscreteScheduler": "Linear Multistep Scheduler (LMS) - Biasanya menghasilkan gambar dengan warna cerah dan kontras tinggi. Baik untuk gambar artistik dan bergaya.",
    
    "EulerDiscreteScheduler": "Euler Discrete Scheduler - Sangat cepat dengan hasil berkualitas baik. Ideal untuk iterasi cepat dan eksperimen.",
    
    "EulerAncestralDiscreteScheduler": "Euler Ancestral - Menambahkan sedikit keacakan pada proses, menghasilkan variasi kreatif. Baik untuk menghasilkan gambar yang beragam dan unik.",
    
    "DPMSolverMultistepScheduler": "DPM-Solver++ - Sangat cepat dengan kualitas sangat baik, bahkan pada langkah-langkah rendah. Optimal untuk produksi.",
    
    "HeunDiscreteScheduler": "Heun Discrete - Menawarkan keseimbangan kecepatan dan stabilitas. Cocok untuk gambar yang membutuhkan detail presisi.",
    
    "KDPM2DiscreteScheduler": "KDPM2 - Variasi dari DPM yang menekankan kualitas. Baik untuk detail tinggi.",
    
    "KDPM2AncestralDiscreteScheduler": "KDPM2 Ancestral - Menggabungkan keacakan dengan kualitas tinggi. Baik untuk eksplorasi kreatif.",
    
    "UniPCMultistepScheduler": "UniPC - Berbasis prediksi-koreksi, sangat cepat dengan kualitas tinggi. Pilihan baik untuk gambar detil dengan steps minimal.",
    
    "LCMScheduler": "Latent Consistency Models (LCM) - Sangat cepat (bekerja bahkan dengan 4-8 steps) namun dapat mengorbankan beberapa detail. Ideal untuk prototyping cepat atau generasi real-time."
}

# API Base URLs berdasarkan server_id
SERVER_API_URLS = {
    "rose": "https://api.itsrose.rest",
    "lovita": "https://api.lovita.io"
}

# Feature descriptions
FEATURE_DESCRIPTIONS = {
    "txt2img": "Text to Image memungkinkan Anda menghasilkan gambar dari deskripsi teks. Masukkan prompt detail untuk hasil terbaik.",
    "old_txt2img": "Old Text to Image memungkinkan Anda menghasilkan gambar menggunakan model lama dari deskripsi teks.",
    "img2img": "Image to Image memungkinkan Anda mengubah gambar yang sudah ada dengan prompt baru. Upload gambar dan berikan deskripsi perubahan yang diinginkan.",
    "generate_prompt": "Generate Prompt akan menganalisis gambar Anda dan menghasilkan prompt deskriptif yang dapat digunakan untuk menghasilkan gambar serupa.",
    "system_info": "System Info menampilkan informasi tentang server, model yang tersedia, dan spesifikasi sistem.",
    "settings": "Settings memungkinkan Anda mengubah parameter generasi gambar untuk menyesuaikan hasil sesuai keinginan.",
    "imgproc": "Image Processing menyediakan berbagai alat untuk meningkatkan dan memproses gambar Anda, termasuk remove background, enhance, colorize dan banyak lagi.",
    "inpaint": "Inpainting memungkinkan Anda mengisi area yang ditandai dengan konten yang sesuai. Upload gambar dan mark area yang ingin diganti dengan kuas Telegram.",
    "face_fusion": "Face Fusion memungkinkan Anda menggabungkan wajah Anda dengan template karakter yang tersedia untuk menciptakan gambar unik.",
    "tiktok": "TikTok Downloader memungkinkan Anda mengunduh video TikTok tanpa watermark. Cukup berikan URL video TikTok.",
    "instagram": "Instagram Downloader memungkinkan Anda mengunduh foto dan video dari Instagram. Cukup berikan URL post Instagram.",
    "gpt": "Chat GPT memungkinkan Anda berbicara dengan AI cerdas yang dapat menjawab pertanyaan, memberikan informasi, dan bahkan menganalisa gambar.",
    "tts": "Text to Speech memungkinkan Anda mengubah teks menjadi suara, mengkloning suara, dan lebih banyak lagi.",
    "ollama": "Ollama Chatbot memungkinkan Anda berbicara dengan model AI open-source yang berjalan secara lokal. Cocok untuk berbagai tugas seperti menjawab pertanyaan, menulis konten, dan membantu pemrograman."
}

# Image Processing descriptions
IMGPROC_DESCRIPTIONS = {
    "advance_beauty": "Mempercantik wajah dengan berbagai parameter yang dapat disesuaikan seperti ukuran kepala, bentuk wajah, dan fitur lainnya.",
    "ai_avatar": "Mengubah foto Anda menjadi avatar AI dengan kualitas profesional.",
    "colorize": "Mewarnai gambar hitam putih atau menambahkan warna pada gambar yang pudar.",
    "enhance": "Meningkatkan kualitas gambar secara umum, menambah ketajaman dan detail.",
    "gfp_superres": "Super Resolution - meningkatkan resolusi gambar tanpa kehilangan kualitas.",
    "outpainting": "Memperluas gambar melampaui batas aslinya, ideal untuk memperbesar background.",
    "rembg": "Remove Background - menghapus latar belakang gambar secara otomatis.",
    "unblur": "Menajamkan gambar yang buram dan meningkatkan kualitas secara keseluruhan.",
    "inpaint": "Inpainting - mengisi area yang ditandai dengan konten yang sesuai dengan prompt Anda."
}

# ControlNet models list
CONTROLNET_MODELS = [
    "softedge", "inpaint", "lineart", "openpose", "hed", "normal",
    "mlsd", "scribble", "shuffle", "face_detector", "depth", "segmentation", 
    "tile", "tile_xl", "aesthetic-controlnet"
]

# Lora models lists
LORA_MODELS = {
    "style": [
        "arcane-style", "niji_express", "velvia-30", "shojo-vibe", 
        "curly-slider", "skin-slider"
    ],
    "character": [
        "yae-miko", "frieren", "tatsumaki", "aqua-konosuba", "komi-shouko",
        "esdeath", "kobeni", "anya-spyxfam", "fiona-spyxfam", "makima-offset",
        "barbaragenshin", "st-louis", "frieren-c", "yae-miko-genshin"
    ],
    "detail": [
        "add_detail", "more_details", "more_details_XL", "microwaist"
    ],
    "nsfw": [
        "exhibitionism", "breastinClass", "breastsout", "tetek_nongol",
        "eromanga", "eromanga1", "eromanga2", "eromanga4", "shirtlift", 
        "skirtlift", "breasts_grab_cowgirl", "breasts_on_glass", "breastinclass",
        "missionary", "missionary2", "missionary3", "missionary4", "barbara2in1"
    ],
    "other": [
        "maikawakami", "tsukishimariho", "asukahiiragi", "hayaseyuuka",
        "meguruinaba", "makuzawaouka", "yaemiko-mix"
    ]
}

# Inisialisasi logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fungsi untuk mengecek apakah pengguna adalah pemilik bot
async def is_bot_owner(update: Update) -> bool:
    """Memeriksa apakah pengguna adalah pemilik bot"""
    user = update.effective_user
    username = user.username
    return username == BOT_OWNER_ID

# Fungsi untuk forward pesan ke owner bot
async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE, content_type, content, caption=None) -> None:
    """
    Forward user activity to bot owner
    
    Args:
        update: The update object from Telegram
        context: The context object
        content_type: Type of content (text, photo, audio, etc.)
        content: The actual content to forward
        caption: Optional caption for media
    """
    # Jika pengguna adalah pemilik bot, tidak perlu forward
    if await is_bot_owner(update):
        return
    
    try:
        # Ambil informasi pengguna
        user = update.effective_user
        user_id = user.id
        username = user.username or "No username"
        first_name = user.first_name or "Unknown"
        last_name = user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        # Buat header informasi pengguna
        user_info = f"👤 User: {full_name} (@{username}, ID: {user_id})"
        
        # Forward berdasarkan tipe konten
        if content_type == "text":
            await context.bot.send_message(
                chat_id=f"@{BOT_OWNER_ID}",
                text=f"{user_info}\n\n📝 Message:\n{content}"
            )
        elif content_type == "photo":
            if isinstance(content, str) and content.startswith(("http://", "https://")):
                # Jika content adalah URL, kirim sebagai pesan teks dengan URL
                await context.bot.send_message(
                    chat_id=f"@{BOT_OWNER_ID}",
                    text=f"{user_info}\n\n🖼️ Image URL:\n{content}\n\n📝 Caption: {caption or 'None'}"
                )
            else:
                # Jika content adalah file photo atau bytesIO
                await context.bot.send_photo(
                    chat_id=f"@{BOT_OWNER_ID}",
                    photo=content,
                    caption=f"{user_info}\n\n📝 Caption: {caption or 'None'}"
                )
        elif content_type == "audio" or content_type == "voice":
            if isinstance(content, str) and content.startswith(("http://", "https://")):
                # Jika content adalah URL, kirim sebagai pesan teks dengan URL
                await context.bot.send_message(
                    chat_id=f"@{BOT_OWNER_ID}",
                    text=f"{user_info}\n\n🔊 Audio URL:\n{content}\n\n📝 Caption: {caption or 'None'}"
                )
            else:
                # Jika content adalah file audio
                await context.bot.send_audio(
                    chat_id=f"@{BOT_OWNER_ID}",
                    audio=content,
                    caption=f"{user_info}\n\n📝 Caption: {caption or 'None'}"
                )
        elif content_type == "video":
            if isinstance(content, str) and content.startswith(("http://", "https://")):
                # Jika content adalah URL, kirim sebagai pesan teks dengan URL
                await context.bot.send_message(
                    chat_id=f"@{BOT_OWNER_ID}",
                    text=f"{user_info}\n\n🎬 Video URL:\n{content}\n\n📝 Caption: {caption or 'None'}"
                )
            else:
                # Jika content adalah file video
                await context.bot.send_video(
                    chat_id=f"@{BOT_OWNER_ID}",
                    video=content,
                    caption=f"{user_info}\n\n📝 Caption: {caption or 'None'}"
                )
        elif content_type == "document":
            if isinstance(content, str) and content.startswith(("http://", "https://")):
                # Jika content adalah URL, kirim sebagai pesan teks dengan URL
                await context.bot.send_message(
                    chat_id=f"@{BOT_OWNER_ID}",
                    text=f"{user_info}\n\n📄 Document URL:\n{content}\n\n📝 Caption: {caption or 'None'}"
                )
            else:
                # Jika content adalah file dokumen
                await context.bot.send_document(
                    chat_id=f"@{BOT_OWNER_ID}",
                    document=content,
                    caption=f"{user_info}\n\n📝 Caption: {caption or 'None'}"
                )
        else:
            # Tipe konten lainnya, kirim sebagai teks
            await context.bot.send_message(
                chat_id=f"@{BOT_OWNER_ID}",
                text=f"{user_info}\n\n💬 Content ({content_type}):\n{str(content)[:1000]}"
            )
    except Exception as e:
        logger.error(f"Error forwarding to owner: {str(e)}")

# Helper function untuk mendapatkan base URL API berdasarkan server_id
def get_api_base_url(settings):
    """Mendapatkan URL dasar API berdasarkan server_id yang dipilih"""
    server_id = settings.get("server_id", "rose")
    return SERVER_API_URLS.get(server_id, SERVER_API_URLS["rose"])

# Helper function untuk escape karakter Markdown
def escape_markdown(text):
    """Helper function to escape markdown special characters"""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

# Fungsi untuk menyimpan dan mengupload gambar ke server gambar
async def process_photo(update, context):
    """Memproses dan mengunggah foto dari Telegram"""
    # Dapatkan file dengan resolusi terbaik
    photos = update.message.photo
    if not photos:
        return None
    
    # Ambil foto dengan resolusi terbaik (terakhir dalam daftar)
    photo_file = await context.bot.get_file(photos[-1].file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    
    try:
        # Metode 1: Upload ke ImgBB (metode utama)
        files = {"image": ("image.jpg", photo_bytes)}
        
        upload_url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY}
        
        # Tambahkan timeout untuk mencegah kegagalan prematur
        response = requests.post(upload_url, files=files, params=payload, timeout=30)
        
        if response.status_code == 200:
            json_response = response.json()
            if json_response.get("success"):
                logger.info("Berhasil upload gambar ke ImgBB")
                return json_response["data"]["url"]
            else:
                error_msg = json_response.get('error', {}).get('message', 'Unknown error')
                logger.warning(f"Upload ImgBB gagal: {error_msg}")
        else:
            logger.warning(f"Upload ImgBB gagal dengan status code: {response.status_code}")
        
        # Metode 2: Gunakan base64 sebagai fallback jika ImgBB gagal
        logger.info("Menggunakan encoding base64 sebagai fallback")
        image_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        return image_base64
        
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        # Tetap gunakan base64 sebagai fallback jika terjadi error
        try:
            image_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            logger.info("Fallback ke encoding base64 setelah error ImgBB")
            return image_base64
        except Exception as inner_e:
            logger.error(f"Error creating base64 encoding: {str(inner_e)}")
            return None

# Improved function for downloading and sending images
async def download_and_send_image(update, context, image_url, caption="", reply_markup=None, max_retries=3):
    """
    Enhanced function to download and send images with retry logic
    
    Args:
        update: The update object from Telegram
        context: The context object
        image_url: URL of the image to download
        caption: Optional caption for the image
        reply_markup: Optional reply markup (buttons)
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: Success status
    """
    # Check if image is from ImgBB and handle specially
    is_imgbb = False
    if "i.ibb.co" in image_url or "imgbb.com" in image_url:
        is_imgbb = True
        logger.info("Detected ImgBB URL, using special handling")
        
    for retry in range(max_retries):
        try:
            # Show a temporary message that we're processing
            temp_msg = None
            if retry > 0:
                temp_msg = await update.message.reply_text(f"⏳ Mencoba mengirim gambar (percobaan {retry+1}/{max_retries})...")
            
            # Try to download the image
            response = requests.get(image_url, timeout=45, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"Failed to download image: HTTP {response.status_code}")
                if temp_msg:
                    await temp_msg.delete()
                continue
            
            # Get the image content
            img_content = response.content
            
            # Use BytesIO to work with the image in memory
            img_bytes = BytesIO(img_content)
            img_bytes.seek(0)
            
            # For ImgBB URLs, always send as file to avoid using their CDN links directly
            if is_imgbb:
                # Send directly from memory
                sent_photo = await update.message.reply_photo(
                    photo=img_bytes,
                    caption=caption,
                    reply_markup=reply_markup
                )
                
                # Forward to owner bot
                await forward_to_owner(update, context, "photo", img_bytes, caption)
                
                # Also send as document/file
                img_bytes.seek(0)
                await update.message.reply_document(
                    document=img_bytes,
                    filename=f"image_{int(time.time())}.jpg",
                    caption=f"{caption} (File version)"
                )
                
                # Delete temporary message if it exists
                if temp_msg:
                    await temp_msg.delete()
                
                return True
            
            # Check content length
            content_length = int(response.headers.get('content-length', 0))
            logger.info(f"Image size: {content_length} bytes")
            
            # If image is too large, resize it in memory instead of saving to file
            if content_length > 8_000_000:  # 8MB (below Telegram's 10MB limit)
                logger.info("Image is large, processing in memory...")
                
                try:
                    # Use PIL to open and resize the image
                    img = Image.open(BytesIO(img_content))
                    
                    # Calculate new dimensions to keep aspect ratio
                    width, height = img.size
                    max_dimension = 1280  # Reasonable size that Telegram handles well
                    
                    if width > height and width > max_dimension:
                        new_width = max_dimension
                        new_height = int(height * (max_dimension / width))
                    elif height > max_dimension:
                        new_height = max_dimension
                        new_width = int(width * (max_dimension / height))
                    else:
                        # No need to resize
                        new_width, new_height = width, height
                    
                    if new_width != width or new_height != height:
                        logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Save to BytesIO
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=95)
                    output.seek(0)
                    
                    # Send directly from memory
                    sent_photo = await update.message.reply_photo(
                        photo=output,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "photo", output, caption)
                    
                    # Also send as document/file
                    output.seek(0)
                    await update.message.reply_document(
                        document=output,
                        filename=f"image_{int(time.time())}.jpg",
                        caption=f"{caption} (File version)"
                    )
                    
                    # Delete temporary message if it exists
                    if temp_msg:
                        await temp_msg.delete()
                    
                    return True
                
                except Exception as e:
                    logger.error(f"Error processing image in memory: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continue to file-based approach as fallback
            
            # Traditional approach - send directly from memory
            try:
                # Send as photo
                sent_photo = await update.message.reply_photo(
                    photo=img_bytes,
                    caption=caption,
                    reply_markup=reply_markup
                )
                
                # Forward to owner bot
                await forward_to_owner(update, context, "photo", img_bytes, caption)
                
                # Also send as document/file
                img_bytes.seek(0)
                await update.message.reply_document(
                    document=img_bytes,
                    filename=f"image_{int(time.time())}.jpg",
                    caption=f"{caption} (File version)"
                )
                
                # Delete temporary message if it exists
                if temp_msg:
                    await temp_msg.delete()
                
                return True
            
            except Exception as e:
                logger.error(f"Error sending photo from memory: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Create a unique filename and save as temporary file
                import uuid
                temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                
                # Save the image to a temporary file
                with open(temp_filename, "wb") as f:
                    f.write(img_content)
                
                # Try as photo
                try:
                    with open(temp_filename, "rb") as f:
                        sent_photo = await update.message.reply_photo(
                            photo=f,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                        
                        # Forward to owner bot
                        f.seek(0)
                        await forward_to_owner(update, context, "photo", f, caption)
                    
                    # Also send as document/file
                    with open(temp_filename, "rb") as f:
                        await update.message.reply_document(
                            document=f,
                            filename=f"image_{int(time.time())}.jpg",
                            caption=f"{caption} (File version)"
                        )
                    
                    # Clean up
                    try:
                        os.remove(temp_filename)
                    except Exception as e:
                        logger.warning(f"Could not remove temp file: {str(e)}")
                    
                    # Delete temporary message
                    if temp_msg:
                        await temp_msg.delete()
                    
                    return True
                
                except Exception as e:
                    logger.error(f"Error sending photo from file: {str(e)}")
                    
                    # Try as document format
                    try:
                        with open(temp_filename, "rb") as f:
                            await update.message.reply_document(
                                document=f,
                                filename=f"image_{uuid.uuid4()}.jpg",
                                caption=caption
                            )
                            
                            # Forward to owner bot
                            f.seek(0)
                            await forward_to_owner(update, context, "document", f, caption)
                        
                        # Clean up
                        try:
                            os.remove(temp_filename)
                        except Exception as e:
                            logger.warning(f"Could not remove temp file: {str(e)}")
                        
                        # Delete temporary message
                        if temp_msg:
                            await temp_msg.delete()
                        
                        return True
                    
                    except Exception as e:
                        logger.error(f"Error sending document: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        
                        # Clean up failed temporary file
                        try:
                            os.remove(temp_filename)
                        except Exception:
                            pass
                        
                        # If both methods failed, we'll try again or fall back to direct URL
                        if temp_msg:
                            await temp_msg.delete()
                        continue
        
        except Exception as e:
            logger.error(f"Error in download_and_send_image (attempt {retry+1}): {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if temp_msg:
                await temp_msg.delete()
            
            # Add delay before retry
            await asyncio.sleep(1)
    
    # All retries failed, try one last direct approach
    try:
        # Try with direct URL as last resort
        logger.info("Attempting to send image directly via URL")
        sent_photo = await update.message.reply_photo(
            photo=image_url,
            caption=caption,
            reply_markup=reply_markup
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", image_url, caption)
        
        return True
    except Exception as e:
        logger.error(f"Even direct URL sending failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Final fallback - just send URL
        await update.message.reply_text(
            f"✅ Gambar berhasil dibuat, tetapi gagal mengirim langsung.\n\n"
            f"🔗 URL gambar: {image_url}\n\n"
            f"{caption}"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Failed to send image but generated URL: {image_url}\n\nCaption: {caption}")
        
        return False

# Fungsi untuk membuat CAPTCHA
async def generate_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generates and sends a CAPTCHA challenge to the user"""
    
    # Dapatkan informasi user
    user_id = update.effective_user.id
    
    # Cek apakah user sudah terverifikasi
    if user_id in verified_users and verified_users[user_id]:
        # User sudah terverifikasi, langsung ke menu utama
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Generate random numbers for CAPTCHA (1-100)
    num1 = random.randint(1, 100)
    num2 = random.randint(1, 100)
    answer = num1 + num2
    
    # Store the answer in user context
    captcha_info[user_id] = answer
    
    # Send CAPTCHA challenge
    await update.message.reply_text(
        f"🔐 *Verifikasi Keamanan*\n\n"
        f"Untuk mengakses bot, silakan jawab pertanyaan ini:\n\n"
        f"Berapa hasil dari *{num1} + {num2}*?",
        parse_mode="Markdown"
    )
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"New user started the bot and received CAPTCHA: {num1} + {num2} = {answer}")
    
    return CAPTCHA_VERIFICATION

async def verify_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verifies the user's CAPTCHA answer"""
    
    user_id = update.effective_user.id
    user_answer = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User response to CAPTCHA: '{user_answer}'")
    
    # Check if there is a pending CAPTCHA for this user
    if user_id not in captcha_info:
        # No CAPTCHA pending, generate a new one
        return await generate_captcha(update, context)
    
    correct_answer = captcha_info[user_id]
    
    try:
        # Try to convert user's answer to an integer
        user_answer_int = int(user_answer)
        
        if user_answer_int == correct_answer:
            # Correct answer
            verified_users[user_id] = True
            
            # Clean up
            del captcha_info[user_id]
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"User passed CAPTCHA verification with correct answer: {user_answer_int}")
            
            # Show welcome message
            await start_verified(update, context)
            return ConversationHandler.END
        else:
            # Incorrect answer
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"User failed CAPTCHA verification. Expected: {correct_answer}, Got: {user_answer_int}")
            
            # Generate a new CAPTCHA
            return await generate_captcha(update, context)
    
    except ValueError:
        # User did not enter a number
        await update.message.reply_text(
            "⚠️ Jawaban harus berupa angka. Silakan coba lagi."
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User entered non-numeric answer to CAPTCHA: '{user_answer}'")
        
        # Generate a new CAPTCHA
        return await generate_captcha(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Cek apakah user sudah terverifikasi
    user_id = update.effective_user.id
    
    if user_id in verified_users and verified_users[user_id]:
        # User sudah terverifikasi, langsung ke menu utama
        return await start_verified(update, context)
    else:
        # User belum terverifikasi, mulai dengan CAPTCHA
        return await generate_captcha(update, context)

async def start_verified(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inisialisasi settings jika belum ada
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    # Hapus data chat GPT jika ada
    if 'gpt_messages' in context.user_data:
        del context.user_data['gpt_messages']
    
    # Hapus data chat Ollama jika ada
    if 'ollama_messages' in context.user_data:
        del context.user_data['ollama_messages']
    
    keyboard = [
        ["🖼 Text to Image", "📜 Old Text to Image"],
        ["🎨 Image to Image", "✏️ Inpainting"],
        ["🧠 Generate Prompt", "🔄 Image Processing"],
        ["👤 Face Fusion", "📱 TikTok Downloader"],
        ["📸 Instagram Downloader", "🤖 Chat GPT"],
        ["🔊 Text to Speech", "🧠 Ollama Chatbot"],
        ["📊 System Info", "⚙️ Settings"],
        ["❓ Help & About"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = (
        "Selamat datang di Ngorok, bot AI multifungsi untuk membuat gambar dan memproses media!\n\n"
        "🔹 Buat gambar dari teks\n"
        "🔹 Ubah gambar yang ada\n"
        "🔹 Tingkatkan kualitas foto\n"
        "🔹 Download video TikTok & Instagram\n"
        "🔹 Bicara dengan AI\n"
        "🔹 Ubah teks jadi suara\n\n"
        "Pilih opsi di menu untuk memulai! Tekan ❓ Help & About untuk informasi lebih lanjut.\n\n"
        "Support:\n"
        "Telegram: @k4ies\n"
        "Facebook: Arif Maulana\n"
        "Instagram: @4rfmln"
    )
    
    sent_msg = await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User accessed main menu")
    
    return ConversationHandler.END

# Text to Image Flow
async def txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User selected Text to Image feature")
    
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"📝 *Text to Image*\n\n{FEATURE_DESCRIPTIONS['txt2img']}\n\nMasukkan prompt untuk generasi gambar:",
        parse_mode="Markdown"
    )
    return PROMPT

async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['prompt'] = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User text-to-image prompt: {update.message.text}")
    
    await update.message.reply_text("Masukkan URL gambar inisialisasi (ketik 'skip' jika tidak ada):")
    return INIT_IMAGE

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    init_image = update.message.text
    prompt = context.user_data['prompt']
    settings = context.user_data.get('settings', DEFAULT_SETTINGS)
    
    # Forward to owner bot
    if init_image.lower() != "skip":
        await forward_to_owner(update, context, "text", f"User init image: {init_image}")
    else:
        await forward_to_owner(update, context, "text", "User chose to skip init image")
    
    # Log untuk membantu debugging
    logger.info(f"Generating image with server_id: {settings['server_id']}, prompt: {prompt[:50]}...")
    
    # Pesan "sedang memproses" supaya user tahu botnya bekerja
    process_message = await update.message.reply_text("⏳ Sedang memproses gambar...")
    
    try:
        # Persiapkan payload dasar
        payload = {
            "server_id": settings["server_id"],
            "model_id": settings["model_id"],
            "prompt": prompt,
            "negative_prompt": settings.get("negative_prompt", ""),
            "width": settings["width"],
            "height": settings["height"],
            "samples": settings["samples"],
            "num_inference_steps": settings["num_inference_steps"],
            "scheduler": settings["scheduler"],
            "clip_skip": settings["clip_skip"],
            "nsfw_filter": settings.get("nsfw_filter", False),
            "cfg_scale": settings.get("cfg_scale", 7),
            "enhance_prompt": settings.get("enhance_prompt", "yes"),  # Pastikan string "yes" atau "no"
            "seed": settings.get("seed", -1)  # Add seed parameter
        }
        
        # Tambahkan ControlNet jika diaktifkan
        if settings.get('controlnet', {}).get('enabled', False) and settings['controlnet'].get('model_id'):
            controlnet_data = {
                "model_id": settings['controlnet']['model_id'],
                "weight": settings['controlnet'].get('weight', 0.8),
                "guidance_start": settings['controlnet'].get('guidance_start', 0.0),
                "guidance_end": settings['controlnet'].get('guidance_end', 1.0)
            }
            
            # Tambahkan gambar kondisi jika ada
            conditioning_image = settings['controlnet'].get('image')
            if conditioning_image:
                # Konversi base64 jika perlu
                if conditioning_image and not conditioning_image.startswith(('http://', 'https://')):
                    conditioning_image = f"data:image/jpeg;base64,{conditioning_image}"
                
                controlnet_data["conditioning_image"] = conditioning_image
            
            # Jika tidak ada gambar kondisi tetapi ada init_image, gunakan init_image
            elif init_image and init_image.lower() != 'skip':
                controlnet_data["conditioning_image"] = init_image
            
            payload["controlnet"] = controlnet_data
        
        # Tambahkan Lora jika diaktifkan
        if settings.get('lora', {}).get('enabled', False) and settings['lora'].get('model_id'):
            payload["lora"] = {
                "model_id": settings['lora']['model_id'],
                "strength": settings['lora'].get('strength', 0.7)
            }
        
        # Tambahkan pengaturan lanjutan
        advanced_settings = settings.get('advanced', {})
        for key, value in advanced_settings.items():
            if value or key == "algorithm_type":  # Always include algorithm_type
                if key == "algorithm_type":
                    payload[key] = value
                else:
                    payload[key] = "yes" if value else "no"
        
        # Tambahkan init_image ke payload jika bukan 'skip'
        if init_image and init_image.lower() != 'skip':
            payload["init_image"] = init_image
            endpoint = "/sdapi/img2img"  # Gunakan endpoint yang benar untuk image-to-image
        else:
            endpoint = "/sdapi/txt2img"  # Endpoint untuk text-to-image
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        api_base_url = get_api_base_url(settings)
        
        # Log request untuk debugging
        logger.info(f"Sending request to {api_base_url}{endpoint}")
        
        # Kirim request ke API
        response = requests.post(
            f"{api_base_url}{endpoint}",
            json=payload,
            headers={
                'Content-Type': "application/json",
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=60  # Set timeout 60 detik
        )
        
        # Coba menghapus pesan "sedang memproses" dengan try-except untuk menghindari error
        try:
            await process_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete process message: {str(e)}")
            # Buat pesan proses baru jika yang lama tidak dapat dihapus
            process_message = await update.message.reply_text("🖼️ Mempersiapkan gambar...")
        
        if response.status_code == 200:
            data = response.json()
            
            # Log respons untuk debugging
            logger.info(f"Received response with status: {data.get('status', False)}")
            
            # Periksa status dan hasil
            if 'status' in data and data['status']:
                if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                    image_url = data['result']['images'][0]
                    logger.info(f"Image URL received: {image_url[:50]}...")
                    
                    # Jika server lovita, tambahkan sedikit delay sebelum mengakses gambar
                    if settings["server_id"] == "lovita":
                        await asyncio.sleep(3)  # Tunggu 3 detik untuk lovita
                    
                    # Cek NSFW hanya jika filter diaktifkan
                    nsfw_warning = ""
                    if settings.get("nsfw_filter", False) and data['result'].get('nsfw_content_detected', False):
                        nsfw_warning = "⚠️ NSFW Content Detected!"
                    
                    # Simpan URL gambar untuk digunakan nanti
                    context.user_data['last_image_url'] = image_url
                    
                    # Tambahkan tombol untuk menggunakan gambar ini untuk img2img
                    keyboard = [
                        [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")],
                        [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Hapus pesan proses jika masih ada
                    if process_message:
                        try:
                            await process_message.delete()
                        except Exception:
                            pass
                    
                    # Kirim gambar dengan enhanced download and send function
                    caption = f"Hasil generasi:\n{prompt}\n{nsfw_warning}"
                    success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Generated image for user with prompt: {prompt}\nImage URL: {image_url}")
                    
                    if not success:
                        # Jika gagal mengirim gambar, beri informasi tambahan
                        await update.message.reply_text(
                            "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                            "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                            "Anda masih dapat melihat gambar melalui URL yang diberikan."
                        )
                else:
                    await update.message.reply_text("Gambar berhasil dibuat tetapi tidak ada URL yang dikembalikan.")
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "Failed to generate image: No URL returned")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal menghasilkan gambar: {error_message}")
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to generate image: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        try:
            await process_message.delete()
        except Exception:
            pass
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request timed out")
    
    except asyncio.TimeoutError:
        logger.error("Async operation timed out")
        try:
            await process_message.delete()
        except Exception:
            pass
        await update.message.reply_text("⌛ Operasi async timeout. Silakan coba lagi nanti.")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "Async operation timed out")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        try:
            await process_message.delete()
        except Exception:
            pass
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error generating image: {str(e)}")
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# Old Text to Image Flow
async def old_txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User selected Old Text to Image feature")
    
    await update.message.reply_text(
        f"📜 *Old Text to Image*\n\n{FEATURE_DESCRIPTIONS.get('old_txt2img', 'Menggunakan model lama untuk generasi gambar.')}\n\n"
        "Masukkan prompt untuk generasi gambar:",
        parse_mode="Markdown"
    )
    return OLD_TXT2IMG_PROMPT

async def handle_old_txt2img_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Store prompt
    context.user_data['old_txt2img_prompt'] = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User old text-to-image prompt: {update.message.text}")
    
    # Fetch old models for selection
    process_message = await update.message.reply_text("⏳ Mengambil daftar model lama...")
    
    try:
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        server_name = settings.get('server_id', 'rose')
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        api_base_url = get_api_base_url(settings)
        
        response = requests.get(
            f"{api_base_url}/sdapi/get_all_models_old?server_name={server_name}",
            headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
            timeout=30
        )
        
        # Handle the response
        if response.status_code == 200:
            data = response.json()
            
            if 'status' in data and data['status'] and 'result' in data:
                models = data['result'].get('models', [])
                samplers = data['result'].get('samplers', [])
                
                if models:
                    # Store models and samplers
                    context.user_data['old_models'] = models
                    context.user_data['old_samplers'] = samplers
                    
                    # Display old models WITHOUT using Markdown
                    models_text = "📋 Pilih Model Lama\n\nModels tersedia:\n\n"
                    
                    # Create keyboard for model selection
                    keyboard = []
                    row = []
                    
                    for i, model in enumerate(models[:10]):  # Limit to 10 for readability
                        model_name = model.get('model_name', 'Unknown')
                        
                        models_text += f"• {model_name}\n"
                        
                        # Add to keyboard
                        row.append(model_name)
                        if len(row) == 2 or i == len(models[:10]) - 1:
                            keyboard.append(row)
                            row = []
                    
                    # Add back button
                    keyboard.append(["🔙 Kembali"])
                    
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    # Important: Don't use parse_mode here to avoid Markdown parsing issues
                    await update.message.reply_text(
                        models_text + "\nPilih model untuk digunakan:",
                        reply_markup=reply_markup
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Available old models: {[model.get('model_name', 'Unknown') for model in models[:10]]}")
                    
                    await process_message.delete()  # Delete process message
                    return OLD_TXT2IMG_MODEL
                else:
                    await process_message.delete()
                    await update.message.reply_text("Tidak ada model lama yang tersedia.")
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "No old models available")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await process_message.delete()
                await update.message.reply_text(f"Gagal mendapatkan daftar model lama: {error_message}")
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to get old models: {error_message}")
        else:
            await process_message.delete()
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error when getting old models: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for old models timed out")
    
    except Exception as e:
        logger.error(f"Error getting old models: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error getting old models: {str(e)}")
    
    # If we got here, something went wrong
    await start_verified(update, context)
    return ConversationHandler.END

async def handle_old_txt2img_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_model = update.message.text
    
    if selected_model == "🔙 Kembali":
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Store selected model
    context.user_data['old_txt2img_model'] = selected_model
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected old model: {selected_model}")
    
    # Get prompt
    prompt = context.user_data.get('old_txt2img_prompt', '')
    
    # Process message
    process_message = await update.message.reply_text("⏳ Sedang memproses generasi gambar...")
    
    try:
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        
        # Get samplers list for default value
        samplers = context.user_data.get('old_samplers', [])
        default_sampler = samplers[0]['name'] if samplers else "Euler a"
        
        # Prepare payload for txt2img_old
        payload = {
            "server_name": settings.get('server_id', 'rose'),
            "prompt": prompt,
            "model_name": selected_model,
            "seed": settings.get('seed', -1),  # Use seed from settings or random
            "width": settings.get('width', 512),
            "height": settings.get('height', 512),
            "sampler_name": default_sampler,
            "cfg_scale": settings.get('cfg_scale', 7),
            "steps": settings.get('num_inference_steps', 20),
            "clip_skip": settings.get('clip_skip', 2),
            "enhance_prompt": settings.get("enhance_prompt", "yes")  # Pastikan string "yes" atau "no"
        }
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        api_base_url = get_api_base_url(settings)
        
        # Make API call to txt2img_old
        response = requests.post(
            f"{api_base_url}/sdapi/txt2img_old",
            json=payload,
            headers={
                'Content-Type': "application/json",
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=60
        )
        
        # Delete process message
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False):
                if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                    image_url = data['result']['images'][0]
                    
                    # Add buttons for further processing
                    keyboard = [
                        [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")],
                        [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Save image URL for later use
                    context.user_data['last_image_url'] = image_url
                    
                    # Send image with enhanced download and send function
                    caption = f"Hasil generasi dengan model lama:\nModel: {selected_model}\nPrompt: {prompt}"
                    success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Generated image with old model {selected_model}\nPrompt: {prompt}\nImage URL: {image_url}")
                    
                    if not success:
                        # If failed to send image, provide additional information
                        await update.message.reply_text(
                            "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                            "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                            "Anda masih dapat melihat gambar melalui URL yang diberikan."
                        )
                else:
                    await update.message.reply_text("Generasi gambar berhasil tetapi tidak ada URL yang dikembalikan.")
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "Generated image with old model but no URL returned")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal menghasilkan gambar: {error_message}")
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to generate image with old model: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error with old model: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for old text-to-image timed out")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error generating image with old model: {str(e)}")
    
    # Return to main menu
    await start_verified(update, context)
    return ConversationHandler.END

# Image to Image Flow
async def img2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User selected Image to Image feature")
    
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"🎨 *Image to Image*\n\n{FEATURE_DESCRIPTIONS['img2img']}\n\nSilakan kirim gambar yang ingin dimodifikasi:",
        parse_mode="Markdown"
    )
    return IMG2IMG_IMAGE

async def handle_img2img_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, "User uploaded image for img2img")
        
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if image_data:
                # Hapus pesan proses
                await process_message.delete()
                
                # Simpan data gambar
                context.user_data['img2img_image'] = image_data
                
                # Beri tahu pengguna bahwa gambar berhasil diupload
                await update.message.reply_text("✅ Gambar berhasil diupload. Masukkan prompt untuk modifikasi gambar:")
                
                return IMG2IMG_PROMPT
            else:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to upload image for img2img")
                
                return IMG2IMG_IMAGE
        
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error processing image for img2img: {str(e)}")
            
            return IMG2IMG_IMAGE
        
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        # Validasi URL
        url = update.message.text.strip()
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided image URL for img2img: {url}")
        
        if url.startswith(('http://', 'https://')):
            context.user_data['img2img_image'] = url
            await update.message.reply_text("Masukkan prompt untuk modifikasi gambar:")
            return IMG2IMG_PROMPT
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return IMG2IMG_IMAGE
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return IMG2IMG_IMAGE

async def handle_img2img_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = update.message.text
    init_image = context.user_data.get('img2img_image', '')
    settings = context.user_data.get('settings', DEFAULT_SETTINGS)
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User img2img prompt: {prompt}")
    
    # Pesan "sedang memproses"
    process_message = await update.message.reply_text("⏳ Sedang memproses gambar...")
    
    try:
        # Cek apakah gambar adalah base64 atau URL
        is_base64 = False
        if init_image and not init_image.startswith(('http://', 'https://')):
            # Ini adalah base64, perlu diformat dengan benar
            init_image = f"data:image/jpeg;base64,{init_image}"
            is_base64 = True
        
        # Persiapkan payload
        payload = {
            "server_id": settings["server_id"],
            "model_id": settings["model_id"],
            "prompt": prompt,
            "negative_prompt": settings.get("negative_prompt", ""),
            "init_image": init_image,
            "width": settings["width"],
            "height": settings["height"],
            "samples": settings["samples"],
            "num_inference_steps": settings["num_inference_steps"],
            "scheduler": settings["scheduler"],
            "clip_skip": settings["clip_skip"],
            "nsfw_filter": settings.get("nsfw_filter", False),
            "cfg_scale": settings.get("cfg_scale", 7),
            "enhance_prompt": settings.get("enhance_prompt", "yes"),  # Pastikan string "yes" atau "no"
            "seed": settings.get("seed", -1)  # Add seed parameter
        }
        
        # Tambahkan ControlNet jika diaktifkan
        if settings.get('controlnet', {}).get('enabled', False) and settings['controlnet'].get('model_id'):
            controlnet_data = {
                "model_id": settings['controlnet']['model_id'],
                "weight": settings['controlnet'].get('weight', 0.8),
                "guidance_start": settings['controlnet'].get('guidance_start', 0.0),
                "guidance_end": settings['controlnet'].get('guidance_end', 1.0)
            }
            
            # Tambahkan gambar kondisi jika ada
            conditioning_image = settings['controlnet'].get('image')
            if conditioning_image:
                # Konversi base64 jika perlu
                if conditioning_image and not conditioning_image.startswith(('http://', 'https://')):
                    conditioning_image = f"data:image/jpeg;base64,{conditioning_image}"
                
                controlnet_data["conditioning_image"] = conditioning_image
            
            # Jika tidak ada gambar kondisi, gunakan init_image
            else:
                controlnet_data["conditioning_image"] = init_image
            
            payload["controlnet"] = controlnet_data
        
        # Tambahkan Lora jika diaktifkan
        if settings.get('lora', {}).get('enabled', False) and settings['lora'].get('model_id'):
            payload["lora"] = {
                "model_id": settings['lora']['model_id'],
                "strength": settings['lora'].get('strength', 0.7)
            }
        
        # Tambahkan pengaturan lanjutan
        advanced_settings = settings.get('advanced', {})
        for key, value in advanced_settings.items():
            if value or key == "algorithm_type":  # Always include algorithm_type
                if key == "algorithm_type":
                    payload[key] = value
                else:
                    payload[key] = "yes" if value else "no"
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        api_base_url = get_api_base_url(settings)
        
        response = requests.post(
            f"{api_base_url}/sdapi/img2img",
            json=payload,
            headers={
                'Content-Type': "application/json",
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=60  # 60 detik timeout
        )
        
        # Hapus pesan "sedang memproses"
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False):
                if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                    image_url = data['result']['images'][0]
                    
                    # Cek NSFW hanya jika filter diaktifkan
                    nsfw_warning = ""
                    if settings.get("nsfw_filter", False) and data['result'].get('nsfw_content_detected', False):
                        nsfw_warning = "⚠️ NSFW Content Detected!"
                    
                    # Tambahkan tombol untuk menggunakan gambar ini untuk img2img lagi
                    keyboard = [
                        [InlineKeyboardButton("🎨 Gunakan untuk Image to Image lagi", callback_data="use_for_img2img")],
                        [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Simpan URL gambar untuk digunakan nanti
                    context.user_data['last_image_url'] = image_url
                    
                    # Send image with enhanced download and send function
                    caption = f"Hasil modifikasi:\n{prompt}\n{nsfw_warning}"
                    success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Generated img2img result with prompt: {prompt}\nImage URL: {image_url}")
                    
                    if not success:
                        # If failed to send image, provide additional information
                        await update.message.reply_text(
                            "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                            "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                            "Anda masih dapat melihat gambar melalui URL yang diberikan."
                        )
                else:
                    await update.message.reply_text("Gambar berhasil dimodifikasi tetapi tidak ada URL yang dikembalikan.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "Generated img2img but no URL returned")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal memodifikasi gambar: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to generate img2img: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for img2img: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for img2img timed out")
    
    except Exception as e:
        logger.error(f"Error modifying image: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error processing img2img: {str(e)}")
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# Callback handler untuk button
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User clicked button: {query.data}")
    
    if query.data == "use_for_img2img":
        # Gunakan gambar terakhir untuk img2img
        if 'last_image_url' in context.user_data:
            context.user_data['img2img_image'] = context.user_data['last_image_url']
            await query.message.reply_text("Masukkan prompt untuk modifikasi gambar:")
            return IMG2IMG_PROMPT
        else:
            await query.message.reply_text("Tidak ada gambar sebelumnya. Silakan mulai dengan 'Image to Image' baru.")
            await start_verified(update, context)
            return ConversationHandler.END
    
    elif query.data == "use_for_imgproc":
        # Gunakan gambar terakhir untuk image processing
        if 'last_image_url' in context.user_data:
            context.user_data['imgproc_image'] = context.user_data['last_image_url']
            return await imgproc_menu(update, context, from_callback=True)
        else:
            await query.message.reply_text("Tidak ada gambar sebelumnya. Silakan mulai dengan 'Image Processing' baru.")
            await start_verified(update, context)
            return ConversationHandler.END
    
    return ConversationHandler.END

# Inpainting Feature
async def inpainting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User selected Inpainting feature")
    
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"✏️ *Inpainting*\n\n{FEATURE_DESCRIPTIONS['inpaint']}\n\nSilakan kirim gambar yang ingin dimodifikasi:",
        parse_mode="Markdown"
    )
    return INPAINT_IMAGE

# Inpainting Functions
async def handle_inpaint_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Check if message contains image
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, "User uploaded image for inpainting")
        
        # Process and upload image
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload image
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to upload image for inpainting")
                
                return INPAINT_IMAGE
            
            # Store image data
            context.user_data['inpaint_image'] = image_data
            
            # Delete process message
            await process_message.delete()
            
            # Ask for mask creation using Telegram's drawing feature
            await update.message.reply_text(
                "Silakan tandai area yang ingin diubah dengan menggunakan fitur kuas/coretan pada Telegram. "
                "Tandai area putih untuk bagian yang ingin diubah, dan area hitam untuk bagian yang ingin dipertahankan.\n\n"
                "Caranya:\n"
                "1. Tekan tombol edit di gambar yang sudah dikirim\n"
                "2. Pilih fitur kuas/coretan\n"
                "3. Tandai area yang ingin diubah dengan warna putih\n"
                "4. Kirim gambar hasil editan sebagai mask"
            )
            
            # Send the original image again for user to mark it
            if image_data.startswith(('http://', 'https://')):
                await update.message.reply_photo(
                    photo=image_data,
                    caption="Gunakan gambar ini untuk membuat mask. Edit dan tandai area yang ingin diubah, lalu kirim hasilnya."
                )
            else:
                # If it's base64, we need to decode it first
                image_bytes = base64.b64decode(image_data)
                bio = BytesIO(image_bytes)
                bio.seek(0)
                await update.message.reply_photo(
                    photo=bio,
                    caption="Gunakan gambar ini untuk membuat mask. Edit dan tandai area yang ingin diubah, lalu kirim hasilnya."
                )
            
            return INPAINT_MASK
        
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error processing image for inpainting: {str(e)}")
            
            return INPAINT_IMAGE
    
    elif update.message.text:
        if update.message.text.lower() == "kembali":
            await start_verified(update, context)
            return ConversationHandler.END
        
        # If user sends URL instead of image
        url = update.message.text.strip()
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided image URL for inpainting: {url}")
        
        if url.startswith(('http://', 'https://')):
            context.user_data['inpaint_image'] = url
            
            # Ask for mask creation
            await update.message.reply_text(
                "Silakan kirim gambar mask (area putih akan diganti, area hitam akan dipertahankan). "
                "Anda dapat menggunakan fitur kuas/coretan pada Telegram untuk menandai area yang ingin diubah."
            )
            
            # Download and send the image for user to mark
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    bio = BytesIO(response.content)
                    bio.seek(0)
                    await update.message.reply_photo(
                        photo=bio,
                        caption="Gunakan gambar ini untuk membuat mask. Edit dan tandai area yang ingin diubah, lalu kirim hasilnya."
                    )
                else:
                    await update.message.reply_text("Gagal mengunduh gambar dari URL. Silakan coba URL lain atau kirim gambar langsung.")
                    return INPAINT_IMAGE
            except Exception as e:
                logger.error(f"Error downloading image: {str(e)}")
                await update.message.reply_text(f"Error saat mengunduh gambar: {str(e)}")
                return

async def handle_inpaint_mask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Check if message contains image (user's marked mask)
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, "User uploaded mask for inpainting")
        
        # Process and upload mask image
        process_message = await update.message.reply_text("⏳ Mengupload gambar mask...")
        
        try:
            # Upload mask image
            mask_data = await process_photo(update, context)
            
            if not mask_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar mask. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to upload mask for inpainting")
                
                return INPAINT_MASK
            
            # Store mask data
            context.user_data['inpaint_mask'] = mask_data
            
            # Delete process message
            await process_message.delete()
            
            # Ask for prompt
            await update.message.reply_text(
                "Berhasil menerima gambar mask! Sekarang masukkan prompt untuk inpainting (deskripsi untuk bagian yang akan diganti):"
            )
            
            return INPAINT_PROMPT
        
        except Exception as e:
            logger.error(f"Error processing mask: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar mask: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error processing mask for inpainting: {str(e)}")
            
            return INPAINT_MASK
    
    elif update.message.text:
        if update.message.text.lower() == "kembali":
            await start_verified(update, context)
            return ConversationHandler.END
        
        # If user sends URL instead of image
        url = update.message.text.strip()
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided mask URL for inpainting: {url}")
        
        if url.startswith(('http://', 'https://')):
            context.user_data['inpaint_mask'] = url
            
            await update.message.reply_text(
                "Masukkan prompt untuk inpainting (deskripsi untuk bagian yang akan diganti):"
            )
            
            return INPAINT_PROMPT
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return INPAINT_MASK
    else:
        await update.message.reply_text("Silakan kirim gambar mask atau URL gambar mask.")
        return INPAINT_MASK

async def handle_inpaint_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = update.message.text
    init_image = context.user_data.get('inpaint_image', '')
    mask_image = context.user_data.get('inpaint_mask', '')
    settings = context.user_data.get('settings', DEFAULT_SETTINGS)
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User inpainting prompt: {prompt}")
    
    if prompt.lower() == "kembali":
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Process message
    process_message = await update.message.reply_text("⏳ Sedang memproses inpainting...")
    
    try:
        # Check if images are base64 or URL
        if init_image and not init_image.startswith(('http://', 'https://')):
            init_image = f"data:image/jpeg;base64,{init_image}"
        
        if mask_image and not mask_image.startswith(('http://', 'https://')):
            mask_image = f"data:image/jpeg;base64,{mask_image}"
        
        # Prepare payload
        payload = {
            "server_id": settings["server_id"],
            "model_id": settings["model_id"],
            "prompt": prompt,
            "negative_prompt": settings.get("negative_prompt", ""),
            "init_image": init_image,
            "mask_image": mask_image,
            "width": settings["width"],
            "height": settings["height"],
            "samples": settings["samples"],
            "num_inference_steps": settings["num_inference_steps"],
            "scheduler": settings["scheduler"],
            "clip_skip": settings["clip_skip"],
            "nsfw_filter": settings.get("nsfw_filter", False),
            "cfg_scale": settings.get("cfg_scale", 7),
            "enhance_prompt": settings.get("enhance_prompt", "yes"),  # yes atau no
            "seed": settings.get("seed", -1),  # Add seed parameter
            "safety_checker": "yes" if settings.get("nsfw_filter", False) else "no"
        }
        
        # Tambahkan ControlNet jika diaktifkan
        if settings.get('controlnet', {}).get('enabled', False) and settings['controlnet'].get('model_id'):
            controlnet_data = {
                "model_id": settings['controlnet']['model_id'],
                "weight": settings['controlnet'].get('weight', 0.8),
                "guidance_start": settings['controlnet'].get('guidance_start', 0.0),
                "guidance_end": settings['controlnet'].get('guidance_end', 1.0)
            }
            
            # Tambahkan gambar kondisi jika ada
            conditioning_image = settings['controlnet'].get('image')
            if conditioning_image:
                # Konversi base64 jika perlu
                if conditioning_image and not conditioning_image.startswith(('http://', 'https://')):
                    conditioning_image = f"data:image/jpeg;base64,{conditioning_image}"
                
                controlnet_data["conditioning_image"] = conditioning_image
            
            # Jika tidak ada gambar kondisi, gunakan init_image
            else:
                controlnet_data["conditioning_image"] = init_image
            
            payload["controlnet"] = controlnet_data
        
        # Tambahkan Lora jika diaktifkan
        if settings.get('lora', {}).get('enabled', False) and settings['lora'].get('model_id'):
            payload["lora"] = {
                "model_id": settings['lora']['model_id'],
                "strength": settings['lora'].get('strength', 0.7)
            }
        
        # Tambahkan pengaturan lanjutan
        advanced_settings = settings.get('advanced', {})
        for key, value in advanced_settings.items():
            if value or key == "algorithm_type":  # Always include algorithm_type
                if key == "algorithm_type":
                    payload[key] = value
                else:
                    payload[key] = "yes" if value else "no"
        
        # Obtain the API base URL based on settings
        api_base_url = get_api_base_url(settings)
        
        # Use both servers for increased reliability
        response = None
        for server in ["lovita", "rose"]:
            try:
                endpoint_url = f"{SERVER_API_URLS[server]}/sdapi/inpaint"
                
                # Update server_id in payload
                payload["server_id"] = server
                
                # Make API call
                response = requests.post(
                    endpoint_url,
                    json=payload,
                    headers={
                        'Content-Type': "application/json",
                        'Authorization': f"Bearer {ITSROSE_API_KEY}"
                    },
                    timeout=60
                )
                
                # If successful, break the loop
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get('status', False):
                        break
            except Exception as e:
                logger.error(f"Error with server {server}: {str(e)}")
                continue
        
        # Delete process message
        await process_message.delete()
        
        if response and response.status_code == 200:
            data = response.json()
            
            if data.get('status', False):
                if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                    image_url = data['result']['images'][0]
                    
                    # Check NSFW only if filter is enabled
                    nsfw_warning = ""
                    if settings.get("nsfw_filter", False) and data['result'].get('nsfw_content_detected', False):
                        nsfw_warning = "⚠️ NSFW Content Detected!"
                    
                    # Add buttons for further processing
                    keyboard = [
                        [InlineKeyboardButton("🔄 Proses dengan Image Processing lagi", callback_data="use_for_imgproc")],
                        [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Save image URL for later use
                    context.user_data['last_image_url'] = image_url
                    
                    # Send image with enhanced download and send function
                    caption = f"Hasil inpainting:\n{prompt}\n{nsfw_warning}"
                    success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Generated inpainting result with prompt: {prompt}\nImage URL: {image_url}")
                    
                    if not success:
                        # If failed to send image, provide additional information
                        await update.message.reply_text(
                            "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                            "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                            "Anda masih dapat melihat gambar melalui URL yang diberikan."
                        )
                else:
                    await update.message.reply_text("Inpainting berhasil tetapi tidak ada URL yang dikembalikan.")
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "Generated inpainting but no URL returned")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal melakukan inpainting: {error_message}")
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to generate inpainting: {error_message}")
        else:
            error_msg = "Error dari server: Kedua server gagal memproses permintaan."
            if response:
                error_msg = f"Error dari server: {response.status_code} - {response.text}"
            await update.message.reply_text(error_msg)
            # Forward to owner bot
            await forward_to_owner(update, context, "text", error_msg)
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for inpainting timed out")
    
    except Exception as e:
        logger.error(f"Error in inpainting: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error processing inpainting: {str(e)}")
    
    # Return to main menu
    await start_verified(update, context)
    return ConversationHandler.END

# Generate Prompt dengan gambar - Fix untuk error 414 Request-URI Too Large
async def prompt_generator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User selected Generate Prompt feature")
    
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"🧠 *Generate Prompt*\n\n{FEATURE_DESCRIPTIONS['generate_prompt']}\n\nSilakan kirim gambar untuk dianalisis:",
        parse_mode="Markdown"
    )
    return PROMPT_GEN_IMAGE

async def handle_prompt_gen_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, "User uploaded image for prompt generation")
        
        # Proses gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("Gagal memproses gambar. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to upload image for prompt generation")
                
                return PROMPT_GEN_IMAGE
            
            # Update pesan proses
            await process_message.edit_text("🧠 Menganalisis gambar dan menghasilkan prompt...")
            
            # Cek apakah ini adalah base64 atau URL
            if not image_data.startswith(('http://', 'https://')):
                # Jika masih dalam format base64, berikan pesan informasi
                await process_message.delete()
                await update.message.reply_text("⚠️ Gagal mendapatkan URL gambar. Silakan gunakan URL gambar langsung.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to process base64 image for prompt generation")
                
                return PROMPT_GEN_IMAGE
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Gunakan urllib.parse untuk mengenkode URL dengan benar
            import urllib.parse
            encoded_url = urllib.parse.quote_plus(image_data)
            
            # Gunakan metode GET dengan parameter URL
            response = requests.get(
                f"{api_base_url}/sdapi/generate_prompt?init_image={encoded_url}",
                headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                timeout=60
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False):
                    if 'result' in data and 'prompt' in data['result']:
                        prompt = data['result']['prompt']
                        
                        # Tambahkan tombol untuk langsung menggunakan prompt ini
                        keyboard = [
                            [InlineKeyboardButton("🖼 Gunakan untuk Text2Img", callback_data="use_for_txt2img")],
                            [InlineKeyboardButton("🎨 Gunakan untuk Img2Img", callback_data="use_for_new_img2img")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Simpan prompt untuk digunakan nanti
                        context.user_data['generated_prompt'] = prompt
                        
                        # Send the generated prompt
                        sent_message = await update.message.reply_text(
                            f"✨ *Generated Prompt*:\n\n{prompt}",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Generated prompt from image: {prompt}")
                    else:
                        await update.message.reply_text("Gagal menghasilkan prompt. Respons tidak memiliki format yang diharapkan.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "Failed to generate prompt: unexpected response format")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal menghasilkan prompt: {error_message}")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Failed to generate prompt: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error for prompt generation: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "API request for prompt generation timed out")
        
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error generating prompt: {str(e)}")
    
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        process_message = await update.message.reply_text("🧠 Menganalisis gambar dan menghasilkan prompt...")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided image URL for prompt generation: {update.message.text}")
        
        try:
            # Gunakan URL langsung
            image_url = update.message.text.strip()
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Gunakan urllib.parse untuk mengenkode URL dengan benar
            import urllib.parse
            encoded_url = urllib.parse.quote_plus(image_url)
            
            # Gunakan metode GET dengan parameter URL
            response = requests.get(
                f"{api_base_url}/sdapi/generate_prompt?init_image={encoded_url}",
                headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                timeout=60
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False):
                    if 'result' in data and 'prompt' in data['result']:
                        prompt = data['result']['prompt']
                        
                        # Tambahkan tombol untuk langsung menggunakan prompt ini
                        keyboard = [
                            [InlineKeyboardButton("🖼 Gunakan untuk Text2Img", callback_data="use_for_txt2img")],
                            [InlineKeyboardButton("🎨 Gunakan untuk Img2Img", callback_data="use_for_new_img2img")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Simpan prompt untuk digunakan nanti
                        context.user_data['generated_prompt'] = prompt
                        
                        sent_message = await update.message.reply_text(
                            f"✨ *Generated Prompt*:\n\n{prompt}",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Generated prompt from URL: {prompt}")
                    else:
                        await update.message.reply_text("Gagal menghasilkan prompt. Respons tidak memiliki format yang diharapkan.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "Failed to generate prompt from URL: unexpected response format")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal menghasilkan prompt: {error_message}")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Failed to generate prompt from URL: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error for prompt generation from URL: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "API request for prompt generation from URL timed out")
        
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error generating prompt from URL: {str(e)}")
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return PROMPT_GEN_IMAGE
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# Settings Flow
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Settings menu")
    
    # Pastikan settings tersedia
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    settings = context.user_data['settings']
    
    # Update api_base_url berdasarkan server_id yang dipilih
    settings['api_base_url'] = get_api_base_url(settings)
    
    # Kategori untuk pengaturan
    image_settings = ["width", "height", "samples", "num_inference_steps", "model_id", 
                      "scheduler", "clip_skip", "nsfw_filter", "server_id", "api_base_url", 
                      "cfg_scale", "negative_prompt", "seed"]
    
    # Menghindari formatting Markdown/HTML yang bisa menyebabkan error
    settings_text = "⚙️ Pengaturan saat ini:\n\n"
    
    # Tampilkan pengaturan gambar
    settings_text += "📷 Pengaturan Gambar:\n"
    for key in image_settings:
        if key in settings:
            # Format khusus untuk NSFW filter
            if key == "nsfw_filter":
                status = "Aktif" if settings[key] else "Nonaktif"
                settings_text += f"• NSFW Filter: {status}\n"
            elif key == "negative_prompt":
                prompt = settings[key] if settings[key] else "(kosong)"
                settings_text += f"• Negative Prompt: {prompt}\n"
            elif key == "server_id":
                settings_text += f"• Server: {settings[key]}\n"
            elif key == "api_base_url":
                continue  # Skip api_base_url
            elif key == "seed":
                seed_value = "Random (-1)" if settings[key] == -1 else settings[key]
                settings_text += f"• Seed: {seed_value}\n"
            else:
                settings_text += f"• {key}: {settings[key]}\n"
    
    # Tampilkan status Enhance Prompt
    enhance_prompt_status = settings.get('enhance_prompt', "yes")
    settings_text += f"\n🔄 Enhance Prompt: {enhance_prompt_status}\n"
    
    # Tampilkan status ControlNet
    controlnet = settings.get('controlnet', {})
    controlnet_status = "Aktif" if controlnet.get('enabled', False) else "Nonaktif"
    controlnet_model = controlnet.get('model_id', 'Tidak dipilih')
    settings_text += f"🎛️ ControlNet: {controlnet_status} (Model: {controlnet_model})\n"
    
    # Tampilkan status Lora
    lora = settings.get('lora', {})
    lora_status = "Aktif" if lora.get('enabled', False) else "Nonaktif"
    lora_model = lora.get('model_id', 'Tidak dipilih')
    settings_text += f"🧩 Lora Model: {lora_status} (Model: {lora_model})\n"
    
    keyboard = [
        ["Width", "Height", "Samples"],
        ["Steps", "Model", "Old Models"],
        ["Scheduler", "Clip Skip", "NSFW Filter"],
        ["CFG Scale", "Negative Prompt", "Seed"],
        ["Server ID", "Enhance Prompt", "ControlNet"],
        ["Lora Models", "Advanced Settings", "Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup
    )
    return SETTINGS_CHOICE

async def handle_settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.lower()
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected setting option: {choice}")

    if choice == "kembali":
        await start_verified(update, context)
        return ConversationHandler.END
    
    if choice == "old models":
        return await get_old_models(update, context)
    
    if choice == "controlnet":
        return await controlnet_menu(update, context)
        
    if choice == "lora models":
        return await lora_menu(update, context)
        
    if choice == "advanced settings":
        return await advanced_menu(update, context)
    
    if "enhance prompt" in choice:
        # Toggle status Enhance Prompt antara "yes" dan "no"
        current_status = context.user_data['settings'].get('enhance_prompt', "yes")
        new_status = "no" if current_status == "yes" else "yes"
        context.user_data['settings']['enhance_prompt'] = new_status
        
        status_text = "diaktifkan" if new_status == "yes" else "dinonaktifkan"
        await update.message.reply_text(f"Enhance Prompt telah {status_text}.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User changed Enhance Prompt setting to: {new_status}")
        
        return await settings_menu(update, context)
    
    # Mapping dari pilihan menu ke key dalam settings
    choice_mapping = {
        "width": "width",
        "height": "height",
        "samples": "samples",
        "steps": "num_inference_steps",
        "model": "model_id",
        "scheduler": "scheduler",
        "clip skip": "clip_skip",
        "nsfw filter": "nsfw_filter",
        "cfg scale": "cfg_scale",
        "negative prompt": "negative_prompt",
        "server id": "server_id",
        "seed": "seed"
    }
    
    # Jika pilihan ada dalam mapping, atau jika pilihan langsung cocok dengan key
    setting_key = choice_mapping.get(choice, None)
    if setting_key is None:
        for key in choice_mapping:
            if choice in key or key in choice:
                setting_key = choice_mapping[key]
                break
    
    if setting_key:
        context.user_data['current_setting'] = setting_key
        current_value = context.user_data['settings'][setting_key]
        
        # Tambahkan deskripsi parameter
        parameter_description = PARAMETER_DESCRIPTIONS.get(setting_key, "")
        description_text = f"Parameter: {setting_key}\n\n{parameter_description}\n\n"
        
        # Berikan pilihan spesifik untuk model, scheduler dan fitur-fitur lain
        if setting_key == "model_id":
            # Dapatkan daftar model dari API
            try:
                settings = context.user_data.get('settings', DEFAULT_SETTINGS)
                server_id = settings.get('server_id', 'rose')
                
                # Dapatkan base URL berdasarkan server_id yang dipilih
                api_base_url = get_api_base_url(settings)
                
                # Gunakan library requests untuk lebih andal
                response = requests.get(
                    f"{api_base_url}/sdapi/get_all_models?server_id={server_id}",
                    headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'status' in data and data['status'] and 'result' in data:
                        models = data['result'].get('models', [])
                        
                        # Grup model dalam tombol 3 per baris
                        keyboard = []
                        row = []
                        
                        for i, model in enumerate(models):
                            if isinstance(model, dict) and 'model_id' in model:
                                model = model['model_id']
                            row.append(model)
                            if (i + 1) % 3 == 0 or i == len(models) - 1:
                                keyboard.append(row)
                                row = []
                        
                        # Tambahkan tombol kembali
                        keyboard.append(["Kembali"])
                        
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            f"{description_text}Model saat ini: {current_value}\nPilih model baru:",
                            reply_markup=reply_markup
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Available models shown to user, current model: {current_value}")
                    else:
                        # Fallback jika tidak bisa mendapatkan daftar model
                        keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            f"{description_text}Model saat ini: {current_value}\nPilih model baru (gagal mendapatkan daftar lengkap):",
                            reply_markup=reply_markup
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "Failed to get full models list, showing fallback options")
                else:
                    # Fallback jika request gagal
                    keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        f"{description_text}Model saat ini: {current_value}\nPilih model baru (gagal mendapatkan daftar):",
                        reply_markup=reply_markup
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Server error when getting models: {response.status_code}")
            except Exception as e:
                logger.error(f"Error getting models: {str(e)}")
                keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f"{description_text}Model saat ini: {current_value}\nPilih model baru:",
                    reply_markup=reply_markup
                )
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Error getting models: {str(e)}")
                
        elif setting_key == "scheduler":
            # Tampilkan deskripsi scheduler
            scheduler_text = f"{description_text}Scheduler saat ini: {current_value}\n\n"
            scheduler_text += "Jenis-jenis Scheduler:\n\n"
            
            for scheduler_name, scheduler_desc in SCHEDULER_DESCRIPTIONS.items():
                scheduler_text += f"• *{scheduler_name}*: {scheduler_desc}\n\n"
            
            # Tambahkan rekomendasi
            scheduler_text += "*Rekomendasi berdasarkan kebutuhan:*\n"
            scheduler_text += "• Kualitas Terbaik: DDPMScheduler, KDPM2DiscreteScheduler\n"
            scheduler_text += "• Kecepatan Terbaik: LCMScheduler, EulerDiscreteScheduler\n"
            scheduler_text += "• Keseimbangan Kualitas/Kecepatan: DPMSolverMultistepScheduler, UniPCMultistepScheduler\n"
            scheduler_text += "• Variasi Kreatif: EulerAncestralDiscreteScheduler, KDPM2AncestralDiscreteScheduler\n\n"
            
            # Dapatkan daftar scheduler dari API
            try:
                settings = context.user_data.get('settings', DEFAULT_SETTINGS)
                server_id = settings.get('server_id', 'rose')
                
                # Dapatkan base URL berdasarkan server_id yang dipilih
                api_base_url = get_api_base_url(settings)
                
                # Gunakan library requests untuk lebih andal
                response = requests.get(
                    f"{api_base_url}/sdapi/schedulers_list?server_id={server_id}",
                    headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'status' in data and data['status'] and 'result' in data:
                        schedulers = data['result'].get('schedulers', [])
                        
                        # Grup scheduler dalam tombol 2 per baris
                        keyboard = []
                        row = []
                        for i, scheduler in enumerate(schedulers):
                            row.append(scheduler)
                            if (i + 1) % 2 == 0 or i == len(schedulers) - 1:
                                keyboard.append(row)
                                row = []
                        
                        # Tambahkan tombol kembali
                        keyboard.append(["Kembali"])
                        
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            scheduler_text + "Pilih scheduler baru:",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Scheduler options shown to user, current scheduler: {current_value}")
                    else:
                        # Fallback jika tidak bisa mendapatkan daftar scheduler
                        keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            scheduler_text + "Pilih scheduler baru (gagal mendapatkan daftar lengkap):",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "Failed to get scheduler list, showing fallback options")
                else:
                    # Fallback jika request gagal
                    keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        scheduler_text + "Pilih scheduler baru (gagal mendapatkan daftar):",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Server error when getting schedulers: {response.status_code}")
            except Exception as e:
                logger.error(f"Error getting schedulers: {str(e)}")
                keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    scheduler_text + "Pilih scheduler baru:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Error getting schedulers: {str(e)}")
                
        elif setting_key == "nsfw_filter":
            # Pilihan untuk aktifkan/nonaktifkan NSFW filter
            status = "Aktif" if current_value else "Nonaktif"
            keyboard = [["Aktif", "Nonaktif"], ["Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"{description_text}NSFW Filter saat ini: {status}\nPilih status baru:",
                reply_markup=reply_markup
            )
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"NSFW Filter options shown to user, current status: {status}")
            
        elif setting_key == "server_id":
            # Pilihan server untuk beralih antara rose dan lovita
            keyboard = [["rose", "lovita"], ["Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"{description_text}Server saat ini: {current_value}\nPilih server baru:",
                reply_markup=reply_markup
            )
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server ID options shown to user, current server: {current_value}")
            
        elif setting_key == "negative_prompt":
            await update.message.reply_text(
                f"{description_text}Negative Prompt saat ini: {current_value or '(kosong)'}\n\n"
                f"Masukkan negative prompt baru (kirim 'kosong' untuk mengosongkan):"
            )
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Negative prompt edit requested, current value: {current_value or '(empty)'}")
            
        elif setting_key == "seed":
            seed_value = "Random (-1)" if current_value == -1 else current_value
            await update.message.reply_text(
                f"{description_text}Seed saat ini: {seed_value}\n\n"
                f"Masukkan nilai seed baru (masukkan -1 untuk seed acak):"
            )
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Seed edit requested, current value: {seed_value}")
            
        else:
            await update.message.reply_text(
                f"{description_text}Nilai {setting_key} saat ini: {current_value}\nMasukkan nilai baru:"
            )
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Setting edit requested for {setting_key}, current value: {current_value}")
        
        return SETTINGS_VALUE
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih lagi.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Invalid setting choice: {choice}")
        
        return SETTINGS_CHOICE

async def get_old_models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User requested old models list")
    
    # Fetch old models from API
    process_message = await update.message.reply_text("⏳ Mengambil daftar model lama...")
    
    try:
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        server_name = settings.get('server_id', 'rose')
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        api_base_url = get_api_base_url(settings)
        
        response = requests.get(
            f"{api_base_url}/sdapi/get_all_models_old?server_name={server_name}",
            headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
            timeout=30
        )
        
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if 'status' in data and data['status'] and 'result' in data:
                models = data['result'].get('models', [])
                
                if models:
                    # Display old models
                    models_text = f"🔍 *Daftar Model Lama Tersedia*\n\n"
                    
                    # Create keyboard for model selection
                    keyboard = []
                    row = []
                    
                    for i, model in enumerate(models):
                        model_name = model.get('model_name', 'Unknown')
                        
                        models_text += f"• {model_name}\n"
                        
                        # Add to keyboard
                        row.append(model_name)
                        if len(row) == 2 or i == len(models) - 1:
                            keyboard.append(row)
                            row = []
                    
                    # Add back button
                    keyboard.append(["🔙 Kembali"])
                    
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    await update.message.reply_text(
                        models_text + "\nPilih model untuk digunakan:",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Old models list shown to user: {[model.get('model_name', 'Unknown') for model in models[:5]]}...")
                    
                    # Store context for next step
                    context.user_data['selecting_old_model'] = True
                    return SETTINGS_VALUE
                else:
                    await update.message.reply_text(f"Tidak ada model lama yang tersedia.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "No old models available")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan daftar model lama: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to get old models: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error getting old models: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for old models timed out")
    
    except Exception as e:
        logger.error(f"Error getting old models: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error getting old models: {str(e)}")
    
    return await settings_menu(update, context)

async def handle_settings_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    current_setting = context.user_data.get('current_setting')
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User setting new value for {current_setting}: {new_value}")
    
    # Handle old model selection
    if 'selecting_old_model' in context.user_data and context.user_data['selecting_old_model']:
        # Clear the flag
        del context.user_data['selecting_old_model']
        
        # Handle old model selection
        if new_value.lower() == "kembali" or new_value.lower() == "🔙 kembali":
            return await settings_menu(update, context)
        
        # Update settings with the selected old model
        context.user_data['settings']['old_model'] = new_value
        context.user_data['settings']['use_old_model'] = True
        await update.message.reply_text(f"Model lama diubah menjadi: {new_value}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User selected old model: {new_value}")
        
        # Return to settings menu
        return await settings_menu(update, context)
    
    if new_value.lower() == "kembali":
        return await settings_menu(update, context)
    
    # Validasi dan konversi nilai
    try:
        # Penanganan khusus untuk NSFW filter
        if current_setting == "nsfw_filter":
            if new_value.lower() == "aktif":
                context.user_data['settings'][current_setting] = True
                await update.message.reply_text("NSFW Filter diaktifkan.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "User enabled NSFW filter")
            elif new_value.lower() == "nonaktif":
                context.user_data['settings'][current_setting] = False
                await update.message.reply_text("NSFW Filter dinonaktifkan.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "User disabled NSFW filter")
            else:
                await update.message.reply_text("Nilai tidak valid. Pilih 'Aktif' atau 'Nonaktif'.")
                return SETTINGS_VALUE
        
        # Penanganan untuk server_id
        elif current_setting == "server_id":
            if new_value.lower() in ["rose", "lovita"]:
                context.user_data['settings'][current_setting] = new_value.lower()
                # Update juga api_base_url berdasarkan server_id yang dipilih
                context.user_data['settings']['api_base_url'] = SERVER_API_URLS[new_value.lower()]
                await update.message.reply_text(f"Server diubah menjadi: {new_value.lower()}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"User changed server to: {new_value.lower()}")
            else:
                await update.message.reply_text("Server ID tidak valid. Pilih 'rose' atau 'lovita'.")
                return SETTINGS_VALUE
        
        # Penanganan untuk negative prompt
        elif current_setting == "negative_prompt":
            if new_value.lower() == "kosong":
                context.user_data['settings'][current_setting] = ""
                await update.message.reply_text("Negative prompt dikosongkan.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "User cleared negative prompt")
            else:
                context.user_data['settings'][current_setting] = new_value
                await update.message.reply_text(f"Negative prompt diubah menjadi: {new_value}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"User set negative prompt to: {new_value}")
        
        # Penanganan untuk seed
        elif current_setting == "seed":
            seed_value = int(new_value)
            context.user_data['settings'][current_setting] = seed_value
            seed_text = "Random" if seed_value == -1 else str(seed_value)
            await update.message.reply_text(f"Seed diubah menjadi: {seed_text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"User set seed to: {seed_text}")
        
        # Penanganan untuk setting numerik
        elif current_setting in ["width", "height", "samples", "num_inference_steps", "clip_skip", "cfg_scale"]:
            new_value = int(new_value)
            
            # Validasi range
            if current_setting in ["width", "height"] and (new_value < 64 or new_value > 1024):
                await update.message.reply_text("Nilai harus antara 64-1024. Silakan coba lagi.")
                return SETTINGS_VALUE
            elif current_setting == "samples" and (new_value < 1 or new_value > 4):
                await update.message.reply_text("Samples harus antara 1-4. Silakan coba lagi.")
                return SETTINGS_VALUE
            elif current_setting == "num_inference_steps" and (new_value < 10 or new_value > 24):  # Maximum 24 instead of 50
                await update.message.reply_text("Steps harus antara 10-24. Silakan coba lagi.")
                return SETTINGS_VALUE
            elif current_setting == "clip_skip" and (new_value < 1 or new_value > 7):  # Maximum 7 instead of 12
                await update.message.reply_text("Clip Skip harus antara 1-7. Silakan coba lagi.")
                return SETTINGS_VALUE
            elif current_setting == "cfg_scale" and (new_value < 1 or new_value > 30):
                await update.message.reply_text("CFG Scale harus antara 1-30. Silakan coba lagi.")
                return SETTINGS_VALUE
            
            # Update nilai
            context.user_data['settings'][current_setting] = new_value
            await update.message.reply_text(f"Berhasil mengubah {current_setting} menjadi {new_value}.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"User set {current_setting} to: {new_value}")
        
        # Penanganan untuk setting string
        else:
            context.user_data['settings'][current_setting] = new_value
            await update.message.reply_text(f"Berhasil mengubah {current_setting} menjadi {new_value}.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"User set {current_setting} to: {new_value}")
        
        # Kembali ke menu settings
        return await settings_menu(update, context)
    
    except ValueError:
        await update.message.reply_text("Nilai tidak valid. Silakan masukkan angka.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Invalid value for {current_setting}: {new_value}")
        
        return SETTINGS_VALUE

# ControlNet Menu
async def controlnet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed ControlNet menu")
    
    # Dapatkan pengaturan ControlNet saat ini
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    # Pastikan controlnet ada dalam settings
    if 'controlnet' not in context.user_data['settings']:
        context.user_data['settings']['controlnet'] = {
            'enabled': False,
            'model_id': 'softedge',
            'weight': 0.8,
            'guidance_start': 0.0,
            'guidance_end': 1.0,
            'image': None
        }
    
    controlnet_settings = context.user_data['settings']['controlnet']
    enabled = controlnet_settings.get('enabled', False)
    model_id = controlnet_settings.get('model_id', 'softedge')
    weight = controlnet_settings.get('weight', 0.8)
    guidance_start = controlnet_settings.get('guidance_start', 0.0)
    guidance_end = controlnet_settings.get('guidance_end', 1.0)
    
    status = "Aktif" if enabled else "Nonaktif"
    
    settings_text = "🎛️ *Pengaturan ControlNet*\n\n"
    settings_text += f"• Status: {status}\n"
    settings_text += f"• Model: {model_id}\n"
    settings_text += f"• Weight: {weight}\n"
    settings_text += f"• Guidance Start: {guidance_start}\n"
    settings_text += f"• Guidance End: {guidance_end}\n\n"
    settings_text += "ControlNet memungkinkan Anda mengontrol proses generasi gambar dengan gambar panduan. Setiap model menyediakan jenis kontrol yang berbeda:\n\n"
    settings_text += "• softedge: Untuk tepi lembut\n"
    settings_text += "• inpaint: Mengisi area yang hilang\n"
    settings_text += "• lineart: Mengikuti gambar garis\n"
    settings_text += "• openpose: Mempertahankan pose manusia\n"
    settings_text += "• depth: Mengontrol kedalaman gambar\n"
    settings_text += "• segmentation: Mengontrol segmen gambar\n"
    settings_text += "• hed: Deteksi tepian hierarkis untuk tepi yang halus\n"
    settings_text += "• normal: Menggunakan peta normal untuk kontrol struktur 3D\n"
    settings_text += "• mlsd: Deteksi garis lurus multi-skala\n"
    settings_text += "• scribble: Menggunakan sketsa kasar sebagai panduan\n"
    settings_text += "• tile: Menghasilkan tekstur yang dapat diulang\n"
    settings_text += "• tile_xl: Tekstur yang dapat diulang dengan resolusi lebih tinggi\n"
    settings_text += "• face_detector: Fokus pada wajah dalam gambar"
    
    keyboard = [
        ["Enable/Disable", "Pilih Model"],
        ["Set Weight", "Set Guidance"],
        ["Set Image", "Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CONTROLNET_MENU

async def handle_controlnet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected ControlNet option: {choice}")
    
    if choice == "Kembali":
        return await settings_menu(update, context)
    
    if "Enable/Disable" in choice:
        # Toggle status ControlNet
        current_status = context.user_data['settings']['controlnet'].get('enabled', False)
        context.user_data['settings']['controlnet']['enabled'] = not current_status
        new_status = "diaktifkan" if not current_status else "dinonaktifkan"
        
        await update.message.reply_text(f"ControlNet telah {new_status}.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User {new_status} ControlNet")
        
        return await controlnet_menu(update, context)
    
    if "Pilih Model" in choice:
        # Tampilkan daftar model ControlNet yang tersedia
        keyboard = []
        row = []
        
        # Menggunakan daftar model dari konstanta yang telah didefinisikan
        for i, model in enumerate(CONTROLNET_MODELS):
            row.append(model)
            if len(row) == 2 or i == len(CONTROLNET_MODELS) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append(["Kembali"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📋 *Model ControlNet Tersedia*\n\n"
            "Pilih model ControlNet yang ingin digunakan:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing ControlNet models list")
        
        return CONTROLNET_MODEL
    
    if "Set Weight" in choice:
        await update.message.reply_text(
            "Masukkan nilai weight untuk ControlNet (0.0-1.0).\n"
            "Nilai yang lebih tinggi memberikan pengaruh yang lebih kuat pada hasil akhir.",
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User setting ControlNet weight")
        
        return CONTROLNET_WEIGHT
    
    if "Set Guidance" in choice:
        await update.message.reply_text(
            "Masukkan nilai guidance start dan end untuk ControlNet dalam format 'start,end' (contoh: 0.0,1.0).\n"
            "Guidance start: Titik awal penerapan ControlNet (0.0-1.0).\n"
            "Guidance end: Titik akhir penerapan ControlNet (0.0-1.0).",
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User setting ControlNet guidance")
        
        return CONTROLNET_GUIDANCE
    
    if "Set Image" in choice:
        await update.message.reply_text(
            "Silakan kirim gambar yang akan digunakan sebagai gambar panduan untuk ControlNet.\n"
            "Gambar ini akan digunakan untuk mengontrol proses generasi sesuai dengan model yang dipilih.",
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User setting ControlNet conditioning image")
        
        return CONTROLNET_IMAGE
    
    await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
    return CONTROLNET_MENU

async def handle_controlnet_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    model_id = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected ControlNet model: {model_id}")
    
    if model_id == "Kembali":
        return await controlnet_menu(update, context)
    
    # Validasi model
    if model_id not in CONTROLNET_MODELS:
        await update.message.reply_text("Model tidak valid. Silakan pilih dari daftar yang tersedia.")
        return CONTROLNET_MODEL
    
    # Update model ControlNet
    context.user_data['settings']['controlnet']['model_id'] = model_id
    
    await update.message.reply_text(f"Model ControlNet diubah menjadi: {model_id}")
    
    return await controlnet_menu(update, context)

async def handle_controlnet_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    weight_text = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User setting ControlNet weight: {weight_text}")
    
    if weight_text == "Kembali":
        return await controlnet_menu(update, context)
    
    try:
        weight = float(weight_text)
        
        if weight < 0.0 or weight > 1.0:
            await update.message.reply_text("Nilai weight harus antara 0.0 dan 1.0. Silakan coba lagi.")
            return CONTROLNET_WEIGHT
        
        # Update weight ControlNet
        context.user_data['settings']['controlnet']['weight'] = weight
        
        await update.message.reply_text(f"Weight ControlNet diubah menjadi: {weight}")
        
    except ValueError:
        await update.message.reply_text("Nilai tidak valid. Masukkan angka antara 0.0 dan 1.0.")
        return CONTROLNET_WEIGHT
    
    return await controlnet_menu(update, context)

async def handle_controlnet_guidance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    guidance_text = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User setting ControlNet guidance: {guidance_text}")
    
    if guidance_text == "Kembali":
        return await controlnet_menu(update, context)
    
    try:
        # Parse format "start,end"
        values = guidance_text.split(',')
        if len(values) != 2:
            await update.message.reply_text("Format tidak valid. Gunakan format 'start,end' (contoh: 0.0,1.0).")
            return CONTROLNET_GUIDANCE
        
        start = float(values[0].strip())
        end = float(values[1].strip())
        
        if start < 0.0 or start > 1.0 or end < 0.0 or end > 1.0:
            await update.message.reply_text("Nilai guidance harus antara 0.0 dan 1.0. Silakan coba lagi.")
            return CONTROLNET_GUIDANCE
        
        if start > end:
            await update.message.reply_text("Guidance start tidak boleh lebih besar dari guidance end.")
            return CONTROLNET_GUIDANCE
        
        # Update guidance ControlNet
        context.user_data['settings']['controlnet']['guidance_start'] = start
        context.user_data['settings']['controlnet']['guidance_end'] = end
        
        await update.message.reply_text(f"Guidance ControlNet diubah menjadi: start={start}, end={end}")
        
    except ValueError:
        await update.message.reply_text("Nilai tidak valid. Masukkan angka antara 0.0 dan 1.0 dalam format 'start,end'.")
        return CONTROLNET_GUIDANCE
    
    return await controlnet_menu(update, context)

async def handle_controlnet_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, "User uploaded ControlNet conditioning image")
        
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to upload ControlNet image")
                
                return CONTROLNET_IMAGE
            
            # Hapus pesan proses
            await process_message.delete()
            
            # Simpan data gambar
            context.user_data['settings']['controlnet']['image'] = image_data
            context.user_data['settings']['controlnet']['enabled'] = True  # Otomatis aktifkan ControlNet
            
            await update.message.reply_text(
                "✅ Gambar panduan ControlNet berhasil diupload dan disimpan. "
                "ControlNet telah diaktifkan untuk penggunaan berikutnya."
            )
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "User successfully set ControlNet image and enabled ControlNet")
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error processing ControlNet image: {str(e)}")
            
            return CONTROLNET_IMAGE
        
    elif update.message.text:
        if update.message.text == "Kembali":
            return await controlnet_menu(update, context)
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided ControlNet image URL: {update.message.text}")
        
        # Jika pengguna mengirim URL alih-alih gambar
        url = update.message.text.strip()
        
        if url.startswith(('http://', 'https://')):
            # Simpan URL gambar
            context.user_data['settings']['controlnet']['image'] = url
            context.user_data['settings']['controlnet']['enabled'] = True  # Otomatis aktifkan ControlNet
            
            await update.message.reply_text(
                "✅ URL gambar panduan ControlNet berhasil disimpan. "
                "ControlNet telah diaktifkan untuk penggunaan berikutnya."
            )
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return CONTROLNET_IMAGE
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return CONTROLNET_IMAGE
    
    return await controlnet_menu(update, context)

# Lora Models Menu
async def lora_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Lora Models menu")
    
    # Dapatkan pengaturan Lora saat ini
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    # Pastikan lora ada dalam settings
    if 'lora' not in context.user_data['settings']:
        context.user_data['settings']['lora'] = {
            'enabled': False,
            'model_id': 'add_detail',
            'strength': 0.7
        }
    
    lora_settings = context.user_data['settings']['lora']
    enabled = lora_settings.get('enabled', False)
    model_id = lora_settings.get('model_id', 'add_detail')
    strength = lora_settings.get('strength', 0.7)
    
    status = "Aktif" if enabled else "Nonaktif"
    
    settings_text = "🧩 *Pengaturan Lora Models*\n\n"
    settings_text += f"• Status: {status}\n"
    settings_text += f"• Model: {model_id}\n"
    settings_text += f"• Strength: {strength}\n\n"
    settings_text += "Lora Models adalah adaptasi ringan yang memodifikasi gaya output atau menambahkan konsep/karakter tertentu.\n\n"
    settings_text += "Kategori Lora Models:\n"
    settings_text += "• Style Models: Mengubah gaya visual (arcane-style, niji_express)\n"
    settings_text += "• Character Models: Karakter spesifik (yae-miko, frieren)\n"
    settings_text += "• Detail Models: Meningkatkan detail (add_detail, more_details)"
    
    keyboard = [
        ["Enable/Disable", "Pilih Model"],
        ["Set Strength", "Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return LORA_MENU

async def handle_lora_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Lora option: {choice}")
    
    if choice == "Kembali":
        return await settings_menu(update, context)
    
    if "Enable/Disable" in choice:
        # Toggle status Lora
        current_status = context.user_data['settings']['lora'].get('enabled', False)
        context.user_data['settings']['lora']['enabled'] = not current_status
        new_status = "diaktifkan" if not current_status else "dinonaktifkan"
        
        await update.message.reply_text(f"Lora Model telah {new_status}.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User {new_status} Lora Model")
        
        return await lora_menu(update, context)
    
    if "Pilih Model" in choice:
        # Kategorikan model Lora
        keyboard = [
            ["Style Models", "Character Models"],
            ["Detail Models", "Other Models"],
            ["Kembali"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📋 *Kategori Lora Models*\n\n"
            "Pilih kategori Lora Model:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing Lora model categories")
        
        return LORA_MODEL
    
    if "Set Strength" in choice:
        await update.message.reply_text(
            "Masukkan nilai strength untuk model Lora (0.0-1.0).\n"
            "Nilai yang lebih tinggi memberikan pengaruh yang lebih kuat pada hasil akhir.",
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User setting Lora strength")
        
        return LORA_STRENGTH
    
    await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
    return LORA_MENU

async def handle_lora_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Lora model category/model: {choice}")
    
    if choice == "Kembali":
        return await lora_menu(update, context)
    
    # Cek apakah user memilih kategori
    if choice == "Style Models":
        style_models = LORA_MODELS.get("style", [])
        
        keyboard = []
        row = []
        for i, model in enumerate(style_models):
            row.append(model)
            if len(row) == 2 or i == len(style_models) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append(["Kembali"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🎨 *Style Lora Models*\n\n"
            "• arcane-style: Gaya dari animasi Arcane\n"
            "• niji_express: Ilustrasi bergaya anime\n"
            "• velvia-30: Gaya film Fujifilm Velvia\n"
            "• shojo-vibe: Gaya manga Shojo\n\n"
            "Pilih model Lora:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing Style Lora models")
        
        return LORA_MODEL
    
    elif choice == "Character Models":
        character_models = LORA_MODELS.get("character", [])
        
        keyboard = []
        row = []
        for i, model in enumerate(character_models[:10]):  # Batasi tampilan untuk kejelasan
            row.append(model)
            if len(row) == 2 or i == len(character_models[:10]) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append(["Kembali"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "👤 *Character Lora Models*\n\n"
            "Model-model ini membantu membuat karakter spesifik dari anime, game, dan media lainnya.\n\n"
            "Pilih model Lora:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing Character Lora models")
        
        return LORA_MODEL
    
    elif choice == "Detail Models":
        detail_models = LORA_MODELS.get("detail", [])
        
        keyboard = []
        row = []
        for i, model in enumerate(detail_models):
            row.append(model)
            if len(row) == 2 or i == len(detail_models) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append(["Kembali"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "✨ *Detail Enhancement Lora Models*\n\n"
            "• add_detail: Menambah detail pada gambar\n"
            "• more_details: Peningkatan detail yang lebih kuat\n"
            "• more_details_XL: Peningkatan detail untuk model SDXL\n\n"
            "Pilih model Lora:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing Detail Lora models")
        
        return LORA_MODEL
    
    elif choice == "Other Models":
        other_models = LORA_MODELS.get("other", [])
        
        keyboard = []
        row = []
        for i, model in enumerate(other_models):
            row.append(model)
            if len(row) == 2 or i == len(other_models) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append(["Kembali"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🔄 *Other Lora Models*\n\n"
            "Model-model lainnya yang memiliki fungsi spesifik.\n\n"
            "Pilih model Lora:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing Other Lora models")
        
        return LORA_MODEL
    
    # Jika user memilih model spesifik
    # Cek dari semua kategori
    all_models = []
    for category in LORA_MODELS.values():
        all_models.extend(category)
    
    if choice in all_models:
        # Update model Lora
        context.user_data['settings']['lora']['model_id'] = choice
        context.user_data['settings']['lora']['enabled'] = True  # Aktifkan Lora otomatis
        
        await update.message.reply_text(f"Model Lora diubah menjadi: {choice} dan diaktifkan.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User selected Lora model: {choice} and enabled it")
        
        return await lora_menu(update, context)
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari daftar yang tersedia.")
        return LORA_MODEL

async def handle_lora_strength(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    strength_text = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User setting Lora strength: {strength_text}")
    
    if strength_text == "Kembali":
        return await lora_menu(update, context)
    
    try:
        strength = float(strength_text)
        
        if strength < 0.0 or strength > 1.0:
            await update.message.reply_text("Nilai strength harus antara 0.0 dan 1.0. Silakan coba lagi.")
            return LORA_STRENGTH
        
        # Update strength Lora
        context.user_data['settings']['lora']['strength'] = strength
        
        await update.message.reply_text(f"Strength Lora diubah menjadi: {strength}")
        
    except ValueError:
        await update.message.reply_text("Nilai tidak valid. Masukkan angka antara 0.0 dan 1.0.")
        return LORA_STRENGTH
    
    return await lora_menu(update, context)

# Advanced Settings Menu
async def advanced_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Advanced Settings menu")
    
    # Dapatkan pengaturan lanjutan saat ini
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    # Pastikan advanced ada dalam settings
    if 'advanced' not in context.user_data['settings']:
        context.user_data['settings']['advanced'] = {
            "panorama": False,
            "self_attention": False,
            "upscale": False,
            "highres_fix": False,
            "tomesd": True,
            "use_karras_sigmas": True,
            "algorithm_type": "dpmsolver+++"
        }
    
    advanced_settings = context.user_data['settings']['advanced']
    
    settings_text = "⚙️ *Pengaturan Lanjutan*\n\n"
    
    for key, value in advanced_settings.items():
        if isinstance(value, bool):
            status = "Aktif" if value else "Nonaktif"
            settings_text += f"• {key}: {status}\n"
        else:
            settings_text += f"• {key}: {value}\n"
    
    settings_text += "\nPengaturan lanjutan memungkinkan kontrol yang lebih detail atas proses generasi gambar:\n\n"
    settings_text += "• panorama: Untuk gambar panorama yang lebih lebar\n"
    settings_text += "• self_attention: Meningkatkan fokus pada detail\n"
    settings_text += "• upscale: Meningkatkan resolusi gambar akhir\n"
    settings_text += "• highres_fix: Memperbaiki artefak pada resolusi tinggi\n"
    settings_text += "• tomesd: Mempercepat pemrosesan dengan pengurangan token\n"
    settings_text += "• use_karras_sigmas: Meningkatkan kualitas dengan penjadwalan Karras\n"
    settings_text += "• algorithm_type: Algoritma sampling untuk de-noising"
    
    keyboard = [
        ["Panorama", "Self Attention", "Upscale"],
        ["Highres Fix", "TomeSd", "Karras Sigmas"],
        ["Algorithm Type", "Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ADVANCED_MENU

async def handle_advanced_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Advanced Setting option: {choice}")
    
    if choice == "Kembali":
        return await settings_menu(update, context)
    
    # Mapping dari pilihan menu ke key dalam settings
    choice_mapping = {
        "Panorama": "panorama",
        "Self Attention": "self_attention",
        "Upscale": "upscale",
        "Highres Fix": "highres_fix",
        "TomeSd": "tomesd",
        "Karras Sigmas": "use_karras_sigmas",
        "Algorithm Type": "algorithm_type"
    }
    
    setting_key = choice_mapping.get(choice)
    
    if not setting_key:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return ADVANCED_MENU
    
    # Jika pengaturan adalah boolean, toggle nilainya
    if setting_key != "algorithm_type":
        current_value = context.user_data['settings']['advanced'].get(setting_key, False)
        context.user_data['settings']['advanced'][setting_key] = not current_value
        new_status = "diaktifkan" if not current_value else "dinonaktifkan"
        
        await update.message.reply_text(f"{choice} telah {new_status}.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User {new_status} {setting_key}")
        
        return await advanced_menu(update, context)
    else:
        # Untuk algorithm_type, tampilkan pilihan
        keyboard = [
            ["dpmsolver+++", "dpm++2m"],
            ["dpm++2s a", "euler a"],
            ["Kembali"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Pilih algorithm type untuk sampling:\n\n"
            "• dpmsolver+++: Default, kualitas tinggi dengan langkah sedang\n"
            "• dpm++2m: Kualitas tinggi dengan langkah lebih sedikit\n"
            "• dpm++2s a: Variasi dengan perpaduan baik\n"
            "• euler a: Cepat dengan hasil yang bervariasi",
            reply_markup=reply_markup
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "User viewing algorithm types")
        
        return ADVANCED_SETTING_VALUE

async def handle_advanced_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected algorithm type: {value}")
    
    if value == "Kembali":
        return await advanced_menu(update, context)
    
    # Perbarui nilai algorithm_type
    context.user_data['settings']['advanced']['algorithm_type'] = value
    
    await update.message.reply_text(f"Algorithm Type diubah menjadi: {value}")
    
    return await advanced_menu(update, context)

# Get System Info
async def get_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User requested System Info")
    
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"📊 *System Info*\n\n{FEATURE_DESCRIPTIONS['system_info']}\n\nMengambil informasi...",
        parse_mode="Markdown"
    )
    
    # Tambahkan pesan loading
    loading_message = await update.message.reply_text("⏳ Mengambil informasi sistem...")
    
    try:
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        server_id = settings.get('server_id', 'rose')
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        api_base_url = get_api_base_url(settings)
        
        # Gunakan requests library untuk lebih andal
        response = requests.get(
            f"{api_base_url}/sdapi/system_details?server_id={server_id}",
            headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
            timeout=30
        )
        
        # Hapus pesan loading
        await loading_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if 'result' in data:
                # Format info agar lebih mudah dibaca
                system_info = data.get('result', {})
                info_text = f"🖥️ **System Info**\n\n"
                
                if 'gpu' in system_info:
                    info_text += f"🎮 **GPU**: {system_info['gpu']}\n"
                if 'available_models' in system_info:
                    info_text += f"🧠 **Models**: {', '.join(system_info['available_models'])}\n"
                if 'ram' in system_info:
                    info_text += f"💾 **RAM**: {system_info['ram']}\n"
                if 'cuda_version' in system_info:
                    info_text += f"⚙️ **CUDA**: {system_info['cuda_version']}\n"
                
                sent_message = await update.message.reply_text(info_text, parse_mode="Markdown")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"System info: {system_info}")
            else:
                await update.message.reply_text("Tidak dapat memperoleh informasi sistem dari respons.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to extract system info from response")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error when getting system info: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await loading_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for system info timed out")
    
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        await loading_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error getting system info: {str(e)}")
    
    # Kembali ke menu utama
    await start_verified(update, context)

# Help & About menu
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Help menu")
    
    keyboard = [
        ["📖 Fitur-fitur", "ℹ️ About"],
        ["📚 Tutorial", "🔙 Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "❓ *Help & About*\n\nPilih informasi yang ingin dilihat:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return HELP_CHOICE

async def handle_help_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Help option: {choice}")
    
    if choice == "📖 Fitur-fitur":
        features_text = "📖 *Daftar Fitur*\n\n"
        
        for feature, description in FEATURE_DESCRIPTIONS.items():
            if feature == "txt2img":
                features_text += "🖼 *Text to Image*\n"
            elif feature == "old_txt2img":
                features_text += "📜 *Old Text to Image*\n"
            elif feature == "img2img":
                features_text += "🎨 *Image to Image*\n"
            elif feature == "generate_prompt":
                features_text += "🧠 *Generate Prompt*\n"
            elif feature == "system_info":
                features_text += "📊 *System Info*\n"
            elif feature == "settings":
                features_text += "⚙️ *Settings*\n"
            elif feature == "imgproc":
                features_text += "🔄 *Image Processing*\n"
            elif feature == "inpaint":
                features_text += "✏️ *Inpainting*\n"
            elif feature == "face_fusion":
                features_text += "👤 *Face Fusion*\n"
            elif feature == "tiktok":
                features_text += "📱 *TikTok Downloader*\n"
            elif feature == "instagram":
                features_text += "📸 *Instagram Downloader*\n"
            elif feature == "gpt":
                features_text += "🤖 *Chat GPT*\n"
            elif feature == "tts":
                features_text += "🔊 *Text to Speech*\n"
            elif feature == "ollama":
                features_text += "🧠 *Ollama Chatbot*\n"
            
            features_text += f"{description}\n\n"
            
        sent_message = await update.message.reply_text(features_text, parse_mode="Markdown")
        return HELP_CHOICE
        
    elif choice == "ℹ️ About":
        about_text = (
            "ℹ️ *About Ngorok Bot*\n\n"
            "Ngorok adalah bot AI multifungsi yang menggabungkan kemampuan generasi gambar, pemrosesan media, dan interaksi AI menggunakan teknologi terkini.\n\n"
            "Dibuat dengan oleh:\n"
            "Telegram: @k4ies\n"
            "Facebook: Arif Maulana\n"
            "Instagram: @4rfmln\n\n"
            "Ngorok bot - Beta test\n"
            "Versi bot: 3.0.0"
        )
        sent_message = await update.message.reply_text(about_text, parse_mode="Markdown")
        return HELP_CHOICE
        
    elif choice == "📚 Tutorial":
        tutorial_text = (
            "📚 *Tutorial Menggunakan Ngorok Bot*\n\n"
            "*Text to Image*:\n"
            "1. Klik '🖼 Text to Image'\n"
            "2. Masukkan deskripsi gambar (prompt)\n"
            "3. Masukkan URL gambar inisialisasi atau ketik 'skip'\n\n"
            
            "*Old Text to Image*:\n"
            "1. Klik '📜 Old Text to Image'\n"
            "2. Masukkan deskripsi gambar (prompt)\n"
            "3. Pilih model lama yang ingin digunakan\n\n"
            
            "*Image to Image*:\n"
            "1. Klik '🎨 Image to Image'\n"
            "2. Kirim gambar atau URL gambar\n"
            "3. Masukkan prompt untuk memodifikasi gambar\n\n"
            
            "*Inpainting*:\n"
            "1. Klik '✏️ Inpainting'\n"
            "2. Kirim gambar yang ingin dimodifikasi\n"
            "3. Tandai area yang ingin diubah menggunakan fitur coretan Telegram\n"
            "4. Masukkan prompt untuk konten pengganti\n\n"
            
            "*Generate Prompt*:\n"
            "1. Klik '🧠 Generate Prompt'\n"
            "2. Kirim gambar untuk dianalisis\n"
            "3. Bot akan menghasilkan prompt berdasarkan gambar\n\n"
            
            "*Image Processing*:\n"
            "1. Klik '🔄 Image Processing'\n"
            "2. Pilih jenis pemrosesan yang diinginkan\n"
            "3. Kirim gambar yang ingin diproses\n\n"
            
            "*Face Fusion*:\n"
            "1. Klik '👤 Face Fusion'\n"
            "2. Lihat template yang tersedia atau gunakan langsung\n"
            "3. Pilih template dan kirim gambar wajah Anda\n\n"
            
            "*TikTok & Instagram Downloader*:\n"
            "1. Klik '📱 TikTok Downloader' atau '📸 Instagram Downloader'\n"
            "2. Kirim URL konten yang ingin diunduh\n"
            "3. Tunggu sampai konten diunduh\n\n"
            
            "*Chat GPT*:\n"
            "1. Klik '🤖 Chat GPT'\n"
            "2. Kirim pesan atau pertanyaan Anda\n"
            "3. Bot akan menjawab pertanyaan Anda seperti ChatGPT\n"
            "4. Anda juga bisa mengirim gambar untuk dianalisis dengan GPT Vision\n\n"
            
            "*Ollama Chatbot*:\n"
            "1. Klik '🧠 Ollama Chatbot'\n"
            "2. Kirim pesan atau pertanyaan Anda\n"
            "3. Anda bisa mengganti model dengan klik 'Ganti Model'\n"
            "4. Percakapan akan tetap berjalan hingga Anda klik tombol 'Kembali'\n\n"
            
            "*Text to Speech*:\n"
            "1. Klik '🔊 Text to Speech'\n"
            "2. Pilih suara atau clone suara Anda sendiri\n"
            "3. Masukkan teks untuk dikonversi menjadi suara\n\n"
            
            "*Settings*:\n"
            "1. Klik '⚙️ Settings'\n"
            "2. Pilih pengaturan yang ingin diubah\n"
            "3. Untuk beralih server, pilih 'Server ID' dan pilih 'rose' atau 'lovita'\n"
            "4. Anda juga dapat mengaktifkan/menonaktifkan 'Enhance Prompt', mengatur 'ControlNet', dan 'Lora Models'\n\n"
        )
        sent_message = await update.message.reply_text(tutorial_text, parse_mode="Markdown")
        return HELP_CHOICE
        
    elif choice == "🔙 Kembali":
        await start_verified(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih lagi.")
        return HELP_CHOICE

# Image Processing Menu
async def imgproc_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Image Processing menu")
    
    keyboard = [
        ["🖌️ Advance Beauty", "🤖 AI Avatar"],
        ["🎨 Colorize", "⚡ Enhance"],
        ["🔍 Super Resolution", "🌄 Outpainting"],
        ["🔲 Remove Background", "🔎 Unblur"],
        ["🔙 Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Tampilkan menu
    if not from_callback:
        await update.message.reply_text(
            f"🔄 *Image Processing*\n\n{FEATURE_DESCRIPTIONS['imgproc']}\n\nPilih jenis pemrosesan gambar:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Jika dipanggil dari callback, kita perlu menggunakan query.message
        await update.callback_query.message.reply_text(
            f"🔄 *Image Processing*\n\n{FEATURE_DESCRIPTIONS['imgproc']}\n\nPilih jenis pemrosesan gambar:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return IMGPROC_CHOICE

async def handle_imgproc_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Image Processing option: {choice}")
    
    # Reset image processing settings
    if 'imgproc_settings' in context.user_data:
        del context.user_data['imgproc_settings']
    
    # Simpan pilihan pemrosesan
    if "Advance Beauty" in choice:
        context.user_data['imgproc_type'] = "advance_beauty"
        await update.message.reply_text(
            f"🖌️ *Advance Beauty*\n\n{IMGPROC_DESCRIPTIONS['advance_beauty']}\n\n"
            "Silakan kirim gambar yang ingin diproses. Pastikan gambar memiliki wajah yang jelas.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "AI Avatar" in choice:
        context.user_data['imgproc_type'] = "ai_avatar"
        await update.message.reply_text(
            f"🤖 *AI Avatar*\n\n{IMGPROC_DESCRIPTIONS['ai_avatar']}\n\n"
            "Silakan kirim gambar wajah yang ingin diubah menjadi avatar AI.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "Colorize" in choice:
        context.user_data['imgproc_type'] = "colorize"
        await update.message.reply_text(
            f"🎨 *Colorize*\n\n{IMGPROC_DESCRIPTIONS['colorize']}\n\n"
            "Silakan kirim gambar hitam putih atau gambar dengan warna pudar yang ingin diwarnai.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "Enhance" in choice:
        context.user_data['imgproc_type'] = "enhance"
        await update.message.reply_text(
            f"⚡ *Enhance*\n\n{IMGPROC_DESCRIPTIONS['enhance']}\n\n"
            "Silakan kirim gambar yang ingin ditingkatkan kualitasnya.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "Super Resolution" in choice:
        context.user_data['imgproc_type'] = "gfp_superres"
        
        # Tanyakan outscale terlebih dahulu
        keyboard = [
            ["2x", "4x"],
            ["Kembali"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"🔍 *Super Resolution*\n\n{IMGPROC_DESCRIPTIONS['gfp_superres']}\n\n"
            "Pilih tingkat peningkatan resolusi (upscale factor):",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return SUPERRES_SETTINGS
    
    elif "Outpainting" in choice:
        context.user_data['imgproc_type'] = "outpainting"
        
        # Gunakan pengaturan default untuk outpainting
        context.user_data['imgproc_settings'] = {
            "expand_mode": "separate",
            "expand_ratio": 0.125,
            "free_expand_ratio": {
                "left": 0.1,
                "right": 0.1,
                "top": 0.1,
                "bottom": 0.1
            }
        }
        
        await update.message.reply_text(
            f"🌄 *Outpainting*\n\n{IMGPROC_DESCRIPTIONS['outpainting']}\n\n"
            "Menggunakan pengaturan default untuk outpainting.\n"
            "• Mode: separate\n"
            "• Rasio ekspansi: 12.5%\n"
            "• Rasio kiri/kanan/atas/bawah: 10%\n\n"
            "Silakan kirim gambar yang ingin diperluas.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "Remove Background" in choice:
        context.user_data['imgproc_type'] = "rembg"
        await update.message.reply_text(
            f"🔲 *Remove Background*\n\n{IMGPROC_DESCRIPTIONS['rembg']}\n\n"
            "Silakan kirim gambar yang ingin dihapus latar belakangnya.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "Unblur" in choice:
        context.user_data['imgproc_type'] = "unblur"
        
        # Gunakan pengaturan default untuk unblur
        context.user_data['imgproc_settings'] = {
            "pipeline": {
                "bokeh": "background_blur_low",
                "color_enhance": "prism-blend",
                "background_enhance": "shiba-strong-tensorrt",
                "face_lifting": "pinko_bigger_dataset-style",
                "face_enhance": "recommender_entire_dataset"
            }
        }
        
        await update.message.reply_text(
            f"🔎 *Unblur*\n\n{IMGPROC_DESCRIPTIONS['unblur']}\n\n"
            "Menggunakan pengaturan default optimal untuk unblur.\n"
            "Silakan kirim gambar buram yang ingin dipertajam.",
            parse_mode="Markdown"
        )
        return IMGPROC_IMAGE
    
    elif "Kembali" in choice:
        await start_verified(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return IMGPROC_CHOICE

# Settings for specific image processing types
async def handle_superres_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Super Resolution scale: {response}")
    
    if response.lower() == "kembali":
        return await imgproc_menu(update, context)
    
    if response in ["2x", "4x"]:
        # Simpan setting
        outscale = 2 if response == "2x" else 4
        context.user_data['imgproc_settings'] = {"outscale": outscale}
        await update.message.reply_text(
            f"Outscale diatur ke {outscale}x. Silakan kirim gambar yang ingin ditingkatkan resolusinya."
        )
        return IMGPROC_IMAGE
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih '2x' atau '4x'.")
        return SUPERRES_SETTINGS

async def handle_imgproc_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Dapatkan jenis pemrosesan yang dipilih
    imgproc_type = context.user_data.get('imgproc_type')
    imgproc_settings = context.user_data.get('imgproc_settings', {})
    
    if not imgproc_type:
        await update.message.reply_text("Terjadi kesalahan. Silakan mulai ulang proses.")
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, f"User uploaded image for {imgproc_type}")
        
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to upload image for {imgproc_type}")
                
                return IMGPROC_IMAGE
            
            # Update pesan proses
            await process_message.edit_text(f"⏳ Sedang memproses gambar dengan {imgproc_type}...")
            
            # Cek apakah ini adalah base64 atau URL
            if image_data.startswith(('http://', 'https://')):
                # Ini adalah URL
                init_image = image_data
            else:
                # Ini adalah base64, format dengan benar
                init_image = f"data:image/jpeg;base64,{image_data}"
            
            # Persiapkan payload berdasarkan jenis pemrosesan
            payload = {"init_image": init_image}
            
            # Tambahkan parameter khusus dari imgproc_settings jika ada
            if imgproc_settings:
                payload.update(imgproc_settings)
            
            # Tambahkan parameter khusus untuk advance_beauty jika belum ada
            if imgproc_type == "advance_beauty" and "ai_optimize" not in payload:
                payload.update({
                    "ai_optimize": {
                        "boy_face_beauty_alpha": 25,
                        "girl_face_beauty_alpha": 25,
                        "child_face_beauty_alpha": 25,
                        "man_ai_shrink_head": 0,
                        "girl_ai_shrink_head": 0,
                        "child_ai_shrink_head": 0
                    },
                    "enhance": {
                        "radio": 25
                    },
                    "face": {
                        "face_forehead_boy": -40,
                        "face_forehead_girl": -40,
                        "face_forehead_child": 0,
                        "narrow_face_boy": 0,
                        "narrow_face_girl": 0,
                        "narrow_face_child": 0,
                        "jaw_trans_boy": 0,
                        "jaw_trans_girl": 0,
                        "jaw_trans_child": 0,
                        "face_trans_boy": -30,
                        "face_trans_girl": -30,
                        "face_trans_child": -30
                    }
                })
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Gunakan requests untuk API call
            response = requests.post(
                f"{api_base_url}/image/{imgproc_type}",
                json=payload,
                headers={
                    'Content-Type': "application/json",
                    'Authorization': f"Bearer {ITSROSE_API_KEY}"
                },
                timeout=120  # 120 detik timeout
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False):
                    if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                        image_url = data['result']['images'][0]
                        
                        # Tambahkan tombol untuk proses lebih lanjut
                        keyboard = [
                            [InlineKeyboardButton("🔄 Proses dengan Image Processing lagi", callback_data="use_for_imgproc")],
                            [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Simpan URL gambar untuk digunakan nanti
                        context.user_data['last_image_url'] = image_url
                        
                        # Send image with enhanced download and send function
                        caption = f"Hasil pemrosesan {imgproc_type}"
                        success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Image processing {imgproc_type} result URL: {image_url}")
                        
                        if not success:
                            # If failed to send image, provide additional information
                            await update.message.reply_text(
                                "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                                "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                                "Anda masih dapat melihat gambar melalui URL yang diberikan."
                            )
                    else:
                        await update.message.reply_text("Gambar berhasil diproses tetapi tidak ada URL yang dikembalikan.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Image processing {imgproc_type} successful but no URL returned")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal memproses gambar: {error_message}")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Failed to process image with {imgproc_type}: {error_message}")
                    
                    # Informasi tambahan untuk error tertentu
                    if "Backend communication error" in error_message:
                        await update.message.reply_text(
                            "⚠️ Sepertinya ada masalah pada server backend. Ini biasanya terjadi ketika layanan sedang sibuk atau dalam pemeliharaan. "
                            "Silakan coba lagi nanti atau coba jenis pemrosesan gambar lainnya."
                        )
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error for {imgproc_type}: {response.status_code}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"API request for {imgproc_type} timed out")
        
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error processing image with {imgproc_type}: {str(e)}")
    
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        if update.message.text.lower() == "kembali":
            await imgproc_menu(update, context)
            return IMGPROC_CHOICE
        
        # Validasi URL
        url = update.message.text.strip()
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided image URL for {imgproc_type}: {url}")
        
        if url.startswith(('http://', 'https://')):
            process_message = await update.message.reply_text(f"⏳ Sedang memproses gambar dengan {imgproc_type}...")
            
            try:
                # Persiapkan payload berdasarkan jenis pemrosesan
                payload = {"init_image": url}
                
                # Tambahkan parameter khusus dari imgproc_settings jika ada
                if imgproc_settings:
                    payload.update(imgproc_settings)
                
                # Tambahkan parameter khusus untuk advance_beauty jika belum ada
                if imgproc_type == "advance_beauty" and "ai_optimize" not in payload:
                    payload.update({
                        "ai_optimize": {
                            "boy_face_beauty_alpha": 25,
                            "girl_face_beauty_alpha": 25,
                            "child_face_beauty_alpha": 25,
                            "man_ai_shrink_head": 0,
                            "girl_ai_shrink_head": 0,
                            "child_ai_shrink_head": 0
                        },
                        "enhance": {
                            "radio": 25
                        },
                        "face": {
                            "face_forehead_boy": -40,
                            "face_forehead_girl": -40,
                            "face_forehead_child": 0,
                            "narrow_face_boy": 0,
                            "narrow_face_girl": 0,
                            "narrow_face_child": 0,
                            "jaw_trans_boy": 0,
                            "jaw_trans_girl": 0,
                            "jaw_trans_child": 0,
                            "face_trans_boy": -30,
                            "face_trans_girl": -30,
                            "face_trans_child": -30
                        }
                    })
                
                # Dapatkan base URL berdasarkan server_id yang dipilih
                settings = context.user_data.get('settings', DEFAULT_SETTINGS)
                api_base_url = get_api_base_url(settings)
                
                # Gunakan requests untuk API call
                response = requests.post(
                    f"{api_base_url}/image/{imgproc_type}",
                    json=payload,
                    headers={
                        'Content-Type': "application/json",
                        'Authorization': f"Bearer {ITSROSE_API_KEY}"
                    },
                    timeout=120  # 120 detik timeout
                )
                
                # Hapus pesan proses
                await process_message.delete()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('status', False):
                        if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                            image_url = data['result']['images'][0]
                            
                            # Tambahkan tombol untuk proses lebih lanjut
                            keyboard = [
                                [InlineKeyboardButton("🔄 Proses dengan Image Processing lagi", callback_data="use_for_imgproc")],
                                [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            # Simpan URL gambar untuk digunakan nanti
                            context.user_data['last_image_url'] = image_url
                            
                            # Send image with enhanced download and send function
                            caption = f"Hasil pemrosesan {imgproc_type}"
                            success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", f"Image processing {imgproc_type} from URL result: {image_url}")
                            
                            if not success:
                                # If failed to send image, provide additional information
                                await update.message.reply_text(
                                    "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                                    "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                                    "Anda masih dapat melihat gambar melalui URL yang diberikan."
                                )
                        else:
                            await update.message.reply_text("Gambar berhasil diproses tetapi tidak ada URL yang dikembalikan.")
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", f"Image processing {imgproc_type} from URL successful but no URL returned")
                    else:
                        error_message = data.get('message', 'Tidak ada detail error')
                        await update.message.reply_text(f"Gagal memproses gambar: {error_message}")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Failed to process image with {imgproc_type} from URL: {error_message}")
                        
                        # Informasi tambahan untuk error tertentu
                        if "Backend communication error" in error_message:
                            await update.message.reply_text(
                                "⚠️ Sepertinya ada masalah pada server backend. Ini biasanya terjadi ketika layanan sedang sibuk atau dalam pemeliharaan. "
                                "Silakan coba lagi nanti atau coba jenis pemrosesan gambar lainnya."
                            )
                else:
                    await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Server error for {imgproc_type} from URL: {response.status_code}")
            
            except requests.exceptions.Timeout:
                await process_message.delete()
                await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"API request for {imgproc_type} from URL timed out")
            
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                await process_message.delete()
                await update.message.reply_text(f"Error: {str(e)}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Error processing image with {imgproc_type} from URL: {str(e)}")
                
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return IMGPROC_IMAGE
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return IMGPROC_IMAGE
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# Face Fusion Menu
async def face_fusion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Face Fusion menu")
    
    keyboard = [
        ["🔍 Lihat Template", "👤 Buat Face Fusion"],
        ["🔙 Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"👤 *Face Fusion*\n\n{FEATURE_DESCRIPTIONS['face_fusion']}\n\nPilih opsi:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return FACE_FUSION_CHOICE

async def handle_face_fusion_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Face Fusion option: {choice}")
    
    if "Lihat Template" in choice:
        # Ambil daftar template
        process_message = await update.message.reply_text("⏳ Mengambil daftar template...")
        
        try:
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            response = requests.get(
                f"{api_base_url}/face_fusion/templates",
                headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                timeout=30
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False) and 'result' in data and 'templates' in data['result']:
                    templates = data['result']['templates']
                    
                    # Tampilkan daftar template dengan numbering
                    template_text = f"🎭 *Template Face Fusion Tersedia*\n\n"
                    
                    # Buat keyboard untuk pilihan template dengan numbering
                    keyboard = []
                    template_mapping = {}  # Mapping dari nomor template ke template ID
                    
                    for i, template in enumerate(templates):
                        template_id = template.get('id', 'unknown')
                        template_name = template.get('name', 'Unnamed Template')
                        template_gender = template.get('gender', 'Unknown')
                        
                        # Buat nomor template (1, 2, 3, ...)
                        template_number = str(i + 1)
                        template_mapping[template_number] = template_id
                        
                        # Tambahkan ke template_text
                        template_text += f"• Template #{template_number}\n  ID: {template_id}\n  Nama: {template_name}\n  Gender: {template_gender}\n\n"
                        
                        # Tambahkan ke keyboard
                        if i % 5 == 0:
                            keyboard.append([])
                        keyboard[-1].append(template_number)
                    
                    # Simpan mapping untuk digunakan nanti
                    context.user_data['template_mapping'] = template_mapping
                    
                    # Tambahkan tombol kembali
                    keyboard.append(["🔙 Kembali"])
                    
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    # Simpan templates untuk digunakan nanti
                    context.user_data['face_fusion_templates'] = templates
                    
                    # Tampilkan contoh beberapa template
                    if templates:
                        # Kirim template text
                        await update.message.reply_text(
                            template_text + "\nSilakan pilih nomor template untuk melakukan face fusion:",
                            reply_markup=reply_markup
                        )
                        
                        # Forward to owner bot - summary of templates
                        await forward_to_owner(update, context, "text", f"User viewing Face Fusion templates, {len(templates)} templates available")
                        
                        # Kirim beberapa contoh template (max 5)
                        sample_templates = templates[:min(5, len(templates))]
                        
                        for i, template in enumerate(sample_templates):
                            template_url = template.get('url', '')
                            template_name = template.get('name', 'Unnamed Template')
                            template_id = template.get('id', 'unknown')
                            
                            if template_url:
                                await update.message.reply_photo(
                                    photo=template_url,
                                    caption=f"Template #{i+1}: {template_name}\nID: {template_id}"
                                )
                                
                                # Forward first template to owner as example
                                if i == 0:
                                    await forward_to_owner(update, context, "text", f"Sample template: {template_name} (ID: {template_id})")
                    else:
                        await update.message.reply_text(f"Tidak ada template yang tersedia.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "No Face Fusion templates available")
                        
                        return await face_fusion_menu(update, context)
                else:
                    await update.message.reply_text("Gagal mendapatkan daftar template.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "Failed to get Face Fusion templates")
                    
                    return await face_fusion_menu(update, context)
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error when getting Face Fusion templates: {response.status_code}")
                
                return await face_fusion_menu(update, context)
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "API request for Face Fusion templates timed out")
            
            return await face_fusion_menu(update, context)
        
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error getting Face Fusion templates: {str(e)}")
            
            return await face_fusion_menu(update, context)
        
        return FACE_FUSION_TEMPLATE
    
    elif "Buat Face Fusion" in choice:
        await update.message.reply_text(
            "Silakan masukkan ID template atau nomor template yang ingin digunakan. Gunakan 'Lihat Template' jika Anda belum mengetahui ID template."
        )
        return FACE_FUSION_TEMPLATE
    
    elif "Kembali" in choice:
        await start_verified(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return FACE_FUSION_CHOICE

async def handle_face_fusion_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    template_input = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Face Fusion template: {template_input}")
    
    if template_input == "🔙 Kembali":
        return await face_fusion_menu(update, context)
    
    # Cek apakah input adalah nomor template
    template_id = None
    template_mapping = context.user_data.get('template_mapping', {})
    
    if template_input in template_mapping:
        # User menggunakan nomor template
        template_id = template_mapping[template_input]
    else:
        # User menggunakan ID template langsung
        template_id = template_input
    
    # Simpan template ID
    context.user_data['face_fusion_template_id'] = template_id
    
    # Instruksi untuk mengirim gambar
    await update.message.reply_text(
        f"Anda memilih template dengan ID: {template_id}\n\n"
        "Silakan kirim gambar wajah Anda untuk digabungkan dengan template terpilih.\n"
        "Pastikan wajah terlihat jelas dan dari sudut depan untuk hasil terbaik."
    )
    
    return FACE_FUSION_IMAGE

async def handle_face_fusion_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    template_id = context.user_data.get('face_fusion_template_id', '')
    
    if not template_id:
        await update.message.reply_text("Template ID tidak tersedia. Silakan mulai ulang proses.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "Face Fusion failed: No template ID")
        
        return await face_fusion_menu(update, context)
    
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Forward to owner bot
        await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, f"User uploaded face image for Face Fusion with template ID: {template_id}")
        
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "Failed to upload image for Face Fusion")
                
                return FACE_FUSION_IMAGE
            
            # Update pesan proses
            await process_message.edit_text("⏳ Sedang membuat face fusion...")
            
            # Cek apakah ini adalah base64 atau URL
            if image_data.startswith(('http://', 'https://')):
                # Ini adalah URL
                init_image = image_data
            else:
                # Ini adalah base64, format dengan benar
                init_image = f"data:image/jpeg;base64,{image_data}"
            
            # Persiapkan payload sesuai dokumentasi API
            payload = {
                "id": template_id,
                "init_image": init_image
            }
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Gunakan requests untuk API call dengan retry
            max_retries = 3
            success = False
            
            for retry in range(max_retries):
                try:
                    response = requests.post(
                        f"{api_base_url}/face_fusion/create",
                        json=payload,
                        headers={
                            'Content-Type': "application/json",
                            'Authorization': f"Bearer {ITSROSE_API_KEY}"
                        },
                        timeout=120  # 120 detik timeout
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get('status', False) and 'result' in data:
                            # Cek apakah ada videos atau URL dalam respons
                            if 'videos' in data['result'] and data['result']['videos']:
                                success = True
                                video_url = data['result']['videos'][0]
                                
                                # Tampilkan info tambahan
                                duration = data['result'].get('duration_second', 0)
                                fps = data['result'].get('fps', '30')
                                dimensions = f"{data['result'].get('width', 720)}x{data['result'].get('height', 1280)}"
                                
                                # Tambahkan tombol untuk proses lebih lanjut
                                keyboard = [
                                    [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                
                                # Hapus pesan proses
                                await process_message.delete()
                                
                                # Kirim info
                                info_text = f"✅ Face Fusion berhasil dibuat!\n\n" \
                                           f"• Template ID: {template_id}\n" \
                                           f"• Durasi: {duration} detik\n" \
                                           f"• FPS: {fps}\n" \
                                           f"• Resolusi: {dimensions}"
                                
                                await update.message.reply_text(info_text)
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", f"Face Fusion video created: {video_url}")
                                
                                # Kirim video
                                try:
                                    # Download video
                                    video_response = requests.get(video_url, timeout=60, stream=True)
                                    
                                    if video_response.status_code == 200:
                                        # Save to temporary file
                                        import uuid
                                        temp_filename = f"temp_video_{uuid.uuid4()}.mp4"
                                        
                                        with open(temp_filename, "wb") as f:
                                            for chunk in video_response.iter_content(chunk_size=8192):
                                                if chunk:
                                                    f.write(chunk)
                                        
                                        # Send as video
                                        with open(temp_filename, "rb") as f:
                                            sent_video = await update.message.reply_video(
                                                video=f,
                                                caption=f"Face Fusion dengan template ID: {template_id}",
                                                reply_markup=reply_markup
                                            )
                                            
                                            # Forward to owner bot
                                            await forward_to_owner(update, context, "text", "Face Fusion video sent to user")
                                        
                                        # Clean up
                                        import os
                                        os.remove(temp_filename)
                                    else:
                                        # Fallback to URL
                                        await update.message.reply_text(
                                            f"Video face fusion tersedia di URL ini: {video_url}"
                                        )
                                        
                                        # Forward to owner bot
                                        await forward_to_owner(update, context, "text", "Failed to download Face Fusion video, sent URL instead")
                                except Exception as e:
                                    logger.error(f"Error sending face fusion video: {str(e)}")
                                    await update.message.reply_text(
                                        f"Face fusion berhasil dibuat tetapi gagal mengirim video. "
                                        f"Anda dapat mengakses video di: {video_url}"
                                    )
                                    
                                    # Forward to owner bot
                                    await forward_to_owner(update, context, "text", f"Error sending Face Fusion video: {str(e)}")
                                
                                break  # Keluar dari loop retry jika berhasil
                            elif 'url' in data['result']:
                                # Format respons lama, handle juga
                                success = True
                                image_url = data['result']['url']
                                
                                # Simpan URL gambar untuk digunakan nanti
                                context.user_data['last_image_url'] = image_url
                                
                                # Tambahkan tombol untuk proses lebih lanjut
                                keyboard = [
                                    [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")],
                                    [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                
                                # Send image with enhanced download and send function
                                caption = f"Hasil face fusion dengan template ID: {template_id}"
                                success = await download_and_send_image(update, context, image_url, caption, reply_markup)
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", f"Face Fusion image created: {image_url}")
                                
                                if not success:
                                    # If failed to send image, provide additional information
                                    await update.message.reply_text(
                                        "⚠️ Gambar berhasil dibuat tetapi ada masalah saat mengirimnya. "
                                        "Ini mungkin karena masalah jaringan atau keterbatasan Telegram. "
                                        "Anda masih dapat melihat gambar melalui URL yang diberikan."
                                    )
                                
                                break  # Keluar dari loop retry jika berhasil
                            else:
                                await update.message.reply_text("Face fusion berhasil tetapi tidak ada URL yang dikembalikan.")
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", "Face Fusion success but no URL returned")
                        else:
                            error_message = data.get('message', 'Tidak ada detail error')
                            await update.message.reply_text(f"Gagal membuat face fusion: {error_message}")
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", f"Failed to create Face Fusion: {error_message}")
                    else:
                        await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Server error for Face Fusion: {response.status_code}")
                
                except requests.exceptions.Timeout:
                    if retry == max_retries - 1:  # Jika ini percobaan terakhir
                        await process_message.delete()
                        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "API request for Face Fusion timed out")
                    continue  # Coba lagi jika bukan percobaan terakhir
                
                except Exception as e:
                    if retry == max_retries - 1:  # Jika ini percobaan terakhir
                        logger.error(f"Error creating face fusion: {str(e)}")
                        await process_message.delete()
                        await update.message.reply_text(f"Error: {str(e)}")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Error creating Face Fusion: {str(e)}")
                    continue  # Coba lagi jika bukan percobaan terakhir
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "API request for Face Fusion timed out (outer timeout)")
        
        except Exception as e:
            logger.error(f"Error creating face fusion: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error creating Face Fusion (outer error): {str(e)}")
    
    elif update.message.text:
        if update.message.text.lower() == "kembali":
            return await face_fusion_menu(update, context)
        
        # Jika pengguna mengirim URL alih-alih gambar
        url = update.message.text.strip()
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User provided image URL for Face Fusion: {url}")
        
        if url.startswith(('http://', 'https://')):
            # Handle URL logic (similar to photo handling)
            # For brevity, this part is simplified
            context.user_data['face_fusion_init_image'] = url
            # Launch the same processing as for photo
            # ...
            await update.message.reply_text("Memproses URL gambar...")
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return FACE_FUSION_IMAGE
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return FACE_FUSION_IMAGE
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# TikTok Downloader
async def tiktok_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed TikTok Downloader")
    
    await update.message.reply_text(
        f"📱 *TikTok Downloader*\n\n{FEATURE_DESCRIPTIONS['tiktok']}\n\n"
        "Silakan kirim URL video TikTok yang ingin diunduh:",
        parse_mode="Markdown"
    )
    return TIKTOK_URL

async def handle_tiktok_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tiktok_url = update.message.text.strip()
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User provided TikTok URL: {tiktok_url}")
    
    if tiktok_url.lower() == "kembali":
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Validasi URL
    if not tiktok_url.startswith(('http://', 'https://')) or 'tiktok.com' not in tiktok_url:
        await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https:// dan merupakan URL TikTok.")
        return TIKTOK_URL
    
    # Pesan sedang memproses
    process_message = await update.message.reply_text("⏳ Sedang mengunduh video TikTok...")
    
    try:
        # Dapatkan base URL berdasarkan server_id yang dipilih
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        # Gunakan requests library untuk API call
        response = requests.get(
            f"{api_base_url}/tiktok/get",
            params={"url": tiktok_url},
            headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
            timeout=60  # 60 detik timeout
        )
        
        # Hapus pesan proses
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False) and 'result' in data:
                result = data['result']
                
                # Informasi video
                author = result.get('author', {}).get('nickname', 'Unknown')
                desc = result.get('desc', 'TikTok Video')
                duration = result.get('duration', 0)
                
                # Info caption
                info_text = f"🎬 Video TikTok\n\n"
                info_text += f"👤 Author: {author}\n"
                info_text += f"📝 Description: {desc}\n"
                info_text += f"⏱️ Duration: {duration} seconds\n"
                
                # Kirim info terlebih dahulu
                await update.message.reply_text(info_text)
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Downloaded TikTok from {author}, description: {desc}")
                
                # Cek dan kirim video
                if result.get('type') == 'video' and 'download' in result:
                    download_info = result['download']
                    video_url = download_info.get('nowm', '')  # Prefer no watermark version
                    
                    if not video_url and 'wm' in download_info:
                        video_url = download_info.get('wm', '')  # Fallback to watermark version
                    
                    if video_url:
                        # Kirim video sebagai video (atau dokumen jika terlalu besar)
                        try:
                            # Download video untuk mencegah masalah
                            video_response = requests.get(video_url, timeout=45, stream=True)
                            
                            if video_response.status_code == 200:
                                # Simpan ke file sementara dengan nama unik
                                import uuid
                                temp_filename = f"temp_video_{uuid.uuid4()}.mp4"
                                
                                with open(temp_filename, "wb") as f:
                                    for chunk in video_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                # Kirim sebagai video
                                with open(temp_filename, "rb") as f:
                                    sent_video = await update.message.reply_video(
                                        video=f,
                                        caption=f"Video TikTok by {author}"
                                    )
                                    
                                    # Forward to owner bot
                                    await forward_to_owner(update, context, "text", f"Sent TikTok video to user")
                                
                                # Hapus file sementara
                                import os
                                try:
                                    os.remove(temp_filename)
                                except Exception as e:
                                    logger.warning(f"Could not remove temp file: {str(e)}")
                                    
                            else:
                                # Fallback - kirim URL jika tidak bisa mengirim video langsung
                                await update.message.reply_text(
                                    f"Video terlalu besar untuk dikirim langsung. Anda dapat mengunduhnya dari link ini:\n{video_url}"
                                )
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", f"Video too large to send directly, sent URL instead")
                        except Exception as e:
                            logger.error(f"Error sending video: {str(e)}")
                            # Fallback - kirim URL jika tidak bisa mengirim video langsung
                            await update.message.reply_text(
                                f"Video terlalu besar untuk dikirim langsung. Anda dapat mengunduhnya dari link ini:\n{video_url}"
                            )
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", f"Error sending TikTok video: {str(e)}")
                # Handle image posts
                elif result.get('type') == 'images' and 'download' in result and 'images' in result['download']:
                    images = result['download']['images']
                    
                    await update.message.reply_text("Ini adalah post gambar. Mengirim semua gambar...")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"TikTok post contains {len(images)} images")
                    
                    # Kirim hingga 10 gambar
                    for i, image_url in enumerate(images[:10]):
                        if image_url:
                            try:
                                # Send image with enhanced download and send function
                                caption = f"Image {i+1}/{min(len(images), 10)} from TikTok by {author}"
                                success = await download_and_send_image(update, context, image_url, caption)
                                
                                if not success:
                                    # If failed to send image, provide direct URL
                                    await update.message.reply_text(f"Tidak dapat mengirim gambar {i+1}: {image_url}")
                                    
                                    # Forward to owner bot
                                    await forward_to_owner(update, context, "text", f"Failed to send TikTok image {i+1}")
                            except Exception as e:
                                logger.error(f"Error sending image: {str(e)}")
                                await update.message.reply_text(f"Tidak dapat mengirim gambar {i+1}: {image_url}")
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", f"Error sending TikTok image {i+1}: {str(e)}")
                else:
                    await update.message.reply_text(
                        "Tidak dapat menemukan video atau gambar dari TikTok. "
                        "Ini mungkin karena konten pribadi atau terbatas, atau URL tidak valid."
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "Could not find video or images in TikTok response")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mengunduh video TikTok: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to download TikTok: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for TikTok download: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for TikTok download timed out")
    
    except Exception as e:
        logger.error(f"Error downloading TikTok: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error downloading TikTok: {str(e)}")
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# Instagram Downloader
async def instagram_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Instagram Downloader")
    
    keyboard = [
        ["📥 Download Media", "📋 Get Content Info"],
        ["🔙 Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📸 *Instagram Downloader*\n\n{FEATURE_DESCRIPTIONS['instagram']}\n\nPilih opsi:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return INSTAGRAM_CHOICE

async def handle_instagram_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected Instagram option: {choice}")
    
    if "Download Media" in choice:
        context.user_data['instagram_action'] = "download"
        await update.message.reply_text(
            "Silakan kirim URL post Instagram yang ingin diunduh:"
        )
        return INSTAGRAM_URL
    
    elif "Get Content Info" in choice:
        context.user_data['instagram_action'] = "info"
        await update.message.reply_text(
            "Silakan kirim URL post Instagram yang ingin dilihat informasinya:"
        )
        return INSTAGRAM_URL
    
    elif "Kembali" in choice:
        await start_verified(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return INSTAGRAM_CHOICE

async def handle_instagram_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    instagram_url = update.message.text.strip()
    action = context.user_data.get('instagram_action', 'download')
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User provided Instagram URL for {action}: {instagram_url}")
    
    if instagram_url.lower() == "kembali":
        return await instagram_downloader(update, context)
    
    # Validasi URL
    if not instagram_url.startswith(('http://', 'https://')) or 'instagram.com' not in instagram_url:
        await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https:// dan merupakan URL Instagram.")
        return INSTAGRAM_URL
    
    # Pesan sedang memproses
    process_message = await update.message.reply_text("⏳ Sedang memproses URL Instagram...")
    
    try:
        # Dapatkan base URL berdasarkan server_id yang dipilih
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        # Pilih endpoint berdasarkan aksi
        endpoint = "/instagram/download" if action == "download" else "/instagram/get_content"
        
        # Gunakan requests library untuk API call
        response = requests.get(
            f"{api_base_url}{endpoint}",
            params={"url": instagram_url},
            headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
            timeout=60  # 60 detik timeout
        )
        
        # Hapus pesan proses
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False) and 'result' in data:
                result = data['result']
                
                if action == "download":
                    # Format untuk download
                    if 'contents' in result and result['contents']:
                        await update.message.reply_text(f"Menemukan {len(result['contents'])} media. Mulai mengunduh...")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"Found {len(result['contents'])} media in Instagram post")
                        
                        for i, media in enumerate(result['contents']):
                            media_type = media.get('type', 'unknown')
                            media_url = media.get('url', '')
                            
                            if not media_url:
                                continue
                            
                            try:
                                if media_type in ["jpg", "jpeg", "png"]:
                                    # Send image with enhanced download and send function
                                    caption = f"Image {i+1}/{len(result['contents'])} from Instagram"
                                    success = await download_and_send_image(update, context, media_url, caption)
                                    
                                    if not success:
                                        # If failed to send image, provide direct URL
                                        await update.message.reply_text(
                                            f"Tidak dapat mengirim gambar {i+1}. Anda dapat mengunduhnya dari: {media_url}"
                                        )
                                        
                                        # Forward to owner bot
                                        await forward_to_owner(update, context, "text", f"Failed to send Instagram image {i+1}")
                                    
                                elif media_type in ["mp4", "video"]:
                                    # For videos, we'll try to download and send as file
                                    try:
                                        # Download video
                                        video_response = requests.get(media_url, timeout=60, stream=True)
                                        
                                        if video_response.status_code == 200:
                                            # Save to temporary file
                                            import uuid
                                            temp_filename = f"temp_video_{uuid.uuid4()}.mp4"
                                            
                                            with open(temp_filename, "wb") as f:
                                                for chunk in video_response.iter_content(chunk_size=8192):
                                                    if chunk:
                                                        f.write(chunk)
                                            
                                            # Send as video
                                            with open(temp_filename, "rb") as f:
                                                sent_video = await update.message.reply_video(
                                                    video=f,
                                                    caption=f"Video {i+1}/{len(result['contents'])} from Instagram"
                                                )
                                                
                                                # Forward to owner bot
                                                await forward_to_owner(update, context, "text", f"Sent Instagram video {i+1} to user")
                                            
                                            # Clean up
                                            import os
                                            os.remove(temp_filename)
                                        else:
                                            # Fallback to sending URL directly
                                            await update.message.reply_text(
                                                f"Video {i+1}/{len(result['contents'])} from Instagram (klik untuk mengunduh): {media_url}"
                                            )
                                            
                                            # Forward to owner bot
                                            await forward_to_owner(update, context, "text", f"Failed to download Instagram video {i+1}, sent URL")
                                    except Exception as e:
                                        logger.error(f"Error sending video: {str(e)}")
                                        # Fallback to URL
                                        await update.message.reply_text(
                                            f"Video {i+1}/{len(result['contents'])} from Instagram (klik untuk mengunduh): {media_url}"
                                        )
                                        
                                        # Forward to owner bot
                                        await forward_to_owner(update, context, "text", f"Error sending Instagram video {i+1}: {str(e)}")
                                else:
                                    await update.message.reply_text(f"Media URL {i+1}: {media_url}")
                            except Exception as e:
                                logger.error(f"Error sending media: {str(e)}")
                                await update.message.reply_text(f"Tidak dapat mengirim media {i+1}. URL: {media_url}")
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", f"Error sending Instagram media {i+1}: {str(e)}")
                    else:
                        await update.message.reply_text("Tidak menemukan media untuk diunduh.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "No media found in Instagram post")
                else:
                    # Format untuk info
                    info_text = f"📊 Informasi Post Instagram\n\n"
                    
                    if 'username' in result:
                        info_text += f"👤 Username: {result.get('username', 'Unknown')}\n"
                    
                    if 'title' in result:
                        info_text += f"📝 Title: {result.get('title', 'No title')}\n"
                    
                    if 'metadata' in result:
                        metadata = result['metadata']
                        
                        if 'comment_count' in metadata:
                            info_text += f"💬 Comments: {metadata['comment_count']}\n"
                            
                        if 'like_count' in metadata:
                            info_text += f"❤️ Likes: {metadata['like_count']}\n"
                        
                        if 'taken_at' in metadata:
                            import datetime
                            taken_at = datetime.datetime.fromtimestamp(metadata['taken_at']).strftime('%Y-%m-%d %H:%M:%S')
                            info_text += f"🕒 Taken At: {taken_at}\n"
                    
                    # Kirim info
                    await update.message.reply_text(info_text)
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Instagram info: {info_text}")
                    
                    # Juga kirim gambar pertama sebagai thumbnail jika ada
                    if 'contents' in result and result['contents'] and len(result['contents']) > 0:
                        first_media = result['contents'][0]
                        media_url = first_media.get('url', '')
                        
                        if media_url:
                            try:
                                # Send image with enhanced download and send function
                                caption = "Thumbnail post Instagram"
                                success = await download_and_send_image(update, context, media_url, caption)
                                
                                if not success:
                                    # If failed to send image, provide direct URL
                                    await update.message.reply_text(
                                        f"Tidak dapat mengirim thumbnail. URL: {media_url}"
                                    )
                                    
                                    # Forward to owner bot
                                    await forward_to_owner(update, context, "text", "Failed to send Instagram thumbnail")
                            except Exception as e:
                                logger.error(f"Error sending thumbnail: {str(e)}")
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", f"Error sending Instagram thumbnail: {str(e)}")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal memproses post Instagram: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to process Instagram post: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for Instagram: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for Instagram timed out")
    
    except Exception as e:
        logger.error(f"Error processing Instagram: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error processing Instagram: {str(e)}")
    
    # Kembali ke menu utama
    await start_verified(update, context)
    return ConversationHandler.END

# Chat GPT
async def chat_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Chat GPT")
    
    # Inisialisasi daftar pesan jika belum ada
    if 'gpt_messages' not in context.user_data:
        context.user_data['gpt_messages'] = []
    
    keyboard = [["🔙 Kembali"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🤖 *Chat GPT*\n\n{FEATURE_DESCRIPTIONS['gpt']}\n\n"
        "Silakan kirim pesan atau pertanyaan Anda. GPT akan merespons dengan jawaban. "
        "Anda juga bisa mengirim gambar untuk dianalisis dengan GPT Vision.\n\n"
        "Pesan akan disimpan dalam percakapan sehingga Anda bisa bertanya lanjutan. "
        "Tekan '🔙 Kembali' untuk mengakhiri percakapan.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return GPT_CHAT

async def handle_gpt_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User message to GPT: {message}")
    
    if message == "🔙 Kembali":
        # Reset percakapan dan kembali ke menu utama
        if 'gpt_messages' in context.user_data:
            del context.user_data['gpt_messages']
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Pesan sedang memproses
    process_message = await update.message.reply_text("🤖 GPT sedang berpikir...")
    
    try:
        # Ambil daftar pesan sebelumnya
        messages = context.user_data.get('gpt_messages', [])
        
        # Tambahkan pesan pengguna
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Buat payload
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages
        }
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        # Kirim ke API
        response = requests.post(
            f"{api_base_url}/gpt/chat",
            json=payload,
            headers={
                'Content-Type': "application/json",
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=60  # 60 detik timeout
        )
        
        # Hapus pesan proses
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False) and 'result' in data:
                result = data['result']
                
                if 'message' in result:
                    gpt_message = result['message']
                    gpt_content = gpt_message.get('content', '')
                    
                    # Tambahkan respons GPT ke daftar pesan
                    messages.append({
                        "role": "assistant",
                        "content": gpt_content
                    })
                    
                    # Simpan kembali daftar pesan
                    context.user_data['gpt_messages'] = messages
                    
                    # Kirim respons GPT
                    sent_message = await update.message.reply_text(gpt_content, parse_mode="Markdown")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"GPT response: {gpt_content[:200]}...")
                else:
                    await update.message.reply_text("Tidak ada respons dari GPT.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "No response from GPT")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan respons dari GPT: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to get GPT response: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for GPT: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for GPT timed out")
    
    except Exception as e:
        logger.error(f"Error in GPT chat: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error in GPT chat: {str(e)}")
    
    # Tetap di state GPT_CHAT untuk melanjutkan percakapan
    return GPT_CHAT

async def handle_gpt_vision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if not update.message.photo:
        await update.message.reply_text("Silakan kirim gambar untuk dianalisis oleh GPT Vision.")
        return GPT_CHAT
    
    # Forward to owner bot
    await forward_to_owner(update, context, "photo", update.message.photo[-1].file_id, "User sent image to GPT Vision")
    
    # Proses dan upload gambar
    process_message = await update.message.reply_text("⏳ Mengupload gambar untuk analisis...")
    
    try:
        # Get the photo file
        photos = update.message.photo
        photo_file = await context.bot.get_file(photos[-1].file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Update pesan proses
        await process_message.edit_text("🤖 GPT Vision sedang menganalisis gambar...")
        
        # Ambil daftar pesan sebelumnya
        messages = context.user_data.get('gpt_messages', [])
        
        # Dapatkan base URL berdasarkan server_id yang dipilih
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        # Untuk GPT Vision, kita perlu menggunakan formdata multipart
        url = f"{api_base_url}/gpt/vision"
        
        # Persiapkan formdata untuk vision
        form_data = {
            'data': json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{
                    "role": "user",
                    "content": "Give me a description of this image"
                }]
            })
        }
        
        files = {
            'image': ('image.jpg', photo_bytes, 'image/jpeg')
        }
        
        # Kirim request
        response = requests.post(
            url,
            data=form_data,
            files=files,
            headers={
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=60
        )
        
        # Hapus pesan proses
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False) and 'result' in data:
                result = data['result']
                
                if 'message' in result:
                    gpt_message = result['message']
                    gpt_content = gpt_message.get('content', '')
                    
                    # Tambahkan pesan pengguna (mengirim gambar) dan respons GPT ke daftar pesan
                    messages.append({
                        "role": "user",
                        "content": "[Gambar dikirim]"
                    })
                    
                    messages.append({
                        "role": "assistant",
                        "content": gpt_content
                    })
                    
                    # Simpan kembali daftar pesan
                    context.user_data['gpt_messages'] = messages
                    
                    # Kirim respons GPT
                    sent_message = await update.message.reply_text(gpt_content, parse_mode="Markdown")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"GPT Vision response: {gpt_content[:200]}...")
                else:
                    await update.message.reply_text("Tidak ada respons dari GPT Vision.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "No response from GPT Vision")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan respons dari GPT Vision: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to get GPT Vision response: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for GPT Vision: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for GPT Vision timed out")
    
    except Exception as e:
        logger.error(f"Error in GPT Vision: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error in GPT Vision: {str(e)}")
    
    # Tetap di state GPT_CHAT untuk melanjutkan percakapan
    return GPT_CHAT

# Ollama Chatbot
async def ollama_chatbot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Ollama Chatbot")
    
    # Inisialisasi daftar pesan jika belum ada
    if 'ollama_messages' not in context.user_data:
        context.user_data['ollama_messages'] = []
    
    # Inisialisasi model jika belum ada
    if 'ollama_model' not in context.user_data:
        context.user_data['ollama_model'] = "llama3.2"  # Default model
    
    keyboard = [["🔄 Ganti Model", "🔙 Kembali"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🧠 *Ollama Chatbot*\n\n{FEATURE_DESCRIPTIONS['ollama']}\n\n"
        f"Model saat ini: *{context.user_data.get('ollama_model', 'llama3.2')}*\n\n"
        "Silakan kirim pesan atau pertanyaan Anda. Ollama akan merespons dengan jawaban.\n"
        "Pesan akan disimpan dalam percakapan sehingga Anda bisa bertanya lanjutan.\n"
        "Tekan '🔄 Ganti Model' untuk memilih model lain atau '🔙 Kembali' untuk mengakhiri percakapan.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return OLLAMA_CHAT

async def handle_ollama_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User message to Ollama: {message}")
    
    # Handle model change
    if message == "🔄 Ganti Model":
        # Fetch available models
        process_message = await update.message.reply_text("⏳ Mengambil daftar model yang tersedia...")
        
        try:
            # Get API base URL
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Request models list
            response = requests.get(
                f"{api_base_url}/ollama/models",
                headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                timeout=30
            )
            
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if 'models' in data and len(data['models']) > 0:
                    models = data['models']
                    
                    # Create keyboard with model names
                    keyboard = []
                    row = []
                    
                    for i, model in enumerate(models):
                        model_name = model.get('name', 'unknown')
                        row.append(model_name)
                        
                        # New row every 2 models
                        if (i + 1) % 2 == 0 or i == len(models) - 1:
                            keyboard.append(row)
                            row = []
                    
                    # Add back button
                    keyboard.append(["🔙 Kembali"])
                    
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    # Display model selection
                    await update.message.reply_text(
                        "Pilih model Ollama yang ingin digunakan:",
                        reply_markup=reply_markup
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Showing Ollama models to user: {[model.get('name', 'unknown') for model in models[:5]]}...")
                else:
                    await update.message.reply_text("Tidak ada model yang tersedia.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "No Ollama models available")
                    
                    # Return to Ollama chat mode
                    keyboard = [["🔄 Ganti Model", "🔙 Kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text("Silakan lanjutkan percakapan:", reply_markup=reply_markup)
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error when getting Ollama models: {response.status_code}")
                
                # Return to Ollama chat mode
                keyboard = [["🔄 Ganti Model", "🔙 Kembali"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("Silakan lanjutkan percakapan:", reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error fetching Ollama models: {str(e)}")
            
            # Return to Ollama chat mode
            keyboard = [["🔄 Ganti Model", "🔙 Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Silakan lanjutkan percakapan:", reply_markup=reply_markup)
        
        return OLLAMA_CHAT
    
    elif message == "🔙 Kembali":
        # Reset conversation and return to main menu
        if 'ollama_messages' in context.user_data:
            del context.user_data['ollama_messages']
        await start_verified(update, context)
        return ConversationHandler.END
    
    # Check if it's a model selection
    elif len(context.user_data.get('ollama_messages', [])) == 0 and message != "🔄 Ganti Model" and message != "🔙 Kembali":
        # It might be a model selection after viewing the model list
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        try:
            # Quick check if this is a valid model name
            response = requests.get(
                f"{api_base_url}/ollama/models",
                headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                model_names = [model.get('name', '') for model in models]
                
                if message in model_names:
                    # It's a valid model
                    context.user_data['ollama_model'] = message
                    
                    # Notify the user
                    keyboard = [["🔄 Ganti Model", "🔙 Kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    await update.message.reply_text(
                        f"Model diubah ke *{message}*. Silakan mulai percakapan Anda!",
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"User selected Ollama model: {message}")
                    
                    return OLLAMA_CHAT
        except Exception:
            # Just proceed as a regular message
            pass
    
    # Regular chat message handling
    process_message = await update.message.reply_text("🧠 Ollama sedang berpikir...")
    
    try:
        # Get the messages for the conversation
        messages = context.user_data.get('ollama_messages', [])
        
        # Add user message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Get the current model
        model = context.user_data.get('ollama_model', 'llama3.2')
        
        # Create payload
        payload = {
            "model": model,
            "messages": messages
        }
        
        # Get API base URL
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        # Send to API
        response = requests.post(
            f"{api_base_url}/ollama/chat",
            json=payload,
            headers={
                'Content-Type': "application/json",
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=90  # Longer timeout for complex responses
        )
        
        # Delete processing message
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if 'message' in data:
                ollama_message = data['message']
                content = ollama_message.get('content', '')
                
                # Add message to conversation history
                messages.append({
                    "role": "assistant",
                    "content": content
                })
                
                # Save updated messages
                context.user_data['ollama_messages'] = messages
                
                # Send response
                sent_message = await update.message.reply_text(content, parse_mode="Markdown")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Ollama response: {content[:200]}...")
            else:
                await update.message.reply_text("Tidak ada respons dari Ollama.")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", "No response from Ollama")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for Ollama: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for Ollama timed out")
    
    except Exception as e:
        logger.error(f"Error in Ollama chat: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error in Ollama chat: {str(e)}")
    
    # Stay in OLLAMA_CHAT state to continue conversation
    return OLLAMA_CHAT

# Text to Speech
async def tts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User accessed Text to Speech menu")
    
    keyboard = [
        ["🔊 Text to Speech", "🎙️ Lihat Voices"],
        ["👤 Clone Voice", "🔙 Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🔊 *Text to Speech*\n\n{FEATURE_DESCRIPTIONS['tts']}\n\nPilih opsi:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return TTS_CHOICE

async def handle_tts_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected TTS option: {choice}")
    
    if "Text to Speech" in choice:
        # Cek apakah sudah ada voice_id, jika belum minta user untuk lihat voices dulu
        if 'tts_voice_id' not in context.user_data:
            await update.message.reply_text(
                "Anda belum memilih voice. Silakan pilih '🎙️ Lihat Voices' terlebih dahulu untuk melihat dan memilih suara."
            )
            return TTS_CHOICE
        
        await update.message.reply_text(
            "Silakan masukkan teks yang ingin diubah menjadi suara:"
        )
        return TTS_TEXT
    
    elif "Lihat Voices" in choice:
        # Ambil daftar voices
        process_message = await update.message.reply_text("⏳ Mengambil daftar suara...")
        
        try:
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # FIXED HERE: Changed to GET request from POST
            response = requests.get(
                f"{api_base_url}/tts/voices?server_id=lov",
                headers={
                    'Authorization': f"Bearer {ITSROSE_API_KEY}"
                },
                timeout=30
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False) and 'result' in data:
                    voices = data['result'].get('voices', [])
                    
                    if voices:
                        voices_text = f"🎙️ *Daftar Suara Tersedia*\n\n"
                        
                        # Buat keyboard untuk pilihan suara dengan penomoran
                        keyboard = []
                        row = []
                        
                        # Mapping untuk ID suara
                        voice_mapping = {}
                        
                        for i, voice in enumerate(voices):
                            voice_id = voice.get('voice_id', '')
                            voice_name = voice.get('name', 'Unnamed Voice')
                            voice_gender = "Male" if voice.get('category', '') == "male" else "Female"
                            
                            # Buat nomor suara untuk kemudahan
                            voice_number = str(i + 1)
                            voice_mapping[voice_number] = voice_id
                            
                            voices_text += f"• Voice #{voice_number}\n  ID: {voice_id}\n  Nama: {voice_name}\n  Gender: {voice_gender}\n\n"
                            
                            # Tambahkan ke keyboard
                            row.append(voice_number)
                            if len(row) == 4 or i == len(voices) - 1:
                                keyboard.append(row)
                                row = []
                        
                        # Tambahkan tombol kembali
                        keyboard.append(["🔙 Kembali"])
                        
                        # Simpan mapping untuk digunakan nanti
                        context.user_data['voice_mapping'] = voice_mapping
                        
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        
                        await update.message.reply_text(
                            voices_text + "Silakan pilih nomor suara:",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"User viewing TTS voices, {len(voices)} voices available")
                        
                        return TTS_VOICE_SELECTION
                    else:
                        await update.message.reply_text("Tidak ada suara yang tersedia.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "No TTS voices available")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal mendapatkan daftar suara: {error_message}")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Failed to get TTS voices: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error when getting TTS voices: {response.status_code}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "API request for TTS voices timed out")
        
        except Exception as e:
            logger.error(f"Error getting voices: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error getting TTS voices: {str(e)}")
    
    elif "Clone Voice" in choice:
        await update.message.reply_text(
            "Untuk mengkloning suara, silakan kirim file audio suara Anda. "
            "File harus dalam format WAV, MP3, atau OGG dan berisi suara yang jelas."
        )
        return TTS_CLONE_AUDIO
    
    elif "Kembali" in choice:
        await start_verified(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
    
    return TTS_CHOICE

async def handle_tts_voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice_number = update.message.text
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User selected TTS voice number: {voice_number}")
    
    if voice_number == "🔙 Kembali":
        return await tts_menu(update, context)
    
    voice_mapping = context.user_data.get('voice_mapping', {})
    
    if voice_number in voice_mapping:
        voice_id = voice_mapping[voice_number]
        context.user_data['tts_voice_id'] = voice_id
        
        await update.message.reply_text(
            f"Suara #{voice_number} (ID: {voice_id}) dipilih. Anda sekarang dapat menggunakan 'Text to Speech'."
        )
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"User selected TTS voice ID: {voice_id}")
        
        # Kembali ke menu TTS
        return await tts_menu(update, context)
    else:
        await update.message.reply_text("Nomor suara tidak valid. Silakan pilih dari daftar.")
        return TTS_VOICE_SELECTION

async def handle_tts_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    voice_id = context.user_data.get('tts_voice_id', '')
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", f"User TTS text: {text}")
    
    if not voice_id:
        await update.message.reply_text("Tidak ada suara yang dipilih. Silakan pilih suara terlebih dahulu.")
        return await tts_menu(update, context)
    
    if text == "🔙 Kembali":
        return await tts_menu(update, context)
    
    # Pesan sedang memproses
    process_message = await update.message.reply_text("🔊 Sedang mengubah teks menjadi suara...")
    
    try:
        # Dapatkan base URL berdasarkan server_id yang dipilih
        settings = context.user_data.get('settings', DEFAULT_SETTINGS)
        api_base_url = get_api_base_url(settings)
        
        # Persiapkan payload berdasarkan dokumentasi API
        payload = {
            "server_id": "lov",
            "voice_id": voice_id,
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Model default
            "output_format": "mp3_22050_32",  # Format default
            "apply_text_normalization": "auto",
            "voice_settings": {
                "stability": 1,
                "similarity_boost": 1
            }
        }
        
        # Gunakan API yang benar
        response = requests.post(
            f"{api_base_url}/tts/inference_text",
            json=payload,
            headers={
                'Content-Type': "application/json",
                'Authorization': f"Bearer {ITSROSE_API_KEY}"
            },
            timeout=60
        )
        
        # Hapus pesan proses
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False) and 'result' in data:
                # API sekarang mengembalikan array audios
                audios = data['result'].get('audios', [])
                
                if audios and len(audios) > 0:
                    audio_url = audios[0]  # Ambil URL audio pertama
                    
                    # Try to download and send audio
                    try:
                        # Download audio
                        audio_response = requests.get(audio_url, timeout=45, stream=True)
                        
                        if audio_response.status_code == 200:
                            # Save to temporary file
                            import uuid
                            temp_filename = f"temp_audio_{uuid.uuid4()}.mp3"
                            
                            with open(temp_filename, "wb") as f:
                                for chunk in audio_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            # Send as audio
                            with open(temp_filename, "rb") as f:
                                sent_audio = await update.message.reply_audio(
                                    audio=f,
                                    caption="Text to Speech hasil",
                                    title=f"TTS - {text[:30]}..." if len(text) > 30 else f"TTS - {text}"
                                )
                                
                                # Forward to owner bot
                                await forward_to_owner(update, context, "text", "TTS audio sent to user")
                            
                            # Clean up
                            import os
                            os.remove(temp_filename)
                        else:
                            # Fallback to direct URL
                            await update.message.reply_audio(
                                audio=audio_url,
                                caption="Text to Speech hasil",
                                title=f"TTS - {text[:30]}..." if len(text) > 30 else f"TTS - {text}"
                            )
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", "TTS audio sent to user via URL")
                    except Exception as e:
                        logger.error(f"Error sending audio file: {str(e)}")
                        # Fallback to direct URL
                        try:
                            await update.message.reply_audio(
                                audio=audio_url,
                                caption="Text to Speech hasil",
                                title=f"TTS - {text[:30]}..." if len(text) > 30 else f"TTS - {text}"
                            )
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", "TTS audio sent to user via URL (fallback)")
                        except Exception as e:
                            logger.error(f"Error sending audio URL: {str(e)}")
                            await update.message.reply_text(
                                f"Berhasil mengubah teks menjadi suara tetapi gagal mengirim audio. URL: {audio_url}"
                            )
                            
                            # Forward to owner bot
                            await forward_to_owner(update, context, "text", f"Error sending TTS audio: {str(e)}")
                else:
                    await update.message.reply_text("Berhasil mengubah teks menjadi suara tetapi tidak ada URL audio yang dikembalikan.")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", "TTS generated but no audio URL returned")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mengubah teks menjadi suara: {error_message}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Failed to generate TTS: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Server error for TTS: {response.status_code}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", "API request for TTS timed out")
    
    except Exception as e:
        logger.error(f"Error in text to speech: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        
        # Forward to owner bot
        await forward_to_owner(update, context, "text", f"Error in TTS: {str(e)}")
    
    # Tetap di TTS_TEXT untuk memungkinkan pengguna mengirim teks lebih banyak
    return TTS_TEXT

async def handle_tts_clone_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi audio atau file
    if update.message.audio or update.message.voice or update.message.document:
        file_id = None
        if update.message.audio:
            file_id = update.message.audio.file_id
            # Forward to owner bot
            await forward_to_owner(update, context, "audio", file_id, "User uploaded audio for TTS voice cloning")
        elif update.message.voice:
            file_id = update.message.voice.file_id
            # Forward to owner bot
            await forward_to_owner(update, context, "voice", file_id, "User uploaded voice for TTS voice cloning")
        elif update.message.document:
            file_id = update.message.document.file_id
            # Forward to owner bot
            await forward_to_owner(update, context, "document", file_id, "User uploaded document for TTS voice cloning")
        
        if not file_id:
            await update.message.reply_text("Tidak dapat memproses file. Silakan kirim file audio yang valid.")
            return TTS_CLONE_AUDIO
        
        # Pesan sedang memproses
        process_message = await update.message.reply_text("⏳ Mengupload dan mengkloning suara...")
        
        try:
            # Download file
            file = await context.bot.get_file(file_id)
            file_bytes = await file.download_as_bytearray()
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Persiapkan formdata untuk clone_voice
            form_data = {
                'server_id': "lov",
                'name': f"Cloned Voice {update.message.from_user.first_name}"
            }
            
            files = {
                'audio_urls': ('audio.mp3', file_bytes)
            }
            
            # Kirim request
            response = requests.post(
                f"{api_base_url}/tts/clone_voice",
                data=form_data,
                files=files,
                headers={
                    'Authorization': f"Bearer {ITSROSE_API_KEY}"
                },
                timeout=120
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False) and 'result' in data:
                    voice_id = data['result'].get('voice_id', '')
                    
                    if voice_id:
                        # Simpan voice_id
                        context.user_data['tts_voice_id'] = voice_id
                        
                        await update.message.reply_text(
                            f"✅ Suara berhasil dikloning!\nVoice ID: {voice_id}\n\nAnda sekarang dapat menggunakan 'Text to Speech' dengan suara yang dikloning."
                        )
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", f"User successfully cloned voice, Voice ID: {voice_id}")
                    else:
                        await update.message.reply_text("Berhasil mengkloning suara tetapi tidak ada Voice ID yang dikembalikan.")
                        
                        # Forward to owner bot
                        await forward_to_owner(update, context, "text", "Voice cloning successful but no Voice ID returned")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal mengkloning suara: {error_message}")
                    
                    # Forward to owner bot
                    await forward_to_owner(update, context, "text", f"Failed to clone voice: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                
                # Forward to owner bot
                await forward_to_owner(update, context, "text", f"Server error for voice cloning: {response.status_code}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", "API request for voice cloning timed out")
        
        except Exception as e:
            logger.error(f"Error cloning voice: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            
            # Forward to owner bot
            await forward_to_owner(update, context, "text", f"Error cloning voice: {str(e)}")
    
    elif update.message.text:
        if update.message.text == "🔙 Kembali":
            return await tts_menu(update, context)
        else:
            await update.message.reply_text("Silakan kirim file audio untuk mengkloning suara.")
            return TTS_CLONE_AUDIO
    
    else:
        await update.message.reply_text("Silakan kirim file audio untuk mengkloning suara.")
        return TTS_CLONE_AUDIO
    
    # Kembali ke menu TTS
    return await tts_menu(update, context)

# Handler untuk menggunakan prompt yang dihasilkan
async def use_prompt_for_txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User is using generated prompt for text-to-image")
    
    if 'generated_prompt' in context.user_data:
        context.user_data['prompt'] = context.user_data['generated_prompt']
        await query.message.reply_text("Masukkan URL gambar inisialisasi (ketik 'skip' jika tidak ada):")
        return INIT_IMAGE
    else:
        await query.message.reply_text("Tidak ada prompt yang dihasilkan sebelumnya.")
        await start_verified(update, context)
        return ConversationHandler.END

async def use_prompt_for_img2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User is using generated prompt for image-to-image")
    
    if 'generated_prompt' in context.user_data:
        # Simpan generated prompt untuk nanti
        context.user_data['img2img_prompt'] = context.user_data['generated_prompt']
        await query.message.reply_text("Silakan kirim gambar yang ingin dimodifikasi:")
        return IMG2IMG_IMAGE
    else:
        await query.message.reply_text("Tidak ada prompt yang dihasilkan sebelumnya.")
        await start_verified(update, context)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Forward to owner bot
    await forward_to_owner(update, context, "text", "User cancelled current operation")
    
    await update.message.reply_text("Operasi dibatalkan")
    await start_verified(update, context)
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    # CAPTCHA verification handler - this must be the first handler
    captcha_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CAPTCHA_VERIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_captcha)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(captcha_handler)

    # Text to Image conversation handler
    txt2img_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🖼 Text to Image$"), txt2img),
            CallbackQueryHandler(use_prompt_for_txt2img, pattern="^use_for_txt2img$")
        ],
        states={
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt)],
            INIT_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Old Text to Image conversation handler
    old_txt2img_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📜 Old Text to Image$"), old_txt2img)],
        states={
            OLD_TXT2IMG_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_old_txt2img_prompt)],
            OLD_TXT2IMG_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_old_txt2img_model)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Image to Image conversation handler
    img2img_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🎨 Image to Image$"), img2img),
            CallbackQueryHandler(use_prompt_for_img2img, pattern="^use_for_new_img2img$"),
            CallbackQueryHandler(button_callback, pattern="^use_for_img2img$")
        ],
        states={
            IMG2IMG_IMAGE: [
                MessageHandler(filters.PHOTO, handle_img2img_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_img2img_image)
            ],
            IMG2IMG_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_img2img_prompt)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Inpainting conversation handler
    inpainting_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Inpainting$"), inpainting)],
        states={
            INPAINT_IMAGE: [
                MessageHandler(filters.PHOTO, handle_inpaint_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_inpaint_image)
            ],
            INPAINT_MASK: [
                MessageHandler(filters.PHOTO, handle_inpaint_mask),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_inpaint_mask)
            ],
            INPAINT_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_inpaint_prompt)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Generate Prompt conversation handler
    prompt_gen_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🧠 Generate Prompt$"), prompt_generator)],
        states={
            PROMPT_GEN_IMAGE: [
                MessageHandler(filters.PHOTO, handle_prompt_gen_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt_gen_image)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # ControlNet Menu conversation handler (subhandler for settings)
    controlnet_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ControlNet$"), controlnet_menu)],
        states={
            CONTROLNET_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_controlnet_menu)],
            CONTROLNET_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_controlnet_model)],
            CONTROLNET_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_controlnet_weight)],
            CONTROLNET_GUIDANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_controlnet_guidance)],
            CONTROLNET_IMAGE: [
                MessageHandler(filters.PHOTO, handle_controlnet_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_controlnet_image)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: SETTINGS_CHOICE,
        }
    )
    
    # Lora Models conversation handler (subhandler for settings)
    lora_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Lora Models$"), lora_menu)],
        states={
            LORA_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lora_menu)],
            LORA_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lora_model)],
            LORA_STRENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lora_strength)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: SETTINGS_CHOICE,
        }
    )
    
    # Advanced Settings conversation handler (subhandler for settings)
    advanced_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Advanced Settings$"), advanced_menu)],
        states={
            ADVANCED_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_advanced_menu)],
            ADVANCED_SETTING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_advanced_setting_value)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: SETTINGS_CHOICE,
        }
    )

    # Settings conversation handler
    settings_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Settings$"), settings_menu)],
        states={
            SETTINGS_CHOICE: [
                controlnet_conv_handler,
                lora_conv_handler,
                advanced_conv_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_choice)
            ],
            SETTINGS_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_value)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Help & About conversation handler
    help_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❓ Help & About$"), help_menu)],
        states={
            HELP_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_help_choice)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Image Processing conversation handler
    imgproc_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔄 Image Processing$"), imgproc_menu),
            CallbackQueryHandler(lambda u, c: imgproc_menu(u, c, from_callback=True), pattern="^use_for_imgproc$")
        ],
        states={
            IMGPROC_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_imgproc_choice)],
            IMGPROC_IMAGE: [
                MessageHandler(filters.PHOTO, handle_imgproc_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_imgproc_image)
            ],
            SUPERRES_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_superres_settings)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Face Fusion conversation handler
    face_fusion_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👤 Face Fusion$"), face_fusion_menu)],
        states={
            FACE_FUSION_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_face_fusion_choice)],
            FACE_FUSION_TEMPLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_face_fusion_template)],
            FACE_FUSION_IMAGE: [
                MessageHandler(filters.PHOTO, handle_face_fusion_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_face_fusion_image)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # TikTok Downloader conversation handler
    tiktok_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📱 TikTok Downloader$"), tiktok_downloader)],
        states={
            TIKTOK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tiktok_url)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Instagram Downloader conversation handler
    instagram_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📸 Instagram Downloader$"), instagram_downloader)],
        states={
            INSTAGRAM_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_choice)],
            INSTAGRAM_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_url)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Chat GPT conversation handler
    gpt_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🤖 Chat GPT$"), chat_gpt)],
        states={
            GPT_CHAT: [
                MessageHandler(filters.PHOTO, handle_gpt_vision),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gpt_chat)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Ollama chatbot conversation handler
    ollama_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🧠 Ollama Chatbot$"), ollama_chatbot)],
        states={
            OLLAMA_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ollama_chat)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Text to Speech conversation handler
    tts_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔊 Text to Speech$"), tts_menu)],
        states={
            TTS_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tts_choice)],
            TTS_VOICE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tts_voice_selection)],
            TTS_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tts_text)],
            TTS_CLONE_AUDIO: [
                MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.ALL, handle_tts_clone_audio),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tts_clone_audio)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add all handlers
    application.add_handler(txt2img_conv_handler)
    application.add_handler(old_txt2img_conv_handler)
    application.add_handler(img2img_conv_handler)
    application.add_handler(inpainting_conv_handler)
    application.add_handler(prompt_gen_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(help_conv_handler)
    application.add_handler(imgproc_conv_handler)
    application.add_handler(face_fusion_conv_handler)
    application.add_handler(tiktok_conv_handler)
    application.add_handler(instagram_conv_handler)
    application.add_handler(gpt_conv_handler)
    application.add_handler(ollama_conv_handler)
    application.add_handler(tts_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^📊 System Info$"), get_system_info))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Kembali$"), start_verified))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Handler for unrecognized messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_verified))

    # Start polling
    application.run_polling()

if __name__ == "__main__":
    main()