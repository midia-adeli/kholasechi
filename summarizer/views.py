import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from PyPDF2 import PdfReader
from docx import Document
from django.conf import settings
import google.generativeai as genai
from django.shortcuts import render

genai.configure(api_key="AIzaSyAg-0FQeebux4nycnLgD0P5eSgIGCfPBp8")
def home(request):
    return render(request, 'home.html')
class PDFSummaryView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        pdf_file = request.FILES['file']
        
        # استخراج متن از PDF
        reader = PdfReader(pdf_file)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"

        # ارسال به Gemini برای خلاصه‌سازی
        prompt = f"""شما به‌عنوان یک مترجم حرفه‌ای کتاب فعالیت می‌کنید.
وظیفه شما ترجمه‌ی کامل و دقیق متن این متن از کتاب است که به شما ارائه شده است.
\n\n{raw_text}"""
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        summary = response.text.strip()

        # ذخیره فایل ورد (اختیاری)
        doc_path = os.path.join(settings.MEDIA_ROOT, "summary.docx")
        doc = Document()
        doc.add_paragraph(summary)
        doc.save(doc_path)

        return Response({
            "summary": summary,
            "docx_url": request.build_absolute_uri(settings.MEDIA_URL + "summary.docx")
        })
