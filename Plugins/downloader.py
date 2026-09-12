# ============================================================
# downloader.py - تحميل للتشغيل (ميوزك) + جلب السجل
# أمرا "يوت" و"تحميل" اتنقلوا لملف music.py - الملف ده دلوقتي بيوفر بس
# دوال التحميل المشتركة (download_for_play وغيرها) اللي music.py بيستخدمها
# ============================================================

import os
import re
import time
import asyncio
import json
import sys
import yt_dlp
from youtube_search import YoutubeSearch
from pyrogram import Client, filters
from telethon.errors import FloodWaitError
from config import *
from helpers.Ranks import *

# ============================================================
# مجلد مخصص لتحميلات الأغاني/الفيديوهات - منفصل تمامًا عن ملفات البوت
# ============================================================
# قبل كده كان yt-dlp بيحفظ الملفات في مجلد الشغل الحالي من غير مسار محدد
# (outtmpl افتراضي)، فكانت بتتحط جنب main.py و config.py وملفات البوت
# نفسها في نفس المجلد. دلوقتي كل تحميل بيروح في مجلد "downloads" منفصل
# جوه جذر المشروع، بعيد تمامًا عن كود البوت.
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# ============================================================
# مسار ثابت (absolute) لملف الكوكيز - المشكلة الأصلية كانت إن الكود بيدور
# على "cookies.txt" بمسار نسبي، واللي بيعتمد على مجلد الشغل (cwd) وقت
# التشغيل. لو البوت بيتشغل بـ systemd/pm2/أي مدير عمليات بيغيّر الـ cwd،
# os.path.exists("cookies.txt") بيرجع False بصمت وبيبقى cookiefile=None
# من غير أي تحذير، فيوت-دي-إل-بي بيحمّل من غير كوكيز خالص، وده اللي بيدي
# "Sign in to confirm you're not a bot" حتى لو الملف موجود فعلاً وسليم.
# دلوقتي بندور على الملف في أكتر من مكان محتمل (جنب هذا الملف نفسه، وفي
# جذر المشروع فوقه)، وبنثبت المسار الكامل مرة واحدة هنا.
def _resolve_cookies_path():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "cookies.txt"),
        os.path.join(os.path.dirname(here), "cookies.txt"),  # جذر المشروع (فوق Plugins)
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def _count_valid_cookies(path):
    """بيعد عدد أسطر الكوكيز الصحيحة (Netscape format) في الملف، عشان نتأكد
    إن الملف مش فاضي أو تالف - ده مختلف عن مجرد وجود الملف على القرص."""
    if not path or not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(
                1 for line in f
                if line.strip() and not line.strip().startswith("#") and "\t" in line
            )
    except Exception:
        return 0

COOKIES_PATH = _resolve_cookies_path()
if COOKIES_PATH:
    _cookie_count = _count_valid_cookies(COOKIES_PATH)
    if _cookie_count > 0:
        print(f"✅ ملف الكوكيز متلاقي: {COOKIES_PATH} (عدد الكوكيز الصحيحة: {_cookie_count})")
    else:
        print(f"⚠️ ملف الكوكيز متلاقي في {COOKIES_PATH} بس فاضي أو الصيغة غلط (0 كوكيز صحيحة)")
else:
    print("⚠️ ملف cookies.txt مش متلاقي في أي مكان متوقع - التحميل هيشتغل من غير كوكيز")

# ============================================================
# Logger مخصص عشان نشوف رسائل yt-dlp الداخلية اللي بتوضح استخدام الكوكيز
# فعليًا (زي "Loaded N cookies") وكذلك سبب فشل الفورمات الحقيقي
# (PO Token / SABR / إلخ) - الرسائل دي عادة بتختفي بسبب quiet=True
# ============================================================
class _YTDLPDiagnosticLogger:
    def debug(self, msg):
        low = msg.lower()
        if any(k in low for k in ("cookie", "po token", "sabr", "sign in", "player_client", "player client")):
            print(f"[yt-dlp] {msg}")

    def warning(self, msg):
        print(f"[yt-dlp warning] {msg}")

    def error(self, msg):
        print(f"[yt-dlp error] {msg}")

