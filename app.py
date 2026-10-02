import io
import urllib.request
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# مكتبات معالجة وتشكيل النص العربي للـ PDF
import arabic_reshaper
from bidi.algorithm import get_display

# مكتبات ReportLab لتوليد ملفات الـ PDF
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ----------------------------------------------------
# 1. تحميل الخط العربي المعتمد
# ----------------------------------------------------
FONT_PATH = "Amiri-Regular.ttf"
if not os.path.exists(FONT_PATH):
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        urllib.request.urlretrieve(url, FONT_PATH)
    except Exception:
        pass

# ----------------------------------------------------
# 2. إدارة عداد الزوار
# ----------------------------------------------------
VISITOR_FILE = "visitor_count.txt"

def get_and_update_visitor_count():
    count = 0
    if os.path.exists(VISITOR_FILE):
        try:
            with open(VISITOR_FILE, "r") as f:
                count = int(f.read().strip())
        except Exception:
            count = 0
    if 'visited_session' not in st.session_state:
        count += 1
        st.session_state.visited_session = True
        with open(VISITOR_FILE, "w") as f:
            f.write(str(count))
    return count

visitor_number = get_and_update_visitor_count()

# ----------------------------------------------------
# 3. إعدادات الصفحة والتصميم المتجاوب مع الهواتف (Mobile CSS)
# ----------------------------------------------------
st.set_page_config(
    page_title="برنامج إدارة غيابات الطلبة ومفردات المواد وطلبات الغياب",
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 16px 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        position: relative;
    }
    
    .main-header h2 {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
    }

    .visitor-badge {
        background-color: rgba(255, 255, 255, 0.2);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        display: inline-block;
        margin-top: 8px;
        border: 1px solid rgba(255, 255, 255, 0.4);
    }

    .notice-box {
        background-color: #eef2f7;
        border-right: 4px solid #1e3c72;
        padding: 10px 15px;
        border-radius: 6px;
        font-weight: 600;
        color: #1e3c72;
        margin-bottom: 12px;
    }

    div[data-testid="stDataFrame"] {
        direction: rtl !important;
        text-align: right !important;
    }

    .stDownloadButton > button, .stButton > button {
        width: 100%;
        background-color: #1e3c72;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        padding: 10px;
        border: none;
        font-size: 15px;
        transition: background-color 0.3s;
    }

    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #2a5298;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: bold;
    }

    .external-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 25px;
        text-align: center;
        margin-top: 15px;
    }

    /* ------------------------------------------------ */
    /* 📱 تحسينات استجابة الجوال والشاشات الصغيرة (Mobile CSS) */
    /* ------------------------------------------------ */
    @media (max-width: 768px) {
        .main-header {
            padding: 12px 10px !important;
            border-radius: 8px !important;
        }
        .main-header h2 {
            font-size: 16px !important;
        }
        .visitor-badge {
            font-size: 11px !important;
            padding: 4px 10px !important;
        }
        
        /* مرونة التبويب للهاتف */
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap !important;
            gap: 4px !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 12px !important;
            padding: 8px 10px !important;
            height: auto !important;
            flex-grow: 1;
            text-align: center;
        }

        /* تحسين الأزرار وحقول الإدخال للمس */
        .stButton > button, .stDownloadButton > button {
            padding: 12px !important;
            font-size: 15px !important;
            margin-top: 6px;
        }
        
        div[data-testid="stForm"] {
            padding: 10px !important;
        }
        
        .notice-box {
            font-size: 13px !important;
            padding: 8px 10px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. القوائم وقواعد البيانات والكلمات السرية
# ----------------------------------------------------
DAYS_LIST = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
TIMES_LIST = [
    "08:00 - 09:30",
    "09:30 - 11:00",
    "11:00 - 12:30",
    "12:30 - 14:00",
    "14:00 - 15:30"
]
ROOMS_LIST = [f"القاعة {i}" for i in range(5, 17)] + [f"القاعة {i}" for i in range(21, 25)] + ["المدرج أ", "المدرج ب", "المدرج ج", "المدرج د"]
GROUPS_LIST = ["الفوج 01", "الفوج 02", "الفوج 03", "الفوج 04"]
STAGES_LIST = ["ليسانس", "ماستر"]
YEARS_LIST = ["الأولى", "الثانية", "الثالثة"]
SPECIALTIES_LIST = [
    "جذع مشترك", "دراسات لغوية", "دراسات أدبية", "نقد ومناهج",
    "لسانيات عامة", "لسانيات تطبيقية", "أدب حديث ومعاصر", "نقد حديث ومعاصر", "أدب شعبي"
]

RANKS_LIST = [
    "أستاذ تعليم عال", "أستاذ محاضر أ", "أستاذ محاضر ب", 
    "أستاذ مساعد أ", "أستاذ مساعد ب", "أستاذ متعاقد"
]
REASON_LIST = ["عطلة مرضية", "ظرف عائلي", "ملتقى", "اجتماع", "دعوة", "سبب آخر"]
COMPENSATION_LIST = ["غياب مع التعويض", "غياب من دون تعويض"]

# كلمة مرور رئيس القسم
if 'dept_password' not in st.session_state:
    st.session_state.dept_password = "1234"

# قاعدة بيانات طلبات الغياب
DB_REQUESTS_FILE = 'absence_requests.xlsx'

def load_absence_requests():
    if os.path.exists(DB_REQUESTS_FILE):
        try:
            return pd.read_excel(DB_REQUESTS_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "رقم_الطلب", "اسم_الأستاذ", "الرتبة", "مدة_الغياب", 
        "التاريخ", "التعويض", "السبب", "السبب_التفصيلي", 
        "تاريخ_التقديم", "الحالة"
    ])

