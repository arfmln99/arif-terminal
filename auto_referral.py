from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from faker import Faker
import time

# Inisialisasi Faker untuk generator data
faker = Faker()

# Fungsi membuat akun acak
def generate_account():
    email = faker.email()
    password = faker.password()
    return email, password

# Fungsi menjalankan proses auto referral
def auto_referral(referral_link):
    options = Options()
    options.add_argument("--headless")  # Jalankan tanpa tampilan browser
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    try:
        # Membuka tautan referral
        driver.get(referral_link)

        # Generate email dan password acak
        email, password = generate_account()
        print(f"Membuat akun dengan email: {email} dan password: {password}")

        # Isi form (sesuaikan dengan elemen form Anda)
        driver.find_element("name", "email").send_keys(email)
        driver.find_element("name", "password").send_keys(password)
        driver.find_element("xpath", "//button[@type='submit']").click()

        print("[+] Akun berhasil dibuat!")
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        driver.quit()

# Main program
if __name__ == "__main__":
    referral_link = input("Masukkan link referral: ")
    auto_referral(referral_link)