_ytdlp_diagnostic_logger = _YTDLPDiagnosticLogger()

# ============================================================
# استيراد من music.py (تجنب circular import)
# ============================================================
def get_music_module():
    return sys.modules.get('Plugins.music')

def get_bot_cache():
    mod = get_music_module()
    if mod:
        return mod.bot_cache, mod.save_cache
    return None, None

def get_assistant():
    mod = get_music_module()
    if mod and hasattr(mod, 'get_assistant'):
        return mod.get_assistant()
    return None, None, None

# ===== المتغيرات =====

# ============================================================
# تحميل بالتجربة على أكثر من نتيجة لو فيه فيديو محظور/متاح في بلد تاني
# ============================================================
UNAVAILABLE_MARKERS = (
    "video is not available",
    "video unavailable",
    "private video",
    "this video is unavailable",
    "removed by the user",
    "requested format is not available",
    "sign in to confirm",
    # ===== خطأ يوتيوب/يوت-دي-إل-بي شائع ومؤقت هذه الأيام تحديدًا مع
    # الفورمات اللي بتتطلب كوكيز (tv/web_safari) - بيظهر بشكل متقطع
    # ومش له علاقة بتوفر الفيديو نفسه. لو ضفناه هنا، أي فيديو يجيبه
    # هيتم تخطيه لمحاولة "الزيارة كضيف" (بدون كوكيز) على نفس الفيديو -
    # وده غالبًا بيعدي عادي لأن المشكلة مرتبطة بالكوكيز بالذات - وبعدين
    # لباقي نتائج البحث لو لسه مش راضي يعدي. من غيره، الخطأ ده كان
    # بيوقف التحميل بالكامل فورًا من غير ما يجرب أي بديل خالص.
    "the page needs to be reloaded",
    "please reload this page",
)

def _build_guest_ydl_ops(base_ops):
    """نسخة بديلة 'زائر' بدون كوكيز خالص. لو الحظر (SABR-only) مرتبط
    بالحساب المسجل بالكوكيز بالذات، زيارة كضيف (من غير تسجيل دخول)
    ممكن تتفادى الحظر ده لأنه غير مرتبط بحساب معين."""
    guest_ops = dict(base_ops)
    guest_ops["cookiefile"] = None
    guest_ops["extractor_args"] = {"youtube": {"player_client": ["android", "web", "mweb"]}}
    return guest_ops

def extract_info_with_fallback(ydl_ops, results):
    """
    بتاخد قائمة نتائج بحث (من YoutubeSearch) وتجرب تحمّل أول واحد شغال.
    لكل فيديو، بتجرب أولاً بالكوكيز (الحساب المسجل)، ولو فشل بسبب
    SABR/فورمات غير متاح، بتجرب "زيارة ضيف" بدون كوكيز على نفس الفيديو
    قبل ما تتخطاه للفيديو اللي بعده. بترجع (info, ydl, res) لأول محاولة
    نجحت، أو (None, None, None).
    """
    last_err = None
    guest_ops = _build_guest_ydl_ops(ydl_ops)
    for res in results:
        vid_id = res["id"]
        url = f"https://youtu.be/{vid_id}"
        for attempt_ops, label in ((ydl_ops, "بالكوكيز"), (guest_ops, "كضيف")):
            try:
                ydl = yt_dlp.YoutubeDL(attempt_ops)
                info = ydl.extract_info(url, download=False)
                return info, ydl, res
            except yt_dlp.utils.DownloadError as e:
                msg = str(e).lower()
                last_err = e
                if any(marker in msg for marker in UNAVAILABLE_MARKERS):
                    print(f"[Skip {label}] {vid_id}: {e}")
                    continue
                # خطأ من نوع تاني (نت، إلخ) - نوقف ونرجع الخطأ
                raise
    if last_err:
        raise last_err
    return None, None, None

def time_to_seconds(time_str):
    try:
        return sum(int(x) * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))
    except:
        return 0