def save_absence_requests(df):
    df.to_excel(DB_REQUESTS_FILE, index=False)

if 'db_requests' not in st.session_state:
    st.session_state.db_requests = load_absence_requests()

# ----------------------------------------------------
# 5. الدوال المساعدة وتوليد ملفات PDF
# ----------------------------------------------------
def smart_name_match(name1, name2):
    if pd.isna(name1) or pd.isna(name2):
        return False
    words1 = set(str(name1).strip().split())
    words2 = set(str(name2).strip().split())
    return words1 == words2 and len(words1) > 0

def fix_arabic(text):
    if not text or pd.isna(text):
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

def create_pdf(teacher_name, session_info):
    buffer = io.BytesIO()
    ignored_keys = ['اسم الأستاذ', 'الرقم', 'رقم', 'الرقم التسلسلي', 'id', 'ID', 'no', 'No', 'الرقم السري', 'اليوم', 'التوقيت', 'القاعة', 'المكان', 'تاريخ']
    items = [
        (key, val) for key, val in session_info.items()
        if key not in ignored_keys and not any(k in str(key) for k in ['الرقم', 'رقم'])
    ]

    width = 420
    header_height = 140
    title_height = 35
    teacher_line_height = 20
    fields_height = len(items) * 18
    footer_height = 80
    height = header_height + title_height + teacher_line_height + fields_height + footer_height

    c = canvas.Canvas(buffer, pagesize=(width, height))
    font_name = 'ArabicFont' if os.path.exists(FONT_PATH) else 'Helvetica'
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('ArabicFont', FONT_PATH))

    c.setFont(font_name, 9)
    c.drawCentredString(width / 2, height - 25, fix_arabic("الجمهورية الجزائرية الديمقراطية الشعبية"))
    c.drawCentredString(width / 2, height - 39, fix_arabic("وزارة التعليم العالي والبحث العلمي"))
    c.drawCentredString(width / 2, height - 53, fix_arabic("جامعة الوادي"))

    c.drawRightString(width - 25, height - 69, fix_arabic("كلية الآداب واللغات"))
    c.drawString(25, height - 69, fix_arabic("السنة الجامعية: 2026-2027"))
    c.drawRightString(width - 25, height - 81, fix_arabic("قسم اللغة والأدب العربي"))

    title_y = height - 110
    c.setFont(font_name, 13)
    c.drawCentredString(width / 2, title_y, fix_arabic("تقرير غياب جماعي للطلبة"))

    c.setFont(font_name, 9.5)
    y_pos = title_y - 25
    c.drawRightString(width - 25, y_pos, fix_arabic("لقد سجلنا غياباً جماعياً للطلبة وفقاً للمعلومات الآتية:"))
    
    y_pos -= 18
    c.drawRightString(width - 25, y_pos, fix_arabic(f"• أستاذ المادة: {teacher_name}"))

    for key, val in items:
        y_pos -= 18
        c.drawRightString(width - 25, y_pos, fix_arabic(f"• {key}: {val}"))

    y_pos -= 30
    doc_date = session_info.get("التاريخ", datetime.now().strftime("%Y-%m-%d"))
    c.drawString(25, y_pos, fix_arabic(f"حرر بتاريخ: {doc_date}"))

    y_pos -= 20
    c.drawString(25, y_pos, fix_arabic("توقيع الأستاذ(ة):"))

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def create_absence_request_pdf(req_row):
    """توليد ملف PDF لطلب الغياب المعتمد"""
    buffer = io.BytesIO()
    width = 420
    height = 550

    c = canvas.Canvas(buffer, pagesize=(width, height))
    font_name = 'ArabicFont' if os.path.exists(FONT_PATH) else 'Helvetica'
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('ArabicFont', FONT_PATH))

    c.setFont(font_name, 9)
    c.drawCentredString(width / 2, height - 25, fix_arabic("الجمهورية الجزائرية الديمقراطية الشعبية"))
    c.drawCentredString(width / 2, height - 39, fix_arabic("وزارة التعليم العالي والبحث العلمي"))
    c.drawCentredString(width / 2, height - 53, fix_arabic("جامعة الوادي"))

    c.drawRightString(width - 25, height - 69, fix_arabic("كلية الآداب واللغات"))
    c.drawString(25, height - 69, fix_arabic("السنة الجامعية: 2026-2027"))
    c.drawRightString(width - 25, height - 81, fix_arabic("قسم اللغة والأدب العربي"))

    title_y = height - 120
    c.setFont(font_name, 14)
    c.drawCentredString(width / 2, title_y, fix_arabic("طلب غياب"))

    y_pos = title_y - 35
    c.setFont(font_name, 10.5)
    c.drawRightString(width - 25, y_pos, fix_arabic(f"الأستاذ(ة): {req_row['اسم_الأستاذ']}"))
    y_pos -= 18
    c.drawRightString(width - 25, y_pos, fix_arabic(f"الرتبة العلمية: {req_row['الرتبة']}"))

    y_pos -= 35
    c.setFont(font_name, 11)
    c.drawRightString(width - 25, y_pos, fix_arabic("إلى السيد المحترم: رئيس القسم"))
    
    y_pos -= 25
    c.setFont(font_name, 10)
    c.drawRightString(width - 25, y_pos, fix_arabic("أتقدم إليكم بطلب الموافقة على غيابي عن التدريس نظراً لارتباطي بالظرف المحدد والمبين أدناه:"))

    y_pos -= 25
    c.drawRightString(width - 35, y_pos, fix_arabic(f"• مدة الغياب: {req_row['مدة_الغياب']}"))
    y_pos -= 18
    c.drawRightString(width - 35, y_pos, fix_arabic(f"• التاريخ / الفترة: {req_row['التاريخ']}"))
    y_pos -= 18
    c.drawRightString(width - 35, y_pos, fix_arabic(f"• تحديد طبيعة الغياب: {req_row['التعويض']}"))
    
    reason_str = req_row['السبب']
    if pd.notna(req_row['السبب_التفصيلي']) and str(req_row['السبب_التفصيلي']).strip():
        reason_str += f" ({req_row['السبب_التفصيلي']})"
    
    y_pos -= 18
    c.drawRightString(width - 35, y_pos, fix_arabic(f"• سبب الغياب: {reason_str}"))

    y_pos -= 50
    current_date = datetime.now().strftime("%Y-%m-%d")
    c.drawString(30, y_pos, fix_arabic(f"حرر بتاريخ: {current_date}"))
    y_pos -= 20
    c.drawString(30, y_pos, fix_arabic("إمضاء الأستاذ(ة):"))

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ----------------------------------------------------
# 6. الواجهة الرئيسية للبرنامج
# ----------------------------------------------------
st.markdown(f"""
    <div class="main-header">
        <h2>برنامج إدارة غيابات الطلبة ومفردات المواد وطلبات الغياب</h2>
        <div class="visitor-badge">👤 عدد زوار المنصة: {visitor_number}</div>
    </div>
""", unsafe_allow_html=True)

