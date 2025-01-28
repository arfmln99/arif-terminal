from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from faker import Faker

faker = Faker()

def generate_account():
    email = faker.email()
    password = faker.password()
    return email, password

def auto_referral(referral_link):
    options = Options()
    options.add_argument("--headless")  # Jalankan tanpa tampilan browser
    driver = webdriver.Firefox(options=options)

    try:
        driver.get(referral_link)
        email, password = generate_account()
        print(f"Membuat akun dengan email: {email} dan password: {password}")
        # Sesuaikan elemen form dengan elemen dari halaman referral
        driver.find_element("name", "email").send_keys(email)
        driver.find_element("name", "password").send_keys(password)
        driver.find_element("xpath", "//button[@type='submit']").click()
        print("[+] Akun berhasil dibuat!")
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    referral_link = input("Masukkan link referral: ")
    auto_referral(referral_link)
