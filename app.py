import io
import urllib.request
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

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
# 2. إنشاء الاتصال الدائم بـ Google Sheets
# ----------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_from_sheet(worksheet_name, expected_cols):
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    except Exception:
        return pd.DataFrame(columns=expected_cols)

def save_data_to_sheet(worksheet_name, df):
    try:
        conn.update(worksheet=worksheet_name, data=df)
        return True
    except Exception as e:
        st.error(f"خطأ أثناء حفظ البيانات: {e}")
        return False

# --- تحميل كلمة المرور وتحديثها في جوجل شيت ---
def get_dept_password():
    df_sett = load_data_from_sheet("الإعدادات", ["المفتاح", "القيمة"])
    if not df_sett.empty:
        pass_row = df_sett[df_sett["المفتاح"] == "dept_password"]
        if not pass_row.empty:
            return str(pass_row.iloc[0]["القيمة"]).strip()
    return "1234"

def save_dept_password(new_pass):
    df_sett = load_data_from_sheet("الإعدادات", ["المفتاح", "القيمة"])
    if df_sett.empty:
        df_sett = pd.DataFrame([{"المفتاح": "dept_password", "القيمة": str(new_pass).strip()}])
    else:
        if "dept_password" in df_sett["المفتاح"].values:
            df_sett.loc[df_sett["المفتاح"] == "dept_password", "القيمة"] = str(new_pass).strip()
        else:
            df_sett = pd.concat([df_sett, pd.DataFrame([{"المفتاح": "dept_password", "القيمة": str(new_pass).strip()}])], ignore_index=True)
    save_data_to_sheet("الإعدادات", df_sett)

if 'dept_password' not in st.session_state:
    st.session_state.dept_password = get_dept_password()

# --- عداد الزوار الدائم مع جوجل شيت ---
def get_and_update_visitor_count():
    df_vis = load_data_from_sheet("الزوار", ["عدد_الزوار"])
    count = 0
    if not df_vis.empty and pd.notna(df_vis.iloc[0]["عدد_الزوار"]):
        try:
            count = int(df_vis.iloc[0]["عدد_الزوار"])
        except Exception:
            count = 0
    if 'visited_session' not in st.session_state:
        count += 1
        st.session_state.visited_session = True
        df_vis_updated = pd.DataFrame([{"عدد_الزوار": count}])
        save_data_to_sheet("الزوار", df_vis_updated)
    return count

visitor_number = get_and_update_visitor_count()

FIXED_PROG_PASSWORD = "khelil2026_1982"

REQUIRED_REPORT_COLS = [
    "رقم_التقرير", "اسم_الأستاذ", "نوع_الأستاذ", "اليوم", "التاريخ", 
    "التوقيت", "القاعة", "المادة", "الطور", "التخصص", "السنة", "الفوج", 
    "تاريخ_التسجيل", "حالة_الاطلاع"
]

REQUIRED_REQ_COLS = [
    "رقم_الطلب", "اسم_الأستاذ", "الرتبة", "مدة_الغياب", 
    "التاريخ", "التعويض", "السبب", "السبب_التفصيلي", 
    "تاريخ_التقديم", "الحالة"
]

if 'db_reports' not in st.session_state:
    st.session_state.db_reports = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)

if 'db_requests' not in st.session_state:
    st.session_state.db_requests = load_data_from_sheet("الطلبات", REQUIRED_REQ_COLS)

# ----------------------------------------------------
# 3. إعدادات الصفحة والتصميم
# ----------------------------------------------------
st.set_page_config(
    page_title="منصة إدارة خدمات القسم (نسخة تجريبية)",
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }

    .main-header h1 {
        margin: 5px 0 10px 0;
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }

    .main-header .version-line {
        font-size: 13px;
        color: #e0e6ed;
        margin-top: 5px;
        font-weight: 400;
    }

    .visitor-badge {
        background-color: rgba(255, 255, 255, 0.2);
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
        margin-top: 5px;
        border: 1px solid rgba(255, 255, 255, 0.3);
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

    .confirm-box {
        background-color: #fff3cd;
        border: 2px solid #ffeeba;
        padding: 15px;
        border-radius: 10px;
        margin-top: 15px;
        margin-bottom: 15px;
    }

    .stButton > button, .stDownloadButton > button, .stLinkButton > a {
        width: 100%;
        background-color: #1e3c72 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        padding: 10px !important;
        border: none !important;
        font-size: 15px !important;
        text-align: center !important;
        text-decoration: none !important;
        display: inline-block !important;
        transition: background-color 0.3s !important;
    }

    .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
        background-color: #2a5298 !important;
    }

    .prog-btn > button {
        background-color: #dc3545 !important;
        color: white !important;
        font-weight: bold !important;
    }

    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 20px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. القوائم والدوال المساعدة والـ PDF
# ----------------------------------------------------
DEFAULT_OPTION = "-- اختر من هنا --"