try:
    df_teachers = pd.read_excel('teachers.xlsx')
    df_teachers.columns = df_teachers.columns.astype(str).str.strip()
    teacher_col = df_teachers.columns[0]
    pass_col = df_teachers.columns[1]
    teachers_list = df_teachers[teacher_col].dropna().astype(str).str.strip().unique().tolist()
except Exception:
    df_teachers = None
    teachers_list = []

tab_regular, tab_contract, tab_syllabus, tab_absence_req = st.tabs([
    "👨‍🏫 تقرير غياب خاص بالأستاذ المرسم", 
    "📝 تقرير غياب خاص بالأستاذ المتعاقد", 
    "📚 مفردات مواد عروض التكوين المحيّنة",
    "📩 طلب غياب"
])

# ====================================================
# التبويب الأول: تقرير غياب خاص بالأستاذ المرسم
# ====================================================
with tab_regular:
    try:
        df_sessions = pd.read_excel('sessions.xlsx')
        df_sessions.columns = df_sessions.columns.astype(str).str.strip()
    except Exception:
        st.error("⚠ يتعذر قراءة ملف الحصص 'sessions.xlsx'.")
        st.stop()

    session_teacher_col = [c for c in df_sessions.columns if 'أستاذ' in c or 'الاستاذ' in c or 'اسم' in c]
    session_teacher_key = session_teacher_col[0] if session_teacher_col else df_sessions.columns[0]

    c1, c2, c3 = st.columns([2, 2, 1])

    with c1:
        selected_teacher = st.selectbox("اسم الأستاذ:", ["-- اختر الاسم --"] + teachers_list, key="reg_teacher")
    with c2:
        password_input = st.text_input("الرقم السري للأستاذ:", type="password", key="reg_pass")
    with c3:
        teacher_login_btn = st.button("🔑 دخول", key="btn_teacher_login")

    if selected_teacher != "-- اختر الاسم --" and (password_input or teacher_login_btn):
        teacher_row = df_teachers[df_teachers[teacher_col].astype(str).str.strip() == selected_teacher]
        real_password = str(teacher_row.iloc[0][pass_col]).strip()

        if password_input.strip() == real_password:
            st.success(f"مرحباً بك أستاذ(ة) {selected_teacher}")
            
            matching_rows = []
            for idx, row in df_sessions.iterrows():
                if smart_name_match(selected_teacher, row[session_teacher_key]):
                    matching_rows.append(row)

            teacher_sessions = pd.DataFrame(matching_rows)

            if not teacher_sessions.empty:
                teacher_sessions = teacher_sessions.reset_index(drop=True)
                
                cols_to_exclude = [session_teacher_key, 'اليوم', 'التوقيت', 'القاعة', 'المكان', 'تاريخ', 'الفوج']
                display_cols = [c for c in teacher_sessions.columns if c not in cols_to_exclude and not any(k in str(c) for k in ['الرقم', 'رقم'])]
                
                teacher_sessions_display = teacher_sessions[display_cols].copy()
                teacher_sessions_display.insert(0, 'الرقم', range(1, len(teacher_sessions_display) + 1))

                st.markdown("""
                    <div class="notice-box">
                        👇 حدد الحصة المراد طباعتها بالنقر عليها من الجدول، ثم اختر تفاصيل الحضور:
                    </div>
                """, unsafe_allow_html=True)

                event = st.dataframe(
                    teacher_sessions_display,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="reg_grid"
                )

                selected_rows = event.selection.rows if event and hasattr(event, 'selection') else []

                if len(selected_rows) > 0:
                    selected_index = selected_rows[0]
                    selected_row = teacher_sessions_display.iloc[selected_index].to_dict()

                    st.markdown("##### 📌 تحديد تفاصيل الحصة (الفوج، الزمان والمكان):")
                    col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns(5)
                    with col_d1:
                        sel_group = st.selectbox("الفوج:", GROUPS_LIST, key="reg_group")
                    with col_d2:
                        sel_day = st.selectbox("اليوم:", DAYS_LIST, key="reg_day")
                    with col_d3:
                        sel_date = st.date_input("التاريخ:", datetime.now(), key="reg_date")
                    with col_d4:
                        sel_time = st.selectbox("التوقيت:", TIMES_LIST, key="reg_time")
                    with col_d5:
                        sel_room = st.selectbox("القاعة / المدرج:", ROOMS_LIST, key="reg_room")

                    full_session_info = selected_row.copy()
                    full_session_info["الفوج"] = sel_group
                    full_session_info["اليوم"] = sel_day
                    full_session_info["التاريخ"] = str(sel_date)
                    full_session_info["التوقيت"] = sel_time
                    full_session_info["القاعة"] = sel_room

                    pdf_data = create_pdf(selected_teacher, full_session_info)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button(
                        label="🖨 طباعة تقرير الغياب (PDF)",
                        data=pdf_data,
                        file_name=f"تقرير_غياب_{selected_teacher}.pdf",
                        mime="application/pdf",
                        key="btn_dl_reg"
                    )
                else:
                    st.info("💡 انقر على أحد أسطر الجدول لتحديد الحصة.")
            else:
                st.warning("لا توجد حصص مسجلة باسمك حالياً.")
        else:
            st.error("الرقم السري الخاص بالأستاذ غير صحيح.")

