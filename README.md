# BL Taxation File Transfering App

## Run locally
```bash
pip install streamlit pandas supabase pyjwt openpyxl
streamlit run app.py
```

## Streamlit Secrets
Create `.streamlit/secrets.toml` with:
```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "your-anon-key"
GMAIL_APP_PASSWORD = "your-gmail-app-password"
```

## Supabase setup
1. Run `supabase_setup.sql` in SQL Editor.
2. Create a private bucket named `taxvault-files`.
3. Add the admin employee with emp_id `11653` if not created automatically.

## Login
- Employee ID: `11653`
- Password: `11653`