# ============================================================
# البحث في يوتيوب بيعمل طلب شبكة متزامن (blocking) زي extract_info -
# لازم يتلف في Thread منفصل زيه بالظبط، وإلا بيوقف الـ event loop
# بتاع البوت كله (كل الجروبات) لحد ما نتيجة البحث ترجع. ده كان السبب
# الحقيقي وراء "البوت بيوقف وهو بيدور" - مش التحميل نفسه.
# ============================================================
async def yt_search_async(query, max_results=5):
    return await asyncio.to_thread(lambda: YoutubeSearch(query, max_results=max_results).to_dict())

# ============================================================
# فحص سلامة الملف المُحمّل - عشان ما نضيفش للطابور أو نبلّغ نجاح
# لو التحميل جه ناقص/فاضي/تالف
# ============================================================
MIN_VALID_FILE_SIZE = 20 * 1024  # 20KB - أقل حجم منطقي لملف صوت/فيديو سليم

def _is_valid_downloaded_file(path):
    try:
        return bool(path) and os.path.exists(path) and os.path.getsize(path) >= MIN_VALID_FILE_SIZE
    except Exception:
        return False

def _cleanup_invalid_file(path):
    if path and os.path.exists(path):
        try: os.remove(path)
        except: pass

def _is_path_still_needed(file_path):
    """يتأكد ان الملف ده لسه محجوز لتشغيل حالي أو موجود في طابور أي مجموعة،
    عشان upload_to_storage ما يمسحوش الملف من تحت رجل التشغيل قبل ما ياخد دوره.
    بيفحص path و original_path مع بعض، لأن original_path بيفضل هو المرجع
    الأساسي اللي التمرير (seek) بيعتمد عليه حتى بعد ما path يتغير لملف مؤقت."""
    if not file_path:
        return False
    mod = get_music_module()
    if not mod:
        return False
    try:
        for track in getattr(mod, 'current_playing', {}).values():
            if track and (track.get('path') == file_path or track.get('original_path') == file_path):
                return True
        for queue in getattr(mod, 'music_queue', {}).values():
            for track in queue:
                if track.get('path') == file_path or track.get('original_path') == file_path:
                    return True
    except Exception:
        pass
    return False

# ============================================================
# دالة مساعدة - البحث في قناة التخزين (ترجع msg_id بس)
# ============================================================

async def find_in_storage_channel(vid_id, is_video=False):
    """
    تبحث عن الملف في قناة التخزين باستخدام:
    1. bot_cache (الأسرع)
    2. البحث المباشر في القناة (Telethon search)
    ترجع: message_id (int) أو None
    """
    bot_cache, save_cache = get_bot_cache()
    cache_key_type = "video" if is_video else "audio"
    target = f"@{STORAGE_CHANNEL}"
    
    call_py, assistant_id, assistant_client = get_assistant()
    if not assistant_client:
        return None
    
    # 1. البحث في bot_cache
    if bot_cache and bot_cache.get(cache_key_type, {}).get(vid_id):
        msg_id = bot_cache[cache_key_type][vid_id]
        try:
            # Telethon get_messages بيرجع TotalList (list) — لازم [0]
            result = await assistant_client.get_messages(target, msg_id)
            msg = result[0] if result else None
            has_right_type = msg and (msg.video if is_video else (msg.audio or msg.document))
            if has_right_type:
                # في Telethon: msg.text = caption
                caption = (msg.text or "").strip()
                if caption == vid_id:
                    return msg_id
        except Exception as e:
            print(f"[Cache Lookup Error] {e}")
    
    # 2. البحث المباشر في القناة بالمساعد (Telethon)
    try:
        async for msg in assistant_client.iter_messages(target, search=vid_id, limit=20):
            if not msg:
                continue
            # لازم نوع الميديا يطابق المطلوب بالتحديد (فيديو لو is_video، صوت
            # لو مش كذلك) - قبل كده كان بيقبل أي نوع ميديا بالكابشن بس، فلو
            # الفيديو كان محفوظ كصوت بس، كان "بيتلاقى" هنا بس يفشل بعد كده
            # في مطابقة النوع الفعلي، فيرجع يحمل من يوتيوب من الصفر كل مرة
            has_right_type = msg.video if is_video else (msg.audio or msg.document)
            if not has_right_type:
                continue
            
            # في Telethon: msg.text = caption
            caption = (msg.text or "").strip()
            if caption == vid_id:
                # تحديث bot_cache
                if bot_cache is not None:
                    bot_cache.setdefault(cache_key_type, {})
                    bot_cache[cache_key_type][vid_id] = msg.id
                    if save_cache:
                        save_cache()
                
                return msg.id
                
    except Exception as e:
        print(f"[Channel Search Error] {e}")
    
    return None

