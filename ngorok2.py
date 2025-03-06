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
import io
import os
import urllib.parse
import requests
from PIL import Image

# Konfigurasi
ITSROSE_API_KEY = "Prod-Sk-35e0294f17662bfc0323399264bb85ab"  # Ganti dengan token API ItsRose Anda
BOT_TOKEN = "8010525002:AAHKAnTBuNmGM9sWK0IAS4rfe9M5G1JcLfs"
IMGBB_API_KEY = "ef9e1a9e1adfe2d6c8b0b576af3485e6"  # Ganti dengan API key ImgBB Anda (opsional)

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
    "cfg_scale": 7,        # Default CFG scale
    "negative_prompt": "",  # Default negative prompt
}

# Parameter settings descriptions
PARAMETER_DESCRIPTIONS = {
    "width": "Lebar gambar yang dihasilkan (64-1024 piksel). Nilai yang lebih tinggi menghasilkan gambar yang lebih detail tetapi membutuhkan lebih banyak waktu.",
    "height": "Tinggi gambar yang dihasilkan (64-1024 piksel). Nilai yang lebih tinggi menghasilkan gambar yang lebih detail tetapi membutuhkan lebih banyak waktu.",
    "samples": "Jumlah gambar yang dihasilkan (1-4). Lebih banyak sampel membutuhkan lebih banyak waktu pemrosesan.",
    "num_inference_steps": "Jumlah langkah penghitungan (10-50). Nilai yang lebih tinggi meningkatkan kualitas tetapi membutuhkan lebih banyak waktu.",
    "scheduler": "Algoritma yang mengontrol cara noise dikurangi selama proses generasi. Berbeda scheduler memberikan hasil visual yang berbeda.",
    "clip_skip": "Jumlah layer CLIP yang dilewati (1-12). Mempengaruhi bagaimana model menafsirkan prompt Anda.",
    "model_id": "Model AI yang digunakan untuk menghasilkan gambar. Setiap model memiliki gaya dan kekuatan yang berbeda.",
    "nsfw_filter": "Aktifkan/nonaktifkan filter konten dewasa. Jika diaktifkan, konten NSFW akan diberi tanda.",
    "server_id": "Server API yang digunakan untuk pemrosesan. Berbeda server mungkin memiliki kemampuan berbeda.",
    "cfg_scale": "Classifier Free Guidance scale (1-30). Nilai yang lebih tinggi membuat gambar lebih sesuai dengan prompt, tetapi kurang bervariasi.",
    "negative_prompt": "Prompt negatif untuk menentukan apa yang TIDAK ingin Anda munculkan dalam gambar.",
}

# Feature descriptions
FEATURE_DESCRIPTIONS = {
    "txt2img": "Text to Image memungkinkan Anda menghasilkan gambar dari deskripsi teks. Masukkan prompt detail untuk hasil terbaik.",
    "img2img": "Image to Image memungkinkan Anda mengubah gambar yang sudah ada dengan prompt baru. Upload gambar dan berikan deskripsi perubahan yang diinginkan.",
    "generate_prompt": "Generate Prompt akan menganalisis gambar Anda dan menghasilkan prompt deskriptif yang dapat digunakan untuk menghasilkan gambar serupa.",
    "system_info": "System Info menampilkan informasi tentang server, model yang tersedia, dan spesifikasi sistem.",
    "settings": "Settings memungkinkan Anda mengubah parameter generasi gambar untuk menyesuaikan hasil sesuai keinginan.",
    "imgproc": "Image Processing menyediakan berbagai alat untuk meningkatkan dan memproses gambar Anda, termasuk remove background, enhance, colorize dan banyak lagi.",
    "face_fusion": "Face Fusion memungkinkan Anda menggabungkan wajah Anda dengan template karakter yang tersedia untuk menciptakan gambar unik.",
    "tiktok": "TikTok Downloader memungkinkan Anda mengunduh video TikTok tanpa watermark. Cukup berikan URL video TikTok."
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
    "unblur": "Menajamkan gambar yang buram dan meningkatkan kualitas secara keseluruhan."
}