# ====================================================
# التبويب الثاني: تقرير غياب خاص بالأستاذ المتعاقد
# ====================================================
with tab_contract:
    st.markdown("##### 📝 إدخال تفاصيل الأستاذ المتعاقد والحصة:")
    
    contract_teacher_name = st.text_input("اسم ولقب الأستاذ المتعاقد:", key="cont_name")

    c_stage, c_year, c_spec = st.columns(3)
    with c_stage:
        cont_stage = st.selectbox("الطور:", STAGES_LIST, key="cont_stage")
    with c_year:
        cont_year = st.selectbox("السنة:", YEARS_LIST, key="cont_year")
    with c_spec:
        cont_spec = st.selectbox("التخصص:", SPECIALTIES_LIST, key="cont_spec")

    c_sub, c_group = st.columns(2)
    with c_sub:
        cont_subject = st.text_input("المادة / المقياس:", key="cont_sub")
    with c_group:
        cont_group = st.selectbox("الفوج:", GROUPS_LIST, key="cont_group")

    st.markdown("##### 📌 تحديد زمان ومكان الحصة:")
    c_day, c_date, c_time, c_room = st.columns(4)
    with c_day:
        cont_day = st.selectbox("اليوم:", DAYS_LIST, key="cont_day")
    with c_date:
        cont_date = st.date_input("التاريخ:", datetime.now(), key="cont_date")
    with c_time:
        cont_time = st.selectbox("التوقيت:", TIMES_LIST, key="cont_time")
    with c_room:
        cont_room = st.selectbox("القاعة / المدرج:", ROOMS_LIST, key="cont_room")

    if contract_teacher_name.strip():
        contract_data = {
            "الطور": cont_stage,
            "السنة": cont_year,
            "التخصص": cont_spec,
            "المادة": cont_subject,
            "الفوج": cont_group,
            "اليوم": cont_day,
            "التاريخ": str(cont_date),
            "التوقيت": cont_time,
            "القاعة": cont_room
        }

        pdf_contract_data = create_pdf(contract_teacher_name, contract_data)

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="🖨 طباعة تقرير الغياب (PDF)",
            data=pdf_contract_data,
            file_name=f"تقرير_غياب_{contract_teacher_name}.pdf",
            mime="application/pdf",
            key="btn_dl_cont"
        )
    else:
        st.info("💡 يرجى كتابة اسم ولقب الأستاذ المتعاقد لتتمكن من طباعة التقرير.")