DAYS_LIST = [DEFAULT_OPTION, "السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
TIMES_LIST = [DEFAULT_OPTION, "08:00 - 09:30", "09:30 - 11:00", "11:00 - 12:30", "12:30 - 14:00", "14:00 - 15:30"]
ROOMS_LIST = [DEFAULT_OPTION] + [f"القاعة {i}" for i in range(5, 17)] + [f"القاعة {i}" for i in range(21, 25)] + ["المدرج أ", "المدرج ب", "المدرج ج", "المدرج د"]
GROUPS_LIST = [DEFAULT_OPTION, "الفوج 01", "الفوج 02", "الفوج 03", "الفوج 04"]
STAGES_LIST = [DEFAULT_OPTION, "ليسانس", "ماستر"]
YEARS_LIST = [DEFAULT_OPTION, "الأولى", "الثانية", "الثالثة"]
SPECIALTIES_LIST = [DEFAULT_OPTION, "جذع مشترك", "دراسات لغوية", "دراسات أدبية", "نقد ومناهج", "لسانيات عامة", "لسانيات تطبيقية", "أدب حديث ومعاصر", "نقد حديث ومعاصر", "أدب شعبي"]
RANKS_LIST = [DEFAULT_OPTION, "أستاذ تعليم عال", "أستاذ محاضر أ", "أستاذ محاضر ب", "أستاذ مساعد أ", "أستاذ مساعد ب", "أستاذ متعاقد"]
REASON_LIST = [DEFAULT_OPTION, "عطلة مرضية", "ظرف عائلي", "ملتقى", "اجتماع", "دعوة", "سبب آخر"]
COMPENSATION_LIST = [DEFAULT_OPTION, "غياب مع التعويض", "غياب من دون تعويض"]

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
    ignored_keys = ['اسم الأستاذ', 'الرقم', 'رقم', 'الرقم التسلسلي', 'id', 'ID', 'no', 'No', 'الرقم السري', 'المكان', 'حالة_الاطلاع', 'رقم_التقرير', 'تاريخ_التسجيل', 'نوع_الأستاذ']
    items = [(key, val) for key, val in session_info.items() if key not in ignored_keys and not any(k in str(key) for k in ['الرقم', 'رقم'])]

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

def create_reports_summary_pdf(df_reports, title_text="جدول ملخص تقارير الغياب الجماعي"):
    buffer = io.BytesIO()
    width = 595
    height = 842

    c = canvas.Canvas(buffer, pagesize=(width, height))
    font_name = 'ArabicFont' if os.path.exists(FONT_PATH) else 'Helvetica'
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('ArabicFont', FONT_PATH))

    c.setFont(font_name, 10)
    c.drawCentredString(width / 2, height - 30, fix_arabic("الجمهورية الجزائرية الديمقراطية الشعبية"))
    c.drawCentredString(width / 2, height - 45, fix_arabic("وزارة التعليم العالي والبحث العلمي - جامعة الوادي"))
    c.drawCentredString(width / 2, height - 60, fix_arabic("كلية الآداب واللغات - قسم اللغة والأدب العربي"))

    c.setFont(font_name, 14)
    c.drawCentredString(width / 2, height - 90, fix_arabic(title_text))

    c.setFont(font_name, 9)
    y = height - 120

    headers = ["رقم", "اسم الأستاذ", "اليوم", "التاريخ", "التوقيت", "القاعة", "المادة", "الفوج", "الحالة"]
    col_x = [550, 520, 410, 360, 290, 220, 160, 100, 50]

    for i, h in enumerate(headers):
        c.drawRightString(col_x[i], y, fix_arabic(h))

    y -= 10
    c.line(40, y, 560, y)
    y -= 15

    for idx, row in df_reports.iterrows():
        if y < 50:
            c.showPage()
            c.setFont(font_name, 9)
            y = height - 50

        vals = [
            str(row.get('رقم_التقرير', '')),
            str(row.get('اسم_الأستاذ', '')),
            str(row.get('اليوم', '')),
            str(row.get('التاريخ', '')),
            str(row.get('التوقيت', '')),
            str(row.get('القاعة', '')),
            str(row.get('المادة', '')),
            str(row.get('الفوج', '')),
            str(row.get('حالة_الاطلاع', ''))
        ]

        for i, val in enumerate(vals):
            c.drawRightString(col_x[i], y, fix_arabic(val))
        
        y -= 18

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def create_absence_request_pdf(req_row):
    buffer = io.BytesIO()
    width = 420
    height = 560

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

    y_pos = height - 117
    c.setFont(font_name, 10.5)
    c.drawRightString(width - 25, y_pos, fix_arabic(f"الأستاذ(ة): {req_row['اسم_الأستاذ']}"))
    y_pos -= 18
    c.drawRightString(width - 25, y_pos, fix_arabic(f"الدرجة / الرتبة العلمية: {req_row['الرتبة']}"))

    y_pos -= 36
    c.setFont(font_name, 13)
    c.drawCentredString(width / 2, y_pos, fix_arabic("طلب الموافقة على الغياب"))

    y_pos -= 36
    c.setFont(font_name, 11)
    c.drawRightString(width - 25, y_pos, fix_arabic("السيد المحترم رئيس القسم ،"))
    
    y_pos -= 22
    c.setFont(font_name, 9.5)
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

    y_pos -= 45
    current_date = datetime.now().strftime("%Y-%m-%d")
    c.drawString(30, y_pos, fix_arabic(f"حرر بتاريخ: {current_date}"))
    y_pos -= 20
    c.drawString(30, y_pos, fix_arabic("إمضاء الأستاذ(ة):"))

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def render_dept_head_view(target_view_name):
    st.markdown(f"### 👔 لوحة رئيس القسم - إدارة ({target_view_name})")
    dept_p_in = st.text_input("أدخل كلمة مرور رئيس القسم / البرمجة:", type="password", key=f"dept_pass_{target_view_name}")
    dept_b_in = st.button("🔑 تسجيل الدخول", key=f"btn_dept_login_{target_view_name}")

    if dept_b_in or dept_p_in:
        if dept_p_in and (dept_p_in.strip() == FIXED_PROG_PASSWORD or dept_p_in.strip() == st.session_state.dept_password):
            st.session_state[f"auth_{target_view_name}"] = True
        else:
            if dept_b_in:
                st.session_state[f"auth_{target_view_name}"] = False
                st.error("كلمة المرور غير صحيحة!")

    if st.session_state.get(f"auth_{target_view_name}", False):
        st.success("تم الدخول بنجاح بصفة رئيس القسم!")

        with st.expander("🔑 تغيير كلمة مرور رئيس القسم"):
            old_p = st.text_input("كلمة المرور الحالية:", type="password", key=f"old_p_{target_view_name}")
            new_p = st.text_input("كلمة المرور الجديدة:", type="password", key=f"new_p_{target_view_name}")
            confirm_p = st.text_input("تأكيد كلمة المرور الجديدة:", type="password", key=f"conf_p_{target_view_name}")
            if st.button("تحديث كلمة المرور", key=f"btn_change_pass_{target_view_name}"):
                if old_p.strip() == st.session_state.dept_password or old_p.strip() == FIXED_PROG_PASSWORD:
                    if new_p and new_p == confirm_p:
                        st.session_state.dept_password = new_p.strip()
                        save_dept_password(new_p)
                        st.success("تم تغيير كلمة المرور بنجاح وحفظها سحابياً!")
                    else:
                        st.error("كلمتا المرور غير متطابقتين!")
                else:
                    st.error("كلمة المرور الحالية غير صحيحة!")

        st.markdown("---")
        if target_view_name in ["الغياب الجماعي للمرسم", "الغياب الجماعي للمتعاقد"]:
            st.markdown("##### 📋 كافة تقارير الغياب الجماعي المسجلة بالقسم:")
            df_rep = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
            if not df_rep.empty:
                filter_day = st.selectbox("تصفية التقارير حسب اليوم:", [DEFAULT_OPTION, "جميع الأيام"] + [d for d in DAYS_LIST if d != DEFAULT_OPTION], key=f"filter_day_{target_view_name}")
                
                filtered_rep = df_rep
                if filter_day not in [DEFAULT_OPTION, "جميع الأيام"]:
                    filtered_rep = df_rep[df_rep["اليوم"] == filter_day]

                cols_display = [c for c in ["رقم_التقرير", "اسم_الأستاذ", "نوع_الأستاذ", "اليوم", "التاريخ", "التوقيت", "القاعة", "المادة", "الفوج", "حالة_الاطلاع"] if c in filtered_rep.columns]
                st.dataframe(filtered_rep[cols_display], use_container_width=True, hide_index=True)

                st.markdown("##### 📌 تأكيد الاطلاع على تقارير الأساتذة:")
                for idx, row in filtered_rep.iterrows():
                    c_rep_info, c_rep_btn = st.columns([3, 1])
                    with c_rep_info:
                        st.write(f"• تقرير رقم ({row['رقم_التقرير']}) - الأستاذ: {row['اسم_الأستاذ']} ({row.get('نوع_الأستاذ','مرسم')}) | المادة: **{row.get('المادة','--')}** | الحالة: **{row['حالة_الاطلاع']}**")
                    with c_rep_btn:
                        if row["حالة_الاطلاع"] != "تم الاطلاع":
                            if st.button("👁 تأكيد الاطلاع", key=f"btn_mark_read_{target_view_name}_{idx}"):
                                df_rep.at[idx, "حالة_الاطلاع"] = "تم الاطلاع"
                                save_data_to_sheet("التقارير", df_rep)
                                st.success("تم التحديث إلى (تم الاطلاع).")
                                st.rerun()

                st.markdown("---")
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    pdf_day = create_reports_summary_pdf(filtered_rep, "ملخص تقارير الغياب الجماعي")
                    st.download_button("🖨 تحميل/طباعة تقارير اليوم المختار (PDF)", data=pdf_day, file_name="تقارير_المختار.pdf", mime="application/pdf", key=f"print_day_{target_view_name}")
                with c_p2:
                    pdf_all = create_reports_summary_pdf(df_rep, "ملخص جميع تقارير الغياب الجماعي بالقسم")
                    st.download_button("🖨 تحميل/طباعة جميع التقارير الجماعية (PDF)", data=pdf_all, file_name="جميع_التقارير.pdf", mime="application/pdf", key=f"print_all_{target_view_name}")
            else:
                st.info("لا توجد تقارير غياب جماعي مسجلة حالياً.")

        elif target_view_name == "طلب الغياب":
            st.markdown("##### 📋 كافة طلبات الغياب الفردية المسجلة:")
            df_req = load_data_from_sheet("الطلبات", REQUIRED_REQ_COLS)
            if not df_req.empty:
                for idx, row in df_req.iterrows():
                    with st.expander(f"طلب رقم {row['رقم_الطلب']} - الأستاذ: {row['اسم_الأستاذ']} | الحالة: ({row['الحالة']})"):
                        st.write(f"**الرتبة:** {row['الرتبة']} | **الفترة:** {row['التاريخ']}")
                        st.write(f"**طبيعة الغياب:** {row['التعويض']} | **السبب:** {row['السبب']}")
                        c_acc, c_rej = st.columns(2)
                        with c_acc:
                            if st.button("✅ قبول الطلب", key=f"req_acc_{idx}"):
                                df_req.at[idx, "الحالة"] = "مقبول"
                                save_data_to_sheet("الطلبات", df_req)
                                st.rerun()
                        with c_rej:
                            if st.button("❌ رفض الطلب", key=f"req_rej_{idx}"):
                                df_req.at[idx, "الحالة"] = "مرفوض"
                                save_data_to_sheet("الطلبات", df_req)
                                st.rerun()
            else:
                st.info("لا توجد طلبات غياب فردية مسجلة.")

