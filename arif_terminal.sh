#!/bin/bash

# Warna
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
RESET='\033[0m'

# File penyimpanan konfigurasi
CONFIG_FILE="config.txt"
PROXY_FILE="proxies.txt"
PASSWORD_FILE=".password"

# Fungsi untuk mengenkripsi password menggunakan SHA-256
encrypt_password() {
    echo -n "$1" | sha256sum | awk '{print $1}'
}

# Cek apakah file password ada, jika tidak buat file baru
if [ ! -f "$PASSWORD_FILE" ]; then
    hashed_password=$(encrypt_password "sukusukasaku") # Hash password default
    echo "$hashed_password" > "$PASSWORD_FILE"
fi

# Fungsi membaca password hash dari file
read_password() {
    cat "$PASSWORD_FILE"
}

# Fungsi untuk meminta password saat masuk
login() {
    clear
    echo -e "${YELLOW}==============================${RESET}"
    echo -e "${CYAN}  WELCOME TO ARIF TERMINAL   ${RESET}"
    echo -e "${YELLOW}==============================${RESET}"
    echo -e "${RED}Buy full access: 085778870193 (WhatsApp)${RESET}"
    echo ""
    read -sp "Masukkan Password: " input_password
    echo ""
    
    # Hash password yang dimasukkan
    hashed_input=$(encrypt_password "$input_password")
    
    if [ "$hashed_input" != "$(read_password)" ]; then
        echo -e "${RED}[!] Password Salah! Akses Ditolak.${RESET}"
        exit 1
    else
        echo -e "${GREEN}[+] Login Berhasil! Selamat Datang.${RESET}"
        sleep 2
    fi
}

# Fungsi menyimpan pengaturan
save_config() {
    echo "TOTAL_ACCOUNTS=$TOTAL_ACCOUNTS" > $CONFIG_FILE
    echo "DELAY_TIME=$DELAY_TIME" >> $CONFIG_FILE
}

# Fungsi membaca pengaturan
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source $CONFIG_FILE
    else
        TOTAL_ACCOUNTS=5
        DELAY_TIME=10
        save_config
    fi
}

# Fungsi menampilkan header
show_header() {
    clear
    echo -e "${YELLOW}    █████╗ ██████╗ ██╗███████╗███████╗████████╗████████╗███╗   ███╗██╗██╗"
    echo -e "   ██╔══██╗██╔══██╗██║██╔════╝██╔════╝╚══██╔══╝╚══██╔══╝████╗ ████║██║██║"
    echo -e "   ███████║██████╔╝██║███████╗█████╗     ██║      ██║   ██╔████╔██║██║██║"
    echo -e "   ██╔══██║██╔═══╝ ██║╚════██║██╔══╝     ██║      ██║   ██║╚██╔╝██║╚═╝╚═╝"
    echo -e "   ██║  ██║██║     ██║███████║███████╗   ██║      ██║   ██║ ╚═╝ ██║██╗██╗"
    echo -e "   ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝   ╚═╝      ╚═╝   ╚═╝     ╚═╝╚═╝╚═╝"
    echo -e "${CYAN}                     [~] Created by ARIF TERMINAL [~]${RESET}"
    echo ""
}

# Fungsi untuk menjalankan Auto Referral
run_auto_referral() {
    echo -e "${YELLOW}[!] Masukkan Link Referral sebelum memulai:${RESET}"
    read -p "🔗 Link Referral: " REFERRAL_LINK
    echo -e "${GREEN}[+] Menjalankan Auto Referral dengan link: ${CYAN}$REFERRAL_LINK${RESET}"
    python3 auto_referral.py "$REFERRAL_LINK"
    read -p "Tekan Enter untuk kembali ke menu..."
}

# Menu utama setelah login
while true; do
    show_header
    echo -e "${CYAN}[1] Jalankan Auto Referral${RESET}"
    echo -e "${CYAN}[2] Atur Jumlah Akun${RESET}"
    echo -e "${CYAN}[3] Atur Jeda Waktu${RESET}"
    echo -e "${CYAN}[4] Kelola Proxy${RESET}"
    echo -e "${CYAN}[5] Keluar${RESET}"
    read -p "Pilih opsi: " option

    case $option in
        1) run_auto_referral ;;
        2) set_total_accounts ;;
        3) set_delay_time ;;
        4) manage_proxies ;;
        5) echo -e "${RED}[!] Keluar...${RESET}"; break ;;
        *) echo -e "${RED}[!] Opsi tidak valid.${RESET}" ;;
    esac
done
