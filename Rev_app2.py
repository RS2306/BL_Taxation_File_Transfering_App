
import streamlit as st
import pandas as pd
import os
import io
import hashlib
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="BL Taxation File Transfering App",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================
# BRANDING
# =============================
APP_NAME = "BL Taxation File Transfering App"
APP_SUBTITLE = "Taxation Department — Balmer Lawrie & Co. Ltd."
ADMIN_EMP_ID = "11653"
ADMIN_NAME = "RAJA SAHA"
ADMIN_EMAIL = "caraja.saha@gmail.com"
DEFAULT_BUCKET = "BL Tax Vault"

# =============================
# SECRETS / CONFIG
# =============================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GMAIL_APP_PASSWORD = st.secrets.get("GMAIL_APP_PASSWORD", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing SUPABASE_URL or SUPABASE_KEY in Streamlit secrets.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# CSS
# =============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 45%, #e94560 100%);
    color: white;
    padding: 2rem 2.3rem;
    border-radius: 18px;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}
.main-header h1 { margin: 0; font-size: 2rem; font-weight: 800; }
.main-header p { margin: 0.35rem 0 0; opacity: 0.9; }

.stat-row { display: flex; gap: 1rem; margin-bottom: 1.3rem; flex-wrap: wrap; }
.stat-card {
    flex: 1; min-width: 160px; background: white; border-radius: 14px;
    padding: 1.2rem 1.2rem; box-shadow: 0 3px 14px rgba(0,0,0,0.07); border-top: 4px solid;
}
.stat-card.blue { border-color: #4361ee; }
.stat-card.green { border-color: #06d6a0; }
.stat-card.orange { border-color: #fb8500; }
.stat-card.red { border-color: #e94560; }
.stat-card .val { font-size: 2rem; font-weight: 800; line-height: 1; color: #1a1a2e; }
.stat-card .lbl { font-size: 0.78rem; color: #777; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.5px; }

.file-card {
    background: white; border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06); border-left: 5px solid #4361ee;
}
.file-card .fn { font-size: 0.98rem; font-weight: 700; color: #1a1a2e; }
.file-card .meta { font-size: 0.8rem; color: #777; margin-top: 0.2rem; }
.file-card .from { font-size: 0.82rem; color: #4361ee; margin-top: 0.2rem; font-weight: 600; }

.sec-title {
    font-size: 1.05rem; font-weight: 800; color: #1a1a2e; margin: 1rem 0 0.6rem;
    padding-bottom: 0.35rem; border-bottom: 2px solid #e9ecef;
}
.badge {
    display: inline-block; padding: 0.12rem 0.55rem; border-radius: 999px; font-size: 0.72rem;
    font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;
}
.badge-blue { background: #dbeafe; color: #1d4ed8; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-orange { background: #ffedd5; color: #c2410c; }
.badge-red { background: #fee2e2; color: #991b1b; }
.badge-purple { background: #ede9fe; color: #6d28d9; }

section[data-testid="stSidebar"] { background: #1a1a2e !important; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.08) !important; color: white !important; border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important; width: 100% !important; margin-bottom: 0.25rem !important;
}
section[data-testid="stSidebar"] .stButton button:hover { background: rgba(233,69,96,0.35) !important; border-color: #e94560 !important; }
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def human_size(n: int) -> str:
    n = float(n or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_ts(ts):
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).strftime("%d %b %Y, %I:%M %p")
    except:
        return str(ts)


def file_ext_badge(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "file"
    cmap = {"py":"blue","zip":"orange","json":"purple","html":"orange","htm":"orange","pdf":"red","csv":"green","xlsx":"green","xls":"green","txt":"green"}
    cls = cmap.get(ext, "blue")
    return f'<span class="badge badge-{cls}">.{ext}</span>'


def get_db(table: str, select: str = "*"):
    return supabase.table(table).select(select)


def get_employee(emp_id: str):
    r = supabase.table("employees").select("*").eq("emp_id", emp_id).execute()
    return r.data[0] if r.data else None


def get_active_employees():
    r = supabase.table("employees").select("emp_id,employee_name,email_id,is_admin,is_active").eq("is_active", True).order("employee_name").execute()
    return r.data or []


def ensure_admin():
    emp = get_employee(ADMIN_EMP_ID)
    if not emp:
        supabase.table("employees").insert({
            "emp_id": ADMIN_EMP_ID,
            "employee_name": ADMIN_NAME,
            "email_id": ADMIN_EMAIL,
            "password_hash": hash_pw(ADMIN_EMP_ID),
            "is_admin": True,
            "is_active": True
        }).execute()


def upload_to_supabase_storage(file_name: str, file_bytes: bytes, sender_emp_id: str):
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    storage_path = f"{sender_emp_id}/{ts}_{safe_name}"
    bucket = DEFAULT_BUCKET
    supabase.storage.from_(bucket).upload(storage_path, file_bytes, file_options={"content-type": mimetypes.guess_type(file_name)[0] or "application/octet-stream", "upsert": "false"})
    return storage_path


def download_from_storage(storage_path: str) -> bytes:
    return supabase.storage.from_(DEFAULT_BUCKET).download(storage_path)


def delete_from_storage(storage_path: str):
    try:
        supabase.storage.from_(DEFAULT_BUCKET).remove([storage_path])
    except:
        pass


def create_shared_file(sender_emp_id, sender_name, filename, storage_path, size_bytes, mime_type, file_hash, note, recipient_ids):
    res = supabase.table("shared_files").insert({
        "sender_emp_id": sender_emp_id,
        "sender_name": sender_name,
        "original_filename": filename,
        "storage_path": storage_path,
        "file_size_bytes": int(size_bytes),
        "mime_type": mime_type,
        "file_hash": file_hash,
        "note": note
    }).execute()
    file_id = res.data[0]["id"]
    rows = [{"file_id": file_id, "recipient_emp_id": rid} for rid in recipient_ids]
    if rows:
        supabase.table("file_recipients").insert(rows).execute()
    return file_id


def inbox_for(emp_id: str):
    r = supabase.rpc("get_inbox_for_emp", {"p_emp_id": emp_id}).execute()
    return r.data or []


def sent_by(emp_id: str):
    r = supabase.table("shared_files").select("*").eq("sender_emp_id", emp_id).order("created_at", desc=True).execute()
    return r.data or []


def recipient_count(file_id: int):
    r = supabase.table("file_recipients").select("id", count="exact").eq("file_id", file_id).eq("recipient_deleted", False).execute()
    return r.count or 0


def log_activity(emp_id: str, action: str, details: str):
    try:
        supabase.table("file_activity_log").insert({"emp_id": emp_id, "action_type": action, "details": details}).execute()
    except:
        pass


def send_email_notification(to_emails: list, sender_name: str, filenames: list, note: str = ""):
    if not GMAIL_APP_PASSWORD:
        return False, "GMAIL_APP_PASSWORD not configured"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📂 {sender_name} shared {len(filenames)} file(s) — {APP_NAME}"
        msg["From"] = ADMIN_EMAIL
        msg["To"] = ", ".join(to_emails)
        lis = "".join(f"<li><strong>{f}</strong></li>" for f in filenames)
        note_html = f"<p><strong>Note:</strong> {note}</p>" if note else ""
        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:620px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.1)">
            <div style="background:linear-gradient(135deg,#1a1a2e,#0f3460,#e94560);padding:2rem;color:white;text-align:center">
                <h1 style="margin:0;font-size:1.5rem">📂 {APP_NAME}</h1>
                <p style="margin:0.5rem 0 0;opacity:0.9">{APP_SUBTITLE}</p>
            </div>
            <div style="padding:1.8rem">
                <p><strong>{sender_name}</strong> shared the following file(s) with you:</p>
                <ul style="line-height:1.9">{lis}</ul>
                {note_html}
                <p>Please login to the app and open your Inbox to download.</p>
                <div style="margin-top:1rem;padding:0.8rem 1rem;background:#f8f9fa;border-radius:8px;font-size:0.82rem;color:#777">Auto-generated notification.</div>
            </div>
        </div>
        """
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(ADMIN_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(ADMIN_EMAIL, to_emails, msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)

# =============================
# SESSION STATE
# =============================
for k, v in {"logged_in": False, "emp_id": None, "emp_data": None, "page": "inbox"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

ensure_admin()

# =============================
# UI COMPONENTS
# =============================
def login_screen():
    st.markdown(f"""
    <div style="text-align:center;margin-top:3rem;margin-bottom:2rem">
        <div style="display:inline-block;background:linear-gradient(135deg,#1a1a2e,#0f3460,#e94560);border-radius:50%;width:84px;height:84px;line-height:84px;font-size:2.6rem;color:white;box-shadow:0 8px 30px rgba(233,69,96,0.35)">📂</div>
        <h1 style="font-size:2rem;font-weight:800;color:#1a1a2e;margin:0.9rem 0 0.2rem">{APP_NAME}</h1>
        <p style="color:#777;font-size:0.95rem;margin:0">{APP_SUBTITLE}</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.1, 1])
    with c2:
        with st.container(border=True):
            st.markdown("#### 🔐 Employee Login")
            emp_id = st.text_input("Employee ID", placeholder="e.g. 11653")
            password = st.text_input("Password", type="password", placeholder="Default password = Employee ID")
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                emp_id = emp_id.strip()
                emp = get_employee(emp_id)
                if emp and emp.get("is_active") and emp["password_hash"] == hash_pw(password):
                    st.session_state.logged_in = True
                    st.session_state.emp_id = emp_id
                    st.session_state.emp_data = emp
                    st.session_state.page = "inbox"
                    st.rerun()
                else:
                    st.error("Invalid Employee ID or Password.")
        st.caption("Default password is your Employee ID. Change it after login.")


def sidebar_nav():
    emp = st.session_state.emp_data
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:1.1rem 0 1rem">
            <div style="background:linear-gradient(135deg,#e94560,#fb8500);border-radius:50%;width:54px;height:54px;line-height:54px;font-size:1.5rem;margin:0 auto 0.6rem;color:white">👤</div>
            <div style="font-size:0.95rem;font-weight:800;color:white">{emp['employee_name']}</div>
            <div style="font-size:0.75rem;color:#94a3b8">ID: {emp['emp_id']}</div>
            {"<div style='margin-top:0.35rem'><span style='background:#e94560;color:white;border-radius:999px;padding:0.12rem 0.65rem;font-size:0.7rem;font-weight:800'>ADMIN</span></div>" if emp.get('is_admin') else ""}
        </div>
        <hr style="border-color:rgba(255,255,255,0.12)"/>
        """, unsafe_allow_html=True)

        items = [("📥 Inbox", "inbox"), ("📤 Send Files", "send"), ("📋 Sent History", "sent"), ("🔑 Change Password", "password")]
        if emp.get("is_admin"):
            items.insert(3, ("👥 Employee Master", "employees"))
            items.insert(4, ("📊 Admin Dashboard", "admin"))
        for label, key in items:
            prefix = "→ " if st.session_state.page == key else ""
            if st.button(f"{prefix}{label}", key=f"nav_{key}"):
                st.session_state.page = key
                st.rerun()
        st.markdown("<hr style='border-color:rgba(255,255,255,0.12)'/>", unsafe_allow_html=True)
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.emp_id = None
            st.session_state.emp_data = None
            st.session_state.page = "inbox"
            st.rerun()
        st.markdown(f"<p style='color:#94a3b8;font-size:0.72rem;text-align:center;margin-top:1rem'>{APP_NAME}</p>", unsafe_allow_html=True)


# =============================
# PAGES
# =============================
def page_inbox():
    emp_id = st.session_state.emp_id
    st.markdown(f"""
    <div class="main-header">
        <h1>📥 My Inbox</h1>
        <p>Files shared with you</p>
    </div>
    """, unsafe_allow_html=True)

    r = supabase.rpc("get_inbox_for_emp", {"p_emp_id": emp_id}).execute()
    items = r.data or []

    if not items:
        st.info("Your inbox is empty.")
        return

    for f in items:
        cols = st.columns([7, 1.15, 1.15])
        with cols[0]:
            st.markdown(f"""
            <div class="file-card">
                <div class="fn">{file_ext_badge(f['original_filename'])} &nbsp; {f['original_filename']}</div>
                <div class="meta">📏 {human_size(f['file_size_bytes'])} &nbsp; | &nbsp; 🕐 {fmt_ts(f['created_at'])}</div>
                <div class="from">👤 Shared by: {f['sender_name']}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            try:
                b = download_from_storage(f["storage_path"])
                st.download_button("⬇️ Download", data=b, file_name=f["original_filename"], use_container_width=True, key=f"dl_{f['file_recipient_id']}")
            except Exception:
                st.caption("Missing file")
        with cols[2]:
            if st.button("🗑️ Remove", use_container_width=True, key=f"rm_{f['file_recipient_id']}"):
                supabase.table("file_recipients").update({"recipient_deleted": True}).eq("id", f["file_recipient_id"]).execute()
                log_activity(emp_id, "recipient_delete", f"Removed from inbox: {f['original_filename']}")
                st.success("Removed from your inbox.")
                st.rerun()


def page_send():
    emp = st.session_state.emp_data
    st.markdown("""
    <div class="main-header" style="background:linear-gradient(135deg,#06d6a0,#118ab2,#073b4c)">
        <h1>📤 Send Files</h1>
        <p>Share any type of file with one or more employees</p>
    </div>
    """, unsafe_allow_html=True)

    employees = [e for e in get_active_employees() if e["emp_id"] != emp["emp_id"]]
    if not employees:
        st.warning("No recipient employees found. Admin should upload the employee master list first.")
        return

    label_map = {f"{e['employee_name']} (ID: {e['emp_id']})": e['emp_id'] for e in employees}

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-title">📎 Upload Files</div>', unsafe_allow_html=True)
        uploads = st.file_uploader("Choose files", accept_multiple_files=True, label_visibility="collapsed")
        if uploads:
            st.caption(f"{len(uploads)} file(s) selected")
    with c2:
        st.markdown('<div class="sec-title">👥 Select Recipients</div>', unsafe_allow_html=True)
        selected = st.multiselect("Recipients", options=list(label_map.keys()), label_visibility="collapsed")

    note = st.text_area("Optional message", placeholder="Add a note for recipients...", height=90)

    if st.button("🚀 Send Files Now", use_container_width=True, type="primary"):
        if not uploads:
            st.error("Please upload at least one file.")
            return
        if not selected:
            st.error("Please select at least one recipient.")
            return

        recipient_ids = [label_map[x] for x in selected]
        recipient_emails = [e["email_id"] for e in employees if e["emp_id"] in recipient_ids]
        sent_names = []
        prog = st.progress(0, text="Uploading...")
        for i, uf in enumerate(uploads):
            b = uf.read()
            file_hash = hashlib.sha256(b).hexdigest()
            content_type = mimetypes.guess_type(uf.name)[0] or "application/octet-stream"
            storage_path = upload_to_supabase_storage(uf.name, b, emp["emp_id"])
            create_shared_file(emp["emp_id"], emp["employee_name"], uf.name, storage_path, len(b), content_type, file_hash, note, recipient_ids)
            sent_names.append(uf.name)
            prog.progress((i + 1) / len(uploads), text=f"Uploaded {i+1}/{len(uploads)}")

        ok, err = send_email_notification(recipient_emails, emp["employee_name"], sent_names, note)
        log_activity(emp["emp_id"], "send_files", f"Sent {len(sent_names)} file(s) to {len(recipient_ids)} recipient(s)")
        st.success(f"Shared {len(sent_names)} file(s) with {len(recipient_ids)} recipient(s).")
        if ok:
            st.info("Email notifications sent.")
        else:
            st.warning(f"Files shared, but email failed: {err}")


def page_sent():
    emp_id = st.session_state.emp_id
    st.markdown("""
    <div class="main-header" style="background:linear-gradient(135deg,#7209b7,#3a0ca3,#4361ee)">
        <h1>📋 Sent History</h1>
        <p>Files you have shared</p>
    </div>
    """, unsafe_allow_html=True)

    r = supabase.table("shared_files").select("*").eq("sender_emp_id", emp_id).order("created_at", desc=True).execute()
    items = r.data or []
    if not items:
        st.info("No sent files yet.")
        return

    for f in items:
        rc = supabase.table("file_recipients").select("id").eq("file_id", f["id"]).eq("recipient_deleted", False).execute()
        active_recipients = rc.data or []
        cols = st.columns([7, 1.2, 1.2])
        with cols[0]:
            st.markdown(f"""
            <div class="file-card">
                <div class="fn">{file_ext_badge(f['original_filename'])} &nbsp; {f['original_filename']}</div>
                <div class="meta">📏 {human_size(f['file_size_bytes'])} &nbsp; | &nbsp; 🕐 {fmt_ts(f['created_at'])}</div>
                <div class="from">👥 Active recipients: {len(active_recipients)}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            if st.button("🗑️ Delete All", use_container_width=True, key=f"del_{f['id']}"):
                supabase.table("file_recipients").delete().eq("file_id", f["id"]).execute()
                supabase.table("shared_files").delete().eq("id", f["id"]).execute()
                delete_from_storage(f["storage_path"])
                log_activity(emp_id, "sender_delete", f"Deleted file for all: {f['original_filename']}")
                st.success("Deleted for all recipients.")
                st.rerun()
        with cols[2]:
            if st.button("⬇️ Download", use_container_width=True, key=f"sd_{f['id']}"):
                st.download_button("Download now", data=download_from_storage(f["storage_path"]), file_name=f["original_filename"], key=f"dl_sent_{f['id']}")


def page_employees():
    if not st.session_state.emp_data.get("is_admin"):
        st.error("Access denied.")
        return
    st.markdown("""
    <div class="main-header" style="background:linear-gradient(135deg,#fb8500,#e94560,#1a1a2e)">
        <h1>👥 Employee Master</h1>
        <p>Upload and manage eligible employees</p>
    </div>
    """, unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Current Employees", "Upload Excel/CSV", "Add Manually"])
    with t1:
        r = supabase.table("employees").select("emp_id,employee_name,email_id,is_admin,is_active").order("employee_name").execute()
        df = pd.DataFrame(r.data or [])
        if not df.empty:
            df["Role"] = df["is_admin"].apply(lambda x: "Admin" if x else "Employee")
            st.dataframe(df[["emp_id","employee_name","email_id","Role","is_active"]], use_container_width=True, hide_index=True)
        else:
            st.info("No employees found.")

    with t2:
        up = st.file_uploader("Upload employee list", type=["xlsx", "csv"], key="emp_upload")
        if up is not None:
            df = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            required = {"emp_id", "employee_name", "email_id"}
            if not required.issubset(set(df.columns)):
                st.error("File must contain emp_id, employee_name, email_id")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                if st.button("Import Employees", type="primary"):
                    added = skipped = 0
                    for _, row in df.iterrows():
                        eid = str(row["emp_id"]).strip()
                        if get_employee(eid):
                            skipped += 1
                        else:
                            supabase.table("employees").insert({
                                "emp_id": eid,
                                "employee_name": str(row["employee_name"]).strip(),
                                "email_id": str(row["email_id"]).strip().lower(),
                                "password_hash": hash_pw(eid),
                                "is_admin": False,
                                "is_active": True
                            }).execute()
                            added += 1
                    st.success(f"Imported {added} employee(s). Skipped {skipped} existing employee(s).")
                    log_activity(ADMIN_EMP_ID, "import_employees", f"Imported {added}, skipped {skipped}")

    with t3:
        with st.form("add_emp"):
            c1, c2 = st.columns(2)
            with c1:
                eid = st.text_input("Employee ID *")
                name = st.text_input("Employee Name *")
            with c2:
                email = st.text_input("Email ID *")
                is_admin = st.checkbox("Grant Admin Access")
            submitted = st.form_submit_button("Add Employee", use_container_width=True)
        if submitted:
            if not eid or not name or not email:
                st.error("All fields are required.")
            elif get_employee(eid):
                st.warning("Employee already exists.")
            else:
                supabase.table("employees").insert({
                    "emp_id": eid.strip(),
                    "employee_name": name.strip(),
                    "email_id": email.strip().lower(),
                    "password_hash": hash_pw(eid.strip()),
                    "is_admin": bool(is_admin),
                    "is_active": True
                }).execute()
                st.success(f"Added {name}. Default password = {eid.strip()}")


def page_admin_dashboard():
    if not st.session_state.emp_data.get("is_admin"):
        st.error("Access denied.")
        return
    st.markdown("""
    <div class="main-header">
        <h1>📊 Admin Dashboard</h1>
        <p>Overview of file sharing activity</p>
    </div>
    """, unsafe_allow_html=True)

    emp_count = supabase.table("employees").select("id", count="exact").execute().count or 0
    file_count = supabase.table("shared_files").select("id", count="exact").execute().count or 0
    rec_count = supabase.table("file_recipients").select("id", count="exact").execute().count or 0
    total_size = supabase.table("shared_files").select("file_size_bytes").execute().data or []
    total_bytes = sum(x.get("file_size_bytes", 0) for x in total_size)

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card blue"><div class="val">{emp_count}</div><div class="lbl">Employees</div></div>
        <div class="stat-card green"><div class="val">{file_count}</div><div class="lbl">Files Shared</div></div>
        <div class="stat-card orange"><div class="val">{rec_count}</div><div class="lbl">Deliveries</div></div>
        <div class="stat-card red"><div class="val">{human_size(total_bytes)}</div><div class="lbl">Storage Used</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-title">Recent Activity</div>', unsafe_allow_html=True)
    r = supabase.table("file_activity_log").select("*").order("created_at", desc=True).limit(50).execute()
    df = pd.DataFrame(r.data or [])
    if not df.empty:
        df["created_at"] = df["created_at"].apply(fmt_ts)
        st.dataframe(df[["emp_id","action_type","details","created_at"]], use_container_width=True, hide_index=True)
    else:
        st.info("No activity yet.")


def page_password():
    st.markdown("""
    <div class="main-header" style="background:linear-gradient(135deg,#1a1a2e,#4361ee)">
        <h1>🔑 Change Password</h1>
        <p>Update your login password</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.1, 1])
    with c2:
        with st.container(border=True):
            cur = st.text_input("Current Password", type="password")
            new1 = st.text_input("New Password", type="password")
            new2 = st.text_input("Confirm New Password", type="password")
            if st.button("Update Password", use_container_width=True, type="primary"):
                emp = get_employee(st.session_state.emp_id)
                if emp["password_hash"] != hash_pw(cur):
                    st.error("Current password is incorrect.")
                elif len(new1) < 6:
                    st.error("Password should be at least 6 characters.")
                elif new1 != new2:
                    st.error("Passwords do not match.")
                else:
                    supabase.table("employees").update({"password_hash": hash_pw(new1)}).eq("emp_id", st.session_state.emp_id).execute()
                    st.session_state.emp_data = get_employee(st.session_state.emp_id)
                    st.success("Password updated successfully.")

# =============================
# MAIN
# =============================
def main():
    if not st.session_state.logged_in:
        login_screen()
        return
    sidebar_nav()
    page = st.session_state.page
    if page == "inbox":
        page_inbox()
    elif page == "send":
        page_send()
    elif page == "sent":
        page_sent()
    elif page == "employees":
        page_employees()
    elif page == "admin":
        page_admin_dashboard()
    elif page == "password":
        page_password()
    else:
        page_inbox()

main()