# ----------------------------------------------------
# 5. الواجهة الرئيسية
# ----------------------------------------------------
st.markdown(f"""
    <div class="main-header">
        <h1>منصة إدارة خدمات القسم (نسخة تجريبية)</h1>
        <div class="version-line">النسخة 001_2026 &nbsp;|&nbsp; <span class="visitor-badge">👤 عدد الزوار: {visitor_number}</span></div>
    </div>
""", unsafe_allow_html=True)

if 'open_prog_mode' not in st.session_state:
    st.session_state.open_prog_mode = False

col_nav_main, col_nav_prog = st.columns([4, 1])

with col_nav_prog:
    st.markdown('<div class="prog-btn">', unsafe_allow_html=True)
    if st.button("🔴 برمجة", key="btn_prog_toggle"):
        st.session_state.open_prog_mode = not st.session_state.open_prog_mode
        if st.session_state.open_prog_mode:
            st.session_state.selected_menu_choice = DEFAULT_OPTION
            st.session_state.prog_authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

menu_options = [
    DEFAULT_OPTION,
    "👨‍🏫 تقرير غياب خاص بالأستاذ المرسم",
    "📝 تقرير غياب خاص بالأستاذ المتعاقد",
    "📚 مفردات مواد عروض التكوين المحيّنة",
    "📩 طلب غياب"
]

