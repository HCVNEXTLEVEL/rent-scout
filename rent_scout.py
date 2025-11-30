import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

# ==========================================
# 🎯 CONFIGURATION
# ==========================================
# 1. THE TARGET: Paste your Craigslist URL here
TARGET_URL = "https://denver.craigslist.org/search/apa?min_bedrooms=2&max_bedrooms=2&min_price=1000&max_price=2000"

# 2. THE EMAILER: Paste your credentials here
EMAIL_SENDER    = "hashimi.fazilhaq@gmail.com"
EMAIL_PASSWORD  = "rcil uvim mhfi erhu"

# 3. THE RECIPIENTS: Who gets the market report?
RECIPIENTS = [
    "hashimi.fazilhaq@gmail.com",
    # "hcv_director@pha.org", 
]

# Browser Disguise
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 1. THE SCRAPER
# ==========================================
print("🕵️  Rent Scout 2.0 starting...")
print(f"📍 Visiting: {TARGET_URL}")

try:
    response = requests.get(TARGET_URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ Error: Website blocked us (Status Code {response.status_code})")
        exit()

    soup = BeautifulSoup(response.text, 'html.parser')
    listings = soup.find_all('li', class_='cl-static-search-result')
    print(f"✅ Found {len(listings)} listings. Extracting data...")

    data = []

    for item in listings:
        try:
            title = item.find('div', class_='title').text.strip()
            price = item.find('div', class_='price').text.strip()
            link = item.find('a')['href']
            location_tag = item.find('div', class_='location')
            location = location_tag.text.strip() if location_tag else "Unknown"

            data.append({
                "Price": price,
                "Title": title,
                "Location": location,
                "Link": link,
                "Date Scraped": datetime.now().strftime("%Y-%m-%d")
            })
        except:
            continue

    # ==========================================
    # 2. THE ANALYST (Excel + Stats)
    # ==========================================
    if len(data) > 0:
        df = pd.DataFrame(data)
        
        # Clean price data
        df['Price_Num'] = df['Price'].str.replace('$', '').str.replace(',', '').astype(float)
        
        # Calculate Stats for the Email Body
        avg_rent = df['Price_Num'].mean()
        min_rent = df['Price_Num'].min()
        max_rent = df['Price_Num'].max()
        count    = len(df)
        
        print(f"📊 Stats: Avg ${avg_rent:,.0f} | Count: {count}")

        # Save Excel
        filename = f"Rent_Comps_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        df.to_excel(filename, index=False)
        print(f"💾 File Saved: {filename}")

        # ==========================================
        # 3. THE DELIVERY (Email)
        # ==========================================
        print(f"📧 Sending report to {len(RECIPIENTS)} recipients...")
        
        # Create Email Body
        email_body = f"""
        <h2>🏙️ Market Rent Analysis</h2>
        <p>Here is the latest rent reasonableness data scraped from Craigslist.</p>
        <ul>
            <li><strong>Listings Found:</strong> {count}</li>
            <li><strong>Average Rent:</strong> ${avg_rent:,.2f}</li>
            <li><strong>Lowest Rent:</strong> ${min_rent:,.2f}</li>
            <li><strong>Highest Rent:</strong> ${max_rent:,.2f}</li>
        </ul>
        <p><em>The full data spreadsheet is attached.</em></p>
        """

        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['Subject'] = f"Rent Comp Report: {datetime.now().strftime('%Y-%m-%d')}"
        msg.attach(MIMEText(email_body, 'html'))

        # ATTACH THE FILE
        with open(filename, "rb") as f:
            part = MIMEApplication(f.read(), Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

        # Login and Send
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        
        for recipient in RECIPIENTS:
            msg['To'] = recipient
            server.send_message(msg)
            
        server.quit()
        print("🚀 SUCCESS! Report emailed successfully.")
        
        # Optional: Clean up (delete) the file from your computer after sending
        # os.remove(filename) 
        
    else:
        print("⚠️ No listings found.")

except Exception as e:
    print(f"❌ Critical Error: {e}")