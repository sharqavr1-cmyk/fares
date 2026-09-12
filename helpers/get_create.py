import requests
from datetime import datetime, timedelta
from config import r

# ============================================================
# نقاط مرجعية معروفة ( ايدي تقريبي ↔ تاريخ تقريبي ) نستخدمها للاستيفاء
# الخطي ( Linear Interpolation ) بدل التقسيم الخشن القديم اللي كان بيقفز
# بين تواريخ ثابتة لكل مجموعة كبيرة من الايديهات. الاستيفاء بيدي أقرب
# تاريخ ممكن لأي ايدي، مش بس أقرب "مجموعة" كان فيها الايدي.
# أول نقطة ( 14/08/2013 ) هي تاريخ إطلاق تيليجرام الرسمي للعامة.
# ============================================================
ID_DATE_ANCHORS = [
    (1, "14/08/2013"),
    (50_000_000, "15/01/2018"),
    (150_000_000, "10/01/2019"),
    (300_000_000, "14/06/2019"),
    (500_000_000, "22/01/2020"),
    (700_000_000, "05/05/2020"),
    (900_000_000, "18/09/2020"),
    (1_500_000_000, "11/11/2020"),
    (2_500_000_000, "04/04/2021"),
    (5_500_000_000, "19/03/2022"),
    (6_500_000_000, "10/10/2022"),
    (7_500_000_000, "05/11/2023"),
    (9_000_000_000, "05/01/2025"),
]


def _parse(date_str):
    return datetime.strptime(date_str, "%d/%m/%Y")


def _fmt(dt):
    return dt.strftime("%d/%m/%Y")


def backup_creation_date(user_id: int) -> str:
    # دالة تقريبية ( بالاستيفاء الخطي ) في حالة تعطل الـ API
    try:
        uid = int(user_id)
    except Exception:
        return _fmt(datetime.now())

    anchors = ID_DATE_ANCHORS

    if uid <= anchors[0][0]:
        return anchors[0][1]

    if uid >= anchors[-1][0]:
        # استقراء بعد آخر نقطة معروفة بنفس معدل النمو بين آخر نقطتين،
        # وما نتعدى تاريخ اليوم أبداً
        id1, d1 = anchors[-2]
        id2, d2 = anchors[-1]
        dt1, dt2 = _parse(d1), _parse(d2)
        days_per_id = (dt2 - dt1).total_seconds() / max(id2 - id1, 1)
        est = dt2 + timedelta(seconds=(uid - id2) * days_per_id)
        today = datetime.now()
        if est > today:
            est = today
        return _fmt(est)

    for i in range(len(anchors) - 1):
        id1, d1 = anchors[i]
        id2, d2 = anchors[i + 1]
        if id1 <= uid <= id2:
            dt1, dt2 = _parse(d1), _parse(d2)
            ratio = (uid - id1) / (id2 - id1)
            est = dt1 + (dt2 - dt1) * ratio
            return _fmt(est)

    return anchors[-1][1]


def get_creation_date(id: int) -> str:
    try:
        # 1. التحقق من التخزين المؤقت
        cached = r.get(f'{id}:CreateDate')
        if cached:
            return cached.decode('utf-8') if isinstance(cached, bytes) else str(cached)
    except Exception:
        pass

    # 2. محاولة جلب التاريخ من الـ API الخارجي ( أدق مصدر متاح - لو شغال )
    # ملحوظة: الـ API ده اتأكد إنه بيرجع نفس التاريخ الثابت لأي حساب
    # ( يعني عطلان/مقفول وبيرد بنتيجة وهمية بس status 200، مش بيرمي أي
    # استثناء نقدر نمسكه ). فمقفول دلوقتي افتراضياً عشان ميضللناش بتاريخ
    # غلط شكله واثق. لو حبيت تجربه تاني ( بعد ما تتأكد إنه اتصلح أو
    # حصلت على مفتاح API صحيح )، خلي USE_EXTERNAL_API = True تحت.
    USE_EXTERNAL_API = False

    if USE_EXTERNAL_API:
        url = "https://restore-access.indream.app/regdate"
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
            "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
            "accept-language": "en-US,en;q=0.9"
        }
        data = {"telegramId": id}

        for attempt in range(2):
            try:
                res = requests.post(url, headers=headers, json=data, timeout=6)
                if res.status_code == 200:
                    res_data = res.json()
                    if 'data' in res_data and 'date' in res_data['data']:
                        raw_date = res_data['data']['date']  # يأتي غالباً بصيغة YYYY-MM-DD
                        parts = raw_date.split('-')
                        if len(parts) == 3:
                            # إعادة ترتيبه ليكون باليوم والشهر والسنة: DD/MM/YYYY
                            exact_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                        else:
                            exact_date = raw_date.replace('-', '/')

                        # فحص أمان: لو التاريخ اللي رجع بعيد جداً عن تقديرنا
                        # ( أكتر من سنة ونص فرق )، متأكدش ثقة عمياء فيه -
                        # ده بالظبط اللي كان بيحصل لما الـ API كان بيرجع
                        # نفس التاريخ الثابت لكل الحسابات.
                        try:
                            estimate = _parse(backup_creation_date(id))
                            actual = _parse(exact_date)
                            if abs((estimate - actual).days) > 545:
                                raise ValueError("suspicious api date, ignoring")
                        except Exception:
                            break

                        try:
                            r.set(f'{id}:CreateDate', exact_date)
                        except Exception:
                            pass
                        return exact_date
                break
            except Exception:
                continue

    # 3. الخيار الاحتياطي بالاستيفاء الخطي ( أقرب تاريخ ممكن لحد ما نقدر
    # نجيب التاريخ الدقيق من الـ API ). بنحفظه لمدة أسبوع بس عشان لو
    # الـ API رجع يشتغل نجيب منه التاريخ الدقيق بدل التقريبي.
    fallback_date = backup_creation_date(id)
    try:
        r.set(f'{id}:CreateDate', fallback_date, ex=604800)
    except Exception:
        pass

    return fallback_date
