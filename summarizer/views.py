import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from PyPDF2 import PdfReader
from docx import Document
from django.conf import settings
from django.shortcuts import render
from openai import OpenAI # اطمینان حاصل کنید که این import وجود دارد

# اگر دیگر مستقیماً از google.generativeai برای این ویو استفاده نمی‌کنید،
# می‌توانید این خطوط را حذف یا کامنت کنید:
# import google.generativeai as genai
# genai.configure(api_key="eyJhbGciOi...") # این کلید API در کلاینت OpenAI استفاده خواهد شد

# این کلید API شما برای پلتفرم لیارا است.
# مطمئن شوید که از کلید API صحیح خود که از پنل لیارا دریافت کرده‌اید، استفاده می‌کنید.
# کلیدی که در genai.configure استفاده کرده بودید، احتمالاً همین کلید است.
LIARA_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOiI2ODNlZTE0YjdhOWYzNWZjMGRkNjc2MmQiLCJ0eXBlIjoiYXV0aCIsImlhdCI6MTc0OTAzODkwMn0.ODQL54xKDHWcKl_9R-SeiqRhTFB7GPDfUI4uwQY70XA" # یا کلید جدیدی که از لیارا می‌گیرید


def home(request):
    return render(request, 'home.html')

class PDFSummaryView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        pdf_file = request.FILES['file']
        
        reader = PdfReader(pdf_file)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"

        # مقداردهی اولیه کلاینت OpenAI برای اتصال به لیارا
        client = OpenAI(
            base_url="https://ai.liara.ir/api/v1/683f0155f3e1bc38faca84f2", # این URL از اطلاعات شما گرفته شده
            api_key=LIARA_API_KEY, # از کلید API لیارا خود استفاده کنید
        )

        # پرامپت شما
        prompt_content = f"""ا به‌عنوان یک مترجم حرفه‌ای کتاب فعالیت می‌کنید.
وظیفه شما ترجمه‌ی کامل و دقیق متن این متن از کتاب است که به شما ارائه شده است. لطفاً نکات زیر را با دقت کامل رعایت کن:
•  این منبع یک کتاب است و باید با دقت بالا ترجمه شود.
•  هیچ کلمه‌ای نباید از متن اصلی حذف یا نادیده گرفته شود.
•  ترجمه باید کاملاً وفادار به ساختار، لحن و سبک نویسنده‌ی اصلی باشد.
•  از ترجمه‌ی آزاد، خلاصه‌سازی یا بازنویسی پرهیز شود.
•  جملات باید روان، طبیعی و برای خواننده‌ی فارسی‌زبان قابل فهم باشند، بدون اینکه به اصل معنا لطمه‌ای وارد شود.
•  اسامی خاص، مفاهیم فرهنگی یا اصطلاحات تخصصی در صورت لزوم با توضیح یا معادل دقیق فارسی ارائه شوند.
•  متن به زبان انگلیسی است و باید به فارسی ترجمه شود.
\n\n{raw_text}"""

        try:
            completion = client.chat.completions.create(
                model="openai/gpt-4.1", # شناسه مدل مطابق با مستندات لیارا
                messages=[
                    {
                        "role": "user",
                        "content": prompt_content
                    }
                ]
            )
            generated_text = completion.choices[0].message.content.strip()
        except Exception as e:
            # در صورت بروز خطا، آن را برگردانید یا لاگ کنید
            return Response({"error": str(e)}, status=500)


        # ذخیره فایل ورد (اختیاری)
        # اطمینان حاصل کنید که settings.MEDIA_ROOT و settings.MEDIA_URL به درستی تنظیم شده‌اند
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT)
            
        doc_path = os.path.join(settings.MEDIA_ROOT, "summary.docx")
        doc = Document()
        doc.add_paragraph(generated_text)
        doc.save(doc_path)

        docx_url = ""
        if settings.MEDIA_URL:
            docx_url = request.build_absolute_uri(settings.MEDIA_URL + "summary.docx")

        return Response({
            "summary": generated_text, # نام متغیر را به generated_text تغییر دادم تا با پرامپت همخوانی بیشتری داشته باشد
            "docx_url": docx_url
        })