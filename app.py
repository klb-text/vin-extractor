import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

# -------------------------------
# 🔧 Helper Functions
# -------------------------------

def construct_truecar_url(model, trim):
    """Build TrueCar search URL for a given model and trim (new cars only)."""
    base_url = "https://www.truecar.com/new-cars-for-sale/listings/ford"
    model = model.lower().replace(" ", "-")
    trim = trim.lower().replace(" ", "-")
    return f"{base_url}/{model}/?trim={trim}"

def extract_vins_from_truecar(url, max_vins=30, max_pages=5):
    """Scrape up to `max_vins` VINs from TrueCar listing pages with retry and pagination limits."""
    vins = set()
    headers = {"User-Agent": "Mozilla/5.0"}

    for page in range(1, max_pages + 1):
        paged_url = f"{url}&page={page}"
        for attempt in range(3):
            try:
                response = requests.get(paged_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    break
                else:
                    st.warning(f"⚠️ Status code {response.status_code} for: {paged_url}")
                    time.sleep(2)
            except requests.exceptions.RequestException as e:
                st.warning(f"⏱️ Attempt {attempt+1} failed for {paged_url}: {e}")
                time.sleep(2)
        else:
            st.warning(f"❌ Skipping {paged_url} after 3 failed attempts.")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        vin_tags = soup.find_all(string=re.compile(r'\"vin\":\"[A-HJ-NPR-Z0-9]{17}\"'))
        for tag in vin_tags:
            matches = re.findall(r'\"vin\":\"([A-HJ-NPR-Z0-9]{17})\"', tag)
            vins.update(matches)
            if len(vins) >= max_vins:
                break

        if not vin_tags:
            break

    return list(vins)[:max_vins]

# -------------------------------
# 🚀 Streamlit App
# -------------------------------

st.set_page_config(page_title="TrueCar VIN Extractor", layout="wide")
st.title("🚗 Ford VIN Extractor Dashboard (TrueCar - New Cars Only)")
st.markdown("Upload a CSV with Ford models and trims to extract up to **30 VINs per model** from TrueCar (new car listings only).")

# File uploader
uploaded_file = st.file_uploader("📄 Upload CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if "Model" not in df.columns or "Trim" not in df.columns:
        st.error("CSV must contain 'Model' and 'Trim' columns.")
    else:
        st.success("CSV loaded successfully.")
        st.dataframe(df[["Model", "Trim"]])

        if st.button("🔍 Extract VINs"):
            results = []

            with st.spinner("Scraping VINs from TrueCar (new cars only)..."):
                for _, row in df.iterrows():
                    model = str(row["Model"])
                    trim = str(row["Trim"])
                    search_url = construct_truecar_url(model, trim)
                    vins = extract_vins_from_truecar(search_url)
                    if not vins:
                        st.warning(f"⚠️ No VINs found for {model} {trim}")
                    for vin in vins:
                        results.append({
                            "Model": model,
                            "Trim": trim,
                            "VIN": vin,
                            "TrueCar URL": search_url
                        })

            result_df = pd.DataFrame(results)
            st.subheader("✅ Extracted VINs")
            st.dataframe(result_df)

            # Download button
            csv = result_df.to_csv(index=False)
            st.download_button("📥 Download VINs as CSV", csv, "extracted_vins.csv", "text/csv")

else:
    st.info("Please upload a CSV file to begin.")
