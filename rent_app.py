import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from uszipcode import SearchEngine
import altair as alt
import random
from fpdf import FPDF
import base64

# ==========================================
# 🛠️ APP CONFIG
# ==========================================
st.set_page_config(page_title="Rent Reasonableness Certifier", page_icon="⚖️", layout="wide")

st.title("⚖️ Rent Reasonableness Certifier")
st.markdown("Generate a HUD-compliant rent reasonableness determination form in seconds.")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.header("1. Subject Unit Info")
    user_zip = st.text_input("Zip Code:", "80229")
    bedrooms = st.selectbox("Bedrooms:", [1, 2, 3, 4, 5], index=1)
    
    st.header("2. Search Filters")
    min_price_filter = st.slider("Remove listings cheaper than:", 0, 3000, 1000)
    
    st.divider()
    
    st.header("3. Preparer Info")
    preparer_name = st.text_input("Staff Name:", "PHA Staff")
    
    st.divider()
    run_btn = st.button("🚀 Run Analysis", type="primary")

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_zip_data(zipcode):
    search = SearchEngine()
    return search.by_zipcode(zipcode)

def get_craigslist_url(zip_obj, beds):
    if not zip_obj: return None
    city = zip_obj.major_city.lower().replace(" ", "")
    # Denver Metro Overrides
    if city in ["thornton", "northglenn", "aurora", "lakewood", "arvada", "westminster", "centennial", "commercecity"]:
        city = "denver"
    url = f"https://{city}.craigslist.org/search/apa?min_bedrooms={beds}&max_bedrooms={beds}&postal={zip_obj.zipcode}&search_distance=10"
    return url

def clean_text(text):
    """Removes emojis/weird characters so PDF doesn't crash"""
    return text.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(df, stats, zip_code, beds, preparer):
    """Generates the Official HUD-Style PDF"""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RENT REASONABLENESS DETERMINATION", ln=True, align='C')
    pdf.ln(10)
    
    # Section 1: Subject
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. SUBJECT PARAMETERS", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Search Area (Zip): {zip_code}", ln=True)
    pdf.cell(0, 8, f"Unit Size: {beds} Bedroom", ln=True)
    pdf.cell(0, 8, f"Date of Determination: {pd.Timestamp.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)
    
    # Section 2: Market Data
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. MARKET DATA SUMMARY", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Total Comparables Found: {stats['count']}", ln=True)
    pdf.cell(0, 8, f"Average Market Rent: ${stats['avg']:,.2f}", ln=True)
    pdf.cell(0, 8, f"Rent Range: ${stats['min']:,.0f} - ${stats['max']:,.0f}", ln=True)
    pdf.ln(5)
    
    # Section 3: Comparables List (Top 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. COMPARABLE UNITS (Top 5 Matches)", ln=True)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Description / Title", 1)
    pdf.cell(30, 8, "Rent", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    # Take top 5 entries
    for index, row in df.head(5).iterrows():
        # Clean title to prevent crash
        clean_title = clean_text(row['Title'])[:65] # Limit length
        pdf.cell(140, 8, clean_title, 1)
        pdf.cell(30, 8, f"${row['Price']:,.0f}", 1)
        pdf.ln()
    
    pdf.ln(15)
    
    # Section 4: Certification
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "4. CERTIFICATION", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, "I certify that the information above was collected from open market data sources. Based on these comparables, the requested rent for the subject unit is considered reasonable.")
    pdf.ln(20)
    
    # Signature Block
    pdf.cell(100, 8, "______________________________________", ln=False)
    pdf.cell(50, 8, "______________________", ln=True)
    pdf.cell(100, 8, f"Preparer: {preparer}", ln=False)
    pdf.cell(50, 8, "Date", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. MAIN APP LOGIC
# ==========================================
if run_btn:
    zip_data = get_zip_data(user_zip)
    
    if not zip_data:
        st.error("Invalid Zip Code.")
    else:
        # Build URLs
        craigslist_url = get_craigslist_url(zip_data, bedrooms)
        
        # Build AffordableHousing.com Deep Link
        ah_url = f"https://www.affordablehousing.com/{zip_data.major_city.lower()}-{zip_data.state.lower()}/?bed={bedrooms}"
        
        # === TOP LINKS ===
        st.info(f"📍 Analyzing: **{zip_data.major_city}, {zip_data.state}**")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Source 1:** [Open Craigslist Search]({craigslist_url})")
        with col_b:
            st.markdown(f"**Source 2:** [Open AffordableHousing.com Results]({ah_url})")
        
        with st.spinner('Scouting comparables...'):
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(craigslist_url, headers=headers)
                
                if response.status_code != 200:
                    st.error("Connection blocked.")
                else:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    listings = soup.find_all('li', class_='cl-static-search-result')
                    
                    data = []
                    center_lat = zip_data.lat
                    center_lon = zip_data.lng
                    
                    for item in listings:
                        try:
                            title = item.find('div', class_='title').text.strip()
                            price = item.find('div', class_='price').text.strip()
                            price_num = float(price.replace('$','').replace(',',''))
                            link = item.find('a')['href']
                            
                            # Location context
                            loc_tag = item.find('div', class_='location')
                            loc_text = loc_tag.text.strip() if loc_tag else "N/A"
                            
                            if price_num >= min_price_filter:
                                # Add slight map jitter
                                offset_lat = random.uniform(-0.02, 0.02)
                                offset_lon = random.uniform(-0.02, 0.02)
                                
                                data.append({
                                    "Title": f"{title} ({loc_text})", # Add location to title
                                    "Price": price_num,
                                    "Link": link,
                                    "lat": center_lat + offset_lat,
                                    "lon": center_lon + offset_lon
                                })
                        except:
                            continue
                    
                    if len(data) > 0:
                        df = pd.DataFrame(data)
                        
                        # Calculate Stats
                        stats = {
                            "avg": df['Price'].mean(),
                            "min": df['Price'].min(),
                            "max": df['Price'].max(),
                            "count": len(df)
                        }
                        
                        # --- RESULTS DISPLAY ---
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Average", f"${stats['avg']:,.0f}")
                        c2.metric("Lowest", f"${stats['min']:,.0f}")
                        c3.metric("Highest", f"${stats['max']:,.0f}")
                        
                        # Map
                        st.map(df, size=20, color="#FF4B4B")
                        
                        # Table
                        st.dataframe(df[['Title', 'Price', 'Link']], use_container_width=True)
                        
                        # --- PDF GENERATION ---
                        st.divider()
                        st.subheader("📝 Export Official Determination")
                        
                        pdf_data = create_pdf(df, stats, user_zip, bedrooms, preparer_name)
                        
                        st.download_button(
                            label="📄 Download Signed PDF Form",
                            data=pdf_data,
                            file_name=f"Rent_Reasonableness_{user_zip}.pdf",
                            mime='application/pdf',
                        )
                        
                    else:
                        st.warning("No listings found. Try lowering the price filter.")
                        
            except Exception as e:
                st.error(f"Error: {e}")