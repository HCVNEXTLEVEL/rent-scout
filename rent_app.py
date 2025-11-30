import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
from fpdf import FPDF
import altair as alt

st.set_page_config(page_title="Rent Scout", page_icon="🏢")

st.title("🏢 Rent Reasonableness Scout")
st.markdown("Generate a HUD-compliant market analysis.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Search Parameters")
    # SIMPLIFIED: User types "Denver" or "Chicago" instead of a Zip
    city_input = st.text_input("City Name (e.g. Denver):", "Denver")
    bedrooms = st.selectbox("Bedrooms:", [1, 2, 3, 4], index=1)
    min_price = st.slider("Min Price:", 0, 2000, 1000)
    preparer = st.text_input("Preparer Name:", "Staff")
    run_btn = st.button("🚀 Run Analysis", type="primary")

# --- LOGIC ---
if run_btn:
    # Clean the city name for the URL
    city_clean = city_input.lower().replace(" ", "")
    url = f"https://{city_clean}.craigslist.org/search/apa?min_bedrooms={bedrooms}&max_bedrooms={bedrooms}&search_distance=10"
    
    st.info(f"📍 Searching: **{city_input.title()}**")
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            st.error(f"Could not find a Craigslist page for '{city_input}'. Try a major city name.")
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = soup.find_all('li', class_='cl-static-search-result')
            
            data = []
            for item in listings:
                try:
                    title = item.find('div', class_='title').text.strip()
                    price = item.find('div', class_='price').text.strip()
                    price_num = float(price.replace('$','').replace(',',''))
                    link = item.find('a')['href']
                    
                    if price_num >= min_price:
                        data.append({"Title": title, "Price": price_num, "Link": link})
                except:
                    continue
            
            if data:
                df = pd.DataFrame(data)
                
                # Stats
                avg = df['Price'].mean()
                c1, c2 = st.columns(2)
                c1.metric("Average Rent", f"${avg:,.0f}")
                c2.metric("Listings Found", len(df))
                
                # Chart
                st.altair_chart(alt.Chart(df).mark_bar().encode(x="Price", y="count()"), use_container_width=True)
                
                # Table
                st.dataframe(df)
            else:
                st.warning("No listings found.")
                
    except Exception as e:
        st.error(f"Error: {e}")