# ============================================================
# 1. دالة التحميل للتشغيل (ميوزك) - وأمري "يوت"/"تحميل" في music.py
# بيستخدموها هي كمان (get_downloader) بدل ما يكرروا نفس منطق التحميل
# ============================================================

PROGRESSIVE_MIN_SIZE = 15 * 1024 * 1024  # 15 ميجا - نفس الحد المستخدم مع تحميل يوتيوب

async def _progressive_download_media(client, media, file_path):
    """
    بينزل أي ميديا من تليجرام (كاش Redis، قناة تخزين، رد على ملف) في
    الخلفية، وبيرجع فورًا بعد أول 1% (أو 300 كيلو، أيًا كان أكبر) لو حجم
    الملف أكبر من 15 ميجا - عشان التشغيل يبدأ على طول من غير ما نستنى
    التحميل الكامل. الملفات الأصغر بتستني التحميل الكامل عادي لأنها
    سريعة كفاية أصلاً. بترجع (file_path, download_task).
    """
    loop = asyncio.get_event_loop()
    ready_event = asyncio.Event()

    def _progress(current, total):
        if ready_event.is_set():
            return
        if total and total > PROGRESSIVE_MIN_SIZE:
            threshold = max(total * 0.01, 300 * 1024)
            if current >= threshold:
                loop.call_soon_threadsafe(ready_event.set)

    async def _do_download():
        try:
            return await client.download_media(media, file_name=file_path, progress=_progress)
        finally:
            loop.call_soon_threadsafe(ready_event.set)

    download_task = asyncio.create_task(_do_download())

    try:
        await asyncio.wait_for(ready_event.wait(), timeout=25)
    except asyncio.TimeoutError:
        pass

    return file_path, download_task

