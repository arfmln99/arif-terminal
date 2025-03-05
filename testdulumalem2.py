import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
import http.client
import json
import time

# Konfigurasi
LOVITA_API_KEY = "Prod-Sk-35e0294f17662bfc0323399264bb85ab"
BOT_TOKEN = "8010525002:AAHKAnTBuNmGM9sWK0IAS4rfe9M5G1JcLfs"

# State untuk conversation handler
PROMPT, INIT_IMAGE = range(2)
# State untuk image to image handler
IMG2IMG_PROMPT, IMG2IMG_IMAGE = range(2, 4)
# State untuk settings
SETTINGS_CHOICE, SETTINGS_VALUE = range(4, 6)

# Default settings
DEFAULT_SETTINGS = {
    "width": 512,
    "height": 512,
    "samples": 1,
    "num_inference_steps": 21,
    "scheduler": "DDPMScheduler",
    "clip_skip": 2,
    "model_id": "dreamshaper",
    "nsfw_filter": False  # Default NSFW filter dimatikan
}

# Inisialisasi logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inisialisasi settings jika belum ada
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    keyboard = [
        ["🖼 Text to Image", "🎨 Image to Image"],
        ["🧠 Generate Prompt", "📊 System Info"],
        ["⚙️ Settings"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Selamat datang di Lovita AI Bot! Pilih opsi:", reply_markup=reply_markup)

# Text to Image Flow
async def txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Masukkan prompt untuk generasi gambar:")
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
    
    conn = http.client.HTTPSConnection("api.lovita.io")
    headers = {
        'Content-Type': "application/json",
        'Authorization': f"Bearer {LOVITA_API_KEY}"
    }
    
    payload = {
        "server_id": "rose",
        "model_id": settings["model_id"],
        "prompt": prompt,
        "width": settings["width"],
        "height": settings["height"],
        "samples": settings["samples"],
        "num_inference_steps": settings["num_inference_steps"],
        "scheduler": settings["scheduler"],
        "clip_skip": settings["clip_skip"],
        "nsfw_filter": settings.get("nsfw_filter", False)  # Tambahkan parameter NSFW filter ke API
    }
    
    # Tambahkan init_image ke payload jika bukan 'skip'
    if init_image and init_image.lower() != 'skip':
        payload["init_image"] = init_image
        endpoint = "/sdapi/img2img"  # Gunakan endpoint yang benar untuk image-to-image
    else:
        endpoint = "/sdapi/txt2img"  # Endpoint untuk text-to-image
    
    try:
        # Kirim request ke API
        conn.request("POST", endpoint, json.dumps(payload), headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
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
                
                await update.message.reply_photo(
                    photo=image_url,
                    caption=f"Hasil generasi:\n{prompt}\n{nsfw_warning}"
                )
            else:
                await update.message.reply_text("Gambar berhasil dibuat tetapi tidak ada URL yang dikembalikan.")
        else:
            error_message = data.get('message', 'Tidak ada detail error')
            await update.message.reply_text(f"Gagal menghasilkan gambar: {error_message}")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Image to Image Flow
async def img2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Masukkan URL gambar yang ingin dimodifikasi:")
    return IMG2IMG_IMAGE

async def handle_img2img_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['init_image'] = update.message.text
    await update.message.reply_text("Masukkan prompt untuk modifikasi gambar:")
    return IMG2IMG_PROMPT

async def handle_img2img_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = update.message.text
    init_image = context.user_data['init_image']
    settings = context.user_data.get('settings', DEFAULT_SETTINGS)
    
    # Pesan "sedang memproses"
    process_message = await update.message.reply_text("⏳ Sedang memproses gambar...")
    
    conn = http.client.HTTPSConnection("api.lovita.io")
    headers = {
        'Content-Type': "application/json",
        'Authorization': f"Bearer {LOVITA_API_KEY}"
    }
    
    payload = {
        "server_id": "rose",
        "model_id": settings["model_id"],
        "prompt": prompt,
        "init_image": init_image,  # Selalu gunakan init_image untuk img2img
        "width": settings["width"],
        "height": settings["height"],
        "samples": settings["samples"],
        "num_inference_steps": settings["num_inference_steps"],
        "scheduler": settings["scheduler"],
        "clip_skip": settings["clip_skip"],
        "nsfw_filter": settings.get("nsfw_filter", False)  # Tambahkan parameter NSFW filter ke API
    }
    
    try:
        conn.request("POST", "/sdapi/img2img", json.dumps(payload), headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        # Hapus pesan "sedang memproses"
        await process_message.delete()
        
        if 'status' in data and data['status']:
            if 'result' in data and 'images' in data['result'] and len(data['result']['images']) > 0:
                image_url = data['result']['images'][0]
                
                # Cek NSFW hanya jika filter diaktifkan
                nsfw_warning = ""
                if settings.get("nsfw_filter", False) and data['result'].get('nsfw_content_detected', False):
                    nsfw_warning = "⚠️ NSFW Content Detected!"
                
                await update.message.reply_photo(
                    photo=image_url,
                    caption=f"Hasil modifikasi:\n{prompt}\n{nsfw_warning}"
                )
            else:
                await update.message.reply_text("Gambar berhasil dimodifikasi tetapi tidak ada URL yang dikembalikan.")
        else:
            error_message = data.get('message', 'Tidak ada detail error')
            await update.message.reply_text(f"Gagal memodifikasi gambar: {error_message}")
    
    except Exception as e:
        logger.error(f"Error modifying image: {str(e)}")
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Settings Flow
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Pastikan settings tersedia
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    settings = context.user_data['settings']
    settings_text = "Pengaturan saat ini:\n"
    for key, value in settings.items():
        # Format khusus untuk NSFW filter
        if key == "nsfw_filter":
            status = "Aktif" if value else "Nonaktif"
            settings_text += f"• NSFW Filter: {status}\n"
        else:
            settings_text += f"• {key}: {value}\n"
    
    keyboard = [
        ["Width", "Height", "Samples"],
        ["Steps", "Model", "Scheduler"],
        ["Clip Skip", "NSFW Filter", "Kembali"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"{settings_text}\nPilih pengaturan yang ingin diubah:",
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
        "nsfw filter": "nsfw_filter"
    }
    
    if choice in choice_mapping:
        context.user_data['current_setting'] = choice_mapping[choice]
        current_value = context.user_data['settings'][choice_mapping[choice]]
        
        # Berikan pilihan spesifik untuk model dan scheduler
        if choice == "model":
            keyboard = [["dreamshaper", "realistic_vision"], ["sdxl", "kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"Model saat ini: {current_value}. Pilih model baru:",
                reply_markup=reply_markup
            )
        elif choice == "scheduler":
            keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"Scheduler saat ini: {current_value}. Pilih scheduler baru:",
                reply_markup=reply_markup
            )
        elif choice == "nsfw filter":
            # Pilihan untuk aktifkan/nonaktifkan NSFW filter
            status = "Aktif" if current_value else "Nonaktif"
            keyboard = [["Aktif", "Nonaktif"], ["Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"NSFW Filter saat ini: {status}. Pilih status baru:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"Nilai {choice} saat ini: {current_value}. Masukkan nilai baru:"
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
        
        # Penanganan untuk setting numerik
        elif current_setting in ["width", "height", "samples", "num_inference_steps", "clip_skip"]:
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

async def get_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tambahkan pesan loading
    loading_message = await update.message.reply_text("⏳ Mengambil informasi sistem...")
    
    conn = http.client.HTTPSConnection("api.lovita.io")
    headers = {'Authorization': f"Bearer {LOVITA_API_KEY}"}
    
    try:
        conn.request("GET", "/sdapi/system_details?server_id=rose", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        # Hapus pesan loading
        await loading_message.delete()
        
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
            await update.message.reply_text("Tidak dapat memperoleh informasi sistem.")
    
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        await loading_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)

async def generate_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tambahkan pesan loading
    loading_message = await update.message.reply_text("🧠 Menghasilkan prompt...")
    
    conn = http.client.HTTPSConnection("api.lovita.io")
    headers = {'Authorization': f"Bearer {LOVITA_API_KEY}"}
    
    try:
        conn.request("GET", "/sdapi/generate_prompt", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        # Hapus pesan loading
        await loading_message.delete()
        
        if 'result' in data and 'prompt' in data['result']:
            prompt = data['result']['prompt']
            # Tambahkan tombol untuk langsung menggunakan prompt ini
            keyboard = [["🖼 Gunakan untuk Text2Img", "🎨 Gunakan untuk Img2Img"], ["🔙 Kembali"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Simpan prompt untuk digunakan nanti
            context.user_data['generated_prompt'] = prompt
            
            await update.message.reply_text(
                f"✨ **Generated Prompt**:\n\n{prompt}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Gagal menghasilkan prompt.")
            await start(update, context)
    
    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        await loading_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
        await start(update, context)

async def use_generated_prompt_txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'generated_prompt' in context.user_data:
        context.user_data['prompt'] = context.user_data['generated_prompt']
        await update.message.reply_text("Masukkan URL gambar inisialisasi (ketik 'skip' jika tidak ada):")
        return INIT_IMAGE
    else:
        await update.message.reply_text("Tidak ada prompt yang dihasilkan sebelumnya.")
        await start(update, context)
        return ConversationHandler.END

async def use_generated_prompt_img2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'generated_prompt' in context.user_data:
        context.user_data['prompt'] = context.user_data['generated_prompt']
        await update.message.reply_text("Masukkan URL gambar yang ingin dimodifikasi:")
        return IMG2IMG_IMAGE
    else:
        await update.message.reply_text("Tidak ada prompt yang dihasilkan sebelumnya.")
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
            MessageHandler(filters.Regex("^🖼 Gunakan untuk Text2Img$"), use_generated_prompt_txt2img)
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
            MessageHandler(filters.Regex("^🎨 Gunakan untuk Img2Img$"), use_generated_prompt_img2img)
        ],
        states={
            IMG2IMG_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_img2img_image)],
            IMG2IMG_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_img2img_prompt)]
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

    # Tambahkan semua handler
    application.add_handler(txt2img_conv_handler)
    application.add_handler(img2img_conv_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^📊 System Info$"), get_system_info))
    application.add_handler(MessageHandler(filters.Regex("^🧠 Generate Prompt$"), generate_prompt))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Kembali$"), start))

    # Handler untuk pesan yang tidak dikenali
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    # Mulai polling
    application.run_polling()

if __name__ == "__main__":
    main()