if 'selected_menu_choice' not in st.session_state:
    st.session_state.selected_menu_choice = DEFAULT_OPTION

with col_nav_main:
    def on_menu_change():
        if st.session_state.menu_choice_widget != DEFAULT_OPTION:
            st.session_state.open_prog_mode = False

    menu_choice = st.selectbox(
        "اختر الخدمة المطلوبة:",
        menu_options,
        index=menu_options.index(st.session_state.selected_menu_choice) if st.session_state.selected_menu_choice in menu_options else 0,
        key="menu_choice_widget",
        on_change=on_menu_change
    )
    st.session_state.selected_menu_choice = menu_choice

try:
    df_teachers = pd.read_excel('teachers.xlsx')
    df_teachers.columns = df_teachers.columns.astype(str).str.strip()
    teacher_col = df_teachers.columns[0]
    pass_col = df_teachers.columns[1]
    teachers_list = df_teachers[teacher_col].dropna().astype(str).str.strip().unique().tolist()
except Exception:
    df_teachers = None
    teachers_list = []

# ----------------------------------------------------
# 🔐 1. نافذة البرمجة الأمنية المعزولة تماماً
# ----------------------------------------------------
if st.session_state.open_prog_mode:
    st.markdown("---")
    st.markdown("### 🔐 إدارة النظام والبرمجة")
    
    col_p_in1, col_p_in2 = st.columns([3, 1])
    with col_p_in1:
        prog_pass_input = st.text_input("أدخل كلمة المرور لدخول نظام البرمجة:", type="password", key="prog_pass_input")
    with col_p_in2:
        st.markdown('<div style="margin-top:28px;">', unsafe_allow_html=True)
        prog_login_click = st.button("🔑 تسجيل الدخول", key="btn_prog_login")
        st.markdown('</div>', unsafe_allow_html=True)

    if prog_login_click or prog_pass_input:
        if prog_pass_input and (prog_pass_input.strip() == FIXED_PROG_PASSWORD or prog_pass_input.strip() == st.session_state.dept_password):
            st.session_state.prog_authenticated = True
        else:
            if prog_login_click:
                st.session_state.prog_authenticated = False
                st.error("ويحك! أرجو عدم التطفل والدخول لإدارة النظام،،")

    if st.session_state.get('prog_authenticated', False):
        st.success("تم الدخول بنجاح!")
        st.markdown("#### 🛠 اختر الشاشة المطلوبة لإدارتها:")
        prog_page = st.radio("الصفحات المتاحة:", ["غياب جماعي", "طلب الغياب"], horizontal=True)

        if prog_page == "غياب جماعي":
            st.markdown("##### 📋 كافة تقارير الغياب الجماعي المسجلة بالقسم:")
            df_rep = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
            if not df_rep.empty:
                filter_day = st.selectbox("تصفية التقارير حسب اليوم:", [DEFAULT_OPTION, "جميع الأيام"] + [d for d in DAYS_LIST if d != DEFAULT_OPTION], key="filter_day_prog")
                
                filtered_rep = df_rep
                if filter_day not in [DEFAULT_OPTION, "جميع الأيام"]:
                    filtered_rep = df_rep[df_rep["اليوم"] == filter_day]

                cols_display = [c for c in ["رقم_التقرير", "اسم_الأستاذ", "نوع_الأستاذ", "اليوم", "التاريخ", "التوقيت", "القاعة", "المادة", "الفوج", "حالة_الاطلاع"] if c in filtered_rep.columns]
                st.dataframe(filtered_rep[cols_display], use_container_width=True, hide_index=True)

                st.markdown("##### 📌 تحديد الاطلاع على تقارير الأساتذة:")
                for idx, row in filtered_rep.iterrows():
                    c_rep_info, c_rep_btn = st.columns([3, 1])
                    with c_rep_info:
                        st.write(f"• تقرير رقم ({row['رقم_التقرير']}) - الأستاذ: {row['اسم_الأستاذ']} ({row.get('نوع_الأستاذ','مرسم')}) | المادة: **{row.get('المادة','--')}** | الحالة: **{row['حالة_الاطلاع']}**")
                    with c_rep_btn:
                        if row["حالة_الاطلاع"] != "تم الاطلاع":
                            if st.button("👁 تأكيد الاطلاع", key=f"btn_prog_mark_read_{idx}"):
                                df_rep.at[idx, "حالة_الاطلاع"] = "تم الاطلاع"
                                save_data_to_sheet("التقارير", df_rep)
                                st.success("تم التحديث إلى (تم الاطلاع).")
                                st.rerun()
            else:
                st.info("لا توجد تقارير غياب جماعي مسجلة حالياً.")

        elif prog_page == "طلب الغياب":
            st.markdown("##### 📋 كافة طلبات الغياب الفردية المسجلة:")
            df_req = load_data_from_sheet("الطلبات", REQUIRED_REQ_COLS)
            if not df_req.empty:
                for idx, row in df_req.iterrows():
                    with st.expander(f"طلب رقم {row['رقم_الطلب']} - الأستاذ: {row['اسم_الأستاذ']} | الحالة: ({row['الحالة']})"):
                        st.write(f"**الرتبة:** {row['الرتبة']} | **الفترة:** {row['التاريخ']}")
                        st.write(f"**طبيعة الغياب:** {row['التعويض']} | **السبب:** {row['السبب']}")
                        c_acc, c_rej = st.columns(2)
                        with c_acc:
                            if st.button("✅ قبول الطلب", key=f"prog_acc_{idx}"):
                                df_req.at[idx, "الحالة"] = "مقبول"
                                save_data_to_sheet("الطلبات", df_req)
                                st.rerun()
                        with c_rej:
                            if st.button("❌ رفض الطلب", key=f"prog_rej_{idx}"):
                                df_req.at[idx, "الحالة"] = "مرفوض"
                                save_data_to_sheet("الطلبات", df_req)
                                st.rerun()
            else:
                st.info("لا توجد طلبات غياب فردية مسجلة.")