async def download_for_play(client, query, is_video=False, direct_result=None):
    """
    بترجع (file_path, title, info, download_task).

    download_task بيكون None لو الملف رجع كامل وجاهز فعلاً (من Redis أو من
    قناة التخزين). لو الملف بينزل من يوتيوب وحجمه أكبر من 15 ميجا، الدالة
    بترجع بعد أول 1% بس (أو 300 كيلو، أيًا كان أكبر) عشان التشغيل يبدأ
    فورًا من غير ما نستنى التحميل الكامل، والباقي بينزل في الخلفية عن
    طريق download_task. الملفات الأصغر من 15 ميجا بتستني التحميل الكامل
    زي الأول لأنها سريعة كفاية أصلاً.
    """
    try:
        if direct_result:
            results = [direct_result]
        else:
            results = await yt_search_async(query, max_results=5)
            if not results:
                return None, None, None, None

        res = results[0]
        vid_id = res["id"]
        title = res["title"]
        duration_str = res.get("duration", "0:00")
        duration = time_to_seconds(duration_str)

        cache_key = f"yt_{'video' if is_video else 'audio'}_{vid_id}"

        # 1. البحث في Redis
        if r.get(cache_key):
            file_id = r.get(cache_key)
            ext = "mp4" if is_video else "mp3"
            file_path, dl_task = await _progressive_download_media(
                client, file_id, f"downloads/cached_{vid_id}.{ext}"
            )
            if _is_valid_downloaded_file(file_path):
                return file_path, title, {"id": vid_id, "duration": duration, "duration_str": duration_str}, dl_task
            _cleanup_invalid_file(file_path)

        # 2. البحث في قناة التخزين (بيرجع msg_id)
        msg_id = await find_in_storage_channel(vid_id, is_video=is_video)
        if msg_id:
            try:
                pyro_msg = await client.get_messages(f"@{STORAGE_CHANNEL}", msg_id)
                if pyro_msg:
                    media = pyro_msg.video if is_video else (pyro_msg.audio or pyro_msg.document)
                    if media:
                        ext = "mp4" if is_video else "mp3"
                        file_path, dl_task = await _progressive_download_media(
                            client, media, f"downloads/cached_{vid_id}.{ext}"
                        )
                        if _is_valid_downloaded_file(file_path):
                            r.set(cache_key, media.file_id)
                            return file_path, title, {"id": vid_id, "duration": duration, "duration_str": duration_str}, dl_task
                        _cleanup_invalid_file(file_path)
            except Exception as e:
                print(f"[Storage Download Error] {e}")

        # 3. تحميل من يوتيوب (بيتخطى أي نتيجة محظورة/غير متاحة)
        common_ops = {
            "forceduration": True,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": COOKIES_PATH,
            "js_runtimes": {"deno": {}},
            "extractor_retries": 1,
            "socket_timeout": 8,
            "logger": _ytdlp_diagnostic_logger,
            "verbose": True,
            "remote_components": {"ejs:github"},
            # عميلا tv/web_safari بقى ليهم مشكلة نشطة موثقة في yt-dlp نفسها
            # هذه الأيام تحديدًا لما بيتبعتوا مع كوكيز - بيرجعوا خطأ
            # "The page needs to be reloaded" بشكل شبه دائم (SABR-only،
            # مفيش حل نهائي من عند yt-dlp لسه). فريق yt-dlp نفسه بينصح
            # لما تستخدم كوكيز إنك تستخدم "default,web_embedded" بدالهم
            # (github.com/yt-dlp/yt-dlp/issues/17389) - ده اللي بنعمله هنا
            "extractor_args": {"youtube": {"player_client": ["default", "web_embedded"]}},
            "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s [%(id)s].%(ext)s"),
            # يكتب على اسم الملف النهائي من أول بايت (من غير .part مؤقت) -
            # ضروري عشان نقدر نبدأ تشغيله وهو لسه بينزل في الخلفية
            "nopart": True,
            # ===== منع "استكمال تحميل" (resume) بريكوست Range =====
            # لو فيه ملف قديم متبقي على نفس الاسم (من محاولة سابقة اتقطعت،
            # أو retry بعد فشل مؤقت)، yt-dlp بمحاولة "يكمل" منه بطلب
            # Range: bytes=<حجم الملف الحالي>- . لو السيرفر مابيدعمش
            # الاستكمال على الرابط ده، أو الملف كان أصلاً مكتمل/أكبر من
            # الحجم الحقيقي، السيرفر بيرفض بخطأ 416 (Requested range not
            # satisfiable) وده اللي كان بيحصل مع بعض المقاطع بس مش كلها.
            # تعطيل الاستكمال هنا بيخلي كل تحميل يبدأ نضيف من الصفر ويكتب
            # فوق أي ملف قديم، فمفيش أي طلب Range خالص ومفيش 416.
            "continuedl": False,
            "overwrites": True,
        }
        if is_video:
            ydl_ops = {
                "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
                "merge_output_format": "mp4",
                **common_ops,
            }
        else:
            ydl_ops = {
                "format": "bestaudio/best",
                **common_ops,
            }

        # ===== تتبع تقدم التحميل عشان نبدأ التشغيل بعد أول 1% لو الملف كبير =====
        loop = asyncio.get_event_loop()
        ready_event = asyncio.Event()
        PROGRESSIVE_MIN_SIZE = 15 * 1024 * 1024  # 15 ميجا

        def _progress_hook(d):
            if ready_event.is_set():
                return
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > PROGRESSIVE_MIN_SIZE:
                    threshold = max(total * 0.01, 300 * 1024)  # 1% أو 300 كيلو، أيًا كان أكبر
                    if downloaded >= threshold:
                        loop.call_soon_threadsafe(ready_event.set)
            elif status == "finished":
                loop.call_soon_threadsafe(ready_event.set)

        ydl_ops["progress_hooks"] = [_progress_hook]

        # البحث عن الفورمات وجلب معلومات الفيديو (extract_info) بيعمل طلبات
        # شبكة حقيقية بيتنفذوا بشكل متزامن (blocking) - بنشغلها في Thread
        # منفصل عشان ما توقفش حلقة الأحداث كلها لحد ما تخلص
        try:
            info, ydl, picked_res = await asyncio.to_thread(extract_info_with_fallback, ydl_ops, results)
        except yt_dlp.utils.DownloadError as e:
            print(f"[Download Error] {e}")
            info = None

        # لو كان معنا نتيجة واحدة بس (direct_result) وفشلت، مفيش نسخ تانية
        # جربناها لسه - ندور بعنوانها على 2-3 نسخ تانية من نفس الفيديو
        # ونجرب عليهم قبل ما نستسلم خالص
        if info is None and direct_result:
            alt_results = await yt_search_async(title, max_results=4)
            alt_results = [r2 for r2 in alt_results if r2["id"] != vid_id][:3]
            if alt_results:
                try:
                    info, ydl, picked_res = await asyncio.to_thread(extract_info_with_fallback, ydl_ops, alt_results)
                except yt_dlp.utils.DownloadError as e:
                    print(f"[Download Error - alt titles] {e}")
                    info = None

        if info is None:
            return None, None, None, None

        if picked_res["id"] != vid_id:
            vid_id = picked_res["id"]
            title = picked_res["title"]
            duration_str = picked_res.get("duration", "0:00")
            duration = time_to_seconds(duration_str)
            cache_key = f"yt_{'video' if is_video else 'audio'}_{vid_id}"

        file_path = ydl.prepare_filename(info)
        download_error = {"exc": None}

        def _blocking_download():
            with ydl:
                ydl.process_info(info)

        async def _finish_download():
            # ده بيشغل التحميل الفعلي (اللي محتاج وقت) في Thread منفصل، عشان
            # لا يوقف حلقة الأحداث ولا يوقف تشغيل الأغنية اللي بدأت بالفعل
            try:
                await asyncio.to_thread(_blocking_download)
            except Exception as e:
                download_error["exc"] = e
                print(f"[Background Download Error] {e}")
            finally:
                loop.call_soon_threadsafe(ready_event.set)

            if download_error["exc"] is not None:
                return
            if not _is_valid_downloaded_file(file_path):
                _cleanup_invalid_file(file_path)
                return
            # رفع للتخزين - بعد التأكد من اكتمال التحميل فعليًا لحد آخره
            asyncio.create_task(upload_to_storage(client, file_path, vid_id, title, duration_str, is_video))

        download_task = asyncio.create_task(_finish_download())

        # ننتظر لغاية أول 1% (للملفات الكبيرة) أو التحميل الكامل (الملفات
        # الصغيرة بتخلص بسرعة أصلاً فبتوصل لـ "finished" بسرعة). حد أقصى
        # 25 ثانية استعداداً لأي ظرف غريب عشان منستناش للأبد
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=25)
        except asyncio.TimeoutError:
            pass

        if download_error["exc"] is not None:
            return None, None, None, None

        if not os.path.exists(file_path) or os.path.getsize(file_path) <= 0:
            return None, None, None, None

        return file_path, title, {"id": vid_id, "duration": duration, "duration_str": duration_str}, download_task

    except Exception as e:
        print(f"[Download Error] {e}")
        return None, None, None, None

