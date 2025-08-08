import requests
import time
import json
import os

# التوكن الخاص بك (⚠️ يُفضّل حفظه في متغير بيئة وعدم نشره علنًا)
TELEGRAM_TOKEN = "8254518680:AAFcBX59fJPcQnlhQzFHjstWc684NADnZ5Y"

# ملفات التخزين
SUBSCRIBERS_FILE = "subscribers.json"
STATUS_FILE = "status.json"

# تحميل قائمة المشتركين
if os.path.exists(SUBSCRIBERS_FILE):
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            subscribers = json.load(f)
    except:
        subscribers = []
else:
    subscribers = []

# الروابط + الحالة
links_status = {
    "https://testflight.apple.com/join/1Z9HQgNw": None,
    "https://testflight.apple.com/join/6drWGVde": None,
    "https://testflight.apple.com/join/uk4993r5": None,
    "https://testflight.apple.com/join/kYbkecxa": None
}

# تحميل الحالة القديمة إن وجدت
if os.path.exists(STATUS_FILE):
    try:
        with open(STATUS_FILE, "r") as f:
            saved_status = json.load(f)
            links_status.update(saved_status)
    except:
        pass

# ترويسة للطلبات (تساعد مع TestFlight أحيانًا)
REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def save_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(subscribers, f)
    except Exception as e:
        print(f"❌ خطأ في حفظ المشتركين: {e}")

def send_telegram(chat_id, message, button_url=None, button_text=None):
    """إرسال رسالة مع إمكانية إضافة زر"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    if button_url and button_text:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[{"text": button_text, "url": button_url}]]
        })
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"❌ خطأ في الإرسال: {e}")

def broadcast(message, button_url=None, button_text=None):
    """إرسال رسالة لكل المشتركين"""
    for chat_id in list(subscribers):
        send_telegram(chat_id, message, button_url, button_text)

def get_updates(offset=None):
    """جلب الرسائل الجديدة من التليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    try:
        r = requests.get(url, params=params, timeout=20).json()
        return r.get("result", [])
    except Exception as e:
        print(f"❌ خطأ في getUpdates: {e}")
        return []

def handle_new_messages():
    """التعامل مع الرسائل: ترحيب وتسجيل مشتركين جدد فقط"""
    global last_update_id
    updates = get_updates(last_update_id)
    for update in updates:
        last_update_id = update["update_id"] + 1
        if "message" not in update:
            continue

        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        # بيانات العرض
        first_name = msg["chat"].get("first_name", "")
        username = msg["chat"].get("username", "")
        display_name = f"@{username}" if username else first_name

        # تسجيل مستخدم جديد + رسالة الترحيب
        if chat_id not in subscribers:
            subscribers.append(chat_id)
            save_subscribers()
            welcome_message = (
                f"👋 أهلاً بك {display_name}\n\n"
                "هذا بوت التحقق من توفر TDS Video على TestFlight.\n\n"
                "سيقوم البوت بإرسال الروابط تلقائياً عند توفر أماكن شاغرة ✅\n\n"
                "📌 تذكير: يجب تثبيت تطبيق TestFlight لتثبيت التطبيق."
            )
            send_telegram(
                chat_id,
                welcome_message,
                button_url="https://apps.apple.com/app/testflight/id899247664",
                button_text="📥 تحميل TestFlight"
            )
            continue

        # تجاهل أي رسائل أخرى (لا /status ولا /unsubscribe)
        pass

# اعتبار التشغيل الأول كأنه تغيير لو كانت الحالة "متاح"
first_run = True

def check_links():
    global links_status, first_run
    changed = False
    new_available_links = []

    for link in list(links_status.keys()):
        try:
            r = requests.get(link, timeout=15, headers=REQ_HEADERS)
            html = r.text or ""
            # فحص أوسع بقليل من الجملة الحرفية
            is_full = ("beta is full" in html.lower()) or ("this beta is full" in html.lower())
            status = "ممتلئ" if is_full else "متاح"

            # إرسال عند التغير، أو عند التشغيل الأول إذا كان "متاح"
            if links_status[link] != status or (first_run and status == "متاح"):
                changed = True
                if status == "متاح":
                    new_available_links.append(link)

            links_status[link] = status
        except Exception as e:
            print(f"❌ خطأ في الرابط {link}: {e}")

    if changed:
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(links_status, f)
        except Exception as e:
            print(f"❌ خطأ في حفظ الحالة: {e}")

        for link in new_available_links:
            broadcast(f"🚨 رابط متاح الآن:\n{link}", button_url=link, button_text="📥 فتح الرابط")

    # بعد أول فحص ننهي وضع التشغيل الأول
    first_run = False

print("🚀 البوت يعمل... في انتظار أي تغيير")
last_update_id = None

# تفريغ التحديثات القديمة عند الإقلاع حتى لا نكرر الردود
_boot_updates = get_updates()
if _boot_updates:
    last_update_id = _boot_updates[-1]["update_id"] + 1

# أول دورة: سيُعتبر أي رابط "متاح" كأنه تغيّر ويتم إرساله فورًا
while True:
    handle_new_messages()  # متابعة الرسائل الجديدة
    check_links()          # فحص الروابط + إرسال المتاح
    time.sleep(300)        # كل 5 دقائق