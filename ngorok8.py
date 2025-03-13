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
import asyncio
from PIL import Image
import random

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
        "tomesd": False,
        "use_karras_sigmas": False,
        "algorithm_type": "dpmsolver+++"
    }
}

# Kategori prompt untuk peningkatan prompt secara lokal
PROMPT_ENHANCEMENTS = {
    "id": {
        "general": [
            "foto resolusi tinggi", "detail sangat tinggi", "pencahayaan profesional", 
            "fotorealistik", "kualitas studio", "8K UHD", "ultra detail", 
            "tekstur realistik", "proporsi sempurna", "masterpiece", "hyperrealistic",
            "detail wajah", "warna vivid", "fotografi tajam", "karya seni digital",
            "efek cahaya dramatis", "bayangan realistik", "komposisi dinamis",
            "tekstur kulit alami", "detail mata", "rambut terurai indah"
        ],
        "landscape": [
            "pemandangan indah", "panorama luas", "sunrise dramatis", "sunset memukau", "golden hour", 
            "awan dramatis", "refleksi di air", "sinar matahari tembus", "bayangan panjang",
            "pegunungan megah", "hutan hijau subur", "lembah yang dalam", "sungai berkelok-kelok",
            "air terjun memesona", "kabut tipis", "hujan rintik", "petir menyambar", "pelangi lengkung"
        ],
        "portrait": [
            "sudut potret terbaik", "lensa potret profesional", "bokeh natural", "depth of field",
            "ekspresi wajah alami", "tatapan mata fokus", "detail kulit natural",
            "rambut terurai indah", "cahaya depan lembut", "pencahayaan Rembrandt",
            "senyum alami", "sudut wajah terbaik", "tekstur kulit halus", "bulu mata lentik",
            "bibir berkilau", "garis rahang tegas", "leher jenjang", "tulang pipi menonjol"
        ],
        "artistic": [
            "gaya seni tinggi", "concept art", "ilustrasi digital premium", "digital painting",
            "cat air", "minyak pada kanvas", "lukisan detil", "brushstrokes halus", 
            "warna cerah", "kontras tinggi", "sentuhan artistik", "pastel lembut",
            "teknik chiaroscuro", "impasto", "tekstur kanvas", "ukiran detail",
            "seni kontemporer", "gaya surrealis", "kubisme", "art nouveau"
        ],
        "fantasy": [
            "dunia fantasi memukau", "makhluk mistis indah", "peri bersayap", "naga berkilau", "sihir berkilauan",
            "kastil megah", "hutan ajaib", "efek cahaya magis", "pedang legendaris",
            "pakaian fantasi mewah", "armor elegan", "simbol mistis bercahaya", "portal dimensi",
            "binatang mitologi", "unicorn", "phoenix", "centaur", "elf", "dwarf", "orc", 
            "batu kristal bercahaya", "tongkat sihir", "ramuan magis", "perkamen kuno"
        ],
        "sci_fi": [
            "futuristik canggih", "cyber environment", "neon bercahaya", "teknologi canggih", "robot humanoid", "cyberpunk",
            "kota masa depan", "hologram interaktif", "interface digital", "pesawat luar angkasa",
            "senjata laser", "armor futuristik", "android", "augmented reality",
            "planet asing", "stasiun luar angkasa", "implan cybernetic", "android", "AI visual",
            "jalan berlapis neon", "megastructure", "hologram 3D", "portal wormhole"
        ],
        "body_detail": [
            "anatomi tubuh sempurna", "proporsi tubuh ideal", "detail otot halus", "bentuk tubuh proporsional",
            "tulang selangka menonjol", "otot perut terbentuk", "lengan berotot", "kaki jenjang",
            "pinggang ramping", "bahu lebar", "pinggang kecil", "pinggul melengkung",
            "postur sempurna", "struktur tulang ideal", "jari tangan panjang", "leher jenjang",
            "tulang belikat terlihat", "otot punggung terbentuk", "garis pinggang tegas"
        ],
        "nsfw": [
            "pose menggoda", "pakaian minim", "ekspresi sensual", "tubuh indah",
            "lekuk tubuh sensual", "kulit halus mengkilap", "cahaya intim", "angle sensual",
            "siluet menawan", "lingerie mewah", "kostum seksi", "gaun ketat",
            "pakaian transparan", "kulit berkeringat", "tatapan menggoda",
            "belahan dada", "punggung terbuka", "kaki jenjang", "paha mulus",
            "bibir berkilau", "gaya sensual", "pakaian basah", "jari menyentuh bibir"
        ],
        "adult": [
            "telanjang artistik", "kulit mulus berkilau", "posisi erotis", "ruangan intim",
            "tanpa busana", "ketelanjangan artistik", "tubuh sempurna", "kurva tubuh sensual",
            "posisi intim", "sensualitas tinggi", "keindahan natural", "kulit berkilau",
            "leher jenjang", "pundak eksotis", "punggung melengkung", "payudara indah",
            "puting tegang", "pinggang ramping", "pinggul berisi", "bokong bulat sempurna",
            "paha berisi", "betis proporsional", "perut rata", "lekuk sisi tubuh",
            "bulu halus tubuh", "aurat tertutup strategis", "niple piercing", "tato artistik",
            "bulu kemaluan rapi", "lipatan paha jelas", "lekukan bokong dalam", "kemaluan terlihat samar"
        ],
        "face_detail": [
    "wajah sempurna", "fitur wajah proporsional", "struktur wajah ideal", "simetri wajah",
    "tulang pipi menonjol", "garis rahang tegas", "dagu proporsional", "kontur wajah jelas",
    "kulit wajah halus", "kompleksi wajah tanpa cela", "tekstur kulit natural", "pori-pori halus",
    "rona pipi alami", "warna kulit merata", "gradasi warna kulit sempurna", "undertone kulit seimbang",
    "alis tebal", "alis rapi", "lengkungan alis sempurna", "bentuk alis proporsional",
    "mata berbinar", "mata ekspresif", "sorot mata intens", "tatapan dalam",
    "bulu mata lentik", "bulu mata panjang", "bulu mata tebal", "bulu mata berlapis",
    "kelopak mata terdefinisi", "lipatan mata jelas", "sudut mata terangkat", "bentuk mata harmonis",
    "iris mata detail", "warna mata cemerlang", "pupil mata jelas", "refleksi cahaya pada mata",
    "hidung proporsional", "bentuk hidung ideal", "batang hidung lurus", "ujung hidung terdefinisi",
    "bibir penuh", "bibir sensual", "kontur bibir jelas", "bentuk bibir simetris",
    "senyum menawan", "senyum natural", "gigi putih", "gigi rata",
    "ekspresi wajah hidup", "emosi terpancar", "mimik wajah ekspresif", "raut wajah dinamis",
    "dahi halus", "dahi proporsional", "garis dahi minimal", "pertemuan alis dan dahi sempurna",
    "telinga proporsional", "bentuk telinga seimbang", "cuping telinga terdefinisi", "telinga sejajar dengan wajah",
    "leher jenjang", "garis leher anggun", "pertemuan leher dan dagu jelas", "kontur leher halus",
    "tahi lalat strategis", "bintik kecantikan menarik", "penanda wajah unik", "detail karakteristik wajah"
],
        "nudity": [
            "nude", "tanpa pakaian", "telanjang penuh", "naked", "ketelanjangan sempurna",
            "model nude", "ekspos tubuh total", "full body exposure", "figure study",
            "anatomi indah", "bentuk tubuh ideal", "sensual tanpa busana",
            "ketelanjangan artistik", "pose telanjang", "tubuh polos", "nude art",
            "alat kelamin terlihat", "vulva detail", "penis detail", "bulu kemaluan alami",
            "bokong terbuka penuh", "payudara terbuka", "kemaluan terekspos", "testis terlihat",
            "opening vagina", "opening anus", "labia detail", "glans detail", "bulu pubis lebat",
            "penetrasi", "squirting", "ejakulasi", "cairan tubuh", "bukaan intim",
            "seks eksplisit", "intercourse", "masturbasi", "orgasme", "klimaks"
        ]
    },
    "en": {
    "general": [
        "high resolution photo", "highly detailed", "professional lighting", 
        "photorealistic", "studio quality", "8K UHD", "ultra detailed", 
        "realistic texture", "perfect proportions", "masterpiece", "hyperrealistic",
        "facial details", "vivid colors", "sharp photography", "digital artwork",
        "dramatic lighting effects", "realistic shadows", "dynamic composition",
        "natural skin texture", "eye details", "flowing hair",
        "cinematic shot", "high fidelity", "professional photography", "award-winning photo",
        "lifelike render", "photorealistic rendering", "crystal clear image", "extreme detail",
        "perfect focus", "professional color grading", "ultra-realistic", "immaculate detail",
        "stunning photograph", "professional image", "perfect lighting", "natural lighting", 
        "volumetric lighting", "rim lighting", "ambient lighting", "soft lighting",
        "hard lighting", "directional lighting", "diffused lighting", "atmospheric lighting",
        "key lighting", "fill lighting", "backlighting", "side lighting",
        "symmetrical composition", "rule of thirds", "golden ratio composition", "dynamic angle",
        "perfect exposure", "high dynamic range", "detailed textures", "realistic materials",
        "accurate reflections", "precise shadows", "ambient occlusion", "subsurface scattering",
        "physically based rendering", "ray tracing", "global illumination", "color accuracy",
        "detailed skin texture", "pore-level detail", "anatomically correct", "detailed iris",
        "detailed retina", "detailed sclera", "detailed pupil", "detailed cornea",
        "detailed eyelashes", "detailed eyebrows", "detailed hair strands", "detailed hair fibers",
        "detailed fur", "detailed fabric", "detailed leather", "detailed metal",
        "detailed glass", "detailed water", "detailed wood", "detailed stone",
        "detailed concrete", "detailed sand", "detailed snow", "detailed clouds",
        "detailed smoke", "detailed fire", "detailed explosion", "detailed debris",
        "detailed dust", "detailed particle effects", "detailed atmospheric effects", "detailed weather effects",
        "detailed rain", "detailed fog", "detailed mist", "detailed steam",
        "detailed breath", "detailed sweat", "detailed tears", "detailed blood",
        "detailed wounds", "detailed scars", "detailed veins", "detailed muscles",
        "detailed tendons", "detailed bones", "detailed joints", "detailed fingernails",
        "detailed toenails", "detailed teeth", "detailed gums", "detailed tongue",
        "detailed lips", "detailed nose", "detailed ears", "detailed face",
        "accurate anatomy", "accurate proportions", "accurate perspective", "accurate scale",
        "accurate reflections", "accurate refractions", "accurate diffusion", "accurate absorption",
        "accurate subsurface scattering", "accurate translucency", "accurate transparency", "accurate opacity",
        "accurate specularity", "accurate roughness", "accurate metalness", "accurate emissiveness",
        "film grain", "bokeh effect", "depth of field", "tilt-shift effect",
        "fisheye effect", "wide-angle effect", "telephoto effect", "macro photography",
        "microscopical detail", "astronomical detail", "aerial photography", "drone photography",
        "satellite imagery", "panoramic view", "spherical panorama", "360-degree view",
        "VR compatible", "AR compatible", "stereoscopic 3D", "anaglyph 3D",
        "high contrast", "low contrast", "high saturation", "low saturation",
        "high brightness", "low brightness", "high clarity", "low clarity",
        "high sharpness", "low sharpness", "high definition", "low definition",
        "high fidelity", "low fidelity", "high vibrance", "low vibrance",
        "high resolution", "low resolution", "high detail", "low detail",
        "high poly", "low poly", "high complexity", "low complexity",
        "high realism", "low realism", "high stylization", "low stylization",
        "high abstraction", "low abstraction", "high surrealism", "low surrealism",
        "high expressionism", "low expressionism", "high impressionism", "low impressionism",
        "high cubism", "low cubism", "high minimalism", "low minimalism",
        "high maximalism", "low maximalism", "high conceptualism", "low conceptualism",
        "fine art photography", "documentary photography", "street photography", "fashion photography",
        "portrait photography", "landscape photography", "architectural photography", "industrial photography",
        "product photography", "food photography", "wildlife photography", "sports photography",
        "action photography", "event photography", "wedding photography", "travel photography",
        "night photography", "long exposure photography", "time-lapse photography", "high-speed photography",
        "ultra-detailed environment", "photo-realistic environment", "ultra-realistic environment", "hyper-realistic environment",
        "ultra-detailed character", "photo-realistic character", "ultra-realistic character", "hyper-realistic character",
        "ultra-detailed object", "photo-realistic object", "ultra-realistic object", "hyper-realistic object",
        "ultra-detailed landscape", "photo-realistic landscape", "ultra-realistic landscape", "hyper-realistic landscape",
        "ultra-detailed portrait", "photo-realistic portrait", "ultra-realistic portrait", "hyper-realistic portrait",
        "ultra-detailed still life", "photo-realistic still life", "ultra-realistic still life", "hyper-realistic still life",
        "perfect color balance", "perfect white balance", "perfect black levels", "perfect highlights",
        "perfect midtones", "perfect shadows", "perfect contrast", "perfect saturation",
        "perfect vibrance", "perfect clarity", "perfect sharpness", "perfect focus",
        "perfect exposure", "perfect lighting", "perfect composition", "perfect framing",
        "perfect angle", "perfect perspective", "perfect proportion", "perfect scale",
        "perfect depth", "perfect detail", "perfect texture", "perfect finish",
        "perfect reflection", "perfect refraction", "perfect specularity", "perfect diffusion",
        "perfect absorption", "perfect scattering", "perfect translucency", "perfect transparency",
        "perfect opacity", "perfect emission", "perfect ambient occlusion", "perfect global illumination",
        "award-winning composition", "museum quality", "gallery quality", "exhibition quality",
        "professional quality", "commercial quality", "editorial quality", "advertising quality",
        "broadcast quality", "cinema quality", "documentary quality", "archival quality",
        "detailed foreground", "detailed middleground", "detailed background", "detailed scenery",
        "detailed environment", "detailed surroundings", "detailed context", "detailed setting",
        "detailed weather", "detailed time of day", "detailed season", "detailed climate",
        "detailed geography", "detailed topography", "detailed geology", "detailed flora",
        "detailed fauna", "detailed ecosystem", "detailed biome", "detailed habitat",
        "detailed microclimate", "detailed macroscape", "detailed landscape", "detailed cityscape",
        "detailed seascape", "detailed skyscape", "detailed spacescape", "detailed dreamscape",
        "detailed nightmare", "detailed fantasy", "detailed sci-fi", "detailed horror",
        "detailed thriller", "detailed drama", "detailed comedy", "detailed romance",
        "detailed action", "detailed adventure", "detailed mystery", "detailed noir",
        "detailed western", "detailed eastern", "detailed northern", "detailed southern",
        "highly polished", "expertly rendered", "meticulously detailed", "painstakingly crafted",
        "precisely executed", "carefully designed", "thoughtfully composed", "skillfully created",
        "artfully arranged", "beautifully balanced", "harmoniously structured", "elegantly presented",
        "professionally produced", "technically perfect", "aesthetically pleasing", "visually stunning",
        "optically impressive", "perceptually engaging", "sensually stimulating", "emotionally evocative",
        "intellectually stimulating", "spiritually moving", "transcendentally beautiful", "sublimely perfect",
        "visual coherence", "logical consistency", "narrative clarity", "thematic unity",
        "stylistic consistency", "compositional balance", "proportional harmony", "chromatic harmony",
        "luminous harmony", "tonal harmony", "textural harmony", "formal harmony",
        "atmospheric quality", "ethereal quality", "sublime quality", "transcendent quality",
        "divine quality", "celestial quality", "infernal quality", "terrestrial quality",
        "aquatic quality", "aerial quality", "igneous quality", "glacial quality",
        "extreme close-up", "close-up", "medium shot", "full shot",
        "long shot", "extreme long shot", "establishing shot", "tracking shot",
        "dolly shot", "crane shot", "aerial shot", "overhead shot",
        "low angle shot", "high angle shot", "dutch angle shot", "over-the-shoulder shot",
        "point-of-view shot", "two-shot", "three-shot", "group shot",
        "master shot", "insert shot", "cutaway shot", "reaction shot",
        "golden hour lighting", "magic hour lighting", "blue hour lighting", "midday lighting",
        "dawn lighting", "dusk lighting", "twilight lighting", "midnight lighting",
        "morning lighting", "afternoon lighting", "evening lighting", "night lighting",
        "natural lighting", "artificial lighting", "mixed lighting", "practical lighting",
        "studio lighting", "on-location lighting", "environmental lighting", "practical lighting",
        "controlled lighting", "uncontrolled lighting", "consistent lighting", "inconsistent lighting",
        "hard lighting", "soft lighting", "direct lighting", "indirect lighting",
        "diffused lighting", "focused lighting", "even lighting", "uneven lighting",
        "high-key lighting", "low-key lighting", "mid-key lighting", "chiaroscuro lighting",
        "Rembrandt lighting", "butterfly lighting", "loop lighting", "split lighting",
        "backlight", "key light", "fill light", "rim light",
        "hair light", "kicker light", "practical light", "motivated light",
        "volumetric light", "shaped light", "patterned light", "textured light",
        "colored light", "white light", "warm light", "cool light",
        "daylight", "tungsten light", "fluorescent light", "LED light",
        "HMI light", "kino flo light", "incandescent light", "halogen light",
        "flash", "strobe", "continuous light", "ambient light",
        "natural light", "artificial light", "mixed light", "practical light",
        "reflector", "diffuser", "scrim", "flag",
        "gobo", "cookie", "gel", "filter",
        "softbox", "umbrella", "beauty dish", "ring light",
        "octabox", "stripbox", "snoot", "barn doors",
        "grid", "honeycomb", "fresnel", "parabolic",
        "raw film", "processed film", "digital sensor", "analog film",
        "35mm film", "medium format film", "large format film", "instant film",
        "black and white film", "color film", "slide film", "negative film",
        "high iso film", "low iso film", "grainy film", "smooth film",
        "cross-processed film", "pushed film", "pulled film", "expired film",
        "vibrant colors", "muted colors", "desaturated colors", "oversaturated colors",
        "monochromatic colors", "duotone colors", "tritone colors", "quadtone colors",
        "complementary colors", "analogous colors", "triadic colors", "tetradic colors",
        "split-complementary colors", "double-split complementary colors", "square colors", "rectangle colors",
        "primary colors", "secondary colors", "tertiary colors", "quaternary colors",
        "warm colors", "cool colors", "neutral colors", "earth colors",
        "pastel colors", "neon colors", "fluorescent colors", "metallic colors",
        "iridescent colors", "pearlescent colors", "translucent colors", "transparent colors",
        "opaque colors", "depth of field", "tilt shift", "bokeh",
        "motion blur", "radial blur", "gaussian blur", "lens blur",
        "defocus", "rack focus", "pull focus", "soft focus",
        "sharp focus", "selective focus", "pan focus", "deep focus",
        "shallow focus", "hyperfocal distance", "beyond hyperfocal", "focal plane",
        "focal point", "focal length", "aperture", "f-stop",
        "wide open", "stopped down", "diffraction", "vignette",
        "natural vignette", "artificial vignette", "light vignette", "dark vignette",
        "lens flare", "lens distortion", "barrel distortion", "pincushion distortion",
        "chromatic aberration", "spherical aberration", "coma", "astigmatism",
        "field curvature", "focus breathing", "lens compression", "lens expansion",
        "perspective distortion", "keystone distortion", "foreshortening", "forced perspective",
        "optical illusion", "anamorphic", "squeezed", "desqueezed",
        "cinemascope", "panavision", "techniscope", "vistavision",
        "full frame", "crop sensor", "medium format", "large format",
        "red camera", "arri camera", "black magic camera", "sony camera",
        "canon camera", "nikon camera", "fujifilm camera", "hasselblad camera",
        "leica camera", "pentax camera", "olympus camera", "panasonic camera",
        "smartphone camera", "action camera", "drone camera", "security camera",
        "webcam", "mirrorless camera", "DSLR camera", "point and shoot camera",
        "16mm film", "35mm film", "65mm film", "70mm film",
        "imax film", "technicolor", "eastman color", "fujicolor",
        "kodachrome", "ektachrome", "velvia", "portra",
        "ilford", "adox", "agfa", "fomapan",
        "raw digital", "jpeg", "tiff", "png",
        "high bit depth", "8-bit", "10-bit", "12-bit",
        "14-bit", "16-bit", "32-bit", "hdr",
        "sdr", "rec709", "rec2020", "aces",
        "srgb", "adobe rgb", "prophoto rgb", "dci-p3",
        "gamma", "log", "linear", "nonlinear",
        "time of day", "time of year", "time of decade", "time of century",
        "time of millennium", "time of era", "time of epoch", "time of eon",
        "time of day", "morning", "noon", "afternoon",
        "evening", "night", "midnight", "dawn",
        "dusk", "spring", "summer", "autumn",
        "winter", "january", "february", "march",
        "april", "may", "june", "july",
        "august", "september", "october", "november",
        "december", "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "sunday",
        "blue hour", "golden hour", "magic hour", "civil twilight",
        "nautical twilight", "astronomical twilight", "full moon", "new moon",
        "waxing moon", "waning moon", "crescent moon", "gibbous moon",
        "quarter moon", "solar eclipse", "lunar eclipse", "meteor shower",
        "aurora borealis", "aurora australis", "zodiacal light", "gegenschein",
        "airglow", "noctilucent clouds", "polar night", "midnight sun",
        "cloudy", "partly cloudy", "clear skies", "overcast",
        "foggy", "misty", "hazy", "smoky",
        "rainy", "drizzly", "pouring", "stormy",
        "thunderstorm", "lightning", "snowy", "sleety",
        "haily", "windy", "breezy", "gusty",
        "gale force winds", "hurricane force winds", "tornadic winds", "calm winds",
        "dry", "humid", "arid", "moist",
        "tropical", "polar", "temperate", "continental",
        "mediterranean", "oceanic", "desert", "semi-arid",
        "rainforest", "jungle", "savanna", "grassland",
        "prairie", "steppe", "tundra", "taiga",
        "boreal forest", "temperate forest", "tropical forest", "deciduous forest",
        "coniferous forest", "mixed forest", "shrubland", "chaparral",
        "wetland", "marsh", "swamp", "bog",
        "fen", "lake", "river", "stream",
        "creek", "brook", "spring", "waterfall",
        "ocean", "sea", "bay", "gulf",
        "strait", "channel", "fjord", "lagoon",
        "beach", "coast", "shore", "dune",
        "cliff", "crag", "mountain", "hill",
        "valley", "canyon", "gorge", "ravine",
        "plain", "plateau", "mesa", "butte",
        "volcano", "crater", "caldera", "geyser",
        "hot spring", "fumarole", "solfatara", "mudpot",
        "cave", "cavern", "grotto", "tunnel",
        "underwater cave", "ice cave", "lava tube", "cenote",
        "sinkhole", "limestone", "sandstone", "granite",
        "basalt", "marble", "slate", "quartz",
        "crystal", "gem", "mineral", "ore",
        "dust", "sand", "clay", "loam",
        "silt", "soil", "dirt", "mud",
        "gravel", "pebble", "cobble", "boulder",
        "rock", "stone", "ore", "mineral",
        "crystal", "gem", "geode", "fossil",
        "petrified", "water", "ice", "snow",
        "sleet", "hail", "rain", "drizzle",
        "mist", "fog", "cloud", "vapor",
        "steam", "smoke", "fire", "flame",
        "ember", "ash", "cinder", "spark",
        "lava", "magma", "obsidian", "pumice",
        "scoria", "tuff", "gas", "air",
        "wind", "breeze", "gust", "gale",
        "hurricane", "tornado", "cyclone", "typhoon",
        "storm", "thunderstorm", "lightning", "thunder",
        "sunrise", "sunset", "moonrise", "moonset",
        "moonlight", "sunlight", "starlight", "skylight",
        "northern lights", "southern lights", "zodiacal light", "airglow",
        "afterglow", "zenith", "horizon", "azimuth",
        "elevation", "altitude", "depth", "height",
        "width", "length", "circumference", "diameter",
        "radius", "area", "volume", "mass",
        "density", "velocity", "acceleration", "friction",
        "momentum", "inertia", "gravity", "anti-gravity",
        "real", "surreal", "imaginary", "fantastical",
        "photographic", "photogrammetric", "photometric", "photorealistic",
        "hyper-realistic", "ultra-realistic", "super-realistic", "mega-realistic",
        "giga-realistic", "tera-realistic", "peta-realistic", "exa-realistic",
        "zetta-realistic", "yotta-realistic", "ronna-realistic", "quetta-realistic",
        "exceptional quality", "superlative quality", "outstanding quality", "excellent quality",
        "magnificent quality", "breathtaking quality", "astonishing quality", "astounding quality",
        "incredible quality", "unbelievable quality", "phenomenal quality", "fantastic quality",
        "magical quality", "miraculous quality", "mythical quality", "legendary quality",
        "unreal quality", "ethereal quality", "divine quality", "heavenly quality",
        "godly quality", "superhuman quality", "extraterrestrial quality", "otherworldly quality",
        "futuristic quality", "timeless quality", "classic quality", "vintage quality",
        "retro quality", "antique quality", "contemporary quality", "modern quality",
        "post-modern quality", "avant-garde quality", "cutting-edge quality", "innovative quality",
        "adaptive quality", "intelligent quality", "sentient quality", "conscious quality",
        "emotive quality", "psychological quality", "philosophical quality", "spiritual quality",
        "religious quality", "sacred quality", "profane quality", "secular quality",
        "cultural quality", "societal quality", "political quality", "economic quality",
        "historical quality", "prehistoric quality", "ancient quality", "medieval quality",
        "renaissance quality", "baroque quality", "rococo quality", "neoclassical quality",
        "romantic quality", "expressionist quality", "impressionist quality", "abstract expressionist quality",
        "cubist quality", "surrealist quality", "dadaist quality", "pop art quality",
        "minimalist quality", "maximalist quality", "conceptual quality", "performative quality",
        "digital quality", "analog quality", "hybrid quality", "synthetic quality",
        "organic quality", "mechanical quality", "electronic quality", "robotic quality",
        "industrial quality", "post-industrial quality", "agricultural quality", "urban quality",
        "rural quality", "suburban quality", "cosmopolitan quality", "metropolitan quality",
        "coastal quality", "inland quality", "continental quality", "insular quality",
        "astronomical quality", "cosmic quality", "galactic quality", "interstellar quality",
        "interplanetary quality", "solar system quality", "planetary quality", "lunar quality",
        "terrestrial quality", "aquatic quality", "marine quality", "fresh water quality",
        "salt water quality", "brackish quality", "aerial quality", "atmospheric quality",
        "stratospheric quality", "mesospheric quality", "thermospheric quality", "exospheric quality",
        "ionospheric quality", "tropospheric quality", "tropopause quality", "stratopause quality",
        "mesopause quality", "thermopause quality", "exopause quality", "interplanetary quality",
        "interstellar quality", "intergalactic quality", "multiversal quality", "multidimensional quality",
        "quantum quality", "subatomic quality", "atomic quality", "molecular quality",
        "cellular quality", "organismal quality", "biotic quality", "abiotic quality",
        "live render", "pre-rendered", "real-time render", "offline render",
        "raytraced", "rasterized", "voxelized", "vectorized",
        "3D model", "2D image", "4D object", "5D object",
        "ultra-high resolution", "super-high resolution", "mega-high resolution", "giga-high resolution",
        "high dynamic range", "super dynamic range", "ultra dynamic range", "extreme dynamic range",
        "realistic light transport", "physically accurate materials", "physically accurate lighting", "physically accurate rendering",
        "physically accurate reflections", "physically accurate refractions", "physically accurate diffusion", "physically accurate absorption",
        "detailed at any scale", "highly coherent", "spatially consistent", "temporally consistent",
        "narrative integrity", "aesthetic integrity", "conceptual integrity", "contextual integrity",
        "historical integrity", "cultural integrity", "scientific integrity", "technical integrity",
        "artistic merit", "technical merit", "conceptual merit", "execution merit",
        "presentation merit", "impact merit", "innovation merit", "communication merit",
        "studio quality lighting", "professional studio equipment", "high-end production value", "expertly lit",
        "masterfully composed", "artistically balanced", "aesthetically pleasing", "visually stunning",
        "eye-catching composition", "captivating imagery", "enthralling visuals", "mesmerizing scene",
        "fascinating subject", "intriguing elements", "compelling narrative", "engaging story",
        "thought-provoking concept", "intellectually stimulating", "emotionally evocative", "spiritually inspiring",
        "technically impressive", "skillfully executed", "expertly crafted", "professionally finished",
        "perfectly proportioned", "mathematically harmonious", "geometrically balanced", "structurally sound",
        "highly detailed", "intricate texturing", "elaborate patterning", "complex structuring",
        "fine workmanship", "precise execution", "meticulous crafting", "careful detailing",
        "highest professional standard", "reference quality", "benchmark quality", "industry standard",
        "award-winning quality", "museum quality", "gallery quality", "collector quality",
        "detailed rendering", "precise modeling", "accurate texturing", "realistic lighting",
        "convincing shading", "believable materials", "authentic appearance", "genuine look",
        "natural feel", "organic quality", "living atmosphere", "dynamic presence",
        "immersive environment", "engrossing experience", "captivating scene", "enthralling moment",
        "masterful execution", "expert technique", "skilled craftsmanship", "professional results",
        "perfect lighting", "ideal exposure", "optimal contrast", "balanced colors",
        "harmonious composition", "rhythmic arrangement", "symphonic structure", "melodic flow",
        "poetic quality", "lyrical beauty", "narrative strength", "dramatic impact",
        "cinematic framing", "theatrical presentation", "performative quality", "expressive power",
        "emotive resonance", "psychological depth", "philosophical insight", "spiritual elevation",
        "cultural relevance", "historical significance", "social commentary", "political statement",
        "anatomical accuracy", "biological correctness", "physical realism", "natural authenticity",
        "extreme detail level", "microscopic precision", "nanoscopic accuracy", "subatomic detailing",
        "visible to atomic scale", "observable at quantum level", "highest possible fidelity", "ultimate resolution",
        "professional color grading", "cinematic color palette", "atmospheric color scheme", "mood-enhancing tones",
        "emotional color temperature", "psychological color impact", "symbolic color usage", "metaphorical color meaning",
        "perfectly balanced exposure", "technically perfect lighting", "masterfully controlled contrast", "expertly managed highlights",
        "professionally handled shadows", "skillfully rendered midtones", "artfully crafted transitions", "seamlessly blended gradients",
        "meticulous attention to detail", "obsessive precision", "perfectionist execution", "comprehensive thoroughness",
        "complete and total realism", "absolute photographic fidelity", "perfect reproduction of reality", "indistinguishable from nature",
        "flawless execution", "impeccable technique", "immaculate rendering", "pristine quality",
        "polished presentation", "refined aesthetic", "sophisticated style", "elegant design",
        "photorealistic rendering", "hyperrealistic visualization", "ultrarealistic representation", "superrealistic depiction",
        "megarealistic illustration", "gigarealistic portrayal", "terarealistic image", "petarealistic picture",
        "intricate details", "elaborate features", "complex textures", "sophisticated patterns",
        "artisan quality", "handcrafted appearance", "bespoke design", "custom creation",
        "premium finish", "luxury quality", "high-end result", "top-tier output",
        "excellent result", "superior outcome", "outstanding achievement", "remarkable accomplishment",
        "exceptional image", "extraordinary picture", "phenomenal rendering", "spectacular visualization",
        "magnificent depiction", "marvelous representation", "wonderful illustration", "glorious portrayal",
        "brilliant execution", "dazzling realization", "stunning manifestation", "astonishing materialization",
        "breathtaking realism", "awe-inspiring detail", "mind-blowing quality", "jaw-dropping fidelity",
        "intensely realistic", "profoundly detailed", "deeply textured", "richly rendered",
        "vividly depicted", "boldly presented", "strongly portrayed", "powerfully conveyed",
        "distinctly visualized", "clearly illustrated", "precisely captured", "accurately represented",
        "faithful reproduction", "truthful depiction", "honest portrayal", "genuine representation",
        "authentic visualization", "legitimate rendering", "lifelike quality", "vitality",
        "dimensionality", "palpability", "tangibility", "substantiality",
        "presence", "immediacy", "vividness", "brightness",
        "clarity", "definition", "resolution", "sharpness",
        "granularity", "specificity", "precision", "exactness",
        "optimal framing", "perfect centering", "ideal cropping", "harmonious composition",
        "rhythmic arrangement", "balanced elements", "proportional design", "symmetric layout",
        "directional energy", "dynamic tension", "visual flow", "compositional movement",
        "artistic interpretation", "creative vision", "imaginative concept", "innovative approach",
        "groundbreaking technique", "revolutionary method", "pioneering style", "trailblazing execution",
        "historical reference", "cultural context", "societal relevance", "political awareness",
        "psychological depth", "emotional resonance", "spiritual dimension", "philosophical underpinning",
        "archival quality", "museum grade", "gallery standard", "curatorial selection",
        "critically acclaimed style", "award-winning approach", "recognized excellence", "acknowledged mastery",
        "creative insight", "artistic intuition", "aesthetic sensibility", "visual intelligence",
        "conceptual sophistication", "intellectual depth", "cognitive complexity", "mental ingenuity",
        "emotional intelligence", "psychological awareness", "spiritual sensitivity", "philosophical understanding",
        "cultural literacy", "historical knowledge", "societal comprehension", "political acumen",
        "scientific accuracy", "technical precision", "mathematical correctness", "logical consistency",
        "empirical validity", "factual basis", "truthful representation", "honest depiction",
        "ethical consideration", "moral awareness", "responsible portrayal", "considerate representation",
        "respectful depiction", "dignified portrayal", "honorable treatment", "principled approach",
        "virtuous execution", "integrity of vision", "truthfulness of representation", "honesty of depiction",
        "authenticity of portrayal", "genuineness of expression", "sincerity of communication", "veracity of statement",
        "absolute realism", "complete verisimilitude", "total naturalism", "perfect mimesis",
        "highest resolution", "maximum detail", "ultimate clarity", "supreme definition",
        "extreme precision", "absolute accuracy", "perfect fidelity", "flawless reproduction",
        "masterful realism", "expert naturalism", "skillful verisimilitude", "accomplished mimesis",
        "professional appearance", "industry standard", "commercial quality", "product grade",
        "editorial standard", "publication quality", "broadcast grade", "theatrical specification",
        "cinematic quality", "film grade", "movie specification", "cinema standard",
        "IMAX quality", "Hollywood standard", "blockbuster grade", "feature film specification",
        "prime time quality", "network standard", "studio grade", "production specification",
        "high production value", "big budget quality", "premium grade", "luxury specification",
        "ultra premium quality", "super luxury grade", "elite specification", "exclusive standard",
        "perfect image quality", "flawless visual standard", "immaculate graphic grade", "pristine picture specification",
        "technically perfect", "mechanically flawless", "functionally immaculate", "operationally pristine",
        "structurally sound", "architecturally solid", "engineeringly robust", "constructionally stable",
        "mathematically precise", "geometrically accurate", "trigonometrically correct", "algebraically sound",
        "physically realistic", "chemically accurate", "biologically correct", "anatomically precise",
        "geologically accurate", "meteorologically correct", "astronomically precise", "cosmologically sound",
        "historically accurate", "chronologically correct", "periodically precise", "epochally sound",
        "culturally authentic", "societally accurate", "communally correct", "tribally precise",
        "linguistically accurate", "grammatically correct", "syntactically precise", "semantically sound",
        "artistically harmonious", "aesthetically balanced", "visually rhythmic", "pictorially melodic",
        "emotionally resonant", "psychologically impactful", "mentally stimulating", "cognitively engaging",
        "spiritually moving", "soulfully touching", "transcendentally elevating", "metaphysically inspiring",
        "physically tangible", "sensually palpable", "bodily perceptible", "materially substantial",
        "realistically detailed", "naturalistically rendered", "truthfully depicted", "faithfully portrayed",
        "authentically visualized", "genuinely represented", "honestly illustrated", "sincerely shown",
        "vividly colorful", "richly chromatic", "deeply saturated", "intensely pigmented",
        "tonally balanced", "chromatically harmonious", "colorimetrically accurate", "spectrally precise",
        "perfect composition", "ideal arrangement", "optimal organization", "supreme structuring",
        "masterful framing", "expert cropping", "skillful positioning", "accomplished placement",
        "professional layout", "industry-standard arrangement", "commercial-grade organization", "product-quality structuring",
        "editorially sound framing", "publication-grade cropping", "broadcast-quality positioning", "theatrical-standard placement",
        "cinematically excellent composition", "film-quality arrangement", "movie-grade organization", "cinema-standard structuring",
        "IMAX-level framing", "Hollywood-quality cropping", "blockbuster-grade positioning", "feature-film-standard placement",
        "prime-time-worthy composition", "network-quality arrangement", "studio-grade organization", "production-standard structuring",
        "high-production-value framing", "big-budget-quality cropping", "premium-grade positioning", "luxury-standard placement",
        "ultra-premium-quality composition", "super-luxury-grade arrangement", "elite-standard organization", "exclusive-quality structuring",
        "perfect lighting", "ideal illumination", "optimal radiosity", "supreme luminosity",
        "masterful shadows", "expert highlights", "skillful midtones", "accomplished contrast",
        "professional exposure", "industry-standard brightness", "commercial-grade darkness", "product-quality balance",
        "editorially perfect lighting", "publication-grade illumination", "broadcast-quality radiosity", "theatrical-standard luminosity",
        "cinematically excellent shadows", "film-quality highlights", "movie-grade midtones", "cinema-standard contrast",
        "IMAX-level exposure", "Hollywood-quality brightness", "blockbuster-grade darkness", "feature-film-standard balance",
        "prime-time-worthy lighting", "network-quality illumination", "studio-grade radiosity", "production-standard luminosity",
        "high-production-value shadows", "big-budget-quality highlights", "premium-grade midtones", "luxury-standard contrast",
        "ultra-premium-quality exposure", "super-luxury-grade brightness", "elite-standard darkness", "exclusive-quality balance",
        "perfect texture", "ideal material", "optimal surface", "supreme substance",
        "masterful detail", "expert intricacy", "skillful complexity", "accomplished elaboration",
        "professional granularity", "industry-standard specificity", "commercial-grade precision", "product-quality exactness",
        "editorially perfect texture", "publication-grade material", "broadcast-quality surface", "theatrical-standard substance",
        "cinematically excellent detail", "film-quality intricacy", "movie-grade complexity", "cinema-standard elaboration",
        "IMAX-level granularity", "Hollywood-quality specificity", "blockbuster-grade precision", "feature-film-standard exactness",
        "prime-time-worthy texture", "network-quality material", "studio-grade surface", "production-standard substance",
        "high-production-value detail", "big-budget-quality intricacy", "premium-grade complexity", "luxury-standard elaboration",
        "ultra-premium-quality granularity", "super-luxury-grade specificity", "elite-standard precision", "exclusive-quality exactness",
        "perfect angle", "ideal perspective", "optimal viewpoint", "supreme position",
        "masterful framing", "expert cropping", "skillful positioning", "accomplished placement",
        "professional alignment", "industry-standard orientation", "commercial-grade direction", "product-quality arrangement",
        "editorially perfect angle", "publication-grade perspective", "broadcast-quality viewpoint", "theatrical-standard position",
        "cinematically excellent framing", "film-quality cropping", "movie-grade positioning", "cinema-standard placement",
        "IMAX-level alignment", "Hollywood-quality orientation", "blockbuster-grade direction", "feature-film-standard arrangement",
        "prime-time-worthy angle", "network-quality perspective", "studio-grade viewpoint", "production-standard position",
        "high-production-value framing", "big-budget-quality cropping", "premium-grade positioning", "luxury-standard placement",
        "ultra-premium-quality alignment", "super-luxury-grade orientation", "elite-standard direction", "exclusive-quality arrangement",
        "perfect focus", "ideal sharpness", "optimal clarity", "supreme definition",
        "masterful resolution", "expert detail", "skillful precision", "accomplished exactness",
        "professional crispness", "industry-standard acuity", "commercial-grade distinctness", "product-quality legibility",
        "editorially perfect focus", "publication-grade sharpness", "broadcast-quality clarity", "theatrical-standard definition",
        "cinematically excellent resolution", "film-quality detail", "movie-grade precision", "cinema-standard exactness",
        "IMAX-level crispness", "Hollywood-quality acuity", "blockbuster-grade distinctness", "feature-film-standard legibility",
        "prime-time-worthy focus", "network-quality sharpness", "studio-grade clarity", "production-standard definition",
        "high-production-value resolution", "big-budget-quality detail", "premium-grade precision", "luxury-standard exactness",
        "ultra-premium-quality crispness", "super-luxury-grade acuity", "elite-standard distinctness", "exclusive-quality legibility",
        "perfect depth", "ideal dimensionality", "optimal volume", "supreme spatiality",
        "masterful perspective", "expert projection", "skillful recession", "accomplished foreshortening",
        "professional stereopsis", "industry-standard parallax", "commercial-grade relief", "product-quality solidity",
        "editorially perfect depth", "publication-grade dimensionality", "broadcast-quality volume", "theatrical-standard spatiality",
        "cinematically excellent perspective", "film-quality projection", "movie-grade recession", "cinema-standard foreshortening",
        "IMAX-level stereopsis", "Hollywood-quality parallax", "blockbuster-grade relief", "feature-film-standard solidity",
        "prime-time-worthy depth", "network-quality dimensionality", "studio-grade volume", "production-standard spatiality",
        "high-production-value perspective", "big-budget-quality projection", "premium-grade recession", "luxury-standard foreshortening",
        "ultra-premium-quality stereopsis", "super-luxury-grade parallax", "elite-standard relief", "exclusive-quality solidity",
        "perfect rendering", "ideal visualization", "optimal representation", "supreme depiction",
        "masterful illustration", "expert portrayal", "skillful realization", "accomplished actualization",
        "professional execution", "industry-standard manifestation", "commercial-grade materialization", "product-quality concretization",
        "editorially perfect rendering", "publication-grade visualization", "broadcast-quality representation", "theatrical-standard depiction",
        "cinematically excellent illustration", "film-quality portrayal", "movie-grade realization", "cinema-standard actualization",
        "IMAX-level execution", "Hollywood-quality manifestation", "blockbuster-grade materialization", "feature-film-standard concretization",
        "prime-time-worthy rendering", "network-quality visualization", "studio-grade representation", "production-standard depiction",
        "high-production-value illustration", "big-budget-quality portrayal", "premium-grade realization", "luxury-standard actualization",
        "ultra-premium-quality execution", "super-luxury-grade manifestation", "elite-standard materialization", "exclusive-quality concretization",
        "perfect quality", "ideal excellence", "optimal superiority", "supreme fineness",
        "masterful craftsmanship", "expert artisanship", "skillful workmanship", "accomplished handwork",
        "professional production", "industry-standard manufacturing", "commercial-grade fabrication", "product-quality construction",
        "editorially perfect quality", "publication-grade excellence", "broadcast-quality superiority", "theatrical-standard fineness",
        "cinematically excellent craftsmanship", "film-quality artisanship", "movie-grade workmanship", "cinema-standard handwork",
        "IMAX-level production", "Hollywood-quality manufacturing", "blockbuster-grade fabrication", "feature-film-standard construction",
        "prime-time-worthy quality", "network-quality excellence", "studio-grade superiority", "production-standard fineness",
        "high-production-value craftsmanship", "big-budget-quality artisanship", "premium-grade workmanship", "luxury-standard handwork",
        "ultra-premium-quality production", "super-luxury-grade manufacturing", "elite-standard fabrication", "exclusive-quality construction",
        "detailed craftsmanship", "fine workmanship", "minute detailing", "intricate fabrication",
        "painstaking crafting", "meticulous construction", "careful manufacturing", "precise making",
        "expert handiwork", "skilled crafting", "artisanal production", "handmade quality",
        "traditional crafting", "modern manufacturing", "contemporary fabrication", "cutting-edge production",
        "historical techniques", "ancient methods", "medieval crafting", "renaissance workmanship",
        "industrial revolution production", "machine age manufacturing", "computer era fabrication", "digital age creation",
        "artisanal quality", "handcrafted excellence", "custom-made superiority", "bespoke fineness",
        "mass-produced precision", "factory-made consistency", "machine-crafted accuracy", "robot-built exactness",
        "human-made character", "machine-made uniformity", "handmade variation", "automated regularity",
        "one-of-a-kind uniqueness", "limited edition rarity", "mass-market ubiquity", "custom variation",
        "high-quality craftsmanship", "superior workmanship", "exceptional detailing", "outstanding fabrication",
        "remarkable construction", "extraordinary manufacturing", "phenomenal production", "incredible making",
        "stunning handiwork", "amazing crafting", "astonishing artisanship", "breathtaking creation",
        "mind-blowing quality", "eye-popping excellence", "jaw-dropping superiority", "head-turning fineness",
        "extremely detailed", "highly intricate", "exceedingly complex", "remarkably elaborate",
        "unbelievably precise", "incredibly accurate", "amazingly exact", "astonishingly specific",
        "perfect photographic quality", "ideal cinema quality", "optimal documentary quality", "supreme reference quality",
        "definitive visual fidelity", "ultimate imagistic realism", "unsurpassed pictorial accuracy", "unexcelled graphic precision",
        "unmatched optical clarity", "unrivaled ocular definition", "peerless visual acuity", "matchless pictorial sharpness",
        "inimitable photographic character", "incomparable cinematic style", "singular documentary approach", "unique reference standard",
        "distinctive visual signature", "characteristic imagistic treatment", "individualistic pictorial handling", "personal graphic touch",
        "creative photographic interpretation", "imaginative cinema visualization", "innovative documentary representation", "original reference presentation",
        "artistic photographic expression", "aesthetic cinema realization", "expressive documentary manifestation", "creative reference actualization",
        "beautiful photographic execution", "gorgeous cinema rendering", "striking documentary depiction", "magnificent reference portrayal",
        "stunning photographic illustration", "spectacular cinema portrayal", "impressive documentary realization", "remarkable reference actualization",
        "extraordinary photographic execution", "exceptional cinema rendering", "outstanding documentary depiction", "phenomenal reference portrayal",
        "hyperdetailed scene", "ultrarealistic environment", "superdetailed setting", "megarealistic surroundings",
        "gigadetailed context", "terarealistic background", "petadetailed foreground", "exarealistic middleground",
        "zettadetailed elements", "yottarealistic components", "ronnarealistic constituents", "quettarealistic features"
    ],
    "landscape": [
        "beautiful vista", "wide panorama", "dramatic sunrise", "breathtaking sunset", "golden hour", 
        "dramatic clouds", "water reflection", "piercing sunlight rays", "long shadows",
        "majestic mountains", "lush green forest", "deep valley", "winding river",
        "mesmerizing waterfall", "thin mist", "light rain", "lightning strike", "arching rainbow",
        "expansive horizon", "rolling hills", "vast plains", "sweeping meadows",
        "towering cliffs", "jagged peaks", "snow-capped mountains", "alpine scenery",
        "forested ridges", "cascading waterfalls", "pristine lake", "crystal clear water",
        "reflective pond", "rippling stream", "babbling brook", "rushing rapids",
        "serene coastline", "rugged shore", "sandy beach", "rocky outcrop",
        "desert dunes", "endless savanna", "tropical oasis", "volcanic landscape",
        "glacial terrain", "arctic tundra", "coral reef", "oceanic view",
        "island paradise", "coastal cliffs", "secluded cove", "hidden valley",
        "canyon depths", "mesa formation", "butte silhouette", "pinnacle rock",
        "natural arch", "cave entrance", "geyser eruption", "hot spring steam",
        "lava flow", "crater view", "canyon vista", "gorge overlook",
        "fjord passage", "glacier front", "ice field", "frozen lake",
        "foggy valley", "misty mountains", "hazy atmosphere", "clear visibility",
        "stormy sky", "thunderhead clouds", "cirrus wisps", "cumulus formations",
        "stratocumulus layers", "nimbus rain clouds", "crepuscular rays", "corona effect",
        "sunburst", "starburst", "sunstar effect", "lens flare",
        "rainbow colors", "aurora display", "zodiacal light", "milky way visible",
        "star trail", "meteor shower", "comet tail", "planetary conjunction",
        "lunar landscape", "full moon rising", "crescent moon", "moonlit scene",
        "twilight ambiance", "dawn colors", "dusk hues", "morning light",
        "afternoon glow", "evening shadow", "night sky", "starry expanse",
        "planetary visibility", "constellation view", "galactic center", "deep space",
        "wilderness expanse", "untamed nature", "pristine environment", "virgin territory",
        "ancient forest", "primeval woodland", "primary growth", "old growth trees",
        "giant redwoods", "massive sequoias", "towering pines", "ancient oaks",
        "bamboo forest", "mangrove swamp", "peat bog", "marshland view",
        "wetland habitat", "estuarine system", "river delta", "alluvial plain",
        "fertile valley", "agricultural vista", "terraced hillside", "vineyard slopes",
        "orchard rows", "lavender fields", "tulip gardens", "sunflower expanse",
        "rice paddies", "wheat fields", "corn maze", "countryside view",
        "rural setting", "farmland vista", "pastoral scene", "bucolic landscape",
        "rustic atmosphere", "idyllic setting", "picturesque view", "scenic overlook",
        "panoramic vista", "wide-angle perspective", "fish-eye distortion", "telephoto compression",
        "drone perspective", "aerial view", "bird's eye view", "worm's eye view",
        "low angle shot", "high angle view", "dutch angle", "straight horizon",
        "rule of thirds composition", "leading lines", "vanishing point", "foreground interest",
        "middle ground detail", "background context", "depth layers", "scene stacking",
        "focus stacking", "exposure blending", "HDR rendering", "bracketed exposure",
        "long exposure water", "motion blur clouds", "star trail capture", "light painting",
        "silhouette effect", "shadow detail", "highlight control", "split lighting",
        "side lighting", "backlight rimming", "front lighting", "overhead lighting",
        "directional light", "diffused light", "reflected light", "refracted light",
        "striated light", "dappled light", "graduated light", "zone lighting",
        "natural color palette", "complementary colors", "analogous hues", "monochromatic scheme",
        "split complementary", "triadic color", "tetradic arrangement", "rgb separation",
        "cmyk values", "pantone matching", "color calibration", "white balance",
        "color temperature", "warm tones", "cool tones", "neutral palette",
        "vibrance adjustment", "saturation control", "hue variation", "tonal contrast",
        "atmospheric perspective", "aerial perspective", "linear perspective", "curvilinear perspective",
        "depth perception", "spatial arrangement", "three-dimensional effect", "stereoscopic depth",
        "parallax view", "focal plane", "focus point", "hyperfocal distance",
        "near-far relationship", "scale reference", "human element", "figure in landscape",
        "indigenous flora", "native plants", "endemic species", "invasive vegetation",
        "botanical variety", "biodiversity representation", "ecosystem depiction", "habitat illustration",
        "wildlife presence", "animal tracks", "bird flight", "insect activity",
        "mammal territory", "reptile habitat", "amphibian environment", "fish domain",
        "seasonal display", "spring bloom", "summer growth", "autumn colors",
        "winter starkness", "vernal change", "estival flourish", "autumnal transition",
        "hibernal dormancy", "growing season", "harvest time", "planting period",
        "dormant phase", "weather conditions", "climate representation", "atmospheric phenomena",
        "temperature indication", "precipitation evidence", "wind effect", "pressure system",
        "thermal variation", "humidity level", "aridity display", "moisture presence",
        "geological formation", "rock strata", "mineral deposits", "fossil record",
        "tectonic evidence", "volcanic activity", "seismic influence", "erosional pattern",
        "depositional feature", "weathering effect", "geomorphological interest", "hydrological system",
        "drainage pattern", "watershed boundary", "catchment area", "water divide",
        "time of day", "solar position", "shadow length", "light quality",
        "blue hour", "golden hour", "magic hour", "midday harsh light",
        "early morning softness", "late afternoon warmth", "gloaming period", "astronomical twilight",
        "civil twilight", "nautical twilight", "diurnal change", "nocturnal aspect",
        "photographic excellence", "tonal richness", "textural detail", "compositional balance",
        "visual harmony", "aesthetic appeal", "emotional resonance", "atmospheric mood",
        "evocative feeling", "sense of place", "genius loci", "environmental context",
        "historical significance", "cultural importance", "social relevance", "economic impact",
        "political boundary", "territorial marker", "ownership indication", "property delineation",
        "conservation status", "protection level", "management regime", "usage designation",
        "recreational value", "tourism potential", "inspirational quality", "meditative aspect",
        "spiritual significance", "religious association", "mythological connection", "legendary status",
        "literary reference", "artistic representation", "cinematic portrayal", "musical evocation",
        "poetic description", "narrative setting", "dramatic backdrop", "theatrical stage",
        "photographic interpretation", "painterly quality", "impressionistic rendering", "expressionistic treatment",
        "realistic depiction", "naturalistic presentation", "documentary approach", "journalistic style",
        "artistic license", "creative interpretation", "imaginative visualization", "innovative representation",
        "traditional view", "classical composition", "romantic vision", "modernist perspective",
        "postmodern deconstruction", "contemporary reimagining", "futuristic projection", "historical reconstruction",
        "geographical accuracy", "topographical precision", "planimetric correctness", "altimetric accuracy",
        "orientation alignment", "cardinal direction", "compass bearing", "azimuthal indication",
        "locational context", "situational awareness", "wayfinding reference", "navigational aid",
        "cartographic representation", "map correlation", "GPS coordination", "GIS integration",
        "remote sensing data", "satellite imagery", "aerial photography", "LiDAR scanning",
        "photogrammetric accuracy", "geometric correction", "spatial resolution", "spectral fidelity",
        "temporal relevance", "historical evolution", "geological time", "ecological succession",
        "environmental change", "climatic shift", "anthropogenic influence", "natural dynamics",
        "scenic beauty", "natural wonder", "landscape marvel", "geographical highlight",
        "environmental treasure", "ecological jewel", "natural heritage", "landscape patrimony",
        "wilderness preservation", "conservation priority", "biodiversity hotspot", "endemic center",
        "habitat protection", "ecological restoration", "environmental remediation", "natural recovery",
        "sustainable management", "responsible stewardship", "ecological balance", "environmental harmony",
        "natural processes", "biological cycling", "geological activity", "hydrological movement",
        "atmospheric interaction", "solar influence", "lunar effect", "cosmic impact",
        "terrestrial dynamics", "aquatic systems", "aerial dimension", "subterranean aspect",
        "microclimatic condition", "mesoclimatic influence", "macroclimatic context", "global climate",
        "regional weather", "local conditions", "site-specific factors", "point-source influence",
        "natural beauty", "scenic wonder", "visual splendor", "optical magnificence",
        "ocular delight", "visual feast", "sensory richness", "perceptual abundance",
        "natural melody", "environmental symphony", "landscape harmony", "geographical composition",
        "terrene arrangement", "earthly configuration", "planetary feature", "global element",
        "continental character", "regional trait", "local distinction", "site-specific uniqueness",
        "physical geography", "human geography", "cultural landscape", "vernacular environment",
        "indigenous relationship", "aboriginal connection", "native association", "historic bond",
        "contemporary usage", "modern utilization", "current application", "present-day function",
        "future potential", "developmental possibility", "evolutionary trajectory", "change prospect",
        "mountain peak", "mountain ridge", "mountain range", "mountain chain",
        "mountain system", "mountain massif", "mountain belt", "mountain arc",
        "volcanic peak", "volcanic cone", "volcanic plug", "volcanic dome",
        "volcanic caldera", "volcanic crater", "volcanic field", "volcanic island",
        "hill summit", "hill slope", "hill crest", "hill brow",
        "hill flank", "hill base", "hill foot", "hill range",
        "plateau surface", "plateau edge", "plateau escarpment", "plateau terrace",
        "mesa top", "mesa side", "mesa rim", "mesa scarp",
        "butte crown", "butte face", "butte talus", "butte base",
        "canyon rim", "canyon wall", "canyon floor", "canyon bend",
        "gorge edge", "gorge side", "gorge bottom", "gorge curve",
        "valley floor", "valley side", "valley head", "valley mouth",
        "valley watershed", "valley divide", "valley tributary", "valley confluence",
        "plain expanse", "plain horizon", "plain vista", "plain stretch",
        "steppe grassland", "steppe horizon", "steppe expanse", "steppe vastness",
        "prairie grassland", "prairie horizon", "prairie vista", "prairie meadow",
        "savanna grassland", "savanna trees", "savanna horizon", "savanna vastness",
        "desert sand", "desert dune", "desert flat", "desert pavement",
        "desert bedrock", "desert outcrop", "desert wash", "desert playa",
        "forest canopy", "forest understory", "forest floor", "forest edge",
        "forest glade", "forest path", "forest clearing", "forest thicket",
        "woodland grove", "woodland copse", "woodland thicket", "woodland fringe",
        "jungle canopy", "jungle understory", "jungle floor", "jungle river",
        "jungle clearing", "jungle path", "jungle density", "jungle edge",
        "rainforest canopy", "rainforest emergents", "rainforest understory", "rainforest floor",
        "tundra plain", "tundra horizon", "tundra pool", "tundra vegetation",
        "tundra permafrost", "tundra polygons", "tundra hummocks", "tundra flowers",
        "wetland marsh", "wetland swamp", "wetland bog", "wetland fen",
        "wetland pool", "wetland channel", "wetland vegetation", "wetland wildlife",
        "river flow", "river bend", "river rapid", "river pool",
        "river gorge", "river canyon", "river waterfall", "river cascade",
        "lake surface", "lake shore", "lake bay", "lake inlet",
        "lake outlet", "lake island", "lake depth", "lake clarity",
        "waterfall drop", "waterfall cascade", "waterfall plunge", "waterfall pool",
        "waterfall mist", "waterfall spray", "waterfall rainbow", "waterfall force",
        "stream flow", "stream bend", "stream riffle", "stream pool",
        "stream bank", "stream bed", "stream source", "stream mouth",
        "creek meander", "creek cascade", "creek ripple", "creek eddy",
        "brook bubble", "brook babble", "brook burble", "brook flow",
        "ocean horizon", "ocean wave", "ocean swell", "ocean surf",
        "ocean tide", "ocean depth", "ocean current", "ocean blue",
        "sea expanse", "sea wave", "sea foam", "sea spray",
        "sea horizon", "sea depth", "sea current", "sea color",
        "coast shoreline", "coast cliff", "coast beach", "coast dune",
        "coast headland", "coast bay", "coast inlet", "coast spit",
        "beach sand", "beach pebble", "beach shell", "beach surf",
        "beach dune", "beach tide", "beach footprint", "beach treasure",
        "cliff face", "cliff edge", "cliff top", "cliff base",
        "cliff strata", "cliff erosion", "cliff cave", "cliff nesting",
        "rock outcrop", "rock formation", "rock strata", "rock layer",
        "rock texture", "rock color", "rock mineral", "rock fossil",
        "cave entrance", "cave passage", "cave chamber", "cave depth",
        "cave stalactite", "cave stalagmite", "cave column", "cave pool",
        "cavern vastness", "cavern height", "cavern echo", "cavern darkness",
        "grotto opening", "grotto interior", "grotto pool", "grotto moss",
        "arch span", "arch support", "arch height", "arch erosion",
        "glacier ice", "glacier crevasse", "glacier serac", "glacier moraine",
        "glacier till", "glacier erratic", "glacier meltwater", "glacier flow",
        "iceberg float", "iceberg mass", "iceberg blue", "iceberg melt",
        "iceberg crack", "iceberg tip", "iceberg underwater", "iceberg danger",
        "snow cover", "snow drift", "snow depth", "snow crystal",
        "snow footprint", "snow track", "snow melt", "snow field",
        "ice sheet", "ice floe", "ice pack", "ice shelf",
        "ice crystal", "ice pattern", "ice thickness", "ice clarity",
        "fog layer", "fog bank", "fog wisp", "fog shroud",
        "fog lifting", "fog descending", "fog swirling", "fog burning",
        "mist rising", "mist clinging", "mist drifting", "mist dissipating",
        "mist morning", "mist evening", "mist valley", "mist mountain",
        "cloud formation", "cloud layer", "cloud mass", "cloud bank",
        "cloud wisp", "cloud billowing", "cloud drifting", "cloud building",
        "cloud thunderhead", "cloud anvil", "cloud mammatus", "cloud cumulus",
        "cloud stratus", "cloud cirrus", "cloud altocumulus", "cloud stratocumulus",
        "cloud nimbostratus", "cloud cumulonimbus", "cloud lenticular", "cloud iridescence",
        "rain shower", "rain downpour", "rain drizzle", "rain mist",
        "rain torrential", "rain gentle", "rain seasonal", "rain tropical",
        "storm approaching", "storm breaking", "storm intensity", "storm passing",
        "storm lightning", "storm thunder", "storm wind", "storm surge",
        "rainbow arch", "rainbow double", "rainbow partial", "rainbow bright",
        "rainbow vivid", "rainbow faint", "rainbow complete", "rainbow segment",
        "lightning strike", "lightning bolt", "lightning fork", "lightning sheet",
        "lightning cloud", "lightning ground", "lightning storm", "lightning night",
        "thunder rumble", "thunder crack", "thunder boom", "thunder roll",
        "thunder distant", "thunder close", "thunder echoing", "thunder fading",
        "wind effect", "wind strength", "wind direction", "wind constancy",
        "wind gust", "wind sustained", "wind variable", "wind seasonal",
        "breeze gentle", "breeze cooling", "breeze steady", "breeze refreshing",
        "gale force", "gale bending", "gale sustained", "gale damaging",
        "hurricane force", "hurricane spiral", "hurricane eye", "hurricane devastation",
        "tornado funnel", "tornado touch-down", "tornado path", "tornado destruction",
        "dust devil", "dust storm", "dust cloud", "dust haze",
        "sand storm", "sand dune", "sand ripple", "sand pattern",
        "hail size", "hail damage", "hail bounce", "hail accumulation",
        "sleet falling", "sleet bouncing", "sleet accumulation", "sleet melting",
        "frost crystal", "frost pattern", "frost coating", "frost sparkle",
        "dew drop", "dew glistening", "dew morning", "dew evaporating",
        "heat wave", "heat mirage", "heat distortion", "heat intensity",
        "cold snap", "cold clarity", "cold preservation", "cold bite",
        "seasonal change", "seasonal color", "seasonal growth", "seasonal decline",
        "season spring", "season summer", "season autumn", "season winter",
        "winter snow", "winter ice", "winter bare", "winter dormant",
        "spring bloom", "spring bud", "spring green", "spring growth",
        "summer lush", "summer vibrant", "summer peak", "summer heat",
        "autumn color", "autumn leaf", "autumn harvest", "autumn transition",
        "morning dew", "morning fog", "morning light", "morning clarity",
        "noon harsh", "noon bright", "noon shadow", "noon heat",
        "afternoon golden", "afternoon warm", "afternoon long-shadow", "afternoon clarity",
        "evening glow", "evening shadow", "evening color", "evening fading",
        "night darkness", "night star", "night moon", "night mystery",
        "dawn breaking", "dawn color", "dawn mist", "dawn promise",
        "dusk fading", "dusk color", "dusk silhouette", "dusk transition",
        "day clear", "day cloudy", "day variable", "day pattern",
        "week cycle", "week change", "week variance", "week pattern",
        "month progression", "month change", "month cycle", "month variation",
        "year seasons", "year cycle", "year change", "year growth",
        "decade evolution", "decade change", "decade development", "decade alteration",
        "century transformation", "century development", "century evolution", "century progression",
        "millennium scale", "millennium view", "millennium perspective", "millennium evolution",
        "epoch evidence", "epoch change", "epoch transition", "epoch development",
        "era indication", "era evolution", "era transition", "era evidence",
        "period marker", "period evidence", "period representation", "period signature",
        "age indication", "age evidence", "age marker", "age signature",
        "eon scale", "eon perspective", "eon evidence", "eon indication",
        "geological time", "geological evidence", "geological marker", "geological signature",
        "historical record", "historical evidence", "historical indication", "historical marker",
        "prehistoric record", "prehistoric evidence", "prehistoric indication", "prehistoric marker",
        "ancient landscape", "ancient formation", "ancient evidence", "ancient structure",
        "primeval scene", "primeval environment", "primeval formation", "primeval structure",
        "primordial landscape", "primordial formation", "primordial environment", "primordial structure",
        "original state", "original condition", "original form", "original structure",
        "pristine environment", "pristine condition", "pristine state", "pristine quality",
        "untouched nature", "untouched condition", "untouched state", "untouched quality",
        "virgin territory", "virgin state", "virgin land", "virgin quality",
        "wilderness extent", "wilderness quality", "wilderness condition", "wilderness value",
        "natural state", "natural condition", "natural quality", "natural value",
        "artificial influence", "artificial change", "artificial alteration", "artificial adaptation",
        "human impact", "human change", "human alteration", "human adaptation",
        "technological influence", "technological change", "technological alteration", "technological adaptation",
        "industrial effect", "industrial change", "industrial alteration", "industrial adaptation",
        "agricultural impact", "agricultural change", "agricultural pattern", "agricultural system",
        "urban effect", "urban expansion", "urban pattern", "urban system",
        "rural character", "rural pattern", "rural system", "rural lifestyle",
        "suburban pattern", "suburban expansion", "suburban character", "suburban system",
        "development impact", "development pattern", "development system", "development character",
        "conservation effect", "conservation area", "conservation status", "conservation value",
        "protection result", "protection area", "protection status", "protection value",
        "management outcome", "management area", "management system", "management value",
        "restoration result", "restoration area", "restoration system", "restoration process",
        "sustainability aspect", "sustainability practice", "sustainability system", "sustainability value",
        "environmental health", "environmental quality", "environmental value", "environmental service",
        "ecological function", "ecological service", "ecological value", "ecological importance",
        "biodiversity level", "biodiversity value", "biodiversity importance", "biodiversity function",
        "geodiversity aspect", "geodiversity value", "geodiversity importance", "geodiversity function",
        "Heritage significance", "heritage value", "heritage importance", "heritage function",
        "cultural meaning", "cultural value", "cultural importance", "cultural function",
        "spiritual significance", "spiritual value", "spiritual importance", "spiritual function",
        "aesthetic quality", "aesthetic value", "aesthetic importance", "aesthetic function",
        "recreational use", "recreational value", "recreational importance", "recreational function",
        "educational aspect", "educational value", "educational importance", "educational function",
        "scientific interest", "scientific value", "scientific importance", "scientific function",
        "economic resource", "economic value", "economic importance", "economic function",
        "political boundary", "political division", "political unit", "political entity",
        "administrative division", "administrative unit", "administrative boundary", "administrative entity",
        "national border", "national territory", "national jurisdiction", "national sovereignty",
        "international boundary", "international border", "international territory", "international jurisdiction",
        "provincial border", "provincial territory", "provincial jurisdiction", "provincial authority",
        "regional boundary", "regional territory", "regional jurisdiction", "regional authority",
        "local limit", "local area", "local jurisdiction", "local authority",
        "property boundary", "property limit", "property extent", "property demarcation",
        "ownership indication", "ownership extent", "ownership boundary", "ownership limit",
        "possession marker", "possession boundary", "possession extent", "possession limit",
        "territorial marker", "territorial boundary", "territorial extent", "territorial limit",
        "jurisdictional line", "jurisdictional boundary", "jurisdictional extent", "jurisdictional limit",
        "traditional territory", "traditional boundary", "traditional extent", "traditional limit",
        "ancestral land", "ancestral territory", "ancestral boundary", "ancestral extent",
        "indigenous domain", "indigenous territory", "indigenous boundary", "indigenous extent",
        "aboriginal land", "aboriginal territory", "aboriginal boundary", "aboriginal extent",
        "native domain", "native territory", "native boundary", "native extent",
        "historical boundary", "historical territory", "historical extent", "historical limit",
        "colonial border", "colonial territory", "colonial extent", "colonial limit",
        "imperial boundary", "imperial territory", "imperial extent", "imperial limit",
        "global view", "global perspective", "global scale", "global context",
        "hemispheric view", "hemispheric perspective", "hemispheric scale", "hemispheric context",
        "continental view", "continental perspective", "continental scale", "continental context",
        "subcontinental view", "subcontinental perspective", "subcontinental scale", "subcontinental context",
        "national view", "national perspective", "national scale", "national context",
        "regional view", "regional perspective", "regional scale", "regional context",
        "local view", "local perspective", "local scale", "local context",
        "site view", "site perspective", "site scale", "site context",
        "planet Earth", "continent Africa", "continent Antarctica", "continent Asia",
        "continent Australia", "continent Europe", "continent North America", "continent South America",
        "ocean Pacific", "ocean Atlantic", "ocean Indian", "ocean Arctic",
        "ocean Southern", "sea Mediterranean", "sea Caribbean", "sea Baltic",
        "sea North", "sea South China", "sea Arabian", "sea Coral",
        "mountain Everest", "mountain K2", "mountain Kilimanjaro", "mountain Denali",
        "mountain Aconcagua", "mountain Elbrus", "mountain Mont Blanc", "mountain Fuji",
        "river Amazon", "river Nile", "river Mississippi", "river Yangtze",
        "river Danube", "river Rhine", "river Thames", "river Ganges",
        "lake Superior", "lake Victoria", "lake Baikal", "lake Tanganyika",
        "lake Caspian", "lake Erie", "lake Geneva", "lake Titicaca",
        "island Greenland", "island New Guinea", "island Borneo", "island Madagascar",
        "island Japan", "island Great Britain", "island Ireland", "island Iceland",
        "desert Sahara", "desert Arabian", "desert Gobi", "desert Kalahari",
        "desert Atacama", "desert Mojave", "desert Great Victoria", "desert Patagonian",
        "forest Amazon", "forest Congo", "forest Taiga", "forest Black",
        "forest Daintree", "forest Bialowieza", "forest Redwood", "forest Sherwood",
        "mountain range Himalayas", "mountain range Andes", "mountain range Rockies", "mountain range Alps",
        "mountain range Appalachians", "mountain range Urals", "mountain range Great Dividing", "mountain range Carpathians",
        "canyon Grand", "canyon Fish River", "canyon Colca", "canyon Copper",
        "canyon Tara", "canyon Blyde River", "canyon Itaimbezinho", "canyon Yarlung Tsangpo",
        "plateau Tibet", "plateau Deccan", "plateau Colorado", "plateau Ethiopian",
        "plateau Altiplano", "plateau Massif Central", "plateau Laurentian", "plateau Kimberley",
        "plain Great", "plain Indo-Gangetic", "plain European", "plain Nullarbor",
        "plain Serengeti", "plain Pampas", "plain Tarim", "plain Sundarbans",
        "delta Nile", "delta Ganges-Brahmaputra", "delta Mississippi", "delta Danube",
        "delta Mekong", "delta Niger", "delta Lena", "delta Pearl River",
        "peninsula Iberian", "peninsula Italian", "peninsula Scandinavian", "peninsula Arabian",
        "peninsula Indian", "peninsula Korean", "peninsula Kamchatka", "peninsula Yucatan",
        "isthmus Panama", "isthmus Suez", "isthmus Kra", "isthmus Tehuantepec",
        "isthmus Corinth", "isthmus Karelian", "isthmus Auckland", "isthmus Chignecto",
        "strait Gibraltar", "strait Bering", "strait Malacca", "strait Dover",
        "strait Magellan", "strait Bass", "strait Bosphorus", "strait Dardanelles",
        "bay Hudson", "bay Bengal", "bay Biscay", "bay Fundy",
        "bay Chesapeake", "bay San Francisco", "bay Tokyo", "bay Naples",
        "archipelago Indonesian", "archipelago Philippine", "archipelago Hawaiian", "archipelago Japanese",
        "archipelago Caribbean", "archipelago Greek", "archipelago Maldives", "archipelago Svalbard",
        "reef Great Barrier", "reef Belize Barrier", "reef Red Sea", "reef New Caledonia Barrier",
        "reef Mesoamerican", "reef Florida", "reef Andros", "reef Saya de Malha",
        "glacier Lambert", "glacier Siachen", "glacier Vatnajökull", "glacier Jostedalsbreen",
        "glacier Aletsch", "glacier Columbia", "glacier Tasman", "glacier Perito Moreno",
        "ice sheet Antarctic", "ice sheet Greenland", "ice cap Arctic", "ice cap Patagonian",
        "ice cap Penny", "ice cap Barnes", "ice cap Vatnajökull", "ice cap Austfonna",
        "waterfall Angel", "waterfall Niagara", "waterfall Victoria", "waterfall Iguazu",
        "waterfall Yosemite", "waterfall Sutherland", "waterfall Jog", "waterfall Detian",
        "volcano Everest", "volcano Kilimanjaro", "volcano Fuji", "volcano Etna",
        "volcano Vesuvius", "volcano Krakatoa", "volcano St. Helens", "volcano Eyjafjallajökull",
        "geyser Strokkur", "geyser Old Faithful", "geyser Grand Geyser", "geyser Castle Geyser",
        "geyser Giant Geyser", "geyser Steamboat Geyser", "geyser Pohutu Geyser", "geyser El Tatio",
        "cave Mammoth", "cave Son Doong", "cave Sarawak Chamber", "cave Krubera",
        "cave Eisriesenwelt", "cave Clearwater", "cave Punkva", "cave Fingal's",
        "wetland Pantanal", "wetland Everglades", "wetland Okavango", "wetland Sundarbans",
        "wetland Camargue", "wetland Iberá", "wetland Kakadu", "wetland Wasur",
        "city New York", "city London", "city Tokyo", "city Mumbai",
        "city Paris", "city Cairo", "city Rio de Janeiro", "city Sydney",
        "landmark Eiffel Tower", "landmark Statue of Liberty", "landmark Taj Mahal", "landmark Pyramids",
        "landmark Colosseum", "landmark Sagrada Familia", "landmark Machu Picchu", "landmark Petra",
        "world heritage Yellowstone", "world heritage Galápagos", "world heritage Serengeti", "world heritage Uluru",
        "world heritage Angkor", "world heritage Bagan", "world heritage Pompeii", "world heritage Lascaux",
        "national park Yellowstone", "national park Yosemite", "national park Serengeti", "national park Kruger",
        "national park Banff", "national park Lake District", "national park Swiss", "national park Fiordland",
        "reserve Masai Mara", "reserve Monteverde", "reserve Galápagos", "reserve Białowieża",
        "reserve Danube Delta", "reserve Great Nicobar", "reserve Sundarbans", "reserve Lagunas de Montebello",
        "biosphere reserve Pantanal", "biosphere reserve Camargue", "biosphere reserve Manu", "biosphere reserve Sian Ka'an",
        "biosphere reserve Berezinsky", "biosphere reserve Yangambi", "biosphere reserve Calakmul", "biosphere reserve Wakatobi",
        "wildlife sanctuary Kaziranga", "wildlife sanctuary Jim Corbett", "wildlife sanctuary Thung Yai", "wildlife sanctuary Manas",
        "wildlife sanctuary Etosha", "wildlife sanctuary Dinder", "wildlife sanctuary El Kala", "wildlife sanctuary Belovezhskaya Pushcha",
        "marine reserve Great Barrier Reef", "marine reserve Galápagos", "marine reserve Chagos", "marine reserve Papahānaumokuākea",
        "marine reserve Ross Sea", "marine reserve Pitcairn Islands", "marine reserve Natural Park of the Coral Sea", "marine reserve Phoenix Islands",
        "geological phenomenon Grand Canyon", "geological phenomenon Victoria Falls", "geological phenomenon Mount Everest", "geological phenomenon Great Barrier Reef",
        "geological phenomenon Northern Lights", "geological phenomenon Giant's Causeway", "geological phenomenon Wave Rock", "geological phenomenon Dead Sea",
        "natural wonder Grand Canyon", "natural wonder Great Barrier Reef", "natural wonder Mount Everest", "natural wonder Victoria Falls",
        "natural wonder Northern Lights", "natural wonder Harbor of Rio de Janeiro", "natural wonder Paricutin", "natural wonder Mount Fuji",
        "landscape feature fjord", "landscape feature mesa", "landscape feature valley", "landscape feature glacier",
        "landscape feature volcano", "landscape feature waterfall", "landscape feature canyon", "landscape feature mountain range",
        "geographic region Sahara", "geographic region Amazon Basin", "geographic region Himalayas", "geographic region Great Plains",
        "geographic region Siberia", "geographic region Outback", "geographic region Patagonia", "geographic region Scandinavia",
        "terrain type mountainous", "terrain type hilly", "terrain type flat", "terrain type undulating",
        "terrain type rugged", "terrain type gentle", "terrain type steep", "terrain type gradual",
        "elevation high", "elevation moderate", "elevation low", "elevation variable",
        "elevation extreme", "elevation gradual", "elevation abrupt", "elevation gentle",
        "slope steep", "slope gentle", "slope moderate", "slope variable",
        "slope uniform", "slope irregular", "slope consistent", "slope inconsistent",
        "aspect north-facing", "aspect south-facing", "aspect east-facing", "aspect west-facing",
        "aspect variable", "aspect uniform", "aspect consistent", "aspect inconsistent",
        "exposition exposed", "exposition sheltered", "exposition partially exposed", "exposition fully exposed",
        "exposition wind-sheltered", "exposition sun-exposed", "exposition shade-sheltered", "exposition weather-exposed",
        "vegetation dense", "vegetation sparse", "vegetation absent", "vegetation varied",
        "vegetation uniform", "vegetation irregular", "vegetation patterned", "vegetation structured",
        "biodiversity high", "biodiversity moderate", "biodiversity low", "biodiversity extreme",
        "biodiversity threatened", "biodiversity protected", "biodiversity endemic", "biodiversity invasive",
        "conservation pristine", "conservation protected", "conservation threatened", "conservation endangered",
        "conservation managed", "conservation restored", "conservation degraded", "conservation lost",
        "human presence absent", "human presence minimal", "human presence moderate", "human presence significant",
        "human presence dominant", "human presence historical", "human presence contemporary", "human presence future",
        "accessibility easy", "accessibility moderate", "accessibility difficult", "accessibility impossible",
        "accessibility seasonal", "accessibility variable", "accessibility consistent", "accessibility inconsistent",
        "visitation high", "visitation moderate", "visitation low", "visitation restricted",
        "visitation seasonal", "visitation variable", "visitation consistent", "visitation inconsistent",
        "tourism developed", "tourism undeveloped", "tourism sustainable", "tourism unsustainable",
        "tourism ecotourism", "tourism mass tourism", "tourism adventure tourism", "tourism cultural tourism",
        "infrastructure present", "infrastructure absent", "infrastructure minimal", "infrastructure significant",
        "infrastructure sustainable", "infrastructure unsustainable", "infrastructure historical", "infrastructure contemporary",
        "development none", "development minimal", "development moderate", "development significant",
        "development sustainable", "development unsustainable", "development planned", "development unplanned",
        "pollution absent", "pollution minimal", "pollution moderate", "pollution significant",
        "pollution air", "pollution water", "pollution soil", "pollution noise",
        "pollution light", "pollution visual", "pollution radioactive", "pollution chemical",
        "agricultural presence absent", "agricultural presence minimal", "agricultural presence moderate", "agricultural presence significant",
        "agricultural presence sustainable", "agricultural presence unsustainable", "agricultural presence traditional", "agricultural presence industrial",
        "forestry presence absent", "forestry presence minimal", "forestry presence moderate", "forestry presence significant",
        "forestry presence sustainable", "forestry presence unsustainable", "forestry presence selective", "forestry presence clear-cut",
        "mining presence absent", "mining presence minimal", "mining presence moderate", "mining presence significant",
        "mining presence historical", "mining presence contemporary", "mining presence open-pit", "mining presence underground",
        "energy production absent", "energy production minimal", "energy production moderate", "energy production significant",
        "energy production renewable", "energy production nonrenewable", "energy production sustainable", "energy production unsustainable",
        "urbanization absent", "urbanization minimal", "urbanization moderate", "urbanization significant",
        "urbanization planned", "urbanization unplanned", "urbanization sustainable", "urbanization unsustainable",
        "industrialization absent", "industrialization minimal", "industrialization moderate", "industrialization significant",
        "industrialization historical", "industrialization contemporary", "industrialization clean", "industrialization polluting",
        "transportation network absent", "transportation network minimal", "transportation network moderate", "transportation network significant",
        "transportation network road", "transportation network rail", "transportation network water", "transportation network air",
        "utility infrastructure absent", "utility infrastructure minimal", "utility infrastructure moderate", "utility infrastructure significant",
        "utility infrastructure water", "utility infrastructure electricity", "utility infrastructure gas", "utility infrastructure telecommunications",
        "land use natural", "land use agricultural", "land use forestry", "land use mining",
        "land use energy", "land use urban", "land use industrial", "land use transportation",
        "ownership public", "ownership private", "ownership communal", "ownership corporate",
        "ownership indigenous", "ownership government", "ownership individual", "ownership institutional",
        "protection status unprotected", "protection status protected", "protection status core", "protection status buffer",
        "protection status transition", "protection status world heritage", "protection status biosphere reserve", "protection status national park",
        "management regime none", "management regime minimal", "management regime moderate", "management regime intensive",
        "management regime sustainable", "management regime unsustainable", "management regime traditional", "management regime contemporary",
        "ecosystem service provisioning", "ecosystem service regulating", "ecosystem service cultural", "ecosystem service supporting",
        "ecosystem service food", "ecosystem service water", "ecosystem service climate", "ecosystem service recreation",
        "cultural significance none", "cultural significance minimal", "cultural significance moderate", "cultural significance high",
        "cultural significance historical", "cultural significance contemporary", "cultural significance religious", "cultural significance spiritual",
        "historical importance none", "historical importance minimal", "historical importance moderate", "historical importance high",
        "historical importance prehistoric", "historical importance ancient", "historical importance medieval", "historical importance modern",
        "geological significance none", "geological significance minimal", "geological significance moderate", "geological significance high",
        "geological significance unique", "geological significance representative", "geological significance rare", "geological significance common",
        "ecological significance none", "ecological significance minimal", "ecological significance moderate", "ecological significance high",
        "ecological significance unique", "ecological significance representative", "ecological significance rare", "ecological significance common",
        "scientific importance none", "scientific importance minimal", "scientific importance moderate", "scientific importance high",
        "scientific importance unique", "scientific importance representative", "scientific importance rare", "scientific importance common",
        "economic value none", "economic value minimal", "economic value moderate", "economic value high",
        "economic value direct", "economic value indirect", "economic value use", "economic value non-use",
        "aesthetic value none", "aesthetic value minimal", "aesthetic value moderate", "aesthetic value high",
        "aesthetic value scenic", "aesthetic value picturesque", "aesthetic value beautiful", "aesthetic value sublime",
        "recreational value none", "recreational value minimal", "recreational value moderate", "recreational value high",
        "recreational value active", "recreational value passive", "recreational value adventure", "recreational value relaxation",
        "educational value none", "educational value minimal", "educational value moderate", "educational value high",
        "educational value formal", "educational value informal", "educational value scientific", "educational value cultural",
        "inspirational value none", "inspirational value minimal", "inspirational value moderate", "inspirational value high",
        "inspirational value artistic", "inspirational value spiritual", "inspirational value emotional", "inspirational value intellectual",
        "spiritual value none", "spiritual value minimal", "spiritual value moderate", "spiritual value high",
        "spiritual value religious", "spiritual value secular", "spiritual value traditional", "spiritual value contemporary",
        "symbolic value none", "symbolic value minimal", "symbolic value moderate", "symbolic value high",
        "symbolic value cultural", "symbolic value national", "symbolic value international", "symbolic value universal",
        "identity value none", "identity value minimal", "identity value moderate", "identity value high",
        "identity value personal", "identity value communal", "identity value regional", "identity value national",
        "bequest value none", "bequest value minimal", "bequest value moderate", "bequest value high",
        "bequest value cultural", "bequest value natural", "bequest value tangible", "bequest value intangible",
        "existence value none", "existence value minimal", "existence value moderate", "existence value high",
        "existence value personal", "existence value communal", "existence value national", "existence value universal",
        "option value none", "option value minimal", "option value moderate", "option value high",
        "option value current", "option value future", "option value certain", "option value uncertain",
        "photogenic quality high", "photogenic quality moderate", "photogenic quality variable", "photogenic quality exceptional",
        "photogenic quality dramatic", "photogenic quality subtle", "photogenic quality consistent", "photogenic quality variable",
        "visual appeal high", "visual appeal moderate", "visual appeal variable", "visual appeal exceptional",
        "visual appeal dramatic", "visual appeal subtle", "visual appeal consistent", "visual appeal variable",
        "scenic beauty high", "scenic beauty moderate", "scenic beauty variable", "scenic beauty exceptional",
        "scenic beauty dramatic", "scenic beauty subtle", "scenic beauty consistent", "scenic beauty variable",
        "landscape photography ideal", "landscape photography challenging", "landscape photography rewarding", "landscape photography frustrating",
        "landscape photography technical", "landscape photography artistic", "landscape photography documentary", "landscape photography creative",
        "landscape composition foreground", "landscape composition middleground", "landscape composition background", "landscape composition layered",
        "landscape composition balanced", "landscape composition asymmetrical", "landscape composition centered", "landscape composition rule-of-thirds",
        "landscape composition leading-lines", "landscape composition s-curve", "landscape composition diagonal", "landscape composition frame-within-frame",
        "landscape composition golden-ratio", "landscape composition triangular", "landscape composition radial", "landscape composition symmetrical",
        "landscape lighting frontlit", "landscape lighting backlit", "landscape lighting sidelit", "landscape lighting rim-lit",
        "landscape lighting diffused", "landscape lighting harsh", "landscape lighting high-contrast", "landscape lighting low-contrast",
        "landscape mood peaceful", "landscape mood dramatic", "landscape mood mysterious", "landscape mood threatening",
        "landscape mood serene", "landscape mood ominous", "landscape mood tranquil", "landscape mood dynamic",
        "landscape atmosphere clear", "landscape atmosphere hazy", "landscape atmosphere foggy", "landscape atmosphere misty",
        "landscape atmosphere smoky", "landscape atmosphere dusty", "landscape atmosphere rainy", "landscape atmosphere snowy",
        "landscape season spring", "landscape season summer", "landscape season autumn", "landscape season winter",
        "landscape weather clear", "landscape weather cloudy", "landscape weather stormy", "landscape weather variable",
        "landscape weather rainy", "landscape weather snowy", "landscape weather foggy", "landscape weather windy",
        "landscape time-of-day dawn", "landscape time-of-day morning", "landscape time-of-day midday", "landscape time-of-day afternoon",
        "landscape time-of-day evening", "landscape time-of-day dusk", "landscape time-of-day night", "landscape time-of-day astronomical",
        "landscape color-scheme monochromatic", "landscape color-scheme analogous", "landscape color-scheme complementary", "landscape color-scheme triadic",
        "landscape color-scheme split-complementary", "landscape color-scheme tetradic", "landscape color-scheme square", "landscape color-scheme neutral",
        "landscape color-palette warm", "landscape color-palette cool", "landscape color-palette neutral", "landscape color-palette vibrant",
        "landscape color-palette muted", "landscape color-palette pastel", "landscape color-palette earthy", "landscape color-palette jewel-toned",
        "landscape texture smooth", "landscape texture rough", "landscape texture variable", "landscape texture contrasting",
        "landscape texture consistent", "landscape texture patterned", "landscape texture random", "landscape texture mixed",
        "landscape pattern regular", "landscape pattern irregular", "landscape pattern random", "landscape pattern mixed",
        "landscape pattern natural", "landscape pattern artificial", "landscape pattern organic", "landscape pattern geometric",
        "landscape line horizontal", "landscape line vertical", "landscape line diagonal", "landscape line curved",
        "landscape line zigzag", "landscape line flowing", "landscape line angular", "landscape line mixed",
        "landscape shape organic", "landscape shape geometric", "landscape shape amorphous", "landscape shape defined",
        "landscape shape angular", "landscape shape rounded", "landscape shape mixed", "landscape shape contrasting",
        "landscape form three-dimensional", "landscape form flat", "landscape form variable", "landscape form contrasting",
        "landscape form dominant", "landscape form recessive", "landscape form harmonious", "landscape form dissonant",
        "landscape scale intimate", "landscape scale small", "landscape scale medium", "landscape scale large",
        "landscape scale vast", "landscape scale variable", "landscape scale contrasting", "landscape scale graduated",
        "landscape perspective linear", "landscape perspective aerial", "landscape perspective atmospheric", "landscape perspective multiple",
        "landscape perspective wide-angle", "landscape perspective telephoto", "landscape perspective normal", "landscape perspective distorted",
        "landscape dimension horizontal", "landscape dimension vertical", "landscape dimension diagonal", "landscape dimension multiple",
        "landscape dimension panoramic", "landscape dimension square", "landscape dimension portrait", "landscape dimension varied",
        "landscape dynamics static", "landscape dynamics fluid", "landscape dynamics evolving", "landscape dynamics cyclical",
        "landscape dynamics chaotic", "landscape dynamics ordered", "landscape dynamics rhythmic", "landscape dynamics arrhythmic",
        "landscape movement frozen", "landscape movement suggested", "landscape movement captured", "landscape movement implied",
        "landscape movement water", "landscape movement vegetation", "landscape movement clouds", "landscape movement wildlife",
        "landscape sound quiet", "landscape sound loud", "landscape sound variable", "landscape sound rhythmic",
        "landscape sound natural", "landscape sound artificial", "landscape sound harmonious", "landscape sound dissonant",
        "landscape smell fresh", "landscape smell pungent", "landscape smell variable", "landscape smell subtle",
        "landscape smell natural", "landscape smell artificial", "landscape smell pleasant", "landscape smell unpleasant",
        "landscape feeling peaceful", "landscape feeling energetic", "landscape feeling threatening", "landscape feeling welcoming",
        "landscape feeling familiar", "landscape feeling exotic", "landscape feeling comfortable", "landscape feeling challenging",
        "landscape response awe", "landscape response fear", "landscape response joy", "landscape response sadness",
        "landscape response excitement", "landscape response calm", "landscape response curiosity", "landscape response indifference",
        "landscape memory childhood", "landscape memory adulthood", "landscape memory collective", "landscape memory individual",
        "landscape memory cultural", "landscape memory historical", "landscape memory recent", "landscape memory distant",
        "landscape association personal", "landscape association cultural", "landscape association historical", "landscape association universal",
        "landscape association positive", "landscape association negative", "landscape association neutral", "landscape association mixed",
        "landscape interpretation literal", "landscape interpretation symbolic", "landscape interpretation metaphorical", "landscape interpretation allegorical",
        "landscape interpretation personal", "landscape interpretation cultural", "landscape interpretation historical", "landscape interpretation universal",
        "landscape representation realistic", "landscape representation impressionistic", "landscape representation expressionistic", "landscape representation abstract",
        "landscape representation naturalistic", "landscape representation stylized", "landscape representation idealized", "landscape representation subjective",
        "landscape narrative explicit", "landscape narrative implicit", "landscape narrative absent", "landscape narrative multilayered",
        "landscape narrative personal", "landscape narrative cultural", "landscape narrative historical", "landscape narrative universal",
        "landscape context geographical", "landscape context ecological", "landscape context cultural", "landscape context historical",
        "landscape context political", "landscape context economic", "landscape context social", "landscape context personal",
        "landscape function ecological", "landscape function agricultural", "landscape function recreational", "landscape function residential",
        "landscape function industrial", "landscape function commercial", "landscape function transportation", "landscape function spiritual",
        "landscape management conservation", "landscape management preservation", "landscape management restoration", "landscape management enhancement",
        "landscape management sustainable-use", "landscape management exploitation", "landscape management abandonment", "landscape management development",
        "landscape change natural", "landscape change human", "landscape change rapid", "landscape change gradual",
        "landscape change cyclical", "landscape change linear", "landscape change reversible", "landscape change irreversible",
        "landscape future preserved", "landscape future enhanced", "landscape future degraded", "landscape future transformed",
        "landscape future sustainable", "landscape future unsustainable", "landscape future balanced", "landscape future imbalanced",
        "landscape vulnerability low", "landscape vulnerability moderate", "landscape vulnerability high", "landscape vulnerability variable",
        "landscape vulnerability decreasing", "landscape vulnerability increasing", "landscape vulnerability stable", "landscape vulnerability unknown",
        "landscape resilience low", "landscape resilience moderate", "landscape resilience high", "landscape resilience variable",
        "landscape resilience decreasing", "landscape resilience increasing", "landscape resilience stable", "landscape resilience unknown",
        "landscape sensitivity low", "landscape sensitivity moderate", "landscape sensitivity high", "landscape sensitivity variable",
        "landscape sensitivity decreasing", "landscape sensitivity increasing", "landscape sensitivity stable", "landscape sensitivity unknown",
        "landscape adaptability low", "landscape adaptability moderate", "landscape adaptability high", "landscape adaptability variable",
        "landscape adaptability decreasing", "landscape adaptability increasing", "landscape adaptability stable", "landscape adaptability unknown",
        "landscape sustainability low", "landscape sustainability moderate", "landscape sustainability high", "landscape sustainability variable",
        "landscape sustainability decreasing", "landscape sustainability increasing", "landscape sustainability stable", "landscape sustainability unknown",
        "landscape priority conservation", "landscape priority restoration", "landscape priority enhancement", "landscape priority sustainable-use",
        "landscape priority development", "landscape priority research", "landscape priority education", "landscape priority recreation",
        "landscape status protected", "landscape status unprotected", "landscape status managed", "landscape status unmanaged",
        "landscape status pristine", "landscape status degraded", "landscape status threatened", "landscape status endangered",
        "landscape designation world-heritage", "landscape designation biosphere-reserve", "landscape designation national-park", "landscape designation nature-reserve",
        "landscape designation wilderness-area", "landscape designation protected-landscape", "landscape designation multiple-use", "landscape designation undesignated",
        "landscape ownership public", "landscape ownership private", "landscape ownership communal", "landscape ownership mixed",
        "landscape ownership indigenous", "landscape ownership government", "landscape ownership individual", "landscape ownership corporate",
        "landscape access public", "landscape access private", "landscape access restricted", "landscape access prohibited",
        "landscape access paid", "landscape access free", "landscape access conditional", "landscape access seasonal",
        "landscape visitation high", "landscape visitation moderate", "landscape visitation low", "landscape visitation none",
        "landscape visitation increasing", "landscape visitation decreasing", "landscape visitation stable", "landscape visitation variable",
        "landscape infrastructure extensive", "landscape infrastructure moderate", "landscape infrastructure minimal", "landscape infrastructure none",
        "landscape infrastructure increasing", "landscape infrastructure decreasing", "landscape infrastructure stable", "landscape infrastructure variable",
        "landscape development extensive", "landscape development moderate", "landscape development minimal", "landscape development none",
"landscape development sustainable", "landscape development unsustainable", "landscape development planned", "landscape development unplanned",
"landscape conservation high", "landscape conservation moderate", "landscape conservation low", "landscape conservation none",
"landscape conservation increasing", "landscape conservation decreasing", "landscape conservation stable", "landscape conservation variable",
"landscape restoration active", "landscape restoration planned", "landscape restoration completed", "landscape restoration none",
"landscape restoration successful", "landscape restoration unsuccessful", "landscape restoration partial", "landscape restoration ongoing",
"landscape preservation active", "landscape preservation planned", "landscape preservation long-term", "landscape preservation temporary",
"landscape preservation successful", "landscape preservation threatened", "landscape preservation partial", "landscape preservation ongoing",
"landscape management active", "landscape management passive", "landscape management adaptive", "landscape management rigid",
"landscape management sustainable", "landscape management unsustainable", "landscape management traditional", "landscape management innovative",
"landscape planning comprehensive", "landscape planning partial", "landscape planning absent", "landscape planning ongoing",
"landscape planning long-term", "landscape planning short-term", "landscape planning strategic", "landscape planning tactical",
"landscape monitoring regular", "landscape monitoring occasional", "landscape monitoring absent", "landscape monitoring comprehensive",
"landscape monitoring partial", "landscape monitoring technical", "landscape monitoring community-based", "landscape monitoring scientific",
"landscape research extensive", "landscape research moderate", "landscape research minimal", "landscape research absent",
"landscape research ongoing", "landscape research completed", "landscape research planned", "landscape research published",
"landscape education extensive", "landscape education moderate", "landscape education minimal", "landscape education absent",
"landscape education formal", "landscape education informal", "landscape education traditional", "landscape education innovative",
"landscape interpretation extensive", "landscape interpretation moderate", "landscape interpretation minimal", "landscape interpretation absent",
"landscape interpretation scientific", "landscape interpretation cultural", "landscape interpretation historical", "landscape interpretation personal",
"landscape visualization realistic", "landscape visualization artistic", "landscape visualization diagrammatic", "landscape visualization symbolic",
"landscape visualization photographic", "landscape visualization cartographic", "landscape visualization three-dimensional", "landscape visualization multi-sensory",
"landscape representation accurate", "landscape representation stylized", "landscape representation symbolic", "landscape representation abstract",
"landscape representation photographic", "landscape representation cartographic", "landscape representation artistic", "landscape representation technical",
"landscape documentation comprehensive", "landscape documentation partial", "landscape documentation minimal", "landscape documentation absent",
"landscape documentation scientific", "landscape documentation cultural", "landscape documentation historical", "landscape documentation personal",
"landscape narrative linear", "landscape narrative cyclic", "landscape narrative complex", "landscape narrative simple",
"landscape narrative historical", "landscape narrative cultural", "landscape narrative ecological", "landscape narrative personal",
"landscape story geological", "landscape story ecological", "landscape story cultural", "landscape story historical",
"landscape story personal", "landscape story mythological", "landscape story fictional", "landscape story factual",
"landscape value ecological", "landscape value cultural", "landscape value historical", "landscape value economic",
"landscape value scientific", "landscape value educational", "landscape value recreational", "landscape value spiritual",
"landscape significance local", "landscape significance regional", "landscape significance national", "landscape significance global",
"landscape significance increasing", "landscape significance decreasing", "landscape significance stable", "landscape significance variable",
"landscape importance ecological", "landscape importance cultural", "landscape importance historical", "landscape importance economic",
"landscape importance scientific", "landscape importance educational", "landscape importance recreational", "landscape importance spiritual",
"landscape uniqueness high", "landscape uniqueness moderate", "landscape uniqueness low", "landscape uniqueness variable",
"landscape uniqueness increasing", "landscape uniqueness decreasing", "landscape uniqueness stable", "landscape uniqueness threatened",
"landscape representativeness high", "landscape representativeness moderate", "landscape representativeness low", "landscape representativeness variable",
"landscape representativeness increasing", "landscape representativeness decreasing", "landscape representativeness stable", "landscape representativeness threatened",
"landscape intactness high", "landscape intactness moderate", "landscape intactness low", "landscape intactness variable",
"landscape intactness increasing", "landscape intactness decreasing", "landscape intactness stable", "landscape intactness threatened",
"landscape authenticity high", "landscape authenticity moderate", "landscape authenticity low", "landscape authenticity variable",
"landscape authenticity increasing", "landscape authenticity decreasing", "landscape authenticity stable", "landscape authenticity threatened",
"landscape integrity high", "landscape integrity moderate", "landscape integrity low", "landscape integrity variable",
"landscape integrity increasing", "landscape integrity decreasing", "landscape integrity stable", "landscape integrity threatened",
"landscape diversity high", "landscape diversity moderate", "landscape diversity low", "landscape diversity variable",
"landscape diversity increasing", "landscape diversity decreasing", "landscape diversity stable", "landscape diversity threatened",
"landscape complexity high", "landscape complexity moderate", "landscape complexity low", "landscape complexity variable",
"landscape complexity increasing", "landscape complexity decreasing", "landscape complexity stable", "landscape complexity simplified",
"landscape heterogeneity high", "landscape heterogeneity moderate", "landscape heterogeneity low", "landscape heterogeneity variable",
"landscape heterogeneity increasing", "landscape heterogeneity decreasing", "landscape heterogeneity stable", "landscape heterogeneity homogenized",
"landscape connectivity high", "landscape connectivity moderate", "landscape connectivity low", "landscape connectivity variable",
"landscape connectivity increasing", "landscape connectivity decreasing", "landscape connectivity stable", "landscape connectivity fragmented",
"landscape continuity high", "landscape continuity moderate", "landscape continuity low", "landscape continuity variable",
"landscape continuity increasing", "landscape continuity decreasing", "landscape continuity stable", "landscape continuity interrupted",
"landscape coherence high", "landscape coherence moderate", "landscape coherence low", "landscape coherence variable",
"landscape coherence increasing", "landscape coherence decreasing", "landscape coherence stable", "landscape coherence disrupted",
"landscape legibility high", "landscape legibility moderate", "landscape legibility low", "landscape legibility variable",
"landscape legibility increasing", "landscape legibility decreasing", "landscape legibility stable", "landscape legibility confused",
"landscape readability high", "landscape readability moderate", "landscape readability low", "landscape readability variable",
"landscape readability increasing", "landscape readability decreasing", "landscape readability stable", "landscape readability obscured",
"landscape mystery high", "landscape mystery moderate", "landscape mystery low", "landscape mystery variable",
"landscape mystery increasing", "landscape mystery decreasing", "landscape mystery stable", "landscape mystery revealed",
"landscape surprise high", "landscape surprise moderate", "landscape surprise low", "landscape surprise variable",
"landscape surprise increasing", "landscape surprise decreasing", "landscape surprise stable", "landscape surprise predictable",
"landscape drama high", "landscape drama moderate", "landscape drama low", "landscape drama variable",
"landscape drama increasing", "landscape drama decreasing", "landscape drama stable", "landscape drama subdued",
"landscape sublimity high", "landscape sublimity moderate", "landscape sublimity low", "landscape sublimity variable",
"landscape sublimity increasing", "landscape sublimity decreasing", "landscape sublimity stable", "landscape sublimity diminished",
"landscape grandeur high", "landscape grandeur moderate", "landscape grandeur low", "landscape grandeur variable",
"landscape grandeur increasing", "landscape grandeur decreasing", "landscape grandeur stable", "landscape grandeur reduced",
"landscape wildness high", "landscape wildness moderate", "landscape wildness low", "landscape wildness variable",
"landscape wildness increasing", "landscape wildness decreasing", "landscape wildness stable", "landscape wildness domesticated",
"landscape naturalness high", "landscape naturalness moderate", "landscape naturalness low", "landscape naturalness variable",
"landscape naturalness increasing", "landscape naturalness decreasing", "landscape naturalness stable", "landscape naturalness artificial",
"landscape remoteness high", "landscape remoteness moderate", "landscape remoteness low", "landscape remoteness variable",
"landscape remoteness increasing", "landscape remoteness decreasing", "landscape remoteness stable", "landscape remoteness accessible",
"landscape solitude high", "landscape solitude moderate", "landscape solitude low", "landscape solitude variable",
"landscape solitude increasing", "landscape solitude decreasing", "landscape solitude stable", "landscape solitude crowded",
"landscape tranquility high", "landscape tranquility moderate", "landscape tranquility low", "landscape tranquility variable",
"landscape tranquility increasing", "landscape tranquility decreasing", "landscape tranquility stable", "landscape tranquility disturbed",
"landscape peace high", "landscape peace moderate", "landscape peace low", "landscape peace variable",
"landscape peace increasing", "landscape peace decreasing", "landscape peace stable", "landscape peace disturbed",
"landscape charm high", "landscape charm moderate", "landscape charm low", "landscape charm variable",
"landscape charm increasing", "landscape charm decreasing", "landscape charm stable", "landscape charm lost",
"landscape romance high", "landscape romance moderate", "landscape romance low", "landscape romance variable",
"landscape romance increasing", "landscape romance decreasing", "landscape romance stable", "landscape romance disenchanted",
"landscape intimacy high", "landscape intimacy moderate", "landscape intimacy low", "landscape intimacy variable",
"landscape intimacy increasing", "landscape intimacy decreasing", "landscape intimacy stable", "landscape intimacy detached",
"landscape familiarity high", "landscape familiarity moderate", "landscape familiarity low", "landscape familiarity variable",
"landscape familiarity increasing", "landscape familiarity decreasing", "landscape familiarity stable", "landscape familiarity strange",
"landscape nostalgia high", "landscape nostalgia moderate", "landscape nostalgia low", "landscape nostalgia variable",
"landscape nostalgia increasing", "landscape nostalgia decreasing", "landscape nostalgia stable", "landscape nostalgia forgotten",
"landscape memory strong", "landscape memory moderate", "landscape memory weak", "landscape memory variable",
"landscape memory increasing", "landscape memory decreasing", "landscape memory stable", "landscape memory forgotten",
"landscape history rich", "landscape history moderate", "landscape history poor", "landscape history variable",
"landscape history revealing", "landscape history hidden", "landscape history continuous", "landscape history interrupted",
"landscape time deep", "landscape time shallow", "landscape time layered", "landscape time compressed",
"landscape time linear", "landscape time cyclic", "landscape time static", "landscape time dynamic",
"landscape change rapid", "landscape change moderate", "landscape change slow", "landscape change variable",
"landscape change linear", "landscape change cyclic", "landscape change random", "landscape change planned",
"landscape evolution natural", "landscape evolution cultural", "landscape evolution mixed", "landscape evolution directed",
"landscape evolution convergent", "landscape evolution divergent", "landscape evolution parallel", "landscape evolution unique",
"landscape dynamics stable", "landscape dynamics unstable", "landscape dynamics equilibrium", "landscape dynamics disequilibrium",
"landscape dynamics steady-state", "landscape dynamics threshold", "landscape dynamics resistant", "landscape dynamics resilient",
"landscape process active", "landscape process passive", "landscape process natural", "landscape process cultural",
"landscape process constructive", "landscape process destructive", "landscape process cyclic", "landscape process linear",
"landscape transformation natural", "landscape transformation cultural", "landscape transformation mixed", "landscape transformation planned",
"landscape transformation gradual", "landscape transformation rapid", "landscape transformation reversible", "landscape transformation irreversible",
"landscape disturbance natural", "landscape disturbance cultural", "landscape disturbance mixed", "landscape disturbance planned",
"landscape disturbance frequent", "landscape disturbance rare", "landscape disturbance intense", "landscape disturbance mild",
"landscape stability high", "landscape stability moderate", "landscape stability low", "landscape stability variable",
"landscape stability increasing", "landscape stability decreasing", "landscape stability cyclic", "landscape stability unpredictable",
"landscape permanence high", "landscape permanence moderate", "landscape permanence low", "landscape permanence variable",
"landscape permanence increasing", "landscape permanence decreasing", "landscape permanence illusory", "landscape permanence genuine",
"landscape ephemeral", "landscape persistent", "landscape fleeting", "landscape enduring",
"landscape momentary", "landscape lasting", "landscape transient", "landscape permanent",
"landscape susceptible", "landscape resistant", "landscape vulnerable", "landscape resilient",
"landscape fragile", "landscape robust", "landscape delicate", "landscape hardy",
"landscape sensitive", "landscape tolerant", "landscape responsive", "landscape adaptive",
"landscape simple", "landscape complex", "landscape uniform", "landscape diverse",
"landscape homogeneous", "landscape heterogeneous", "landscape regular", "landscape irregular",
"landscape ordered", "landscape chaotic", "landscape structured", "landscape unstructured",
"landscape symmetrical", "landscape asymmetrical", "landscape balanced", "landscape unbalanced",
"landscape harmonious", "landscape dissonant", "landscape congruent", "landscape incongruent",
"landscape unified", "landscape fragmented", "landscape coherent", "landscape incoherent",
"landscape open", "landscape enclosed", "landscape exposed", "landscape sheltered",
"landscape vast", "landscape confined", "landscape expansive", "landscape restricted",
"landscape boundless", "landscape bounded", "landscape limitless", "landscape limited",
"landscape horizontal", "landscape vertical", "landscape flat", "landscape rugged",
"landscape smooth", "landscape rough", "landscape even", "landscape uneven",
"landscape gentle", "landscape harsh", "landscape soft", "landscape hard",
"landscape rounded", "landscape angular", "landscape curving", "landscape straight",
"landscape flowing", "landscape static", "landscape dynamic", "landscape inert",
"landscape active", "landscape passive", "landscape energetic", "landscape calm",
"landscape busy", "landscape quiet", "landscape loud", "landscape silent",
"landscape vibrant", "landscape subdued", "landscape lively", "landscape still",
"landscape bright", "landscape dark", "landscape light", "landscape shadow",
"landscape sunny", "landscape cloudy", "landscape clear", "landscape overcast",
"landscape warm", "landscape cool", "landscape hot", "landscape cold",
"landscape dry", "landscape wet", "landscape arid", "landscape humid",
"landscape moist", "landscape parched", "landscape saturated", "landscape desiccated",
"landscape lush", "landscape barren", "landscape fertile", "landscape sterile",
"landscape abundant", "landscape sparse", "landscape rich", "landscape poor",
"landscape diverse", "landscape monotonous", "landscape varied", "landscape uniform",
"landscape colorful", "landscape monochrome", "landscape vibrant", "landscape muted",
"landscape saturated", "landscape desaturated", "landscape contrasting", "landscape harmonious",
"landscape patterned", "landscape plain", "landscape textured", "landscape smooth",
"landscape detailed", "landscape simple", "landscape intricate", "landscape minimal",
"landscape complex", "landscape basic", "landscape elaborate", "landscape elemental",
"landscape ornate", "landscape austere", "landscape decorated", "landscape unadorned",
"landscape layered", "landscape flat", "landscape dimensional", "landscape compressed",
"landscape distant", "landscape close", "landscape remote", "landscape intimate",
"landscape far", "landscape near", "landscape beyond", "landscape immediate",
"landscape foreign", "landscape familiar", "landscape exotic", "landscape indigenous",
"landscape universal", "landscape specific", "landscape global", "landscape local",
"landscape urban", "landscape rural", "landscape suburban", "landscape wild",
"landscape developed", "landscape undeveloped", "landscape cultivated", "landscape uncultivated",
"landscape inhabited", "landscape uninhabited", "landscape populated", "landscape unpopulated",
"landscape busy", "landscape quiet", "landscape crowded", "landscape empty",
"landscape communal", "landscape private", "landscape public", "landscape secret",
"landscape accessible", "landscape inaccessible", "landscape reachable", "landscape unreachable",
"landscape inviting", "landscape forbidding", "landscape welcoming", "landscape threatening",
"landscape safe", "landscape dangerous", "landscape secure", "landscape perilous",
"landscape comfortable", "landscape uncomfortable", "landscape pleasant", "landscape unpleasant",
"landscape healthy", "landscape unhealthy", "landscape vital", "landscape sick",
"landscape clean", "landscape polluted", "landscape pristine", "landscape contaminated",
"landscape pure", "landscape impure", "landscape untainted", "landscape tainted",
"landscape beneficial", "landscape harmful", "landscape helpful", "landscape hurtful",
"landscape useful", "landscape useless", "landscape valuable", "landscape worthless",
"landscape priceless", "landscape worthless", "landscape significant", "landscape insignificant",
"landscape meaningful", "landscape meaningless", "landscape important", "landscape unimportant",
"landscape spiritual", "landscape material", "landscape sacred", "landscape profane",
"landscape holy", "landscape mundane", "landscape divine", "landscape earthly",
"landscape magical", "landscape ordinary", "landscape enchanted", "landscape disenchanted",
"landscape mythical", "landscape real", "landscape legendary", "landscape factual",
"landscape fictional", "landscape actual", "landscape imagined", "landscape concrete",
"landscape symbolic", "landscape literal", "landscape metaphorical", "landscape exact",
"landscape allegorical", "landscape historical", "landscape mythological", "landscape documentarian",
"landscape evocative", "landscape descriptive", "landscape suggestive", "landscape explicit",
"landscape implicit", "landscape obvious", "landscape subtle", "landscape overt",
"landscape striking", "landscape unremarkable", "landscape memorable", "landscape forgettable",
"landscape distinctive", "landscape common", "landscape unique", "landscape generic",
"landscape iconic", "landscape anonymous", "landscape famous", "landscape obscure",
"landscape photogenic", "landscape unphotogenic", "landscape picturesque", "landscape plain",
"landscape painterly", "landscape photographic", "landscape artistic", "landscape documentary",
"landscape beautiful", "landscape ugly", "landscape attractive", "landscape unattractive",
"landscape handsome", "landscape homely", "landscape lovely", "landscape repulsive",
"landscape appealing", "landscape unappealing", "landscape charming", "landscape charmless",
"landscape delightful", "landscape dreary", "landscape pleasant", "landscape unpleasant",
"landscape enjoyable", "landscape unenjoyable", "landscape pleasing", "landscape displeasing",
"landscape satisfying", "landscape unsatisfying", "landscape fulfilling", "landscape unfulfilling",
"landscape engaging", "landscape disengaging", "landscape involving", "landscape uninvolving",
"landscape immersive", "landscape detached", "landscape absorbing", "landscape disconnecting",
"landscape captivating", "landscape boring", "landscape fascinating", "landscape tedious",
"landscape interesting", "landscape uninteresting", "landscape intriguing", "landscape dull",
"landscape exciting", "landscape unexciting", "landscape thrilling", "landscape bland",
"landscape stimulating", "landscape unstimulating", "landscape arousing", "landscape deadening",
"landscape invigorating", "landscape enervating", "landscape energizing", "landscape draining",
"landscape refreshing", "landscape tiring", "landscape rejuvenating", "landscape exhausting",
"landscape restorative", "landscape depletive", "landscape healing", "landscape harming",
"landscape nourishing", "landscape depleting", "landscape sustaining", "landscape unsustaining",
"landscape supportive", "landscape unsupportive", "landscape nurturing", "landscape neglecting",
"landscape comforting", "landscape discomforting", "landscape consoling", "landscape distressing",
"landscape soothing", "landscape disturbing", "landscape calming", "landscape agitating",
"landscape peaceful", "landscape turbulent", "landscape tranquil", "landscape tumultuous",
"landscape serene", "landscape chaotic", "landscape placid", "landscape stormy",
"landscape quiet", "landscape noisy", "landscape silent", "landscape loud",
"landscape restful", "landscape restless", "landscape still", "landscape active",
"landscape motionless", "landscape moving", "landscape static", "landscape dynamic",
"landscape stable", "landscape unstable", "landscape steady", "landscape fluctuating",
"landscape constant", "landscape variable", "landscape consistent", "landscape inconsistent",
"landscape predictable", "landscape unpredictable", "landscape regular", "landscape irregular",
"landscape ordered", "landscape disordered", "landscape structured", "landscape unstructured",
"landscape organized", "landscape disorganized", "landscape systematic", "landscape unsystematic",
"landscape methodical", "landscape random", "landscape patterned", "landscape patternless",
"landscape rhythmic", "landscape arrhythmic", "landscape metric", "landscape ametric",
"landscape harmonic", "landscape disharmonic", "landscape melodic", "landscape unmelodic",
"landscape symphonic", "landscape cacophonic", "landscape orchestral", "landscape discordant",
"landscape balanced", "landscape unbalanced", "landscape proportional", "landscape disproportional",
"landscape symmetrical", "landscape asymmetrical", "landscape even", "landscape uneven",
"landscape unified", "landscape disunified", "landscape integrated", "landscape disintegrated",
"landscape coherent", "landscape incoherent", "landscape congruent", "landscape incongruent",
"landscape consistent", "landscape inconsistent", "landscape harmonious", "landscape disharmonious",
"landscape compatible", "landscape incompatible", "landscape complementary", "landscape contradictory",
"landscape synergistic", "landscape antagonistic", "landscape cooperative", "landscape uncooperative",
"landscape collaborative", "landscape uncollaborative", "landscape collective", "landscape individual",
"landscape communal", "landscape personal", "landscape shared", "landscape private",
"landscape public", "landscape private", "landscape common", "landscape exclusive",
"landscape open", "landscape closed", "landscape accessible", "landscape inaccessible",
"landscape inclusive", "landscape exclusive", "landscape welcoming", "landscape unwelcoming",
"landscape hospitable", "landscape inhospitable", "landscape friendly", "landscape unfriendly",
"landscape inviting", "landscape uninviting", "landscape appealing", "landscape unappealing",
"landscape attractive", "landscape unattractive", "landscape beautiful", "landscape ugly",
"landscape lovely", "landscape unlovely", "landscape pleasant", "landscape unpleasant",
"landscape agreeable", "landscape disagreeable", "landscape enjoyable", "landscape unenjoyable",
"landscape delightful", "landscape dreadful", "landscape wonderful", "landscape terrible",
"landscape fantastic", "landscape horrific", "landscape marvelous", "landscape monstrous",
"landscape spectacular", "landscape unremarkable", "landscape sensational", "landscape ordinary",
"landscape extraordinary", "landscape ordinary", "landscape special", "landscape common",
"landscape unique", "landscape generic", "landscape distinctive", "landscape indistinctive",
"landscape characteristic", "landscape uncharacteristic", "landscape typical", "landscape atypical",
"landscape representative", "landscape unrepresentative", "landscape exemplary", "landscape unexemplary",
"landscape ideal", "landscape nonideal", "landscape perfect", "landscape imperfect",
"landscape flawless", "landscape flawed", "landscape spotless", "landscape spotted",
"landscape pristine", "landscape defiled", "landscape immaculate", "landscape contaminated",
"landscape pure", "landscape impure", "landscape clean", "landscape dirty",
"landscape hygienic", "landscape unhygienic", "landscape sanitary", "landscape unsanitary",
"landscape healthy", "landscape unhealthy", "landscape wholesome", "landscape unwholesome",
"landscape nourishing", "landscape toxic", "landscape nutritious", "landscape poisonous",
"landscape safe", "landscape dangerous", "landscape secure", "landscape insecure",
"landscape protected", "landscape unprotected", "landscape defended", "landscape undefended",
"landscape guarded", "landscape unguarded", "landscape shielded", "landscape unshielded",
"landscape sheltered", "landscape exposed", "landscape covered", "landscape uncovered",
"landscape hidden", "landscape visible", "landscape concealed", "landscape revealed",
"landscape obscured", "landscape apparent", "landscape masked", "landscape unmasked",
"landscape veiled", "landscape unveiled", "landscape shrouded", "landscape bare",
"landscape clothed", "landscape naked", "landscape dressed", "landscape undressed",
"landscape decorated", "landscape undecorated", "landscape adorned", "landscape unadorned",
"landscape embellished", "landscape unembellished", "landscape ornate", "landscape plain",
"landscape fancy", "landscape simple", "landscape elaborate", "landscape basic",
"landscape complex", "landscape elementary", "landscape complicated", "landscape straightforward",
"landscape intricate", "landscape uncomplicated", "landscape sophisticated", "landscape unsophisticated",
"landscape advanced", "landscape primitive", "landscape developed", "landscape undeveloped",
"landscape evolved", "landscape unevolved", "landscape progressive", "landscape regressive",
"landscape forward", "landscape backward", "landscape cutting-edge", "landscape traditional",
"landscape innovative", "landscape conventional", "landscape original", "landscape derivative",
"landscape creative", "landscape uncreative", "landscape imaginative", "landscape unimaginative",
"landscape inspired", "landscape uninspired", "landscape artistic", "landscape inartistic",
"landscape aesthetic", "landscape unaesthetic", "landscape beautiful", "landscape unbeautiful",
"landscape elevated", "landscape base", "landscape noble", "landscape ignoble",
"landscape dignified", "landscape undignified", "landscape majestic", "landscape unmajestic",
"landscape grand", "landscape modest", "landscape magnificent", "landscape ordinary",
"landscape splendid", "landscape plain", "landscape glorious", "landscape inglorious",
"landscape sumptuous", "landscape meager", "landscape opulent", "landscape austere",
"landscape luxurious", "landscape spartan", "landscape rich", "landscape poor",
"landscape wealthy", "landscape impoverished", "landscape abundant", "landscape scarce",
"landscape plentiful", "landscape sparse", "landscape copious", "landscape meager",
"landscape bountiful", "landscape barren", "landscape fertile", "landscape infertile",
"landscape productive", "landscape unproductive", "landscape fruitful", "landscape fruitless",
"landscape yielding", "landscape unyielding", "landscape giving", "landscape taking",
"landscape generous", "landscape miserly", "landscape liberal", "landscape conservative",
"landscape open", "landscape closed", "landscape accessible", "landscape inaccessible",
"landscape available", "landscape unavailable", "landscape obtainable", "landscape unobtainable",
"landscape attainable", "landscape unattainable", "landscape reachable", "landscape unreachable",
"landscape touchable", "landscape untouchable", "landscape tangible", "landscape intangible",
"landscape concrete", "landscape abstract", "landscape physical", "landscape metaphysical",
"landscape material", "landscape immaterial", "landscape corporeal", "landscape incorporeal",
"landscape substantial", "landscape insubstantial", "landscape solid", "landscape fluid",
"landscape liquid", "landscape gaseous", "landscape dense", "landscape sparse",
"landscape compact", "landscape diffuse", "landscape concentrated", "landscape diluted",
"landscape heavy", "landscape light", "landscape weighty", "landscape weightless",
"landscape massive", "landscape tiny", "landscape enormous", "landscape minuscule",
"landscape gigantic", "landscape small", "landscape colossal", "landscape diminutive",
"landscape huge", "landscape little", "landscape vast", "landscape narrow",
"landscape wide", "landscape constricted", "landscape broad", "landscape limited",
"landscape extensive", "landscape restricted", "landscape expansive", "landscape constrained",
"landscape boundless", "landscape bounded", "landscape infinite", "landscape finite",
"landscape eternal", "landscape temporal", "landscape everlasting", "landscape ephemeral",
"landscape permanent", "landscape temporary", "landscape enduring", "landscape transient",
"landscape lasting", "landscape fleeting", "landscape abiding", "landscape passing",
"landscape persistent", "landscape momentary", "landscape continuous", "landscape discontinuous",
"landscape unbroken", "landscape broken", "landscape intact", "landscape fractured",
"landscape whole", "landscape partial", "landscape complete", "landscape incomplete",
"landscape full", "landscape empty", "landscape filled", "landscape vacant",
"landscape occupied", "landscape unoccupied", "landscape inhabited", "landscape uninhabited",
"landscape populated", "landscape unpopulated", "landscape crowded", "landscape deserted",
"landscape busy", "landscape quiet", "landscape active", "landscape inactive",
"landscape lively", "landscape still", "landscape dynamic", "landscape static",
"landscape energetic", "landscape lethargic", "landscape vibrant", "landscape dormant",
"landscape awake", "landscape asleep", "landscape alert", "landscape drowsy",
"landscape attentive", "landscape inattentive", "landscape observant", "landscape unobservant",
"landscape aware", "landscape unaware", "landscape conscious", "landscape unconscious",
"landscape sentient", "landscape nonsentient", "landscape responsive", "landscape unresponsive",
"landscape reactive", "landscape unreactive", "landscape sensitive", "landscape insensitive",
"landscape feeling", "landscape unfeeling", "landscape emotional", "landscape unemotional",
"landscape passionate", "landscape dispassionate", "landscape ardent", "landscape indifferent",
"landscape caring", "landscape uncaring", "landscape loving", "landscape unloving",
"landscape nurturing", "landscape neglecting", "landscape supportive", "landscape unsupportive",
"landscape helpful", "landscape unhelpful", "landscape beneficial", "landscape harmful",
"landscape useful", "landscape useless", "landscape valuable", "landscape valueless",
"landscape worthy", "landscape unworthy", "landscape deserving", "landscape undeserving",
"landscape meritorious", "landscape unmeritorious", "landscape praiseworthy", "landscape blameworthy",
"landscape commendable", "landscape reprehensible", "landscape laudable", "landscape deplorable",
"landscape admirable", "landscape contemptible", "landscape respectable", "landscape disreputable",
"landscape honorable", "landscape dishonorable", "landscape estimable", "landscape disestimable",
"landscape noble", "landscape ignoble", "landscape virtuous", "landscape vicious",
"landscape good", "landscape bad", "landscape excellent", "landscape poor",
"landscape superior", "landscape inferior", "landscape superlative", "landscape substandard",
"landscape exceptional", "landscape unexceptional", "landscape extraordinary", "landscape ordinary",
"landscape remarkable", "landscape unremarkable", "landscape noteworthy", "landscape unnoteworthy",
"landscape significant", "landscape insignificant", "landscape important", "landscape unimportant",
"landscape meaningful", "landscape meaningless", "landscape purposeful", "landscape purposeless",
"landscape intentional", "landscape unintentional", "landscape deliberate", "landscape accidental",
"landscape planned", "landscape unplanned", "landscape designed", "landscape undesigned",
"landscape created", "landscape evolved", "landscape made", "landscape grown",
"landscape built", "landscape developed", "landscape constructed", "landscape formed",
"landscape artificial", "landscape natural", "landscape synthetic", "landscape organic",
"landscape manufactured", "landscape wild", "landscape fabricated", "landscape spontaneous",
"landscape controlled", "landscape uncontrolled", "landscape managed", "landscape unmanaged",
"landscape regulated", "landscape unregulated", "landscape governed", "landscape ungoverned",
"landscape ordered", "landscape disordered", "landscape structured", "landscape unstructured",
"landscape organized", "landscape disorganized", "landscape systematic", "landscape chaotic",
"landscape methodical", "landscape random", "landscape patterned", "landscape patternless",
"landscape regular", "landscape irregular", "landscape symmetric", "landscape asymmetric",
"landscape balanced", "landscape unbalanced", "landscape proportional", "landscape disproportional",
"landscape harmonious", "landscape disharmonious", "landscape concordant", "landscape discordant",
"landscape consonant", "landscape dissonant", "landscape melodious", "landscape unmelodious",
"landscape rhythmic", "landscape arrhythmic", "landscape metric", "landscape ametric",
"landscape flowing", "landscape halting", "landscape smooth", "landscape rough",
"landscape easy", "landscape difficult", "landscape effortless", "landscape labored",
"landscape natural", "landscape forced", "landscape spontaneous", "landscape constrained",
"landscape free", "landscape restricted", "landscape liberated", "landscape confined",
"landscape independent", "landscape dependent", "landscape autonomous", "landscape controlled",
"landscape self-determined", "landscape other-determined", "landscape voluntary", "landscape involuntary",
"landscape intentional", "landscape unintentional", "landscape deliberate", "landscape accidental",
"landscape conscious", "landscape unconscious", "landscape aware", "landscape unaware",
"landscape mindful", "landscape mindless", "landscape thoughtful", "landscape thoughtless",
"landscape considerate", "landscape inconsiderate", "landscape careful", "landscape careless",
"landscape precise", "landscape imprecise", "landscape exact", "landscape inexact",
"landscape accurate", "landscape inaccurate", "landscape correct", "landscape incorrect",
"landscape true", "landscape false", "landscape real", "landscape fake",
"landscape authentic", "landscape inauthentic", "landscape genuine", "landscape counterfeit",
"landscape original", "landscape copy", "landscape innovative", "landscape derivative",
"landscape creative", "landscape imitative", "landscape inventive", "landscape uninventive",
"landscape imaginative", "landscape unimaginative", "landscape visionary", "landscape conventional",
"landscape progressive", "landscape regressive", "landscape advancing", "landscape retreating",
"landscape evolving", "landscape devolving", "landscape improving", "landscape deteriorating",
"landscape developing", "landscape declining", "landscape growing", "landscape shrinking",
"landscape expanding", "landscape contracting", "landscape enlarging", "landscape diminishing",
"landscape increasing", "landscape decreasing", "landscape rising", "landscape falling",
"landscape ascending", "landscape descending", "landscape climbing", "landscape sinking",
"landscape upward", "landscape downward", "landscape skyward", "landscape earthward",
"landscape heavenward", "landscape hellward", "landscape uphill", "landscape downhill",
"landscape mountainous", "landscape flat", "landscape hilly", "landscape level",
"landscape elevated", "landscape depressed", "landscape raised", "landscape lowered",
"landscape high", "landscape low", "landscape tall", "landscape short",
"landscape towering", "landscape squat", "landscape soaring", "landscape stunted",
"landscape lofty", "landscape humble", "landscape noble", "landscape base",
"landscape grand", "landscape modest", "landscape magnificent", "landscape meager",
"landscape splendid", "landscape plain", "landscape opulent", "landscape austere",
"landscape luxuriant", "landscape sparse", "landscape rich", "landscape poor",
"landscape abundant", "landscape scarce", "landscape plentiful", "landscape meager",
"landscape bountiful", "landscape barren", "landscape fertile", "landscape infertile",
"landscape fecund", "landscape sterile", "landscape productive", "landscape unproductive",
"landscape fruitful", "landscape fruitless", "landscape yielding", "landscape unyielding",
"landscape generous", "landscape miserly", "landscape giving", "landscape taking",
"landscape nurturing", "landscape depleting", "landscape sustaining", "landscape exhausting",
"landscape supporting", "landscape undermining", "landscape upholding", "landscape undercutting",
"landscape reinforcing", "landscape weakening", "landscape strengthening", "landscape debilitating",
"landscape empowering", "landscape disempowering", "landscape enabling", "landscape disabling",
"landscape facilitating", "landscape impeding", "landscape helping", "landscape hindering",
"landscape assisting", "landscape obstructing", "landscape aiding", "landscape blocking",
"landscape allowing", "landscape preventing", "landscape permitting", "landscape prohibiting",
"landscape welcoming", "landscape rejecting", "landscape including", "landscape excluding",
"landscape embracing", "landscape shunning", "landscape accepting", "landscape refusing",
"landscape receiving", "landscape rejecting", "landscape admitting", "landscape denying",
"landscape hospitable", "landscape inhospitable", "landscape accommodating", "landscape unaccommodating",
"landscape friendly", "landscape unfriendly", "landscape kind", "landscape unkind",
"landscape gentle", "landscape harsh", "landscape mild", "landscape severe",
"landscape soft", "landscape hard", "landscape tender", "landscape tough",
"landscape delicate", "landscape rough", "landscape fine", "landscape coarse",
"landscape smooth", "landscape abrasive", "landscape polished", "landscape unpolished",
"landscape refined", "landscape unrefined", "landscape cultured", "landscape uncultured",
"landscape civilized", "landscape uncivilized", "landscape sophisticated", "landscape unsophisticated",
"landscape advanced", "landscape primitive", "landscape developed", "landscape undeveloped",
"landscape modern", "landscape ancient", "landscape contemporary", "landscape antiquated",
"landscape current", "landscape obsolete", "landscape new", "landscape old",
"landscape fresh", "landscape stale", "landscape novel", "landscape familiar",
"landscape innovative", "landscape traditional", "landscape original", "landscape conventional",
"landscape unique", "landscape common", "landscape distinctive", "landscape ordinary",
"landscape special", "landscape usual", "landscape extraordinary", "landscape everyday",
"landscape exceptional", "landscape typical", "landscape unusual", "landscape normal",
"landscape remarkable", "landscape unremarkable", "landscape notable", "landscape unnoteworthy",
"landscape memorable", "landscape forgettable", "landscape unforgettable", "landscape ephemeral",
"landscape eternal", "landscape temporary", "landscape enduring", "landscape fleeting",
"landscape permanent", "landscape transient", "landscape everlasting", "landscape momentary",
"landscape immortal", "landscape mortal", "landscape deathless", "landscape perishable",
"landscape undying", "landscape dying", "landscape inextinguishable", "landscape extinguishable",
"landscape indestructible", "landscape destructible", "landscape imperishable", "landscape perishable",
"landscape abiding", "landscape passing", "landscape persistent", "landscape temporary",
"landscape constant", "landscape variable", "landscape steady", "landscape fluctuating",
"landscape stable", "landscape unstable", "landscape fixed", "landscape mobile",
"landscape stationary", "landscape moving", "landscape static", "landscape dynamic",
"landscape calm", "landscape turbulent", "landscape peaceful", "landscape tumultuous",
"landscape serene", "landscape chaotic", "landscape placid", "landscape stormy",
"landscape tranquil", "landscape agitated", "landscape quiet", "landscape noisy",
"landscape silent", "landscape loud", "landscape still", "landscape active",
"landscape restful", "landscape restless", "landscape relaxing", "landscape stressful",
"landscape soothing", "landscape disturbing", "landscape comforting", "landscape discomforting",
"landscape consoling", "landscape distressing", "landscape reassuring", "landscape alarming",
"landscape encouraging", "landscape discouraging", "landscape heartening", "landscape disheartening",
"landscape uplifting", "landscape depressing", "landscape inspiring", "landscape uninspiring",
"landscape motivating", "landscape demotivating", "landscape stimulating", "landscape unstimulating",
"landscape energizing", "landscape enervating", "landscape invigorating", "landscape debilitating",
"landscape refreshing", "landscape exhausting", "landscape rejuvenating", "landscape depleting",
"landscape vitalizing", "landscape devitalizing", "landscape revitalizing", "landscape devitalizing",
"landscape regenerative", "landscape degenerative", "landscape healing", "landscape harmful",
"landscape therapeutic", "landscape toxic", "landscape healthy", "landscape unhealthy",
"landscape wholesome", "landscape unwholesome", "landscape nourishing", "landscape poisonous",
"landscape nutritious", "landscape deleterious", "landscape beneficial", "landscape detrimental",
"landscape advantageous", "landscape disadvantageous", "landscape favorable", "landscape unfavorable",
"landscape helpful", "landscape harmful", "landscape useful", "landscape useless",
"landscape valuable", "landscape worthless", "landscape precious", "landscape valueless",
"landscape priceless", "landscape costless", "landscape invaluable", "landscape irrelevant",
"landscape indispensable", "landscape dispensable", "landscape essential", "landscape inessential",
"landscape necessary", "landscape unnecessary", "landscape vital", "landscape trivial",
"landscape crucial", "landscape incidental", "landscape critical", "landscape peripheral",
"landscape central", "landscape marginal", "landscape core", "landscape tangential",
"landscape fundamental", "landscape superficial", "landscape profound", "landscape shallow",
"landscape deep", "landscape surface", "landscape thoughtful", "landscape thoughtless",
"landscape meaningful", "landscape meaningless", "landscape significant", "landscape insignificant",
"landscape important", "landscape unimportant", "landscape impressive", "landscape unimpressive",
"landscape striking", "landscape unremarkable", "landscape outstanding", "landscape ordinary",
"landscape exceptional", "landscape average", "landscape extraordinary", "landscape commonplace",
"landscape superb", "landscape mediocre", "landscape excellent", "landscape adequate",
"landscape superior", "landscape inferior", "landscape supreme", "landscape subordinate",
"landscape transcendent", "landscape immanent", "landscape elevated", "landscape lowly",
"landscape high", "landscape low", "landscape noble", "landscape common",
"landscape majestic", "landscape modest", "landscape grand", "landscape simple",
"landscape magnificent", "landscape unadorned", "landscape splendid", "landscape plain",
"landscape glorious", "landscape ordinary", "landscape sumptuous", "landscape austere",
"landscape luxurious", "landscape spartan", "landscape opulent", "landscape frugal",
"landscape lavish", "landscape economical", "landscape extravagant", "landscape restrained",
"landscape excessive", "landscape moderate", "landscape exuberant", "landscape reserved",
"landscape flamboyant", "landscape understated", "landscape ornate", "landscape simple",
"landscape elaborate", "landscape plain", "landscape intricate", "landscape straightforward",
"landscape complex", "landscape uncomplicated", "landscape sophisticated", "landscape unsophisticated",
"landscape advanced", "landscape basic", "landscape cutting-edge", "landscape traditional",
"landscape progressive", "landscape conservative", "landscape innovative", "landscape conventional",
"landscape original", "landscape derivative", "landscape creative", "landscape imitative",
"landscape imaginative", "landscape unimaginative", "landscape inspired", "landscape uninspired",
"landscape visionary", "landscape conformist", "landscape revolutionary", "landscape reactionary",
"landscape radical", "landscape moderate", "landscape extreme", "landscape temperate",
"landscape intense", "landscape mild", "landscape powerful", "landscape weak",
"landscape strong", "landscape feeble", "landscape mighty", "landscape puny",
"landscape formidable", "landscape insignificant", "landscape imposing", "landscape unimposing",
"landscape impressive", "landscape unimpressive", "landscape commanding", "landscape unassuming",
"landscape authoritative", "landscape submissive", "landscape dominant", "landscape recessive",
"landscape prominent", "landscape obscure", "landscape conspicuous", "landscape inconspicuous",
"landscape noticeable", "landscape unnoticeable", "landscape obvious", "landscape subtle",
"landscape apparent", "landscape inapparent", "landscape evident", "landscape obscure",
"landscape clear", "landscape unclear", "landscape distinct", "landscape indistinct",
"landscape definite", "landscape indefinite", "landscape precise", "landscape vague",
"landscape explicit", "landscape implicit", "landscape stated", "landscape unstated",
"landscape expressed", "landscape unexpressed", "landscape articulated", "landscape inarticulated",
"landscape voiced", "landscape unvoiced", "landscape spoken", "landscape unspoken",
"landscape verbal", "landscape nonverbal", "landscape written", "landscape unwritten",
"landscape recorded", "landscape unrecorded", "landscape documented", "landscape undocumented",
"landscape preserved", "landscape unpreserved", "landscape conserved", "landscape unconserved",
"landscape protected", "landscape unprotected", "landscape safeguarded", "landscape unsafeguarded",
"landscape defended", "landscape undefended", "landscape secured", "landscape unsecured",
"landscape safe", "landscape unsafe", "landscape harmless", "landscape harmful",
"landscape benign", "landscape malign", "landscape beneficent", "landscape maleficent",
"landscape benevolent", "landscape malevolent", "landscape friendly", "landscape hostile",
"landscape welcoming", "landscape unwelcoming", "landscape hospitable", "landscape inhospitable",
"landscape accommodating", "landscape unaccommodating", "landscape comfortable", "landscape uncomfortable",
"landscape cozy", "landscape uncozy", "landscape homely", "landscape unhomely",
"landscape domestic", "landscape wild", "landscape civilized", "landscape uncivilized",
"landscape cultured", "landscape uncultured", "landscape cultivated", "landscape uncultivated",
"landscape tamed", "landscape untamed", "landscape domesticated", "landscape undomesticated",
"landscape controlled", "landscape uncontrolled", "landscape managed", "landscape unmanaged",
"landscape regulated", "landscape unregulated", "landscape ordered", "landscape disordered",
"landscape organized", "landscape disorganized", "landscape systematic", "landscape unsystematic",
"landscape methodical", "landscape haphazard", "landscape careful", "landscape careless",
"landscape meticulous", "landscape sloppy", "landscape precise", "landscape imprecise",
"landscape exact", "landscape inexact", "landscape accurate", "landscape inaccurate",
"landscape correct", "landscape incorrect", "landscape proper", "landscape improper",
"landscape appropriate", "landscape inappropriate", "landscape suitable", "landscape unsuitable",
"landscape fitting", "landscape unfitting", "landscape becoming", "landscape unbecoming",
"landscape seemly", "landscape unseemly", "landscape decorous", "landscape indecorous",
"landscape tasteful", "landscape tasteless", "landscape elegant", "landscape inelegant",
"landscape graceful", "landscape ungraceful", "landscape refined", "landscape unrefined",
"landscape sophisticated", "landscape unsophisticated", "landscape cultured", "landscape uncultured",
"landscape polished", "landscape unpolished", "landscape smooth", "landscape rough",
"landscape gentle", "landscape harsh", "landscape soft", "landscape hard",
"landscape tender", "landscape tough", "landscape delicate", "landscape sturdy",
"landscape sensitive", "landscape insensitive", "landscape responsive", "landscape unresponsive",
"landscape adaptable", "landscape unadaptable", "landscape flexible", "landscape inflexible",
"landscape adjustable", "landscape unadjustable", "landscape accommodating", "landscape unaccommodating",
"landscape compromising", "landscape uncompromising", "landscape yielding", "landscape unyielding",
"landscape pliable", "landscape rigid", "landscape malleable", "landscape fixed",
"landscape fluid", "landscape solid", "landscape flowing", "landscape static",
"landscape dynamic", "landscape stable", "landscape changing", "landscape unchanging",
"landscape evolving", "landscape stagnant", "landscape developing", "landscape immobile",
"landscape growing", "landscape static", "landscape expanding", "landscape contracting",
"landscape increasing", "landscape decreasing", "landscape augmenting", "landscape diminishing",
"landscape enhancing", "landscape detracting", "landscape improving", "landscape deteriorating",
"landscape advancing", "landscape retreating", "landscape progressing", "landscape regressing",
"landscape elevating", "landscape lowering", "landscape uplifting", "landscape depressing",
"landscape inspiring", "landscape uninspiring", "landscape encouraging", "landscape discouraging",
"landscape motivating", "landscape demotivating", "landscape stimulating", "landscape unstimulating",
"landscape energizing", "landscape enervating", "landscape exciting", "landscape boring",
"landscape thrilling", "landscape dull", "landscape exhilarating", "landscape tedious",
"landscape invigorating", "landscape exhausting", "landscape refreshing", "landscape tiring",
"landscape rejuvenating", "landscape aging", "landscape youthful", "landscape aged",
"landscape young", "landscape old", "landscape new", "landscape ancient",
"landscape modern", "landscape traditional", "landscape contemporary", "landscape historical",
"landscape current", "landscape past", "landscape present", "landscape future",
"landscape becoming", "landscape fading", "landscape emerging", "landscape disappearing",
"landscape developing", "landscape declining", "landscape growing", "landscape shrinking",
"landscape rising", "landscape falling", "landscape ascending", "landscape descending",
"landscape dominant", "landscape recessive", "landscape primary", "landscape secondary",
"landscape central", "landscape peripheral", "landscape focal", "landscape marginal",
"landscape essential", "landscape nonessential", "landscape critical", "landscape noncritical",
"landscape vital", "landscape nonvital", "landscape decisive", "landscape indecisive",
"landscape influential", "landscape uninfluential", "landscape powerful", "landscape powerless",
"landscape commanding", "landscape submissive", "landscape controlling", "landscape controlled",
"landscape directing", "landscape directed", "landscape leading", "landscape following",
"landscape guiding", "landscape guided", "landscape navigating", "landscape navigated",
"landscape steering", "landscape steered", "landscape piloting", "landscape piloted",
"landscape governing", "landscape governed", "landscape ruling", "landscape ruled",
"landscape managing", "landscape managed", "landscape administering", "landscape administered",
"landscape presiding", "landscape presided", "landscape supervising", "landscape supervised",
"landscape overseeing", "landscape overseen", "landscape monitoring", "landscape monitored",
"landscape observing", "landscape observed", "landscape watching", "landscape watched",
"landscape seeing", "landscape seen", "landscape perceiving", "landscape perceived",
"landscape sensing", "landscape sensed", "landscape feeling", "landscape felt",
"landscape touching", "landscape touched", "landscape reaching", "landscape reached",
"landscape grasping", "landscape grasped", "landscape holding", "landscape held",
"landscape containing", "landscape contained", "landscape including", "landscape included",
"landscape encompassing", "landscape encompassed", "landscape embracing", "landscape embraced",
"landscape encircling", "landscape encircled", "landscape surrounding", "landscape surrounded",
"landscape enclosing", "landscape enclosed", "landscape confining", "landscape confined",
"landscape limiting", "landscape limited", "landscape restricting", "landscape restricted",
"landscape constraining", "landscape constrained", "landscape binding", "landscape bound",
"landscape connecting", "landscape connected", "landscape linking", "landscape linked",
"landscape joining", "landscape joined", "landscape uniting", "landscape united",
"landscape bonding", "landscape bonded", "landscape fusing", "landscape fused",
"landscape integrating", "landscape integrated", "landscape incorporating", "landscape incorporated",
"landscape assimilating", "landscape assimilated", "landscape absorbing", "landscape absorbed",
"landscape consuming", "landscape consumed", "landscape devouring", "landscape devoured",
"landscape engulfing", "landscape engulfed", "landscape overwhelming", "landscape overwhelmed",
"landscape dominating", "landscape dominated", "landscape controlling", "landscape controlled",
"landscape conquering", "landscape conquered", "landscape defeating", "landscape defeated",
"landscape overpowering", "landscape overpowered", "landscape subduing", "landscape subdued",
"landscape taming", "landscape tamed", "landscape domesticating", "landscape domesticated",
"landscape civilizing", "landscape civilized", "landscape cultivating", "landscape cultivated",
"landscape educating", "landscape educated", "landscape enlightening", "landscape enlightened",
"landscape illuminating", "landscape illuminated", "landscape clarifying", "landscape clarified",
"landscape explaining", "landscape explained", "landscape expressing", "landscape expressed",
"landscape articulating", "landscape articulated", "landscape communicating", "landscape communicated",
"landscape transmitting", "landscape transmitted", "landscape conveying", "landscape conveyed",
"landscape transferring", "landscape transferred", "landscape exchanging", "landscape exchanged",
"landscape sharing", "landscape shared", "landscape giving", "landscape given",
"landscape receiving", "landscape received", "landscape accepting", "landscape accepted",
"landscape rejecting", "landscape rejected", "landscape denying", "landscape denied",
"landscape affirming", "landscape affirmed", "landscape asserting", "landscape asserted",
"landscape declaring", "landscape declared", "landscape proclaiming", "landscape proclaimed",
"landscape announcing", "landscape announced", "landscape stating", "landscape stated",
"landscape pronouncing", "landscape pronounced", "landscape saying", "landscape said",
"landscape speaking", "landscape spoken", "landscape telling", "landscape told",
"landscape narrating", "landscape narrated", "landscape describing", "landscape described",
"landscape depicting", "landscape depicted", "landscape representing", "landscape represented",
"landscape symbolizing", "landscape symbolized", "landscape signifying", "landscape signified",
"landscape meaning", "landscape meant", "landscape intending", "landscape intended",
"landscape suggesting", "landscape suggested", "landscape implying", "landscape implied",
"landscape indicating", "landscape indicated", "landscape showing", "landscape shown",
"landscape exhibiting", "landscape exhibited", "landscape displaying", "landscape displayed",
"landscape revealing", "landscape revealed", "landscape exposing", "landscape exposed",
"landscape disclosing", "landscape disclosed", "landscape uncovering", "landscape uncovered",
"landscape discovering", "landscape discovered", "landscape finding", "landscape found",
"landscape locating", "landscape located", "landscape identifying", "landscape identified",
"landscape recognizing", "landscape recognized", "landscape knowing", "landscape known",
"landscape understanding", "landscape understood", "landscape comprehending", "landscape comprehended",
"landscape grasping", "landscape grasped", "landscape realizing", "landscape realized",
"landscape appreciating", "landscape appreciated", "landscape valuing", "landscape valued",
"landscape cherishing", "landscape cherished", "landscape treasuring", "landscape treasured",
"landscape prizing", "landscape prized", "landscape loving", "landscape loved",
"landscape adoring", "landscape adored", "landscape worshipping", "landscape worshipped",
"landscape revering", "landscape revered", "landscape venerating", "landscape venerated",
"landscape respecting", "landscape respected", "landscape honoring", "landscape honored",
"landscape admiring", "landscape admired", "landscape marveling", "landscape marveled",
"landscape wondering", "landscape wondered", "landscape amazing", "landscape amazed",
"landscape astonishing", "landscape astonished", "landscape astounding", "landscape astounded",
"landscape magnificent landscape", "landscape resplendent vista", "landscape breathtaking scenery", "landscape awe-inspiring view",
"landscape spectacular panorama", "landscape stunning horizon", "landscape majestic terrain", "landscape grand expanse",
"landscape picturesque scene", "landscape idyllic setting", "landscape pristine wilderness", "landscape unspoiled nature",
"landscape natural wonder", "landscape geographical marvel", "landscape ecological treasure", "landscape environmental jewel",
"landscape scenic beauty", "landscape visual splendor", "landscape aesthetic perfection", "landscape photographic paradise",
"landscape painter's dream", "landscape artist's inspiration", "landscape photographer's delight", "landscape traveler's reward",
"landscape explorer's discovery", "landscape adventurer's prize", "landscape wanderer's joy", "landscape seeker's fulfillment",
"landscape naturalist's heaven", "landscape ecologist's laboratory", "landscape geologist's classroom", "landscape botanist's garden",
"landscape zoologist's habitat", "landscape biologist's ecosystem", "landscape conservationist's priority", "landscape preservationist's mission",
"landscape environmentalist's concern", "landscape activist's cause", "landscape scientist's study", "landscape researcher's site",
"landscape academic's subject", "landscape student's learning", "landscape teacher's example", "landscape professor's field",
"landscape historian's record", "landscape archaeologist's excavation", "landscape anthropologist's context", "landscape sociologist's setting",
"landscape psychologist's therapy", "landscape therapist's treatment", "landscape healer's medicine", "landscape doctor's prescription",
"landscape patient's recovery", "landscape sufferer's relief", "landscape troubled's peace", "landscape stressed's calm",
"landscape anxious's tranquility", "landscape depressed's uplift", "landscape sad's joy", "landscape unhappy's delight",
"landscape discontented's satisfaction", "landscape unsatisfied's fulfillment", "landscape unfulfilled's completion", "landscape empty's filling",
"landscape lonely's company", "landscape isolated's connection", "landscape separated's union", "landscape divided's wholeness",
"landscape broken's healing", "landscape damaged's repair", "landscape injured's recovery", "landscape hurt's comfort",
"landscape pained's soothing", "landscape agonized's relief", "landscape tortured's release", "landscape tormented's freedom",
"landscape imprisoned's liberation", "landscape confined's expansion", "landscape restricted's openness", "landscape limited's vastness",
"landscape small's enlargement", "landscape diminished's growth", "landscape reduced's increase", "landscape decreased's amplification",
"landscape lessened's enhancement", "landscape weakened's strengthening", "landscape enfeebled's empowerment", "landscape powerless's energy",
"landscape helpless's capability", "landscape incapable's ability", "landscape unable's possibility", "landscape impossible's potential",
"landscape improbable's chance", "landscape unlikely's opportunity", "landscape uncertain's surety", "landscape doubtful's confidence",
"landscape hesitant's decisiveness", "landscape indecisive's determination", "landscape wavering's steadfastness", "landscape unstable's stability",
"landscape unsteady's balance", "landscape unbalanced's equilibrium", "landscape disequilibrium's harmony", "landscape disharmonious's accordance",
"landscape discordant's melody", "landscape tuneless's music", "landscape silent's sound", "landscape soundless's noise",
"landscape noiseless's disturbance", "landscape undisturbed's interruption", "landscape uninterrupted's continuity", "landscape discontinuous's flow",
"landscape blocked's movement", "landscape static's dynamism", "landscape motionless's activity", "landscape inactive's action",
"landscape passive's engagement", "landscape disengaged's involvement", "landscape uninvolved's participation", "landscape excluded's inclusion",
"landscape outside's entrance", "landscape external's internality", "landscape peripheral's centrality", "landscape marginal's importance",
"landscape unimportant's significance", "landscape insignificant's prominence", "landscape inconspicuous's noticeability", "landscape unnoticeable's visibility",
"landscape invisible's appearance", "landscape unseen's sighting", "landscape unobserved's observation", "landscape unwitnessed's witness",
"landscape untestified's testimony", "landscape unreported's report", "landscape undocumented's documentation", "landscape unrecorded's record",
"landscape unpreserved's preservation", "landscape unconserved's conservation", "landscape unprotected's protection", "landscape unsaved's salvation",
"landscape unredeemed's redemption", "landscape unforgiven's forgiveness", "landscape unreconciled's reconciliation", "landscape unharmonized's harmony",
"landscape unpeaceful's peace", "landscape disturbed's tranquility", "landscape agitated's calm", "landscape excited's serenity",
"landscape enthusiastic's quietude", "landscape passionate's stillness", "landscape emotional's equilibrium", "landscape sentimental's balance",
"landscape romantic's pragmatism", "landscape idealistic's realism", "landscape unrealistic's actuality", "landscape intangible's tangibility",
"landscape abstract's concreteness", "landscape theoretical's practicality", "landscape conceptual's materiality", "landscape immaterial's substance",
"landscape insubstantial's solidity", "landscape ethereal's groundedness", "landscape spiritual's physicality", "landscape otherworldly's earthiness",
"landscape heavenly's earthliness", "landscape divine's humanity", "landscape godly's mortality", "landscape immortal's temporality",
"landscape eternal's transience", "landscape everlasting's ephemerality", "landscape permanent's impermanence", "landscape enduring's momentariness",
"landscape lasting's briefness", "landscape continuous's interruption", "landscape unbroken's fracture", "landscape whole's fragmentation",
"landscape united's division", "landscape connected's separation", "landscape related's disconnection", "landscape associated's dissociation",
"landscape linked's detachment", "landscape attached's severance", "landscape bonded's breakage", "landscape cemented's cracking",
"landscape fused's splitting", "landscape melded's separation", "landscape merged's division", "landscape combined's segregation",
"landscape integrated's disintegration", "landscape unified's fragmentation", "landscape coordinated's disorganization", "landscape organized's chaos",
"landscape structured's randomness", "landscape ordered's confusion", "landscape systematic's haphazardness", "landscape methodical's carelessness",
"landscape careful's negligence", "landscape attentive's inattention", "landscape focused's distraction", "landscape concentrated's dispersion",
"landscape gathered's scattering", "landscape collected's dispersal", "landscape accumulated's distribution", "landscape centralized's decentralization",
"landscape dense's sparseness", "landscape compact's diffusion", "landscape compressed's expansion", "landscape contracted's dilation",
"landscape constricted's enlargement", "landscape narrowed's widening", "landscape reduced's augmentation", "landscape decreased's increase",
"landscape diminished's enhancement", "landscape lessened's improvement", "landscape worsened's betterment", "landscape deteriorated's amelioration",
"landscape damaged's restoration", "landscape harmed's healing", "landscape injured's recovery", "landscape wounded's cure",
"landscape sick's health", "landscape ill's wellness", "landscape diseased's vitality", "landscape infected's purity",
"landscape contaminated's cleanliness", "landscape polluted's pristineness", "landscape dirty's cleanliness", "landscape soiled's freshness",
"landscape stained's spotlessness", "landscape blemished's flawlessness", "landscape flawed's perfectness", "landscape imperfect's ideality",
"landscape ideal landscape", "landscape perfect vista", "landscape flawless scenery", "landscape pristine view"
    ],
    "portrait": [
        "perfect portrait angle", "professional portrait lens", "natural bokeh", "shallow depth of field",
        "natural facial expression", "focused gaze", "natural skin details",
        "flowing hair", "soft front lighting", "Rembrandt lighting",
        "natural smile", "best facial angle", "smooth skin texture", "long eyelashes",
        "glossy lips", "defined jawline", "slender neck", "prominent cheekbones",
        "expressive eyes", "captivating gaze", "penetrating look", "mesmerizing stare",
        "soulful expression", "emotional depth", "genuine emotion", "authentic feeling",
        "candid moment", "unposed naturalness", "spontaneous capture", "unaffected charm",
        "relaxed posture", "comfortable stance", "confident pose", "elegant positioning",
        "graceful poise", "dignified bearing", "noble carriage", "regal stance",
        "classic portraiture", "timeless style", "ageless beauty", "enduring appeal",
        "photogenic features", "harmonious proportions", "balanced composition", "golden ratio facial structure",
        "perfect symmetry", "pleasing asymmetry", "distinctive features", "unique characteristics",
        "strong character", "personality evident", "identity clear", "individuality expressed",
        "inner beauty", "outer beauty", "radiant complexion", "glowing skin",
        "luminous quality", "ethereal presence", "magnetic charisma", "compelling aura",
        "powerful presence", "commanding attention", "arresting quality", "striking appearance",
        "memorable face", "unforgettable countenance", "remarkable visage", "extraordinary physiognomy",
        "classical beauty", "contemporary style", "modern aesthetic", "current fashion",
        "trendy look", "fashionable appearance", "stylish presentation", "chic portrayal",
        "elegant simplicity", "minimalist approach", "uncluttered background", "clean composition",
        "dramatic contrast", "subtle gradation", "nuanced tonality", "refined color palette",
        "rich color", "vibrant hue", "saturated tone", "intense chromatic value",
        "complementary colors", "harmonious palette", "balanced tones", "coordinated shades",
        "monochromatic elegance", "duotone sophistication", "split-tone refinement", "color-graded perfection",
        "film-like quality", "analog aesthetic", "digital precision", "hybrid approach",
        "painterly effect", "photographic realism", "artistic interpretation", "creative vision",
        "studio polish", "environmental context", "location authenticity", "setting relevance",
        "architectural framing", "natural framing", "geometric composition", "organic arrangement",
        "formal portrait", "informal capture", "official documentation", "personal memento",
        "professional headshot", "casual snapshot", "corporate image", "social media profile",
        "dating app photo", "family portrait", "friendship capture", "relationship moment",
        "milestone documentation", "life event record", "special occasion", "everyday moment",
        "childhood innocence", "adolescent awkwardness", "adult confidence", "elderly wisdom",
        "youthful energy", "mature stability", "ageless grace", "timeless presence",
        "masculine strength", "feminine grace", "androgynous appeal", "gender-fluid presentation",
        "cultural context", "ethnic heritage", "traditional elements", "contemporary interpretation",
        "regional influence", "global perspective", "local character", "universal appeal",
        "historical reference", "modern sensibility", "period accuracy", "timeless quality",
        "vintage style", "retro aesthetic", "classic approach", "innovative technique",
        "conventional portraiture", "experimental approach", "traditional method", "avant-garde style",
        "conservative presentation", "progressive vision", "mainstream appeal", "alternative perspective",
        "commercial quality", "artistic merit", "technical excellence", "creative distinction",
        "professional standard", "amateur charm", "expert execution", "enthusiast passion",
        "master craftsmanship", "journeyman skill", "apprentice effort", "beginner luck",
        "perfect timing", "decisive moment", "critical juncture", "pivotal second",
        "morning freshness", "midday clarity", "evening warmth", "night mystery",
        "dawn softness", "dusk romance", "daylight neutrality", "artificial illumination",
        "natural light", "studio lighting", "window light", "doorway illumination",
        "north light", "south exposure", "east brightness", "west glow",
        "single light source", "multiple light setup", "main and fill", "key and kicker",
        "hard light", "soft diffusion", "direct illumination", "indirect reflection",
        "dramatic shadow", "subtle shading", "deep contrast", "gentle gradation",
        "chiaroscuro effect", "low-key mood", "high-key brightness", "mid-tone balance",
        "rim lighting", "hair light", "catch light", "eye sparkle",
        "specular highlight", "diffused softness", "graduated shadow", "feathered edge",
        "sharp focus", "selective blur", "tilt-shift effect", "lensbaby distortion",
        "wide aperture", "narrow depth", "full-frame look", "medium format quality",
        "35mm perspective", "telephoto compression", "wide-angle view", "normal lens naturalness",
        "85mm portrait", "105mm clarity", "135mm separation", "200mm isolation",
        "macro detail", "environmental context", "close-up intimacy", "distant objectivity",
        "eye-level equality", "high angle dominance", "low angle power", "dutch tilt dynamism",
        "direct gaze", "averted eyes", "profile elegance", "three-quarter view",
        "frontal presentation", "rear mystique", "over-the-shoulder intimacy", "from-below heroism",
        "candid authenticity", "posed perfection", "spontaneous charm", "calculated effect",
        "genuine smile", "practiced pose", "natural expression", "directed emotion",
        "relaxed demeanor", "attentive presence", "engaged interaction", "detached observation",
        "joyful countenance", "thoughtful contemplation", "serious concentration", "playful attitude",
        "professional appearance", "casual naturalness", "formal presentation", "informal charm",
        "business attire", "casual clothing", "traditional costume", "contemporary fashion",
        "minimalist styling", "elaborate decoration", "simple accessorizing", "complex ornamentation",
        "subdued palette", "vibrant coloration", "monochromatic scheme", "complementary contrast",
        "matching coordination", "deliberate clash", "harmonious blend", "striking juxtaposition",
        "clean simplicity", "rich complexity", "spare elegance", "abundant detail",
        "classic hairstyle", "contemporary cut", "traditional arrangement", "innovative styling",
        "natural texture", "styled perfection", "tousled casualness", "sleek formality",
        "no makeup look", "dramatic cosmetics", "subtle enhancement", "theatrical effect",
        "bare-faced honesty", "artistic expression", "natural beauty", "created illusion",
        "authentic character", "constructed persona", "genuine identity", "crafted image",
        "real person", "idealized representation", "truthful depiction", "flattering interpretation",
        "warts-and-all realism", "airbrushed perfection", "documentary approach", "commercial polish",
        "journalistic authenticity", "advertising idealism", "reportage rawness", "marketing sleekness",
        "fine art quality", "social media readiness", "gallery presentation", "online sharing",
        "print publication", "digital display", "physical exhibition", "virtual viewing",
        "analog film grain", "digital smoothness", "hybrid processing", "mixed media approach",
        "chemical development", "electronic rendering", "traditional printing", "computational imaging",
        "darkroom crafting", "lightroom editing", "physical manipulation", "digital enhancement",
        "hand-made quality", "software precision", "artisanal process", "automated workflow",
        "one-of-a-kind original", "reproducible asset", "unique artwork", "multiplied image",
        "singular vision", "shared perspective", "individual interpretation", "collective understanding",
        "personal statement", "universal expression", "subjective view", "objective documentation",
        "intimate revelation", "public presentation", "private moment", "social communication",
        "soulful connection", "surface appearance", "deep emotion", "external form",
        "inner light", "outer beauty", "spiritual presence", "physical manifestation",
        "psychological insight", "physiological record", "character study", "anatomical documentation",
        "personality capture", "identity representation", "self-expression", "subject depiction",
        "artist's vision", "subject's essence", "creator's interpretation", "model's true nature",
        "photographer's eye", "viewer's perception", "maker's intention", "audience's reception",
        "technical skill", "creative vision", "mechanical precision", "artistic intuition",
        "calculated composition", "inspired moment", "planned setup", "fortunate accident",
        "methodical approach", "spontaneous capture", "strategic intention", "instinctive reaction",
        "professional result", "amateur charm", "expert execution", "novice discovery",
        "perfect portrait", "student attempt", "master work", "beginner's luck",
        "exceptional quality", "everyday snapshot", "outstanding achievement", "casual moment",
        "award-winning portrait", "family photo", "competition-worthy", "personal memory",
        "gallery exhibition", "album inclusion", "museum collection", "social media post",
        "historical document", "momentary capture", "cultural artifact", "fleeting expression",
        "enduring image", "temporary record", "permanent artwork", "ephemeral moment",
        "defining portrait", "passing glance", "iconic representation", "casual observation",
        "celebrated likeness", "anonymous face", "famous visage", "unknown countenance",
        "celebrity capture", "ordinary person", "public figure", "private individual",
        "notable personality", "everyday subject", "historical figure", "contemporary person",
        "influential subject", "regular citizen", "powerful individual", "average person",
        "wealthy patron", "working class", "elite subject", "common folk",
        "privileged sitter", "disadvantaged subject", "entitled client", "marginalized individual",
        "majority representation", "minority portrayal", "dominant culture", "diverse perspective",
        "western tradition", "eastern influence", "northern approach", "southern style",
        "global aesthetic", "local character", "international standard", "regional flavor",
        "urban sophistication", "rural simplicity", "metropolitan complexity", "provincial charm",
        "city setting", "country background", "suburban context", "wilderness location",
        "indoor studio", "outdoor environment", "controlled setting", "natural surroundings",
        "artificial backdrop", "authentic location", "created environment", "found setting",
        "plain background", "complex setting", "minimal context", "detailed environment",
        "stark simplicity", "rich complexity", "empty space", "filled composition",
        "negative space", "positive elements", "spatial depth", "flat rendering",
        "three-dimensional illusion", "two-dimensional design", "perspective depth", "planar arrangement",
        "linear structure", "curved organic", "geometric precision", "natural flow",
        "rigid formality", "fluid spontaneity", "strict composition", "loose arrangement",
        "careful planning", "happy accident", "methodical execution", "fortunate circumstance",
        "perfect lighting", "unexpected shadow", "ideal exposure", "challenging contrast",
        "optimal conditions", "difficult situation", "favorable setting", "adverse environment",
        "comfortable studio", "demanding location", "controlled environment", "unpredictable setting",
        "reliable equipment", "makeshift tools", "professional gear", "improvised solution",
        "high-end camera", "smartphone capture", "expensive lens", "basic optics",
        "latest technology", "traditional approach", "cutting-edge technique", "time-honored method",
        "innovative process", "classical procedure", "experimental approach", "established practice",
        "new perspective", "traditional view", "fresh angle", "conventional framing",
        "original concept", "familiar formula", "unique vision", "common approach",
        "boundary-pushing", "comfort-maintaining", "rule-breaking", "convention-following",
        "artistic risk", "safe choice", "creative gamble", "secure decision",
        "bold experiment", "cautious execution", "daring vision", "prudent approach",
        "revolutionary style", "evolutionary development", "dramatic departure", "gradual progression",
        "shocking difference", "subtle improvement", "radical change", "minor adjustment",
        "complete reinvention", "slight modification", "fundamental transformation", "cosmetic alteration",
        "paradigm shift", "incremental change", "complete makeover", "gentle refinement",
        "perfect teeth", "natural smile", "white enamel", "straight alignment",
        "healthy gums", "pink tissue", "proportional teeth", "balanced smile",
        "confident expression", "relaxed demeanor", "poised appearance", "comfortable presence",
        "authentic emotion", "genuine feeling", "real connection", "true expression",
        "engaging personality", "magnetic charisma", "winning charm", "captivating manner",
        "likable subject", "appealing character", "pleasant demeanor", "agreeable disposition",
        "friendly appearance", "approachable look", "open expression", "inviting countenance",
        "warm personality", "cool composure", "hot passion", "cold reserve",
        "burning intensity", "icy detachment", "fiery emotion", "frosty distance",
        "sunny disposition", "cloudy mood", "stormy temperament", "calm presence",
        "serene expression", "turbulent emotion", "placid surface", "churning depths",
        "settled confidence", "nervous energy", "relaxed assurance", "tense anticipation",
        "engaged attention", "distracted gaze", "focused concentration", "wandering mind",
        "present awareness", "absent thought", "mindful attention", "daydreaming expression",
        "alert observation", "drowsy appearance", "sharp perception", "dulled senses",
        "bright intelligence", "simple expression", "clever look", "naive appearance",
        "wise countenance", "foolish grin", "knowing smile", "puzzled expression",
        "understanding nod", "confused frown", "comprehending gaze", "bewildered stare",
        "certain confidence", "doubtful hesitation", "assured stance", "uncertain posture",
        "decisive appearance", "wavering expression", "determined look", "vacillating gaze",
        "resolute demeanor", "ambivalent attitude", "committed stance", "equivocal position",
        "strong character", "weak presence", "powerful personality", "feeble impression",
        "dominant figure", "submissive posture", "commanding appearance", "yielding expression",
        "assertive stance", "passive attitude", "aggressive look", "receptive expression",
        "active engagement", "inactive repose", "energetic presence", "lethargic appearance",
        "vibrant personality", "dull demeanor", "lively expression", "lifeless look",
        "animated features", "static countenance", "dynamic presence", "rigid posture",
        "flexible attitude", "stiff appearance", "adaptable expression", "inflexible look",
        "flowing movement", "frozen posture", "fluid gesture", "fixed position",
        "graceful motion", "awkward stance", "elegant movement", "clumsy posture",
        "coordinated gesture", "uncoordinated action", "harmonious movement", "discordant motion",
        "rhythmic posture", "arrhythmic stance", "measured gesture", "erratic movement",
        "controlled expression", "uncontrolled emotion", "restrained feeling", "unleashed passion",
        "disciplined demeanor", "undisciplined manner", "ordered composure", "chaotic display",
        "balanced temperament", "unbalanced mood", "equilibrium of feeling", "disequilibrium of emotion",
        "centered presence", "eccentric behavior", "grounded attitude", "flighty manner",
        "stable personality", "unstable character", "consistent expression", "inconsistent display",
        "reliable appearance", "unreliable impression", "trustworthy look", "untrustworthy aspect",
        "honest face", "dishonest expression", "sincere countenance", "insincere look",
        "genuine smile", "fake grin", "authentic laugh", "forced chuckle",
        "natural joy", "artificial happiness", "real sadness", "contrived melancholy",
        "true fear", "feigned terror", "actual surprise", "pretended shock",
        "genuine anger", "simulated rage", "authentic disgust", "performed revulsion",
        "real contempt", "acted disdain", "true compassion", "feigned sympathy",
        "honest interest", "fake attention", "sincere concern", "pretended care",
        "authentic engagement", "simulated involvement", "genuine connection", "artificial rapport",
        "real relationship", "staged interaction", "true intimacy", "performed closeness",
        "authentic bond", "simulated attachment", "genuine link", "artificial connection",
        "true understanding", "pretended comprehension", "real knowledge", "feigned awareness",
        "genuine wisdom", "simulated insight", "authentic intelligence", "pretended cleverness",
        "real experience", "claimed expertise", "true skill", "professed ability",
        "authentic talent", "declared gift", "genuine capacity", "claimed capability",
        "real potential", "professed promise", "true possibility", "stated prospect",
        "authentic opportunity", "claimed advantage", "genuine benefit", "stated gain",
        "real value", "declared worth", "true merit", "claimed virtue",
        "genuine quality", "professed excellence", "authentic superiority", "stated preeminence",
        "real distinction", "claimed uniqueness", "true singularity", "professed originality",
        "authentic novelty", "declared innovation", "genuine creativity", "claimed invention",
        "real imagination", "professed vision", "true inspiration", "claimed muse",
        "authentic artistic expression", "declared creative process", "genuine aesthetic vision", "claimed artistic insight",
        "real beauty", "professed attractiveness", "true handsomeness", "claimed comeliness",
        "authentic appeal", "declared charm", "genuine allure", "claimed magnetism",
        "real charisma", "professed presence", "true aura", "claimed atmosphere",
        "authentic essence", "declared spirit", "genuine soul", "claimed being",
        "real nature", "professed character", "true self", "claimed identity",
        "authentic personality", "declared individuality", "genuine uniqueness", "claimed distinction",
        "real person", "professed persona", "true individual", "claimed character",
        "authentic human", "declared person", "genuine being", "claimed entity",
        "real subject", "professed model", "true sitter", "claimed client",
        "authentic portrayal", "declared representation", "genuine depiction", "claimed portraiture",
        "real image", "professed likeness", "true resemblance", "claimed similarity",
        "authentic representation", "declared illustration", "genuine rendering", "claimed portrayal",
        "real visualization", "professed realization", "true manifestation", "claimed materialization",
        "authentic actualization", "declared concretization", "genuine embodiment", "claimed incarnation",
        "real presence", "professed appearance", "true manifestation", "claimed materialization",
        "authentic existence", "declared being", "genuine living", "claimed life",
        "real experience", "professed sensation", "true feeling", "claimed emotion",
        "authentic response", "declared reaction", "genuine interaction", "claimed exchange",
        "real communication", "professed dialogue", "true conversation", "claimed discussion",
        "authentic discourse", "declared talk", "genuine speech", "claimed utterance",
        "real expression", "professed articulation", "true statement", "claimed declaration",
        "authentic pronouncement", "declared assertion", "genuine claim", "claimed proposition",
        "real thesis", "professed hypothesis", "true theory", "claimed explanation",
        "authentic understanding", "declared comprehension", "genuine grasp", "claimed apprehension",
        "real knowledge", "professed awareness", "true cognizance", "claimed familiarity",
        "authentic acquaintance", "declared recognition", "genuine identification", "claimed knowing",
        "real perception", "professed sensation", "true sight", "claimed vision",
        "authentic viewing", "declared observation", "genuine witness", "claimed seeing",
        "real look", "professed gaze", "true stare", "claimed glance",
        "authentic glimpse", "declared peek", "genuine peep", "claimed view",
        "real sight", "professed vision", "true perception", "claimed observation",
        "authentic observation", "declared examination", "genuine investigation", "claimed study",
        "real analysis", "professed scrutiny", "true inspection", "claimed review",
        "authentic evaluation", "declared assessment", "genuine appraisal", "claimed judgment",
        "real opinion", "professed belief", "true conviction", "claimed faith",
        "authentic trust", "declared confidence", "genuine assurance", "claimed certainty",
        "real knowledge", "professed awareness", "true understanding", "claimed comprehension",
        "authentic grasp", "declared apprehension", "genuine cognizance", "claimed familiarity",
        "real acquaintance", "professed recognition", "true identification", "claimed memory",
        "authentic recollection", "declared remembrance", "genuine recall", "claimed reminiscence",
        "real evocation", "professed summoning", "true revival", "claimed resurrection",
        "authentic reanimation", "declared revitalization", "genuine reawakening", "claimed rebirth",
        "real renewal", "professed rejuvenation", "true regeneration", "claimed restoration",
        "authentic rehabilitation", "declared reconstruction", "genuine rebuilding", "claimed reforming",
        "real remaking", "professed recreation", "true remodeling", "claimed reshaping",
        "authentic restructuring", "declared reorganization", "genuine reordering", "claimed rearrangement",
        "real readjustment", "professed realignment", "true reorientation", "claimed redirection",
        "authentic redefinition", "declared reconceptualization", "genuine reimagination", "claimed re-envisioning",
        "real reconception", "professed reinvention", "true transformation", "claimed metamorphosis",
        "authentic transfiguration", "declared transmutation", "genuine conversion", "claimed alteration",
        "real change", "professed modification", "true adjustment", "claimed adaptation",
        "authentic acclimatization", "declared habituation", "genuine assimilation", "claimed integration",
        "real incorporation", "professed embodiment", "true inclusion", "claimed absorption",
        "authentic assimilation", "declared internalization", "genuine adoption", "claimed acceptance",
        "real reception", "professed admission", "true allowance", "claimed permission",
        "authentic authorization", "declared empowerment", "genuine enablement", "claimed facilitation",
        "real assistance", "professed aid", "true help", "claimed support",
        "authentic backing", "declared reinforcement", "genuine buttressing", "claimed bolstering",
        "real strengthening", "professed fortification", "true enhancement", "claimed improvement",
        "authentic betterment", "declared advancement", "genuine progression", "claimed promotion",
        "real elevation", "professed raising", "true lifting", "claimed heightening",
        "authentic amplification", "declared augmentation", "genuine magnification", "claimed enlargement",
        "real expansion", "professed extension", "true stretching", "claimed broadening",
        "authentic widening", "declared spreading", "genuine dispersal", "claimed diffusion",
        "real distribution", "professed dissemination", "true proliferation", "claimed multiplication",
        "authentic increase", "declared growth", "genuine development", "claimed evolution",
        "real unfoldment", "professed emergence", "true manifestation", "claimed appearance",
        "authentic disclosure", "declared revelation", "genuine epiphany", "claimed discovery",
        "real finding", "professed uncovering", "true exposure", "claimed unveiling",
        "authentic unmasking", "declared demystification", "genuine clarification", "claimed elucidation",
        "real explanation", "professed interpretation", "true explication", "claimed exposition",
        "authentic elucidation", "declared illumination", "genuine enlightenment", "claimed education",
        "real instruction", "professed teaching", "true guidance", "claimed direction",
        "authentic leadership", "declared governance", "genuine management", "claimed administration",
        "real control", "professed command", "true mastery", "claimed dominion",
        "authentic authority", "declared power", "genuine influence", "claimed sway",
        "real impact", "professed effect", "true consequence", "claimed result",
        "authentic outcome", "declared product", "genuine creation", "claimed production",
        "photogenic quality", "camera-ready appearance", "lens-friendly features", "pixel-perfect presentation",
        "film-tested face", "digital-optimized countenance", "photography-favored genetics", "image-friendly looks",
        "light-responsive skin", "shadow-defining features", "contrast-enhancing bone structure", "highlight-catching cheekbones",
        "flatteringly framed by camera", "advantageously captured by lens", "perfectly suited for portraiture", "ideally rendered in photographs",
        "exceptionally reproducible features", "consistently photogenic appearance", "reliably attractive in images", "unfailingly appealing in pictures",
        "genetically gifted for photography", "naturally photogenic disposition", "inherently camera-compatible", "intrinsically photographic-friendly",
        "visually harmonious features", "aesthetically balanced countenance", "proportionally perfect for camera", "symmetrically advantaged face",
        "structurally ideal for portraiture", "architecturally sound facial features", "constructionally advantaged for photography", "dimensionally perfect for lens",
        "texture-rich skin for photography", "tone-varied complexion for images", "color-balanced features for camera", "light-reflecting qualities for lens",
        "expressively photogenic face", "emotionally captivating in images", "sentimentally touching in photographs", "affectively powerful in pictures",
        "narratively strong portrait subject", "story-telling face for camera", "character-rich photographic subject", "history-revealing photographic presence",
        "psychological depth captured by lens", "emotionally layered photographic subject", "mentally engaging portrait presence", "cognitively interesting photographic focus",
        "socially significant portrait subject", "culturally relevant photographic face", "historically important image subject", "documentarily valuable portrait focus",
        "artistically inspiring photographic subject", "creatively stimulating portrait face", "aesthetically motivating camera focus", "visually exciting photographic presence",
        "technically demanding portrait subject", "photographically challenging face", "exposure-testing features", "focus-demanding details",
        "lightingly complex subject", "tonally rich portrait focus", "chromatically interesting face", "colorimetrically diverse photographic subject",
        "compositionally engaging presence", "structurally interesting photographic subject", "geometrically compelling portrait face", "spatially complex camera focus",
        "temporally fascinating subject", "chronologically interesting face", "age-revealing photographic presence", "time-documenting portrait focus",
        "environmentally significant subject", "contextually important face", "setting-enhanced photographic presence", "background-complemented portrait focus",
        "intimately revealed portrait subject", "personally exposed photographic face", "privately shown camera presence", "confidentially captured portrait focus",
        "publicly presented subject", "socially displayed face", "communally shared photographic presence", "collectively viewed portrait focus",
        "professionally presented subject", "occupationally shown face", "vocationally revealed photographic presence", "career-expressing portrait focus",
        "familiarly comfortable subject", "intimately at-ease face", "relationally natural photographic presence", "socially relaxed portrait focus",
        "emotionally available subject", "sentimentally open face", "affectively accessible photographic presence", "feelingly transparent portrait focus",
        "expressively dynamic subject", "emotionally mobile face", "sentimentally active photographic presence", "affectively fluid portrait focus",
        "characterfully rich subject", "personally textured face", "individually complex photographic presence", "identitively layered portrait focus",
        "historically significant subject", "temporally important face", "chronologically valuable photographic presence", "periodically noteworthy portrait focus",
        "culturally relevant subject", "socially significant face", "communally important photographic presence", "collectively meaningful portrait focus",
        "artistically valuable subject", "aesthetically significant face", "creatively important photographic presence", "expressively noteworthy portrait focus",
        "technically perfect portrait", "photographically flawless face", "optically ideal subject", "visually impeccable presence",
        "compositionally balanced portrait", "structurally harmonious face", "geometrically perfect subject", "spatially ideal presence",
        "expressively powerful portrait", "emotionally captivating face", "sentimentally moving subject", "affectively touching presence",
        "narratively compelling portrait", "story-rich face", "character-full subject", "history-laden presence",
        "psychologically deep portrait", "mentally complex face", "cognitively interesting subject", "intellectually engaging presence",
        "socially meaningful portrait", "culturally significant face", "historically important subject", "documentarily valuable presence",
        "artistically inspiring portrait", "creatively stimulating face", "aesthetically motivating subject", "visually exciting presence",
        "perfectly lit portrait", "ideally illuminated face", "optimally brightened subject", "flatteringly lightened presence",
        "shadow-sculpted portrait", "highlight-defined face", "contrast-enhanced subject", "tonally optimized presence",
        "color-balanced portrait", "chromatically harmonized face", "hue-optimized subject", "spectrally balanced presence",
        "texture-rich portrait", "detail-abundant face", "information-dense subject", "feature-filled presence",
        "sharply focused portrait", "precisely captured face", "clearly defined subject", "crystallinely rendered presence",
        "depth-enhanced portrait", "dimensionally rich face", "spatially complex subject", "perspectively interesting presence",
        "temporally frozen portrait", "chronologically captured face", "moment-preserving subject", "time-stopping presence",
        "environmentally contextualized portrait", "setting-enhanced face", "background-complemented subject", "surroundings-supported presence",
        "intimately revealing portrait", "personally exposing face", "privately showing subject", "confidentially capturing presence",
        "publicly presentable portrait", "socially displayable face", "communally sharable subject", "collectively viewable presence",
        "professionally crafted portrait", "expertly created face", "skillfully made subject", "masterfully produced presence",
        "technically excellent portrait", "photographically superior face", "optically outstanding subject", "visually exceptional presence",
        "expressively remarkable portrait", "emotionally extraordinary face", "sentimentally exceptional subject", "affectively outstanding presence",
        "narratively superior portrait", "story-wise excellent face", "character-wise remarkable subject", "history-wise extraordinary presence",
        "psychologically profound portrait", "mentally remarkable face", "cognitively extraordinary subject", "intellectually exceptional presence",
        "socially significant portrait", "culturally important face", "historically valuable subject", "documentarily crucial presence",
        "artistically masterful portrait", "creatively brilliant face", "aesthetically superb subject", "visually outstanding presence",
        "perfectly composed portrait", "ideally arranged face", "optimally structured subject", "flatteringly organized presence",
        "dramatically lit portrait", "theatrically illuminated face", "cinematically brightened subject", "performatively lightened presence",
        "dramatically shadowed portrait", "theatrically darkened face", "cinematically contrasted subject", "performatively differentiated presence",
        "dramatically colored portrait", "theatrically chromaticized face", "cinematically hued subject", "performatively tinted presence",
        "dramatically textured portrait", "theatrically surfaced face", "cinematically detailed subject", "performatively featured presence",
        "dramatically focused portrait", "theatrically sharpened face", "cinematically defined subject", "performatively clarified presence",
        "dramatically composed portrait", "theatrically arranged face", "cinematically structured subject", "performatively organized presence",
        "dramatically posed portrait", "theatrically positioned face", "cinematically arranged subject", "performatively situated presence",
        "dramatically expressive portrait", "theatrically emotional face", "cinematically affective subject", "performatively sentimental presence",
        "dramatically narrative portrait", "theatrically story-telling face", "cinematically tale-bearing subject", "performatively recounting presence",
        "dramatically psychological portrait", "theatrically mental face", "cinematically cognitive subject", "performatively intellectual presence",
        "dramatically social portrait", "theatrically cultural face", "cinematically historical subject", "performatively documental presence",
        "dramatically artistic portrait", "theatrically creative face", "cinematically aesthetic subject", "performatively visual presence",
        "classically beautiful portrait", "historically handsome face", "traditionally attractive subject", "conventionally appealing presence",
        "modernly beautiful portrait", "contemporarily handsome face", "currently attractive subject", "presently appealing presence",
        "timelessly beautiful portrait", "eternally handsome face", "enduringly attractive subject", "perpetually appealing presence",
        "uniquely beautiful portrait", "distinctively handsome face", "singularly attractive subject", "individually appealing presence",
        "universally beautiful portrait", "globally handsome face", "cross-culturally attractive subject", "internationally appealing presence",
        "locally beautiful portrait", "regionally handsome face", "culturally attractive subject", "ethnically appealing presence",
        "objectively beautiful portrait", "factually handsome face", "empirically attractive subject", "measurably appealing presence",
        "subjectively beautiful portrait", "personally handsome face", "individually attractive subject", "particularly appealing presence",
        "naturally beautiful portrait", "inherently handsome face", "intrinsically attractive subject", "genuinely appealing presence",
        "artificially beautiful portrait", "enhanced handsome face", "improved attractive subject", "altered appealing presence",
        "honestly beautiful portrait", "truthfully handsome face", "accurately attractive subject", "realistically appealing presence",
        "idealized beautiful portrait", "perfected handsome face", "flawless attractive subject", "impeccable appealing presence",
        "practically beautiful portrait", "functionally handsome face", "usefully attractive subject", "purposefully appealing presence",
        "aesthetically beautiful portrait", "artistically handsome face", "creatively attractive subject", "expressively appealing presence",
        "physically beautiful portrait", "bodily handsome face", "corporeally attractive subject", "materially appealing presence",
        "spiritually beautiful portrait", "soulfully handsome face", "transcendentally attractive subject", "metaphysically appealing presence",
        "intellectually beautiful portrait", "mentally handsome face", "cognitively attractive subject", "cerebrally appealing presence",
        "emotionally beautiful portrait", "sentimentally handsome face", "affectively attractive subject", "feelingly appealing presence",
        "morally beautiful portrait", "ethically handsome face", "principally attractive subject", "virtuously appealing presence",
        "socially beautiful portrait", "communally handsome face", "collectively attractive subject", "culturally appealing presence",
        "historically beautiful portrait", "traditionally handsome face", "conventionally attractive subject", "customarily appealing presence",
        "futuristically beautiful portrait", "progressively handsome face", "forwardly attractive subject", "advancingly appealing presence",
        "femininely beautiful portrait", "womanly handsome face", "girlishly attractive subject", "ladylike appealing presence",
        "masculinely beautiful portrait", "manly handsome face", "boyishly attractive subject", "gentlemanly appealing presence",
        "androgynously beautiful portrait", "gender-fluidly handsome face", "non-binarily attractive subject", "sex-ambiguously appealing presence",
        "youthfully beautiful portrait", "juvenilely handsome face", "adolescently attractive subject", "childishly appealing presence",
        "maturely beautiful portrait", "adultly handsome face", "grown-up attractive subject", "elderlily appealing presence",
        "agelessly beautiful portrait", "timelessly handsome face", "eternally attractive subject", "perpetually appealing presence",
        "racially beautiful portrait", "ethnically handsome face", "tribally attractive subject", "lineage-wise appealing presence",
        "nationally beautiful portrait", "patriotically handsome face", "country-wise attractive subject", "nation-specifically appealing presence",
        "internationally beautiful portrait", "globally handsome face", "world-wide attractive subject", "planet-wide appealing presence",
        "terrestrially beautiful portrait", "earthly handsome face", "worldly attractive subject", "mundanely appealing presence",
        "cosmically beautiful portrait", "universally handsome face", "galaxially attractive subject", "celestially appealing presence",
        "divinely beautiful portrait", "godly handsome face", "heavenly attractive subject", "paradisaically appealing presence",
        "infernally beautiful portrait", "devilishly handsome face", "hellishly attractive subject", "damnably appealing presence",
        "mythically beautiful portrait", "legendarily handsome face", "fabulously attractive subject", "fictionalizingly appealing presence",
        "realistically beautiful portrait", "actually handsome face", "factually attractive subject", "truly appealing presence",
        "romantically beautiful portrait", "lovingly handsome face", "affectionately attractive subject", "passionately appealing presence",
        "platonically beautiful portrait", "friendlily handsome face", "companionably attractive subject", "collegiately appealing presence",
        "familially beautiful portrait", "relationally handsome face", "kinshiply attractive subject", "blood-relatedly appealing presence",
        "professionally beautiful portrait", "occupationally handsome face", "vocationally attractive subject", "career-wise appealing presence",
        "aristocratically beautiful portrait", "nobly handsome face", "blue-bloodedly attractive subject", "high-bornly appealing presence",
        "commonly beautiful portrait", "ordinarily handsome face", "regularly attractive subject", "usually appealing presence",
        "royally beautiful portrait", "majestically handsome face", "regally attractive subject", "monarchically appealing presence",
        "presidentially beautiful portrait", "executively handsome face", "administratively attractive subject", "governmentally appealing presence",
        "militarily beautiful portrait", "martially handsome face", "warriorly attractive subject", "soldierishly appealing presence",
        "athletically beautiful portrait", "sportingly handsome face", "physically-activentially attractive subject", "exercise-wise appealing presence",   
        "intellectually beautiful portrait", "academically handsome face", "scholarly attractive subject", "learnedly appealing presence",
        "artistically beautiful portrait", "creatively handsome face", "expressively attractive subject", "aesthetically appealing presence",
        "musically beautiful portrait", "melodically handsome face", "harmonically attractive subject", "rhythmically appealing presence",
        "literarily beautiful portrait", "poetically handsome face", "lyrically attractive subject", "prosaically appealing presence",
        "dramatically beautiful portrait", "theatrically handsome face", "performatively attractive subject", "actingly appealing presence",
        "cinematically beautiful portrait", "filmically handsome face", "movie-staringly attractive subject", "screen-presencely appealing presence",
        "photographically beautiful portrait", "camera-lovingly handsome face", "lens-flatteringly attractive subject", "picture-perfectingly appealing presence",
        "painterly beautiful portrait", "brushstrokingly handsome face", "canvas-worthily attractive subject", "artist-inspiringly appealing presence",
        "sculpturally beautiful portrait", "chiseledlily handsome face", "three-dimensionally attractive subject", "tactilely appealing presence",
        "architecturally beautiful portrait", "structurally handsome face", "constructionally attractive subject", "building-wise appealing presence",
        "fashionably beautiful portrait", "stylishly handsome face", "trendsettingly attractive subject", "vogue-worthily appealing presence",
        "elegantly beautiful portrait", "gracefully handsome face", "refinedly attractive subject", "sophisticatedly appealing presence",
        "classically beautiful portrait", "timelessly handsome face", "traditionally attractive subject", "enduringly appealing presence",
        "contemporarily beautiful portrait", "modernly handsome face", "currently attractive subject", "presentistically appealing presence",
        "futuristically beautiful portrait", "ahead-of-timely handsome face", "progressively attractive subject", "forward-thinkingly appealing presence",
        "perfectly framed portrait", "masterfully composed face", "expertly positioned subject", "skillfully arranged presence",
        "exquisitely lit portrait", "magnificently illuminated face", "splendidly brightened subject", "gloriously lightened presence",
        "masterfully focused portrait", "expertly sharpened face", "skillfully defined subject", "adeptly clarified presence"
    ],
    "artistic": [
        "high art style", "concept art", "premium digital illustration", "digital painting",
        "watercolor", "oil on canvas", "detailed painting", "smooth brushstrokes", 
        "vibrant colors", "high contrast", "artistic touch", "soft pastels",
        "chiaroscuro technique", "impasto", "canvas texture", "detailed engravings",
        "contemporary art", "surrealist style", "cubism", "art nouveau",
        "renaissance aesthetic", "baroque complexity", "rococo ornamentation", "neoclassical beauty",
        "romantic atmosphere", "impressionist light", "post-impressionist color", "expressionist emotion",
        "abstract expressionism", "color field painting", "minimalist elegance", "maximalist abundance",
        "pop art vibrancy", "op art illusion", "kinetic art movement", "conceptual art depth",
        "installation art immersion", "performance art energy", "land art scale", "digital art precision",
        "net art connectivity", "glitch art distortion", "vaporwave aesthetic", "cyberpunk vision",
        "steampunk imagination", "art deco glamour", "bauhaus functionality", "memphis playfulness",
        "gothic drama", "romanesque solidity", "byzantine richness", "islamic pattern",
        "eastern art tradition", "western art canon", "northern renaissance detail", "southern baroque passion",
        "primitivist rawness", "naive charm", "outsider art authenticity", "folk art tradition",
        "street art rebellion", "graffiti energy", "mural scale", "fresco permanence",
        "mosaic intricacy", "stained glass luminosity", "ceramic glaze", "pottery form",
        "textile art texture", "fiber art tactility", "quilt pattern", "embroidery detail",
        "metalwork precision", "jewelry delicacy", "glass art transparency", "crystal refraction",
        "woodwork grain", "stone carving permanence", "paper art fragility", "origami precision",
        "calligraphy flow", "typography design", "illuminated manuscript", "book art structure",
        "printmaking technique", "etching detail", "lithographic texture", "silkscreen flatness",
        "photographic realism", "camera obscura effect", "daguerreotype nostalgia", "polaroid immediacy",
        "film noir contrast", "technicolor saturation", "black and white elegance", "sepia nostalgia",
        "colored pencil precision", "graphite gradation", "charcoal depth", "conte crayon warmth",
        "pastel softness", "oil pastel vibrancy", "encaustic texture", "gouache flatness",
        "acrylic versatility", "tempera permanence", "fresco technique", "sumi-e simplicity",
        "ukiyo-e flatness", "manga stylization", "anime expressiveness", "cartoon simplification",
        "caricature exaggeration", "comic book dynamism", "pixel art nostalgia", "8-bit aesthetic",
        "vector art precision", "3D rendering depth", "CAD precision", "algorithmic generation",
        "fractal complexity", "generative art surprise", "AI art collaboration", "neural style transfer",
        "deep dream imagination", "data visualization clarity", "scientific illustration accuracy", "technical drawing precision",
        "architectural rendering", "blueprint clarity", "isometric projection", "axonometric view",
        "perspective accuracy", "golden ratio composition", "rule of thirds balance", "dynamic symmetry",
        "sacred geometry", "mathematical precision", "geometric abstraction", "organic form",
        "biomorphic shape", "anthropomorphic suggestion", "zoomorphic inspiration", "phytomorphic pattern",
        "atmospheric perspective", "aerial view", "bird's eye perspective", "worm's eye view",
        "linear perspective", "curvilinear distortion", "anamorphic illusion", "trompe l'oeil deception",
        "pointillism technique", "divisionism method", "sfumato softness", "chiaroscuro contrast",
        "tenebrist drama", "grisaille monochrome", "verdaccio underpainting", "glazing luminosity",
        "scumbling texture", "dry brush effect", "wet-on-wet blending", "sgraffito revelation",
        "pentimento evidence", "palimpsest layers", "collage juxtaposition", "assemblage construction",
        "bricolage ingenuity", "found object repurposing", "ready-made concept", "appropriation strategy",
        "détournement subversion", "pastiche homage", "parody commentary", "satire critique",
        "allegory symbolism", "iconography system", "semiotics meaning", "hermeneutics interpretation",
        "phenomenological experience", "existential questioning", "metaphysical exploration", "ontological inquiry",
        "epistemological investigation", "aesthetic philosophy", "beauty ideal", "sublime experience",
        "picturesque scene", "abject disruption", "grotesque fascination", "uncanny disquiet",
        "kitsch sentimentality", "camp sensibility", "lowbrow accessibility", "highbrow sophistication",
        "avant-garde experimentation", "arrière-garde tradition", "modernist innovation", "postmodernist playfulness",
        "deconstructivist questioning", "reconstructivist affirming", "post-structuralist critiquing", "neo-expressionist emotionality",
        "trans-avant-garde eclecticism", "arte povera simplicity", "fluxus spontaneity", "happening temporality",
        "situationist derivation", "lettrist reduction", "concrete visualization", "visual poetry",
        "sound art aurality", "light art luminosity", "space art vastness", "time art duration",
        "bio art living", "eco art sustainable", "political art engagement", "identity art representation",
        "feminist perspective", "post-colonial critique", "queer visibility", "intersectional awareness",
        "outsider perspective", "indigenous knowledge", "traditional craft", "heritage preservation",
        "futurist anticipation", "speculative imagination", "utopian aspiration", "dystopian warning",
        "anthropocene awareness", "posthuman possibility", "transhuman enhancement", "artificial intelligence",
        "virtual reality immersion", "augmented reality overlay", "mixed reality integration", "extended reality possibility",
        "tactile sensation", "synesthetic experience", "kinesthetic response", "proprioceptive awareness",
        "emotional resonance", "psychological depth", "cognitive challenge", "intellectual stimulation",
        "spiritual dimension", "transcendent aspiration", "immanent presence", "numinous quality",
        "mythic narrative", "archetypal symbolism", "collective unconscious", "personal expression",
        "cultural reference", "historical context", "contemporary relevance", "future potential",
        "local specificity", "global connection", "universal aspiration", "particular detail",
        "subjective impression", "objective documentation", "indexical trace", "symbolic representation",
        "literal depiction", "figurative suggestion", "abstract reduction", "non-representational focus",
        "representational fidelity", "hyperrealistic detail", "photorealistic accuracy", "superrealistic enhancement",
        "magical realist wonder", "fantastic imagination", "surrealist dream", "visionary revelation",
        "naive simplicity", "primitive directness", "childlike wonder", "sophisticated complexity",
        "refined elegance", "raw energy", "delicate subtlety", "bold statement",
        "minimal reduction", "maximal exuberance", "balanced harmony", "dynamic tension",
        "stable composition", "vibrant movement", "rhythmic pattern", "melodic line",
        "harmonic color", "dissonant contrast", "symphonic structure", "improvisational freedom",
        "planned precision", "spontaneous expression", "controlled technique", "accidental discovery",
        "meticulous craft", "inspired vision", "technical skill", "creative imagination",
        "traditional mastery", "innovative experimentation", "conventional foundation", "radical departure",
        "evolutionary development", "revolutionary transformation", "incremental change", "paradigm shift",
        "culturally specific", "historically situated", "geographically located", "temporally defined",
        "materially embodied", "conceptually constructed", "processually developed", "relationally positioned",
        "contextually embedded", "intertextually referenced", "dialogically engaged", "monologically stated",
        "collaboratively created", "individually expressed", "collectively shared", "personally experienced",
        "publicly displayed", "privately treasured", "commercially valued", "spiritually significant",
        "aesthetically appreciated", "critically evaluated", "theoretically analyzed", "emotionally felt",
        "sensually perceived", "intellectually understood", "intuitively grasped", "rationally comprehended",
        "visually captivating", "aurally engaging", "tactilely stimulating", "spatially immersive",
        "temporally evolving", "dimensionally complex", "scalarly variable", "proportionally balanced",
        "symmetrically ordered", "asymmetrically dynamic", "hierarchically structured", "rhizomatically connected",
        "linearly progressive", "cyclically returning", "spirally developing", "fractally self-similar",
        "organically growing", "mechanically constructed", "chemically combining", "physically manifesting",
        "digitally rendered", "analogically referenced", "virtually simulated", "actually embodied",
        "imaginatively conceived", "rationally planned", "emotionally expressed", "spiritually inspired",
        "unconsciously emerged", "consciously crafted", "intuitively sensed", "methodically developed",
        "accidentally discovered", "intentionally created", "randomly generated", "algorithmically computed",
        "hand-crafted quality", "machine-made precision", "digital exactitude", "analog warmth",
        "haptic physicality", "optical illusion", "aural resonance", "conceptual abstraction",
        "narrative suggestion", "lyrical expression", "dramatic tension", "comic relief",
        "tragic depth", "epic scale", "intimate detail", "monumental presence",
        "miniature precision", "gigantic impact", "microscopic detail", "macroscopic view",
        "natural inspiration", "artificial construction", "organic development", "geometric order",
        "chaotic energy", "ordered structure", "random variation", "planned development",
        "evolutionary adaptation", "revolutionary disruption", "traditional continuity", "innovative break",
        "historical reference", "contemporary context", "futuristic vision", "timeless quality",
        "culturally specific", "universally resonant", "locally meaningful", "globally relevant",
        "personally expressive", "socially engaged", "politically conscious", "environmentally aware",
        "materially grounded", "spiritually elevated", "earthily embodied", "cosmically connected",
        "scientifically informed", "poetically imagined", "philosophically considered", "mythologically charged",
        "religiously significant", "secularly meaningful", "sacred dimension", "profane reality",
        "light-filled luminosity", "shadow-rich darkness", "colorfully vibrant", "monochromatically subtle",
        "linearly defined", "tonally graduated", "texturally varied", "smoothly unified",
        "rough and tactile", "sleek and polished", "uneven and organic", "precise and mechanical",
        "warm and inviting", "cool and distant", "hot and passionate", "cold and analytical",
        "wet and flowing", "dry and static", "solid and substantial", "fluid and changeable",
        "heavy and grounded", "light and floating", "dense and compact", "airy and spacious",
        "opaque and substantial", "transparent and ephemeral", "translucent and mysterious", "reflective and mirror-like",
        "matte and absorbing", "glossy and bouncing", "satiny and subtle", "pearlescent and glowing",
        "iridescent and shifting", "metallic and gleaming", "crystalline and faceted", "gelatinous and amorphous",
        "fibrous and woven", "grainy and particulate", "powdery and soft", "solid and impenetrable",
        "liquid and flowing", "gaseous and floating", "plasmaic and energetic", "vacuum-like emptiness",
        "positive space", "negative space", "figure ground relationship", "spatial depth",
        "temporal duration", "fourth-dimensional awareness", "multidimensional complexity", "spatial-temporal continuum",
        "full spectrum color", "limited palette restraint", "monotone concentration", "duotone relationship",
        "triadic harmony", "complementary contrast", "analogous subtlety", "split complementary sophistication",
        "tetradic complexity", "square color relationship", "neutral ground", "dominant accent",
        "subdominant mediation", "subordinate support", "pure saturation", "muted desaturation",
        "high value brightness", "low value darkness", "middle value balance", "contrastive range",
        "subtle gradation", "abrupt juxtaposition", "smooth transition", "hard edge definition",
        "soft focus diffusion", "sharp clarity", "blurred suggestion", "precise detail",
        "flat space", "deep recession", "ambiguous spatiality", "definite location",
        "frontal presentation", "profile view", "three-quarter aspect", "bird's eye perspective",
        "worm's eye viewpoint", "isometric projection", "one-point perspective", "two-point recession",
        "three-point complexity", "atmospheric depth", "linear perspective", "reversed perspective",
        "multiple viewpoints", "cubist simultaneity", "sequential narrative", "single moment",
        "frozen action", "implied movement", "actual kinetics", "optical illusion",
        "representational clarity", "abstract suggestion", "non-objective focus", "minimalist reduction",
        "maximalist inclusion", "horror vacui fullness", "zen-like emptiness", "balanced distribution",
        "asymmetrical interest", "symmetrical stability", "radial expansion", "linear progression",
        "grid-like order", "organic irregularity", "geometric precision", "biomorphic suggestion",
        "anthropomorphic reference", "zoomorphic allusion", "phytomorphic similarity", "crystalline structure",
        "natural pattern", "artificial construction", "found object", "created form",
        "readymade appropriation", "handcrafted uniqueness", "mass produced multiple", "one-of-a-kind original",
        "reproducible image", "irreproducible experience", "recontextualized meaning", "site-specific relevance",
        "portable object", "environmental installation", "permanent monument", "ephemeral event",
        "traditional medium", "experimental material", "conventional technique", "innovative method",
        "historical reference", "contemporary expression", "futuristic anticipation", "timeless quality",
        "culturally specific", "universally human", "individually unique", "collectively representative",
        "painterly brushwork", "hard-edge precision", "gestural energy", "controlled application",
        "impasto thickness", "glazed transparency", "scumbled texture", "smooth surface",
        "collaged assemblage", "unified whole", "fragmented composition", "integrated elements",
        "central focus", "distributed attention", "hierarchical organization", "democratic equality",
        "narrative content", "formal abstraction", "emotional expression", "intellectual concept",
        "sensual appreciation", "spiritual elevation", "physical presence", "virtual simulation",
        "real object", "illusionistic representation", "actual material", "depicted subject",
        "allegorical meaning", "symbolic reference", "metaphorical suggestion", "literal description",
        "ironic commentary", "sincere expression", "satirical critique", "earnest celebration",
        "humorous play", "serious intent", "lighthearted approach", "grave consideration",
        "childlike wonder", "mature contemplation", "youthful energy", "elder wisdom",
        "fresh perspective", "seasoned mastery", "amateur enthusiasm", "professional skill",
        "outsider authenticity", "insider knowledge", "naive directness", "sophisticated complexity",
        "raw emotion", "refined sensibility", "primitive power", "cultivated taste",
        "visceral impact", "cerebral challenge", "gut reaction", "thoughtful response",
        "immediate appeal", "lasting significance", "instantaneous effect", "gradual revelation",
        "momentary experience", "enduring presence", "ephemeral beauty", "permanent record",
        "contemporary relevance", "historical importance", "current context", "timeless value",
        "fashionable trend", "classical standard", "modern approach", "traditional foundation",
        "cutting-edge innovation", "established convention", "revolutionary advance", "evolutionary development",
        "radical departure", "natural progression", "dramatic breakthrough", "subtle shift",
        "major transformation", "minor variation", "paradigm shift", "continuous tradition",
        "Western aesthetic", "Eastern influence", "Northern clarity", "Southern passion",
        "African rhythm", "Asian harmony", "European structure", "American freedom",
        "oceanic fluidity", "desert sparseness", "mountain grandeur", "forest intricacy",
        "urban complexity", "rural simplicity", "industrial precision", "artisanal touch",
        "digital technology", "analog process", "virtual reality", "physical presence",
        "conceptual framework", "material embodiment", "ideational foundation", "sensual realization",
        "intellectual content", "emotional expression", "rational structure", "irrational energy",
        "conscious intention", "unconscious emergence", "deliberate choice", "accidental discovery",
        "planned composition", "spontaneous generation", "methodical development", "intuitive progression",
        "systematic approach", "random exploration", "ordered arrangement", "chaotic vitality",
        "balanced harmony", "dynamic tension", "stable equilibrium", "precarious excitement",
        "formal elegance", "informal charm", "structured organization", "loose arrangement",
        "tight composition", "open framework", "closed system", "expansive vision",
        "intricate detail", "broad gesture", "minute observation", "sweeping statement",
        "precise rendering", "expressive suggestion", "accurate representation", "evocative impression",
        "descriptive clarity", "poetic allusion", "scientific accuracy", "artistic license",
        "objective recording", "subjective interpretation", "factual documentation", "imaginative transformation",
        "realistic depiction", "fantastical invention", "naturalistic observation", "stylized formulation",
        "observed phenomenon", "created fiction", "documented reality", "fabricated illusion",
        "unmanipulated capture", "altered representation", "straight photograph", "constructed image",
        "found composition", "designed arrangement", "discovered subject", "invented content",
        "natural beauty", "artificial construction", "organic development", "geometric order",
        "flowing curves", "angular structure", "sinuous lines", "straight edges",
        "circular movement", "rectilinear grid", "spiral progression", "zigzag energy",
        "centrifugal expansion", "centripetal concentration", "radiating pattern", "converging lines",
        "horizontal stability", "vertical aspiration", "diagonal dynamism", "curved grace",
        "static composition", "dynamic arrangement", "restful balance", "energetic imbalance",
        "symmetric order", "asymmetric interest", "regular pattern", "irregular variation",
        "repeating motif", "unique elements", "serial progression", "singular focus",
        "multiple perspectives", "single viewpoint", "varied approaches", "consistent vision",
        "eclectic collection", "unified whole", "diverse components", "integrated system",
        "fragmented assemblage", "seamless fusion", "discrete parts", "continuous flow",
        "abrupt transition", "smooth gradation", "sharp contrast", "subtle distinction",
        "bold statement", "quiet suggestion", "loud declaration", "whispered intimation",
        "dramatic intensity", "calm serenity", "passionate expression", "cool detachment",
        "hot emotion", "cold analysis", "warm invitation", "chilly distance",
        "fiery energy", "icy precision", "burning desire", "frozen moment",
        "fluid movement", "solid presence", "gaseous atmosphere", "crystalline structure",
        "earthy groundedness", "airy lightness", "watery fluidity", "fiery transformation",
        "material substance", "spiritual essence", "physical presence", "metaphysical concept",
        "concrete reality", "abstract idea", "tangible object", "intangible quality",
        "visible appearance", "invisible meaning", "audible sound", "silent implication",
        "tactile texture", "visual pattern", "sonic rhythm", "conceptual structure",
        "spatial organization", "temporal sequence", "physical dimension", "psychological depth",
        "external form", "internal content", "surface appearance", "deep significance",
        "obvious statement", "hidden meaning", "manifest presence", "latent potential",
        "foreground emphasis", "background context", "figure prominence", "ground support",
        "positive shape", "negative space", "solid form", "empty void",
        "filled plenitude", "vacant absence", "abundant richness", "minimal restraint",
        "maximal complexity", "simple clarity", "ornate decoration", "plain statement",
        "elaborate detail", "essential simplicity", "embellished surface", "reduced form",
        "excessive abundance", "restrained economy", "baroque complexity", "classical clarity",
        "romantic emotion", "neoclassical order", "expressionist intensity", "constructivist structure",
        "surrealist juxtaposition", "minimalist reduction", "abstract expressionist gesture", "pop art appropriation",
        "conceptual idea", "performance action", "installation environment", "land art intervention",
        "body art expression", "digital creation", "interactive engagement", "participatory involvement",
        "passive contemplation", "active participation", "observational distance", "immersive experience",
        "critical analysis", "appreciative enjoyment", "intellectual understanding", "emotional response",
        "sensual delight", "spiritual elevation", "physical reaction", "psychological effect",
        "temporal duration", "spatial extension", "momentary experience", "enduring presence",
        "historical context", "contemporary relevance", "traditional reference", "innovative departure",
        "conservative attachment", "progressive advance", "reactionary return", "revolutionary break",
        "evolutionary development", "cyclical return", "linear progression", "spiral growth",
        "repetitive pattern", "unique occurrence", "serial variation", "singular statement",
        "multiple iteration", "once-only event", "reproducible image", "irreplaceable original",
        "mass-produced object", "handcrafted unique", "mechanical reproduction", "autographic authenticity",
        "democratic accessibility", "elitist exclusivity", "popular appeal", "refined taste",
        "common appreciation", "specialized knowledge", "universal recognition", "esoteric understanding",
        "immediate impact", "gradual revelation", "instant effect", "developing appreciation",
        "superficial attraction", "deep engagement", "casual glance", "sustained attention",
        "fleeting impression", "lasting memory", "momentary distraction", "dedicated focus",
        "peripheral awareness", "central concentration", "divided attention", "unified perception",
        "selective emphasis", "comprehensive inclusion", "partial view", "complete vision",
        "limited perspective", "total understanding", "restricted scope", "expansive breadth",
        "narrow focus", "wide angle", "telephoto compression", "wide-angle distortion",
        "macro detail", "micro precision", "close inspection", "distant view",
        "proximate engagement", "remote observation", "intimate relationship", "detached analysis",
        "emotional investment", "rational assessment", "passionate involvement", "cool appraisal",
        "subjective response", "objective evaluation", "personal reaction", "universal standard",
        "individual taste", "collective judgment", "private pleasure", "public appreciation",
        "commercial value", "aesthetic worth", "market price", "artistic significance",
        "financial investment", "cultural capital", "economic commodity", "spiritual treasure",
        "material object", "cultural symbol", "physical presence", "conceptual meaning",
        "tangible artifact", "intangible idea", "concrete manifestation", "abstract concept",
        "literal representation", "figurative suggestion", "realistic depiction", "symbolic reference",
        "documentary evidence", "imaginative creation", "factual record", "fictional construction",
        "historical documentation", "visionary invention", "empirical observation", "speculative imagination",
        "scientific accuracy", "poetic truth", "logical coherence", "intuitive insight",
        "rational order", "emotional expression", "intellectual concept", "sensual experience",
        "cognitive challenge", "affective response", "cerebral puzzle", "visceral reaction",
        "mental stimulation", "physical sensation", "psychological effect", "physiological impact",
        "neurological process", "biological response", "cultural conditioning", "instinctive reaction",
        "learned appreciation", "innate response", "acquired taste", "natural affinity",
        "cultivated sensitivity", "inherent receptivity", "educated discrimination", "spontaneous reaction",
        "critical judgment", "immediate pleasure", "analytical understanding", "intuitive grasp",
        "theoretical framework", "practical application", "philosophical foundation", "pragmatic function",
        "ideological position", "practical purpose", "political stance", "social role",
        "economic context", "cultural significance", "historical importance", "contemporary relevance",
        "artistic tradition", "innovative departure", "conventional approach", "experimental method",
        "established technique", "novel process", "traditional craft", "new technology",
        "ancient practice", "modern development", "timeless quality", "current trend",
        "enduring value", "passing fashion", "permanent significance", "temporary interest",
        "classical proportion", "romantic expression", "baroque complexity", "minimalist simplicity",
        "realistic accuracy", "expressionist distortion", "impressionist light", "cubist fragmentation",
        "surrealist juxtaposition", "abstract reduction", "pop cultural reference", "conceptual focus",
        "narrative sequence", "lyrical expression", "dramatic tension", "epic scale",
        "intimate detail", "monumental presence", "miniature precision", "colossal impact",
        "delicate subtlety", "powerful statement", "gentle suggestion", "forceful declaration",
        "quiet whisper", "loud proclamation", "subtle nuance", "bold contrast",
        "fine gradation", "sharp distinction", "smooth transition", "abrupt change",
        "flowing continuity", "sudden interruption", "gradual development", "immediate transformation",
        "slow evolution", "rapid revolution", "careful progress", "dramatic breakthrough",
        "methodical improvement", "spontaneous invention", "planned innovation", "accidental discovery",
        "rational design", "intuitive creation", "calculated effect", "instinctive expression",
        "conscious intention", "unconscious revelation", "deliberate choice", "automatic process",
        "controlled technique", "chance operation", "skilled execution", "aleatory result",
        "mastered craft", "experimental play", "professional expertise", "amateur enthusiasm",
        "technical virtuosity", "conceptual insight", "manual dexterity", "intellectual depth",
        "formal sophistication", "emotional authenticity", "structural complexity", "expressive directness",
        "compositional balance", "chaotic energy", "harmonic resolution", "dissonant tension",
        "rhythmic pattern", "syncopated variation", "melodic line", "contrapuntal complexity",
        "symphonic structure", "improvisational freedom", "orchestrated arrangement", "spontaneous expression",
        "polyphonic texture", "monophonic clarity", "homophonic unity", "heterophonic diversity",
        "unified composition", "fragmented collage", "integrated whole", "assembled parts",
        "continuous surface", "interrupted plane", "consistent texture", "varied handling",
        "uniform application", "diverse treatment", "methodical approach", "experimental technique",
        "traditional process", "innovative method", "conventional material", "unusual medium",
        "familiar form", "surprising content", "expected outcome", "unexpected result",
        "planned effect", "serendipitous discovery", "intended consequence", "unforeseen development",
        "calculated risk", "fortunate accident", "deliberate ambiguity", "unintentional clarity",
        "purposeful obscurity", "accidental revelation", "intentional difficulty", "spontaneous accessibility",
        "complex structure", "simple appearance", "elaborate concept", "straightforward execution",
        "multifaceted meaning", "direct statement", "layered significance", "obvious message",
        "profound depth", "surface appeal", "serious purpose", "playful approach",
        "grave importance", "light touch", "weighty significance", "buoyant spirit",
        "dark mystery", "bright clarity", "shadowy suggestion", "illuminating revelation",
        "obscure reference", "clear meaning", "hidden significance", "obvious statement",
        "subtle implication", "explicit declaration", "nuanced suggestion", "blatant assertion",
        "whispered intimation", "shouted proclamation", "gentle insinuation", "forceful pronouncement",
        "polite suggestion", "demanding statement", "respectful address", "confrontational challenge",
        "inviting welcome", "defensive barrier", "open accessibility", "closed exclusion",
        "inclusive embrace", "selective discrimination", "universal appeal", "particular taste",
        "common ground", "specialized interest", "mainstream acceptance", "alternative perspective",
        "popular recognition", "exclusive appreciation", "mass appeal", "elite understanding",
        "democratic access", "privileged knowledge", "open source", "proprietary control",
        "free expression", "regulated communication", "liberated creativity", "constrained production",
        "unlimited possibility", "defined boundary", "infinite potential", "specific limitation",
        "expansive scope", "focused concentration", "comprehensive inclusion", "selective emphasis",
        "diverse multiplicity", "unified singularity", "pluralistic variety", "monolithic uniformity",
        "heterogeneous mixture", "homogeneous consistency", "varied collection", "uniform presentation",
        "eclectic assemblage", "coherent statement", "diverse gathering", "unified composition",
        "mixed media", "pure form", "combined techniques", "singular method",
        "hybrid approach", "purist discipline", "interdisciplinary crossing", "specialized focus",
        "boundary blurring", "category defining", "genre mixing", "type establishing",
        "convention challenging", "tradition upholding", "rule breaking", "principle following",
        "norm subverting", "standard maintaining", "revolutionary overthrow", "evolutionary development",
        "radical departure", "conservative continuation", "innovative advance", "traditional reference",
        "forward looking", "backward glancing", "progressive movement", "historical grounding",
        "futuristic vision", "nostalgic remembrance", "utopian imagination", "memorial preservation",
        "prophetic anticipation", "documentary record", "speculative projection", "historical documentation",
        "imaginative construction", "factual recording", "fictional creation", "truthful representation",
        "fantastical invention", "realistic depiction", "mythical narration", "actual description",
        "legendary recounting", "empirical observation", "fabulous elaboration", "scientific accuracy",
        "magical thinking", "logical reasoning", "irrational connection", "rational analysis",
        "intuitive understanding", "systematic investigation", "holistic comprehension", "reductive simplification",
        "synthetic integration", "analytic dissection", "unifying vision", "differentiating perception",
        "connecting relationship", "separating distinction", "associative linking", "dissociative breaking",
        "binding attachment", "severing detachment", "attracting affinity", "repelling aversion",
        "harmonizing reconciliation", "conflicting opposition", "balancing equilibrium", "destabilizing tension",
        "centering focus", "decentering dispersion", "grounding stability", "dislocating movement",
        "orienting direction", "disorienting confusion", "clarifying explanation", "mystifying complexity",
        "simplifying reduction", "complicating elaboration", "streamlining efficiency", "proliferating excess",
        "economizing restraint", "expanding development", "concentrating essence", "diluting diffusion",
        "intensifying concentration", "weakening dilution", "strengthening reinforcement", "diminishing reduction",
        "amplifying enhancement", "attenuating decrease", "magnifying enlargement", "minimizing diminishment",
        "maximizing expansion", "reducing contraction", "optimizing improvement", "degrading deterioration",
        "refining purification", "corrupting adulteration", "perfecting idealization", "flawing imperfection",
        "completing fulfillment", "fragmenting incompletion", "finishing conclusion", "sketching suggestion",
        "finalizing determination", "initiating beginning", "ending closure", "starting inception",
        "concluding termination", "commencing initiation", "finishing completion", "embarking departure",
        "arriving destination", "journeying process", "reaching goal", "wandering exploration",
        "achieving accomplishment", "searching quest", "finding discovery", "seeking investigation",
        "knowing certainty", "questioning doubt", "answering resolution", "inquiring curiosity",
        "solving solution", "problematizing complication", "resolving conclusion", "challenging difficulty",
        "clarifying explanation", "obscuring confusion", "illuminating revelation", "darkening mystery",
        "revealing disclosure", "concealing secrecy", "exposing visibility", "hiding invisibility",
        "opening access", "closing exclusion", "welcoming invitation", "rejecting refusal",
        "accepting embrace", "declining rejection", "affirming confirmation", "denying negation",
        "asserting declaration", "retracting withdrawal", "advocating support", "opposing resistance",
        "defending protection", "attacking aggression", "shielding cover", "exposing vulnerability",
        "strengthening reinforcement", "weakening undermining", "supporting foundation", "destabilizing erosion",
        "constructing building", "destroying demolition", "creating generation", "annihilating obliteration",
        "making formation", "unmaking dissolution", "forming shaping", "deforming distortion",
        "transforming change", "preserving conservation", "altering modification", "maintaining stability",
        "innovating novelty", "conserving tradition", "renovating renewal", "deteriorating decay",
        "evolving development", "devolving regression", "progressing advancement", "declining deterioration",
        "ascending rise", "descending fall", "climbing elevation", "sinking depression",
        "floating buoyancy", "sinking gravity", "flying liberation", "grounding attachment",
        "soaring transcendence", "rooting immanence", "elevating uplift", "deepening immersion",
        "expanding growth", "contracting reduction", "extending reach", "withdrawing retreat",
        "advancing progress", "receding withdrawal", "approaching proximity", "distancing separation",
        "connecting attachment", "disconnecting detachment", "joining union", "separating division",
        "unifying integration", "fragmenting disintegration", "harmonizing reconciliation", "conflicting opposition",
        "balancing equilibrium", "unbalancing disturbance", "stabilizing steadiness", "destabilizing fluctuation",
        "ordering organization", "disordering chaos", "structuring arrangement", "destructuring randomness",
        "patterning regularity", "scattering dispersion", "gathering collection", "dispersing distribution",
        "concentrating focus", "diluting diffusion", "intensifying density", "thinning sparsity",
        "thickening viscosity", "thinning fluidity", "solidifying fixity", "liquefying flow",
        "freezing immobility", "melting transformation", "cooling moderation", "heating intensification",
        "warming reception", "chilling distance", "burning passion", "freezing detachment",
        "inflaming excitement", "cooling calm", "igniting inspiration", "extinguishing suppression",
        "lighting illumination", "darkening obscurity", "brightening clarity", "dimming opacity",
        "focusing sharpness", "blurring diffusion", "defining precision", "obscuring vagueness",
        "specifying exactitude", "generalizing approximation", "detailing elaboration", "simplifying reduction",
        "complexifying intricacy", "streamlining efficiency", "complicating involvement", "clarifying distinction",
        "differentiating separation", "unifying connection", "diversifying variation", "homogenizing uniformity",
        "standardizing consistency", "customizing uniqueness", "conforming similarity", "deviating difference",
        "matching correspondence", "contrasting opposition", "resembling similarity", "differing distinction",
        "paralleling alignment", "diverging separation", "converging meeting", "interweaving integration",
        "intersecting crossing", "bypassing avoidance", "including incorporation", "excluding omission",
        "containing enclosure", "releasing freedom", "capturing confinement", "liberating emancipation",
        "restraining limitation", "enabling possibility", "constraining restriction", "facilitating assistance",
        "obstructing impediment", "supporting reinforcement", "blocking prevention", "permitting allowance",
        "prohibiting forbiddance", "authorizing permission", "forbidding prohibition", "mandating requirement",
        "requiring necessity", "offering possibility", "demanding insistence", "suggesting option",
        "commanding direction", "inviting participation", "controlling determination", "collaborating cooperation",
        "dominating subjugation", "equalizing balance", "superiority elevation", "inferiority subordination",
        "preceding antecedence", "following subsequence", "leading guidance", "trailing consequence",
        "guiding direction", "following conformity", "teaching instruction", "learning acquisition",
        "educating development", "training preparation", "cultivating nurture", "growing maturation",
        "evolving progression", "adapting adjustment", "modernizing advancement", "traditionalizing conservation",
        "contemporizing updating", "classicizing timelessness", "revolutionizing transformation", "conserving preservation",
        "reforming improvement", "maintaining stability", "correcting rectification", "accepting allowance",
        "improving enhancement", "deteriorating degradation", "refining purification", "corrupting adulteration",
        "clarifying explanation", "confusing obfuscation", "simplifying reduction", "complicating elaboration",
        "stylizing abstraction", "naturalizing representation", "idealizing perfection", "realizing actualization",
        "romanticizing sentimentalization", "dispassionate objectification", "dramatizing intensification", "understating moderation",
        "exaggerating amplification", "diminishing reduction", "enhancing augmentation", "lessening diminution",
        "intensifying concentration", "diluting diffusion", "strengthening reinforcement", "weakening attenuation",
        "emphasizing accentuation", "downplaying de-emphasis", "highlighting prominence", "obscuring recessiveness",
        "focusing attention", "distracting diversion", "attracting interest", "repelling aversion",
        "engaging involvement", "disengaging detachment", "immersing absorption", "distancing separation",
        "revealing disclosure", "concealing hiding", "exposing visibility", "masking concealment",
        "presenting showing", "withdrawing removal", "displaying exhibition", "hiding concealment",
        "performing demonstration", "reserving withholding", "proclaiming announcement", "silencing suppression",
        "declaring statement", "withholding reticence", "expressing communication", "censoring suppression",
        "articulating utterance", "muting silence", "vocalizing speech", "quieting stillness",
        "speaking language", "listening reception", "telling narration", "hearing audition",
        "writing inscription", "reading interpretation", "recording documentation", "interpreting understanding",
        "documenting evidence", "experiencing engagement", "witnessing observation", "participating involvement",
        "observing perception", "engaging interaction", "seeing vision", "touching contact",
        "looking viewing", "feeling sensation", "watching witnessing", "sensing perception",
        "perceiving awareness", "knowing understanding", "apprehending comprehension", "understanding knowledge",
        "comprehending grasp", "creating generation", "grasping apprehension", "making production",
        "conceiving conceptualization", "performing action", "planning design", "achieving accomplishment",
        "designing conception", "completing fulfillment", "imagining ideation", "finishing conclusion",
        "envisioning visualization", "starting commencement", "projecting anticipation", "beginning initiation",
        "predicting forecast", "ending termination", "prophesying foretelling", "concluding completion",
        "anticipating expectation", "arriving destination", "expecting anticipation", "departing leaving",
        "surprising unexpectedness", "journeying traveling", "shocking astonishment", "exploring discovery",
        "awing impression", "finding location", "amazing wonderment", "seeking search",
        "impressing effect", "questioning inquiry", "affecting influence", "answering response",
        "moving emotion", "responding reaction", "touching feeling", "reacting response",
        "stirring excitement", "relating connection", "exciting stimulation", "connecting relationship",
        "stimulating activation", "interacting engagement", "activating energizing", "engaging involvement",
        "energizing vitalization", "participating collaboration", "vitalizing invigoration", "collaborating cooperation",
        "invigorating revitalization", "cooperating coordination", "revitalizing rejuvenation", "coordinating organization",
        "rejuvenating renewal", "organizing arrangement", "renewing restoration", "arranging order",
        "restoring rehabilitation", "ordering systematization", "rehabilitating recovery", "systematizing methodology",
        "recovering retrieval", "methodizing procedure", "retrieving reclamation", "proceeding process",
        "reclaiming repossession", "processing treatment", "repossessing reacquisition", "treating handling",
        "reacquiring reattainment", "handling management", "reattaining regaining", "managing administration",
        "regaining recovery", "administering governance", "recovering restoration", "governing regulation",
        "restoring return", "regulating control", "returning reversion", "controlling determination",
        "reverting regression", "determining decision", "regressing retreat", "deciding resolution",
        "retreating withdrawal", "resolving solution", "withdrawing removal", "solving problem-solving",
        "removing extraction", "problem-solving resolution", "extracting taking", "resolving decision-making",
        "taking acquisition", "decision-making judgment", "acquiring obtaining", "judging evaluation",
        "obtaining procurement", "evaluating assessment", "procuring securing", "assessing appraisal",
        "securing protection", "appraising valuation", "protecting safeguarding", "valuing estimation",
        "safeguarding preservation", "estimating approximation", "preserving conservation", "approximating estimation",
        "conserving sustaining", "measuring quantification", "sustaining maintenance", "quantifying enumeration",
        "maintaining support", "enumerating counting", "supporting assistance", "counting calculation",
        "assisting help", "calculating computation", "helping aid", "computing processing",
        "aiding benefit", "processing operation", "benefiting advantage", "operating functioning",
        "advantaging profit", "functioning working", "profiting gain", "working action",
        "gaining acquisition", "acting performance", "acquiring obtaining", "performing execution",
        "obtaining procurement", "executing implementation", "procuring securing", "implementing realization",
        "securing protection", "realizing actualization", "protecting safeguarding", "actualizing manifestation",
        "safeguarding preservation", "manifesting expression", "preserving conservation", "expressing conveyance",
        "conserving sustaining", "conveying communication", "sustaining maintenance", "communicating transmission",
        "maintaining support", "transmitting broadcast", "supporting assistance", "broadcasting dissemination",
        "artistic approach", "creative methodology", "stylistic technique", "representational mode",
        "expresssionist brushwork", "impressionist lighting", "surrealist imagination", "cubist fragmentation",
        "abstract reduction", "minimalist simplification", "pop appropriation", "conceptual framework",
        "renaissance perspective", "baroque dynamism", "rococo elegance", "neoclassical order",
        "romantic passion", "realist observation", "symbolist suggestion", "futurist dynamism",
        "dadaist irreverence", "constructivist structure", "art deco elegance", "bauhaus functionality",
        "art nouveau organic", "post-impressionist color", "fauvist intensity", "vorticist energy",
        "precisionist clarity", "regionalist authenticity", "surrealist dream", "magical realist wonder",
        "social realist critique", "abstract expressionist gesture", "color field immersion", "hard edge precision",
        "op art illusion", "kinetic movement", "fluxus spontaneity", "happenings improvisation",
        "performance temporality", "land art intervention", "installation immersion", "conceptual idea",
        "body art embodiment", "funk assemblage", "pattern decoration", "new image painting",
        "bad painting deliberation", "transavanguardia eclecticism", "neo-expressionist emotion", "neo-geo criticism",
        "appropriation recontextualization", "simulation questioning", "new media exploration", "digital creation",
        "post-digital fusion", "internet connectivity", "virtual immersion", "augmented overlay",
        "interactive engagement", "generative evolution", "algorithmic pattern", "artificial intelligence",
        "bio art living", "eco art sustainability", "relational aesthetics", "social practice engagement",
        "participatory involvement", "institutional critique", "identity politics", "feminist perspective",
        "postcolonial examination", "queer visibility", "disability awareness", "intersectional understanding",
        "traditional craft", "indigenous knowledge", "folk authenticity", "outsider intuition",
        "visionary imagination", "self-taught directness", "art brut rawness", "naive charm",
        "street art rebellion", "graffiti energy", "public intervention", "activist statement",
        "political critique", "social commentary", "cultural analysis", "historical reference",
        "mythological allusion", "religious symbolism", "spiritual aspiration", "philosophical inquiry",
        "psychological exploration", "cognitive investigation", "emotional expression", "sensual engagement",
        "physical embodiment", "material specificity", "process emphasis", "conceptual foundation",
        "narrative development", "lyrical expression", "dramatic tension", "comedic release",
        "tragic depth", "epic scope", "intimate scale", "monumental presence",
        "miniature precision", "colossal impact", "site-specific relevance", "context-sensitive response",
        "historically grounded", "contemporarily relevant", "traditionally informed", "innovatively adventurous",
        "technically accomplished", "conceptually rigorous", "emotionally resonant", "intellectually stimulating",
        "visually captivating", "aesthetically pleasing", "culturally significant", "personally meaningful",
        "artistically masterful", "creatively inspired", "stylistically distinctive", "expressively powerful"
    ],
    "fantasy": [
        "breathtaking fantasy world", "beautiful mythical creatures", "winged fairy", "shimmering dragon", "glowing magic",
        "grand castle", "magical forest", "magical light effects", "legendary sword",
        "luxurious fantasy clothing", "elegant armor", "glowing mystical symbols", "dimensional portal",
        "mythological beasts", "unicorn", "phoenix", "centaur", "elf", "dwarf", "orc", 
        "glowing crystal stone", "magic wand", "magical potion", "ancient scroll",
        "enchanted realm", "mystical kingdom", "arcane dominion", "ethereal plane",
        "celestial sphere", "eldritch dimension", "faerie world", "shadow realm",
        "elemental domain", "astral projection", "dream landscape", "cosmic void",
        "heavenly paradise", "infernal abyss", "limbo expanse", "purgatorial realm",
        "divine sanctuary", "demonic domain", "angelic heights", "fiendish depths",
        "crystalline spires", "obsidian towers", "emerald citadel", "sapphire palace",
        "ruby fortress", "amethyst bastion", "diamond castle", "pearl monument",
        "golden temple", "silver shrine", "copper pavilion", "bronze stronghold",
        "platinum chamber", "jade sanctuary", "alabaster hall", "marble cathedral",
        "quartz formation", "onyx structure", "opal dwelling", "amber enclave",
        "floating island", "hovering mountain", "suspended city", "airborne village",
        "soaring fortress", "drifting continent", "levitating temple", "flying castle",
        "ancient ruins", "forgotten city", "lost civilization", "abandoned temple",
        "hidden sanctuary", "secret library", "mystical archive", "arcane repository",
        "magical laboratory", "alchemical workshop", "wizard's tower", "sorcerer's sanctum",
        "druid's grove", "shaman's circle", "witch's cottage", "necromancer's crypt",
        "paladin's bastion", "ranger's outpost", "barbarian's stronghold", "bard's tavern",
        "rogue's hideout", "monk's monastery", "cleric's temple", "warlock's haven",
        "vampire's castle", "werewolf's den", "ghost's haunt", "zombie's graveyard",
        "demon's lair", "angel's realm", "dragon's hoard", "giant's hall",
        "troll's bridge", "goblin's warren", "ogre's cave", "harpy's nest",
        "phoenix's roost", "griffin's eyrie", "unicorn's glade", "pegasus's cloud",
        "mermaid's lagoon", "siren's shore", "kraken's depth", "leviathan's trench",
        "fairy circle", "elven glade", "dwarven forge", "orcish encampment",
        "gnomish burrow", "halfling village", "human city", "giant's realm",
        "elemental plane", "fire domain", "water kingdom", "earth territory",
        "air sanctuary", "lightning realm", "ice domain", "metal kingdom",
        "wood territory", "light sanctuary", "shadow realm", "void domain",
        "time kingdom", "space territory", "gravity sanctuary", "entropy realm",
        "crystal forest", "metal woods", "glass jungle", "stone thicket",
        "lava field", "ice desert", "cloud archipelago", "mist marsh",
        "lightning plains", "thunder valley", "rainbow canyon", "aurora heights",
        "starfall meadow", "moondust desert", "sunlight prairie", "twilight forest",
        "dawn highlands", "dusk lowlands", "midnight peak", "noonday crater",
        "verdant wilderness", "desolate wasteland", "abundant oasis", "barren expanse",
        "lush paradise", "scorched hellscape", "fertile valley", "toxic badlands",
        "pristine sanctuary", "corrupted territory", "harmonious realm", "chaotic domain",
        "ordered dimension", "anarchic plane", "balanced world", "extremist reality",
        "peaceful kingdom", "warring nations", "allied territories", "enemy lands",
        "friendly outpost", "hostile fortress", "neutral ground", "contested region",
        "safe haven", "dangerous wilderness", "protected sanctuary", "exposed territory",
        "hidden realm", "revealed dimension", "obscured domain", "apparent plane",
        "lost world", "found kingdom", "forgotten empire", "remembered realm",
        "ancient civilization", "new settlement", "primordial land", "recent territory",
        "eternal domain", "temporary realm", "everlasting kingdom", "fleeting plane",
        "mythic world", "legendary kingdom", "fabled realm", "storied domain",
        "historical territory", "fictional world", "real dimension", "imagined plane",
        "physical realm", "spiritual domain", "material world", "ethereal kingdom",
        "tangible plane", "intangible dimension", "concrete reality", "abstract realm",
        "vibrant world", "muted kingdom", "colorful realm", "monochrome domain",
        "luminous plane", "shadowy dimension", "bright reality", "dark territory",
        "sunny land", "gloomy region", "clear skies", "stormy heavens",
        "calm waters", "turbulent seas", "gentle breeze", "howling winds",
        "solid ground", "shifting sands", "stable platform", "unstable terrain",
        "flat plains", "steep mountains", "rolling hills", "sheer cliffs",
        "deep valleys", "high peaks", "low basins", "tall spires",
        "wide rivers", "narrow streams", "vast oceans", "small ponds",
        "grand lakes", "tiny pools", "extensive swamps", "limited marshes",
        "dense forests", "sparse woods", "thick jungles", "thin groves",
        "lush meadows", "barren fields", "rich pastures", "poor grounds",
        "fertile soil", "sterile earth", "nutritious land", "toxic terrain",
        "magical currents", "mundane flows", "enchanted streams", "ordinary rivers",
        "arcane winds", "normal breezes", "mystical lights", "common illumination",
        "supernatural phenomena", "natural occurrences", "paranormal events", "regular happenings",
        "extraordinary sights", "ordinary views", "remarkable visions", "unremarkable scenes",
        "fantastical creatures", "mundane animals", "mythical beasts", "common critters",
        "legendary monsters", "everyday predators", "fabled entities", "regular fauna",
        "magical vegetation", "normal plants", "enchanted flora", "ordinary botany",
        "arcane fungi", "common mushrooms", "mystical roots", "regular tubers",
        "supernatural weather", "natural climate", "paranormal seasons", "regular cycles",
        "extraordinary atmospheres", "ordinary environments", "remarkable habitats", "unremarkable ecosystems",
        "mystical barrier", "physical wall", "enchanted boundary", "normal fence",
        "arcane threshold", "common doorway", "magical entrance", "ordinary portal",
        "supernatural gateway", "natural opening", "paranormal passage", "regular entrance",
        "legendary artifact", "common tool", "mythical weapon", "ordinary implement",
        "enchanted relic", "normal object", "magical item", "mundane thing",
        "arcane trinket", "everyday bauble", "mystical talisman", "regular charm",
        "divine blessing", "normal benefit", "celestial favor", "ordinary advantage",
        "infernal curse", "common problem", "demonic hex", "everyday trouble",
        "wizardly spell", "normal technique", "sorcerous incantation", "ordinary method",
        "druidic ritual", "regular routine", "shamanic ceremony", "everyday practice",
        "clerical prayer", "normal request", "paladin's oath", "ordinary promise",
        "bardic song", "common tune", "ranger's call", "everyday signal",
        "rogue's trick", "normal deception", "monk's technique", "ordinary skill",
        "magical energy", "normal power", "mana stream", "everyday force",
        "arcane potential", "common ability", "mystical capacity", "ordinary capability",
        "spellcasting focus", "normal tool", "ritual component", "everyday ingredient",
        "alchemical substance", "common material", "magical essence", "ordinary matter",
        "elemental force", "normal energy", "primal power", "everyday strength",
        "divine might", "common potency", "celestial energy", "ordinary vigor",
        "infernal power", "normal influence", "demonic force", "everyday impact",
        "royal lineage", "common ancestry", "noble bloodline", "ordinary heritage",
        "magical heritage", "normal background", "enchanted legacy", "ordinary inheritance",
        "destined hero", "common protagonist", "chosen one", "ordinary champion",
        "prophesied savior", "normal rescuer", "foretold defender", "everyday protector",
        "legendary villain", "common antagonist", "mythical adversary", "ordinary opponent",
        "ancient evil", "normal threat", "primordial darkness", "everyday danger",
        "doomsday prophecy", "common prediction", "apocalyptic foretelling", "ordinary forecast",
        "world-saving quest", "normal mission", "realm-preserving journey", "everyday task",
        "magical transformation", "normal change", "enchanted metamorphosis", "ordinary alteration",
        "mythical rebirth", "common renewal", "legendary resurrection", "ordinary revival",
        "divine intervention", "normal assistance", "celestial aid", "everyday help",
        "fateful encounter", "common meeting", "destined rendezvous", "ordinary introduction",
        "magical bond", "normal connection", "enchanted link", "ordinary relationship",
        "legendary alliance", "common partnership", "mythical fellowship", "ordinary association",
        "ancient feud", "normal disagreement", "age-old conflict", "everyday dispute",
        "kingdom politics", "normal governance", "realm diplomacy", "everyday leadership",
        "royal court", "common gathering", "noble assembly", "ordinary meeting",
        "magical contest", "normal competition", "enchanted tournament", "ordinary game",
        "legendary battle", "common fight", "mythical warfare", "ordinary conflict",
        "arcane research", "normal study", "mystical investigation", "ordinary inquiry",
        "forbidden knowledge", "common information", "secret wisdom", "everyday facts",
        "hidden truth", "normal reality", "concealed verity", "ordinary actuality",
        "ancient prophecy", "common prediction", "legendary foretelling", "ordinary forecast",
        "destined future", "normal prospects", "fated outcome", "everyday eventuality",
        "mystical past", "common history", "enchanted antiquity", "ordinary yesteryear",
        "magical phenomenon", "normal occurrence", "enchanted event", "ordinary happening",
        "supernatural manifestation", "natural appearance", "paranormal materialization", "regular presentation",
        "arcane theory", "common idea", "mystical concept", "ordinary notion",
        "magical practice", "normal activity", "enchanted exercise", "ordinary routine",
        "wizardly tradition", "common custom", "sorcerous convention", "ordinary habit",
        "alchemical process", "normal procedure", "transmutation method", "everyday technique",
        "magical creation", "normal production", "enchanted generation", "ordinary making",
        "arcane destruction", "common demolition", "mystical obliteration", "ordinary removal",
        "supernatural preservation", "natural conservation", "paranormal protection", "regular safeguarding",
        "magical healing", "normal recovery", "enchanted restoration", "ordinary mending",
        "arcane connection", "common link", "mystical bond", "ordinary tie",
        "supernatural communication", "natural exchange", "paranormal contact", "regular interaction",
        "magical perception", "normal sensing", "enchanted awareness", "ordinary detection",
        "arcane concealment", "common hiding", "mystical cloaking", "ordinary obscurement",
        "supernatural revelation", "natural disclosure", "paranormal unveiling", "regular exposure",
        "magical deception", "normal trickery", "enchanted illusion", "ordinary falsity",
        "arcane truth", "common fact", "mystical reality", "ordinary actuality",
        "supernatural power", "natural ability", "paranormal capability", "regular faculty",
        "magical limitation", "normal restriction", "enchanted constraint", "ordinary boundary",
        "arcane potential", "common possibility", "mystical capacity", "ordinary capability",
        "supernatural destiny", "natural fate", "paranormal predestination", "regular future",
        "magical origin", "normal beginning", "enchanted source", "ordinary start",
        "arcane end", "common finale", "mystical conclusion", "ordinary termination",
        "supernatural cycle", "natural period", "paranormal rotation", "regular revolution",
        "magical balance", "normal equilibrium", "enchanted harmony", "ordinary stability",
        "arcane chaos", "common disorder", "mystical entropy", "ordinary randomness",
        "supernatural order", "natural arrangement", "paranormal organization", "regular structure",
        "magical growth", "normal development", "enchanted expansion", "ordinary increase",
        "arcane decay", "common deterioration", "mystical diminishment", "ordinary reduction",
        "supernatural life", "natural existence", "paranormal vitality", "regular being",
        "magical death", "normal ending", "enchanted cessation", "ordinary conclusion",
        "arcane undeath", "common persistence", "mystical continuation", "ordinary endurance",
        "supernatural immortality", "natural mortality", "paranormal eternality", "regular temporality",
        "magical mutation", "normal variation", "enchanted deviation", "ordinary difference",
        "arcane evolution", "common development", "mystical advancement", "ordinary progress",
        "supernatural regression", "natural reversion", "paranormal retrogression", "regular return",
        "magical adaptation", "normal adjustment", "enchanted accommodation", "ordinary modification",
        "arcane resistance", "common opposition", "mystical immunity", "ordinary defense",
        "supernatural vulnerability", "natural susceptibility", "paranormal weakness", "regular frailty",
        "magical strength", "normal power", "enchanted might", "ordinary force",
        "arcane intelligence", "common intellect", "mystical wisdom", "ordinary knowledge",
        "supernatural intuition", "natural instinct", "paranormal perception", "regular sense",
        "magical emotion", "normal feeling", "enchanted sensation", "ordinary experience",
        "arcane personality", "common character", "mystical temperament", "ordinary disposition",
        "supernatural consciousness", "natural awareness", "paranormal cognizance", "regular mindfulness",
        "magical dreams", "normal visions", "enchanted reveries", "ordinary fantasies",
        "arcane nightmares", "common terrors", "mystical horrors", "ordinary fears",
        "supernatural desires", "natural wants", "paranormal yearnings", "regular cravings",
        "magical needs", "normal requirements", "enchanted necessities", "ordinary essentials",
        "arcane satisfaction", "common contentment", "mystical fulfillment", "ordinary gratification",
        "supernatural pleasure", "natural enjoyment", "paranormal delight", "regular happiness",
        "magical pain", "normal suffering", "enchanted agony", "ordinary discomfort",
        "arcane sorrow", "common sadness", "mystical melancholy", "ordinary unhappiness",
        "supernatural rage", "natural anger", "paranormal fury", "regular irritation",
        "magical serenity", "normal calmness", "enchanted tranquility", "ordinary peace",
        "arcane love", "common affection", "mystical adoration", "ordinary fondness",
        "supernatural hatred", "natural dislike", "paranormal loathing", "regular aversion",
        "magical indifference", "normal apathy", "enchanted detachment", "ordinary unconcern",
        "arcane interest", "common curiosity", "mystical inquisitiveness", "ordinary concern",
        "supernatural obsession", "natural preoccupation", "paranormal fixation", "regular attachment",
        "magical loyalty", "normal faithfulness", "enchanted allegiance", "ordinary dedication",
        "arcane betrayal", "common treachery", "mystical faithlessness", "ordinary disloyalty",
        "supernatural trust", "natural confidence", "paranormal reliance", "regular dependence",
        "magical suspicion", "normal doubt", "enchanted skepticism", "ordinary mistrust",
        "arcane justice", "common fairness", "mystical equity", "ordinary impartiality",
        "supernatural injustice", "natural unfairness", "paranormal inequity", "regular partiality",
        "magical honor", "normal integrity", "enchanted virtue", "ordinary morality",
        "arcane corruption", "common depravity", "mystical wickedness", "ordinary immorality",
        "supernatural purity", "natural wholesomeness", "paranormal goodness", "regular decency",
        "magical taint", "normal stain", "enchanted contamination", "ordinary impurity",
        "arcane blessing", "common benefit", "mystical advantage", "ordinary gain",
        "supernatural curse", "natural drawback", "paranormal disadvantage", "regular loss",
        "magical legacy", "normal heritage", "enchanted inheritance", "ordinary bequest",
        "arcane destiny", "common fate", "mystical kismet", "ordinary future",
        "supernatural chance", "natural opportunity", "paranormal possibility", "regular prospect",
        "magical risk", "normal danger", "enchanted peril", "ordinary hazard",
        "arcane safety", "common security", "mystical protection", "ordinary defense",
        "supernatural vulnerability", "natural exposure", "paranormal susceptibility", "regular openness",
        "magical victory", "normal success", "enchanted triumph", "ordinary achievement",
        "arcane defeat", "common failure", "mystical loss", "ordinary disappointment",
        "supernatural glory", "natural prestige", "paranormal honor", "regular recognition",
        "magical shame", "normal disgrace", "enchanted dishonor", "ordinary embarrassment",
        "arcane prosperity", "common wealth", "mystical abundance", "ordinary plenty",
        "supernatural poverty", "natural scarcity", "paranormal lack", "regular insufficiency",
        "magical growth", "normal increase", "enchanted expansion", "ordinary enlargement",
        "arcane diminishment", "common decrease", "mystical reduction", "ordinary shrinkage",
        "supernatural creation", "natural generation", "paranormal formation", "regular production",
        "magical destruction", "normal demolition", "enchanted annihilation", "ordinary removal",
        "arcane construction", "common building", "mystical assembly", "ordinary composition",
        "supernatural deconstruction", "natural dismantling", "paranormal disassembly", "regular decomposition",
        "magical appearance", "normal materialization", "enchanted manifestation", "ordinary emergence",
        "arcane disappearance", "common vanishing", "mystical dematerialization", "ordinary fading",
        "supernatural transformation", "natural change", "paranormal metamorphosis", "regular alteration",
        "magical stasis", "normal stability", "enchanted immutability", "ordinary constancy",
        "arcane revolution", "common upheaval", "mystical overturning", "ordinary overthrowing",
        "supernatural evolution", "natural development", "paranormal progression", "regular advancement",
        "magical entropy", "normal disorder", "enchanted chaos", "ordinary randomness",
        "arcane harmony", "common order", "mystical balance", "ordinary equilibrium",
        "supernatural discord", "natural conflict", "paranormal dissonance", "regular disagreement",
        "magical peace", "normal tranquility", "enchanted serenity", "ordinary calm",
        "arcane war", "common hostility", "mystical conflict", "ordinary struggle",
        "supernatural alliance", "natural cooperation", "paranormal partnership", "regular collaboration",
        "magical isolation", "normal separation", "enchanted solitude", "ordinary aloneness",
        "arcane connection", "common linkage", "mystical bond", "ordinary attachment",
        "supernatural disconnection", "natural detachment", "paranormal severance", "regular separation",
        "magical unity", "normal togetherness", "enchanted wholeness", "ordinary completeness",
        "arcane division", "common partition", "mystical separation", "ordinary segmentation",
        "supernatural community", "natural society", "paranormal collective", "regular group",
        "magical individuality", "normal uniqueness", "enchanted singularity", "ordinary distinctiveness",
        "arcane conformity", "common similarity", "mystical sameness", "ordinary likeness",
        "supernatural diversity", "natural variety", "paranormal multiplicity", "regular difference",
        "magical hierarchy", "normal ranking", "enchanted stratification", "ordinary classification",
        "arcane equality", "common parity", "mystical equivalence", "ordinary sameness",
        "supernatural superiority", "natural advantage", "paranormal ascendancy", "regular dominance",
        "magical inferiority", "normal disadvantage", "enchanted subordination", "ordinary submission",
        "arcane dominance", "common control", "mystical mastery", "ordinary command",
        "supernatural submission", "natural yielding", "paranormal surrender", "regular acquiescence",
        "magical freedom", "normal liberty", "enchanted independence", "ordinary autonomy",
        "arcane constraint", "common limitation", "mystical restriction", "ordinary confinement",
        "supernatural empowerment", "natural enablement", "paranormal authorization", "regular permission",
        "magical prohibition", "normal forbiddance", "enchanted prevention", "ordinary interdiction",
        "arcane knowledge", "common information", "mystical understanding", "ordinary comprehension",
        "supernatural ignorance", "natural unawareness", "paranormal obliviousness", "regular unconsciousness",
        "magical wisdom", "normal insight", "enchanted sagacity", "ordinary prudence",
        "arcane folly", "common foolishness", "mystical imprudence", "ordinary thoughtlessness",
        "supernatural invention", "natural creation", "paranormal innovation", "regular origination",
        "magical discovery", "normal finding", "enchanted revelation", "ordinary uncovering",
        "arcane research", "common investigation", "mystical exploration", "ordinary inquiry",
        "supernatural intuition", "natural instinct", "paranormal sense", "regular feeling",
        "magical calculation", "normal computation", "enchanted reckoning", "ordinary figuring",
        "arcane instinct", "common impulse", "mystical urge", "ordinary inclination",
        "supernatural memory", "natural recollection", "paranormal remembrance", "regular recall",
        "magical forgetting", "normal amnesia", "enchanted oblivion", "ordinary forgetfulness",
        "arcane learning", "common education", "mystical instruction", "ordinary teaching",
        "supernatural training", "natural practice", "paranormal exercise", "regular drill",
        "magical mastery", "normal accomplishment", "enchanted proficiency", "ordinary competence",
        "arcane incompetence", "common ineptitude", "mystical failure", "ordinary deficiency",
        "supernatural skill", "natural ability", "paranormal talent", "regular aptitude",
        "magical gift", "normal endowment", "enchanted present", "ordinary ability",
        "arcane talent", "common aptitude", "mystical knack", "ordinary capacity",
        "supernatural prowess", "natural capability", "paranormal faculty", "regular proficiency",
        "magical might", "normal strength", "enchanted power", "ordinary force",
        "arcane weakness", "common frailty", "mystical feebleness", "ordinary debility",
        "supernatural vitality", "natural energy", "paranormal vigor", "regular liveliness",
        "magical exhaustion", "normal fatigue", "enchanted weariness", "ordinary tiredness",
        "arcane health", "common wellness", "mystical soundness", "ordinary robustness",
        "supernatural sickness", "natural illness", "paranormal disease", "regular malady",
        "magical longevity", "normal lifespan", "enchanted durability", "ordinary duration",
        "arcane mortality", "common finiteness", "mystical temporality", "ordinary limitedness",
        "supernatural immortality", "natural eternity", "paranormal perpetuity", "regular endlessness",
        "magical finiteness", "normal limitation", "enchanted restriction", "ordinary boundary",
        "arcane infinity", "common boundlessness", "mystical limitlessness", "ordinary endlessness",
        "supernatural expansion", "natural growth", "paranormal enlargement", "regular increase",
        "magical contraction", "normal shrinkage", "enchanted reduction", "ordinary decrease",
        "arcane multiplication", "common proliferation", "mystical augmentation", "ordinary expansion",
        "supernatural division", "natural splitting", "paranormal separation", "regular partitioning",
        "magical addition", "normal increase", "enchanted supplementation", "ordinary enhancement",
        "arcane subtraction", "common decrease", "mystical diminution", "ordinary reduction",
        "supernatural combination", "natural mixture", "paranormal blend", "regular fusion",
        "magical separation", "normal division", "enchanted segregation", "ordinary isolation",
        "arcane unification", "common joining", "mystical merging", "ordinary combination",
        "supernatural fragmentation", "natural breaking", "paranormal shattering", "regular splintering",
        "magical wholeness", "normal completeness", "enchanted entirety", "ordinary totality",
        "arcane partiality", "common incompleteness", "mystical portion", "ordinary segment",
        "supernatural fullness", "natural entirety", "paranormal completeness", "regular wholeness",
        "magical emptiness", "normal vacancy", "enchanted void", "ordinary hollowness",
        "arcane presence", "common existence", "mystical being", "ordinary entity",
        "supernatural absence", "natural nonexistence", "paranormal nonbeing", "regular nonentity",
        "magical substance", "normal matter", "enchanted material", "ordinary stuff",
        "arcane essence", "common quintessence", "mystical spirit", "ordinary soul",
        "supernatural form", "natural shape", "paranormal configuration", "regular arrangement",
        "magical formlessness", "normal amorphousness", "enchanted shapelessness", "ordinary indeterminacy",
        "arcane pattern", "common design", "mystical arrangement", "ordinary configuration",
        "supernatural randomness", "natural chaos", "paranormal disorder", "regular entropy",
        "magical symmetry", "normal balance", "enchanted equilibrium", "ordinary evenness",
        "arcane asymmetry", "common imbalance", "mystical disequilibrium", "ordinary unevenness",
        "supernatural beauty", "natural attractiveness", "paranormal allure", "regular loveliness",
        "magical ugliness", "normal unattractiveness", "enchanted repulsiveness", "ordinary unsightliness",
        "arcane perfection", "common flawlessness", "mystical impeccability", "ordinary excellence",
        "supernatural imperfection", "natural flaw", "paranormal defect", "regular shortcoming",
        "magical idealism", "normal perfectionism", "enchanted utopianism", "ordinary optimism",
        "arcane realism", "common pragmatism", "mystical practicality", "ordinary rationality",
        "supernatural fantasy", "natural imagination", "paranormal unreality", "regular fiction",
        "magical reality", "normal actuality", "enchanted factuality", "ordinary truth",
        "arcane dream", "common vision", "mystical reverie", "ordinary fantasy",
        "supernatural nightmare", "natural terror", "paranormal horror", "regular fear",
        "magical consciousness", "normal awareness", "enchanted mindfulness", "ordinary attention",
        "arcane unconsciousness", "common unawareness", "mystical oblivion", "ordinary inattention",
        "supernatural wakefulness", "natural alertness", "paranormal vigilance", "regular attentiveness",
        "magical sleep", "normal slumber", "enchanted rest", "ordinary repose",
        "arcane dream", "common reverie", "mystical vision", "ordinary fantasy",
        "supernatural telepathy", "natural communication", "paranormal transmission", "regular sharing",
        "magical clairvoyance", "normal sight", "enchanted vision", "ordinary perception",
        "arcane precognition", "common foresight", "mystical foreknowledge", "ordinary prediction",
        "supernatural retrocognition", "natural memory", "paranormal recall", "regular remembrance",
        "magical empathy", "normal understanding", "enchanted comprehension", "ordinary sympathy",
        "arcane telekinesis", "common moving", "mystical manipulation", "ordinary handling",
        "supernatural pyrokinesis", "natural burning", "paranormal ignition", "regular combustion",
        "magical cryokinesis", "normal freezing", "enchanted chilling", "ordinary cooling",
        "arcane electrokinesis", "common shocking", "mystical electrification", "ordinary charging",
        "supernatural hydrokinesis", "natural wetting", "paranormal soaking", "regular dampening",
        "magical geokinesis", "normal earthmoving", "enchanted terraforming", "ordinary excavation",
        "arcane aerokinesis", "common blowing", "mystical ventilation", "ordinary fanning",
        "supernatural photokinesis", "natural illumination", "paranormal lighting", "regular brightening",
        "magical umbrakinesis", "normal darkening", "enchanted dimming", "ordinary shadowing",
        "arcane biokinesis", "common healing", "mystical regeneration", "ordinary mending",
        "supernatural necrokinesis", "natural death", "paranormal dying", "regular expiration",
        "magical technokinesis", "normal operation", "enchanted manipulation", "ordinary control",
        "arcane chronokinesis", "common timing", "mystical scheduling", "ordinary planning",
        "supernatural dimensiokinesis", "natural spacing", "paranormal placement", "regular positioning",
        "magical levitation", "normal floating", "enchanted hovering", "ordinary suspension",
        "arcane flight", "common soaring", "mystical gliding", "ordinary flying",
        "supernatural invisibility", "natural concealment", "paranormal hiding", "regular obscurement",
        "magical intangibility", "normal immateriality", "enchanted insubstantiality", "ordinary ghostliness",
        "arcane invulnerability", "common immunity", "mystical imperviousness", "ordinary resistance",
        "supernatural regeneration", "natural healing", "paranormal recovery", "regular mending",
        "magical shapeshifting", "normal changing", "enchanted transforming", "ordinary altering",
        "arcane duplication", "common copying", "mystical replication", "ordinary reproduction",
        "supernatural immortality", "natural longevity", "paranormal eternality", "regular endurance",
        "magical omniscience", "normal knowledge", "enchanted wisdom", "ordinary understanding",
        "arcane omnipotence", "common power", "mystical strength", "ordinary capability",
        "supernatural omnipresence", "natural presence", "paranormal existence", "regular being",
        "magical divination", "normal prediction", "enchanted forecasting", "ordinary prophecy",
        "arcane necromancy", "common death-magic", "mystical undeath", "ordinary mortuary",
        "supernatural transmutation", "natural changing", "paranormal transforming", "regular altering",
        "magical enchantment", "normal charming", "enchanted bewitching", "ordinary fascinating",
        "arcane illusion", "common deception", "mystical trickery", "ordinary falsity",
        "supernatural evocation", "natural calling", "paranormal summoning", "regular invoking",
        "magical conjuration", "normal creation", "enchanted manifestation", "ordinary generation",
        "arcane abjuration", "common protection", "mystical warding", "ordinary shielding",
        "supernatural healing", "natural mending", "paranormal curing", "regular repairing",
        "magical harming", "normal hurting", "enchanted injuring", "ordinary damaging",
        "arcane animation", "common enlivening", "mystical vivification", "ordinary energizing",
        "supernatural binding", "natural restraining", "paranormal constraining", "regular limiting",
        "magical banishing", "normal expelling", "enchanted exorcising", "ordinary removing",
        "arcane summoning", "common calling", "mystical invoking", "ordinary beckoning",
        "supernatural commanding", "natural ordering", "paranormal directing", "regular instructing",
        "magical mind-control", "normal persuasion", "enchanted influence", "ordinary suggestion",
        "arcane scrying", "common viewing", "mystical observing", "ordinary watching",
        "supernatural teleporting", "natural traveling", "paranormal transporting", "regular moving",
        "magical flying", "normal soaring", "enchanted gliding", "ordinary hovering",
        "arcane invisibility", "common concealment", "mystical disguise", "ordinary hiding",
        "supernatural intangibility", "natural immateriality", "paranormal insubstantiality", "regular ghostliness",
        "magical time-travel", "normal chronological-movement", "enchanted temporal-shift", "ordinary time-displacement",
        "arcane prophecy", "common prediction", "mystical forecasting", "ordinary foretelling",
        "supernatural portal", "natural doorway", "paranormal gateway", "regular entrance",
        "magical dimensional-travel", "normal realm-shifting", "enchanted plane-walking", "ordinary world-hopping",
        "arcane wish-granting", "common desire-fulfillment", "mystical want-satisfaction", "ordinary craving-fulfillment",
        "supernatural luck", "natural fortune", "paranormal chance", "regular happenstance",
        "magical destiny", "normal fate", "enchanted kismet", "ordinary predestination",
        "arcane reality-manipulation", "common situation-changing", "mystical circumstance-altering", "ordinary condition-modifying",
        "supernatural mind-reading", "natural thought-sensing", "paranormal mentality-scanning", "regular idea-detecting",
        "magical emotional-manipulation", "normal feeling-changing", "enchanted sentiment-altering", "ordinary mood-modifying",
        "arcane memory-modification", "common recollection-changing", "mystical remembrance-altering", "ordinary recall-adjusting",
        "supernatural dream-manipulation", "natural sleep-influencing", "paranormal reverie-adjusting", "regular fantasy-changing",
        "magical soul-manipulation", "normal spirit-alteration", "enchanted essence-modification", "ordinary being-adjustment",
        "arcane life-force-manipulation", "common vitality-alteration", "mystical energy-modification", "ordinary vivacity-adjustment",
        "supernatural elemental-control", "natural element-direction", "paranormal element-mastery", "regular element-handling",
        "magical weather-control", "normal meteorological-influence", "enchanted climate-mastery", "ordinary atmospheric-handling",
        "arcane nature-manipulation", "common environmental-influence", "mystical ecological-control", "ordinary surroundings-handling",
        "supernatural animal-control", "natural fauna-influence", "paranormal beast-mastery", "regular creature-handling",
        "magical plant-manipulation", "normal flora-influence", "enchanted vegetative-control", "ordinary greenery-handling",
        "arcane metal-control", "common ore-influence", "mystical metallurgical-mastery", "ordinary alloy-handling",
        "supernatural gravity-manipulation", "natural weight-adjustment", "paranormal mass-control", "regular density-handling",
        "magical light-control", "normal illumination-adjustment", "enchanted brightness-mastery", "ordinary radiance-handling",
        "arcane shadow-manipulation", "common darkness-influence", "mystical obscurity-control", "ordinary shade-handling",
        "supernatural sound-control", "natural acoustic-adjustment", "paranormal auditory-mastery", "regular noise-handling",
        "magical silence-manipulation", "normal quietness-influence", "enchanted stillness-control", "ordinary muteness-handling",
        "arcane force-manipulation", "common pressure-adjustment", "mystical energy-control", "ordinary power-handling",
        "supernatural friction-control", "natural resistance-adjustment", "paranormal drag-mastery", "regular impedance-handling",
        "magical magnetic-manipulation", "normal attraction-adjustment", "enchanted polarity-control", "ordinary magnetism-handling",
        "arcane electrical-control", "common current-adjustment", "mystical charge-mastery", "ordinary electricity-handling",
        "supernatural thermal-manipulation", "natural temperature-adjustment", "paranormal heat-control", "regular warmth-handling",
        "magical freezing-control", "normal cold-adjustment", "enchanted chill-mastery", "ordinary frost-handling",
        "arcane acid-manipulation", "common corrosive-adjustment", "mystical caustic-control", "ordinary dissolvent-handling",
        "supernatural poison-control", "natural toxin-adjustment", "paranormal venom-mastery", "regular toxicant-handling",
        "magical disease-manipulation", "normal illness-adjustment", "enchanted malady-control", "ordinary ailment-handling",
        "arcane age-manipulation", "common time-adjustment", "mystical era-control", "ordinary period-handling",
        "supernatural emotion", "natural feeling", "paranormal sentiment", "regular mood",
        "magical happiness", "normal joy", "enchanted gladness", "ordinary pleasure",
        "arcane sadness", "common sorrow", "mystical grief", "ordinary melancholy",
        "supernatural anger", "natural rage", "paranormal fury", "regular irritation",
        "magical fear", "normal terror", "enchanted dread", "ordinary fright",
        "arcane love", "common affection", "mystical fondness", "ordinary attachment",
        "supernatural hate", "natural dislike", "paranormal loathing", "regular aversion",
        "magical jealousy", "normal envy", "enchanted covetousness", "ordinary resentment",
        "arcane surprise", "common astonishment", "mystical amazement", "ordinary wonderment",
        "supernatural disgust", "natural revulsion", "paranormal repugnance", "regular aversion",
        "magical anticipation", "normal expectation", "enchanted awaiting", "ordinary looking-forward",
        "arcane trust", "common faith", "mystical confidence", "ordinary reliance",
        "supernatural suspicion", "natural doubt", "paranormal skepticism", "regular mistrust",
        "magical compassion", "normal empathy", "enchanted sympathy", "ordinary kindness",
        "arcane cruelty", "common harshness", "mystical callousness", "ordinary unkindness",
        "supernatural courage", "natural bravery", "paranormal valor", "regular fearlessness",
        "magical cowardice", "normal timidity", "enchanted fearfulness", "ordinary apprehension",
        "arcane pride", "common dignity", "mystical self-respect", "ordinary self-esteem",
        "supernatural humility", "natural modesty", "paranormal unpretentiousness", "regular unassumingness",
        "magical patience", "normal forbearance", "enchanted tolerance", "ordinary endurance",
        "arcane impatience", "common hastiness", "mystical intolerance", "ordinary restlessness",
        "supernatural calmness", "natural serenity", "paranormal tranquility", "regular composure",
        "magical agitation", "normal disturbance", "enchanted unrest", "ordinary disquiet",
        "arcane curiosity", "common inquisitiveness", "mystical wonderment", "ordinary interest",
        "supernatural indifference", "natural apathy", "paranormal unconcern", "regular disinterest",
        "magical excitement", "normal enthusiasm", "enchanted exhilaration", "ordinary eagerness",
        "arcane boredom", "common tedium", "mystical ennui", "ordinary dullness",
        "supernatural satisfaction", "natural contentment", "paranormal gratification", "regular fulfillment",
        "magical dissatisfaction", "normal discontentment", "enchanted frustration", "ordinary unfulfillment",
        "arcane hope", "common optimism", "mystical expectation", "ordinary anticipation",
        "supernatural despair", "natural pessimism", "paranormal hopelessness", "regular despondency",
        "magical confidence", "normal assurance", "enchanted self-belief", "ordinary self-assurance",
        "arcane insecurity", "common self-doubt", "mystical uncertainty", "ordinary apprehension",
        "supernatural confusion", "natural bewilderment", "paranormal perplexity", "regular puzzlement",
        "magical understanding", "normal comprehension", "enchanted grasp", "ordinary apprehension",
        "arcane wisdom", "common sagacity", "mystical enlightenment", "ordinary insight",
        "supernatural foolishness", "natural folly", "paranormal unwisdom", "regular silliness",
        "magical intelligence", "normal intellect", "enchanted brilliance", "ordinary cleverness",
        "arcane stupidity", "common dullness", "mystical denseness", "ordinary slowness",
        "supernatural knowledge", "natural information", "paranormal lore", "regular data",
        "magical ignorance", "normal unawareness", "enchanted cluelessness", "ordinary uninformedness",
        "arcane sense", "common perception", "mystical awareness", "ordinary detection",
        "supernatural blindness", "natural sightlessness", "paranormal unseeing", "regular nonperception",
        "magical insight", "normal perception", "enchanted discernment", "ordinary recognition",
        "arcane obliviousness", "common unawareness", "mystical unconsciousness", "ordinary inattention",
        "supernatural intuition", "natural instinct", "paranormal hunch", "regular gut-feeling",
        "magical rationality", "normal reasonableness", "enchanted logic", "ordinary sense",
        "arcane irrationality", "common unreasonableness", "mystical illogicality", "ordinary senselessness",
        "supernatural creativity", "natural imagination", "paranormal inventiveness", "regular innovativeness",
        "magical unoriginality", "normal unimaginativeness", "enchanted uninventiveness", "ordinary conventionality",
        "arcane memory", "common recollection", "mystical remembrance", "ordinary recall",
        "supernatural forgetfulness", "natural amnesia", "paranormal oblivion", "regular obliviousness",
        "magical morality", "normal ethics", "enchanted principles", "ordinary values",
        "arcane immorality", "common unethicalness", "mystical unprincipledness", "ordinary valuelessness",
        "supernatural goodness", "natural virtue", "paranormal righteousness", "regular decency",
        "magical evil", "normal vice", "enchanted wickedness", "ordinary badness",
        "arcane justice", "common fairness", "mystical equity", "ordinary impartiality",
        "supernatural injustice", "natural unfairness", "paranormal inequity", "regular partiality",
        "magical harmony", "normal accord", "enchanted agreement", "ordinary concord",
        "arcane conflict", "common discord", "mystical disagreement", "ordinary disharmony",
        "supernatural peace", "natural tranquility", "paranormal calmness", "regular serenity",
        "magical war", "normal hostility", "enchanted strife", "ordinary conflict",
        "arcane unity", "common solidarity", "mystical cohesion", "ordinary togetherness",
        "supernatural division", "natural separation", "paranormal schism", "regular split",
        "magical alliance", "normal partnership", "enchanted coalition", "ordinary association",
        "arcane enmity", "common antagonism", "mystical hostility", "ordinary opposition",
        "supernatural friendship", "natural camaraderie", "paranormal companionship", "regular amity",
        "magical hostility", "normal animosity", "enchanted animus", "ordinary ill-will",
        "arcane loyalty", "common faithfulness", "mystical allegiance", "ordinary fidelity",
        "supernatural betrayal", "natural faithlessness", "paranormal treachery", "regular disloyalty",
        "magical trust", "normal confidence", "enchanted faith", "ordinary belief",
        "arcane suspicion", "common distrust", "mystical doubt", "ordinary skepticism",
        "supernatural support", "natural assistance", "paranormal aid", "regular help",
        "magical opposition", "normal hindrance", "enchanted obstruction", "ordinary impediment",
        "arcane cooperation", "common collaboration", "mystical teamwork", "ordinary joint-effort",
        "supernatural competition", "natural contest", "paranormal rivalry", "regular challenge",
        "magical leadership", "normal guidance", "enchanted direction", "ordinary steering",
        "arcane following", "common adherence", "mystical discipleship", "ordinary subordination",
        "supernatural obedience", "natural compliance", "paranormal submission", "regular acquiescence",
        "magical defiance", "normal disobedience", "enchanted rebellion", "ordinary resistance",
        "arcane conservation", "common preservation", "mystical maintenance", "ordinary retention",
        "supernatural alteration", "natural change", "paranormal modification", "regular adjustment",
        "magical restoration", "normal recovery", "enchanted rehabilitation", "ordinary reclamation",
        "arcane destruction", "common demolition", "mystical annihilation", "ordinary obliteration",
        "supernatural creation", "natural generation", "paranormal production", "regular formation",
        "magical renewal", "normal rejuvenation", "enchanted regeneration", "ordinary revival",
        "arcane decay", "common deterioration", "mystical degeneration", "ordinary decline",
        "supernatural growth", "natural development", "paranormal expansion", "regular increase",
        "magical diminishment", "normal reduction", "enchanted shrinkage", "ordinary decrease",
        "arcane empowerment", "common strengthening", "mystical enablement", "ordinary reinforcement",
        "supernatural weakening", "natural debilitation", "paranormal enfeeblement", "regular sapping",
        "magical balance", "normal equilibrium", "enchanted stability", "ordinary steadiness",
        "arcane imbalance", "common disequilibrium", "mystical instability", "ordinary unsteadiness",
        "supernatural order", "natural organization", "paranormal arrangement", "regular structure",
        "magical chaos", "normal disorder", "enchanted disarray", "ordinary confusion",
        "arcane perfection", "common flawlessness", "mystical impeccability", "ordinary excellence",
        "supernatural imperfection", "natural flaw", "paranormal defect", "regular deficiency",
        "magical success", "normal achievement", "enchanted accomplishment", "ordinary attainment",
        "arcane failure", "common defeat", "mystical disappointment", "ordinary loss",
        "supernatural completion", "natural finish", "paranormal consummation", "regular fulfillment",
        "magical incompletion", "normal unfinished-state", "enchanted partial-completion", "ordinary non-fulfillment",
        "arcane beginning", "common start", "mystical commencement", "ordinary initiation",
        "supernatural ending", "natural conclusion", "paranormal termination", "regular cessation",
        "magical continuation", "normal persistence", "enchanted perseverance", "ordinary endurance",
        "arcane interruption", "common disruption", "mystical cessation", "ordinary stoppage",
        "supernatural repetition", "natural recurrence", "paranormal reiteration", "regular reccurence",
        "magical uniqueness", "normal singularity", "enchanted one-of-a-kind-ness", "ordinary distinctiveness",
        "arcane miracle", "common marvel", "mystical wonder", "ordinary amazement",
        "supernatural disaster", "natural catastrophe", "paranormal calamity", "regular misfortune",
        "magical solution", "normal remedy", "enchanted answer", "ordinary resolution",
        "arcane problem", "common difficulty", "mystical complication", "ordinary trouble",
        "supernatural blessing", "natural benefit", "paranormal advantage", "regular gain",
        "magical curse", "normal bane", "enchanted affliction", "ordinary misfortune",
        "arcane advantage", "common benefit", "mystical gain", "ordinary profit",
        "supernatural disadvantage", "natural drawback", "paranormal loss", "regular detriment",
        "magical protection", "normal defense", "enchanted safeguard", "ordinary shield",
        "arcane vulnerability", "common susceptibility", "mystical weakness", "ordinary frailty",
        "supernatural ability", "natural capability", "paranormal power", "regular faculty",
        "magical inability", "normal incapability", "enchanted powerlessness", "ordinary incapacity",
        "arcane empowerment", "common enablement", "mystical authorization", "ordinary facilitation",
        "supernatural disempowerment", "natural disablement", "paranormal prevention", "regular hinderance",
        "magical enchanted sword", "golden magical amulet", "powerful arcane staff", "mystical crystal orb",
        "ancient runic stone", "glowing ethereal gem", "floating magical book", "whispering ancient scroll",
        "living magical tree", "singing enchanted harp", "omniscient crystal ball", "dragonfire forged blade",
        "starlight imbued bow", "moonsilver magical arrows", "dimensional pocket bag", "animated guardian armor",
        "healing magical waters", "vitality restoring potion", "invisibility granting cloak", "flight enabling boots",
        "underwater breathing pendant", "mind reading circlet", "memory storing crystal", "truth compelling scepter",
        "shapeshifting magical ring", "beast speaking medallion", "weather controlling staff", "earth shaping gauntlets",
        "time manipulating hourglass", "space folding compass", "destiny weaving loom", "fate cutting shears",
        "soul capturing lantern", "spirit seeing spectacles", "ghostly communicating bell", "dimensional traveling door",
        "plant growing seeds", "instant fortress cube", "unfailing light crystal", "eternal flame torch",
        "winged magical steed", "spectral phantom ship", "floating magical carpet", "walking enchanted cottage",
        "omnilingual translation book", "universal lockpicking key", "unfailing tracking compass", "distance viewing mirror",
        "wish granting monkey paw", "luck bestowing horseshoe", "curse breaking talisman", "blessing bestowing chalice",
        "enchanted silver mirror", "mystical crystal pendant", "ancient magical scroll", "powerful runic weapon",
        "alchemical transformation elixir", "essence capturing vial", "magical binding rope", "power storing battery",
        "magical growing beans", "giants' treasure harp", "enchanted dancing shoes", "fairy godmother's wand",
        "sleeping curse spindle", "poisoned magical apple", "enchanted glass slipper", "shape changing cloak",
        "magic revealing glasses", "wizard summoning candle", "demon binding circle", "angel calling trumpet",
        "underwater palace bubble", "cloudtop castle anchor", "shadow realm gateway", "elemental plane portal",
        "phoenix feather quill", "dragon scale armor", "unicorn horn wand", "griffin claw dagger",
        "centaur crafted bow", "mermaid woven net", "troll forged hammer", "elven crafted locket",
        "dwarven mining pick", "orcish battle axe", "gnomish mechanical toy", "halfling cooking pot",
        "fairy dust pouch", "giant strength belt", "frost giant ice axe", "fire giant ember whip",
        "celestial platinum shield", "abyssal shadow dagger", "divine golden chalice", "demonic iron crown",
        "arcane library book", "forgotten magical tome", "enchanted grimoire", "living spellbook",
        "world-creating artifact", "reality-altering device", "dimension-folding key", "plane-shifting compass",
        "soul-binding contract", "magical oath parchment", "unbreakable vow scroll", "truthbinding quill",
        "memory crystal archive", "thought-preserving gem", "experience-storing orb", "wisdom-containing pearl",
        "prophetic dream catcher", "future-seeing monocle", "past-viewing lens", "timeline-exploring sundial",
        "fate-weaving spindle", "destiny-carving chisel", "chance-altering dice", "probability-shifting coin",
        "immortality-granting apple", "youth-restoring flower", "age-reversing hourglass", "time-defying talisman",
        "healing magical spring", "recovery enchanted bandage", "restoration mystic balm", "curative arcane poultice",
        "strength-enhancing gauntlet", "dexterity-boosting gloves", "intelligence-amplifying circlet", "wisdom-increasing tome",
        "charisma-enhancing brooch", "constitution-bolstering amulet", "perception-sharpening lens", "reaction-quickening boots",
        "giant-slaying sling", "dragon-killing spear", "undead-banishing mace", "demon-binding chains",
        "ghost-capturing lantern", "vampire-repelling stake", "werewolf-calming lyre", "witch-detecting compass",
        "elemental summoning ring", "familiar binding band", "spirit calling bell", "ancestor contacting board",
        "weather control scepter", "seasonal shifting orb", "climate changing fan", "temperature altering crystal",
        "earthquake causing drum", "volcano erupting flute", "tsunami summoning conch", "hurricane generating feather",
        "plant growing staff", "animal communicating flute", "beast transforming mask", "nature harmonizing pendant",
        "mountain moving gauntlet", "river redirecting trident", "forest transplanting seed", "canyon creating pick",
        "city concealing cloak", "castle protecting shield", "village hiding mist", "town preserving barrier",
        "army defeating banner", "navy vanquishing horn", "cavalry overwhelming standard", "infantry invincible flag",
        "peace enforcing treaty", "war preventing medallion", "conflict resolving scales", "dispute settling gavel",
        "love inducing arrow", "friendship forming handkerchief", "loyalty ensuring medal", "fidelity maintaining ring",
        "wisdom imparting spectacles", "knowledge granting book", "skill teaching tool", "ability learning crystal",
        "language understanding earring", "script deciphering monocle", "code breaking quill", "message decoding lens",
        "invisibility granting hat", "undetectability ensuring cloak", "concealment providing ring", "hiding enabling boots",
        "flight bestowing cape", "levitation allowing boots", "hovering permitting belt", "soaring enabling wand",
        "underwater breathing necklace", "fire immunity cloak", "lightning absorbing rod", "earth walking boots",
        "interplanar traveling map", "interdimensional archway key", "multiverse navigating compass", "reality hopping boots",
        "teleportation enabling chalk", "location swapping rings", "distance negating boots", "space folding fan",
        "time slowing pocket watch", "moment extending hourglass", "duration stretching crystal", "interval expanding prism",
        "future glimpsing mirror", "past revealing pool", "present clarifying lens", "timeline viewing scroll",
        "life extending elixir", "death delaying talisman", "mortality postponing ring", "aging slowing crystal",
        "youth restoring spring", "vitality renewing fruit", "energy replenishing bread", "strength rebuilding meat",
        "mana regenerating staff", "magic replenishing wand", "power restoring scepter", "energy recovering orb",
        "spell storing ring", "enchantment capturing gem", "magic preserving bottle", "sorcery containing phylactery",
        "animation bestowing brush", "life granting clay", "vitality providing water", "existence ensuring fire",
        "golem creating manual", "homunculus making apparatus", "simulacrum forming mirror", "duplicate generating pool",
        "dragon controlling horn", "giant commanding drum", "elemental directing wand", "beast ordering whip",
        "undead raising staff", "spirit calling bell", "ghost summoning candle", "wraith invoking mirror",
        "demon binding pentacle", "angel calling trumpet", "deity invoking altar", "divinity contacting pool",
        "wish granting lamp", "desire fulfilling monkey's paw", "dream manifesting pillow", "hope actualizing star",
        "curse placing doll", "hex casting needle", "blight spreading seed", "affliction bestowing touch",
        "blessing giving medallion", "fortune providing coin", "luck ensuring horseshoe", "prosperity guaranteeing lamp",
        "truthfulness compelling throne", "honesty ensuring scales", "veracity detecting rod", "sincerity testing water",
        "falsehood revealing mirror", "deception detecting spectacles", "lie uncovering crystal", "insincerity displaying pool",
        "courage instilling banner", "bravery ensuring medal", "valor providing drink", "fearlessness granting helm",
        "terror causing mask", "fear inducing staff", "panic spreading incense", "dread manifesting image",
        "sleep bringing dust", "slumber ensuring flute", "rest compelling pillow", "unconsciousness causing draught",
        "alertness maintaining bean", "wakefulness ensuring talisman", "vigilance providing herb", "attentiveness preserving crystal",
        "rage inducing drum", "fury enabling battle cry", "anger providing potion", "wrath ensuring vision",
        "calmness bringing tea", "tranquility ensuring pool", "serenity providing crystal", "peacefulness bestowing chime",
        "madness causing whisper", "insanity providing vision", "lunacy ensuring maze", "dementia bestowing puzzle",
        "clarity bringing water", "sanity restoring meditation", "rationality ensuring herb", "lucidity providing light",
        "love awakening song", "affection inducing dance", "attraction ensuring perfume", "adoration providing vision",
        "hatred causing curse", "enmity inducing potion", "loathing ensuring ritual", "abhorrence providing symbol",
        "joy bringing feast", "happiness ensuring festival", "delight providing spectacle", "elation bestowing celebration",
        "sorrow causing tale", "sadness inducing image", "grief ensuring memory", "melancholy providing melody",
        "healing hands blessing", "curing touch gift", "mending breath power", "restoring gaze ability",
        "harming gaze curse", "wounding touch hex", "injuring voice spell", "damaging presence affliction",
        "illusory appearance spell", "deceptive image casting", "false vision conjuring", "misleading perception enchantment",
        "true sight blessing", "reality perception gift", "actuality discernment power", "verity recognition ability",
        "future predicting gift", "prophecy speaking power", "divination casting ability", "foreknowledge accessing talent",
        "past viewing spell", "history perceiving enchantment", "bygone era witnessing magic", "antiquity observing ritual",
        "telepathic communication power", "mind reading ability", "thought perceiving talent", "idea discerning gift",
        "mental privacy enchantment", "thought shielding spell", "mind guarding ritual", "cognition protecting magic",
        "emotion sensing ability", "feeling perceiving talent", "sentiment discerning power", "affect recognizing gift",
        "emotional influence enchantment", "feeling altering spell", "sentiment changing ritual", "affect modifying magic",
        "memory extracting ritual", "recollection removing spell", "remembrance collecting enchantment", "recall harvesting magic",
        "memory implanting ability", "recollection inserting power", "remembrance establishing talent", "recall instilling gift",
        "dream entering enchantment", "sleep vision accessing spell", "slumber image joining ritual", "rest perception breaching magic",
        "nightmare crafting ability", "terror sleep creating power", "fear dream forging talent", "dread slumber making gift",
        "pleasant dream ensuring charm", "restful sleep guaranteeing spell", "peaceful slumber providing ritual", "tranquil rest bestowing magic",
        "consciousness transferring ritual", "awareness relocating spell", "sentience moving enchantment", "cognizance shifting magic",
        "body swapping ability", "physical form exchanging power", "corporeal being trading talent", "material vessel switching gift",
        "youth preserving spell", "age halting enchantment", "time defying appearance ritual", "chronological progression stopping magic",
        "rapid aging curse", "quick senescence hex", "accelerated elderlihood spell", "hastened dotage affliction",
        "beauty enhancing glamour", "appearance improving enchantment", "aesthetic increasing ritual", "attractiveness augmenting magic",
        "ugliness causing curse", "appearance degrading hex", "aesthetic decreasing spell", "attractiveness diminishing affliction",
        "shapechanging ability", "form altering power", "appearance shifting talent", "semblance changing gift",
        "size increasing enchantment", "mass enlarging spell", "volume expanding ritual", "dimension augmenting magic",
        "size decreasing charm", "mass reducing hex", "volume shrinking enchantment", "dimension diminishing spell",
        "invisibility granting cloak", "unseen status bestowing hood", "imperceptible condition providing cape", "undetectable state ensuring garment",
        "seeing invisible enchantment", "perceiving unseen spell", "discerning imperceptible ritual", "detecting undetectable magic",
        "physical enhancement ritual", "bodily improvement spell", "corporeal augmentation enchantment", "material form enhancing magic",
        "physical deterioration curse", "bodily degradation hex", "corporeal diminishment spell", "material form weakening affliction",
        "element controlling talent", "elemental manipulation power", "primal force directing ability", "fundamental aspect commanding gift",
        "animal communication spell", "beast speech understanding enchantment", "creature language comprehending ritual", "fauna dialect interpreting magic",
        "plant growth accelerating ability", "vegetation development hastening power", "flora maturation quickening talent", "botanical advancement expediting gift",
        "metal manipulating enchantment", "metallic substance controlling spell", "ore and alloy directing ritual", "ferrous material commanding magic",
        "stone shaping hands", "rock forming touch", "mineral manipulating grasp", "earthen material molding fingers",
        "water controlling gesture", "liquid directing movement", "fluid manipulating motion", "aqueous substance commanding action",
        "fire summoning word", "flame calling utterance", "blaze invoking speech", "inferno conjuring exclamation",
        "air current controlling thought", "wind directing idea", "breeze manipulating concept", "atmospheric flow commanding notion",
        "lightning calling staff", "electrical discharge summoning rod", "thunderbolt invoking wand", "electric current conjuring baton",
        "ice forming breath", "frost creating exhalation", "freezing causing respiration", "coldness generating expiration",
        "light summoning crystal", "illumination calling gem", "brightness invoking stone", "luminosity conjuring mineral",
        "darkness spreading ink", "shadow propagating liquid", "obscurity extending fluid", "dimness expanding substance",
        "sound controlling whistle", "noise directing flute", "audio manipulating whisper", "acoustic commanding song",
        "silence creating bell", "quietude generating chime", "soundlessness causing ring", "noiselessness producing tinkle",
        "gravity defying boots", "weightlessness ensuring footwear", "mass negating shoes", "buoyancy providing sandals",
        "magnetic force controlling lodestone", "attractive power directing mineral", "magnetic field manipulating stone", "ferromagnetic influence commanding object",
        "life energy manipulating crystal", "vital force directing gem", "existence essence controlling stone", "being mana manipulating jewel",
        "death energy channeling obsidian", "mortality force directing onyx", "terminus essence controlling jet", "ending mana manipulating black crystal",
        "time manipulating hourglass", "chronological flow directing timepiece", "temporal progress controlling device", "sequential moment commanding instrument",
        "space altering compass", "dimensional aspect directing tool", "spatial extension controlling implement", "positional relation commanding apparatus",
        "fate weaving loom", "destiny directing frame", "kismet controlling machine", "providence commanding device",
        "chance influencing dice", "probability directing cubes", "randomness controlling polyhedrons", "happenstance commanding game pieces",
        "reality altering brush", "actuality directing stylus", "existence controlling pen", "being commanding writing implement",
        "dream shaping pillow", "sleep vision directing cushion", "slumber image controlling pad", "rest perception commanding comfort",
        "soul manipulating lantern", "spirit directing light", "essence controlling illumination", "being commanding brightness",
        "thought influencing crown", "idea directing diadem", "concept controlling circlet", "notion commanding headpiece",
        "emotion altering perfume", "feeling directing fragrance", "sentiment controlling scent", "affect commanding aroma",
        "health manipulating herb", "vitality directing plant", "wellness controlling flora", "fitness commanding vegetation",
        "disease spreading miasma", "illness directing vapor", "sickness controlling gas", "ailment commanding exhalation",
        "fortune altering coin", "luck directing metal piece", "chance controlling currency", "happenstance commanding money",
        "misfortune causing token", "bad luck directing trinket", "adversity controlling object", "calamity commanding item",
        "conflict inciting banner", "strife directing flag", "discord controlling standard", "contention commanding emblem",
        "peace ensuring olive branch", "harmony directing plant", "accord controlling vegetation", "amity commanding flora",
        "wisdom granting book", "sagacity directing tome", "prudence controlling volume", "judiciousness commanding manuscript",
        "foolishness causing scroll", "imprudence directing parchment", "indiscretion controlling document", "rashness commanding paper",
        "strength enhancing belt", "might directing strap", "power controlling band", "force commanding girdle",
        "weakness causing bracelet", "debility directing wristlet", "frailty controlling band", "feebleness commanding loop",
        "protection ensuring shield", "defense directing guard", "security controlling barrier", "safety commanding protection",
        "vulnerability causing mask", "defenselessness directing covering", "susceptibility controlling façade", "exposure commanding disguise",
        "speed increasing boots", "velocity directing footwear", "quickness controlling shoes", "swiftness commanding sandals",
        "slowness causing chain", "lethargy directing links", "sluggishness controlling fetters", "tardiness commanding restraint",
        "skill improving gloves", "ability directing handwear", "talent controlling mittens", "capability commanding gauntlets",
        "incompetence causing hat", "ineptitude directing headwear", "incapability controlling cap", "inefficiency commanding hood",
        "language understanding earring", "dialect directing hearing piece", "vernacular controlling ornament", "speech commanding jewelry",
        "communication preventing gag", "dialogue directing mouthpiece", "discourse controlling restraint", "conversation commanding obstruction",
        "truth ensuring throne", "veracity directing seat", "honesty controlling chair", "accuracy commanding royal furniture",
        "deception causing mirror", "falsehood directing glass", "dishonesty controlling reflector", "inaccuracy commanding looking glass",
        "friendship creating handshake", "amity directing greeting", "companionship controlling salutation", "camaraderie commanding welcome",
        "enmity causing gesture", "hostility directing signal", "animosity controlling motion", "antagonism commanding movement",
        "travel easing map", "journey directing chart", "voyage controlling parchment", "expedition commanding document",
        "imprisonment causing cage", "confinement directing enclosure", "captivity controlling container", "incarceration commanding barrier",
        "fertility ensuring seed", "productivity directing grain", "fruitfulness controlling kernel", "generativity commanding pit",
        "barrenness causing dust", "sterility directing powder", "infertility controlling granules", "unproductiveness commanding particles",
        "creativity inspiring paintbrush", "innovation directing art tool", "inventiveness controlling implement", "ingenuity commanding utensil",
        "unimaginativeness causing blotter", "uncreative thinking directing pad", "uninspiredness controlling object", "unoriginality commanding item",
        "beauty enhancing cosmetics", "attractiveness directing makeup", "loveliness controlling substances", "charm commanding preparations",
        "memory improving tonic", "recollection directing potion", "remembrance controlling elixir", "recall commanding draught",
        "forgetfulness causing draft", "amnesia directing drink", "oblivion controlling liquid", "memory loss commanding beverage",
        "clairvoyance granting crystal ball", "precognition directing orb", "foresight controlling sphere", "future sight commanding globe",
        "blindness causing blindfold", "sightlessness directing covering", "vision loss controlling band", "unseeing commanding cloth",
        "youth preserving apple", "juvenescence directing fruit", "adolescence controlling produce", "young age commanding edible",
        "aging accelerating hourglass", "senescence directing timepiece", "elderlihood controlling device", "old age commanding instrument",
        "love inducing arrow", "affection directing projectile", "adoration controlling missile", "fondness commanding dart",
        "hatred causing dagger", "loathing directing blade", "abhorrence controlling knife", "detestation commanding weapon",
        "courage enhancing medal", "bravery directing award", "valor controlling decoration", "fearlessness commanding distinction",
        "cowardice causing horn", "timidity directing instrument", "fearfulness controlling device", "apprehensiveness commanding object",
        "intelligence improving tome", "intellect directing book", "acumen controlling volume", "brainpower commanding manuscript",
        "stupidity causing draft", "denseness directing drink", "dullness controlling potion", "slow-wittedness commanding beverage",
        "charisma enhancing mask", "charm directing covering", "allure controlling disguise", "appeal commanding façade",
        "repulsiveness causing mirror", "unattractiveness directing glass", "unappealingness controlling reflector", "repellence commanding looking glass",
        "jumping enhancing boots", "leaping directing footwear", "springing controlling shoes", "bounding commanding sandals",
        "earthbinding chains", "groundedness directing links", "stability controlling fetters", "immobility commanding restraint",
        "damage causing sword", "harm directing blade", "injury controlling weapon", "hurt commanding edge",
        "healing providing staff", "restoration directing rod", "recovery controlling wand", "mending commanding baton",
        "poisonous bite bestowing", "toxicity directing fangs", "venom controlling teeth", "poisonousness commanding mouth",
        "antivenom producing herb", "toxin countering plant", "poison neutralizing flora", "venom defeating vegetation",
        "curse placing needle", "hex directing pin", "jinx controlling spike", "spell commanding sharp implement",
        "blessing bestowing chalice", "benediction directing cup", "invocation controlling vessel", "prayer commanding container",
        "undead raising staff", "reanimation directing rod", "revivification controlling wand", "resurrection commanding baton",
        "final death causing stake", "permanent end directing implement", "ultimate termination controlling weapon", "complete cessation commanding tool",
        "soul capturing gem", "spirit directing jewel", "essence controlling stone", "being commanding crystal",
        "soul releasing trumpet", "spirit directing horn", "essence controlling instrument", "being commanding device",
        "demon summoning pentagram", "fiend directing star", "devil controlling symbol", "hellion commanding shape",
        "demon banishing holy water", "fiend directing sacred liquid", "devil controlling blessed fluid", "hellion commanding consecrated solution",
        "angel calling bell", "celestial directing chime", "heavenly being controlling ring", "divine entity commanding tinkle",
        "angel dismissing incantation", "celestial directing words", "heavenly being controlling speech", "divine entity commanding utterance",
        "dragon controlling horn", "wyrm directing instrument", "drake controlling device", "serpent commanding object",
        "dragon repelling shield", "wyrm directing guard", "drake controlling barrier", "serpent commanding defense",
        "giant commanding drumbeat", "colossus directing rhythm", "titan controlling percussion", "behemoth commanding sound",
        "giant weakening sling", "colossus directing projectile weapon", "titan controlling missile launcher", "behemoth commanding stone thrower",
        "elemental summoning ritual", "primal force directing ceremony", "fundamental energy controlling rite", "essential power commanding observance",
        "elemental banishing circle", "primal force directing boundary", "fundamental energy controlling perimeter", "essential power commanding circumference",
        "weather controlling staff", "atmospheric condition directing rod", "meteorological phenomenon controlling wand", "climate commanding baton",
        "plant growth accelerating fertilizer", "vegetation development hastening substance", "flora maturation quickening material", "botanical advancement expediting matter",
        "animal commanding whip", "beast directing lash", "creature controlling scourge", "fauna commanding thong",
        "animal befriending flute", "beast directing wind instrument", "creature controlling woodwind", "fauna commanding pipe",
        "stone shaping chisel", "rock directing carving tool", "mineral controlling implement", "earthen material commanding utensil",
        "metal manipulating tongs", "metallic substance directing tool", "ore and alloy controlling implement", "ferrous material commanding instrument",
        "fire calling flint", "flame directing stone", "blaze controlling mineral", "inferno commanding rock",
        "fire extinguishing blanket", "flame directing covering", "blaze controlling sheet", "inferno commanding wrap",
        "water collecting bucket", "liquid directing container", "fluid controlling vessel", "aqueous substance commanding receptacle",
        "water repelling cloak", "liquid directing garment", "fluid controlling covering", "aqueous substance commanding attire",
        "air current controlling fan", "wind directing implement", "breeze controlling device", "atmospheric flow commanding object",
        "air stilling chamber", "wind directing enclosure", "breeze controlling room", "atmospheric flow commanding space",
        "electricity generating rod", "lightning directing implement", "thunderbolt controlling device", "electric current commanding object",
        "electricity insulating gloves", "lightning directing handwear", "thunderbolt controlling mittens", "electric current commanding gauntlets",
        "heat producing brazier", "thermal energy directing container", "warmth controlling vessel", "high temperature commanding receptacle",
        "cold generating crystal", "low temperature directing gem", "chill controlling stone", "frigidity commanding mineral",
        "light emitting lantern", "illumination directing container", "brightness controlling vessel", "luminosity commanding receptacle",
        "darkness creating hood", "shadow directing head covering", "obscurity controlling cowl", "dimness commanding headwear",
        "sound amplifying horn", "noise directing instrument", "audio controlling device", "acoustic commanding object",
        "silence creating bell", "quietude directing instrument", "soundlessness controlling device", "noiselessness commanding object",
        "poison detecting amulet", "toxin directing pendant", "venom controlling necklace", "toxic substance commanding jewelry",
        "disease curing elixir", "illness directing potion", "sickness controlling draught", "ailment commanding beverage",
        "lock opening key", "fastening directing implement", "securing mechanism controlling device", "closure commanding object",
        "trap detecting rod", "snare directing implement", "pitfall controlling device", "ambush commanding object",
        "secret passage revealing spectacles", "hidden way directing eyewear", "concealed path controlling glasses", "clandestine route commanding optics",
        "direction finding compass", "orientation directing implement", "bearing controlling device", "course commanding object",
        "message sending scroll", "communication directing parchment", "correspondence controlling document", "missive commanding paper",
        "mind reading crystal", "thought directing gem", "idea controlling stone", "cognition commanding mineral",
        "telepathic blocking helmet", "mind reading directing headgear", "thought controlling head protection", "idea commanding cranial covering",
        "scrying enabling mirror", "remote viewing directing glass", "distant seeing controlling reflector", "far observation commanding looking glass",
        "illusion creating prism", "false appearance directing crystal", "deceptive image controlling glass", "misleading vision commanding object",
        "illusion dispelling spectacles", "false appearance directing eyewear", "deceptive image controlling glasses", "misleading vision commanding optics",
        "invisibility granting cloak", "unseen state directing garment", "imperceptible condition controlling attire", "undetectable status commanding clothing",
        "invisibility revealing dust", "unseen state directing powder", "imperceptible condition controlling particles", "undetectable status commanding granules",
        "flying enabling broom", "aerial movement directing implement", "airborne travel controlling device", "sky traversal commanding object",
        "earth burrowing claws", "subterranean movement directing implements", "underground travel controlling extensions", "soil traversal commanding appendages",
        "water walking sandals", "liquid surface movement directing footwear", "fluid top travel controlling shoes", "aqueous plane traversal commanding footgear",
        "wall climbing gloves", "vertical surface movement directing handwear", "perpendicular plane travel controlling mittens", "upright traversal commanding gauntlets",
        "teleportation enabling chalk", "instant movement directing writing implement", "immediate travel controlling utensil", "instantaneous traversal commanding tool",
        "dimensional travel enabling key", "planar movement directing implement", "reality shifting travel controlling device", "existence traversal commanding object",
        "time travel enabling pocket watch", "chronological movement directing timepiece", "temporal travel controlling instrument", "era traversal commanding device",
        "youth restoring spring", "juvenescence directing water source", "adolescence controlling font", "young age commanding wellspring",
        "rapid aging pool", "senescence directing liquid collection", "elderlihood controlling pond", "old age commanding basin",
        "strength enhancing gauntlet", "might directing handwear", "power controlling mitten", "force commanding glove",
        "weakness causing manacles", "debility directing restraints", "frailty controlling shackles", "feebleness commanding fetters",
        "intelligence boosting headband", "intellect directing head wrap", "acumen controlling circlet", "brainpower commanding diadem",
        "confusion causing labyrinth", "mental disarray directing maze", "cognitive disorder controlling warren", "intellectual chaos commanding network",
        "wisdom granting owl", "sagacity directing bird", "prudence controlling avian", "judiciousness commanding creature",
        "foolishness causing draught", "imprudence directing beverage", "indiscretion controlling drink", "rashness commanding potion",
        "charisma enhancing perfume", "charm directing fragrance", "allure controlling scent", "appeal commanding aroma",
        "repulsiveness causing odor", "unattractiveness directing smell", "unappealingness controlling stench", "repellence commanding reek",
        "luck improving rabbit's foot", "fortune directing animal appendage", "chance controlling creature part", "happenstance commanding token",
        "misfortune causing broken mirror", "bad luck directing shattered glass", "adversity controlling fragmented reflector", "calamity commanding broken looking glass",
        "health restoring fruit", "vitality directing produce", "wellness controlling edible", "fitness commanding food",
        "illness causing fungus", "disease directing mushroom", "sickness controlling toadstool", "ailment commanding growth",
        "love inducing chocolate", "affection directing confection", "adoration controlling sweet", "fondness commanding candy",
        "hatred causing potion", "loathing directing draught", "abhorrence controlling elixir", "detestation commanding drink",
        "courage enhancing draught", "bravery directing potion", "valor controlling elixir", "fearlessness commanding beverage",
        "fear inducing mask", "terror directing covering", "dread controlling disguise", "fright commanding façade",
        "sleep inducing powder", "slumber directing dust", "rest controlling granules", "unconsciousness commanding particles",
        "alertness maintaining herb", "wakefulness directing plant", "vigilance controlling flora", "attentiveness commanding vegetation",
        "truth compelling throne", "veracity directing seat", "honesty controlling chair", "accuracy commanding royal furniture",
        "deception enabling mask", "falsehood directing covering", "dishonesty controlling disguise", "inaccuracy commanding façade",
        "animal communication enabling collar", "beast speech directing neckwear", "creature language controlling band", "fauna dialect commanding loop",
        "animal repelling horn", "beast directing instrument", "creature controlling device", "fauna commanding object",
        "plant growth accelerating sunlight", "vegetation development hastening illumination", "flora maturation quickening radiance", "botanical advancement expediting brightness",
        "plant withering darkness", "vegetation deterioration directing shadow", "flora degradation controlling obscurity", "botanical decline commanding dimness",
        "water purifying crystal", "liquid cleansing directing gem", "fluid decontaminating controlling stone", "aqueous substance purifying commanding mineral",
        "water poisoning powder", "liquid contaminating directing dust", "fluid polluting controlling granules", "aqueous substance tainting commanding particles",
        "fire intensifying bellows", "flame enhancing directing implement", "blaze increasing controlling device", "inferno amplifying commanding object",
        "fire extinguishing sand", "flame reducing directing granules", "blaze decreasing controlling particles", "inferno diminishing commanding matter",
        "air freshening incense", "atmosphere purifying directing substance", "environment decontaminating controlling material", "surroundings cleansing commanding matter",
        "air polluting smoke", "atmosphere contaminating directing vapor", "environment defiling controlling gas", "surroundings tainting commanding emission",
        "earth fertility enhancing seed", "soil productivity directing grain", "ground fruitfulness controlling kernel", "terra generativity commanding pit",
        "earth barrenness causing salt", "soil infertility directing mineral", "ground sterility controlling substance", "terra unproductiveness commanding matter",
        "lightning conducting rod", "electrical discharge directing implement", "thunderbolt guiding controlling device", "electric current channeling commanding object",
        "lightning insulating rubber", "electrical discharge blocking directing material", "thunderbolt impeding controlling substance", "electric current stopping commanding matter",
        "light intensifying lens", "illumination enhancing directing glass", "brightness amplifying controlling optical device", "luminosity increasing commanding transparent object",
        "light dimming shade", "illumination reducing directing cover", "brightness decreasing controlling barrier", "luminosity lessening commanding obstruction",
        "darkness deepening obsidian", "shadow intensifying directing black glass", "obscurity amplifying controlling volcanic glass", "dimness increasing commanding dark mineral",
        "darkness dispelling torch", "shadow reducing directing light source", "obscurity decreasing controlling flame", "dimness lessening commanding fire",
        "sound amplifying shell", "noise increasing directing hollow object", "audio intensifying controlling natural formation", "acoustic enhancing commanding curvature",
        "sound dampening cloth", "noise reducing directing fabric", "audio decreasing controlling textile", "acoustic lessening commanding material",
        "heat increasing coal", "thermal energy amplifying directing carbon", "warmth intensifying controlling fossil fuel", "high temperature enhancing commanding black rock",
        "heat reducing ice", "thermal energy decreasing directing frozen water", "warmth diminishing controlling solidified liquid", "high temperature lessening commanding cold solid",
        "life extending elixir", "existence prolonging directing potion", "being continuing controlling draught", "living lengthening commanding beverage",
        "life shortening poison", "existence reducing directing toxin", "being decreasing controlling venom", "living briefening commanding harmful substance",
        "youth preserving apple", "adolescence maintaining directing fruit", "young age continuing controlling produce", "juvenile persisting commanding edible",
        "aging accelerating dust", "senescence hastening directing powder", "elderlihood quickening controlling granules", "old age expediting commanding particles",
        "beauty enhancing mask", "attractiveness increasing directing covering", "loveliness amplifying controlling disguise", "charm intensifying commanding façade",
        "ugliness causing potion", "unattractiveness increasing directing draught", "unloveliness amplifying controlling elixir", "repulsiveness intensifying commanding beverage",
        "strength enhancing belt", "might increasing directing strap", "power amplifying controlling band", "force intensifying commanding girdle",
        "weakness causing chain", "debility increasing directing links", "frailty amplifying controlling fetters", "feebleness intensifying commanding restraint",
        "intelligence improving book", "intellect enhancing directing tome", "acumen amplifying controlling volume", "brainpower intensifying commanding manuscript",
        "stupidity causing brew", "denseness increasing directing concoction", "dullness amplifying controlling mixture", "slow-wittedness intensifying commanding liquid",
        "wisdom granting meditation", "sagacity providing directing contemplation", "prudence bestowing controlling reflection", "judiciousness giving commanding thought",
        "foolishness causing distraction", "imprudence increasing directing diversion", "indiscretion amplifying controlling amusement", "rashness intensifying commanding entertainment",
        "charisma enhancing garment", "charm increasing directing clothing", "allure amplifying controlling attire", "appeal intensifying commanding garb",
        "repulsiveness causing attire", "unattractiveness increasing directing clothing", "unappealingness amplifying controlling garb", "repellence intensifying commanding garment",
        "luck improving charm", "fortune enhancing directing trinket", "chance amplifying controlling ornament", "happenstance intensifying commanding bauble",
        "misfortune causing token", "bad luck increasing directing object", "adversity amplifying controlling item", "calamity intensifying commanding thing",
        "protection ensuring shield", "defense providing directing guard", "security bestowing controlling barrier", "safety giving commanding protection",
        "vulnerability causing exposure", "defenselessness increasing directing openness", "susceptibility amplifying controlling revelation", "exposure intensifying commanding disclosure",
        "health restoring rest", "vitality enhancing directing slumber", "wellness amplifying controlling sleep", "fitness intensifying commanding repose",
        "disease causing miasma", "illness increasing directing vapor", "sickness amplifying controlling gas", "ailment intensifying commanding emission",
        "friendship creating gesture", "amity providing directing motion", "companionship bestowing controlling movement", "camaraderie giving commanding action",
        "enmity causing insult", "hostility increasing directing offense", "animosity amplifying controlling slight", "antagonism intensifying commanding slight",
        "peace ensuring treaty", "harmony providing directing agreement", "accord bestowing controlling pact", "amity giving commanding covenant",
        "conflict inciting declaration", "strife increasing directing announcement", "discord amplifying controlling proclamation", "contention intensifying commanding statement",
        "truth revealing light", "veracity exposing directing illumination", "honesty disclosing controlling brightness", "accuracy showing commanding radiance",
        "deception enabling shadow", "falsehood facilitating directing darkness", "dishonesty assisting controlling obscurity", "inaccuracy helping commanding dimness",
        "love inducing music", "affection creating directing melody", "adoration providing controlling harmony", "fondness bestowing commanding tune",
        "hatred causing dissonance", "loathing increasing directing discord", "abhorrence amplifying controlling cacophony", "detestation intensifying commanding noise",
        "courage enhancing battle cry", "bravery increasing directing shout", "valor amplifying controlling yell", "fearlessness intensifying commanding scream",
        "fear inducing howl", "terror creating directing cry", "dread providing controlling scream", "fright bestowing commanding shriek",
        "joy bringing feast", "happiness providing directing banquet", "delight bestowing controlling meal", "elation giving commanding repast",
        "sorrow causing lament", "sadness increasing directing dirge", "grief amplifying controlling threnody", "melancholy intensifying commanding elegy",
        "hope inspiring vision", "optimism providing directing apparition", "expectation bestowing controlling sight", "anticipation giving commanding image",
        "despair causing nightmare", "pessimism increasing directing bad dream", "hopelessness amplifying controlling terror", "despondency intensifying commanding horror",
        "creativity inspiring environment", "innovation facilitating directing surroundings", "inventiveness assisting controlling setting", "ingenuity helping commanding context",
        "unimaginativeness causing confinement", "uncreative thinking increasing directing imprisonment", "uninspiredness amplifying controlling captivity", "unoriginality intensifying commanding restraint",
        "memory improving practice", "recollection enhancing directing exercise", "remembrance amplifying controlling training", "recall intensifying commanding drill",
        "forgetfulness causing distraction", "amnesia increasing directing diversion", "oblivion amplifying controlling amusement", "memory loss intensifying commanding entertainment",
        "magical aptitude increasing study", "arcane ability enhancing directing learning", "mystical capability amplifying controlling education", "sorcerous capacity intensifying commanding scholarship",
        "spellcasting preventing restraint", "magic blocking directing constraint", "enchantment stopping controlling restriction", "sorcery impeding commanding limitation",
        "divination enabling crystal", "future seeing facilitating directing gem", "prophecy assisting controlling stone", "foreknowledge helping commanding mineral",
        "fate obscuring mist", "destiny hiding directing vapor", "kismet concealing controlling gas", "providence masking commanding emission",
        "necromancy enabling bone", "death magic facilitating directing skeletal remains", "undeath assisting controlling osseous matter", "mortality manipulation helping commanding remains",
        "spirit repelling salt", "ghost deterring directing mineral", "specter discouraging controlling substance", "phantom dissuading commanding matter",
        "demonic summoning blood", "fiendish calling directing vital fluid", "devilish inviting controlling bodily liquid", "hellish beckoning commanding gore",
        "demonic banishing holy water", "fiendish expelling directing sacred liquid", "devilish removing controlling blessed fluid", "hellish dismissing commanding consecrated solution",
        "angelic calling prayer", "celestial summoning directing supplication", "heavenly inviting controlling petition", "divine beckoning commanding invocation",
        "angelic dismissing command", "celestial expelling directing order", "heavenly removing controlling instruction", "divine dismissing commanding directive",
        "fey detecting silver", "fairy finding directing metal", "sprite locating controlling element", "pixie discovering commanding material",
        "fey repelling iron", "fairy deterring directing metal", "sprite discouraging controlling element", "pixie dissuading commanding material",
        "draconic revealing scale", "dragon detecting directing skin piece", "wyrm finding controlling dermal fragment", "drake locating commanding body part",
        "draconic repelling sword", "dragon deterring directing blade", "wyrm discouraging controlling edge", "drake dissuading commanding weapon",
        "giants revealing rumble", "colossus detecting directing tremor", "titan finding controlling shake", "behemoth locating commanding vibration",
        "giants repelling music", "colossus deterring directing melody", "titan discouraging controlling harmony", "behemoth dissuading commanding tune",
        "elemental summoning circle", "primal force calling directing boundary", "fundamental energy inviting controlling perimeter", "essential power beckoning commanding circumference",
        "elemental binding pentagon", "primal force restraining directing five-sided shape", "fundamental energy confining controlling pentagram", "essential power limiting commanding star",
        "elemental banishing salt", "primal force expelling directing mineral", "fundamental energy removing controlling substance", "essential power dismissing commanding matter",
        "magical detection lens", "arcane revealing directing glass", "mystical discovering controlling optical device", "sorcerous finding commanding transparent object",
        "magic concealing lead", "arcane hiding directing metal", "mystical covering controlling element", "sorcerous masking commanding material",
        "spell storing crystal", "enchantment preserving directing gem", "incantation keeping controlling stone", "charm maintaining commanding mineral",
        "magic dampening iron", "arcane weakening directing metal", "mystical diminishing controlling element", "sorcerous reducing commanding material",
        "charm breaking silver", "enchantment ending directing metal", "incantation terminating controlling element", "spell concluding commanding material",
        "curse removing herb", "hex eliminating directing plant", "jinx eradicating controlling flora", "spell destroying commanding vegetation",
        "blessing providing water", "benediction bestowing directing liquid", "invocation giving controlling fluid", "prayer offering commanding solution",
        "sacred space creating chalk", "holy area forming directing writing implement", "blessed region making controlling utensil", "consecrated zone producing commanding tool",
        "profane area creating blood", "unholy region forming directing vital fluid", "cursed zone making controlling bodily liquid", "desecrated space producing commanding gore",
        "divine connection establishing altar", "godly link forming directing raised platform", "sacred bond making controlling elevated surface", "holy connection producing commanding table",
        "infernal connection establishing pentagram", "devilish link forming directing five-pointed star", "hellish bond making controlling geometric shape", "demonic connection producing commanding symbol",
        "spectral vision enabling potion", "ghost seeing facilitating directing draught", "spirit viewing assisting controlling elixir", "phantom observing helping commanding beverage",
        "undead detecting amulet", "reanimated finding directing pendant", "revived discovering controlling necklace", "resurrected locating commanding jewelry",
        "undead repelling garlic", "reanimated deterring directing plant", "revived discouraging controlling flora", "resurrected dissuading commanding vegetation",
        "vampiric detecting mirror", "blood-drinker finding directing glass", "hemophage discovering controlling reflector", "sanguinivore locating commanding looking glass",
        "vampiric repelling stake", "blood-drinker deterring directing wood", "hemophage discouraging controlling timber", "sanguinivore dissuading commanding lumber",
        "lycanthropic revealing silver", "werewolf finding directing metal", "shape-shifter discovering controlling element", "skin-changer locating commanding material",
        "lycanthropic repelling wolfsbane", "werewolf deterring directing plant", "shape-shifter discouraging controlling flora", "skin-changer dissuading commanding vegetation",
        "invisibility detecting dust", "unseen finding directing powder", "imperceptible discovering controlling granules", "undetectable locating commanding particles",
        "invisibility granting potion", "unseen making directing draught", "imperceptible forming controlling elixir", "undetectable producing commanding beverage",
        "etherealness enabling oil", "incorporeality facilitating directing liquid", "immateriality assisting controlling fluid", "insubstantiality helping commanding solution",
        "soul trapping crystal", "spirit capturing directing gem", "essence imprisoning controlling stone", "being confining commanding mineral",
        "soul releasing chant", "spirit freeing directing vocalization", "essence liberating controlling intonation", "being delivering commanding song",
        "planar travel enabling key", "dimensional movement facilitating directing implement", "reality shifting assisting controlling device", "existence traversing helping commanding object",
        "world anchoring stone", "dimension fixing directing rock", "plane securing controlling mineral", "reality fastening commanding element",
        "time manipulating hourglass", "chronological control facilitating directing timepiece", "temporal adjustment assisting controlling device", "era alteration helping commanding instrument",
        "time freezing crystal", "chronological halting directing gem", "temporal stopping controlling stone", "era pausing commanding mineral",
        "scrying enabling mirror", "remote viewing facilitating directing glass", "distant seeing assisting controlling reflector", "far observation helping commanding looking glass",
        "oracle consulting bones", "prophecy seeking directing remains", "divination pursuing controlling remnants", "foreknowledge chasing commanding remains",
        "wish granting lamp", "desire fulfilling directing container", "want satisfying controlling vessel", "craving appeasing commanding receptacle",
        "wish twisting monkey's paw", "desire perverting directing primate appendage", "want corrupting controlling simian extremity", "craving distorting commanding animal part",
        "prayer answering shrine", "supplication responding directing sacred place", "petition replying controlling holy site", "invocation acknowledging commanding consecrated location",
        "meditation enhancing incense", "contemplation improving directing aromatic", "reflection augmenting controlling fragrant", "introspection intensifying commanding perfumed",
        "emotion reading crystal", "feeling detecting directing gem", "sentiment discovering controlling stone", "affect finding commanding mineral",
        "emotion manipulating music", "feeling altering directing melody", "sentiment changing controlling harmony", "affect modifying commanding tune",
        "fear inducing mask", "terror creating directing covering", "dread producing controlling disguise", "fright generating commanding façade",
        "courage enhancing banner", "bravery improving directing flag", "valor augmenting controlling standard", "fearlessness intensifying commanding emblem",
        "rage provoking war drum", "fury inciting directing percussion", "anger stimulating controlling instrument", "wrath rousing commanding device",
        "tranquility ensuring fountain", "calmness providing directing water feature", "serenity bestowing controlling liquid display", "peace giving commanding aqueous exhibition",
        "joy bringing feast", "happiness providing directing banquet", "delight bestowing controlling meal", "elation giving commanding repast",
        "sorrow causing dirge", "sadness creating directing funeral song", "grief producing controlling lament", "melancholy generating commanding elegy",
        "love inducing ballad", "affection creating directing romantic song", "adoration producing controlling amorous melody", "fondness generating commanding loving tune",
        "hatred causing curse", "loathing creating directing malediction", "abhorrence producing controlling imprecation", "detestation generating commanding execration",
        "luck improving clover", "fortune enhancing directing plant", "chance augmenting controlling flora", "happenstance intensifying commanding vegetation",
        "misfortune causing effigy", "bad luck creating directing figurine", "adversity producing controlling statuette", "calamity generating commanding image",
        "truth revealing lantern", "veracity exposing directing light source", "honesty disclosing controlling illuminator", "accuracy showing commanding brightness",
        "falsehood enabling mask", "deception facilitating directing covering", "dishonesty assisting controlling disguise", "inaccuracy helping commanding façade",
        "life extending elixir", "existence prolonging directing potion", "being continuing controlling draught", "living lengthening commanding beverage",
        "death hastening poison", "existence shortening directing toxin", "being abbreviating controlling venom", "living curtailing commanding harmful substance",
        "sleep inducing lullaby", "slumber creating directing gentle song", "rest producing controlling soft melody", "unconsciousness generating commanding calming tune",
        "alertness maintaining herb", "wakefulness preserving directing plant", "vigilance continuing controlling flora", "attentiveness perpetuating commanding vegetation",
        "wisdom granting meditation", "sagacity providing directing contemplation", "prudence bestowing controlling reflection", "judiciousness giving commanding thought",
        "foolishness causing distraction", "imprudence creating directing diversion", "indiscretion producing controlling amusement", "rashness generating commanding entertainment",
        "health restoring spring", "vitality providing directing water source", "wellness bestowing controlling font", "fitness giving commanding wellspring",
        "illness causing miasma", "disease creating directing vapor", "sickness producing controlling gas", "ailment generating commanding emission",
        "protection ensuring shield", "defense providing directing guard", "security bestowing controlling barrier", "safety giving commanding protection",
        "vulnerability causing exposure", "defenselessness creating directing openness", "susceptibility producing controlling revelation", "exposure generating commanding disclosure",
        "flight enabling broom", "aerial movement facilitating directing implement", "airborne travel assisting controlling device", "sky traversal helping commanding object",
        "earthbinding chains", "ground fixing directing links", "terra securing controlling fetters", "soil fastening commanding restraint",
        "underwater breathing allowing necklace", "subaqueous respiration facilitating directing pendant", "submarine inhalation assisting controlling jewelry", "below-water breathing helping commanding ornament",
        "firewalking enabling boots", "flame traversing facilitating directing footwear", "blaze crossing assisting controlling shoes", "inferno walking helping commanding sandals",
        "earthmoving enabling gauntlet", "soil shifting facilitating directing glove", "ground moving assisting controlling mitt", "terra displacing helping commanding handwear",
        "water walking allowing sandals", "liquid surface traversing facilitating directing footwear", "fluid top crossing assisting controlling shoes", "aqueous plane walking helping commanding footgear",
        "air walking enabling boots", "atmospheric traversing facilitating directing footwear", "gaseous crossing assisting controlling shoes", "aerial plane walking helping commanding sandals",
        "beast speech comprehending collar", "animal language understanding directing neckband", "creature dialect comprehending controlling neckwear", "fauna speech understanding commanding neck ring",
        "plant growth accelerating sunlight", "vegetation development hastening directing illumination", "flora maturation quickening controlling radiance", "botanical advancement expediting commanding brightness",
        "elemental calling pentacle", "primal force summoning directing five-pointed star", "fundamental energy inviting controlling geometric symbol", "essential power beckoning commanding magical shape",
        "supernatural concealing cloak", "paranormal hiding directing garment", "preternatural covering controlling attire", "superhuman masking commanding clothing",
        "telekinesis enabling crown", "psychokinesis facilitating directing headwear", "mind-movement assisting controlling diadem", "thought-motion helping commanding circlet",
        "teleportation allowing chalk", "instant movement facilitating directing writing implement", "immediate travel assisting controlling utensil", "instantaneous traversal helping commanding tool",
        "transmutation enabling philosopher's stone", "form changing facilitating directing alchemical object", "shape altering assisting controlling magical item", "appearance transforming helping commanding mystical thing",
        "energy manipulating crystal", "force controlling directing gem", "power adjusting controlling stone", "might altering commanding mineral",
        "reality warping artifact", "actuality distorting directing object", "existence bending controlling item", "being twisting commanding thing",
        "prophecy enabling oracle bones", "future telling facilitating directing remains", "forthcoming revelation assisting controlling remnants", "coming event disclosure helping commanding remains",
        "memory extracting potion", "recollection removing directing draught", "remembrance withdrawing controlling elixir", "recall taking commanding beverage",
        "memory implanting spell", "recollection inserting directing incantation", "remembrance introducing controlling charm", "recall placing commanding enchantment",
        "mind reading enabling crystal", "thought discerning facilitating directing gem", "idea perceiving assisting controlling stone", "notion detecting helping commanding mineral",
        "mind shielding helmet", "thought protecting directing headgear", "idea guarding controlling cranial covering", "notion defending commanding head protection",
        "emotion manipulating music", "feeling controlling directing melody", "sentiment adjusting controlling harmony", "affect altering commanding tune",
        "emotional shield creating meditation", "feeling protection forming directing contemplation", "sentiment guard making controlling reflection", "affect barrier producing commanding thought",
        "illusion creating prism", "false appearance generating directing crystal", "deceptive image producing controlling glass object", "misleading vision making commanding transparent item",
        "illusion dispelling dust", "false appearance removing directing powder", "deceptive image eliminating controlling granules", "misleading vision destroying commanding particles",
        "life force manipulating crystal", "vitality controlling directing gem", "existence energy adjusting controlling stone", "being power altering commanding mineral",
        "life energy shielding amulet", "vitality protecting directing pendant", "existence force guarding controlling necklace", "being power defending commanding jewelry",
        "magical energy channeling staff", "arcane power directing rod", "mystical force guiding controlling wand", "sorcerous might channeling commanding baton",
        "magic dampening iron", "arcane weakening directing metal", "mystical diminishing controlling element", "sorcerous reducing commanding material",
        "enchantment breaking bell", "spell destroying directing instrument", "charm eliminating controlling device", "incantation annihilating commanding object",
        "curse removing holy water", "hex eliminating directing sacred liquid", "jinx destroying controlling blessed fluid", "spell annihilating commanding consecrated solution",
        "blessing bestowing prayer", "benediction providing directing supplication", "invocation giving controlling petition", "prayer offering commanding entreaty",
        "luck manipulating dice", "fortune controlling directing cubes", "chance adjusting controlling polyhedrons", "happenstance altering commanding gaming pieces",
        "fate weaving spindle", "destiny controlling directing spinning tool", "kismet adjusting controlling fiber implement", "providence altering commanding thread device",
        "divine power channeling altar", "godly energy directing raised surface", "sacred force guiding controlling elevated platform", "holy might channeling commanding table",
        "infernal energy channeling pentagram", "devilish power directing five-pointed star", "hellish force guiding controlling geometric shape", "demonic might channeling commanding symbol",
        "ghost repelling salt", "spirit deterring directing mineral", "specter discouraging controlling substance", "phantom dissuading commanding matter",
        "undead controlling staff", "reanimated directing rod", "revived adjusting controlling wand", "resurrected manipulating commanding baton",
        "vampiric weakening sunlight", "blood-drinker debilitating directing illumination", "hemophage enfeebling controlling radiance", "sanguinivore reducing commanding brightness",
        "werewolf controlling silver chain", "lycanthrope directing metal links", "shape-shifter adjusting controlling metallic fetters", "skin-changer manipulating commanding argentous restraint",
        "dragon commanding horn", "wyrm directing instrument", "drake adjusting controlling device", "serpent manipulating commanding object",
        "giant controlling drum", "colossus directing percussion", "titan adjusting controlling instrument", "behemoth manipulating commanding device",
        "fey manipulating music", "fairy directing melody", "sprite adjusting controlling harmony", "pixie manipulating commanding tune",
        "elemental controlling pentacle", "primal force directing five-pointed star", "fundamental energy adjusting controlling geometric symbol", "essential power manipulating commanding magical shape",
        "golem animating scroll", "construct vivifying directing parchment", "automaton enlivening controlling document", "manufactured being animating commanding paper",
        "golem deactivating chant", "construct stopping directing vocalization", "automaton halting controlling intonation", "manufactured being deactivating commanding song",
        "detection divining rod", "discovery facilitating directing stick", "finding assisting controlling branch", "locating helping commanding twig",
        "concealment enabling cloak", "hiding facilitating directing garment", "covering assisting controlling attire", "masking helping commanding clothing",
        "preservation ensuring salt", "conservation facilitating directing mineral", "maintenance assisting controlling substance", "retention helping commanding matter",
        "decay accelerating mold", "deterioration hastening directing fungus", "degradation quickening controlling growth", "decomposition expediting commanding organism",
        "strength enhancing gauntlet", "might improving directing glove", "power augmenting controlling mitt", "force intensifying commanding handwear",
        "weakness causing chain", "debility creating directing links", "frailty producing controlling fetters", "feebleness generating commanding restraint",
        "intelligence improving tome", "intellect enhancing directing book", "acumen augmenting controlling volume", "brainpower intensifying commanding manuscript",
        "stupidity causing brew", "denseness creating directing concoction", "dullness producing controlling mixture", "slow-wittedness generating commanding liquid",
        "wisdom granting meditation", "sagacity providing directing contemplation", "prudence bestowing controlling reflection", "judiciousness giving commanding thought",
        "foolishness causing distraction", "imprudence creating directing diversion", "indiscretion producing controlling amusement", "rashness generating commanding entertainment",
        "charisma enhancing mask", "charm improving directing covering", "allure augmenting controlling disguise", "appeal intensifying commanding façade",
        "repulsiveness causing potion", "unattractiveness creating directing draught", "unappealingness producing controlling elixir", "repellence generating commanding beverage",
        "constitution enhancing amulet", "physical resilience improving directing pendant", "bodily toughness augmenting controlling necklace", "corporeal sturdiness intensifying commanding jewelry",
        "frailty causing curse", "physical weakness creating directing malediction", "bodily vulnerability producing controlling imprecation", "corporeal fragility generating commanding execration",
        "dexterity enhancing gloves", "agility improving directing handwear", "nimbleness augmenting controlling mittens", "adroitness intensifying commanding gauntlets",
        "clumsiness causing fetters", "awkwardness creating directing shackles", "ineptitude producing controlling restraints", "ungainliness generating commanding bindings",
        "health restoring elixir", "vitality providing directing potion", "wellness bestowing controlling draught", "fitness giving commanding beverage",
        "sickness causing miasma", "illness creating directing vapor", "disease producing controlling gas", "ailment generating commanding emission",
        "regeneration enabling crystal", "recovery facilitating directing gem", "healing assisting controlling stone", "mending helping commanding mineral",
        "wound exacerbating dust", "injury worsening directing powder", "damage aggravating controlling granules", "harm intensifying commanding particles",
        "youth preserving apple", "adolescence maintaining directing fruit", "young age continuing controlling produce", "juvenile persisting commanding edible",
        "aging accelerating potion", "senescence hastening directing draught", "elderlihood quickening controlling elixir", "old age expediting commanding beverage",
        "immortality granting water", "deathlessness providing directing liquid", "eternal life bestowing controlling fluid", "endless existence giving commanding solution",
        "mortality ensuring dust", "finiteness creating directing powder", "limited lifespan producing controlling granules", "definite existence generating commanding particles",
        "beauty enhancing cosmetics", "attractiveness improving directing makeup", "loveliness augmenting controlling preparations", "charm intensifying commanding substances",
        "ugliness causing potion", "unattractiveness creating directing draught", "unloveliness producing controlling elixir", "repellence generating commanding beverage",
        "shapechanging enabling belt", "form altering facilitating directing strap", "appearance shifting assisting controlling band", "semblance changing helping commanding girdle",
        "form fixing manacles", "shape securing directing shackles", "appearance fastening controlling restraints", "semblance fixing commanding bindings",
        "size increasing mushroom", "mass enlarging directing fungus", "volume expanding controlling growth", "dimension augmenting commanding organism",
        "size decreasing potion", "mass reducing directing draught", "volume shrinking controlling elixir", "dimension diminishing commanding beverage",
        "invisibility granting elixir", "unseen state providing directing potion", "imperceptible condition bestowing controlling draught", "undetectable status giving commanding beverage",
        "visibility ensuring dust", "seen state creating directing powder", "perceptible condition producing controlling granules", "detectable status generating commanding particles",
        "etherealness enabling mist", "incorporeality facilitating directing vapor", "immateriality assisting controlling gas", "insubstantiality helping commanding emission",
        "solidity ensuring stone", "corporeality creating directing rock", "materiality producing controlling mineral", "substantiality generating commanding element",
        "levitation enabling feather", "hovering facilitating directing plume", "suspension assisting controlling quill", "floating helping commanding plumage",
        "groundedness ensuring boots", "earthbinding facilitating directing footwear", "terra securing assisting controlling shoes", "soil fastening helping commanding sandals",
        "flight enabling cape", "aerial movement facilitating directing garment", "airborne travel assisting controlling attire", "sky traversal helping commanding clothing",
        "earthbinding chains", "ground fixing directing links", "terra securing controlling fetters", "soil fastening commanding restraint",
        "water breathing allowing necklace", "liquid respiration facilitating directing pendant", "fluid inhalation assisting controlling jewelry", "aqueous breathing helping commanding ornament",
        "air requiring gills", "atmosphere necessitating directing respiratory organs", "gas demanding controlling breathing apparatus", "oxygen compelling commanding respiratory feature",
        "firewalking enabling boots", "flame traversing facilitating directing footwear", "blaze crossing assisting controlling shoes", "inferno walking helping commanding sandals",
        "fire vulnerability causing oil", "flame susceptibility creating directing liquid", "blaze defenselessness producing controlling fluid", "inferno exposure generating commanding solution",
        "elemental immunity granting talisman", "primal force invulnerability providing directing charm", "fundamental energy imperviousness bestowing controlling amulet", "essential power invincibility giving commanding trinket",
        "elemental vulnerability causing hex", "primal force susceptibility creating directing curse", "fundamental energy defenselessness producing controlling jinx", "essential power exposure generating commanding spell",
        "water walking enabling sandals", "liquid surface traversing facilitating directing footwear", "fluid top crossing assisting controlling shoes", "aqueous plane walking helping commanding footgear",
        "sinking causing weights", "submersion creating directing masses", "immersion producing controlling burdens", "submergence generating commanding loads",
        "air walking enabling boots", "atmospheric traversing facilitating directing footwear", "gaseous crossing assisting controlling shoes", "aerial plane walking helping commanding sandals",
        "falling causing grease", "descent creating directing lubricant", "dropping producing controlling slippery substance", "plummeting generating commanding unctuous matter",
        "stone walking enabling boots", "mineral traversing facilitating directing footwear", "rock crossing assisting controlling shoes", "earthen plane walking helping commanding sandals",
        "sinking in stone causing curse", "mineral submersion creating directing hex", "rock immersion producing controlling jinx", "earthen submergence generating commanding spell",
        "telekinesis enabling circlet", "psychokinesis facilitating directing headband", "mind-movement assisting controlling diadem", "thought-motion helping commanding headdress",
        "immobility causing restraint", "motionlessness creating directing fetters", "stillness producing controlling bonds", "stasis generating commanding chains",
        "telepathy enabling crystal", "thought-transference facilitating directing gem", "mind-communication assisting controlling stone", "mental-message helping commanding mineral",
        "thought blocking helmet", "idea preventing directing headgear", "notion stopping controlling head protection", "concept impeding commanding cranial covering",
        "clairvoyance enabling crystal ball", "remote-viewing facilitating directing orb", "distant-seeing assisting controlling sphere", "far-observation helping commanding globe",
        "blindness causing blindfold", "sightlessness creating directing eye covering", "visual impairment producing controlling eye mask", "vision loss generating commanding eye wrap",
        "precognition enabling mirror", "future-seeing facilitating directing reflector", "forthcoming-viewing assisting controlling looking glass", "prospective-observation helping commanding speculum",
        "ignorance of future causing cloud", "foreknowledge preventing directing vapor mass", "prescience stopping controlling aerial condensation", "foresight impeding commanding atmospheric phenomenon",
        "retrocognition enabling pendant", "past-seeing facilitating directing necklace", "bygone-viewing assisting controlling jewelry", "historical-observation helping commanding ornament",
        "ignorance of past causing draught", "hindsight preventing directing potion", "retrospection stopping controlling elixir", "backwards-looking impeding commanding beverage",
        "teleportation enabling chalk", "instant-movement facilitating directing writing implement", "immediate-travel assisting controlling utensil", "instantaneous-traversal helping commanding tool",
        "immobility ensuring stake", "motionlessness creating directing wooden post", "stillness producing controlling timber piece", "stasis generating commanding wooden implement",
        "dimensional travel enabling key", "planar-movement facilitating directing implement", "reality-shifting assisting controlling device", "existence-traversing helping commanding object",
        "dimensional anchoring chain", "planar-fixing directing links", "reality-securing controlling fetters", "existence-fastening commanding restraint",
        "time travel enabling hourglass", "chronological-movement facilitating directing timepiece", "temporal-shifting assisting controlling device", "era-traversing helping commanding instrument",
        "time anchoring sundial", "chronological-fixing directing timepiece", "temporal-securing controlling device", "era-fastening commanding instrument",
        "probability manipulating dice", "chance-control facilitating directing cubes", "likelihood-adjustment assisting controlling polyhedrons", "possibility-alteration helping commanding gaming pieces",
        "fate binding contract", "destiny-fixing directing agreement", "kismet-securing controlling pact", "providence-fastening commanding covenant",
        "wish granting lamp", "desire-fulfilling directing container", "want-satisfying controlling vessel", "craving-appeasing commanding receptacle",
        "wish preventing iron box", "desire-stopping directing metal container", "want-preventing controlling ferrous vessel", "craving-impeding commanding metallic receptacle",
        "truth compelling throne", "veracity-forcing directing seat", "honesty-compelling controlling chair", "accuracy-necessitating commanding royal furniture",
        "falsehood enabling mask", "deception-facilitating directing covering", "dishonesty-assisting controlling disguise", "inaccuracy-helping commanding façade",
        "animal communication enabling collar", "beast-speech facilitating directing neckband", "creature-dialect assisting controlling neckwear", "fauna-language helping commanding neck ring",
        "silence enforcing muzzle", "quietude-creating directing mouth covering", "soundlessness-producing controlling snout wrap", "noiselessness-generating commanding oral restraint",
        "plant growth accelerating fertilizer", "vegetation-development hastening directing nutrient", "flora-maturation quickening controlling substance", "botanical-advancement expediting commanding matter",
        "plant withering causing salt", "vegetation-deterioration creating directing mineral", "flora-degradation producing controlling substance", "botanical-decline generating commanding matter",
        "elemental summoning pentacle", "primal-force calling directing five-pointed star", "fundamental-energy inviting controlling geometric symbol", "essential-power beckoning commanding magical shape",
        "elemental banishing hexagram", "primal-force expelling directing six-pointed star", "fundamental-energy removing controlling geometric symbol", "essential-power dismissing commanding magical shape",
        "fire calling flint and steel", "flame-summoning directing striking implements", "blaze-inviting controlling igniting tools", "inferno-beckoning commanding fire starters"
    ],
    "sci_fi": [
        "advanced futuristic", "cyber environment", "glowing neon", "advanced technology", "humanoid robot", "cyberpunk",
        "future city", "interactive hologram", "digital interface", "spaceship",
        "laser weapons", "futuristic armor", "android", "augmented reality",
        "alien planet", "space station", "cybernetic implants", "android", "visual AI",
        "neon-layered street", "megastructure", "3D hologram", "wormhole portal",
        "quantum computer", "neural interface", "virtual reality", "artificial intelligence",
        "holographic display", "data visualization", "robotic exoskeleton", "mechanized suit",
        "antigravity device", "levitation technology", "hover vehicle", "flying car",
        "teleportation pad", "matter transmitter", "warp drive", "faster-than-light travel",
        "space elevator", "orbital ring", "dyson sphere", "stellar engine",
        "terraforming machine", "climate controller", "weather manipulator", "atmospheric processor",
        "force field", "energy shield", "particle barrier", "deflector array",
        "tractor beam", "gravity manipulator", "mass effect field", "inertial dampener",
        "laser cannon", "plasma weapon", "ion blaster", "railgun",
        "power armor", "battle suit", "combat chassis", "military exoskeleton",
        "nanite swarm", "microscopic robots", "self-replicating machines", "molecular assemblers",
        "neural implant", "brain-computer interface", "mind link", "thought transmitter",
        "cybernetic enhancement", "bionic augmentation", "artificial limb", "synthetic organ",
        "genetic modification", "DNA engineering", "biotech enhancement", "transgenic organism",
        "cloning facility", "genetic duplicate", "artificial womb", "synthetic life",
        "android servant", "robotic assistant", "mechanical helper", "synthetic companion",
        "artificial intelligence", "sentient computer", "machine consciousness", "digital sentience",
        "virtual environment", "simulated reality", "digital world", "computer-generated universe",
        "augmented reality", "enhanced perception", "overlaid information", "digital enhancement",
        "holographic projection", "three-dimensional display", "volumetric imaging", "spatial visualization",
        "neural network", "artificial brain", "synthetic mind", "electronic consciousness",
        "quantum processor", "supercomputer", "data center", "computational array",
        "alien architecture", "extraterrestrial structure", "non-human building", "xenoform construction",
        "interstellar ship", "space vessel", "stellar craft", "cosmic transport",
        "planetary colony", "offworld settlement", "extraterrestrial outpost", "space habitat",
        "orbital station", "space platform", "stellar facility", "cosmic installation",
        "lunar base", "moon colony", "satellite outpost", "natural satellite facility",
        "martian settlement", "red planet colony", "fourth planet outpost", "rust-colored world installation",
        "asteroid mining", "space rock harvesting", "meteor extraction", "celestial body excavation",
        "gas giant harvester", "jovian collector", "massive planet extractor", "gaseous world processor",
        "atmosphere processor", "air converter", "gas transformer", "breathable environment creator",
        "terraforming device", "world shaper", "planet transformer", "environment converter",
        "climate controller", "weather manipulator", "atmospheric adjuster", "meteorological processor",
        "hydroponic farm", "soilless agriculture", "water-based cultivation", "nutrient solution growing",
        "vertical farm", "stacked agriculture", "layered cultivation", "elevated growing system",
        "food synthesizer", "nutrient generator", "meal materializer", "sustenance creator",
        "water reclaimer", "liquid purifier", "moisture recycler", "hydration processor",
        "fusion reactor", "plasma generator", "nuclear combiner", "atomic energy source",
        "antimatter engine", "opposite mass reactor", "contrasting energy generator", "negative matter power source",
        "zero-point energy", "vacuum potential harvester", "empty space power", "nothing energy extractor",
        "quantum battery", "subatomic energy storage", "particle power bank", "wave-function capacitor",
        "solar collector", "stellar energy harvester", "sun power absorber", "photonic gatherer",
        "starlight harvester", "distant sun collector", "cosmic ray absorber", "interstellar energy gatherer",
        "ion engine", "charged particle propulsion", "electric exhaust thruster", "plasma pushing drive",
        "warp drive", "space-folding propulsion", "reality-bending engine", "metric-warping system",
        "jump drive", "instantaneous transit system", "immediate translation engine", "sudden transport mechanism",
        "hyperspace engine", "dimension-shifting drive", "alternate-reality propulsion", "other-space transit system",
        "gravity generator", "mass simulator", "weight producer", "attraction field creator",
        "antigravity platform", "weightlessness pad", "float inducer", "levitation generator",
        "inertial dampener", "motion-impact reducer", "acceleration-effect lessener", "movement-force diminisher",
        "artificial gravity", "simulated weight", "synthetic mass effect", "replicated planetary pull",
        "stasis field", "time-stopping zone", "temporal halt area", "chronological pause region",
        "time accelerator", "clock-speeding device", "temporal hastener", "chronological accelerator",
        "time dilation device", "relative-time manipulator", "temporal relativity generator", "chronological stretching mechanism",
        "personal shield", "individual barrier", "body-surrounding protector", "self-enclosing defense",
        "deflector array", "incoming-projectile blocker", "weapon-fire repeller", "attack redirector",
        "energy shield", "power barrier", "force protector", "active defense system",
        "cloaking device", "visibility negator", "visual concealer", "sight-blocking technology",
        "phase shifter", "matter-state alternator", "solidity adjuster", "permeability controller",
        "teleporter pad", "matter transmitter", "instantaneous relocation device", "spatial translation platform",
        "molecular printer", "atomic constructor", "particle assembler", "matter fabricator",
        "replicator", "object duplicator", "item copier", "material reproducer",
        "matter recycler", "substance reprocessor", "material reclaimer", "object recomposer",
        "medical scanner", "health analyzer", "biological examiner", "physiological assessment tool",
        "diagnostic bed", "ailment identifier", "condition determiner", "medical analysis platform",
        "healing accelerator", "recovery enhancer", "convalescence hastener", "recuperation speeder",
        "surgical robot", "medical automaton", "operation mechanoid", "procedure android",
        "brain scanner", "mind analyzer", "thought examiner", "mental assessment tool",
        "memory recorder", "recollection capturer", "reminiscence documenter", "remembrance preserver",
        "memory implanter", "recollection inserter", "artificial reminiscence introducer", "synthetic remembrance installer",
        "neural programmer", "brain coder", "mind software installer", "cerebral application implementer",
        "neural interfacer", "brain connector", "mind linker", "cerebral networker",
        "consciousness transferer", "mind relocater", "awareness shifter", "self-mover",
        "sensory simulator", "perception imitator", "feeling replicator", "experience synthesizer",
        "virtual reality pod", "simulated experience chamber", "digital environment capsule", "computer-generated world container",
        "haptic feedback suit", "touch-sensation outfit", "tactile response garment", "feeling-transmitting attire",
        "olfactory simulator", "smell replicator", "scent synthesizer", "aroma generator",
        "gustatory emulator", "taste imitator", "flavor replicator", "savor synthesizer",
        "audiovisual implant", "sight-sound augmenter", "eye-ear enhancer", "visual-auditory device",
        "universal translator", "all-language interpreter", "omni-speech decoder", "pan-linguistic processor",
        "alien language decipherer", "extraterrestrial communication decoder", "xenolinguistic interpreter", "non-human dialogue translator",
        "telepathic amplifier", "thought-broadcasting enhancer", "mind-transmission booster", "psychic communication strengthener",
        "empathic receiver", "emotion detector", "feeling sensor", "sentiment perceiver",
        "drone controller", "remote operator", "distance manipulator", "afar director",
        "robot commander", "automaton controller", "mechanoid director", "android commander",
        "swarm coordinator", "multi-unit director", "numerous-entity controller", "many-robot commander",
        "satellite uplink", "orbital connection", "space station communicator", "stellar installation connector",
        "interplanetary communicator", "world-to-world transmitter", "planet connector", "celestial body communicator",
        "interstellar communicator", "star-to-star transmitter", "solar system connector", "between-suns communicator",
        "quantum entanglement communicator", "particle-link transmitter", "subatomic connection device", "instantaneous quantum messenger",
        "ansible", "instant communicator", "zero-delay transmitter", "immediate messenger",
        "holographic projector", "three-dimensional image creator", "volumetric display generator", "spatial visualization producer",
        "holographic recorder", "three-dimensional event capturer", "volumetric scene documenter", "spatial happening preserver",
        "data crystal", "information gem", "knowledge stone", "fact mineral",
        "neural storage", "brain-pattern container", "mind-data holder", "thought repository",
        "quantum storage", "subatomic data container", "particle information holder", "wave-function repository",
        "data center", "information facility", "knowledge building", "fact storage location",
        "artificial intelligence core", "synthetic mind center", "electronic brain heart", "digital consciousness nucleus",
        "mainframe", "central computer", "primary processing unit", "principle calculation system",
        "server farm", "multi-computer facility", "numerous processor location", "many-calculation-unit site",
        "distributed network", "decentralized system", "spread-out connection", "dispersed computing arrangement",
        "quantum network", "subatomic connection system", "particle-link arrangement", "wave-function relationship structure",
        "neural network", "brain-like connection system", "mind-imitating relationship structure", "cerebral-copying arrangement",
        "cyberdeck", "digital access tool", "electronic entry device", "computational interface mechanism",
        "heads-up display", "visual information overlay", "sight-based data projection", "eye-level fact presentation",
        "retinal projector", "eye-surface image creator", "cornea-directed display generator", "optic visualization producer",
        "augmented reality glasses", "enhanced-vision eyewear", "supplemented-perception spectacles", "improved-sight goggles",
        "smart contact lenses", "intelligent eye covers", "computational eye surfaces", "processing vision aids",
        "neuro-optical implant", "brain-eye connection device", "mind-sight linking mechanism", "cerebral-visual interface apparatus",
        "cyber-arm", "electronic limb", "mechanical appendage", "robotic extremity",
        "cyber-leg", "electronic lower limb", "mechanical walking appendage", "robotic ambulatory extremity",
        "cyber-hand", "electronic grasper", "mechanical manipulator", "robotic gripping extremity",
        "cyber-eye", "electronic visual organ", "mechanical sight apparatus", "robotic seeing device",
        "cyber-ear", "electronic hearing organ", "mechanical auditory apparatus", "robotic listening device",
        "cyber-heart", "electronic pumping organ", "mechanical circulation apparatus", "robotic blood-moving device",
        "cyber-lung", "electronic breathing organ", "mechanical respiration apparatus", "robotic air-processing device",
        "neural implant", "brain connection device", "mind interface mechanism", "cerebral linking apparatus",
        "cerebral processor", "brain calculation device", "mind computation mechanism", "thought processing apparatus",
        "memory enhancer", "recollection improver", "reminiscence booster", "remembrance strengthener",
        "skill implant", "ability inserter", "capability introducer", "talent installer",
        "reflex booster", "reaction enhancer", "response improver", "quickness augmenter",
        "strength amplifier", "force increaser", "power magnifier", "might enhancer",
        "endurance extender", "stamina prolonger", "lasting-power increaser", "perseverance enhancer",
        "regeneration stimulator", "healing accelerator", "recovery hastener", "mending speedup",
        "pain suppressor", "discomfort blocker", "hurt preventer", "ache stopper",
        "sensory enhancer", "perception improver", "feeling intensifier", "experience augmenter",
        "adrenaline controller", "excitement hormone regulator", "thrill chemical adjuster", "rush substance manipulator",
        "emotion regulator", "feeling controller", "sentiment adjuster", "affect manipulator",
        "thought filter", "idea screener", "notion selector", "concept chooser",
        "sleeping gas", "unconsciousness vapor", "slumber fumes", "rest-inducing emission",
        "truth serum", "honesty-inducing liquid", "veracity-causing fluid", "accuracy-compelling solution",
        "intelligence booster", "smartness enhancer", "cleverness increaser", "brainpower augmenter",
        "radiation shield", "energy-protection barrier", "ray-blocking screen", "emission-stopping barrier",
        "environment suit", "surrounding-condition protection", "external-situation defense", "outside-circumstance safety outfit",
        "space suit", "vacuum protection", "void-condition defense", "cosmic-situation safety outfit",
        "hazmat suit", "dangerous-material protection", "harmful-substance defense", "toxic-element safety outfit",
        "powered armor", "energy-enhanced protection", "force-amplified defense", "strength-augmented safety outfit",
        "exoskeleton", "external skeleton", "outer framework", "outside support structure",
        "jetpack", "personal flight device", "individual aerial system", "self-contained flying apparatus",
        "grappling hook", "distance-grabbing tool", "far-reaching catcher", "remote grasper",
        "energy blade", "power cutting implement", "force slicing tool", "intensity carving instrument",
        "plasma cutter", "superhot-matter slicing implement", "ionized-gas cutting tool", "extreme-temperature carving instrument",
        "laser drill", "light-beam boring implement", "photon excavating tool", "optical perforating instrument",
        "gravity gun", "mass-manipulation weapon", "weight-control firearm", "attraction-force directing instrument",
        "freeze ray", "cold-inducing beam", "temperature-lowering emission", "chilling radiation projector",
        "heat ray", "warmth-inducing beam", "temperature-raising emission", "hot radiation projector",
        "shrink ray", "size-reducing beam", "dimension-decreasing emission", "miniaturizing radiation projector",
        "growth ray", "size-increasing beam", "dimension-expanding emission", "enlarging radiation projector",
        "disintegrator", "matter-destroying device", "substance-eliminating mechanism", "material-vanishing apparatus",
        "paralysis beam", "movement-stopping emission", "motion-halting radiation", "activity-freezing projection",
        "mind control ray", "thought-directing beam", "brain-commanding emission", "mental-dominating radiation",
        "emotion beam", "feeling-inducing emission", "sentiment-creating radiation", "affect-generating projection",
        "hologram disguiser", "three-dimensional image concealer", "volumetric-display camouflager", "spatial-visualization masker",
        "voice changer", "sound-altering device", "audio-modifying mechanism", "speech-transforming apparatus",
        "invisibility cloak", "unseen-making garment", "visibility-negating covering", "perception-avoiding attire",
        "chameleon suit", "environment-matching garment", "surrounding-blending covering", "background-adapting attire",
        "gravity boots", "weight-manipulating footwear", "mass-controlling shoes", "attraction-force adjusting sandals",
        "mag-boots", "magnetic-attaching footwear", "attractive-force shoes", "ferrous-connecting sandals",
        "jet boots", "propulsion footwear", "thrust-generating shoes", "force-expelling sandals",
        "hover platform", "floating surface", "levitating base", "suspended foundation",
        "teleport beacon", "relocation signal", "position-shifting indicator", "translocation marker",
        "jump gate", "instant-travel portal", "immediate-movement doorway", "sudden-transport entrance",
        "wormhole generator", "space-bending creator", "reality-folding producer", "dimension-warping maker",
        "stargate", "stellar transport", "sun-to-sun travel", "interstellar doorway",
        "portal gun", "doorway creator", "entrance maker", "access point generator",
        "dimensional doorway", "reality-connecting entrance", "universe-linking access", "plane-joining portal",
        "subspace communicator", "underspace transmitter", "lower-dimension messenger", "beneath-reality connector",
        "quantum communicator", "subatomic transmitter", "particle-state messenger", "wave-function connector",
        "drone swarm", "robot collective", "automaton group", "mechanoid gathering",
        "nano assembler", "microscopic constructor", "tiny builder", "minuscule creator",
        "molecular disassembler", "atomic deconstructor", "elemental separator", "substance-dividing mechanism",
        "particle accelerator", "atom speeder", "electron hastener", "subatomic velocity increaser",
        "terraform machine", "planet transformer", "world-condition changer", "celestial-body environment modifier",
        "weather controller", "atmospheric-condition director", "meteorological phenomenon regulator", "climate situation adjuster",
        "climate regulator", "long-term atmospheric director", "enduring meteorological regulator", "persistent weather adjuster",
        "atmosphere processor", "air transformer", "gas-composition changer", "breathable-condition creator",
        "water purifier", "liquid cleaner", "fluid decontaminator", "aqueous-substance filter",
        "matter compiler", "substance organizer", "material systematizer", "stuff arranger",
        "quantum computer", "subatomic calculator", "particle-state processor", "wave-function manipulator",
        "neural processor", "brain-like calculator", "mind-imitating computer", "cerebral-copying manipulator",
        "holographic computer", "three-dimensional calculator", "volumetric processor", "spatial-image manipulator",
        "biological computer", "living calculator", "organic processor", "life-based manipulator",
        "DNA computer", "genetic calculator", "hereditary-material processor", "gene-based manipulator",
        "protein computer", "amino-acid calculator", "organic-compound processor", "biological-molecule manipulator",
        "crystalline computer", "gem-structure calculator", "mineral-formation processor", "stone-configuration manipulator",
        "optical computer", "light-based calculator", "photonic processor", "visual-phenomenon manipulator",
        "quantum-entangled particles", "subatomic connected elements", "particle-linked components", "wave-function related items",
        "temporal manipulator", "time-affecting device", "chronological-influence mechanism", "era-altering apparatus",
        "chrono-viewer", "time-seeing machine", "era-observing mechanism", "period-watching apparatus",
        "future predictor", "forthcoming-event calculator", "upcoming-situation processor", "prospective-circumstance manipulator",
        "probability calculator", "likelihood processor", "chance manipulator", "possibility computer",
        "alternate reality viewer", "different-possibility observer", "other-circumstance watcher", "varied-situation examiner",
        "parallel universe portal", "different-reality doorway", "other-existence entrance", "varied-being access",
        "memory extractor", "recollection remover", "reminiscence taker", "remembrance withdrawer",
        "dream recorder", "sleep-vision documenter", "slumber-image preserver", "rest-scene capturer",
        "mind reader", "thought detector", "idea perceiver", "notion discerner",
        "emotion detector", "feeling perceiver", "sentiment discerner", "affect sensor",
        "lie detector", "falsehood perceiver", "untruth discerner", "dishonesty sensor",
        "psychic amplifier", "mental-power increaser", "mind-ability enhancer", "thought-capacity booster",
        "telekinetic enhancer", "mind-movement intensifier", "thought-motion strengthener", "psychokinetic amplifier",
        "telepathic booster", "mind-communication intensifier", "thought-transmission strengthener", "psychic-connection amplifier",
        "precognitive stimulator", "future-seeing intensifier", "forthcoming-event perception strengthener", "prospective-vision amplifier",
        "psychotronic generator", "mind-affecting producer", "thought-influencing creator", "mental-impact maker",
        "brainwave scanner", "mind-oscillation examiner", "cerebral-frequency observer", "neural-vibration watcher",
        "consciousness detector", "awareness perceiver", "sentience discerner", "mindfulness sensor",
        "soul detector", "spirit perceiver", "essence discerner", "being sensor",
        "aura visualizer", "energy-field shower", "force-aura displayer", "power-surrounding manifester",
        "chi manipulator", "life-force controller", "vital-energy director", "essential-power regulator",
        "bioenergy channeler", "life-power director", "organismic-force guider", "living-energy conductor",
        "force field generator", "energy-barrier creator", "power-shield producer", "intensity-protection maker",
        "gravity well", "mass-attraction zone", "weight-increase region", "pulling-force area",
        "antigravity zone", "mass-repulsion region", "weight-decrease area", "pushing-force location",
        "null gravity field", "weightlessness zone", "massless region", "no-pull area",
        "hypergravity region", "extreme-weight zone", "intense-pull region", "super-attraction area",
        "suspended animation chamber", "paused-life container", "halted-existence vessel", "stopped-being receptacle",
        "life support pod", "existence-maintaining container", "being-sustaining vessel", "living-preserving receptacle",
        "stasis field generator", "suspended-time creator", "halted-moment producer", "paused-instant maker",
        "time acceleration field", "chronological-hastening zone", "moment-quickening region", "instant-speeding area",
        "time dilation zone", "chronological-stretching region", "moment-extending area", "instant-prolonging location",
        "pocket dimension", "small-reality space", "compact-universe region", "mini-existence area",
        "spatial fold", "space-bending region", "dimension-curving area", "reality-warping location",
        "quantum fluctuation", "subatomic variation", "particle-state change", "wave-function alteration",
        "energy vortex", "power whirlpool", "force spiral", "intensity swirl",
        "plasma field", "superheated-matter zone", "ionized-gas region", "extreme-energy area",
        "electromagnetic pulse", "electric-magnetic wave", "voltage-field propagation", "current-area expansion",
        "ion storm", "charged-particle tempest", "electric-atom squall", "ionic-element gale",
        "cosmic radiation", "space-originated energy", "universal-source power", "celestial-emitted force",
        "solar wind", "sun-originated flow", "star-emitted current", "stellar-derived stream",
        "gamma ray burst", "high-energy light explosion", "intense-photon eruption", "powerful-radiation detonation",
        "neutrino flux", "neutral-particle flow", "zero-charge stream", "massless-element current",
        "dark matter concentration", "unseen-mass gathering", "invisible-substance collection", "undetectable-material aggregation",
        "dark energy field", "unknown-force zone", "mysterious-power region", "unexplained-intensity area",
        "zero-point energy", "vacuum-state power", "empty-space force", "nothing-condition intensity",
        "tachyon burst", "faster-than-light particle explosion", "superluminal element eruption", "beyond-c corpuscle detonation",
        "graviton wave", "gravity-particle oscillation", "mass-force undulation", "weight-power fluctuation",
        "dimensional rift", "reality-tear opening", "existence-rip gap", "universe-split break",
        "spacetime anomaly", "reality-oddity circumstance", "existence-strangeness situation", "universe-abnormality condition",
        "temporal paradox", "time-contradiction circumstance", "chronological-impossibility situation", "moment-conflict condition",
        "causal loop", "effect-cause-effect circle", "result-origin-result cycle", "consequence-source-consequence rotation",
        "multiverse nexus", "all-reality junction", "every-universe connection", "total-existence intersection",
        "reality anchor", "existence stabilizer", "universe steadier", "cosmos balancer",
        "infinity circuit", "endless loop", "boundless cycle", "limitless rotation",
        "eternity engine", "everlasting mechanism", "perpetual apparatus", "ceaseless device",
        "singularity core", "infinite-density center", "boundless-mass heart", "limitless-weight nucleus",
        "event horizon", "no-return boundary", "impossible-escape perimeter", "inevitable-capture edge",
        "black hole", "light-trapping phenomenon", "radiation-capturing event", "illumination-seizing occurrence",
        "white hole", "light-emitting phenomenon", "radiation-releasing event", "illumination-expelling occurrence",
        "wormhole", "space-connecting tunnel", "dimension-linking passage", "reality-joining corridor",
        "space-time distortion", "reality-warping effect", "existence-bending influence", "universe-flexing impact",
        "quantum entanglement", "subatomic connection", "particle-state relationship", "wave-function linkage",
        "antimatter containment", "opposite-substance vessel", "contrary-material receptacle", "inverse-matter container",
        "cold fusion reactor", "low-temperature combining device", "cool-condition merging mechanism", "reduced-heat joining apparatus",
        "zero-point reactor", "vacuum-energy device", "empty-space power mechanism", "nothing-force apparatus",
        "matter-energy converter", "substance-to-power transformer", "material-to-force changer", "stuff-to-intensity modifier",
        "energy-matter converter", "power-to-substance transformer", "force-to-material changer", "intensity-to-stuff modifier",
        "stellar compressor", "star-crushing device", "sun-condensing mechanism", "astral-body compacting apparatus",
        "planetary engine", "world-moving device", "globe-propelling mechanism", "sphere-driving apparatus",
        "solar harvester", "sun-energy collector", "star-power gatherer", "stellar-force accumulator",
        "dyson sphere", "star-enclosing structure", "sun-surrounding construction", "stellar-encompassing formation",
        "stellar lifter", "star-material extractor", "sun-substance remover", "stellar-element withdrawer",
        "star forge", "solar-material processor", "sun-substance transformer", "stellar-element modifier",
        "megastructure", "enormous construction", "gigantic building", "colossal formation",
        "space habitat", "cosmic living area", "void dwelling place", "vacuum residence zone",
        "orbital ring", "planet-circling structure", "world-surrounding construction", "globe-encompassing formation",
        "space elevator", "orbital access structure", "cosmos-reaching tower", "star-connecting spire",
        "orbital defense", "space-protecting mechanism", "cosmic-guarding apparatus", "void-securing device",
        "planetary shield", "world-defending barrier", "globe-guarding screen", "sphere-protecting cover",
        "star lifter", "solar-substance extractor", "stellar-material remover", "sun-element withdrawer",
        "interstellar beacon", "between-stars signal", "cross-solar indicator", "trans-stellar marker",
        "hyperspace beacon", "dimension-crossing signal", "reality-traversing indicator", "existence-spanning marker",
        "subspace transponder", "underreality transmitter", "lower-dimension sender", "beneath-existence communicator",
        "ansible network", "instant-communication system", "zero-delay connection", "immediate-contact arrangement",
        "galactic positioning system", "star-location identifier", "cosmic-position determiner", "space-place finder",
        "star charts", "stellar-location documents", "cosmic-position records", "space-place information",
        "hyperspace routes", "dimension-crossing paths", "reality-traversing ways", "existence-spanning courses",
        "warp lanes", "space-bending paths", "reality-warping ways", "dimension-distorting courses",
        "jump coordinates", "instant-travel positions", "immediate-movement locations", "sudden-transport places",
        "neural interface", "brain connection", "mind link", "cerebral junction",
        "brain-computer link", "cerebral-digital connection", "mental-electronic junction", "psychological-technological interface",
        "virtual reality", "simulated existence", "artificial world", "synthetic universe",
        "augmented reality", "enhanced existence", "improved world", "supplemented universe",
        "mixed reality", "combined existence", "dual world", "merged universe",
        "holographic environment", "three-dimensional surroundings", "volumetric setting", "spatial context",
        "digital consciousness", "electronic awareness", "computerized sentience", "technological self-knowledge",
        "uploaded mind", "digitized consciousness", "computerized awareness", "electronic sentience",
        "artificial intelligence", "synthetic intellect", "man-made understanding", "constructed comprehension",
        "superhumanity", "beyond-person status", "above-mortal condition", "transcendent-human state",
        "transhumanism", "beyond-person philosophy", "above-mortal belief", "transcended-human thinking",
        "posthumanism", "after-person condition", "following-mortal state", "succeeding-human status",
        "technological singularity", "machine-surpassing event", "artificial-exceeding occurrence", "synthetic-transcending happening",
        "digital afterlife", "electronic hereafter", "computerized post-death", "technological next-existence",
        "mind backup", "consciousness copy", "awareness duplicate", "sentience reproduction",
        "cortical stack", "brain-data storage", "mind-information repository", "consciousness-detail container",
        "synthetic body", "artificial form", "man-made physique", "constructed figure",
        "android body", "humanoid-robot form", "person-machine physique", "human-automaton figure",
        "clone body", "genetic-duplicate form", "dna-copy physique", "hereditary-reproduction figure",
        "designer body", "custom-made form", "specially-created physique", "particularly-constructed figure",
        "gene therapy", "hereditary-material treatment", "dna medication", "genetic-substance remedy",
        "genetic engineering", "hereditary-material modification", "dna alteration", "gene changing",
        "selective breeding", "chosen reproduction", "particular mating", "specific pairing",
        "hybridization", "cross-type creation", "mixed-category production", "combined-class formation",
        "radiation mutation", "energy-alteration change", "power-modification transformation", "force-based variation",
        "viral vector", "disease-carrier deliverer", "illness-transport vehicle", "sickness-movement means",
        "nanite injection", "microscopic-robot introduction", "tiny-machine insertion", "minuscule-device placement",
        "neural programming", "brain coding", "mind software", "cerebral application",
        "memory overlay", "recollection covering", "reminiscence superimposition", "remembrance concealment",
        "memory implantation", "recollection insertion", "reminiscence introduction", "remembrance placement",
        "cognitive modification", "understanding alteration", "comprehension change", "intellectual transformation",
        "emotional regulation", "feeling control", "sentiment adjustment", "affect manipulation",
        "personality alteration", "character change", "nature transformation", "temperament modification",
        "behavioral conditioning", "action training", "conduct preparation", "deportment readying",
        "sensory enhancement", "perception improvement", "feeling intensification", "experience augmentation",
        "pain suppression", "discomfort reduction", "hurt diminishment", "ache lessening",
        "pleasure amplification", "enjoyment increase", "delight intensification", "gratification enhancement",
        "cybernetic integration", "electronic merging", "technological combining", "mechanical unifying",
        "neural lace", "brain mesh", "mind network", "cerebral web",
        "brain augmentation", "cerebral enhancement", "mind improvement", "psychological intensification",
        "cognitive implant", "understanding insert", "comprehension introduction", "intellectual placement",
        "memory enhancement", "recollection improvement", "reminiscence intensification", "remembrance augmentation",
        "skill implant", "ability insert", "capability introduction", "talent placement",
        "knowledge download", "information transfer", "fact transmission", "data movement",
        "reflex boosting", "reaction enhancement", "response improvement", "instinct augmentation",
        "strength augmentation", "force enhancement", "power improvement", "might augmentation",
        "speed increasing", "velocity enhancement", "quickness improvement", "rapidity augmentation",
        "endurance extension", "stamina enhancement", "perseverance improvement", "lasting-power augmentation",
        "immune enhancement", "disease-resistance improvement", "illness-opposition augmentation", "sickness-combating intensification",
        "regeneration acceleration", "healing hastening", "recovery quickening", "mending speeding",
        "age retardation", "senescence slowing", "elderlihood delaying", "old-age postponing",
        "longevity treatment", "long-life medication", "extended-existence remedy", "prolonged-being therapy",
        "immortality procedure", "deathlessness treatment", "endless-life"
        ],
        "body_detail_en": [
    # Anatomical structure (500)
    "perfect anatomical proportions", "ideal body symmetry", "anatomically correct figure", "balanced physical structure", "perfect body composition",
    "precise musculature definition", "anatomical perfection", "golden ratio proportions", "harmonious body structure", "ideal physical symmetry",
    "perfect biological structure", "anatomically detailed", "perfect bodily proportions", "anatomically precise", "ideal human proportions",
    "biologically accurate anatomy", "perfect physical proportions", "anatomically balanced", "ideal body architecture", "structurally perfect physique",
    "perfect skeletal structure", "anatomically flawless", "harmonious skeletal frame", "ideal anatomical balance", "perfect bodily symmetry",
    "natural body proportions", "anatomically harmonious", "balanced skeletal structure", "perfect biological proportions", "anatomically true",
    "ideal physical framework", "perfect body structure", "anatomically realistic", "correct body proportions", "perfect physiological structure",
    "harmonious physical symmetry", "anatomically proportionate", "ideal bodily framework", "perfect physical framework", "natural anatomical flow",
    "anatomically aligned", "ideal body framework", "balanced physical features", "perfect structural symmetry", "anatomically coherent",
    "flawless physical structure", "ideal skeletal alignment", "perfect corporal proportions", "anatomically proper", "balanced body architecture",
    "perfect structural alignment", "anatomically symmetrical", "ideal physical composition", "perfect biological alignment", "natural body symmetry",
    "anatomically balanced proportions", "ideal structure and form", "perfect physical harmony", "anatomically sound", "balanced body composition",
    "perfect bodily alignment", "anatomically refined", "ideal corporal structure", "flawless body architecture", "anatomically elegant",
    "perfect morphological structure", "ideal body harmony", "flawless anatomical design", "balanced structural alignment", "perfect physiological form",
    "ideal anatomical composition", "natural physical proportions", "balanced anatomical harmony", "perfect structural composition", "ideal biological structure",
    "anatomically exquisite", "perfect bodily structure", "ideal physical integrity", "anatomically harmonized", "natural structural balance",
    "perfect anatomical harmony", "ideal bodily symmetry", "balanced physiological structure", "anatomically ideal", "perfect physical geometry",
    "harmonious bodily composition", "ideal anatomical symmetry", "perfect structural integrity", "anatomically balanced design", "natural physical harmony",
    "ideal body geometry", "perfect anatomical alignment", "balanced corporal proportions", "harmonious skeletal proportions", "ideal body mechanics",
    "perfect physical configuration", "anatomically optimized", "balanced physiological proportions", "ideal structural design", "perfect body metrics",
    "anatomically well-proportioned", "harmonious body metrics", "ideal physical dimensions", "perfect structural proportions", "anatomically perfect dimensions",
    "balanced body metrics", "ideal anatomical measurements", "perfect physical measurements", "harmonious structural dimensions", "anatomically balanced measurements",
    "ideal body measurements", "perfect corporal dimensions", "harmonious anatomical metrics", "balanced physical metrics", "ideal structural metrics",
    "anatomically accurate dimensions", "perfect body dimensions", "harmonious physical measurements", "balanced anatomical dimensions", "ideal corporal measurements",
    "anatomically precise metrics", "perfect physical metrics", "harmonious body dimensions", "balanced structural measurements", "ideal physiological dimensions",
    "anatomically harmonious metrics", "perfect bodily measurements", "harmonious corporal metrics", "balanced physical dimensions", "ideal anatomical metrics",
    "perfect structural measurements", "harmonious physiological dimensions", "balanced bodily metrics", "anatomically proportionate measurements", "ideal physical metrics",
    "perfect anatomical dimensions", "harmonious structural metrics", "balanced corporal dimensions", "anatomically harmonized measurements", "ideal bodily dimensions",
    "perfect physiological metrics", "harmonious anatomical dimensions", "balanced physical measurements", "anatomically ideal metrics", "perfect corporal metrics",
    "harmonious bodily dimensions", "balanced anatomical measurements", "ideal structural dimensions", "perfect physical dimensions", "harmonious physiological metrics",
    "balanced bodily dimensions", "anatomically perfect metrics", "ideal corporal metrics", "perfect anatomical measurements", "harmonious physical dimensions",
    "balanced physiological metrics", "anatomically balanced dimensions", "ideal bodily metrics", "perfect structural dimensions", "harmonious corporal dimensions",
    "anatomically proportionate dimensions", "balanced anatomical metrics", "ideal physiological measurements", "perfect bodily dimensions", "harmonious structural measurements",
    "anatomically harmonious dimensions", "balanced corporal metrics", "ideal physical dimensions", "perfect physiological dimensions", "harmonious anatomical measurements",
    "balanced structural dimensions", "anatomically precise dimensions", "ideal bodily measurements", "perfect corporal dimensions", "harmonious physiological measurements",
    "balanced physical dimensions", "anatomically accurate metrics", "ideal structural measurements", "perfect anatomical metrics", "harmonious bodily measurements",
    "balanced physiological dimensions", "anatomically perfect measurements", "ideal physical measurements", "perfect bodily metrics", "harmonious corporal measurements",
    "balanced anatomical dimensions", "anatomically harmonized dimensions", "ideal structural metrics", "perfect physiological measurements", "harmonious physical metrics",
    "balanced bodily measurements", "anatomically ideal dimensions", "ideal corporal dimensions", "perfect physical dimensions", "harmonious structural dimensions",
    "balanced physiological measurements", "anatomically balanced metrics", "ideal anatomical dimensions", "perfect corporal measurements", "harmonious bodily metrics",
    "balanced physical measurements", "anatomically proportionate metrics", "ideal physiological metrics", "perfect structural metrics", "harmonious anatomical dimensions",
    "balanced corporal measurements", "anatomically harmonious metrics", "ideal bodily dimensions", "perfect physical measurements", "harmonious physiological dimensions",
    "balanced structural metrics", "anatomically precise measurements", "ideal corporal metrics", "perfect anatomical dimensions", "harmonious physical measurements",
    "balanced physiological metrics", "anatomically accurate dimensions", "ideal structural dimensions", "perfect bodily measurements", "harmonious corporal dimensions",
    "balanced anatomical metrics", "anatomically perfect dimensions", "ideal physical metrics", "perfect physiological dimensions", "harmonious bodily dimensions",
    "balanced corporal metrics", "anatomically harmonized metrics", "ideal anatomical measurements", "perfect structural dimensions", "harmonious physiological metrics",
    "balanced bodily dimensions", "anatomically ideal metrics", "ideal physical dimensions", "perfect corporal metrics", "harmonious anatomical dimensions",
    "balanced physiological dimensions", "anatomically balanced measurements", "ideal bodily metrics", "perfect anatomical measurements", "harmonious structural dimensions",
    "balanced corporal dimensions", "anatomically proportionate dimensions", "ideal structural metrics", "perfect physical dimensions", "harmonious bodily measurements",
    "balanced anatomical dimensions", "anatomically harmonious measurements", "ideal physiological dimensions", "perfect bodily dimensions", "harmonious corporal metrics",
    "ideal body structure", "flawless anatomical balance", "perfectly developed physique", "harmonious body ratios", "ideal physical structure",
    "masterful anatomical precision", "anatomically superior", "extraordinary physical proportions", "flawless body architecture", "remarkable physical harmony",
    "immaculate anatomical design", "exceptionally proportioned figure", "perfect structural development", "superb anatomical harmony", "ideal physical blueprint",
    "immaculately balanced physique", "superior body framework", "exquisite anatomical ratios", "flawlessly proportional", "sublime physical symmetry",
    "impeccable body mechanics", "artfully structured physique", "unerring anatomical balance", "perfect physical congruence", "masterful bodily harmonization",
    "exceptional anatomical integration", "supremely balanced structure", "flawless biomechanical design", "ideal structural composition", "perfect kinetic alignment",
    "anatomically optimized proportions", "superior physical architecture", "exquisite structural symmetry", "perfectly calibrated dimensions", "masterful physiological design",
    "immaculate bodily ratios", "exceptional structural harmony", "flawless corporeal geometry", "ideal anatomical organization", "perfect morphological balance",
    "sublime structural integrity", "artfully proportioned anatomy", "superior physiological harmony", "perfect kinesthetic balance", "exceptional anatomical coordination",
    "masterfully proportioned physique", "flawless physical calibration", "ideal bodily composition", "perfect structural synchronization", "superb anatomical calibration",
    "exquisite physical integration", "perfectly harmonized structure", "immaculate bodily organization", "superior anatomical geometry", "flawless physical orchestration",
    
    # Muscle detail (500)
    "defined muscle tone", "perfectly toned muscles", "subtle muscle definition", "well-defined musculature", "natural muscle tone",
    "balanced muscle development", "elegant muscle definition", "harmonious muscular structure", "perfect muscle symmetry", "refined muscular detail",
    "gentle muscle contours", "ideal muscle tone", "delicate muscle definition", "balanced muscle tone", "perfect muscular development",
    "natural muscle definition", "elegant muscular tone", "harmonious muscle detail", "refined muscle development", "subtle muscular contours",
    "well-proportioned muscles", "perfect muscle detail", "graceful muscular definition", "balanced muscle structure", "ideal muscular contours",
    "natural muscle symmetry", "elegant muscle development", "harmonious muscular tone", "refined muscle symmetry", "subtle muscle structure",
    "well-defined muscle detail", "perfect muscular balance", "graceful muscle contours", "balanced muscular definition", "ideal muscle structure",
    "natural muscular detail", "elegant muscle contours", "harmonious muscle development", "refined muscular structure", "subtle muscle tone",
    "well-proportioned muscular tone", "perfect muscle structure", "graceful muscular contours", "balanced muscle detail", "ideal muscular development",
    "natural muscle contours", "elegant muscular detail", "harmonious muscle symmetry", "refined muscular tone", "subtle muscle development",
    "lean muscle definition", "distinct muscle separation", "visible muscle striations", "anatomically correct muscles", "perfect muscle insertions",
    "well-developed muscle bellies", "detailed muscle separation", "clear muscular details", "pronounced muscle tone", "sculpted muscle appearance",
    "sharply defined musculature", "perfect muscle maturity", "detailed muscle insertions", "visible muscle heads", "perfectly shaped muscle peaks",
    "clean muscle definition", "clear intermuscular lines", "deep muscle separation", "perfect muscle quality", "symmetrical muscle development",
    "well-placed muscle insertions", "detailed muscle texture", "prominent muscle vascularity", "evenly developed muscles", "balanced muscle density",
    "crisp muscular detail", "anatomically perfect muscle structure", "clearly visible muscle fibers", "perfect muscle hardness", "detailed muscular relief",
    "prominent muscle contours", "perfect muscle proportions", "full muscle bellies", "natural muscle fullness", "properly developed muscles",
    "aesthetically pleasing muscle flow", "optimal muscle development", "flawless muscle symmetry", "proportionate muscle groups", "beautiful muscle shapes",
    "textured muscle surfaces", "perfect muscle conditioning", "detailed muscle valleys", "perfect muscle fiber alignment", "enhanced muscle detail",
    "bold muscle presentation", "clear muscular grooves", "perfect muscle refinement", "finely detailed muscle lines", "outstanding muscle clarity",
    "powerful muscle appearance", "perfectly composed muscles", "comprehensive muscle development", "clear muscle structure", "detailed muscle architecture",
    "precise muscle detail", "phenomenal muscle definition", "exceptional muscle separation", "impressive muscle quality", "sublime muscle refinement",
    "extraordinary muscle density", "superb muscle detail", "outstanding muscular development", "remarkable muscle definition", "exquisite muscular refinement",
    "superior muscle quality", "phenomenal muscle separation", "extraordinary muscular clarity", "exceptional muscle refinement", "superb muscular balance",
    "immaculate muscle definition", "supreme muscular detail", "perfect muscle conditioning", "masterful muscle separation", "flawless muscular development",
    "superior muscle refinement", "extraordinary muscle structure", "exceptional muscular symmetry", "superb muscle proportions", "outstanding muscle balance",
    "remarkable muscular texture", "exquisite muscle separation", "immaculate muscular harmony", "supreme muscle definition", "flawless muscle detail",
    "masterful muscular development", "superior muscle symmetry", "extraordinary muscular refinement", "exceptional muscle details", "outstanding muscular quality",
    "remarkable muscle precision", "exquisite muscular definition", "immaculate muscle structure", "supreme muscular balance", "flawless muscle harmony",
    "perfectly detailed muscle separation", "exceptionally defined muscularity", "remarkably balanced muscle development", "impressively detailed muscle striations", "perfectly clear intermuscular lines",
    "extraordinarily visible muscle insertions", "remarkably detailed muscle architecture", "exceptionally proportioned muscle groups", "impressively balanced muscle symmetry", "perfectly developed muscle maturity",
    "extraordinarily refined muscle definition", "remarkably detailed muscle texture", "exceptionally visible muscle fibers", "impressively developed muscle bellies", "perfectly balanced muscle density",
    "extraordinarily clean muscle separation", "remarkably proportioned muscle structure", "exceptionally detailed muscle heads", "impressively symmetrical muscle development", "perfectly visible muscle valleys",
    "extraordinarily harmonious muscle flow", "remarkably refined muscle contours", "exceptionally balanced muscle shapes", "impressively detailed muscle grooves", "perfectly clear muscle relief",
    "well-defined abdominal muscles", "clearly visible six-pack", "perfect abdominal symmetry", "deep abdominal muscle separation", "well-developed intercostals",
    "perfectly visible serratus muscles", "detailed oblique definition", "symmetrical rectus abdominis", "perfect abdominal tapering", "clearly defined lower abs",
    "well-developed upper abdominals", "perfect abdominal muscle rows", "detailed transverse abdominis", "harmonious abdominal development", "perfect abdominal conditioning",
    "clearly separated abdominal segments", "well-defined abdominal contours", "perfect abdominal muscle depth", "detailed abdominal ridges", "symmetrical abdominal structure",
    "well-developed chest muscles", "perfect pectoral symmetry", "detailed pectoral striations", "well-defined pectoral contours", "perfect chest muscle separation",
    "clearly visible pectoral fibers", "well-developed upper chest", "perfect lower chest development", "detailed chest muscle insertions", "symmetrical pectoral structure",
    "well-balanced pectoral development", "perfect chest muscle density", "detailed pectoral shape", "harmonious chest development", "perfect chest muscle conditioning",
    "well-defined deltoid muscles", "perfect shoulder cap development", "detailed shoulder striations", "well-separated deltoid heads", "perfect shoulder roundness",
    "clearly defined anterior deltoids", "well-developed lateral delts", "perfect posterior deltoid detail", "detailed shoulder muscle insertions", "symmetrical deltoid development",
    "well-balanced shoulder muscles", "perfect deltoid density", "detailed shoulder muscle separation", "harmonious deltoid development", "perfect shoulder conditioning",
    "well-defined trapezius muscles", "perfect upper back development", "detailed back muscle striations", "well-separated back muscle groups", "perfect lat spread",
    "clearly visible latissimus dorsi", "well-developed rhomboids", "perfect erector spinae detail", "detailed back muscle insertions", "symmetrical back development",
    "well-balanced back muscles", "perfect back muscle density", "detailed upper back definition", "harmonious back muscle development", "perfect back conditioning",
    "well-defined arm muscles", "perfect bicep peaks", "detailed arm striations", "well-separated tricep heads", "perfect arm muscle insertions",
    "clearly visible bicep fibers", "well-developed brachialis", "perfect forearm development", "detailed arm vascularity", "symmetrical arm development",
    "well-balanced arm muscles", "perfect bicep and tricep proportion", "detailed forearm muscle separation", "harmonious arm development", "perfect arm conditioning",
    "well-defined leg muscles", "perfect quad development", "detailed leg striations", "well-separated quadriceps", "perfect hamstring development",
    "clearly visible leg muscle fibers", "well-developed vastus medialis", "perfect calf muscle detail", "detailed leg muscle insertions", "symmetrical leg development",
    "well-balanced leg muscles", "perfect thigh muscle density", "detailed calf muscle separation", "harmonious leg development", "perfect leg conditioning",
    "visible muscle separation between glutes", "perfect gluteal development", "detailed glute muscle shape", "well-rounded buttocks muscles", "perfect lower body proportions",
    "clearly defined gluteal-hamstring tie-in", "well-developed gluteus maximus", "perfect gluteal muscle contours", "detailed gluteal striations", "symmetrical gluteal development",
    "well-balanced gluteal muscles", "perfect glute muscle density", "detailed gluteal definition", "harmonious lower body development", "perfect gluteal conditioning",
    
    # Body shape (500)
    "perfect hourglass figure", "ideal body contours", "harmonious physical proportions", "flawless body shape", "perfect figure symmetry",
    "beautiful body silhouette", "ideal body proportions", "elegant physical form", "perfect body lines", "harmonious figure contours",
    "flawless physical silhouette", "perfect body curves", "ideal figure shape", "elegant body contours", "harmonious physical lines",
    "flawless body proportions", "perfect physical silhouette", "ideal body form", "elegant figure proportions", "harmonious body curves",
    "flawless figure lines", "perfect body symmetry", "ideal physical contours", "elegant body curves", "harmonious figure symmetry",
    "flawless body form", "perfect figure contours", "ideal physical silhouette", "elegant body proportions", "harmonious physical curves",
    "flawless figure contours", "perfect body lines", "ideal figure symmetry", "elegant physical proportions", "harmonious body form",
    "flawless physical contours", "perfect figure lines", "ideal body symmetry", "elegant figure lines", "harmonious physical form",
    "flawless body curves", "perfect physical proportions", "ideal figure contours", "elegant body form", "harmonious figure lines",
    "flawless physical form", "perfect figure proportions", "ideal body lines", "elegant physical contours", "harmonious body symmetry",
    "sublime body contours", "exquisite physical proportions", "magnificent body shape", "divine figure symmetry", "extraordinary silhouette",
    "impeccable body proportions", "splendid physical form", "immaculate body lines", "exceptional figure contours", "majestic physical silhouette",
    "flawless body curves", "superb figure shape", "sublime body contours", "exceptional physical lines", "immaculate body proportions",
    "splendid physical silhouette", "exquisite body form", "divine figure proportions", "extraordinary body curves", "majestic figure lines",
    "impeccable body symmetry", "magnificent physical contours", "sublime body curves", "exceptional figure symmetry", "immaculate body form",
    "splendid figure contours", "exquisite physical silhouette", "divine body proportions", "extraordinary figure contours", "majestic physical curves",
    "impeccable figure contours", "magnificent body lines", "sublime figure symmetry", "exceptional physical proportions", "immaculate body form",
    "splendid physical contours", "exquisite figure lines", "divine body symmetry", "extraordinary figure lines", "majestic physical form",
    "impeccable body curves", "magnificent physical proportions", "sublime figure contours", "exceptional body form", "immaculate figure lines",
    "splendid physical form", "exquisite figure proportions", "divine body lines", "extraordinary physical contours", "majestic body symmetry",
    "stunning body contours", "remarkable physical proportions", "impressive body shape", "outstanding figure symmetry", "striking silhouette",
    "lovely body proportions", "beautiful physical form", "captivating body lines", "attractive figure contours", "eye-catching physical silhouette",
    "gorgeous body curves", "stunning figure shape", "remarkable body contours", "impressive physical lines", "outstanding body proportions",
    "striking physical silhouette", "lovely body form", "beautiful figure proportions", "captivating body curves", "attractive figure lines",
    "eye-catching body symmetry", "gorgeous physical contours", "stunning body curves", "remarkable figure symmetry", "impressive body form",
    "outstanding figure contours", "striking physical silhouette", "lovely body proportions", "beautiful figure contours", "captivating physical curves",
    "attractive figure contours", "eye-catching body lines", "gorgeous figure symmetry", "stunning physical proportions", "remarkable body form",
    "impressive physical contours", "outstanding figure lines", "striking body symmetry", "lovely figure lines", "beautiful physical form",
    "captivating body curves", "attractive physical proportions", "eye-catching figure contours", "gorgeous body form", "stunning figure lines",
    "remarkable body symmetry", "impressive figure lines", "outstanding physical form", "striking figure proportions", "lovely body lines",
    "slim yet shapely figure", "beautifully proportioned physique", "naturally curved silhouette", "perfectly balanced body shape", "elegantly formed figure",
    "gracefully contoured body", "harmoniously shaped physique", "ideally proportioned silhouette", "perfectly formed body lines", "elegantly curved figure",
    "naturally shaped physical form", "beautifully contoured body proportions", "perfectly balanced figure shape", "elegantly proportioned physical contours", "gracefully shaped body lines",
    "harmoniously curved physical silhouette", "ideally formed body proportions", "perfectly contoured figure lines", "elegantly shaped physique", "naturally proportioned body curves",
    "beautifully formed figure contours", "perfectly shaped physical form", "elegantly balanced body symmetry", "gracefully proportioned figure lines", "harmoniously contoured physical shape",
    "ideally curved body proportions", "perfectly shaped figure symmetry", "elegantly formed physical contours", "naturally balanced body lines", "beautifully curved figure shape",
    "perfectly contoured physique", "elegantly shaped body proportions", "gracefully formed figure contours", "harmoniously balanced physical lines", "ideally shaped body curves",
    "perfectly proportioned figure form", "elegantly contoured physical shape", "naturally shaped body symmetry", "beautifully balanced figure contours", "perfectly curved physical lines",
    "elegantly shaped body form", "gracefully contoured figure proportions", "harmoniously shaped physical symmetry", "ideally balanced body contours", "perfectly formed figure curves",
    "naturally contoured physical proportions", "beautifully shaped body symmetry", "perfectly balanced figure lines", "elegantly curved physical form", "gracefully shaped body contours",
    "well-proportioned athletic build", "perfectly balanced muscular physique", "harmoniously developed fitness figure", "ideally shaped athletic silhouette", "elegantly toned physical form",
    "gracefully muscled body contours", "beautifully defined athletic proportions", "perfectly developed fitness shape", "naturally toned muscular lines", "elegantly balanced athletic figure",
    "harmoniously contoured fitness physique", "ideally muscled body proportions", "perfectly defined athletic contours", "naturally shaped fitness form", "elegantly developed muscular symmetry",
    "gracefully balanced athletic lines", "beautifully contoured fitness shape", "perfectly toned muscular proportions", "harmoniously shaped athletic form", "ideally defined fitness contours",
    "elegantly muscled body symmetry", "naturally balanced athletic proportions", "perfectly contoured fitness lines", "gracefully shaped muscular form", "beautifully defined athletic symmetry",
    "harmoniously toned body contours", "ideally balanced fitness shape", "perfectly muscled athletic lines", "elegantly contoured fitness proportions", "naturally defined muscular shape",
    "gracefully balanced athletic contours", "beautifully shaped fitness symmetry", "perfectly toned body lines", "harmoniously contoured athletic form", "ideally muscled fitness proportions",
    "elegantly defined physical contours", "naturally shaped athletic symmetry", "perfectly balanced fitness lines", "gracefully toned muscular form", "beautifully contoured athletic shape",
    "harmoniously defined body proportions", "ideally balanced muscular contours", "perfectly shaped fitness symmetry", "elegantly muscled athletic lines", "naturally contoured fitness shape",
    "gracefully defined physical proportions", "beautifully balanced muscular form", "perfectly contoured athletic symmetry", "harmoniously shaped fitness lines", "ideally toned body shape",
    "voluptuous feminine curves", "softly rounded womanly figure", "perfectly curved female form", "beautifully proportioned feminine silhouette", "elegantly shaped womanly contours",
    "gracefully curved female proportions", "harmoniously rounded feminine shape", "ideally formed womanly lines", "perfectly contoured female figure", "naturally shaped feminine physique",
    "softly curved womanly proportions", "beautifully rounded female contours", "perfectly shaped feminine lines", "elegantly contoured womanly form", "gracefully shaped female symmetry",
    "harmoniously curved feminine proportions", "ideally rounded womanly contours", "perfectly formed female shape", "naturally contoured feminine lines", "beautifully shaped womanly symmetry",
    "softly formed female proportions", "perfectly curved feminine contours", "elegantly rounded womanly shape", "gracefully contoured female form", "harmoniously shaped feminine symmetry",
    "ideally curved womanly lines", "perfectly rounded female proportions", "naturally shaped feminine contours", "beautifully contoured womanly lines", "softly shaped female form",
    "elegantly curved feminine symmetry", "gracefully rounded womanly proportions", "harmoniously contoured female shape", "ideally shaped feminine lines", "perfectly formed womanly contours",
    "naturally curved female symmetry", "beautifully shaped feminine form", "softly contoured womanly lines", "elegantly formed female proportions", "gracefully shaped feminine contours",
    "harmoniously rounded womanly form", "ideally contoured female lines", "perfectly shaped feminine symmetry", "naturally formed womanly proportions", "beautifully curved female contours",
    "softly shaped feminine lines", "elegantly contoured womanly symmetry", "gracefully formed female shape", "harmoniously shaped womanly lines", "ideally rounded feminine form",
    "broad-shouldered masculine build", "powerfully structured male physique", "perfectly proportioned masculine form", "strongly built male silhouette", "robustly shaped masculine contours",
    "solidly structured male proportions", "powerfully formed masculine shape", "perfectly built male lines", "strongly contoured masculine figure", "robustly proportioned male physique",
    "solidly shaped masculine contours", "powerfully structured male form", "perfectly contoured masculine lines", "strongly shaped male symmetry", "robustly formed masculine proportions",
    "solidly built male contours", "powerfully shaped masculine symmetry", "perfectly structured male form", "strongly contoured masculine lines", "robustly shaped male proportions",
    "solidly formed masculine figure", "powerfully contoured male shape", "perfectly shaped masculine symmetry", "strongly structured male contours", "robustly built masculine lines",
    "solidly contoured male form", "powerfully shaped masculine proportions", "perfectly formed male contours", "strongly shaped masculine lines", "robustly structured male symmetry",
    "solidly proportioned masculine shape", "powerfully built male contours", "perfectly contoured masculine form", "strongly formed male lines", "robustly shaped masculine symmetry",
    "solidly structured male shape", "powerfully contoured masculine lines", "perfectly shaped male proportions", "strongly built masculine contours", "robustly formed male symmetry",
    "solidly shaped masculine lines", "powerfully formed male proportions", "perfectly structured masculine contours", "strongly contoured male shape", "robustly built masculine form",
    "solidly built masculine lines", "powerfully shaped male symmetry", "perfectly formed masculine shape", "strongly structured male proportions", "robustly contoured masculine lines",
    
    # Specific body parts (500)
    "elegant neck line", "perfectly shaped neck", "graceful neck contour", "harmonious neck structure", "ideal neck length",
    "elegant collarbone structure", "perfectly defined clavicles", "graceful collarbone contour", "harmonious clavicle structure", "ideal collarbone prominence",
    "elegant shoulder line", "perfectly shaped shoulders", "graceful shoulder contour", "harmonious shoulder structure", "ideal shoulder breadth",
    "elegant upper arm shape", "perfectly toned biceps", "graceful arm contour", "harmonious arm structure", "ideal arm definition",
    "elegant forearm shape", "perfectly toned forearms", "graceful forearm contour", "harmonious forearm structure", "ideal forearm definition",
    "elegant wrist structure", "perfectly shaped wrists", "graceful wrist contour", "harmonious wrist bones", "ideal wrist proportion",
    "elegant hand structure", "perfectly shaped hands", "graceful hand contour", "harmonious hand bones", "ideal hand proportion",
    "elegant finger structure", "perfectly shaped fingers", "graceful finger contour", "harmonious finger bones", "ideal finger proportion",
    "elegant chest shape", "perfectly formed chest", "graceful chest contour", "harmonious chest structure", "ideal chest proportion",
    "elegant breast shape", "perfectly formed breasts", "graceful breast contour", "harmonious breast structure", "ideal breast proportion",
    "elegant waistline", "perfectly shaped waist", "graceful waist contour", "harmonious waist structure", "ideal waist proportion",
    "elegant abdominal structure", "perfectly toned abdomen", "graceful abdominal contour", "harmonious abdominal definition", "ideal abdominal shape",
    "elegant hip structure", "perfectly shaped hips", "graceful hip contour", "harmonious hip structure", "ideal hip width",
    "elegant buttock shape", "perfectly formed buttocks", "graceful posterior contour", "harmonious gluteal structure", "ideal buttock proportion",
    "elegant thigh shape", "perfectly formed thighs", "graceful thigh contour", "harmonious thigh structure", "ideal thigh proportion",
    "elegant knee structure", "perfectly shaped knees", "graceful knee contour", "harmonious knee bones", "ideal knee proportion",
    "elegant calf shape", "perfectly formed calves", "graceful calf contour", "harmonious calf structure", "ideal calf proportion",
    "elegant ankle structure", "perfectly shaped ankles", "graceful ankle contour", "harmonious ankle bones", "ideal ankle proportion",
    "elegant foot structure", "perfectly shaped feet", "graceful foot contour", "harmonious foot bones", "ideal foot proportion",
    "elegant toe structure", "perfectly shaped toes", "graceful toe contour", "harmonious toe structure", "ideal toe proportion",
    "long elegant neck", "perfectly poised head", "graceful neckline", "harmonious neck-shoulder junction", "ideal neck musculature",
    "prominent shapely collarbones", "perfectly defined clavicle line", "graceful collarbone protrusion", "harmonious collarbone length", "ideal clavicle visibility",
    "broad structured shoulders", "perfectly aligned shoulder caps", "graceful deltoid curve", "harmonious shoulder width", "ideal shoulder muscle development",
    "perfectly formed biceps", "well-defined upper arm muscles", "graceful bicep curve", "harmonious arm taper", "ideal upper arm shape",
    "strong defined forearms", "perfectly developed forearm muscles", "graceful wrist taper", "harmonious forearm definition", "ideal forearm musculature",
    "delicate wrist structure", "perfectly proportioned wrist bones", "graceful wrist narrowing", "harmonious wrist definition", "ideal wrist circumference",
    "elegant hand shape", "perfectly proportioned palms", "graceful hand structure", "harmonious hand size", "ideal hand contours",
    "long tapered fingers", "perfectly proportioned digit length", "graceful finger structure", "harmonious fingernail shape", "ideal finger spacing",
    "strong defined chest", "perfectly developed pectoral muscles", "graceful chest contour", "harmonious chest width", "ideal chest muscle separation",
    "beautifully shaped breasts", "perfectly proportioned bust", "graceful breast curve", "harmonious breast placement", "ideal breast contour",
    "narrow cinched waist", "perfectly tapered midsection", "graceful waist indentation", "harmonious waist-to-hip ratio", "ideal waist definition",
    "flat toned abdomen", "perfectly defined abdominal muscles", "graceful abdominal taper", "harmonious abdominal separation", "ideal abdominal leanness",
    "wide curved hips", "perfectly proportioned pelvic structure", "graceful hip flare", "harmonious hip width", "ideal hip-to-waist ratio",
    "round firm buttocks", "perfectly shaped gluteal muscles", "graceful buttock curve", "harmonious posterior projection", "ideal gluteal separation",
    "strong shapely thighs", "perfectly toned quadriceps", "graceful thigh contour", "harmonious thigh taper", "ideal thigh musculature",
    "well-structured knees", "perfectly aligned knee caps", "graceful knee contour", "harmonious knee proportion", "ideal knee definition",
    "defined muscular calves", "perfectly shaped lower leg muscles", "graceful calf curve", "harmonious calf development", "ideal calf muscle insertion",
    "slim tapered ankles", "perfectly proportioned ankle bones", "graceful ankle narrowing", "harmonious ankle structure", "ideal ankle circumference",
    "well-arched feet",
        ],
        "face_detail": [
         "perfect face", "proportional facial features", "ideal facial structure", "facial symmetry",
        "prominent cheekbones", "defined jawline", "proportional chin", "clear facial contours",
        "smooth facial skin", "flawless complexion", "natural skin texture", "fine pores",
        "natural blush", "even skin tone", "perfect skin tone gradation", "balanced skin undertone",
        "thick eyebrows", "well-groomed eyebrows", "perfect eyebrow arch", "proportional eyebrow shape",
        "sparkling eyes", "expressive eyes", "intense gaze", "deep look",
        "curled eyelashes", "long eyelashes", "thick eyelashes", "layered eyelashes",
        "defined eyelids", "clear eye fold", "uplifted eye corners", "harmonious eye shape",
        "detailed iris", "brilliant eye color", "clear pupil", "light reflection in eyes",
        "proportional nose", "ideal nose shape", "straight nose bridge", "defined nose tip",
        "full lips", "sensual lips", "clear lip contour", "symmetrical lip shape",
        "charming smile", "natural smile", "white teeth", "straight teeth",
        "lively facial expression", "radiant emotion", "expressive facial features", "dynamic countenance",
        "smooth forehead", "proportional forehead", "minimal forehead lines", "perfect brow-forehead junction",
        "proportional ears", "balanced ear shape", "defined ear lobes", "ears aligned with face",
        "slender neck", "elegant neckline", "clear neck-chin junction", "smooth neck contour",
        "strategic beauty mark", "attractive mole", "unique facial marker", "characteristic facial detail"  
        ],
        "nsfw": [
    "alluring pose", "enticing posture", "seductive stance", "tempting position", "provocative pose",
    "suggestive posture", "teasing stance", "sensual positioning", "flirtatious pose", "inviting posture",
    "beguiling stance", "sultry pose", "tantalizing position", "captivating posture", "enchanting stance",
    "enthralling pose", "ravishing posture", "bewitching stance", "mesmerizing position", "spellbinding pose",
    "arresting posture", "attractive stance", "charming position", "appealing pose", "enticing posture",
    "magnetic stance", "alluring position", "engaging pose", "fascinating posture", "beguiling stance",
    "captivating position", "irresistible pose", "tempting posture", "seductive positioning", "provocative stance",
    "suggestive position", "teasing pose", "sensual posture", "flirtatious stance", "inviting position",
    "coy pose", "demure posture", "bashful stance", "shy position", "modest pose",
    "playful posture", "mischievous stance", "roguish position", "impish pose", "naughty posture",
    "frisky stance", "sportive position", "coquettish pose", "flirty posture", "kittenish stance",
    "elegant position", "graceful pose", "sophisticated posture", "refined stance", "polished position",
    "poised pose", "dignified posture", "stately stance", "distinguished position", "noble pose",
    "regal posture", "majestic stance", "grand position", "impressive pose", "striking posture",
    "dramatic stance", "theatrical position", "expressive pose", "emotive posture", "passionate stance",
    "ardent position", "fervent pose", "intense posture", "zealous stance", "enthusiastic position",
    "eager pose", "avid posture", "keen stance", "animated position", "lively pose",
    "energetic posture", "vibrant stance", "dynamic position", "active pose", "spirited posture",
    "vigorous stance", "robust position", "hardy pose", "sturdy posture", "strong stance",
    "powerful position", "mighty pose", "forceful posture", "potent stance", "dominant position",
    "commanding pose", "authoritative posture", "imposing stance", "formidable position", "daunting pose",
    "intimidating posture", "overwhelming stance", "overpowering position", "staggering pose", "astounding posture",
    "astonishing stance", "surprising position", "startling pose", "unexpected posture", "stunning stance",
    "breathtaking position", "awe-inspiring pose", "wonderful posture", "marvelous stance", "magnificent position",
    "splendid pose", "glorious posture", "superb stance", "excellent position", "exceptional pose",
    "outstanding posture", "extraordinary stance", "remarkable position", "notable pose", "significant posture",
    "important stance", "consequential position", "momentous pose", "weighty posture", "substantial stance",
    "considerable position", "appreciable pose", "marked posture", "pronounced stance", "conspicuous position",
    "apparent pose", "evident posture", "manifest stance", "patent position", "clear pose",
    "obvious posture", "plain stance", "explicit position", "unmistakable pose", "unequivocal posture",
    "unambiguous stance", "indisputable position", "undeniable pose", "incontestable posture", "irrefutable stance",
    "indubitable position", "incontrovertible pose", "undoubted posture", "unquestionable stance", "incontestable position",
    "seductively arched back", "suggestively parted lips", "temptingly tilted hips", "provocatively raised chin", "enticingly crossed legs",
    "teasingly exposed neckline", "alluringly positioned arms", "sensually curved posture", "flirtatiously angled head", "invitingly stretched body",
    "suggestively bent knee", "seductively turned shoulders", "provocatively positioned hands", "temptingly angled hips", "enticingly relaxed posture",
    "teasingly sideways glance", "alluringly casual stance", "sensually reclined position", "flirtatiously leaning forward", "invitingly open stance",
    "provocatively lounging", "seductively poised", "temptingly balanced", "enticingly supported", "suggestively inclined",
    "teasingly perched", "alluringly suspended", "sensually reclining", "flirtatiously sprawled", "invitingly nestled",
    "suggestively draped", "seductively propped", "provocatively positioned", "temptingly aligned", "enticingly situated",
    "teasingly arranged", "alluringly displayed", "sensually exhibited", "flirtatiously presented", "invitingly disposed",
    "suggestively oriented", "seductively directed", "provocatively turned", "temptingly pivoted", "enticingly rotated",
    "teasingly twisted", "alluringly contorted", "sensually flexed", "flirtatiously bent", "invitingly curved",
    "suggestively arched", "seductively angled", "provocatively tilted", "temptingly inclined", "enticingly slanted",
    "teasingly leaning", "alluringly tipped", "sensually canted", "flirtatiously sloped", "invitingly diagonal",
    "suggestively askew", "seductively oblique", "provocatively aslant", "temptingly athwart", "enticingly biased",
    "teasingly deflected", "alluringly diverted", "sensually divergent", "flirtatiously deviant", "invitingly wayward",
    "suggestively irregular", "seductively atypical", "provocatively unconventional", "temptingly unorthodox", "enticingly eccentric",
    "teasingly peculiar", "alluringly odd", "sensually curious", "flirtatiously strange", "invitingly weird",
    "suggestively bizarre", "seductively outlandish", "provocatively extraordinary", "temptingly remarkable", "enticingly noteworthy",
    "teasingly significant", "alluringly considerable", "sensually substantial", "flirtatiously important", "invitingly consequential",
    "suggestively momentous", "seductively critical", "provocatively crucial", "temptingly essential", "enticingly vital",
    "teasingly imperative", "alluringly urgent", "sensually pressing", "flirtatiously immediate", "invitingly instant",
    "suggestively prompt", "seductively expeditious", "provocatively speedy", "temptingly swift", "enticingly rapid",
    "teasingly fleet", "alluringly quick", "sensually hasty", "flirtatiously hurried", "invitingly fast",
    "suggestively brisk", "seductively nimble", "provocatively agile", "temptingly lithe", "enticingly spry",
    "teasingly lissome", "alluringly lithesome", "sensually supple", "flirtatiously flexible", "invitingly limber",
    "sultrily curved spine", "evocatively stretched neck", "tantalizingly positioned arms", "enticingly angled legs", "suggestively placed hands",
    "seductively poised shoulders", "provocatively turned hips", "alluringly tilted head", "temptingly exposed neckline", "invitingly arched back",
    "sensually crossed ankles", "flirtatiously extended leg", "teasingly bent elbow", "suggestively positioned fingers", "enticingly relaxed wrists",
    "provocatively curved waist", "seductively aligned posture", "alluringly balanced stance", "temptingly casual pose", "invitingly reclined position",
    "sensually poised figure", "flirtatiously relaxed demeanor", "teasingly graceful posture", "suggestively elegant stance", "enticingly refined pose",
    "provocatively sophisticated position", "seductively styled posture", "alluringly fashionable stance", "temptingly trendy pose", "invitingly chic position",
    "sensually dapper posture", "flirtatiously smart stance", "teasingly dashing pose", "suggestively suave position", "enticingly urbane posture",
    "provocatively polished stance", "seductively refined pose", "alluringly cultured position", "temptingly civilized posture", "invitingly genteel stance",
    "sensually gracious pose", "flirtatiously charming position", "teasingly engaging posture", "suggestively pleasing stance", "enticingly winning pose",
    "provocatively likable position", "seductively appealing posture", "alluringly attractive stance", "temptingly engaging pose", "invitingly pleasing position",
    "sensually agreeable posture", "flirtatiously congenial stance", "teasingly genial pose", "suggestively cordial position", "enticingly affable posture",
    "provocatively amiable stance", "seductively pleasant pose", "alluringly delightful position", "temptingly enjoyable posture", "invitingly gratifying stance",
    "sensually satisfying pose", "flirtatiously fulfilling position", "teasingly rewarding posture", "suggestively enriching stance", "enticingly meaningful pose",
    "provocatively significant position", "seductively important posture", "alluringly consequential stance", "temptingly momentous pose", "invitingly crucial position",
    "sensually vital posture", "flirtatiously essential stance", "teasingly indispensable pose", "suggestively necessary position", "enticingly requisite posture",
    "provocatively imperative stance", "seductively urgent pose", "alluringly pressing position", "temptingly immediate posture", "invitingly instant stance",
    "sensually immediate pose", "flirtatiously prompt position", "teasingly ready posture", "suggestively prepared stance", "enticingly primed pose",
    "provocatively poised position", "seductively set posture", "alluringly arranged stance", "temptingly positioned pose", "invitingly stationed position",
    "sensually placed posture", "flirtatiously situated stance", "teasingly located pose", "suggestively positioned position", "enticingly sited posture",

    # Revealing outfits (750)
    "revealing attire", "provocative clothing", "suggestive outfit", "seductive ensemble", "alluring garments",
    "tempting apparel", "enticing dress", "sensual garb", "flirtatious wardrobe", "tantalizing costume",
    "teasing outfit", "intimate apparel", "daring attire", "exposing clothing", "minimal ensemble",
    "scant garments", "barely-there apparel", "skimpy dress", "scanty attire", "risqué outfit",
    "bold clothing", "audacious ensemble", "immodest garments", "revealing apparel", "indiscreet dress",
    "adventurous attire", "brazen outfit", "daring clothing", "fearless ensemble", "intrepid garments",
    "valiant apparel", "courageous dress", "unabashed attire", "unashamed outfit", "uninhibited clothing",
    "unreserved ensemble", "restraint-free garments", "inhibition-free apparel", "constraint-free dress", "abandon-filled attire",
    "unfettered outfit", "unrestrained clothing", "liberated ensemble", "emancipated garments", "unconstrained apparel",
    "unbound dress", "unleashed attire", "uncontrolled outfit", "unrestricted clothing", "unconfined ensemble",
    "unbridled garments", "limitless apparel", "boundless dress", "illimitable attire", "unchecked outfit",
    "uninhibited clothing", "unrestricted ensemble", "unrestrained garments", "untrammeled apparel", "uncurbed dress",
    "untamed attire", "wild outfit", "feral clothing", "fierce ensemble", "ferocious garments",
    "savage apparel", "barbaric dress", "primitive attire", "primal outfit", "aboriginal clothing",
    "elemental ensemble", "fundamental garments", "natural apparel", "native dress", "indigenous attire",
    "autochthonous outfit", "aboriginal clothing", "primeval ensemble", "primordial garments", "prehistoric apparel",
    "antediluvian dress", "ancient attire", "antiquated outfit", "archaic clothing", "old-time ensemble",
    "traditional garments", "conventional apparel", "customary dress", "habitual attire", "accustomed outfit",
    "usual clothing", "ordinary ensemble", "regular garments", "normal apparel", "standard dress",
    "typical attire", "common outfit", "commonplace clothing", "everyday ensemble", "quotidian garments",
    "daily apparel", "diurnal dress", "day-to-day attire", "routine outfit", "habitual clothing",
    "customary ensemble", "accustomed garments", "usual apparel", "wonted dress", "familiar attire",
    "intimate outfit", "close clothing", "confidential ensemble", "detailed garments", "intricate apparel",
    "elaborate dress", "ornate attire", "decorated outfit", "adorned clothing", "embellished ensemble",
    "embroidered garments", "fancy apparel", "dressy dress", "formal attire", "ceremonial outfit",
    "ritual clothing", "solemn ensemble", "serious garments", "grave apparel", "important dress",
    "plunging neckline", "low-cut top", "deep v-neck", "revealing décolletage", "exposed cleavage",
    "backless design", "open-back style", "bare-backed cut", "revealing rear view", "spine-exposing silhouette",
    "high hemline", "short skirt", "mini-length", "above-knee cut", "thigh-revealing hem",
    "side slit", "high-cut slit", "leg-revealing opening", "thigh-high division", "provocative split",
    "sheer fabric", "see-through material", "transparent textile", "diaphanous cloth", "translucent covering",
    "cut-out details", "strategic openings", "revealing perforations", "skin-showing accents", "peekaboo elements",
    "bodycon fit", "form-fitting silhouette", "figure-hugging shape", "curve-accentuating cut", "body-emphasizing design",
    "crop top", "midriff-revealing shirt", "stomach-exposing blouse", "navel-baring top", "abbreviated upper garment",
    "off-shoulder style", "shoulder-baring design", "collarbone-revealing cut", "clavicle-exposing shape", "shoulder-showcasing silhouette",
    "halter neck", "neck-accentuating style", "throat-highlighting design", "bare-shouldered shape", "neck-showcasing cut",
    "strapless design", "shoulder-free style", "bandeau shape", "tube-top silhouette", "shoulderless cut",
    "corset-inspired", "waist-cinching design", "bustier-like style", "tight-laced silhouette", "bodice-accentuating shape",
    "lingerie-inspired", "underwear-as-outerwear", "bedroom-to-street style", "intimate-wear design", "boudoir-inspired silhouette",
    "mesh panel details", "netted fabric inserts", "fishnet elements", "open-weave sections", "grid-pattern reveals",
    "strappy design", "multiple-strap style", "cage-like details", "harness-inspired elements", "intertwined strap accents",
    "tight-fitting", "snug-cut", "closely-fitted", "narrow-shaped", "slim-designed",
    "second-skin appearance", "painted-on look", "shrink-wrapped aesthetic", "vacuum-sealed impression", "poured-in seeming",
    "clinging fabric", "adhesive material", "stick-to-skin textile", "body-gripping cloth", "form-following material",
    "glossy finish", "shiny texture", "lustrous surface", "gleaming appearance", "polished look",
    "reflective material", "mirror-like finish", "light-catching texture", "radiant surface", "luminous appearance",
    "wet-look fabric", "moisture-appearance textile", "dew-like finish", "water-resembling surface", "rain-kissed impression",
    "latex-inspired", "rubber-like material", "plastic-resembling texture", "synthetic-appearing surface", "polymer-esque look",
    "skin-toned", "flesh-colored", "body-hued", "epidermis-matched", "dermal-tinted",
    "nude shade", "birthday-suit colored", "bare-appearing", "unclothed-looking", "undressed-seeming",
    "illusion design", "trompe l'oeil effect", "deceiving appearance", "visual-trick styling", "optical-illusion pattern",
    "body-mapping print", "anatomy-highlighting pattern", "physique-emphasizing design", "figure-outlining motif", "form-tracing print",
    "suggestively unbuttoned", "provocatively unzipped", "teasingly unfastened", "seductively loosened", "tantalizingly undone",
    "strategically tattered", "deliberately torn", "purposefully ripped", "intentionally distressed", "designedly damaged",
    "provocatively asymmetrical", "teasingly uneven", "seductively lopsided", "tantalizingly unbalanced", "suggestively irregular",
    "daringly color-blocked", "boldly contrasted", "fearlessly juxtaposed", "audaciously combined", "provocatively paired",
    "skin-baring cutouts", "flesh-revealing openings", "body-exposing perforations", "figure-displaying holes", "form-showing apertures",
    "barely-buttoned blouse", "minimally fastened shirt", "scarcely closed top", "hardly secured bodice", "nominally fastened garment",
    "deliberately oversized", "intentionally too large", "purposefully voluminous", "designedly baggy", "calculatedly loose",
    "strategically undersized", "deliberately too small", "purposefully tight", "designedly constricting", "calculatedly snug",
    "suggestively layered", "provocatively tiered", "teasingly stratified", "seductively stacked", "tantalizingly arranged",
    "peek-a-boo detail", "glimpse-providing element", "peep-offering accent", "glance-allowing highlight", "glimpse-affording feature",
    "tactically positioned logo", "strategically placed emblem", "deliberately situated insignia", "purposefully positioned monogram", "calculatedly arranged emblem",
    "alluringly accessorized", "seductively adorned", "tantalizingly decorated", "teasingly embellished", "provocatively garnished",
    "suggestively styled hair", "seductively arranged locks", "tantalizingly coiffed tresses", "teasingly shaped mane", "provocatively groomed hair",
    "daringly high heels", "boldly elevated shoes", "provocatively raised footwear", "seductively heightened pumps", "tantalizingly lifted stilettos",
    "sheer fabric blouse", "see-through mesh top", "transparent lace shirt", "diaphanous chiffon garment", "translucent organza covering",
    "body-hugging dress", "figure-clinging gown", "form-fitting outfit", "curve-accentuating attire", "silhouette-enhancing ensemble",
    "plunging back design", "deeply cut rear neckline", "dramatically low back", "spine-revealing silhouette", "vertebrae-exposing style",
    "thigh-high slit", "leg-revealing cut", "high-rise opening", "elongated dress division", "extended skirt split",
    "strapless bodice", "shoulder-baring top", "tube-style upper garment", "bandeau-inspired design", "support-free chest covering",
    "low-rise pants", "hip-baring trousers", "waist-skimming bottoms", "pelvis-revealing jeans", "barely-covering lower garment",
    "cropped jacket", "abbreviated outer layer", "shortened covering", "truncated coat", "reduced-length outerwear",
    "deep v-neck sweater", "plunging front knitwear", "dramatically low neckline jumper", "chest-revealing pullover", "décolletage-displaying woolen",
    "off-shoulder blouse", "collarbone-baring top", "dropped-sleeve shirt", "shoulder-exposing garment", "clavicle-highlighting design",
    "high-cut swimsuit", "leg-elongating bathing suit", "hip-accentuating beachwear", "thigh-emphasizing swim garment", "pelvis-highlighting aquatic attire",
    "micromini skirt", "ultra-short lower garment", "barely-there hemline", "extremely abbreviated bottom", "minimalist lower covering",
    "halterneck design", "neck-tied style", "throat-anchored cut", "nape-secured shape", "cervical-fastened pattern",
    "keyhole cutout", "circular opening detail", "round aperture accent", "peephole feature", "ring-shaped reveal",
    "cold-shoulder design", "upper arm reveal", "deltoid-displaying cut", "bicep-baring style", "arm-exposing pattern",
    "peek-a-boo paneling", "glimpse-offering sections", "teasing transparent inserts", "tantalizingly see-through segments", "provocatively sheer portions",
    "side-boob revealing", "lateral chest exposure", "outer breast displaying", "side thorax highlighting", "peripheral bust accentuating",
    "underboob design", "lower breast revealing", "under-chest exposure", "inferior mammary highlighting", "sub-bust accentuating",
    "waist cutout", "midriff opening", "midsection reveal", "torso aperture", "abdominal display window",
    "hip-bone highlighting", "iliac crest displaying", "pelvic prominence accentuating", "hip-revealing", "lateral pelvic exposing",
    "cross-body strapping", "diagonal restraint detailing", "transverse binding element", "cross-torso securing", "body-traversing fastening",
    "harness-inspired overlay", "restraint-suggesting covering", "bondage-reminiscent accessory", "constraint-evoking addition", "limitation-suggesting supplement",
    "cage-style bodice", "barred torso covering", "latticed upper garment", "gridded chest enclosure", "barricaded bust design",
    "corset lacing", "bodice cinching", "waist-constricting fastening", "torso-binding closure", "midsection-narrowing tying",
    "strategic minimalism", "calculated scarcity", "deliberate sparseness", "intentional paucity", "purposeful insufficiency",
    "body-conscious design", "figure-aware styling", "physique-considerate patterning", "form-cognizant shaping", "silhouette-mindful cutting",
    "suggestively draped", "teasingly hung", "provocatively suspended", "seductively arranged", "tantalizingly disposed",
    "barely adequate covering", "minimally sufficient attire", "scantly appropriate dress", "marginally decent outfit", "just-acceptable garments",
    
    # Expressions and gaze (750)
    "seductive expression", "alluring gaze", "tempting look", "enticing stare", "provocative glance",
    "suggestive expression", "inviting gaze", "flirtatious look", "teasing stare", "sultry glance",
    "smoldering expression", "heated gaze", "passionate look", "ardent stare", "fervent glance",
    "intense expression", "burning gaze", "fiery look", "scorching stare", "sizzling glance",
    "penetrating expression", "piercing gaze", "searching look", "probing stare", "examining glance",
    "curious expression", "inquisitive gaze", "wondering look", "questioning stare", "inquiring glance",
    "playful expression", "mischievous gaze", "teasing look", "sly stare", "impish glance",
    "lively expression", "animated gaze", "spirited look", "vivacious stare", "vibrant glance",
    "bright expression", "luminous gaze", "radiant look", "gleaming stare", "shining glance",
    "warm expression", "affectionate gaze", "loving look", "tender stare", "fond glance",
    "caring expression", "compassionate gaze", "sympathetic look", "empathetic stare", "understanding glance",
    "kind expression", "benevolent gaze", "benign look", "gentle stare", "mild glance",
    "soft expression", "tender gaze", "delicate look", "light stare", "subtle glance",
    "nuanced expression", "layered gaze", "complex look", "sophisticated stare", "intricate glance",
    "enigmatic expression", "mysterious gaze", "puzzling look", "perplexing stare", "baffling glance",
    "confusing expression", "bewildering gaze", "mystifying look", "confounding stare", "perplexing glance",
    "intriguing expression", "fascinating gaze", "interesting look", "engaging stare", "captivating glance",
    "spellbinding expression", "mesmerizing gaze", "hypnotic look", "entrancing stare", "bewitching glance",
    "enchanting expression", "charming gaze", "delightful look", "pleasing stare", "agreeable glance",
    "likable expression", "amiable gaze", "friendly look", "genial stare", "amicable glance",
    "sympathetic expression", "supportive gaze", "encouraging look", "reassuring stare", "comforting glance",
    "soothing expression", "calming gaze", "pacifying look", "tranquilizing stare", "relaxing glance",
    "peaceful expression", "serene gaze", "tranquil look", "placid stare", "quiet glance",
    "still expression", "motionless gaze", "fixed look", "stationary stare", "immobile glance",
    "frozen expression", "icy gaze", "cold look", "frigid stare", "chilly glance",
    "cool expression", "collected gaze", "composed look", "self-possessed stare", "self-controlled glance",
    "controlled expression", "disciplined gaze", "restrained look", "held-back stare", "in-check glance",
    "checked expression", "inhibited gaze", "suppressed look", "repressed stare", "held-in glance",
    "contained expression", "reserved gaze", "reticent look", "taciturn stare", "unforthcoming glance",
    "reluctant expression", "unwilling gaze", "disinclined look", "loath stare", "averse glance",
    "unwelcoming expression", "inhospitable gaze", "forbidding look", "uninviting stare", "hostile glance",
    "antagonistic expression", "oppositional gaze", "contrary look", "conflicting stare", "contentious glance",
    "combative expression", "fighting gaze", "battling look", "warring stare", "struggling glance",
    "parted lips", "half-open mouth", "slightly separated lips", "gently opened mouth", "softly parted lips",
    "inviting smile", "beckoning grin", "enticing smirk", "tempting beam", "alluring simper",
    "hooded eyes", "heavy-lidded gaze", "partially closed eyelids", "veiled glance", "shaded look",
    "smoldering gaze", "burning look", "heated stare", "fiery glance", "passionate regard",
    "direct eye contact", "unwavering stare", "steady gaze", "fixed look", "unblinking regard",
    "sideways glance", "coy look", "bashful gaze", "shy peek", "demure regard",
    "through lowered lashes", "beneath downcast eyelids", "under dropped lids", "below lowered eye shields", "beneath descended eye coverings",
    "playful wink", "teasing blink", "mischievous eye closure", "impish lid drop", "roguish lid shutting",
    "bitten lip", "gently nibbled mouth", "softly gnawed lip", "tenderly chewed mouth", "delicately nipped lip",
    "licked lips", "moistened mouth", "dampened lip surface", "wet oral boundaries", "saliva-slicked mouth edges",
    "slow smile", "gradually spreading grin", "unhurriedly forming beam", "leisurely developing simper", "deliberately manifesting mouth curve",
    "knowing look", "understanding gaze", "comprehending stare", "cognizant glance", "aware regard",
    "arched eyebrow", "raised brow", "lifted eye ridge", "elevated forehead fringe", "heightened brow line",
    "half-smile", "partial grin", "incomplete beam", "semi-simper", "demi-smirk",
    "dreamlike gaze", "faraway look", "distant stare", "abstracted glance", "removed regard",
    "fluttering eyelashes", "batting lids", "rapid blink", "quick lid movement", "swift eye shield motion",
    "intense stare", "concentrated gaze", "focused look", "absorbed glance", "attentive regard",
    "longing expression", "yearning face", "desiring visage", "wanting countenance", "craving look",
    "flushed cheeks", "reddened face", "pinkened visage", "rosied countenance", "blushed appearance",
    "swollen lips", "engorged mouth", "plumped oral region", "inflated lip area", "tumescent mouth region",
    "dilated pupils", "expanded eye centers", "widened eye circles", "broadened eye middles", "enlarged eye cores",
    "upward gaze", "skyward look", "heavenward stare", "elevated sight direction", "raised visual focus",
    "downcast eyes", "lowered gaze", "downward look", "descended stare", "dropped visual focus",
    "lips forming 'O'", "circular mouth shape", "rounded lip form", "orbicular oral arrangement", "annular mouth position",
    "sultry pout", "provocative lip protrusion", "seductive mouth projection", "alluring oral thrust", "enticing lip extension",
    "languid gaze", "leisurely look", "unhurried stare", "relaxed glance", "easy regard",
    "bedroom eyes", "intimate gaze", "private look", "personal stare", "confidential glance",
    "playful expression", "fun-loving look", "sport-enjoying gaze", "game-appreciating stare", "frolic-relishing glance",
    "enigmatic smile", "mysterious grin", "puzzling beam", "perplexing smirk", "bewildering simper",
    "vulnerable expression", "defenseless look", "unprotected gaze", "exposed stare", "susceptible glance",
    "confident smile", "self-assured grin", "certain beam", "positive smirk", "assured simper",
    "shocked expression", "surprised look", "astonished gaze", "amazed stare", "startled glance",
    "ecstatic appearance", "rapturous look", "delighted gaze", "overjoyed stare", "thrilled glance",
    "dreamy expression", "wistful look", "pensive gaze", "contemplative stare", "reflective glance",
    "pleading eyes", "beseeching gaze", "imploring look", "entreating stare", "supplicating glance",
    "innocent expression", "pure look", "virtuous gaze", "guiltless stare", "blameless glance",
    "sinful look", "wicked gaze", "immoral stare", "corrupt glance", "depraved expression",
    "mournful appearance", "sorrowful look", "grieving gaze",
        ],
        "adult": [
           "artistic nude", "glossy smooth skin", "erotic position", "intimate room",
"unclothed", "artistic nakedness", "perfect physique", "sensual body curves",
"intimate pose", "high sensuality", "natural beauty", "glowing skin",
"slender neck", "exotic shoulders", "arched back", "beautiful breasts",
"erect nipples", "slim waist", "full hips", "perfect round buttocks",
"full thighs", "proportional calves", "flat stomach", "side body curve",
"fine body hair", "strategically covered genitals", "nipple piercing", "artistic tattoo",
"trimmed pubic hair", "clear thigh fold", "deep buttock curve", "barely visible genitals",
"elegant pose", "figure study", "bodily perfection", "anatomical beauty",
"sensual lighting", "soft shadows", "body contours", "physical form",
"natural pose", "body composition", "artistic composition", "aesthetic nudity",
"classical nude", "renaissance style", "body harmony", "graceful form",
"tasteful exposure", "intimate portrait", "gentle curves", "elegant lines",
"body landscape", "human canvas", "form exploration", "physical beauty",
"body confidence", "natural elegance", "unadorned beauty", "pure form",
"body celebration", "intimate moment", "vulnerable pose", "confident display",
"natural state", "human figure", "body appreciation", "artistic interpretation",
"body silhouette", "anatomical detail", "figure outline", "body angles",
"intimate scene", "private moment", "bedroom setting", "boudoir style",
"sensual atmosphere", "intimate lighting", "moody ambiance", "romantic setting",
"body language", "expressive pose", "inviting position", "suggestive stance",
"body symmetry", "proportional figure", "balanced form", "harmonious shape",
"studio nude", "professional lighting", "controlled environment", "artistic setup",
"body study", "anatomical study", "figure analysis", "form observation",
"intimate detail", "close observation", "careful rendering", "meticulous depiction",
"body narrative", "visual story", "form expression", "physical communication",
"revealing pose", "strategic positioning", "calculated exposure", "deliberate display",
"body truth", "genuine representation", "authentic depiction", "honest portrayal",
"sculptural form", "statuesque pose", "marble-like quality", "stone-carved appearance",
"oil-painting effect", "canvas texture", "brushstroke quality", "painted appearance",
"photographic realism", "lifelike detail", "true-to-life representation", "realistic rendering",
"intimate setting", "private space", "personal environment", "secluded location",
"warm lighting", "golden hour", "soft illumination", "gentle highlights",
"dramatic shadows", "chiaroscuro effect", "light contrast", "shadow play",
"body temperature", "warm skin tones", "cool undertones", "color temperature",
"monochrome treatment", "black and white", "grayscale rendering", "desaturated palette",
"high contrast", "deep shadows", "bright highlights", "tonal extremes",
"soft focus", "dream-like quality", "ethereal appearance", "misty effect",
"sharp detail", "clear definition", "crisp edges", "precise rendering",
"body texture", "skin detail", "surface quality", "tactile appearance",
"form volume", "three-dimensional quality", "spatial presence", "physical depth",
"body motion", "implied movement", "dynamic pose", "kinetic suggestion",
"static pose", "stillness captured", "frozen moment", "timeless position",
"intimate proximity", "close framing", "personal space", "intimate distance",
"wide composition", "environmental context", "spatial relationship", "setting inclusion",
"body fragmentation", "partial view", "cropped composition", "segmented display",
"complete figure", "full-body view", "entire form", "total representation",
"natural environment", "outdoor setting", "environmental integration", "nature context",
"indoor intimacy", "interior space", "contained environment", "domestic setting",
"water element", "bathing scene", "swimming context", "aquatic environment",
"fabric interaction", "textile contrast", "material juxtaposition", "cloth relationship",
"jewelry accent", "ornamental detail", "decorative element", "adornment focus",
"prop integration", "object inclusion", "item interaction", "accessory presence",
"mirror reflection", "duplicated image", "reflective surface", "multiple perspective",
"window light", "natural illumination", "environmental lighting", "situational brightness",
"candlelight intimacy", "flame illumination", "warm glow", "flickering light",
"body as landscape", "topographical approach", "geographical metaphor", "terrain perspective",
"emotional expression", "feeling conveyance", "mood representation", "emotional state",
"psychological portrait", "mental state", "inner condition", "psychological exposure",
"vulnerable display", "emotional openness", "defenseless position", "exposed state",
"confident pose", "self-assured stance", "certain positioning", "deliberate presentation",
"submissive position", "yielding pose", "surrendered stance", "acquiescent attitude",
"dominant posture", "commanding stance", "authoritative pose", "controlling position",
"intimate eye contact", "direct gaze", "personal connection", "visual engagement",
"averted gaze", "looking away", "indirect attention", "visual disconnection",
"natural expression", "genuine emotion", "authentic feeling", "spontaneous reaction",
"composed demeanor", "controlled expression", "deliberate emotion", "intentional appearance",
"playful attitude", "lighthearted approach", "joyful expression", "carefree display",
"serious mood", "solemn expression", "grave demeanor", "weighty presence",
"erotic suggestion", "sensual implication", "passionate hint", "desire indication",
"romantic atmosphere", "love-focused", "affectionate setting", "tender context",
"body politics", "form statement", "physical declaration", "corporeal expression",
"cultural context", "societal framework", "traditional reference", "contemporary interpretation",
"historical allusion", "period reference", "timely context", "era-specific depiction",
"mythological reference", "legendary allusion", "folkloric connection", "mythic context",
"religious overtone", "spiritual reference", "sacred allusion", "divine connection",
"personal narrative", "individual story", "unique communication", "specific message",
"silky skin", "smooth surface", "flawless complexion", "unblemished appearance",
"body glow", "radiant skin", "luminous appearance", "effulgent presence",
"goosebumps detail", "skin reaction", "dermal response", "epidermal sensitivity",
"flushed appearance", "blushing skin", "reddened surface", "heated complexion",
"firm physique", "toned body", "muscular definition", "athletic form",
"soft curves", "rounded edges", "gentle contours", "smooth transitions",
"physical contrast", "body juxtaposition", "form comparison", "figure distinction",
"back dimples", "lumbar indentations", "spinal depressions", "posterior marks",
"spine detail", "vertebral relief", "backbone definition", "spinal articulation",
"shoulder blades", "scapular definition", "upper back detail", "dorsal emphasis",
"clavicle prominence", "collar bone detail", "upper chest accent", "throat base definition",
"nape focus", "neck back", "posterior cervical", "occipital region",
"jawline definition", "mandibular angle", "facial boundary", "profile edge",
"cheekbone highlight", "zygomatic accent", "facial contour", "visage structure",
"ribcage subtle", "costal suggestion", "thoracic frame", "chest structure",
"hip bones", "pelvic crest", "iliac prominence", "waist-hip junction",
"thigh definition", "femoral shape", "upper leg contour", "quadriceps detail",
"calf shaping", "gastrocnemius definition", "lower leg contour", "tibia line",
"ankle delicacy", "malleolar detail", "foot junction", "lower extremity transition",
"foot arch", "plantar curve", "sole contour", "pedal structure",
"wrist detail", "carpal definition", "hand junction", "lower arm transition",
"finger elegance", "digital grace", "hand extremity", "manual finish",
"knuckle detail", "finger joint", "digital articulation", "hand structure",
"nail grooming", "fingertip finish", "digital end", "extremity completion",
"elbow definition", "arm mid-point", "cubital detail", "joint articulation",
"shoulder roundness", "deltoid curve", "upper arm transition", "limb beginning",
"armpit suggestion", "axillary region", "underarm area", "lateral torso",
"breast shape", "mammary contour", "chest prominence", "thoracic feature",
"nipple detail", "areola definition", "breast apex", "mammary peak",
"chest definition", "pectoral shape", "thoracic front", "upper torso",
"stomach contour", "abdominal shape", "midriff definition", "central torso",
"navel detail", "umbilical focus", "belly button", "abdominal center",
"pelvic region", "lower abdomen", "pubic area", "inferior torso",
"genital suggestion", "intimate implication", "private indication", "personal hint",
"buttock shape", "gluteal contour", "posterior prominence", "rear feature",
"thigh-buttock junction", "posterior-lateral transition", "hip-leg connection", "gluteal fold",
"inner thigh", "medial femoral", "leg interior", "adductor region",
"knee definition", "leg articulation", "lower limb joint", "femoral-tibial junction",
"skin translucency", "dermal transparency", "surface clarity", "cutaneous lucidity",
"vein suggestion", "venous detail", "blood vessel hint", "circulatory indication",
"muscle definition", "fibrous detail", "contractile tissue", "motor component",
"tendon visibility", "connecting tissue", "muscle-bone link", "structural connection",
"anatomical accuracy", "physiological correctness", "biological precision", "body-truth rendering",
"posture evaluation", "stance assessment", "position analysis", "bearing examination",
"weighted pose", "gravitational influence", "physical pressure", "force distribution",
"balanced stance", "equilibrium position", "stabilized posture", "centered bearing",
"tension expression", "physical stress", "bodily pressure", "muscular strain",
"relaxation depiction", "physical ease", "bodily comfort", "muscular release",
"physical narrative", "body story", "corporeal account", "anatomical tale",
"aesthetic appreciation", "beauty recognition", "visual admiration", "form enjoyment",
"sensory evocation", "feeling stimulation", "sense activation", "perception triggering",
"viewer relationship", "observer connection", "audience engagement", "spectator involvement",
"creative interpretation", "artistic license", "expressive freedom", "imaginative rendering",
"stylistic choice", "aesthetic decision", "artistic determination", "creative selection",
"medium consideration", "material awareness", "creation substance", "production matter",
"technical execution", "skill application", "craftsmanship display", "expertise demonstration",
"artistic purpose", "creative intention", "expressive aim", "aesthetic objective",
"cultural relevance", "societal significance", "communal importance", "collective relevance",
"personal meaning", "individual significance", "private importance", "self-relevance",
"universal appeal", "widespread resonance", "general attraction", "common appreciation",
"specific audience", "targeted viewers", "particular spectators", "defined observers",
"tasteful limitation", "aesthetic boundary", "artistic constraint", "creative restriction",
"sensual boundary", "erotic limit", "passionate threshold", "intimate border",
"suggestive maximum", "allusive ceiling", "indicative peak", "implicit uppermost",
"subtle provocation", "gentle provocation", "mild incitement", "soft stimulus"
        ],
        "nudity": [
            "nude", "unclothed", "fully naked", "naked", "perfect nakedness",
"nude model", "total body exposure", "full body exposure", "figure study",
"beautiful anatomy", "ideal body shape", "sensual uncovered",
"artistic nakedness", "nude pose", "bare body", "nude art",
"visible genitalia", "detailed vulva", "detailed penis", "natural pubic hair",
"fully exposed buttocks", "exposed breasts", "exposed genitals", "visible testicles",
"vaginal opening", "anal opening", "detailed labia", "detailed glans", "thick pubic hair",
"penetration", "squirting", "ejaculation", "body fluids", "intimate openings",
"explicit sex", "intercourse", "masturbation", "orgasm", "climax",
"complete nudity", "unconcealed body", "unrestricted exposure", "uninhibited display",
"full frontal", "rear view explicit", "side profile nude", "anatomical orientation",
"spreading pose", "legs apart", "explicit angle", "revealing position",
"gynecological view", "medical perspective", "clinical examination", "anatomical study",
"educational nudity", "instructional exposure", "teaching position", "learning reference",
"graphic detail", "explicit focus", "uncensored view", "unfiltered representation",
"sexual anatomy", "reproductive organs", "genital display", "intimate parts",
"exposed orifices", "body openings", "physical entries", "anatomical portals",
"erogenous zones", "pleasure centers", "sensitive areas", "stimulation points",
"aroused state", "physical excitement", "bodily response", "sexual readiness",
"erection detail", "tumescence depiction", "arousal representation", "excitement illustration",
"vaginal detail", "labia minora", "labia majora", "clitoral hood",
"penile anatomy", "shaft detail", "foreskin depiction", "glans exposure",
"scrotal detail", "testicle rendering", "sack depiction", "gonad illustration",
"pubic region", "genital area", "intimate zone", "private sector",
"anus detail", "rectal entrance", "posterior opening", "rear aperture",
"perineum area", "taint region", "between-zone", "intermediate space",
"buttock spread", "cheek separation", "gluteal divide", "posterior parting",
"intimate touch", "self-contact", "manual stimulation", "digital manipulation",
"genital interaction", "sexual contact", "intimate connection", "physical joining",
"penetrative act", "insertion depiction", "entry illustration", "invasive representation",
"sexual position", "coital arrangement", "intercourse stance", "connective pose",
"missionary position", "frontal engagement", "face-to-face connection", "anterior coupling",
"rear entry", "posterior approach", "doggy style", "behind position",
"riding position", "mounted stance", "cowgirl arrangement", "straddling pose",
"sideways coupling", "lateral connection", "spoon position", "side-by-side joining",
"standing connection", "vertical coupling", "upright position", "erect stance",
"seated engagement", "sitting position", "chair activity", "throne coupling",
"oral activity", "mouth engagement", "labial contact", "lingual interaction",
"fellatio depiction", "penile sucking", "male oral reception", "mouth service",
"cunnilingus illustration", "vaginal licking", "female oral reception", "tongue service",
"69 position", "mutual oral", "reciprocal service", "simultaneous mouth",
"manual stimulation", "hand activation", "finger play", "digital manipulation",
"male masturbation", "penis stroking", "self-pleasuring", "autoeroticism",
"female masturbation", "vulva rubbing", "self-stimulation", "personal gratification",
"climax depiction", "orgasmic moment", "pleasure peak", "ecstasy capture",
"ejaculatory event", "seminal expulsion", "fluid emission", "liquid release",
"female ejaculation", "squirting event", "fluid expulsion", "gushing depiction",
"multiple partners", "group activity", "communal sexuality", "shared intimacy",
"threesome configuration", "trio arrangement", "three-person activity", "triple connection",
"orgy depiction", "multi-person activity", "group sexuality", "communal pleasure",
"daisy chain", "connected sequence", "pleasure circuit", "serial joining",
"double penetration", "dual entry", "multiple invasion", "twin insertion",
"spitroasting arrangement", "dual-end service", "bidirectional attention", "two-point focus",
"gangbang depiction", "multiple-on-one", "group focus", "concentrated attention",
"bukkake representation", "multi-emission", "collective release", "group expulsion",
"cream pie depiction", "internal deposit", "filling illustration", "insertion aftermath",
"facial decoration", "external coverage", "surface application", "outer layering",
"body shot", "torso target", "trunk landing", "physical destination",
"sex toy use", "pleasure implement", "satisfaction tool", "gratification device",
"dildo application", "artificial phallus", "substitute penis", "replacement member",
"vibrator use", "oscillating device", "buzzing implement", "trembling tool",
"anal plug", "posterior insert", "rectal device", "behind implement",
"bondage situation", "restraint scenario", "limitation circumstance", "confinement context",
"submission position", "yielding posture", "surrendering stance", "acquiescing pose",
"dominance posture", "controlling stance", "authoritative position", "commanding pose",
"fetish element", "specific fixation", "particular predilection", "special preference",
"role play", "character assumption", "persona adoption", "fantasy embodiment",
"costume element", "partial clothing", "selective coverage", "strategic garment",
"bodily fluid", "natural liquid", "physical secretion", "organic emission",
"lubricant application", "slippery substance", "friction reduction", "smooth facilitation",
"semen representation", "male fluid", "seminal liquid", "reproductive substance",
"vaginal secretion", "female moisture", "natural lubrication", "arousal fluid",
"saliva use", "oral moisture", "mouth liquid", "tongue wetness",
"sweat depiction", "bodily moisture", "exertion liquid", "activity dampness",
"shower scene", "water cleansing", "bathing activity", "aquatic nudity",
"wet appearance", "moisture effect", "liquid coverage", "dampness aesthetic",
"oiled body", "glistening skin", "shiny surface", "reflective coating",
"body painting", "skin decoration", "surface artistry", "epidermal canvas",
"explicit piercing", "genital jewelry", "intimate decoration", "private ornament",
"explicit tattoo", "genital artwork", "intimate design", "private illustration",
"collar wearing", "neck restraint", "submission symbol", "control indicator",
"leash attachment", "guiding tether", "control connection", "direction link",
"handcuff restraint", "wrist binding", "hand limitation", "arm restriction",
"rope binding", "cord restraint", "string limitation", "fiber restriction",
"spreader bar", "limb separator", "extremity divider", "appendage spacer",
"harness wearing", "body rigging", "frame attachment", "form harnessing",
"cage containment", "body enclosure", "form imprisonment", "physical confinement",
"chastity device", "genital lock", "pleasure prevention", "satisfaction denial",
"nipple clamp", "breast grip", "chest pinch", "bosom clasp",
"genital clamp", "private grip", "intimate pinch", "personal clasp",
"whip mark", "lash trace", "strike evidence", "impact indication",
"spanking redness", "impact flush", "striking blush", "slap evidence",
"gag wearing", "mouth obstruction", "verbal prevention", "speech hindrance",
"blindfold coverage", "eye obstruction", "sight prevention", "vision hindrance",
"body writing", "skin message", "epidermal text", "surface communication",
"degradation element", "humiliation factor", "abasement component", "debasement aspect",
"worship position", "adoration pose", "veneration stance", "reverence posture",
"feet focus", "foot attention", "lower extremity emphasis", "pedal concentration",
"exhibitionist setting", "display context", "showing circumstance", "presentation scenario",
"voyeuristic perspective", "watching viewpoint", "observation angle", "viewing position",
"public nudity", "open exposure", "communal display", "social revelation",
"private intimacy", "personal moment", "secluded activity", "exclusive encounter",
"consensual depiction", "agreeing participants", "willing engagement", "approving involvement",
"pleasure expression", "enjoyment demonstration", "satisfaction indication", "gratification display",
"ecstasy face", "pleasure countenance", "enjoyment visage", "gratification expression",
"orgasm contortion", "climax distortion", "peak twisting", "zenith convulsion",
"afterglow state", "post-climax condition", "following-pleasure status", "satisfaction aftermath",
"sexual exhaustion", "intimate fatigue", "pleasure tiredness", "gratification weariness",
"multiple orgasm", "sequential climax", "repeated peak", "serial zenith",
"tantric position", "energy alignment", "chakra arrangement", "spiritual stance",
"kama sutra reference", "ancient position", "traditional stance", "historical arrangement",
"fertility position", "conception stance", "impregnation pose", "procreation arrangement",
"birthing reference", "delivery position", "labor stance", "parturition arrangement",
"anatomical accuracy", "physiological correctness", "biological precision", "organic accuracy",
"scientific detail", "clinical precision", "medical accuracy", "technical correctness",
"age verification", "maturity confirmation", "adulthood validation", "majority assurance",
"intimate hair removal", "genital smoothness", "private depilation", "personal shaving",
"natural growth", "unaltered state", "original condition", "unmodified situation",
"fluid dripping", "liquid descent", "emission falling", "secretion dropping",
"male enhancement", "penile enlargement", "masculine augmentation", "phallus increase",
"breast augmentation", "mammary enhancement", "chest enlargement", "bosom increase",
"genital manipulation", "private handling", "intimate management", "personal operation",
"oral demonstration", "mouth exhibition", "labial display", "lingual presentation",
"sexual instruction", "intimate teaching", "carnal education", "erotic demonstration",
"sensual guide", "pleasure direction", "gratification instruction", "satisfaction guidance",
"explicitness level", "graphic degree", "detailed measure", "vivid extent",
"artistic quality", "aesthetic value", "creative merit", "compositional worth",
"commercial purpose", "sellable intention", "marketable aim", "profitable objective",
"personal expression", "individual statement", "private declaration", "self-communication",
"taboo breaking", "prohibition violation", "restriction transgression", "limitation crossing",
"boundary pushing", "limit testing", "frontier challenging", "border extending",
"explicit close-up", "intimate magnification", "private enlargement", "personal zoom",
"wide perspective", "broad viewpoint", "extensive outlook", "comprehensive angle",
"high definition", "clear resolution", "sharp delineation", "precise definition",
"raw representation", "unfiltered depiction", "unprocessed portrayal", "unrefined illustration",
"stylized version", "artistic interpretation", "creative rendering", "imaginative depiction",
"realistic portrayal", "lifelike representation", "true-to-life depiction", "actual illustration"
        ]
    }
}

# Prompt enhancer untuk membantu menghasilkan prompt yang lebih baik
def enhance_prompt_local(prompt, language="auto", include_nsfw=True):
    """
    Meningkatkan kualitas prompt secara lokal tanpa menggunakan API.
    
    Args:
        prompt (str): Prompt original dari pengguna
        language (str): Bahasa output ("id", "en", atau "auto")
        include_nsfw (bool): Apakah termasuk konten NSFW
        
    Returns:
        str: Prompt yang ditingkatkan kualitasnya
    """
    # Deteksi bahasa dari prompt
    if language == "auto":
        # Gunakan logika sederhana untuk mendeteksi bahasa berdasarkan kata-kata umum
        id_words = ["yang", "dengan", "untuk", "adalah", "dan", "ini", "itu", "di", "ke", "dari", "pada", "dalam", "tidak", "akan", "bisa"]
        id_count = sum(1 for word in id_words if word.lower() in prompt.lower().split())
        language = "id" if id_count >= 2 else "en"
    
    if language not in ["id", "en"]:
        language = "en"  # Default to English if language not supported
    
    # Tentukan kategori yang sesuai dengan prompt
    categories = ["general"]  # Selalu sertakan kategori general
    
    # Deteksi berbagai kategori dari prompt
    lower_prompt = prompt.lower()
    
    # Deteksi landscape
    landscape_keywords = ["landscape", "scenery", "pemandangan", "mountains", "gunung", "laut", "sea", "beach", "pantai", "sunset", "sunrise"]
    if any(keyword in lower_prompt for keyword in landscape_keywords):
        categories.append("landscape")
        
    # Deteksi portrait
    portrait_keywords = ["portrait", "potret", "face", "wajah", "selfie", "closeup", "headshot", "foto orang"]
    if any(keyword in lower_prompt for keyword in portrait_keywords):
        categories.append("portrait")
        
    # Deteksi artistic
    artistic_keywords = ["art", "seni", "artistic", "painting", "lukisan", "illustration", "ilustrasi", "drawing", "sketch"]
    if any(keyword in lower_prompt for keyword in artistic_keywords):
        categories.append("artistic")
        
    # Deteksi fantasy
    fantasy_keywords = ["fantasy", "fantasi", "magic", "sihir", "dragon", "naga", "fairy", "peri", "wizard", "castle", "medieval"]
    if any(keyword in lower_prompt for keyword in fantasy_keywords):
        categories.append("fantasy")
        
    # Deteksi sci-fi
    scifi_keywords = ["sci-fi", "science fiction", "futuristic", "future", "robot", "cyber", "cyberpunk", "space", "alien"]
    if any(keyword in lower_prompt for keyword in scifi_keywords):
        categories.append("sci_fi")
    
    # Deteksi wajah - perbaikan indentasi di sini
    face_keywords = ["face", "wajah", "portrait", "potret", "selfie", "headshot", "facial", "close-up", "closeup", "head", "kepala", "muka"]
    if any(keyword in lower_prompt for keyword in face_keywords):
        categories.append("face_detail")
    
    # Selalu sertakan detail tubuh untuk gambar orang
    body_keywords = ["woman", "wanita", "man", "pria", "girl", "gadis", "boy", "cowok", "person", "orang", "human", "manusia", "body", "tubuh"]
    if any(keyword in lower_prompt for keyword in body_keywords):
        categories.append("body_detail")
    
    # Deteksi konten NSFW jika diizinkan
    if include_nsfw:
        # Deteksi NSFW
        nsfw_keywords = ["sexy", "seksi", "hot", "sensual", "seductive", "menggoda", "lingerie", "bikini", "pakaian dalam"]
        if any(keyword in lower_prompt for keyword in nsfw_keywords):
            categories.append("nsfw")
            
        # Deteksi adult
        adult_keywords = ["adult", "dewasa", "erotic", "erotis", "nude", "semi-nude", "telanjang", "naked", "topless", "breast", "payudara", "ass", "bokong", "butt"]
        if any(keyword in lower_prompt for keyword in adult_keywords):
            categories.append("adult")
            
        # Deteksi nudity
        nudity_keywords = ["nude", "nudity", "naked", "full naked", "telanjang", "full nude", "completely nude", "unclothed", "penis", "vagina", "sex", "seks", "fuck", "fucking", "pussy", "memek", "kontol", "dick", "cock", "cum", "intercourse"]
        if any(keyword in lower_prompt for keyword in nudity_keywords):
            categories.append("nudity")
    
    # Buat daftar semua peningkatan yang mungkin berdasarkan kategori
    all_enhancements = []
    for category in categories:
        if category in PROMPT_ENHANCEMENTS[language]:
            all_enhancements.extend(PROMPT_ENHANCEMENTS[language][category])
    
    # Hilangkan duplikat
    all_enhancements = list(set(all_enhancements))
    
    # Pilih beberapa enhancement secara acak (untuk variasi)
    num_enhancements = min(10, len(all_enhancements))  # Maksimal 10 enhancement
    selected_enhancements = random.sample(all_enhancements, num_enhancements)
    
    # Periksa apakah enhancement sudah ada dalam prompt
    final_enhancements = []
    for enhance in selected_enhancements:
        # Cek apakah enhancement atau variasinya sudah ada dalam prompt
        if not any(enhance.lower() in prompt.lower() for enhance in [enhance]):
            final_enhancements.append(enhance)
    
    # Tambahkan enhancement ke prompt
    enhanced_prompt = prompt
    for enhance in final_enhancements:
        enhanced_prompt += f", {enhance}"
    
    return enhanced_prompt

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
    "inpaint": "Inpainting memungkinkan Anda mengisi area yang ditandai dengan konten yang sesuai. Upload gambar dan mask untuk area yang ingin diganti.",
    "face_fusion": "Face Fusion memungkinkan Anda menggabungkan wajah Anda dengan template karakter yang tersedia untuk menciptakan gambar unik.",
    "tiktok": "TikTok Downloader memungkinkan Anda mengunduh video TikTok tanpa watermark. Cukup berikan URL video TikTok.",
    "instagram": "Instagram Downloader memungkinkan Anda mengunduh foto dan video dari Instagram. Cukup berikan URL post Instagram.",
    "gpt": "Chat GPT memungkinkan Anda berbicara dengan AI cerdas yang dapat menjawab pertanyaan, memberikan informasi, dan bahkan menganalisa gambar.",
    "tts": "Text to Speech memungkinkan Anda mengubah teks menjadi suara, mengkloning suara, dan lebih banyak lagi."
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

# Inisialisasi logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Helper function untuk mendapatkan base URL API berdasarkan server_id
def get_api_base_url(settings):
    """Mendapatkan URL dasar API berdasarkan server_id yang dipilih"""
    server_id = settings.get("server_id", "rose")
    return SERVER_API_URLS.get(server_id, SERVER_API_URLS["rose"])

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
    
    # Hapus data chat GPT jika ada
    if 'gpt_messages' in context.user_data:
        del context.user_data['gpt_messages']
    
    keyboard = [
        ["🖼 Text to Image", "📜 Old Text to Image"],
        ["🎨 Image to Image", "🧠 Generate Prompt"],
        ["📊 System Info", "🔄 Image Processing"],
        ["👤 Face Fusion", "📱 TikTok Downloader"],
        ["📸 Instagram Downloader", "🤖 Chat GPT"],
        ["🔊 Text to Speech", "⚙️ Settings"],
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
    
    # Jika enhance_prompt diaktifkan, tingkatkan prompt secara lokal
    if settings.get("enhance_prompt", "yes") == "yes":
        original_prompt = prompt
        prompt = enhance_prompt_local(prompt)
        logger.info(f"Enhanced prompt from '{original_prompt[:30]}...' to '{prompt[:30]}...'")
    
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
            "enhance_prompt": settings.get("enhance_prompt", "yes")  # Pastikan string "yes" atau "no"
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
            if value:  # Hanya tambahkan jika nilai true atau non-default
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
                    
                    # Kirim gambar dengan caption yang berisi prompt
                    caption = f"Hasil generasi:\n{prompt}\n{nsfw_warning}"
                    
                    # Beri tahu user bahwa gambar sedang diproses
                    if process_message:
                        try:
                            await process_message.edit_text("⬇️ Mengunduh gambar...")
                        except Exception:
                            pass
                    
                    # METODE 1: Unduh gambar dan kirim sebagai file untuk kualitas original
                    try:
                        logger.info("Trying to download and send the image in high quality")
                        # Unduh gambar menggunakan requests dengan timeout lebih panjang
                        image_response = requests.get(image_url, timeout=45, stream=True)
                        
                        if image_response.status_code == 200:
                            # Simpan gambar ke file sementara dengan nama unik
                            import uuid
                            temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                            
                            with open(temp_filename, "wb") as f:
                                for chunk in image_response.iter_content(chunk_size=8192):
                                    if chunk:  # filter out keep-alive chunks
                                        f.write(chunk)
                            
                            # Update pesan proses
                            if process_message:
                                try:
                                    await process_message.edit_text("🖼️ Mengirim gambar...")
                                except Exception:
                                    pass
                            
                            # Kirim gambar sebagai photo (preview terkompresi)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_photo(
                                    photo=f,
                                    caption=f"{caption}\n\nMengirim file kualitas original...",
                                    reply_markup=reply_markup
                                )
                            
                            # Kirim gambar sebagai document (kualitas original)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_document(
                                    document=f,
                                    filename=f"original_quality_{temp_filename}",
                                    caption=f"Original quality image:\n{caption}"
                                )
                            
                            # Hapus file sementara
                            import os
                            try:
                                os.remove(temp_filename)
                            except Exception as e:
                                logger.warning(f"Could not remove temp file: {str(e)}")
                            
                            logger.info("Successfully sent image as both photo and file")
                            
                            # Hapus pesan proses jika masih ada
                            if process_message:
                                try:
                                    await process_message.delete()
                                except Exception:
                                    pass
                            
                            # Kembali ke menu utama
                            await start(update, context)
                            return ConversationHandler.END
                        else:
                            logger.warning(f"Failed to download image: {image_response.status_code}")
                            # Lanjut ke metode berikutnya jika unduhan gagal
                    except Exception as e:
                        logger.error(f"Error sending high quality image: {str(e)}")
                        # Lanjut ke metode berikutnya
                    
                    # METODE 2: Gunakan InputFile dari IO BytesIO (fallback)
                    try:
                        logger.info("Trying to send image using BytesIO")
                        import io
                        
                        # Unduh gambar ke memori
                        image_response = requests.get(image_url, timeout=45)
                        if image_response.status_code == 200:
                            # Buat BytesIO object
                            bio = io.BytesIO(image_response.content)
                            bio.name = 'image.jpg'
                            
                            # Kirim foto dari BytesIO
                            await update.message.reply_photo(
                                photo=bio,
                                caption=caption,
                                reply_markup=reply_markup
                            )
                            
                            logger.info("Successfully sent image using BytesIO")
                            
                            # Hapus pesan proses jika masih ada
                            if process_message:
                                try:
                                    await process_message.delete()
                                except Exception:
                                    pass
                            
                            # Kembali ke menu utama
                            await start(update, context)
                            return ConversationHandler.END
                    except Exception as e:
                        logger.error(f"Error sending image using BytesIO: {str(e)}")
                        # Lanjut ke metode berikutnya
                    
                    # METODE 3: Kirim URL langsung (fallback terakhir)
                    try:
                        logger.info("Trying to send image with URL")
                        
                        await update.message.reply_photo(
                            photo=image_url,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                        
                        logger.info("Successfully sent image with URL")
                        
                        # Hapus pesan proses jika masih ada
                        if process_message:
                            try:
                                await process_message.delete()
                            except Exception:
                                pass
                        
                        # Kembali ke menu utama
                        await start(update, context)
                        return ConversationHandler.END
                    except Exception as e:
                        logger.error(f"Error sending image with URL: {str(e)}")
                        # Lanjut ke metode failsafe
                    
                    # METODE 4 (failsafe): Kirim URL dalam pesan teks dengan informasi tambahan
                    try:
                        logger.info("Using failsafe method: sending URL as text with instructions")
                        
                        # Hapus pesan proses jika masih ada
                        if process_message:
                            try:
                                await process_message.delete()
                            except Exception:
                                pass
                        
                        await update.message.reply_text(
                            f"✅ Gambar berhasil dibuat!\n\n"
                            f"🔗 URL gambar: {image_url}\n\n"
                            f"📝 Prompt: {prompt}\n\n"
                            f"{nsfw_warning}\n\n"
                            f"ℹ️ Silakan klik URL di atas untuk melihat gambar.",
                            reply_markup=reply_markup
                        )
                        
                        logger.info("Successfully sent URL as text with instructions")
                        
                        # Kembali ke menu utama
                        await start(update, context)
                        return ConversationHandler.END
                    except Exception as e:
                        logger.error(f"Error sending URL as text: {str(e)}")
                        await update.message.reply_text(
                            "Gambar berhasil dibuat tetapi terjadi error saat mencoba mengirimnya. "
                            "Silakan coba lagi nanti."
                        )
                else:
                    await update.message.reply_text("Gambar berhasil dibuat tetapi tidak ada URL yang dikembalikan.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal menghasilkan gambar: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        try:
            await process_message.delete()
        except Exception:
            pass
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except asyncio.TimeoutError:
        logger.error("Async operation timed out")
        try:
            await process_message.delete()
        except Exception:
            pass
        await update.message.reply_text("⌛ Operasi async timeout. Silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        try:
            await process_message.delete()
        except Exception:
            pass
        await update.message.reply_text(f"Error saat memproses permintaan: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Old Text to Image Flow
async def old_txt2img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"📜 *Old Text to Image*\n\n{FEATURE_DESCRIPTIONS.get('old_txt2img', 'Menggunakan model lama untuk generasi gambar.')}\n\n"
        "Masukkan prompt untuk generasi gambar:",
        parse_mode="Markdown"
    )
    return OLD_TXT2IMG_PROMPT

async def handle_old_txt2img_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Store prompt
    context.user_data['old_txt2img_prompt'] = update.message.text
    
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
        
        await process_message.delete()
        
        if response.status_code == 200:
            data = response.json()
            
            if 'status' in data and data['status'] and 'result' in data:
                models = data['result'].get('models', [])
                samplers = data['result'].get('samplers', [])
                
                if models:
                    # Store models and samplers
                    context.user_data['old_models'] = models
                    context.user_data['old_samplers'] = samplers
                    
                    # Display old models
                    models_text = "📋 *Pilih Model Lama*\n\nModels tersedia:\n\n"
                    
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
                    
                    await update.message.reply_text(
                        models_text + "\nPilih model untuk digunakan:",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    
                    return OLD_TXT2IMG_MODEL
                else:
                    await update.message.reply_text("Tidak ada model lama yang tersedia.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan daftar model lama: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error getting old models: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # If we got here, something went wrong
    await start(update, context)
    return ConversationHandler.END

async def handle_old_txt2img_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_model = update.message.text
    
    if selected_model == "🔙 Kembali":
        await start(update, context)
        return ConversationHandler.END
    
    # Store selected model
    context.user_data['old_txt2img_model'] = selected_model
    
    # Get prompt
    prompt = context.user_data.get('old_txt2img_prompt', '')
    
    # Jika enhance_prompt diaktifkan, tingkatkan prompt secara lokal
    settings = context.user_data.get('settings', DEFAULT_SETTINGS)
    if settings.get("enhance_prompt", "yes") == "yes":
        original_prompt = prompt
        prompt = enhance_prompt_local(prompt)
        logger.info(f"Enhanced prompt from '{original_prompt[:30]}...' to '{prompt[:30]}...'")
    
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
            "seed": -1,  # Random seed
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
                    
                    try:
                        # Download image for high quality sending
                        image_response = requests.get(image_url, timeout=45, stream=True)
                        
                        if image_response.status_code == 200:
                            # Save to temporary file
                            import uuid
                            temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                            
                            with open(temp_filename, "wb") as f:
                                for chunk in image_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            # Send as photo (preview)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_photo(
                                    photo=f,
                                    caption=f"Hasil generasi dengan model lama:\nModel: {selected_model}\nPrompt: {prompt}\n\nMengirim file kualitas original...",
                                    reply_markup=reply_markup
                                )
                            
                            # Send as document (original quality)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_document(
                                    document=f,
                                    filename=f"original_quality_{temp_filename}",
                                    caption=f"Original quality image:\nModel: {selected_model}\nPrompt: {prompt}"
                                )
                            
                            # Clean up
                            import os
                            os.remove(temp_filename)
                        else:
                            # Fallback to URL
                            await update.message.reply_photo(
                                photo=image_url,
                                caption=f"Hasil generasi dengan model lama:\nModel: {selected_model}\nPrompt: {prompt}",
                                reply_markup=reply_markup
                            )
                    except Exception as e:
                        logger.error(f"Error sending high quality image: {str(e)}")
                        # Fallback to URL
                        await update.message.reply_photo(
                            photo=image_url,
                            caption=f"Hasil generasi dengan model lama:\nModel: {selected_model}\nPrompt: {prompt}",
                            reply_markup=reply_markup
                        )
                else:
                    await update.message.reply_text("Generasi gambar berhasil tetapi tidak ada URL yang dikembalikan.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal menghasilkan gambar: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Return to main menu
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
    
    # Jika enhance_prompt diaktifkan, tingkatkan prompt secara lokal
    if settings.get("enhance_prompt", "yes") == "yes":
        original_prompt = prompt
        prompt = enhance_prompt_local(prompt)
        logger.info(f"Enhanced prompt from '{original_prompt[:30]}...' to '{prompt[:30]}...'")
    
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
            "enhance_prompt": settings.get("enhance_prompt", "yes")  # Pastikan string "yes" atau "no"
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
            if value:  # Hanya tambahkan jika nilai true atau non-default
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
                    
                    try:
                        # Download image for high quality sending
                        image_response = requests.get(image_url, timeout=45, stream=True)
                        
                        if image_response.status_code == 200:
                            # Save to temporary file
                            import uuid
                            temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                            
                            with open(temp_filename, "wb") as f:
                                for chunk in image_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            # Send as photo (preview)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_photo(
                                    photo=f,
                                    caption=f"Hasil modifikasi:\n{prompt}\n{nsfw_warning}\n\nMengirim file kualitas original...",
                                    reply_markup=reply_markup
                                )
                            
                            # Send as document (original quality)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_document(
                                    document=f,
                                    filename=f"original_quality_{temp_filename}",
                                    caption=f"Original quality image:\n{prompt}\n{nsfw_warning}"
                                )
                            
                            # Clean up
                            import os
                            os.remove(temp_filename)
                        else:
                            # Fallback to URL
                            await update.message.reply_photo(
                                photo=image_url,
                                caption=f"Hasil modifikasi:\n{prompt}\n{nsfw_warning}",
                                reply_markup=reply_markup
                            )
                    except Exception as e:
                        logger.error(f"Error sending high quality image: {str(e)}")
                        # Fallback to URL
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
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Gunakan requests untuk menangani API dengan URL yang diencoding
            encoded_url = urllib.parse.quote_plus(image_url)
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
            
            # Dapatkan base URL berdasarkan server_id yang dipilih
            settings = context.user_data.get('settings', DEFAULT_SETTINGS)
            api_base_url = get_api_base_url(settings)
            
            # Gunakan requests untuk menangani API dengan URL yang diencoding
            encoded_url = urllib.parse.quote_plus(image_url)
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
    
    # Update api_base_url berdasarkan server_id yang dipilih
    settings['api_base_url'] = get_api_base_url(settings)
    
    # Kategori untuk pengaturan
    image_settings = ["width", "height", "samples", "num_inference_steps", "model_id", 
                      "scheduler", "clip_skip", "nsfw_filter", "server_id", "api_base_url", "cfg_scale", "negative_prompt"]
    
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
                settings_text += f"• Server ID: {settings[key]} (URL: {settings.get('api_base_url', 'Unknown')})\n"
            elif key == "api_base_url":
                continue  # Skip api_base_url karena sudah ditampilkan bersama server_id
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
        ["CFG Scale", "Negative Prompt", "Server ID"],
        ["Enhance Prompt", "ControlNet", "Lora Models"],
        ["Advanced Settings", "Kembali"]
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
        
        await update.message.reply_text(f"Enhance Prompt telah {new_status}.")
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
                    else:
                        # Fallback jika tidak bisa mendapatkan daftar scheduler
                        keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await update.message.reply_text(
                            scheduler_text + "Pilih scheduler baru (gagal mendapatkan daftar lengkap):",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                else:
                    # Fallback jika request gagal
                    keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        scheduler_text + "Pilih scheduler baru (gagal mendapatkan daftar):",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error getting schedulers: {str(e)}")
                keyboard = [["DDPMScheduler", "PNDMScheduler"], ["EulerAncestralScheduler", "kembali"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    scheduler_text + "Pilih scheduler baru:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
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
            # Pilihan server untuk beralih antara rose dan lovita
            keyboard = [["rose", "lovita"], ["Kembali"]]
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

async def get_old_models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
                    models_text = f"🔍 *Daftar Model Lama Tersedia (Server: {server_name})*\n\n"
                    
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
                    
                    # Store context for next step
                    context.user_data['selecting_old_model'] = True
                    return SETTINGS_VALUE
                else:
                    await update.message.reply_text(f"Tidak ada model lama yang tersedia pada server {server_name}.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan daftar model lama: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error getting old models: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    return await settings_menu(update, context)

async def handle_settings_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    current_setting = context.user_data.get('current_setting')
    
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
            elif new_value.lower() == "nonaktif":
                context.user_data['settings'][current_setting] = False
                await update.message.reply_text("NSFW Filter dinonaktifkan.")
            else:
                await update.message.reply_text("Nilai tidak valid. Pilih 'Aktif' atau 'Nonaktif'.")
                return SETTINGS_VALUE
        
        # Penanganan untuk server_id
        elif current_setting == "server_id":
            if new_value.lower() in ["rose", "lovita"]:
                context.user_data['settings'][current_setting] = new_value.lower()
                # Update juga api_base_url berdasarkan server_id yang dipilih
                context.user_data['settings']['api_base_url'] = SERVER_API_URLS[new_value.lower()]
                await update.message.reply_text(
                    f"Server ID diubah menjadi: {new_value.lower()}\n"
                    f"API Base URL diperbarui: {context.user_data['settings']['api_base_url']}"
                )
            else:
                await update.message.reply_text("Server ID tidak valid. Pilih 'rose' atau 'lovita'.")
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
        
        # Penanganan untuk setting string
        else:
            context.user_data['settings'][current_setting] = new_value
            await update.message.reply_text(f"Berhasil mengubah {current_setting} menjadi {new_value}.")
        
        # Kembali ke menu settings
        return await settings_menu(update, context)
    
    except ValueError:
        await update.message.reply_text("Nilai tidak valid. Silakan masukkan angka.")
        return SETTINGS_VALUE

# ControlNet Menu
async def controlnet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Dapatkan pengaturan ControlNet saat ini
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    controlnet_settings = context.user_data['settings'].get('controlnet', {})
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
    settings_text += "• segmentation: Mengontrol segmen gambar"
    
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
    
    if choice == "Kembali":
        return await settings_menu(update, context)
    
    if "Enable/Disable" in choice:
        # Toggle status ControlNet
        current_status = context.user_data['settings']['controlnet'].get('enabled', False)
        context.user_data['settings']['controlnet']['enabled'] = not current_status
        new_status = "diaktifkan" if not current_status else "dinonaktifkan"
        
        await update.message.reply_text(f"ControlNet telah {new_status}.")
        return await controlnet_menu(update, context)
    
    if "Pilih Model" in choice:
        # Daftar model ControlNet yang tersedia
        models = [
            "softedge", "inpaint", "lineart", "openpose", "hed", "normal",
            "mlsd", "scribble", "depth", "segmentation", "tile", "tile_xl", 
            "aesthetic-controlnet"
        ]
        
        # Buat keyboard untuk pemilihan model
        keyboard = []
        row = []
        for i, model in enumerate(models):
            row.append(model)
            if len(row) == 2 or i == len(models) - 1:
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
        return CONTROLNET_MODEL
    
    if "Set Weight" in choice:
        await update.message.reply_text(
            "Masukkan nilai weight untuk ControlNet (0.0-1.0).\n"
            "Nilai yang lebih tinggi memberikan pengaruh yang lebih kuat pada hasil akhir.",
            parse_mode="Markdown"
        )
        return CONTROLNET_WEIGHT
    
    if "Set Guidance" in choice:
        await update.message.reply_text(
            "Masukkan nilai guidance start dan end untuk ControlNet dalam format 'start,end' (contoh: 0.0,1.0).\n"
            "Guidance start: Titik awal penerapan ControlNet (0.0-1.0).\n"
            "Guidance end: Titik akhir penerapan ControlNet (0.0-1.0).",
            parse_mode="Markdown"
        )
        return CONTROLNET_GUIDANCE
    
    if "Set Image" in choice:
        await update.message.reply_text(
            "Silakan kirim gambar yang akan digunakan sebagai gambar panduan untuk ControlNet.\n"
            "Gambar ini akan digunakan untuk mengontrol proses generasi sesuai dengan model yang dipilih.",
            parse_mode="Markdown"
        )
        return CONTROLNET_IMAGE
    
    await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
    return CONTROLNET_MENU

async def handle_controlnet_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    model_id = update.message.text
    
    if model_id == "Kembali":
        return await controlnet_menu(update, context)
    
    # Daftar model ControlNet yang tersedia
    valid_models = [
        "softedge", "inpaint", "lineart", "openpose", "hed", "normal",
        "mlsd", "scribble", "depth", "segmentation", "tile", "tile_xl", 
        "aesthetic-controlnet"
    ]
    
    if model_id not in valid_models:
        await update.message.reply_text("Model tidak valid. Silakan pilih dari daftar yang tersedia.")
        return CONTROLNET_MODEL
    
    # Update model ControlNet
    context.user_data['settings']['controlnet']['model_id'] = model_id
    
    await update.message.reply_text(f"Model ControlNet diubah menjadi: {model_id}")
    
    return await controlnet_menu(update, context)

async def handle_controlnet_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    weight_text = update.message.text
    
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
        # Proses dan upload gambar
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload gambar ke server eksternal atau encode sebagai base64
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
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
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar: {str(e)}")
            return CONTROLNET_IMAGE
        
    elif update.message.text:
        if update.message.text == "Kembali":
            return await controlnet_menu(update, context)
        
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
    # Dapatkan pengaturan Lora saat ini
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    lora_settings = context.user_data['settings'].get('lora', {})
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
    
    if choice == "Kembali":
        return await settings_menu(update, context)
    
    if "Enable/Disable" in choice:
        # Toggle status Lora
        current_status = context.user_data['settings']['lora'].get('enabled', False)
        context.user_data['settings']['lora']['enabled'] = not current_status
        new_status = "diaktifkan" if not current_status else "dinonaktifkan"
        
        await update.message.reply_text(f"Lora Model telah {new_status}.")
        return await lora_menu(update, context)
    
    if "Pilih Model" in choice:
        # Kategorikan model Lora
        style_models = ["arcane-style", "niji_express", "velvia-30", "shojo-vibe"]
        character_models = [
            "yae-miko", "frieren", "tatsumaki", "aqua-konosuba", "komi-shouko",
            "esdeath", "kobeni", "anya-spyxfam", "fiona-spyxfam", "makima-offset"
        ]
        detail_models = ["add_detail", "more_details", "more_details_XL"]
        
        # Buat keyboard untuk kategori
        keyboard = [
            ["Style Models", "Character Models"],
            ["Detail Models", "Kembali"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📋 *Kategori Lora Models*\n\n"
            "Pilih kategori Lora Model:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return LORA_MODEL
    
    if "Set Strength" in choice:
        await update.message.reply_text(
            "Masukkan nilai strength untuk model Lora (0.0-1.0).\n"
            "Nilai yang lebih tinggi memberikan pengaruh yang lebih kuat pada hasil akhir.",
            parse_mode="Markdown"
        )
        return LORA_STRENGTH
    
    await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
    return LORA_MENU

async def handle_lora_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    if choice == "Kembali":
        return await lora_menu(update, context)
    
    # Kategorikan model Lora
    style_models = ["arcane-style", "niji_express", "velvia-30", "shojo-vibe"]
    character_models = [
        "yae-miko", "frieren", "tatsumaki", "aqua-konosuba", "komi-shouko",
        "esdeath", "kobeni", "anya-spyxfam", "fiona-spyxfam", "makima-offset"
    ]
    detail_models = ["add_detail", "more_details", "more_details_XL"]
    all_models = style_models + character_models + detail_models
    
    # Cek apakah user memilih kategori
    if choice == "Style Models":
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
        return LORA_MODEL
    
    elif choice == "Character Models":
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
        return LORA_MODEL
    
    elif choice == "Detail Models":
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
        return LORA_MODEL
    
    # Jika user memilih model spesifik
    elif choice in all_models:
        # Update model Lora
        context.user_data['settings']['lora']['model_id'] = choice
        context.user_data['settings']['lora']['enabled'] = True  # Aktifkan Lora otomatis
        
        await update.message.reply_text(f"Model Lora diubah menjadi: {choice} dan diaktifkan.")
        
        return await lora_menu(update, context)
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari daftar yang tersedia.")
        return LORA_MODEL

async def handle_lora_strength(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    strength_text = update.message.text
    
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
    # Dapatkan pengaturan lanjutan saat ini
    if 'settings' not in context.user_data:
        context.user_data['settings'] = DEFAULT_SETTINGS.copy()
    
    advanced_settings = context.user_data['settings'].get('advanced', {})
    
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
        return ADVANCED_SETTING_VALUE

async def handle_advanced_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text
    
    if value == "Kembali":
        return await advanced_menu(update, context)
    
    # Perbarui nilai algorithm_type
    context.user_data['settings']['advanced']['algorithm_type'] = value
    
    await update.message.reply_text(f"Algorithm Type diubah menjadi: {value}")
    
    return await advanced_menu(update, context)

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
                info_text = f"🖥️ **System Info (Server: {server_id})**\n\n"
                
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
            
            features_text += f"{description}\n\n"
            
        await update.message.reply_text(features_text, parse_mode="Markdown")
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
        await update.message.reply_text(about_text, parse_mode="Markdown")
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
            
            "*Generate Prompt*:\n"
            "1. Klik '🧠 Generate Prompt'\n"
            "2. Kirim gambar untuk dianalisis\n"
            "3. Bot akan menghasilkan prompt berdasarkan gambar\n\n"
            
            "*Image Processing*:\n"
            "1. Klik '🔄 Image Processing'\n"
            "2. Pilih jenis pemrosesan yang diinginkan\n"
            "3. Kirim gambar yang ingin diproses\n\n"
            
            "*Inpainting*:\n"
            "1. Pilih '✏️ Inpainting' dari menu Image Processing\n"
            "2. Kirim gambar yang ingin diproses\n"
            "3. Kirim gambar mask (area putih akan diganti)\n"
            "4. Masukkan prompt untuk konten pengganti\n\n"
            
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
        ["✏️ Inpainting", "🔙 Kembali"]
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
    
    elif "Inpainting" in choice:
        context.user_data['imgproc_type'] = "inpaint"
        await update.message.reply_text(
            f"✏️ *Inpainting*\n\n{IMGPROC_DESCRIPTIONS.get('inpaint', 'Inpainting memungkinkan Anda mengisi area yang ditandai dengan konten yang sesuai.')}\n\n"
            "Silakan kirim gambar yang ingin di-inpaint:",
            parse_mode="Markdown"
        )
        return INPAINT_IMAGE
    
    elif "Kembali" in choice:
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return IMGPROC_CHOICE

# Settings for specific image processing types
async def handle_superres_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text
    
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
                        
                        try:
                            # Download image for high quality sending
                            image_response = requests.get(image_url, timeout=45, stream=True)
                            
                            if image_response.status_code == 200:
                                # Save to temporary file
                                import uuid
                                temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                                
                                with open(temp_filename, "wb") as f:
                                    for chunk in image_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                # Send as photo (preview)
                                with open(temp_filename, "rb") as f:
                                    await update.message.reply_photo(
                                        photo=f,
                                        caption=f"Hasil pemrosesan {imgproc_type}\n\nMengirim file kualitas original...",
                                        reply_markup=reply_markup
                                    )
                                
                                # Send as document (original quality)
                                with open(temp_filename, "rb") as f:
                                    await update.message.reply_document(
                                        document=f,
                                        filename=f"original_quality_{temp_filename}",
                                        caption=f"Original quality image from {imgproc_type} processing"
                                    )
                                
                                # Clean up
                                import os
                                os.remove(temp_filename)
                            else:
                                # Fallback to URL
                                await update.message.reply_photo(
                                    photo=image_url,
                                    caption=f"Hasil pemrosesan {imgproc_type}",
                                    reply_markup=reply_markup
                                )
                        except Exception as e:
                            logger.error(f"Error sending high quality image: {str(e)}")
                            # Fallback to URL
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
                    
                    # Informasi tambahan untuk error tertentu
                    if "Backend communication error" in error_message:
                        await update.message.reply_text(
                            "⚠️ Sepertinya ada masalah pada server backend. Ini biasanya terjadi ketika layanan sedang sibuk atau dalam pemeliharaan. "
                            "Silakan coba lagi nanti atau coba jenis pemrosesan gambar lainnya."
                        )
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
            await imgproc_menu(update, context)
            return IMGPROC_CHOICE
        
        # Validasi URL
        url = update.message.text.strip()
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
                            
                            try:
                                # Download image for high quality sending
                                image_response = requests.get(image_url, timeout=45, stream=True)
                                
                                if image_response.status_code == 200:
                                    # Save to temporary file
                                    import uuid
                                    temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                                    
                                    with open(temp_filename, "wb") as f:
                                        for chunk in image_response.iter_content(chunk_size=8192):
                                            if chunk:
                                                f.write(chunk)
                                    
                                    # Send as photo (preview)
                                    with open(temp_filename, "rb") as f:
                                        await update.message.reply_photo(
                                            photo=f,
                                            caption=f"Hasil pemrosesan {imgproc_type}\n\nMengirim file kualitas original...",
                                            reply_markup=reply_markup
                                        )
                                    
                                    # Send as document (original quality)
                                    with open(temp_filename, "rb") as f:
                                        await update.message.reply_document(
                                            document=f,
                                            filename=f"original_quality_{temp_filename}",
                                            caption=f"Original quality image from {imgproc_type} processing"
                                        )
                                    
                                    # Clean up
                                    import os
                                    os.remove(temp_filename)
                                else:
                                    # Fallback to URL
                                    await update.message.reply_photo(
                                        photo=image_url,
                                        caption=f"Hasil pemrosesan {imgproc_type}",
                                        reply_markup=reply_markup
                                    )
                            except Exception as e:
                                logger.error(f"Error sending high quality image: {str(e)}")
                                # Fallback to URL
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
                        
                        # Informasi tambahan untuk error tertentu
                        if "Backend communication error" in error_message:
                            await update.message.reply_text(
                                "⚠️ Sepertinya ada masalah pada server backend. Ini biasanya terjadi ketika layanan sedang sibuk atau dalam pemeliharaan. "
                                "Silakan coba lagi nanti atau coba jenis pemrosesan gambar lainnya."
                            )
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

# Inpainting Functions
async def handle_inpaint_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Check if message contains image
    if update.message.photo:
        # Process and upload image
        process_message = await update.message.reply_text("⏳ Mengupload gambar...")
        
        try:
            # Upload image
            image_data = await process_photo(update, context)
            
            if not image_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar. Coba lagi atau gunakan URL gambar.")
                return INPAINT_IMAGE
            
            # Store image data
            context.user_data['inpaint_image'] = image_data
            
            # Delete process message
            await process_message.delete()
            
            # Ask for mask image
            await update.message.reply_text(
                "Silakan kirim gambar mask (area hitam akan diabaikan, area putih akan diganti):"
            )
            
            return INPAINT_MASK
        
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar: {str(e)}")
            return INPAINT_IMAGE
    
    elif update.message.text:
        if update.message.text.lower() == "kembali":
            return await imgproc_menu(update, context)
        
        # If user sends URL instead of image
        url = update.message.text.strip()
        if url.startswith(('http://', 'https://')):
            context.user_data['inpaint_image'] = url
            
            await update.message.reply_text(
                "Silakan kirim gambar mask (area hitam akan diabaikan, area putih akan diganti):"
            )
            
            return INPAINT_MASK
        else:
            await update.message.reply_text("URL tidak valid. Pastikan URL dimulai dengan http:// atau https://")
            return INPAINT_IMAGE
    else:
        await update.message.reply_text("Silakan kirim gambar atau URL gambar.")
        return INPAINT_IMAGE

async def handle_inpaint_mask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Check if message contains image
    if update.message.photo:
        # Process and upload image
        process_message = await update.message.reply_text("⏳ Mengupload gambar mask...")
        
        try:
            # Upload mask image
            mask_data = await process_photo(update, context)
            
            if not mask_data:
                await process_message.delete()
                await update.message.reply_text("❌ Gagal mengupload gambar mask. Coba lagi atau gunakan URL gambar.")
                return INPAINT_MASK
            
            # Store mask data
            context.user_data['inpaint_mask'] = mask_data
            
            # Delete process message
            await process_message.delete()
            
            # Ask for prompt
            await update.message.reply_text(
                "Masukkan prompt untuk inpainting (deskripsi untuk bagian yang akan diganti):"
            )
            
            return INPAINT_PROMPT
        
        except Exception as e:
            logger.error(f"Error processing mask: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"❌ Error saat memproses gambar mask: {str(e)}")
            return INPAINT_MASK
    
    elif update.message.text:
        if update.message.text.lower() == "kembali":
            return await imgproc_menu(update, context)
        
        # If user sends URL instead of image
        url = update.message.text.strip()
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
    
    # Jika enhance_prompt diaktifkan, tingkatkan prompt secara lokal
    if settings.get("enhance_prompt", "yes") == "yes":
        original_prompt = prompt
        prompt = enhance_prompt_local(prompt)
        logger.info(f"Enhanced prompt from '{original_prompt[:30]}...' to '{prompt[:30]}...'")
    
    if prompt.lower() == "kembali":
        return await imgproc_menu(update, context)
    
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
            "enhance_prompt": settings.get("enhance_prompt", "yes")  # Pastikan string "yes" atau "no"
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
        # Tambahkan pengaturan lanjutan
        advanced_settings = settings.get('advanced', {})
        for key, value in advanced_settings.items():
            if value:  # Hanya tambahkan jika nilai true atau non-default
                if key == "algorithm_type":
                    payload[key] = value
                else:
                    payload[key] = "yes" if value else "no"
        
        # Use api.lovita.io for inpainting as specified
        response = requests.post(
            "https://api.lovita.io/sdapi/inpaint",
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
                    
                    try:
                        # Download image for high quality sending
                        image_response = requests.get(image_url, timeout=45, stream=True)
                        
                        if image_response.status_code == 200:
                            # Save to temporary file
                            import uuid
                            temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                            
                            with open(temp_filename, "wb") as f:
                                for chunk in image_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            # Send as photo (preview)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_photo(
                                    photo=f,
                                    caption=f"Hasil inpainting:\n{prompt}\n{nsfw_warning}\n\nMengirim file kualitas original...",
                                    reply_markup=reply_markup
                                )
                            
                            # Send as document (original quality)
                            with open(temp_filename, "rb") as f:
                                await update.message.reply_document(
                                    document=f,
                                    filename=f"original_quality_{temp_filename}",
                                    caption=f"Original quality image:\n{prompt}\n{nsfw_warning}"
                                )
                            
                            # Clean up
                            import os
                            os.remove(temp_filename)
                        else:
                            # Fallback to URL
                            await update.message.reply_photo(
                                photo=image_url,
                                caption=f"Hasil inpainting:\n{prompt}\n{nsfw_warning}",
                                reply_markup=reply_markup
                            )
                    except Exception as e:
                        logger.error(f"Error sending high quality image: {str(e)}")
                        # Fallback to URL
                        await update.message.reply_photo(
                            photo=image_url,
                            caption=f"Hasil inpainting:\n{prompt}\n{nsfw_warning}",
                            reply_markup=reply_markup
                        )
                else:
                    await update.message.reply_text("Inpainting berhasil tetapi tidak ada URL yang dikembalikan.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal melakukan inpainting: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error in inpainting: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Return to main menu
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
                    template_text = f"🎭 *Template Face Fusion Tersedia (Server: {settings['server_id']})*\n\n"
                    
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
                    else:
                        await update.message.reply_text(f"Tidak ada template yang tersedia pada server {settings['server_id']}.")
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
            "Silakan masukkan ID template atau nomor template yang ingin digunakan. Gunakan 'Lihat Template' jika Anda belum mengetahui ID template."
        )
        return FACE_FUSION_TEMPLATE
    
    elif "Kembali" in choice:
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return FACE_FUSION_CHOICE

async def handle_face_fusion_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    template_input = update.message.text
    
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
                        
                        if data.get('status', False):
                            if 'result' in data and 'url' in data['result']:
                                success = True
                                image_url = data['result']['url']
                                
                                # Tambahkan tombol untuk proses lebih lanjut
                                keyboard = [
                                    [InlineKeyboardButton("🔄 Proses dengan Image Processing", callback_data="use_for_imgproc")],
                                    [InlineKeyboardButton("🎨 Gunakan untuk Image to Image", callback_data="use_for_img2img")]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                
                                # Simpan URL gambar untuk digunakan nanti
                                context.user_data['last_image_url'] = image_url
                                
                                # Hapus pesan proses
                                await process_message.delete()
                                
                                try:
                                    # Download image for high quality sending
                                    image_response = requests.get(image_url, timeout=45, stream=True)
                                    
                                    if image_response.status_code == 200:
                                        # Save to temporary file
                                        import uuid
                                        temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                                        
                                        with open(temp_filename, "wb") as f:
                                            for chunk in image_response.iter_content(chunk_size=8192):
                                                if chunk:
                                                    f.write(chunk)
                                        
                                        # Send as photo (preview)
                                        with open(temp_filename, "rb") as f:
                                            await update.message.reply_photo(
                                                photo=f,
                                                caption=f"Hasil face fusion dengan template ID: {template_id}\n\nMengirim file kualitas original...",
                                                reply_markup=reply_markup
                                            )
                                        
                                        # Send as document (original quality)
                                        with open(temp_filename, "rb") as f:
                                            await update.message.reply_document(
                                                document=f,
                                                filename=f"original_quality_{temp_filename}",
                                                caption=f"Original quality image of face fusion with template ID: {template_id}"
                                            )
                                        
                                        # Clean up
                                        import os
                                        os.remove(temp_filename)
                                    else:
                                        # Fallback to URL
                                        await update.message.reply_photo(
                                            photo=image_url,
                                            caption=f"Hasil face fusion dengan template ID: {template_id}",
                                            reply_markup=reply_markup
                                        )
                                except Exception as e:
                                    logger.error(f"Error sending high quality image: {str(e)}")
                                    # Fallback to URL
                                    await update.message.reply_photo(
                                        photo=image_url,
                                        caption=f"Hasil face fusion dengan template ID: {template_id}",
                                        reply_markup=reply_markup
                                    )
                                
                                break  # Keluar dari loop retry jika berhasil
                            else:
                                if retry == max_retries - 1:  # Jika ini adalah retry terakhir
                                    await process_message.delete()
                                    await update.message.reply_text(
                                        "Face fusion berhasil tetapi tidak ada URL yang dikembalikan. "
                                        "Ini mungkin karena server sedang sibuk atau wajah tidak terdeteksi dengan baik dalam gambar. "
                                        "Silakan coba lagi dengan gambar wajah yang lebih jelas."
                                    )
                        else:
                            if retry == max_retries - 1:  # Jika ini adalah retry terakhir
                                error_message = data.get('message', 'Tidak ada detail error')
                                await process_message.delete()
                                await update.message.reply_text(f"Gagal membuat face fusion: {error_message}")
                    else:
                        if retry == max_retries - 1:  # Jika ini adalah retry terakhir
                                await process_message.delete()
                                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
                except requests.exceptions.Timeout:
                    if retry == max_retries - 1:  # Jika ini adalah retry terakhir
                        await process_message.delete()
                        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
                except Exception as e:
                    if retry == max_retries - 1:  # Jika ini adalah retry terakhir
                        logger.error(f"Error creating face fusion: {str(e)}")
                        await process_message.delete()
                        await update.message.reply_text(f"Error: {str(e)}")
                
                if not success and retry < max_retries - 1:
                    # Tunggu sebentar sebelum retry
                    await asyncio.sleep(2)
                    await process_message.edit_text(f"⏳ Mencoba lagi ({retry+2}/{max_retries})...")
        
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
                
                # Dapatkan base URL berdasarkan server_id yang dipilih
                settings = context.user_data.get('settings', DEFAULT_SETTINGS)
                api_base_url = get_api_base_url(settings)
                
                # Gunakan requests untuk API call
                response = requests.post(
                    f"{api_base_url}/face_fusion/create",
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
                            
                            try:
                                # Download image for high quality sending
                                image_response = requests.get(image_url, timeout=45, stream=True)
                                
                                if image_response.status_code == 200:
                                    # Save to temporary file
                                    import uuid
                                    temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                                    
                                    with open(temp_filename, "wb") as f:
                                        for chunk in image_response.iter_content(chunk_size=8192):
                                            if chunk:
                                                f.write(chunk)
                                    
                                    # Send as photo (preview)
                                    with open(temp_filename, "rb") as f:
                                        await update.message.reply_photo(
                                            photo=f,
                                            caption=f"Hasil face fusion dengan template ID: {template_id}\n\nMengirim file kualitas original...",
                                            reply_markup=reply_markup
                                        )
                                    
                                    # Send as document (original quality)
                                    with open(temp_filename, "rb") as f:
                                        await update.message.reply_document(
                                            document=f,
                                            filename=f"original_quality_{temp_filename}",
                                            caption=f"Original quality image of face fusion with template ID: {template_id}"
                                        )
                                    
                                    # Clean up
                                    import os
                                    os.remove(temp_filename)
                                else:
                                    # Fallback to URL
                                    await update.message.reply_photo(
                                        photo=image_url,
                                        caption=f"Hasil face fusion dengan template ID: {template_id}",
                                        reply_markup=reply_markup
                                    )
                            except Exception as e:
                                logger.error(f"Error sending high quality image: {str(e)}")
                                # Fallback to URL
                                await update.message.reply_photo(
                                    photo=image_url,
                                    caption=f"Hasil face fusion dengan template ID: {template_id}",
                                    reply_markup=reply_markup
                                )
                        else:
                            await update.message.reply_text(
                                "Face fusion berhasil tetapi tidak ada URL yang dikembalikan. "
                                "Ini mungkin karena server sedang sibuk atau wajah tidak terdeteksi dengan baik dalam gambar. "
                                "Silakan coba lagi dengan gambar wajah yang lebih jelas."
                            )
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
                
                # Kirim info terlebih dahulu
                await update.message.reply_text(info_text, parse_mode="Markdown")
                
                # Cek dan kirim video atau gambar
                if 'video' in result and 'url_list' in result['video'] and result['video']['url_list']:
                    video_url = result['video']['url_list'][0]
                    
                    # Kirim video sebagai video (atau dokumen jika terlalu besar)
                    try:
                        await update.message.reply_video(
                            video=video_url,
                            caption=f"Video TikTok by {author}"
                        )
                    except Exception as e:
                        logger.error(f"Error sending video: {str(e)}")
                        # Fallback - kirim URL jika tidak bisa mengirim video langsung
                        await update.message.reply_text(
                            f"Video terlalu besar untuk dikirim langsung. Anda dapat mengunduhnya dari link ini:\n{video_url}"
                        )
                elif 'image_post' in result and result['image_post'] and 'images' in result['image_post']:
                    # Ini adalah post gambar
                    images = result['image_post']['images']
                    
                    await update.message.reply_text("Ini adalah post gambar. Mengirim semua gambar...")
                    
                    # Kirim hingga 10 gambar
                    for i, image in enumerate(images[:10]):
                        if 'url_list' in image and image['url_list']:
                            image_url = image['url_list'][0]
                            try:
                                await update.message.reply_photo(
                                    photo=image_url,
                                    caption=f"Image {i+1}/{min(len(images), 10)} from TikTok by {author}"
                                )
                            except Exception as e:
                                logger.error(f"Error sending image: {str(e)}")
                                await update.message.reply_text(f"Tidak dapat mengirim gambar {i+1}: {image_url}")
                else:
                    await update.message.reply_text(
                        "Tidak dapat menemukan video atau gambar dari TikTok. "
                        "Ini mungkin karena konten pribadi atau terbatas, atau URL tidak valid."
                    )
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mengunduh video TikTok: {error_message}")
        else:
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

# Instagram Downloader
async def instagram_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
        return INSTAGRAM_CHOICE

async def handle_instagram_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    instagram_url = update.message.text.strip()
    action = context.user_data.get('instagram_action', 'download')
    
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
                    if 'medias' in result and result['medias']:
                        await update.message.reply_text(f"Menemukan {len(result['medias'])} media. Mulai mengunduh...")
                        
                        for i, media in enumerate(result['medias']):
                            media_type = media.get('type', 'unknown')
                            media_url = media.get('url', '')
                            
                            if not media_url:
                                continue
                            
                            try:
                                if media_type == "image":
                                    # Download image for high quality
                                    image_response = requests.get(media_url, timeout=45, stream=True)
                                    
                                    if image_response.status_code == 200:
                                        # Save to temporary file
                                        import uuid
                                        temp_filename = f"temp_image_{uuid.uuid4()}.jpg"
                                        
                                        with open(temp_filename, "wb") as f:
                                            for chunk in image_response.iter_content(chunk_size=8192):
                                                if chunk:
                                                    f.write(chunk)
                                        
                                        # Send as photo (preview)
                                        with open(temp_filename, "rb") as f:
                                            await update.message.reply_photo(
                                                photo=f,
                                                caption=f"Image {i+1}/{len(result['medias'])} from Instagram\n\nMengirim file kualitas original..."
                                            )
                                        
                                        # Send as document (original quality)
                                        with open(temp_filename, "rb") as f:
                                            await update.message.reply_document(
                                                document=f,
                                                filename=f"original_quality_{temp_filename}",
                                                caption=f"Original quality Image {i+1}/{len(result['medias'])} from Instagram"
                                            )
                                        
                                        # Clean up
                                        import os
                                        os.remove(temp_filename)
                                    else:
                                        # Fallback to URL
                                        await update.message.reply_photo(
                                            photo=media_url,
                                            caption=f"Image {i+1}/{len(result['medias'])} from Instagram"
                                        )
                                elif media_type == "video":
                                    # For videos, we'll try to download and send as file for maximum quality
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
                                            
                                            # Send as video (preview)
                                            with open(temp_filename, "rb") as f:
                                                await update.message.reply_video(
                                                    video=f,
                                                    caption=f"Video {i+1}/{len(result['medias'])} from Instagram\n\nMengirim file kualitas original..."
                                                )
                                            
                                            # Send as document (original quality)
                                            with open(temp_filename, "rb") as f:
                                                await update.message.reply_document(
                                                    document=f,
                                                    filename=f"original_quality_{temp_filename}",
                                                    caption=f"Original quality Video {i+1}/{len(result['medias'])} from Instagram"
                                                )
                                            
                                            # Clean up
                                            import os
                                            os.remove(temp_filename)
                                        else:
                                            # Fallback to sending URL directly as video
                                            await update.message.reply_video(
                                                video=media_url,
                                                caption=f"Video {i+1}/{len(result['medias'])} from Instagram"
                                            )
                                    except Exception as e:
                                        logger.error(f"Error sending video: {str(e)}")
                                        # Fallback to URL
                                        await update.message.reply_text(
                                            f"Video {i+1}/{len(result['medias'])} from Instagram (klik untuk mengunduh): {media_url}"
                                        )
                                else:
                                    await update.message.reply_text(f"Media URL {i+1}: {media_url}")
                            except Exception as e:
                                logger.error(f"Error sending media: {str(e)}")
                                await update.message.reply_text(f"Tidak dapat mengirim media {i+1}. URL: {media_url}")
                    else:
                        await update.message.reply_text("Tidak menemukan media untuk diunduh.")
                else:
                    # Format untuk info
                    info_text = f"📊 *Informasi Post Instagram*\n\n"
                    
                    if 'user' in result:
                        user = result['user']
                        info_text += f"👤 User: {user.get('username', 'Unknown')}\n"
                        info_text += f"📝 Full Name: {user.get('full_name', 'Unknown')}\n"
                    
                    if 'caption' in result:
                        info_text += f"✏️ Caption: {result['caption'][:200]}...\n" if len(result.get('caption', '')) > 200 else f"✏️ Caption: {result.get('caption', 'No caption')}\n"
                    
                    if 'like_count' in result:
                        info_text += f"❤️ Likes: {result['like_count']}\n"
                        
                    if 'comment_count' in result:
                        info_text += f"💬 Comments: {result['comment_count']}\n"
                    
                    if 'taken_at' in result:
                        info_text += f"🕒 Taken At: {result['taken_at']}\n"
                    
                    # Kirim info
                    await update.message.reply_text(info_text, parse_mode="Markdown")
                    
                    # Juga kirim thumbnail jika ada
                    if 'thumbnail_url' in result and result['thumbnail_url']:
                        try:
                            await update.message.reply_photo(
                                photo=result['thumbnail_url'],
                                caption="Thumbnail post Instagram"
                            )
                        except Exception as e:
                            logger.error(f"Error sending thumbnail: {str(e)}")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal memproses post Instagram: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error processing Instagram: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Kembali ke menu utama
    await start(update, context)
    return ConversationHandler.END

# Chat GPT
async def chat_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    
    if message == "🔙 Kembali":
        # Reset percakapan dan kembali ke menu utama
        if 'gpt_messages' in context.user_data:
            del context.user_data['gpt_messages']
        await start(update, context)
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
                    await update.message.reply_text(gpt_content, parse_mode="Markdown")
                else:
                    await update.message.reply_text("Tidak ada respons dari GPT.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan respons dari GPT: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error in GPT chat: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Tetap di state GPT_CHAT untuk melanjutkan percakapan
    return GPT_CHAT

async def handle_gpt_vision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi gambar
    if not update.message.photo:
        await update.message.reply_text("Silakan kirim gambar untuk dianalisis oleh GPT Vision.")
        return GPT_CHAT
    
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
                    await update.message.reply_text(gpt_content, parse_mode="Markdown")
                else:
                    await update.message.reply_text("Tidak ada respons dari GPT Vision.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mendapatkan respons dari GPT Vision: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error in GPT Vision: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Tetap di state GPT_CHAT untuk melanjutkan percakapan
    return GPT_CHAT

# Text to Speech
async def tts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
            
            payload = {
                "server_id": "lov"  # Server ID default untuk TTS
            }
            
            response = requests.post(
                f"{api_base_url}/tts/voices",
                json=payload,
                headers={
                    'Content-Type': "application/json",
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
                        voices_text = f"🎙️ *Daftar Suara Tersedia (Server: {settings['server_id']})*\n\n"
                        
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
                        
                        return TTS_VOICE_SELECTION
                    else:
                        await update.message.reply_text(f"Tidak ada suara yang tersedia pada server {settings['server_id']}.")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal mendapatkan daftar suara: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        except Exception as e:
            logger.error(f"Error getting voices: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
    
    elif "Clone Voice" in choice:
        await update.message.reply_text(
            "Untuk mengkloning suara, silakan kirim file audio suara Anda. "
            "File harus dalam format WAV, MP3, atau OGG dan berisi suara yang jelas."
        )
        return TTS_CLONE_AUDIO
    
    elif "Kembali" in choice:
        await start(update, context)
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan pilih dari menu yang tersedia.")
    
    return TTS_CHOICE

async def handle_tts_voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice_number = update.message.text
    
    if voice_number == "🔙 Kembali":
        return await tts_menu(update, context)
    
    voice_mapping = context.user_data.get('voice_mapping', {})
    
    if voice_number in voice_mapping:
        voice_id = voice_mapping[voice_number]
        context.user_data['tts_voice_id'] = voice_id
        
        await update.message.reply_text(
            f"Suara #{voice_number} (ID: {voice_id}) dipilih. Anda sekarang dapat menggunakan 'Text to Speech'."
        )
        
        # Kembali ke menu TTS
        return await tts_menu(update, context)
    else:
        await update.message.reply_text("Nomor suara tidak valid. Silakan pilih dari daftar.")
        return TTS_VOICE_SELECTION

async def handle_tts_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    voice_id = context.user_data.get('tts_voice_id', '')
    
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
        
        payload = {
            "server_id": "lov",
            "voice_id": voice_id,
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Model default
            "output_format": "mp3_22050_32",  # Format default
            "apply_text_normalization": "auto"
        }
        
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
                audio_url = data['result'].get('audio_url', '')
                
                if audio_url:
                    # Kirim audio
                    await update.message.reply_audio(
                        audio=audio_url,
                        caption="Text to Speech hasil",
                        title=f"TTS - {text[:30]}..." if len(text) > 30 else f"TTS - {text}"
                    )
                else:
                    await update.message.reply_text("Berhasil mengubah teks menjadi suara tetapi tidak ada URL audio yang dikembalikan.")
            else:
                error_message = data.get('message', 'Tidak ada detail error')
                await update.message.reply_text(f"Gagal mengubah teks menjadi suara: {error_message}")
        else:
            await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        await process_message.delete()
        await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
    
    except Exception as e:
        logger.error(f"Error in text to speech: {str(e)}")
        await process_message.delete()
        await update.message.reply_text(f"Error: {str(e)}")
    
    # Tetap di TTS_TEXT untuk memungkinkan pengguna mengirim teks lebih banyak
    return TTS_TEXT

async def handle_tts_clone_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Periksa apakah pesan berisi audio atau file
    if update.message.audio or update.message.voice or update.message.document:
        file_id = None
        if update.message.audio:
            file_id = update.message.audio.file_id
        elif update.message.voice:
            file_id = update.message.voice.file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        
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
                    else:
                        await update.message.reply_text("Berhasil mengkloning suara tetapi tidak ada Voice ID yang dikembalikan.")
                else:
                    error_message = data.get('message', 'Tidak ada detail error')
                    await update.message.reply_text(f"Gagal mengkloning suara: {error_message}")
            else:
                await update.message.reply_text(f"Error dari server: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            await process_message.delete()
            await update.message.reply_text("⌛ Permintaan timeout. Server mungkin sibuk, silakan coba lagi nanti.")
        
        except Exception as e:
            logger.error(f"Error cloning voice: {str(e)}")
            await process_message.delete()
            await update.message.reply_text(f"Error: {str(e)}")
    
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
        # Simpan generated prompt untuk nanti
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

# Fungsi untuk menjelaskan schedulers
async def explain_schedulers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menjelaskan perbedaan berbagai scheduler"""
    
    explanation = "🔄 *Penjelasan Scheduler*\n\nScheduler mengontrol bagaimana noise dikurangi selama proses generasi gambar. Pilihan scheduler yang tepat dapat mempengaruhi kualitas, kecepatan, dan gaya hasil akhir.\n\n"
    
    for scheduler, description in SCHEDULER_DESCRIPTIONS.items():
        explanation += f"• *{scheduler}*: {description}\n\n"
    
    # Recommendations
    explanation += "*Rekomendasi berdasarkan kebutuhan:*\n"
    explanation += "• Kualitas Terbaik: DDPMScheduler, KDPM2DiscreteScheduler\n"
    explanation += "• Kecepatan Terbaik: LCMScheduler, EulerDiscreteScheduler\n"
    explanation += "• Keseimbangan Kualitas/Kecepatan: DPMSolverMultistepScheduler, UniPCMultistepScheduler\n"
    explanation += "• Variasi Kreatif: EulerAncestralDiscreteScheduler, KDPM2AncestralDiscreteScheduler\n"
    
    await update.message.reply_text(explanation, parse_mode="Markdown")

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
    
    # ControlNet Menu conversation handler (subhandler untuk settings)
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
    
    # Lora Models conversation handler (subhandler untuk settings)
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
    
    # Advanced Settings conversation handler (subhandler untuk settings)
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
            SUPERRES_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_superres_settings)],
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

    # Tambahkan semua handler
    application.add_handler(txt2img_conv_handler)
    application.add_handler(old_txt2img_conv_handler)
    application.add_handler(img2img_conv_handler)
    application.add_handler(prompt_gen_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(help_conv_handler)
    application.add_handler(imgproc_conv_handler)
    application.add_handler(face_fusion_conv_handler)
    application.add_handler(tiktok_conv_handler)
    application.add_handler(instagram_conv_handler)
    application.add_handler(gpt_conv_handler)
    application.add_handler(tts_conv_handler)
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