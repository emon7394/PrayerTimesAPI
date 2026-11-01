import requests
import PyPDF2
import re
from flask import Flask, request
from io import BytesIO
from collections import OrderedDict
import json
import traceback
from datetime import datetime

app = Flask(__name__)

# Base PDF URLs with placeholder for month-year
BASE_PDF_URLS = {
    "Narvik": "https://www.alnorsenter.no/wp-content/uploads/2026/01/bonnetider-Narvik-{}.pdf",
    "Tromso": "https://www.alnorsenter.no/wp-content/uploads/2026/01/bonnetider-Tromso-{}.pdf",
    "Bodo": "https://www.alnorsenter.no/wp-content/uploads/2026/01/bonnetider-Bodo-{}.pdf",
}

# Norwegian month names
MONTHS_NO = {
    1: "januar",
    2: "februar",
    3: "mars",
    4: "april",
    5: "mai",
    6: "juni",
    7: "juli",
    8: "august",
    9: "september",
    10: "oktober",
    11: "november",
    12: "desember"
}

# Cache for PDFs: { "kommune-month-year": pdf_text }
pdf_cache = {}

def get_pdf_text(url, cache_key):
    if cache_key in pdf_cache:
        return pdf_cache[cache_key]
    try:
        response = requests.get(url)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        pdf_cache[cache_key] = text
        return text
    except Exception:
        print(f"Error downloading or reading PDF: {url}")
        traceback.print_exc()
        return ""

def parse_prayer_times(text):
    prayer_times = {}
    try:
        pattern = r"^\s*(\d{1,2})\s+(\d{2}:\d{2})\s+\d{2}:\d{2}\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})"
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            day = int(match[0])
            prayer_times[day] = OrderedDict([
                ("Fajr", match[1]),
                ("Dhuhr", match[2]),
                ("Asr", match[3]),
                ("Maghrib", match[4]),
                ("Isha", match[5])
            ])
    except Exception:
        print("Error parsing prayer times:")
        traceback.print_exc()
    return prayer_times

@app.route("/prayer", methods=["GET"])
def get_prayer_times():
    date_str = request.args.get("date")  # YYYY-MM-DD
    kommune = request.args.get("kommune", "Narvik")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return json.dumps({"error": "Invalid date format, use YYYY-MM-DD"}), 400

    month_no = date_obj.month
    day = date_obj.day
    year = date_obj.year

    base_url = BASE_PDF_URLS.get(kommune)
    if not base_url:
        return json.dumps({"error": f"Kommune '{kommune}' not found"}), 404

    month_name = MONTHS_NO.get(month_no)
    pdf_filename = f"{month_name}-{year}"
    pdf_url = base_url.format(pdf_filename)

    cache_key = f"{kommune}-{month_name}-{year}"
    pdf_text = get_pdf_text(pdf_url, cache_key)
    if not pdf_text:
        return json.dumps({"error": "Could not download PDF"}), 500

    prayer_times_dict = parse_prayer_times(pdf_text)

    if day in prayer_times_dict:
        return json.dumps(prayer_times_dict[day])
    else:
        return json.dumps({"error": "Date not found in PDF"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