# ============================================================
# 3. رفع الملفات إلى قناة التخزين (send_audio / send_video)
# ============================================================

async def _normalize_for_storage(file_path, is_video, suffix="_std"):
    """
    بيحوّل الملف لصيغة قياسية متوافقة مع الكل - فيديو H.264/AAC جوه MP4،
    وصوت MP3 - بغض النظر عن الصيغة اللي يوتيوب رجعها فعليًا (ممكن تكون
    VP9/AV1/Opus/webm إلخ بسبب قيود SABR على عملاء يوتيوب المتاحة).
    التشغيل المباشر في المكالمة مش محتاج للتحويل ده لأن pytgcalls بيحوّل
    أي صيغة أونلاين بنفسه وقت البث، فبنعمل التحويل ده بس للنسخة اللي
    هتترسل للمستخدم مباشرة (أمري "يوت"/"تحميل") أو هترفع لقناة التخزين.
    `suffix` بيتحدد لكل استخدام عشان لو نفس الملف بيتحول لغرضين مختلفين
    في نفس الوقت (إرسال للمستخدم + رفع للتخزين في الخلفية)، كل واحد
    يكتب لملف مؤقت باسم مختلف، من غير ما يتصادموا على نفس الملف.
    بيرجع مسار الملف المحوّل (ملف جديد)، أو نفس المسار الأصلي لو التحويل فشل.
    """
    base, _ = os.path.splitext(file_path)
    out_path = base + (f"{suffix}.mp4" if is_video else f"{suffix}.mp3")

    if is_video:
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-vn", "-c:a", "libmp3lame", "-b:a", "192k",
            out_path,
        ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
        print(f"[Normalize] فشل تحويل {file_path} (returncode={proc.returncode}) - هيترفع زي ما هو")
    except Exception as e:
        print(f"[Normalize Error] {e}")

    return file_path  # التحويل فشل - نرفع النسخة الأصلية زي ما هي بدل ما نفشل خالص