# ====================================================
# التبويب الثالث: مفردات مواد عروض التكوين المحيّنة
# ====================================================
with tab_syllabus:
    SYLLABUS_URL = "https://example.com"

    st.markdown(f"""
        <div class="external-card">
            <h3 style="color:#1e3c72; margin-bottom:10px;">📚 موقع مفردات مواد عروض التكوين المحيّنة</h3>
            <p style="color:#6c757d; font-size:15px; margin-bottom:20px;">
                اضغط على الزر أدناه للانتقال المباشر إلى منصة مفردات المواد وفتحها في نافذة جديدة بشكل سريع ودون انتظار:
            </p>
            <a href="{SYLLABUS_URL}" target="_blank" style="text-decoration:none;">
                <button style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color:white; padding:12px 30px; border-radius:8px; border:none; cursor:pointer; font-size:16px; font-weight:bold; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
                    🚀 الانتقال إلى موقع مفردات المواد
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# ====================================================
# التبويب الرابع: طلب غياب
# ====================================================
with tab_absence_req:
    st.markdown("##### 📩 بوابـة تسجيـل ومتابعـة طلبـات الغيـاب")
    
    user_role = st.radio(
        "اختر صفة الدخول للخدمة:",
        ["👨‍🏫 الدخول بصفة أستاذ", "👔 الدخول بصفة رئيس قسم"],
        horizontal=True,
        key="absence_role_radio"
    )

    st.markdown("---")

    # 1. الدخول بصفة أستاذ
    if user_role == "👨‍🏫 الدخول بصفة أستاذ":
        
        col_auth1, col_auth2 = st.columns(2)
        with col_auth1:
            req_teacher_select = st.selectbox("اختر اسم الأستاذ:", ["-- اختر الاسم --"] + teachers_list, key="req_teacher_sel")
        with col_auth2:
            req_teacher_pass = st.text_input("أدخل الرقم السري:", type="password", key="req_teacher_pass_input")

        is_authenticated = False
        if req_teacher_select != "-- اختر الاسم --" and req_teacher_pass:
            teacher_row = df_teachers[df_teachers[teacher_col].astype(str).str.strip() == req_teacher_select]
            real_password = str(teacher_row.iloc[0][pass_col]).strip()
            
            if req_teacher_pass.strip() == real_password:
                is_authenticated = True
                st.success(f"أهلاً بك سعادة الأستاذ: **{req_teacher_select}**")
            else:
                st.error("الرقم السري غير صحيح!")

        if is_authenticated:
            st.markdown("##### 📝 تسجيل طلب غياب جديد:")
            
            if 'req_submitted' not in st.session_state:
                st.session_state.req_submitted = False

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                req_name = st.text_input("الاسم واللقب:", value=req_teacher_select, disabled=True, key="req_name_input_auto")
            with col_t2:
                req_rank = st.selectbox("الرتبة العلمية:", RANKS_LIST, key="req_rank_select")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                req_duration_type = st.selectbox("مدة الغياب:", ["يوم واحد", "أكثر من يوم"], key="req_dur_type")
            
            with col_m2:
                if req_duration_type == "يوم واحد":
                    single_date = st.date_input("تاريخ الغياب:", datetime.now(), key="req_single_date")
                    date_str = str(single_date)
                else:
                    col_from, col_to = st.columns(2)
                    with col_from:
                        date_from = st.date_input("من تاريخ:", datetime.now(), key="req_date_from")
                    with col_to:
                        date_to = st.date_input("إلى تاريخ:", datetime.now(), key="req_date_to")
                    date_str = f"من {date_from} إلى {date_to}"

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                req_comp = st.selectbox("تحديد طبيعة الغياب:", COMPENSATION_LIST, key="req_comp_select")
            with col_c2:
                req_reason = st.selectbox("سبب الغياب:", REASON_LIST, key="req_reason_select")

            req_reason_detail = ""
            if req_reason == "سبب آخر":
                req_reason_detail = st.text_input("توضيح السبب الآخر:", key="req_reason_detail_input")

            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                submit_disabled = st.session_state.req_submitted
                if st.button("✅ تسجيل الطلب", key="btn_submit_req", disabled=submit_disabled):
                    new_id = len(st.session_state.db_requests) + 1
                    new_row = {
                        "رقم_الطلب": new_id,
                        "اسم_الأستاذ": req_teacher_select,
                        "الرتبة": req_rank,
                        "مدة_الغياب": req_duration_type,
                        "التاريخ": date_str,
                        "التعويض": req_comp,
                        "السبب": req_reason,
                        "السبب_التفصيلي": req_reason_detail,
                        "تاريخ_التقديم": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "الحالة": "قيد الدراسة"
                    }
                    
                    st.session_state.db_requests = pd.concat([st.session_state.db_requests, pd.DataFrame([new_row])], ignore_index=True)
                    save_absence_requests(st.session_state.db_requests)
                    st.session_state.req_submitted = True
                    st.success("تم تسجيل طلبك بنجاح وهو الآن قيد الدراسة لدى رئيس القسم.")
                    st.rerun()

            with col_b2:
                if st.button("🗑 مسح الكل", key="btn_clear_req"):
                    st.session_state.req_submitted = False
                    st.rerun()

            st.markdown("---")
            st.markdown("##### 📋 قائمة الطلبات المسجلة بملفك الشخصي:")

            user_requests = st.session_state.db_requests[
                st.session_state.db_requests["اسم_الأستاذ"].astype(str).str.strip() == req_teacher_select.strip()
            ].copy()

            if not user_requests.empty:
                user_requests_display = user_requests[[
                    "رقم_الطلب", "الرتبة", "مدة_الغياب", "التاريخ", 
                    "التعويض", "السبب", "تاريخ_التقديم", "الحالة"
                ]].rename(columns={"التعويض": "طبيعة_الغياب"})
                
                st.dataframe(user_requests_display, use_container_width=True, hide_index=True)

                st.markdown("##### 📌 متابعة القرارات وطباعة التقرير:")
                for idx, row in user_requests.iterrows():
                    status = row["الحالة"]
                    st.markdown(f"**طلب رقم ({row['رقم_الطلب']}) - {row['التاريخ']}**")

                    if status == "قيد الدراسة":
                        st.info("⏳ حالة الطلب: **قيد الدراسة**")
                    elif status == "مقبول":
                        st.success("لقد تم قبول طلبكم، يمكنكم التقدم لمكتب رئيس القسم لإتمام الإجراءات وتسلم الموافقة مختومة.")
                        pdf_req = create_absence_request_pdf(row)
                        st.download_button(
                            label=f"🖨 طباعة الطلب المقبول رقم ({row['رقم_الطلب']}) (PDF)",
                            data=pdf_req,
                            file_name=f"طلب_غياب_مقبول_{row['اسم_الأستاذ']}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_user_{row['رقم_الطلب']}"
                        )
                    elif status == "مرفوض":
                        st.error("نأسف عن عدم قبولكم هذا الطلب لضرورة المصلحة، ونقدر تفهمكم وتعاونكم.")
                    st.markdown("---")
            else:
                st.info("لا توجد طلبات مسجلة سابقاً باسمك.")
        else:
            st.caption("🔒 يرجى اختيار اسمك وإدخال الرقم السري لتسجيل طلب غياب أو عرض طلباتك المسجلة.")

    # 2. الدخول بصفة رئيس قسم
    elif user_role == "👔 الدخول بصفة رئيس قسم":
        dept_pass = st.text_input("أدخل كلمة مرور رئيس القسم:", type="password", key="dept_pass_input")

        if dept_pass == st.session_state.dept_password:
            st.success("تم الدخول بصفة رئيس القسم بنجاح.")
            
            with st.expander("⚙ تغيير كلمة سر رئيس القسم"):
                new_pass = st.text_input("كلمة السر الجديدة:", type="password", key="new_dept_pass")
                confirm_pass = st.text_input("تأكيد كلمة السر الجديدة:", type="password", key="confirm_dept_pass")
                if st.button("تحديث كلمة السر", key="btn_change_pass"):
                    if new_pass and new_pass == confirm_pass:
                        st.session_state.dept_password = new_pass
                        st.success("تم تغيير كلمة السر بنجاح!")
                    else:
                        st.error("كلمتا السر غير متطابقتين!")

            st.markdown("---")
            df_req = st.session_state.db_requests

            if not df_req.empty:
                st.markdown("##### 📋 قائمة كافة طلبات الغياب المسجلة:")

                for idx, row in df_req.iterrows():
                    with st.expander(f"طلب رقم {row['رقم_الطلب']} - الأستاذ(ة): {row['اسم_الأستاذ']} | الحالة: ({row['الحالة']})"):
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            st.write(f"**الرتبة:** {row['الرتبة']}")
                            st.write(f"**مدة الغياب:** {row['مدة_الغياب']}")
                            st.write(f"**التاريخ/الفترة:** {row['التاريخ']}")
                        with col_r2:
                            st.write(f"**طبيعة الغياب:** {row['التعويض']}")
                            st.write(f"**السبب:** {row['السبب']}")
                            if pd.notna(row['السبب_التفصيلي']) and str(row['السبب_التفصيلي']).strip():
                                st.write(f"**التفاصيل:** {row['السبب_التفصيلي']}")

                        c_acc, c_rej = st.columns(2)
                        with c_acc:
                            if st.button("✅ قبول الطلب", key=f"btn_accept_{idx}"):
                                st.session_state.db_requests.at[idx, "الحالة"] = "مقبول"
                                save_absence_requests(st.session_state.db_requests)
                                st.success("تم قبول الطلب بنجاح.")
                                st.rerun()
                        with c_rej:
                            if st.button("❌ رفض الطلب", key=f"btn_reject_{idx}"):
                                st.session_state.db_requests.at[idx, "الحالة"] = "مرفوض"
                                save_absence_requests(st.session_state.db_requests)
                                st.error("تم رفض الطلب.")
                                st.rerun()
            else:
                st.info("لا توجد أي طلبات غياب مسجلة حالياً.")
        elif dept_pass:
            st.error("كلمة المرور غير صحيحة!")
