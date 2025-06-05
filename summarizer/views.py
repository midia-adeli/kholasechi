import os
import uuid
import fitz  
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from docx import Document
from django.conf import settings
from django.shortcuts import render
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

LIARA_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOiI2ODNlZTE0YjdhOWYzNWZjMGRkNjc2MmQiLCJ0eXBlIjoiYXV0aCIsImlhdCI6MTc0OTEyMjM2N30.bOHDWDY1_rp6gP640UxgjnZYC-DSMAML2U3DYAlHJ-M"
LIARA_AI_BASE_URL = "https://ai.liara.ir/api/v1/683f0155f3e1bc38faca84f2"
LIARA_AI_MODEL = "google/gemini-2.0-flash-001"


def home(request):
    return render(request, 'home.html') # نام فایل HTML شما اگر متفاوت است، تغییر دهید


class PDFSummaryView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not LIARA_API_KEY or LIARA_API_KEY == "کلید_API_لیارا_خود_را_اینجا_وارد_کنید": # این بخش برای زمانی بود که کلید را در کد قرار می‌دادید
            logger.error("کلید API لیارا به درستی تنظیم نشده است.")
            return Response({"error": "پیکربندی سمت سرور برای کلید API ناقص است."}, status=500)

        pdf_file = request.data.get('file') # برای MultiPartParser از request.data استفاده کنید
        summary_length_percent_str = request.data.get('summary_length_percent', '50') # پیش‌فرض ۵۰٪

        if not pdf_file:
            logger.warning("هیچ فایلی در درخواست ارسال نشده است.")
            return Response({"error": "فایل PDF ارسال نشده است."}, status=400)

        try:
            summary_length_percent = int(summary_length_percent_str)
            if summary_length_percent not in [25, 50, 75]:
                logger.warning(f"درصد طول خلاصه نامعتبر دریافت شد: {summary_length_percent_str}، از پیش‌فرض ۵۰٪ استفاده می‌شود.")
                summary_length_percent = 50
        except ValueError:
            logger.warning(f"مقدار غیر عددی برای درصد طول خلاصه دریافت شد: {summary_length_percent_str}، از پیش‌فرض ۵۰٪ استفاده می‌شود.")
            summary_length_percent = 50
        
        # تبدیل درصد به یک عبارت توصیفی برای پرامپت
        if summary_length_percent == 25:
            length_description = (
                "خلاصه باید بسیار کوتاه و موجز باشد؛ معادل حدود ۲۵٪ از حجم کل متن. لطفاً تنها بر مهم‌ترین نکات، ایده‌های اصلی و نتیجه‌گیری نهایی تمرکز کنید. "
                "هدف، ارائه‌ی دیدی سریع و فشرده از پیام اصلی نویسنده است. از ذکر جزئیات، مثال‌ها یا بحث‌های فرعی خودداری شود، مگر آنکه برای درک ایده‌ی اصلی کاملاً ضروری باشند."
            )

        elif summary_length_percent == 75:
            length_description = (
                "خلاصه باید جامع و با جزئیات فراوان باشد؛ معادل حدود ۷۵٪ از محتوای متن اصلی. لطفاً به‌صورت دقیق و کامل به تمامی بخش‌ها بپردازید، "
                "و نکات کلیدی، جزئیات مهم، استدلال‌ها و در صورت لزوم، مثال‌ها یا داده‌های پشتیبان را نیز ذکر کنید. "
                "هدف، ارائه‌ی بازنمایی‌ای نزدیک به متن کامل است."
            )

        else:  # summary_length_percent == 50 or default
            length_description = (
                "خلاصه باید متعادل و با پوشش کلی از متن باشد؛ در حدود ۵۰٪ از حجم کل. لطفاً به بخش‌های اصلی اشاره کنید و نکات کلیدی، جزئیات مهم و استدلال‌های اصلی را نیز لحاظ کنید. "
                "هدف، ارائه‌ی درک کامل و مناسبی از محتوا است، بدون ورود به جزئیات ریز یا موضوعات فرعی."
            )

                


        original_filename = pdf_file.name
        logger.info(f"شروع پردازش فایل: {original_filename} با درخواست طول خلاصه: {summary_length_percent}%")
        raw_text = ""

        try:
            pdf_bytes = pdf_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                raw_text += page.get_text(sort=True) + "\n"
            doc.close()

            logger.info(f"--- متن استخراج شده از '{original_filename}' (۲۰۰۰ کاراکتر اول) ---")
            logger.info(raw_text[:2000] if raw_text else "متنی استخراج نشد یا متن خالی است")
            logger.info("--- پایان متن استخراج شده ---")

            if not raw_text.strip():
                logger.warning(f"متنی از فایل PDF '{original_filename}' استخراج نشد.")
                return Response({"error": "متنی از فایل PDF استخراج نشد. ممکن است فایل تصویری باشد یا محتوای متنی نداشته باشد."}, status=400)
        except Exception as e:
            logger.error(f"خطا در پردازش فایل PDF '{original_filename}' با PyMuPDF: {e}", exc_info=True)
            return Response({"error": f"خطا در خواندن یا پردازش فایل PDF: {e}"}, status=500)

        try:
            client = OpenAI(
                base_url=LIARA_AI_BASE_URL,
                api_key=LIARA_API_KEY,
            )
            
            prompt_content = f"""📌 نقش شما:
            شما یک مدل زبان بزرگ (LLM) هستید که نقش یک تحلیلگر زبان‌شناس، خلاصه‌ساز تخصصی، مترجم حرفه‌ای و پردازشگر دقیق اسناد PDF را ایفا می‌کند. هدف شما دریافت فایل PDF آپلودشده توسط کاربر، بررسی زبان و ساختار آن، پردازش دقیق محتوای متنی، ترجمه در صورت نیاز، و ارائه یک خلاصه‌ی دقیق، حرفه‌ای و ساختاریافته است که به‌صورت روان و مفید برای کاربر فارسی‌زبان ارائه می‌شود.
            📌 سناریوی عملیاتی:
            کاربر یک فایل PDF آپلود می‌کند که ممکن است شامل متون فارسی یا انگلیسی یا سایر زبان‌های بین‌المللی باشد. فایل می‌تواند شامل محتوای علمی، تحقیقاتی، کتاب، مقاله، دستورالعمل، گزارش رسمی، یا حتی رمان باشد. سیستم شما باید کاملاً بافت و زبان سند را درک کرده، مطابق دستورالعمل‌های زیر واکنش نشان دهد:
            ---
            ## 🎯 دستورالعمل‌های تحلیل و پاسخ:
            ### 1. تشخیص زبان اولیه فایل:
            - فایل PDF را بررسی کن و زبان متن غالب را مشخص کن.
            - اگر فایل چندزبانه است، زبان بخش‌های مختلف را جداگانه شناسایی و علامت‌گذاری کن.
            - فقط به زبان متن توجه کن، نه زبان متادیتا یا عناوین فایل.
            ### 2. پردازش متون فارسی:
            - اگر زبان اصلی فایل فارسی است:
            - متن را به‌طور کامل پردازش کن.
            - ساختار منطقی متن (مقدمه، بدنه، نتیجه‌گیری، فصل‌بندی و ...) را استخراج کن.
            - یک خلاصه‌ی **کامل، دقیق، وفادار و روان** تولید کن که:
                - مفاهیم کلیدی را حفظ کند.
                - ترتیب منطقی مطالب را رعایت کند.
                - **طول خلاصه باید {length_description} باشد.**
                - از ساده‌سازی بیش‌ازحد پرهیز شود.
                - پیام نویسنده و هدف هر بخش در خلاصه منعکس شود.
                - از نقل‌قول، مثال‌ها یا آمار مهم در خلاصه استفاده شود در صورتی که برای فهم محتوا حیاتی باشند.
                - جملات ساده، قابل فهم و بدون اصطلاحات مبهم باشند، اما لحن تخصصی متن حفظ شود.
            ### 3. پردازش متون غیرفارسی:
            - اگر زبان فایل غیرفارسی است (انگلیسی، آلمانی، فرانسه، عربی و ...):
            #### مرحله اول: ترجمه
            - تمام متن فایل را به‌صورت **کلمه‌به‌کلمه، با حفظ لحن نویسنده، سبک نوشتار و ساختار جمله‌ها** به فارسی ترجمه کن.
            - از حذف یا ساده‌سازی جملات بپرهیز.
            - اصطلاحات تخصصی را با معادل دقیق فارسی ارائه کن و در صورت لزوم معادل اصلی را داخل پرانتز بنویس.
            - سبک نوشتار باید طبیعی و روان باشد ولی وفاداری به متن حفظ شود.
            - از ترجمه‌ی تحت‌اللفظی که به روانی زبان آسیب بزند، پرهیز کن.
            - در صورت مواجهه با نقل‌قول‌ها یا اشعار، ساختار اصلی را حفظ کن و معادل معنا‌دار بیاور.
            #### مرحله دوم: خلاصه‌سازی متن ترجمه‌شده
            - پس از ترجمه، متن ترجمه شده را خلاصه کن.
            - **طول خلاصه باید {length_description} از متن ترجمه شده باشد.**
            - خلاصه باید نمایانگر هدف، ساختار، نکات کلیدی و استدلال نویسنده باشد.
            - اگر سند شامل فصل‌ها یا بخش‌های مجزا است، خلاصه هر بخش را جدا ارائه بده.
            - ساختار منطقی حفظ شود: مقدمه → محتوای کلیدی → جمع‌بندی و نتیجه‌گیری.
            ---
            ## 🗂 ساختار خروجی نهایی:
            1. **🔍 زبان فایل شناسایی‌شده:** [مثلاً: فارسی / انگلیسی / ...] 
            2. **📘 ترجمه فارسی (در صورت نیاز):** - [ترجمه کامل و دقیق محتوای غیرفارسی به فارسی، با رعایت سبک، لحن و اصطلاحات تخصصی] 
            3. **📄 خلاصه‌سازی حرفه‌ای فارسی:** - [خلاصه‌ای از متن (فارسی یا ترجمه‌شده)، وفادار به ساختار اصلی، به زبان ساده، ساختاریافته و روان برای کاربر، با طول مشخص شده]
            ---
            ## 🔧 الزامات فنی و زبانی در پردازش:
            - تشخیص زبان باید با درنظر گرفتن محتوا انجام شود نه صرفاً فونت یا نشانه‌گذاری.
            - متن PDF را از نظر قالب (عنوان‌ها، پاورقی، پاراگراف، شماره صفحه، نمودار، جداول و ...) درک کن اما در صورت بی‌اهمیت بودن در خلاصه، آن‌ها را حذف کن.
            - اگر PDF شامل جدول یا نمودار اطلاعاتی است، فقط داده‌های مهم آن‌ها را به صورت نوشتاری در خلاصه بیاور.
            - اگر متن علمی است، ساختار علمی آن حفظ شود (مقدمه، فرضیه، روش، نتایج، بحث، نتیجه‌گیری).
            - اگر متن ادبی است (رمان، داستان، شعر)، لحن ادبی را در ترجمه و خلاصه‌سازی حفظ کن.
            - از حذف متون درون تصاویر خودداری شود مگر OCR معتبر انجام شده باشد. (توجه: کد فعلی OCR ندارد)
            - اگر محتوای فایل ناقص یا آسیب‌دیده است، اعلام کن که تحلیل کامل ممکن نیست.
            ---
            ## 🧠 توجهات ویژه برای کاربرد در سایت:
            - در خروجی، تمام متن‌ها را به صورت قابل نمایش در صفحه وب یا API-friendly ارائه بده.
            - از فرمت‌بندی استاندارد (مثلاً تیترها، پاراگراف‌ها، فهرست‌ها) استفاده کن تا خوانایی حفظ شود.
            - طول خروجی (ترجمه + خلاصه) متناسب با حجم فایل اصلی و درخواست کاربر برای طول خلاصه باشد اما هیچ‌وقت از کیفیت نکاهد.
            - به‌طور پیش‌فرض، از زبان فارسی برای همه‌ی بخش‌های خروجی استفاده کن، مگر اینکه کاربر خواسته باشد که ترجمه ارائه نشود.
            ---
            ## ✨ نمونه‌های عملی از خروجی:
            ### 📁 فایل نمونه ۱:
            - زبان شناسایی‌شده: انگلیسی 
            - موضوع: روانشناسی رشد 
            - ترجمه: ارائه کامل تمام بخش‌ها به فارسی با لحن علمی 
            - خلاصه: ارائه خلاصه ساختاریافته از نظریه‌های رشد، آزمایش‌ها و نتایج محققان با ذکر نام‌ها و مفاهیم کلیدی و طول خواسته شده.
            ---
            ### 📁 فایل نمونه ۲:
            - زبان شناسایی‌شده: فارسی 
            - موضوع: گزارش پژوهشی درباره مهاجرت 
            - خلاصه: تحلیل اهداف تحقیق، روش‌شناسی، یافته‌های آماری، مشکلات شناسایی‌شده و نتیجه‌گیری نویسندگان، با طول خواسته شده.
            ---
            ## ✅ مأموریت نهایی:
            همواره با دقت، وفاداری به متن، حفظ سبک، وضوح، و ساختار منطقی عمل کن. کاربر باید بتواند با خواندن خلاصه‌ی شما، به‌خوبی محتوای کل سند را درک کند. در صورت نیاز به ترجمه، کیفیت آن باید به‌گونه‌ای باشد که برای انتشار رسمی مناسب باشد. خلاصه‌سازی نیز باید به‌قدری قوی باشد که بتواند جایگزین مطالعه‌ی کامل متن برای تصمیم‌گیری یا یادگیری شود، و طول آن مطابق با درخواست کاربر باشد.
            \n\n{raw_text}"""

            completion = client.chat.completions.create(
                model=LIARA_AI_MODEL,
                messages=[{"role": "user", "content": prompt_content}]
            )
            generated_text = completion.choices[0].message.content.strip()
            logger.info(f"پاسخ با موفقیت از سرویس هوش مصنوعی برای فایل '{original_filename}' دریافت شد.")

        except Exception as e:
            logger.error(f"خطا در ارتباط با سرویس هوش مصنوعی لیارا برای فایل '{original_filename}': {e}", exc_info=True)
            return Response({"error": f"خطا در ارتباط با سرویس هوش مصنوعی: {e}"}, status=500)

        docx_url = ""
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        media_url_prefix = getattr(settings, 'MEDIA_URL', None)

        if media_root and media_url_prefix:
            try:
                if not os.path.exists(media_root):
                    os.makedirs(media_root, exist_ok=True)
                
                unique_id = uuid.uuid4()
                output_filename = f"document_{unique_id}.docx"
                doc_path = os.path.join(media_root, output_filename)
                
                doc_obj = Document()
                doc_obj.add_paragraph(generated_text)
                doc_obj.save(doc_path)
                logger.info(f"فایل Word با موفقیت در '{doc_path}' ذخیره شد.")

                if not media_url_prefix.endswith('/'):
                    media_url_prefix += '/'
                docx_url = request.build_absolute_uri(media_url_prefix + output_filename)
            except Exception as e:
                logger.error(f"خطا در ذخیره یا ایجاد URL برای فایل DOCX '{output_filename if 'output_filename' in locals() else 'نامشخص'}': {e}", exc_info=True)
        else:
            logger.warning("تنظیمات MEDIA_ROOT یا MEDIA_URL برای ذخیره فایل Word یافت نشد یا کامل نیست.")

        return Response({
            "summary": generated_text,
            "docx_url": docx_url
        })