async def upload_to_storage(client, file_path, vid_id, title, duration_str, is_video):
    try:
        if not os.path.exists(file_path):
            return

        cache_key = f"yt_{'video' if is_video else 'audio'}_{vid_id}"
        cache_key_type = "video" if is_video else "audio"
        
        # التحقق من عدم وجودها في Redis
        if r.get(cache_key):
            if not _is_path_still_needed(file_path):
                try: os.remove(file_path)
                except: pass
            return

        # التحقق من عدم وجودها في القناة (bot_cache)
        bot_cache, save_cache = get_bot_cache()
        if bot_cache and bot_cache.get(cache_key_type, {}).get(vid_id):
            if not _is_path_still_needed(file_path):
                try: os.remove(file_path)
                except: pass
            return

        target = f"@{STORAGE_CHANNEL}"

        # ===== تحويل لصيغة قياسية قبل الرفع (مش قبل التشغيل المباشر) =====
        upload_path = await _normalize_for_storage(file_path, is_video)

        if is_video:
            storage_msg = await client.send_video(
                chat_id=target,
                video=upload_path,
                caption=vid_id  # فقط الـ YouTube ID
            )
            file_id = storage_msg.video.file_id
        else:
            dur_sec = time_to_seconds(duration_str)
            storage_msg = await client.send_audio(
                chat_id=target,
                audio=upload_path,
                caption=vid_id,  # فقط الـ YouTube ID
                title=title,
                performer="YouTube",
                duration=dur_sec
            )
            file_id = storage_msg.audio.file_id

        # نمسح نسخة التحويل المؤقتة (لو اتعملت فعلاً وكانت مختلفة عن الأصلية)
        if upload_path != file_path:
            try: os.remove(upload_path)
            except: pass
        
        r.set(cache_key, file_id)
        
        if bot_cache is not None:
            bot_cache.setdefault(cache_key_type, {})
            bot_cache[cache_key_type][vid_id] = storage_msg.id
            if save_cache:
                save_cache()

        # ===== ما نمسحش الملف المحلي لو لسه محجوز لتشغيل حالي أو في الطابور =====
        # ده كان سبب مشكلة "الحساب بينزل والبوت بيوقف": كان بيتمسح فور الرفع
        # حتى لو الأغنية لسه مستنية دورها في الطابور، فلما ييجي دورها الملف
        # يكون اتمسح خلاص ويفشل التشغيل. التنظيف دلوقتي بيحصل من play_next
        # نفسها بعد ما الأغنية تاخد دورها وتخلص فعلياً.
        if not _is_path_still_needed(file_path):
            try: os.remove(file_path)
            except: pass

    except Exception as e:
        print(f"[Upload Error] {e}")