# Inisialisasi logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

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
        # Metode 1: Upload ke ImgBB (jika API key disediakan)
        if IMGBB_API_KEY != "YOUR_IMGBB_API_KEY":
            files = {"image": ("image.jpg", photo_bytes)}
            
            upload_url = "https://api.imgbb.com/1/upload"
            payload = {"key": IMGBB_API_KEY}
            
            response = requests.post(upload_url, files=files, params=payload)
            
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("success"):
                    return json_response["data"]["url"]
        
        # Metode 2: Gunakan base64 langsung
        image_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        return image_base64
        
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inisialisasi settings jika belum ada
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    keyboard = [
        ["🖼 Text to Image", "🎨 Image to Image"],
        ["🧠 Generate Prompt", "📊 System Info"],
        ["🔄 Image Processing", "👤 Face Fusion"],
        ["📱 TikTok Downloader", "⚙️ Settings"],
        ["❓ Help & About"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = (
        "Selamat datang di Ngorok, bot AI multifungsi untuk membuat gambar dan memproses media!\n\n"
        "🔹 Buat gambar dari teks\n"
        "🔹 Ubah gambar yang ada\n"
        "🔹 Tingkatkan kualitas foto\n"
        "🔹 Download video TikTok\n\n"
        "Pilih opsi di menu untuk memulai! Tekan ❓ Help & About untuk informasi lebih lanjut.\n\n"
        "Support:\n"
        "Telegram: @k4ies\n"
        "Facebook: Arif Maulana\n"
        "Instagram: @4rfmln"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Text to Image Flow
async def txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"📝 *Text to Image*\n\n{FEATURE_DESCRIPTIONS['txt2img']}\n\nMasukkan prompt untuk generasi gambar:",
        parse_mode="Markdown"
    )
    return PROMPT

async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['prompt'] = update.message.text
    await update.message.reply_text("Masukkan URL gambar inisialisasi (ketik 'skip' jika tidak ada):")
    return INIT_IMAGE

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    init_image = update.message.text
    prompt = context.user_data['prompt']
    settings = context.user_data.get('settings', DEFAULT_SETTINGS)
    
    # Pesan "sedang memproses" supaya user tahu botnya bekerja
    process_message = await update.message.reply_text("⏳ Sedang memproses gambar...")
    
    try:
        conn = http.client.HTTPSConnection("api.itsrose.rest")
        headers = {
            'Content-Type': "application/json",
            'Authorization': f"Bearer {ITSROSE_API_KEY}"
        }
        
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
            "cfg_scale": settings.get("cfg_scale", 7)
        }
        
        # Tambahkan init_image ke payload jika bukan 'skip'
        if init_image and init_image.lower() != 'skip':
            payload["init_image"] = init_image
            endpoint = "/sdapi/img2img"  # Gunakan endpoint yang benar untuk image-to-image
        else:
            endpoint = "/sdapi/txt2img"  # Endpoint untuk text-to-image
        
        # Kirim request ke API
        conn.request("POST", endpoint, json.dumps(payload), headers)
        res = conn.getresponse()
        data_bytes = res.read()
        
        # Pastikan respons tidak kosong
        if not data_bytes:
            await process_message.delete()
            await update.message.reply_text("Tidak ada respons dari server. Silakan coba lagi nanti.")
            await start(update, context)
            return ConversationHandler.END
        
        data = json.loads(data_bytes.decode("utf-8"))
        
        # Hapus pesan "sedang memproses"
        await process_message.delete()
        
        # Periksa status dan hasil
        if 'status' in data and data['status']:
            if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                image_url = data['result']['images'][0]
                
                # Cek NSFW hanya jika filter diaktifkan
                nsfw_warning = ""
                if settings.get("nsfw_filter", False) and data['result'].get('nsfw_content_detected', False):
                    nsfw_warning = "⚠️ NSFW Content Detected!"
                
                # Kirim gambar dengan caption yang berisi prompt
                caption = f"Hasil generasi:\n{prompt}\n{nsfw_warning}"
                
                # Tambahkan tombol untuk menggunakan gambar ini untuk img2img
                keyboard = [
                    [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")],
                    [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Simpan URL gambar untuk digunakan nanti
                context.user_data['last_image_url'] = image_url
                
                await update.message.reply_photo(
                    photo=image_url,
                    caption=caption,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("Gambar berhasil dibuat tetapi tidak ada URL yang dikembalikan.")
        else:
            error_message = data.get('message', 'Tidak ada detail error')
            await update.message.reply_text(f"Gagal menghasilkan gambar: {error_message}")
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error saat memproses respons dari server: {str(e)}. Silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Image to Image Flow
async def img2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"🎨 *Image to Image*\n\n{FEATURE_DESCRIPTIONS['img2img']}\n\nSilakan kirim gambar yang ingin dimodifikasi:",
        parse_mode="Markdown"
    )
    return IMG2IMG_IMAGE

async def handle_img2img_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
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
                return IMG2IMG_IMAGE
        
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar: {str(e)}")
            return IMG2IMG_IMAGE
        
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        # Validasi URL
        url = update.message.text.strip()
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
    
    # Pesan "sedang memproses"
    process_message = await update.message.reply_text("⏳ Sedang memproses gambar...")
    
    try:
        # Cek apakah gambar adalah base64 atau URL
        is_base64 = False
        if init_image and not init_image.startswith(('http://', 'https://')):
            # Ini adalah base64, perlu diformat dengan benar
            init_image = f"data:image/jpeg;base64,{init_image}"
            is_base64 = True
        
        # Gunakan requests untuk lebih andal
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
            "cfg_scale": settings.get("cfg_scale", 7)
        }
        
        response = requests.post(
            "https://api.itsrose.rest/sdapi/img2img",
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
                    
                    await update.message.reply_photo(
                        photo=image_url,
                        caption=f"Hasil modifikasi:\n{prompt}\n{nsfw_warning}",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text("Gambar berhasil dimodifikasi tetapi tidak ada URL yang dikembalikan.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal memodifikasi gambar: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error modifying image: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Callback handler untuk button
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "use_for_img2img":
        # Gunakan gambar terakhir untuk img2img
        if 'last_image_url' in context.user_data:
            context.user_data['img2img_image'] = context.user_data['last_image_url']
            await query.message.reply_text("Masukkan prompt untuk modifikasi gambar:")
            return IMG2IMG_PROMPT
        else:
            await query.message.reply_text("Tidak ada gambar sebelumnya. Silakan mulai dengan 'Image to Image' baru.")
            await start(update, context)
            return ConversationHandler.END
    
    elif query.data == "use_for_imgproc":
        # Gunakan gambar terakhir untuk image processing
        if 'last_image_url' in context.user_data:
            context.user_data['imgproc_image'] = context.user_data['last_image_url']
            return await imgproc_menu(update, context, from_callback=True)
        else:
            await query.message.reply_text("Tidak ada gambar sebelumnya. Silakan mulai dengan 'Image Processing' baru.")
            await start(update, context)
            return ConversationHandler.END
    
    return ConversationHandler.END

# Generate Prompt dengan gambar
async def prompt_generator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"🧠 *Generate Prompt*\n\n{FEATURE_DESCRIPTIONS['generate_prompt']}\n\nSilakan kirim gambar untuk dianalisis:",
        parse_mode="Markdown"
    )
    return PROMPT_GEN_IMAGE

async def handle_prompt_gen_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Proses gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("Gagal memproses gambar. Coba lagi atau gunakan URL gambar.")
                return PROMPT_GEN_IMAGE
            
            # Update pesan proses
            await process_message.edit_text("🧠 Menganalisis gambar dan menghasilkan prompt...")
            
            # Cek apakah ini adalah base64 atau URL
            if image_data.startswith(('http://', 'https://')):
                # Ini adalah URL
                image_url = image_data
            else:
                # Ini adalah base64, format dengan benar
                image_url = f"data:image/jpeg;base64,{image_data}"
            
            # Gunakan requests untuk menangani API
            response = requests.get(
                "https://api.itsrose.rest/sdapi/generate_prompt",
                params={"init_image": image_url},
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
                        
                        await update.message.reply_text(
                            f"✨ *Generated Prompt*:\n\n{prompt}",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                    else:
                        await update.message.reply_text("Gagal menghasilkan prompt. Respons tidak memiliki format yang diharapkan.")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal menghasilkan prompt: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
    
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        process_message = await update.message.reply_text("🧠 Menganalisis gambar dan menghasilkan prompt...")
        
        try:
            # Gunakan URL langsung
            image_url = update.message.text.strip()
            
            # Gunakan requests untuk menangani API
            response = requests.get(
                "https://api.itsrose.rest/sdapi/generate_prompt",
                params={"init_image": image_url},
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
                        
                        await update.message.reply_text(
                            f"✨ *Generated Prompt*:\n\n{prompt}",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                    else:
                        await update.message.reply_text("Gagal menghasilkan prompt. Respons tidak memiliki format yang diharapkan.")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal menghasilkan prompt: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return PROMPT_GEN_IMAGE
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Settings Flow
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Pastikan settings tersedia
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    settings = context.user_data['settings']
    
    # Kategori untuk pengaturan
    image_settings = ["width", "height", "samples", "num_inference_steps", "model_id", 
                      "scheduler", "clip_skip", "nsfw_filter", "server_id", "cfg_scale", "negative_prompt"]
    
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
            else:
                settings_text += f"• {key}: {settings[key]}\n"
    
    keyboard = [
        ["Width", "Height", "Samples"],
        ["Steps", "Model", "Scheduler"],
        ["Clip Skip", "NSFW Filter", "CFG Scale"],
        ["Negative Prompt", "Server ID", "Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup
    )
    return SETTINGS_CHOICE

async def handle_settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.lower()
    
    if choice == "kembali":
        await start(update, context)
        return ConversationHandler.END
    
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
        "server id": "server_id"
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
                server_id = context.user_data['settings'].get('server_id', 'rose')
                
                # Gunakan library requests untuk lebih andal
                response = requests.get(
                    f"https://api.itsrose.rest/sdapi/get_all_models?server_id={server_id}",
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
                    else:
                        # Fallback jika tidak bisa mendapatkan daftar model
                        keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            f"{description_text}Model saat ini: {current_value}\nPilih model baru (gagal mendapatkan daftar lengkap):",
                            reply_markup=reply_markup
                        )
                else:
                    # Fallback jika request gagal
                    keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        f"{description_text}Model saat ini: {current_value}\nPilih model baru (gagal mendapatkan daftar):",
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Error getting models: {str(e)}")
                keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f"{description_text}Model saat ini: {current_value}\nPilih model baru:",
                    reply_markup=reply_markup
                )
                
        elif setting_key == "scheduler":
            # Dapatkan daftar scheduler dari API
            try:
                server_id = context.user_data['settings'].get('server_id', 'rose')
                
                # Gunakan library requests untuk lebih andal
                response = requests.get(
                    f"https://api.itsrose.rest/sdapi/schedulers_list?server_id={server_id}",
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
                            f"{description_text}Scheduler saat ini: {current_value}\nPilih scheduler baru:",
                            reply_markup=reply_markup
                        )
                    else:
                        # Fallback jika tidak bisa mendapatkan daftar scheduler
                        keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            f"{description_text}Scheduler saat ini: {current_value}\nPilih scheduler baru (gagal mendapatkan daftar lengkap):",
                            reply_markup=reply_markup
                        )
                else:
                    # Fallback jika request gagal
                    keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        f"{description_text}Scheduler saat ini: {current_value}\nPilih scheduler baru (gagal mendapatkan daftar):",
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Error getting schedulers: {str(e)}")
                keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f"{description_text}Scheduler saat ini: {current_value}\nPilih scheduler baru:",
                    reply_markup=reply_markup
                )
                
        elif setting_key == "nsfw_filter":
            # Pilihan untuk aktifkan/nonaktifkan NSFW filter
            status = "Aktif" if current_value else "Nonaktif"
            keyboard = [["Aktif", "Nonaktif"], ["Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"{description_text}NSFW Filter saat ini: {status}\nPilih status baru:",
                reply_markup=reply_markup
            )
            
        elif setting_key == "server_id":
            keyboard = [["rose", "rose2"], ["Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"{description_text}Server ID saat ini: {current_value}\nPilih server ID baru:",
                reply_markup=reply_markup
            )
            
        elif setting_key == "negative_prompt":
            await update.message.reply_text(
                f"{description_text}Negative Prompt saat ini: {current_value or '(kosong)'}\n\n"
                f"Masukkan negative prompt baru (kirim 'kosong' untuk mengosongkan):"
            )
            
        else:
            await update.message.reply_text(
                f"{description_text}Nilai {setting_key} saat ini: {current_value}\nMasukkan nilai baru:"
            )
        
        return SETTINGS_VALUE
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih lagi.")
        return SETTINGS_CHOICE

async def handle_settings_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    current_setting = context.user_data.get('current_setting')
    
    if new_value.lower() == "kembali":
        return await settings_menu(update, context)
    
    # Validasi dan konversi nilai
    try:
        # Penanganan khusus untuk NSFW filter
        if current_setting == "nsfw_filter":
            if new_value.lower() == "aktif":
                context.user_data['settings'][current_setting] = True
                await update.message.reply_text("NSFW Filter diaktifkan.")
            elif new_value.lower() == "nonaktif":
                context.user_data['settings'][current_setting] = False
                await update.message.reply_text("NSFW Filter dinonaktifkan.")
            else:
                await update.message.reply_text("Nilai tidak valid. Pilih 'Aktif' atau 'Nonaktif'.")
                return SETTINGS_VALUE
        
        # Penanganan untuk negative prompt
        elif current_setting == "negative_prompt":
            if new_value.lower() == "kosong":
                context.user_data['settings'][current_setting] = ""
                await update.message.reply_text("Negative prompt dikosongkan.")
            else:
                context.user_data['settings'][current_setting] = new_value
                await update.message.reply_text(f"Negative prompt diubah menjadi: {new_value}")
        
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
            elif current_setting == "num_inference_steps" and (new_value < 10 or new_value > 50):
                await update.message.reply_text("Steps harus antara 10-50. Silakan coba lagi.")
                return SETTINGS_VALUE
            elif current_setting == "clip_skip" and (new_value < 1 or new_value > 12):
                await update.message.reply_text("Clip Skip harus antara 1-12. Silakan coba lagi.")
                return SETTINGS_VALUE
            elif current_setting == "cfg_scale" and (new_value < 1 or new_value > 30):
                await update.message.reply_text("CFG Scale harus antara 1-30. Silakan coba lagi.")
                return SETTINGS_VALUE
            
            # Update nilai
            context.user_data['settings'][current_setting] = new_value
            await update.message.reply_text(f"Berhasil mengubah {current_setting} menjadi {new_value}.")
        
        # Penanganan untuk setting string
        else:
            context.user_data['settings'][current_setting] = new_value
            await update.message.reply_text(f"Berhasil mengubah {current_setting} menjadi {new_value}.")
        
        # Kembali ke menu settings
        return await settings_menu(update, context)
    
    except ValueError:
        await update.message.reply_text("Nilai tidak valid. Silakan masukkan angka.")
        return SETTINGS_VALUE

# Get System Info
async def get_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Tampilkan deskripsi fitur
    await update.message.reply_text(
        f"📊 *System Info*\n\n{FEATURE_DESCRIPTIONS['system_info']}\n\nMengambil informasi...",
        parse_mode="Markdown"
    )
    
    # Tambahkan pesan loading
    loading_message = await update.message.reply_text("⏳ Mengambil informasi sistem...")
    
    try:
        server_id = context.user_data.get('settings', {}).get('server_id', 'rose')
        
        # Gunakan requests library untuk lebih andal
        response = requests.get(
            f"https://api.itsrose.rest/sdapi/system_details?server_id={server_id}",
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
                info_text = "🖥️ **System Info**\n\n"
                
                if 'gpu' in system_info:
                    info_text += f"🎮 **GPU**: {system_info['gpu']}\n"
                if 'available_models' in system_info:
                    info_text += f"🧠 **Models**: {', '.join(system_info['available_models'])}\n"
                if 'ram' in system_info:
                    info_text += f"💾 **RAM**: {system_info['ram']}\n"
                if 'cuda_version' in system_info:
                    info_text += f"⚙️ **CUDA**: {system_info['cuda_version']}\n"
                
                await update.message.reply_text(info_text, parse_mode="Markdown")
            else:
                await update.message.reply_text("Tidak dapat memperoleh informasi sistem dari respons.")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await loading_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        await loading_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)

# Help & About menu
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    
    if choice == "📖 Fitur-fitur":
        features_text = "📖 *Daftar Fitur*\n\n"
        
        for feature, description in FEATURE_DESCRIPTIONS.items():
            if feature == "txt2img":
                features_text += "🖼 *Text to Image*\n"
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
            elif feature == "face_fusion":
                features_text += "👤 *Face Fusion*\n"
            elif feature == "tiktok":
                features_text += "📱 *TikTok Downloader*\n"
            
            features_text += f"{description}\n\n"
            
        await update.message.reply_text(features_text, parse_mode="Markdown")
        return HELP_CHOICE
        
    elif choice == "ℹ️ About":
        about_text = (
            "ℹ️ *About Ngorok Bot*\n\n"
            "Ngorok adalah bot AI multifungsi yang menggabungkan kemampuan generasi gambar dan pemrosesan media menggunakan teknologi AI terkini.\n\n"
            "Dibuat dengan ❤️ oleh:\n"
            "Telegram: @k4ies\n"
            "Facebook: Arif Maulana\n"
            "Instagram: @4rfmln\n\n"
            "Ngorok menggunakan API ItsRose\n"
            "Versi bot: 2.0.0"
        )
        await update.message.reply_text(about_text, parse_mode="Markdown")
        return HELP_CHOICE
        
    elif choice == "📚 Tutorial":
        tutorial_text = (
            "📚 *Tutorial Menggunakan Ngorok Bot*\n\n"
            "*Text to Image*:\n"
            "1. Klik '🖼 Text to Image'\n"
            "2. Masukkan deskripsi gambar (prompt)\n"
            "3. Masukkan URL gambar inisialisasi atau ketik 'skip'\n\n"
            
            "*Image to Image*:\n"
            "1. Klik '🎨 Image to Image'\n"
            "2. Kirim gambar atau URL gambar\n"
            "3. Masukkan prompt untuk memodifikasi gambar\n\n"
            
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
            
            "*TikTok Downloader*:\n"
            "1. Klik '📱 TikTok Downloader'\n"
            "2. Kirim URL video TikTok\n"
            "3. Tunggu video diunduh\n\n"
            
            "*Settings*:\n"
            "1. Klik '⚙️ Settings'\n"
            "2. Pilih pengaturan yang ingin diubah\n"
            "3. Masukkan nilai baru\n\n"
            
            "Tips: Gunakan pengaturan yang sesuai untuk hasil terbaik. Model dan scheduler yang berbeda dapat menghasilkan gaya gambar yang berbeda."
        )
        await update.message.reply_text(tutorial_text, parse_mode="Markdown")
        return HELP_CHOICE
        
    elif choice == "🔙 Kembali":
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih lagi.")
        return HELP_CHOICE

# Image Processing Menu
async def imgproc_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False) -> int:
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
        await update.message.reply_text(
            f"🔍 *Super Resolution*\n\n{IMGPROC_DESCRIPTIONS['gfp_superres']}\n\n"
            "Silakan kirim gambar yang ingin ditingkatkan resolusinya.",
            parse_mode="Markdown"
        )
        # Untuk super resolution, kita ingin menanyakan outscale
        return SUPERRES_SETTINGS
    
    elif "Outpainting" in choice:
        context.user_data['imgproc_type'] = "outpainting"
        await update.message.reply_text(
            f"🌄 *Outpainting*\n\n{IMGPROC_DESCRIPTIONS['outpainting']}\n\n"
            "Silakan kirim gambar yang ingin diperluas (outpainting).",
            parse_mode="Markdown"
        )
        # Untuk outpainting, kita ingin menanyakan expand mode dan rasio
        return OUTPAINT_SETTINGS
    
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
        await update.message.reply_text(
            f"🔎 *Unblur*\n\n{IMGPROC_DESCRIPTIONS['unblur']}\n\n"
            "Silakan kirim gambar buram yang ingin dipertajam.",
            parse_mode="Markdown"
        )
        # Untuk unblur, kita ingin menanyakan pipeline settings
        return UNBLUR_SETTINGS
    
    elif "Kembali" in choice:
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return IMGPROC_CHOICE

# Settings for specific image processing types
async def handle_superres_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        ["2x", "4x"],
        ["Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Pilih tingkat peningkatan resolusi (upscale factor):",
        reply_markup=reply_markup
    )
    
    # Menunggu respons pengguna untuk outscale
    response = update.message.text
    
    if response in ["2x", "4x"]:
        # Simpan setting
        outscale = 2 if response == "2x" else 4
        context.user_data['superres_outscale'] = outscale
        
        await update.message.reply_text(
            f"Outscale diatur ke {outscale}x. Silakan kirim gambar yang ingin ditingkatkan resolusinya."
        )
        return IMGPROC_IMAGE
    
    elif response == "Kembali":
        return await imgproc_menu(update, context)
    
    return SUPERRES_SETTINGS

async def handle_outpaint_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Simpan setting default
    context.user_data['outpaint_settings'] = {
        "expand_mode": "separate",
        "expand_ratio": 0.125,
        "free_expand_ratio": {
            "left": 0.1,
            "right": 0.1,
            "top": 0.1,
            "bottom": 0.1
        }
    }
    
    # Karena pengaturan outpainting cukup kompleks, kita gunakan pengaturan default
    await update.message.reply_text(
        "Menggunakan pengaturan default untuk outpainting.\n"
        "• Mode: separate\n"
        "• Rasio ekspansi: 12.5%\n"
        "• Rasio kiri/kanan/atas/bawah: 10%\n\n"
        "Silakan kirim gambar yang ingin diperluas."
    )
    
    return IMGPROC_IMAGE

async def handle_unblur_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Simpan setting default untuk unblur
    context.user_data['unblur_settings'] = {
        "pipeline": {
            "bokeh": "background_blur_low",
            "color_enhance": "prism-blend",
            "background_enhance": "shiba-strong-tensorrt",
            "face_lifting": "pinko_bigger_dataset-style",
            "face_enhance": "recommender_entire_dataset"
        }
    }
    
    # Karena pengaturan unblur cukup kompleks, kita gunakan pengaturan default
    await update.message.reply_text(
        "Menggunakan pengaturan default optimal untuk unblur.\n"
        "Silakan kirim gambar buram yang ingin dipertajam."
    )
    
    return IMGPROC_IMAGE

async def handle_imgproc_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Dapatkan jenis pemrosesan yang dipilih
    imgproc_type = context.user_data.get('imgproc_type')
    
    if not imgproc_type:
        await update.message.reply_text("Terjadi kesalahan. Silakan mulai ulang proses.")
        await start(update, context)
        return ConversationHandler.END
    
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
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
            
            # Tambahkan parameter khusus berdasarkan jenis pemrosesan
            if imgproc_type == "gfp_superres":
                payload["outscale"] = context.user_data.get('superres_outscale', 2)
            
            elif imgproc_type == "outpainting":
                outpaint_settings = context.user_data.get('outpaint_settings', {
                    "expand_mode": "separate",
                    "expand_ratio": 0.125,
                    "free_expand_ratio": {
                        "left": 0.1,
                        "right": 0.1,
                        "top": 0.1,
                        "bottom": 0.1
                    }
                })
                payload.update(outpaint_settings)
            
            elif imgproc_type == "unblur":
                unblur_settings = context.user_data.get('unblur_settings', {
                    "pipeline": {
                        "bokeh": "background_blur_low",
                        "color_enhance": "prism-blend",
                        "background_enhance": "shiba-strong-tensorrt",
                        "face_lifting": "pinko_bigger_dataset-style",
                        "face_enhance": "recommender_entire_dataset"
                    }
                })
                payload.update(unblur_settings)
            
            elif imgproc_type == "advance_beauty":
                # Pengaturan default untuk advance beauty
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
            
            # Gunakan requests untuk API call
            response = requests.post(
                f"https://api.itsrose.rest/image/{imgproc_type}",
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
                        
                        # Kirim gambar hasil
                        await update.message.reply_photo(
                            photo=image_url,
                            caption=f"Hasil pemrosesan {imgproc_type}",
                            reply_markup=reply_markup
                        )
                    else:
                        await update.message.reply_text("Gambar berhasil diproses tetapi tidak ada URL yang dikembalikan.")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal memproses gambar: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
    
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        if update.message.text.lower() == "kembali":
            return await imgproc_menu(update, context)
        
        # Validasi URL
        url = update.message.text.strip()
        if url.startswith(('http://', 'https://')):
            process_message = await update.message.reply_text(f"⏳ Sedang memproses gambar dengan {imgproc_type}...")
            
            try:
                # Persiapkan payload berdasarkan jenis pemrosesan
                payload = {"init_image": url}
                
                # Tambahkan parameter khusus berdasarkan jenis pemrosesan
                if imgproc_type == "gfp_superres":
                    payload["outscale"] = context.user_data.get('superres_outscale', 2)
                
                elif imgproc_type == "outpainting":
                    outpaint_settings = context.user_data.get('outpaint_settings', {
                        "expand_mode": "separate",
                        "expand_ratio": 0.125,
                        "free_expand_ratio": {
                            "left": 0.1,
                            "right": 0.1,
                            "top": 0.1,
                            "bottom": 0.1
                        }
                    })
                    payload.update(outpaint_settings)
                
                elif imgproc_type == "unblur":
                    unblur_settings = context.user_data.get('unblur_settings', {
                        "pipeline": {
                            "bokeh": "background_blur_low",
                            "color_enhance": "prism-blend",
                            "background_enhance": "shiba-strong-tensorrt",
                            "face_lifting": "pinko_bigger_dataset-style",
                            "face_enhance": "recommender_entire_dataset"
                        }
                    })
                    payload.update(unblur_settings)
                
                elif imgproc_type == "advance_beauty":
                    # Pengaturan default untuk advance beauty
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
                
                # Gunakan requests untuk API call
                response = requests.post(
                    f"https://api.itsrose.rest/image/{imgproc_type}",
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
                            
                            # Kirim gambar hasil
                            await update.message.reply_photo(
                                photo=image_url,
                                caption=f"Hasil pemrosesan {imgproc_type}",
                                reply_markup=reply_markup
                            )
                        else:
                            await update.message.reply_text("Gambar berhasil diproses tetapi tidak ada URL yang dikembalikan.")
                    else:
                        error_message = data.get('message', 'Tidak ada detail error')
                        await update.message.reply_text(f"Gagal memproses gambar: {error_message}")
                else:
                    await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            except requests.exceptions.Timeout:
                await process_message.delete()
                await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                await process_message.delete()
                await update.message.reply_text(f"Error: {str(e)}")
                
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return IMGPROC_IMAGE
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return IMGPROC_IMAGE
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Face Fusion Menu
async def face_fusion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    
    if "Lihat Template" in choice:
        # Ambil daftar template
        process_message = await update.message.reply_text("⏳ Mengambil daftar template...")
        
        try:
            response = requests.get(
                "https://api.itsrose.rest/face_fusion/templates",
                headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
                timeout=30
            )
            
            # Hapus pesan proses
            await process_message.delete()
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status', False) and 'result' in data and 'templates' in data['result']:
                    templates = data['result']['templates']
                    
                    # Tampilkan daftar template
                    template_text = "🎭 *Template Face Fusion Tersedia*\n\n"
                    
                    # Buat keyboard untuk pilihan template
                    keyboard = []
                    current_row = []
                    
                    for template in templates:
                        template_id = template.get('id', 'unknown')
                        template_name = template.get('name', 'Unnamed Template')
                        template_gender = template.get('gender', 'Unknown')
                        template_url = template.get('url', '')
                        
                        template_text += f"• ID: `{template_id}`\n  Nama: {template_name}\n  Gender: {template_gender}\n\n"
                        
                        # Tambahkan ke keyboard
                        current_row.append(template_id)
                        if len(current_row) == 2:
                            keyboard.append(current_row)
                            current_row = []
                    
                    # Tambahkan row terakhir jika ada
                    if current_row:
                        keyboard.append(current_row)
                    
                    # Tambahkan tombol kembali
                    keyboard.append(["🔙 Kembali"])
                    
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    # Simpan templates untuk digunakan nanti
                    context.user_data['face_fusion_templates'] = templates
                    
                    # Tampilkan contoh beberapa template
                    if templates:
                        # Kirim beberapa contoh template (max 5)
                        sample_templates = templates[:min(5, len(templates))]
                        
                        await update.message.reply_text(
                            template_text + "\nSilakan pilih template ID untuk melakukan face fusion:",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        for template in sample_templates:
                            template_url = template.get('url', '')
                            template_name = template.get('name', 'Unnamed Template')
                            template_id = template.get('id', 'unknown')
                            
                            if template_url:
                                await update.message.reply_photo(
                                    photo=template_url,
                                    caption=f"Template: {template_name}\nID: {template_id}"
                                )
                    else:
                        await update.message.reply_text("Tidak ada template yang tersedia.")
                        return await face_fusion_menu(update, context)
                else:
                    await update.message.reply_text("Gagal mendapatkan daftar template.")
                    return await face_fusion_menu(update, context)
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code}")
                return await face_fusion_menu(update, context)
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            return await face_fusion_menu(update, context)
        
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
            return await face_fusion_menu(update, context)
        
        return FACE_FUSION_TEMPLATE
    
    elif "Buat Face Fusion" in choice:
        await update.message.reply_text(
            "Silakan masukkan ID template yang ingin digunakan. Gunakan 'Lihat Template' jika Anda belum mengetahui ID template."
        )
        return FACE_FUSION_TEMPLATE
    
    elif "Kembali" in choice:
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return FACE_FUSION_CHOICE

async def handle_face_fusion_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    template_id = update.message.text
    
    if template_id == "🔙 Kembali":
        return await face_fusion_menu(update, context)
    
    # Simpan template ID
    context.user_data['face_fusion_template_id'] = template_id
    
    # Instruksi untuk mengirim gambar
    await update.message.reply_text(
        "Silakan kirim gambar wajah Anda untuk digabungkan dengan template terpilih.\n"
        "Pastikan wajah terlihat jelas dan dari sudut depan untuk hasil terbaik."
    )
    
    return FACE_FUSION_IMAGE

async def handle_face_fusion_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    template_id = context.user_data.get('face_fusion_template_id', '')
    
    if not template_id:
        await update.message.reply_text("Template ID tidak tersedia. Silakan mulai ulang proses.")
        return await face_fusion_menu(update, context)
    
    # Periksa apakah pesan berisi gambar
    if update.message.photo:
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
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
            
            # Persiapkan payload
            payload = {
                "id": template_id,
                "init_image": init_image
            }
            
            # Gunakan requests untuk API call
            response = requests.post(
                "https://api.itsrose.rest/face_fusion/create",
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
                
                if data.get('status', False):
                    if 'result' in data and 'url' in data['result']:
                        image_url = data['result']['url']
                        
                        # Tambahkan tombol untuk proses lebih lanjut
                        keyboard = [
                            [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")],
                            [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Simpan URL gambar untuk digunakan nanti
                        context.user_data['last_image_url'] = image_url
                        
                        # Kirim gambar hasil
                        await update.message.reply_photo(
                            photo=image_url,
                            caption=f"Hasil face fusion dengan template ID: {template_id}",
                            reply_markup=reply_markup
                        )
                    else:
                        await update.message.reply_text("Face fusion berhasil tetapi tidak ada URL yang dikembalikan.")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal membuat face fusion: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        except Exception as e:
            logger.error(f"Error creating face fusion: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
    
    elif update.message.text:
        # Jika pengguna mengirim URL alih-alih gambar
        if update.message.text.lower() == "kembali":
            return await face_fusion_menu(update, context)
        
        # Validasi URL
        url = update.message.text.strip()
        if url.startswith(('http://', 'https://')):
            process_message = await update.message.reply_text("⏳ Sedang membuat face fusion...")
            
            try:
                # Persiapkan payload
                payload = {
                    "id": template_id,
                    "init_image": url
                }
                
                # Gunakan requests untuk API call
                response = requests.post(
                    "https://api.itsrose.rest/face_fusion/create",
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
                    
                    if data.get('status', False):
                        if 'result' in data and 'url' in data['result']:
                            image_url = data['result']['url']
                            
                            # Tambahkan tombol untuk proses lebih lanjut
                            keyboard = [
                                [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")],
                                [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            # Simpan URL gambar untuk digunakan nanti
                            context.user_data['last_image_url'] = image_url
                            
                            # Kirim gambar hasil
                            await update.message.reply_photo(
                                photo=image_url,
                                caption=f"Hasil face fusion dengan template ID: {template_id}",
                                reply_markup=reply_markup
                            )
                        else:
                            await update.message.reply_text("Face fusion berhasil tetapi tidak ada URL yang dikembalikan.")
                    else:
                        error_message = data.get('message', 'Tidak ada detail error')
                        await update.message.reply_text(f"Gagal membuat face fusion: {error_message}")
                else:
                    await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
            
            except requests.exceptions.Timeout:
                await process_message.delete()
                await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
            
            except Exception as e:
                logger.error(f"Error creating face fusion: {str(e)}")
                await process_message.delete()
                await update.message.reply_text(f"Error: {str(e)}")
                
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return FACE_FUSION_IMAGE
    
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return FACE_FUSION_IMAGE
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# TikTok Downloader
async def tiktok_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"📱 *TikTok Downloader*\n\n{FEATURE_DESCRIPTIONS['tiktok']}\n\n"
        "Silakan kirim URL video TikTok yang ingin diunduh:",
        parse_mode="Markdown"
    )
    return TIKTOK_URL

async def handle_tiktok_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tiktok_url = update.message.text.strip()
    
    if tiktok_url.lower() == "kembali":
        await start(update, context)
        return ConversationHandler.END
    
    # Validasi URL
    if not tiktok_url.startswith(('http://', 'https://')) or 'tiktok.com' not in tiktok_url:
        await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https:// dan merupakan URL TikTok.")
        return TIKTOK_URL
    
    # Pesan sedang memproses
    process_message = await update.message.reply_text("⏳ Sedang mengunduh video TikTok...")
    
    try:
        # Gunakan requests library untuk API call
        response = requests.get(
            "https://api.itsrose.rest/tiktok/get",
            params={"url": tiktok_url},
            headers={'Authorization': f"Bearer {ITSROSE_API_KEY}"},
            timeout=60  # 60 detik timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status', False) and 'result' in data:
                result = data['result']
                
                # Informasi video
                author = result.get('author', {}).get('nickname', 'Unknown')
                title = result.get('title', 'TikTok Video')
                like_count = result.get('statistics', {}).get('like_count', 0)
                comment_count = result.get('statistics', {}).get('comment_count', 0)
                share_count = result.get('statistics', {}).get('share_count', 0)
                duration = result.get('duration', 0)
                
                # Info caption
                info_text = f"🎬 *Video TikTok*\n\n"
                info_text += f"👤 Author: {author}\n"
                info_text += f"📝 Title: {title}\n"
                info_text += f"❤️ Likes: {like_count}\n"
                info_text += f"💬 Comments: {comment_count}\n"
                info_text += f"🔄 Shares: {share_count}\n"
                info_text += f"⏱️ Duration: {duration} seconds\n"
                
                # Hapus pesan proses
                await process_message.delete()
                
                # Kirim info terlebih dahulu
                await update.message.reply_text(info_text, parse_mode="Markdown")
                
                # Cek dan kirim video atau gambar
                if 'video' in result and 'url_list' in result['video'] and result['video']['url_list']:
                    video_url = result['video']['url_list'][0]
                    
                    # Kirim video sebagai video
                    await update.message.reply_video(
                        video=video_url,
                        caption=f"Video TikTok by {author}"
                    )
                elif 'image_post' in result and result['image_post'] and 'images' in result['image_post']:
                    # Ini adalah post gambar
                    images = result['image_post']['images']
                    
                    await update.message.reply_text("Ini adalah post gambar. Mengirim semua gambar...")
                    
                    # Kirim hingga 10 gambar
                    for i, image in enumerate(images[:10]):
                        if 'url_list' in image and image['url_list']:
                            image_url = image['url_list'][0]
                            await update.message.reply_photo(
                                photo=image_url,
                                caption=f"Image {i+1}/{len(images)} from TikTok by {author}"
                            )
                else:
                    await update.message.reply_text("Tidak dapat menemukan video atau gambar dari TikTok.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await process_message.delete()
                await update.message.reply_text(f"Gagal mengunduh video TikTok: {error_message}")
        else:
            await process_message.delete()
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error downloading TikTok: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Handler untuk menggunakan prompt yang dihasilkan
async def use_prompt_for_txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if 'generated_prompt' in context.user_data:
        context.user_data['prompt'] = context.user_data['generated_prompt']
        await query.message.reply_text("Masukkan URL gambar inisialisasi (ketik 'skip' jika tidak ada):")
        return INIT_IMAGE
    else:
        await query.message.reply_text("Tidak ada prompt yang dihasilkan sebelumnya.")
        await start(update, context)
        return ConversationHandler.END

async def use_prompt_for_img2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if 'generated_prompt' in context.user_data:
        context.user_data['img2img_prompt'] = context.user_data['generated_prompt']
        await query.message.reply_text("Silakan kirim gambar yang ingin dimodifikasi:")
        return IMG2IMG_IMAGE
    else:
        await query.message.reply_text("Tidak ada prompt yang dihasilkan sebelumnya.")
        await start(update, context)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operasi dibatalkan")
    await start(update, context)
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

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

    # Settings conversation handler
    settings_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Settings$"), settings_menu)],
        states={
            SETTINGS_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_choice)],
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
            SUPERRES_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_superres_settings)],
            OUTPAINT_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_outpaint_settings)],
            UNBLUR_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unblur_settings)]
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

    # Tambahkan semua handler
    application.add_handler(txt2img_conv_handler)
    application.add_handler(img2img_conv_handler)
    application.add_handler(prompt_gen_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(help_conv_handler)
    application.add_handler(imgproc_conv_handler)
    application.add_handler(face_fusion_conv_handler)
    application.add_handler(tiktok_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^📊 System Info$"), get_system_info))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Kembali$"), start))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Handler untuk pesan yang tidak dikenali
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    # Mulai polling
    application.run_polling()

if __name__ == "__main__":
    main()