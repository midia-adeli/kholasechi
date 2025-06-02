import google.generativeai as genai

# **حتماً کلید API خود را در اینجا قرار دهید**
genai.configure(api_key="AIzaSyAg-0FQeebux4nycnLgD0P5eSgIGCfPBp8")

model = genai.GenerativeModel("gemini-2.0-flash")  # یا هر مدل دیگر
try:
    response = model.generate_content("آیا کار می کنی؟")
    print("پاسخ از Gemini:", response.text)
    print("وضعیت پاسخ:", response.prompt_feedback)
except Exception as e:
    print("خطا در تست API:", e)