# ----------------------------------------------------
# 2. تقرير غياب خاص بالأستاذ المرسم
# ----------------------------------------------------
elif menu_choice == "👨‍🏫 تقرير غياب خاص بالأستاذ المرسم":
    role_choice = st.radio("اختر صفة الدخول للخدمة:", ["👨‍🏫 الدخول بصفة أستاذ", "👔 الدخول بصفة رئيس قسم"], horizontal=True, key="role_reg")
    st.markdown("---")

    if role_choice == "👔 الدخول بصفة رئيس قسم":
        render_dept_head_view("الغياب الجماعي للمرسم")
    else:
        st.markdown("### 👨‍🏫 تسجيل تقرير غياب جماعي - أستاذ مرسّم")
        try:
            df_sessions = pd.read_excel('sessions.xlsx')
            df_sessions.columns = df_sessions.columns.astype(str).str.strip()
        except Exception:
            st.error("⚠ يتعذر قراءة ملف الحصص 'sessions.xlsx'.")
            st.stop()

        session_teacher_col = [c for c in df_sessions.columns if 'أستاذ' in c or 'الاستاذ' in c or 'اسم' in c]
        session_teacher_key = session_teacher_col[0] if session_teacher_col else df_sessions.columns[0]

        c_in1, c_in2, c_in3 = st.columns([2, 2, 1])
        with c_in1:
            selected_teacher = st.selectbox("اسم الأستاذ:", [DEFAULT_OPTION] + teachers_list, key="reg_teacher")
        with c_in2:
            password_input = st.text_input("الرقم السري للأستاذ:", type="password", key="reg_pass")
        with c_in3:
            st.markdown('<div style="margin-top:28px;">', unsafe_allow_html=True)
            teacher_login_btn = st.button("🔑 تسجيل الدخول", key="btn_teacher_login")
            st.markdown('</div>', unsafe_allow_html=True)

        if selected_teacher != DEFAULT_OPTION and (password_input or teacher_login_btn):
            teacher_row = df_teachers[df_teachers[teacher_col].astype(str).str.strip() == selected_teacher]
            real_password = str(teacher_row.iloc[0][pass_col]).strip()

            if password_input.strip() == real_password:
                st.success(f"مرحباً بك أستاذ(ة) {selected_teacher}")
                
                matching_rows = []
                for idx, row in df_sessions.iterrows():
                    if smart_name_match(selected_teacher, row[session_teacher_key]):
                        matching_rows.append(row)

                teacher_sessions = pd.DataFrame(matching_rows)
                has_selected_official_session = False

                if not teacher_sessions.empty:
                    teacher_sessions = teacher_sessions.reset_index(drop=True)
                    
                    cols_to_exclude = [
                        session_teacher_key, 'اليوم', 'التوقيت', 'القاعة', 'المكان', 
                        'تاريخ', 'الفوج', 'قاعة', 'مكان', 'المكان/القاعة'
                    ]
                    display_cols = [
                        c for c in teacher_sessions.columns 
                        if c not in cols_to_exclude 
                        and not any(k in str(c).lower() for k in ['الرقم', 'رقم', 'قاعة', 'مكان', 'room', 'hall'])
                    ]
                    
                    teacher_sessions_display = teacher_sessions[display_cols].copy()
                    teacher_sessions_display.insert(0, 'الرقم', range(1, len(teacher_sessions_display) + 1))

                    st.markdown("""
                        <div class="notice-box">
                            👇 حدد الحصة المراد تسجيلها بالنقر عليها من الجدول، ثم حدد تفاصيل الحضور:
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
                        has_selected_official_session = True
                        selected_index = selected_rows[0]
                        selected_row = teacher_sessions_display.iloc[selected_index].to_dict()

                        st.markdown("##### 📌 تحديد تفاصيل الزمان والمكان والفوج:")
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

                        subject_name = full_session_info.get("المادة", full_session_info.get("المقياس", ""))
                        if not subject_name:
                            for k, v in selected_row.items():
                                if "مادة" in str(k) or "مقياس" in str(k):
                                    subject_name = v
                                    break

                        pdf_data = create_pdf(selected_teacher, full_session_info)

                        can_submit = (
                            sel_group != DEFAULT_OPTION and
                            sel_day != DEFAULT_OPTION and
                            sel_time != DEFAULT_OPTION and
                            sel_room != DEFAULT_OPTION
                        )

                        st.markdown("<br>", unsafe_allow_html=True)
                        if not can_submit:
                            st.warning("⚠ يرجى اختيار جميع الحقول (الفوج، اليوم، التوقيت، القاعة) لتكشف زر التأكيد وتتمكن من التسجيل والطباعة.")
                        else:
                            if 'confirm_reg_show' not in st.session_state:
                                st.session_state.confirm_reg_show = False

                            if st.button("🖨 تسجيل وطباعة التقرير (PDF)", key="btn_trigger_reg"):
                                st.session_state.confirm_reg_show = True

                            if st.session_state.confirm_reg_show:
                                st.markdown("""
                                    <div class="confirm-box">
                                        <h4 style="color:#856404; margin-top:0;">⚠ هل أنت متأكد من أن المعلومات التي أدخلتها صحيحة؟</h4>
                                    </div>
                                """, unsafe_allow_html=True)
                                col_confirm_yes, col_confirm_no = st.columns(2)
                                with col_confirm_yes:
                                    if st.download_button(
                                        label="✅ نعم، تأكيد وتسجيل",
                                        data=pdf_data,
                                        file_name=f"تقرير_غياب_{selected_teacher}.pdf",
                                        mime="application/pdf",
                                        key="btn_confirm_yes_reg"
                                    ):
                                        df_rep = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
                                        new_rep_id = len(df_rep) + 1
                                        new_rep_row = {
                                            "رقم_التقرير": new_rep_id,
                                            "اسم_الأستاذ": selected_teacher,
                                            "نوع_الأستاذ": "مرسم",
                                            "اليوم": sel_day,
                                            "التاريخ": str(sel_date),
                                            "التوقيت": sel_time,
                                            "القاعة": sel_room,
                                            "المادة": subject_name,
                                            "الطور": full_session_info.get("الطور", ""),
                                            "التخصص": full_session_info.get("التخصص", ""),
                                            "السنة": full_session_info.get("السنة", ""),
                                            "الفوج": sel_group,
                                            "تاريخ_التسجيل": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                            "حالة_الاطلاع": "قيد المراجعة"
                                        }
                                        df_rep_updated = pd.concat([df_rep, pd.DataFrame([new_rep_row])], ignore_index=True)
                                        save_data_to_sheet("التقارير", df_rep_updated)
                                        st.session_state.confirm_reg_show = False
                                        st.success("تم تسجيل التقرير وطباعته بنجاح!")
                                        st.rerun()

                                with col_confirm_no:
                                    if st.button("❌ لا، إلغاء", key="btn_confirm_no_reg"):
                                        st.session_state.confirm_reg_show = False
                                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                if 'show_add_custom_session' not in st.session_state:
                    st.session_state.show_add_custom_session = False

                col_btn_add, col_space = st.columns([2, 3])
                with col_btn_add:
                    btn_disabled = has_selected_official_session
                    if btn_disabled:
                        st.info("💡 تم تحديد حصة رسمية من الجدول أعلاه.")
                    
                    if st.button("➕ إضافة حصة غير مدرجة", key="btn_toggle_custom_session", disabled=btn_disabled):
                        st.session_state.show_add_custom_session = not st.session_state.show_add_custom_session

                if st.session_state.show_add_custom_session and not has_selected_official_session:
                    st.markdown("""
                        <div class="notice-box">
                            📝 نموذج إضافة حصة غير موجودة بقوائم الاختيار الرسمية:
                        </div>
                    """, unsafe_allow_html=True)

                    st.text_input("اسم الأستاذ:", value=selected_teacher, disabled=True, key="custom_teacher_readonly")

                    col_cs1, col_cs2, col_cs3 = st.columns(3)
                    with col_cs1:
                        c_stage = st.selectbox("الطور:", STAGES_LIST, key="custom_stage")
                    with col_cs2:
                        c_year = st.selectbox("السنة:", YEARS_LIST, key="custom_year")
                    with col_cs3:
                        c_spec = st.selectbox("التخصص:", SPECIALTIES_LIST, key="custom_spec")

                    col_cs4, col_cs5 = st.columns(2)
                    with col_cs4:
                        c_sub = st.text_input("المادة / المقياس:", key="custom_sub")
                    with col_cs5:
                        c_group = st.selectbox("الفوج:", GROUPS_LIST, key="custom_group")

                    col_cs6, col_cs7, col_cs8, col_cs9 = st.columns(4)
                    with col_cs6:
                        c_day = st.selectbox("اليوم:", DAYS_LIST, key="custom_day")
                    with col_cs7:
                        c_date = st.date_input("التاريخ:", datetime.now(), key="custom_date")
                    with col_cs8:
                        c_time = st.selectbox("التوقيت:", TIMES_LIST, key="custom_time")
                    with col_cs9:
                        c_room = st.selectbox("القاعة / المدرج:", ROOMS_LIST, key="custom_room")

                    can_submit_custom = (
                        c_stage != DEFAULT_OPTION and
                        c_year != DEFAULT_OPTION and
                        c_spec != DEFAULT_OPTION and
                        c_group != DEFAULT_OPTION and
                        c_day != DEFAULT_OPTION and
                        c_time != DEFAULT_OPTION and
                        c_room != DEFAULT_OPTION and
                        c_sub.strip() != ""
                    )

                    custom_session_data = {
                        "الطور": c_stage if c_stage != DEFAULT_OPTION else "",
                        "السنة": c_year if c_year != DEFAULT_OPTION else "",
                        "التخصص": c_spec if c_spec != DEFAULT_OPTION else "",
                        "المادة": c_sub,
                        "الفوج": c_group if c_group != DEFAULT_OPTION else "",
                        "اليوم": c_day if c_day != DEFAULT_OPTION else "",
                        "التاريخ": str(c_date),
                        "التوقيت": c_time if c_time != DEFAULT_OPTION else "",
                        "القاعة": c_room if c_room != DEFAULT_OPTION else ""
                    }

                    pdf_custom_data = create_pdf(selected_teacher, custom_session_data)

                    if not can_submit_custom:
                        st.warning("⚠ يرجى ملء كافة الخيارات الحقول لتكشف زر التأكيد وتتمكن من تسجيل الحصة المضافة.")

                    if 'confirm_custom_show' not in st.session_state:
                        st.session_state.confirm_custom_show = False

                    if st.button("🖨 تسجيل وطباعة الحصة المضافة (PDF)", key="btn_trigger_custom", disabled=not can_submit_custom):
                        st.session_state.confirm_custom_show = True

                    if st.session_state.confirm_custom_show:
                        st.markdown("""
                            <div class="confirm-box">
                                <h4 style="color:#856404; margin-top:0;">⚠ هل أنت متأكد من أن المعلومات التي أدخلتها صحيحة؟</h4>
                            </div>
                        """, unsafe_allow_html=True)
                        col_cyes, col_cno = st.columns(2)
                        with col_cyes:
                            if st.download_button(
                                label="✅ نعم، تأكيد وتسجيل",
                                data=pdf_custom_data,
                                file_name=f"تقرير_غياب_{selected_teacher}.pdf",
                                mime="application/pdf",
                                key="btn_confirm_yes_custom"
                            ):
                                df_rep = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
                                new_rep_id = len(df_rep) + 1
                                new_rep_row = {
                                    "رقم_التقرير": new_rep_id,
                                    "اسم_الأستاذ": selected_teacher,
                                    "نوع_الأستاذ": "مرسم",
                                    "اليوم": c_day,
                                    "التاريخ": str(c_date),
                                    "التوقيت": c_time,
                                    "القاعة": c_room,
                                    "المادة": c_sub,
                                    "الطور": c_stage,
                                    "التخصص": c_spec,
                                    "السنة": c_year,
                                    "الفوج": c_group,
                                    "تاريخ_التسجيل": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "حالة_الاطلاع": "قيد المراجعة"
                                }
                                df_rep_updated = pd.concat([df_rep, pd.DataFrame([new_rep_row])], ignore_index=True)
                                save_data_to_sheet("التقارير", df_rep_updated)
                                st.session_state.confirm_custom_show = False
                                st.session_state.show_add_custom_session = False
                                st.success("تم تسجيل الحصة غير المدرجة وطباعتها بنجاح!")
                                st.rerun()

                        with col_cno:
                            if st.button("❌ لا، إلغاء", key="btn_confirm_no_custom"):
                                st.session_state.confirm_custom_show = False
                                st.rerun()

                st.markdown("---")
                st.markdown("##### 📋 التقارير الجماعية المسجلة بملفك الشخصي:")
                df_rep_all = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
                t_reports = df_rep_all[
                    df_rep_all["اسم_الأستاذ"].astype(str).str.strip() == selected_teacher.strip()
                ]

                if not t_reports.empty:
                    cols_to_show_user = [c for c in ["رقم_التقرير", "اليوم", "التاريخ", "التوقيت", "القاعة", "المادة", "الفوج", "حالة_الاطلاع"] if c in t_reports.columns]
                    st.dataframe(t_reports[cols_to_show_user], use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد تقارير غياب جماعي مسجلة باسمك حالياً.")
            else:
                st.error("الرقم السري غير صحيح.")

# ----------------------------------------------------
# 3. تقرير غياب خاص بالأستاذ المتعاقد
# ----------------------------------------------------
elif menu_choice == "📝 تقرير غياب خاص بالأستاذ المتعاقد":
    role_choice = st.radio("اختر صفة الدخول للخدمة:", ["👨‍🏫 الدخول بصفة أستاذ", "👔 الدخول بصفة رئيس قسم"], horizontal=True, key="role_cont")
    st.markdown("---")

    if role_choice == "👔 الدخول بصفة رئيس قسم":
        render_dept_head_view("الغياب الجماعي للمتعاقد")
    else:
        st.markdown("### 📝 تسجيل تقرير غياب جماعي - أستاذ متعاقد")
        
        contract_teacher_name = st.text_input("اسم ولقب الأستاذ المتعاقد:", key="cont_name_input")

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

        c_day, c_date, c_time, c_room = st.columns(4)
        with c_day:
            cont_day = st.selectbox("اليوم:", DAYS_LIST, key="cont_day")
        with c_date:
            cont_date = st.date_input("التاريخ:", datetime.now(), key="cont_date")
        with c_time:
            cont_time = st.selectbox("التوقيت:", TIMES_LIST, key="cont_time")
        with c_room:
            cont_room = st.selectbox("القاعة / المدرج:", ROOMS_LIST, key="cont_room")

        can_submit_cont = (
            contract_teacher_name.strip() != "" and
            cont_stage != DEFAULT_OPTION and
            cont_year != DEFAULT_OPTION and
            cont_spec != DEFAULT_OPTION and
            cont_group != DEFAULT_OPTION and
            cont_day != DEFAULT_OPTION and
            cont_time != DEFAULT_OPTION and
            cont_room != DEFAULT_OPTION and
            cont_subject.strip() != ""
        )

        if contract_teacher_name.strip():
            contract_data = {
                "الطور": cont_stage if cont_stage != DEFAULT_OPTION else "",
                "السنة": cont_year if cont_year != DEFAULT_OPTION else "",
                "التخصص": cont_spec if cont_spec != DEFAULT_OPTION else "",
                "المادة": cont_subject,
                "الفوج": cont_group if cont_group != DEFAULT_OPTION else "",
                "اليوم": cont_day if cont_day != DEFAULT_OPTION else "",
                "التاريخ": str(cont_date),
                "التوقيت": cont_time if cont_time != DEFAULT_OPTION else "",
                "القاعة": cont_room if cont_room != DEFAULT_OPTION else ""
            }

            pdf_contract_data = create_pdf(contract_teacher_name, contract_data)

            st.markdown("<br>", unsafe_allow_html=True)
            if not can_submit_cont:
                st.warning("⚠ يرجى ملء كافة حقول الخيارات لتكشف زر التأكيد وتتمكن من التسجيل والطباعة.")
            else:
                if 'confirm_cont_show' not in st.session_state:
                    st.session_state.confirm_cont_show = False

                if st.button("🖨 تسجيل وطباعة التقرير (PDF)", key="btn_trigger_cont"):
                    st.session_state.confirm_cont_show = True

                if st.session_state.confirm_cont_show:
                    st.markdown("""
                        <div class="confirm-box">
                            <h4 style="color:#856404; margin-top:0;">⚠ هل أنت متأكد من أن المعلومات التي أدخلتها صحيحة؟</h4>
                        </div>
                    """, unsafe_allow_html=True)
                    col_confirm_yes, col_confirm_no = st.columns(2)
                    with col_confirm_yes:
                        if st.download_button(
                            label="✅ نعم، تأكيد وتسجيل",
                            data=pdf_contract_data,
                            file_name=f"تقرير_غياب_{contract_teacher_name}.pdf",
                            mime="application/pdf",
                            key="btn_confirm_yes_cont"
                        ):
                            df_rep = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
                            new_rep_id = len(df_rep) + 1
                            new_rep_row = {
                                "رقم_التقرير": new_rep_id,
                                "اسم_الأستاذ": contract_teacher_name.strip(),
                                "نوع_الأستاذ": "متعاقد",
                                "اليوم": cont_day,
                                "التاريخ": str(cont_date),
                                "التوقيت": cont_time,
                                "القاعة": cont_room,
                                "المادة": cont_subject,
                                "الطور": cont_stage,
                                "التخصص": cont_spec,
                                "السنة": cont_year,
                                "الفوج": cont_group,
                                "تاريخ_التسجيل": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "حالة_الاطلاع": "قيد المراجعة"
                            }
                            df_rep_updated = pd.concat([df_rep, pd.DataFrame([new_rep_row])], ignore_index=True)
                            save_data_to_sheet("التقارير", df_rep_updated)
                            st.session_state.confirm_cont_show = False
                            st.success("تم تسجيل تقرير الأستاذ المتعاقد وطباعته بنجاح!")
                            st.rerun()

                    with col_confirm_no:
                        if st.button("❌ لا، إلغاء", key="btn_confirm_no_cont"):
                            st.session_state.confirm_cont_show = False
                            st.rerun()

        if contract_teacher_name.strip():
            st.markdown("---")
            st.markdown("##### 📋 التقارير الجماعية المسجلة بملفك الشخصي:")
            df_rep_all = load_data_from_sheet("التقارير", REQUIRED_REPORT_COLS)
            t_reports = df_rep_all[
                df_rep_all["اسم_الأستاذ"].astype(str).str.strip() == contract_teacher_name.strip()
            ]

            if not t_reports.empty:
                cols_to_show_user = [c for c in ["رقم_التقرير", "اليوم", "التاريخ", "التوقيت", "القاعة", "المادة", "الفوج", "حالة_الاطلاع"] if c in t_reports.columns]
                st.dataframe(t_reports[cols_to_show_user], use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد تقارير غياب جماعي مسجلة باسمك حالياً.")

# ----------------------------------------------------
# 4. مفردات مواد عروض التكوين المحيّنة
# ----------------------------------------------------
elif menu_choice == "📚 مفردات مواد عروض التكوين المحيّنة":
    SYLLABUS_URL = "https://univformationlettre-rdkvfkdwl9usl5nyudsjkx.streamlit.app/"

    st.markdown("""
        <div class="notice-box">
            📚 <b>موقع مفردات مواد عروض التكوين المحيّنة</b><br>
            اضغط على الزر أدناه للانتقال المباشر لفتح منصة مفردات المواد في نافذة جديدة بسهولة وسرعة:
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.link_button(
        label="🚀 الانتقال إلى موقع مفردات المواد",
        url=SYLLABUS_URL,
        use_container_width=True
    )

# ----------------------------------------------------
# 5. طلب غياب فردي
# ----------------------------------------------------
elif menu_choice == "📩 طلب غياب":
    role_choice = st.radio("اختر صفة الدخول للخدمة:", ["👨‍🏫 الدخول بصفة أستاذ", "👔 الدخول بصفة رئيس قسم"], horizontal=True, key="role_req")
    st.markdown("---")

    if role_choice == "👔 الدخول بصفة رئيس قسم":
        render_dept_head_view("طلب الغياب")
    else:
        st.markdown("### 📩 بوابـة تسجيـل ومتابعـة طلبـات الغيـاب")

        col_auth1, col_auth2, col_auth3 = st.columns([2, 2, 1])
        with col_auth1:
            req_teacher_select = st.selectbox("اختر اسم الأستاذ:", [DEFAULT_OPTION] + teachers_list, key="req_teacher_sel")
        with col_auth2:
            req_teacher_pass = st.text_input("أدخل الرقم السري:", type="password", key="req_teacher_pass_input")
        with col_auth3:
            st.markdown('<div style="margin-top:28px;">', unsafe_allow_html=True)
            req_login_click = st.button("🔑 تسجيل الدخول", key="btn_req_login")
            st.markdown('</div>', unsafe_allow_html=True)

        is_authenticated = False
        if req_teacher_select != DEFAULT_OPTION and (req_teacher_pass or req_login_click):
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
                req_duration_type = st.selectbox("مدة الغياب:", [DEFAULT_OPTION, "يوم واحد", "أكثر من يوم"], key="req_dur_type")
            
            with col_m2:
                if req_duration_type == "يوم واحد":
                    single_date = st.date_input("تاريخ الغياب:", datetime.now(), key="req_single_date")
                    date_str = str(single_date)
                elif req_duration_type == "أكثر من يوم":
                    col_from, col_to = st.columns(2)
                    with col_from:
                        date_from = st.date_input("من تاريخ:", datetime.now(), key="req_date_from")
                    with col_to:
                        date_to = st.date_input("إلى تاريخ:", datetime.now(), key="req_date_to")
                    date_str = f"من {date_from} إلى {date_to}"
                else:
                    date_str = ""

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                req_comp = st.selectbox("تحديد طبيعة الغياب:", COMPENSATION_LIST, key="req_comp_select")
            with col_c2:
                req_reason = st.selectbox("سبب الغياب:", REASON_LIST, key="req_reason_select")

            req_reason_detail = ""
            if req_reason == "سبب آخر":
                req_reason_detail = st.text_input("توضيح السبب الآخر:", key="req_reason_detail_input")

            can_submit_req = (
                req_rank != DEFAULT_OPTION and
                req_duration_type != DEFAULT_OPTION and
                req_comp != DEFAULT_OPTION and
                req_reason != DEFAULT_OPTION
            )

            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                submit_disabled = st.session_state.req_submitted or (not can_submit_req)
                if st.button("✅ تسجيل الطلب", key="btn_submit_req", disabled=submit_disabled):
                    df_req = load_data_from_sheet("الطلبات", REQUIRED_REQ_COLS)
                    new_id = len(df_req) + 1
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
                    df_req_updated = pd.concat([df_req, pd.DataFrame([new_row])], ignore_index=True)
                    save_data_to_sheet("الطلبات", df_req_updated)
                    st.session_state.req_submitted = True
                    st.success("تم تسجيل طلبك بنجاح وهو الآن قيد الدراسة لدى رئيس القسم.")
                    st.rerun()

            with col_b2:
                if st.button("🗑 مسح الكل", key="btn_clear_req"):
                    st.session_state.req_submitted = False
                    st.rerun()

            st.markdown("---")
            st.markdown("##### 📋 قائمة الطلبات المسجلة بملفك الشخصي:")
            df_req_all = load_data_from_sheet("الطلبات", REQUIRED_REQ_COLS)
            user_requests = df_req_all[
                df_req_all["اسم_الأستاذ"].astype(str).str.strip() == req_teacher_select.strip()
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
