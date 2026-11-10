"""Run: .venv/bin/python -m streamlit run ci_dashboard.py --server.address 127.0.0.1"""
import os
from pathlib import Path
import streamlit as st
from app import load_env_file
from ci_dashboard_support import demo_context, live_context

st.set_page_config(page_title='TISE Collective Intelligence Laboratory',layout='wide')
st.title('TISE Collective Intelligence Laboratory')
st.caption('CI · pengetahuan bersama | NI · penilaian manusia | AI · dukungan analisis')
load_env_file(Path(__file__).resolve().parent/'.env')
mode=os.environ.get('CI_DASHBOARD_MODE','demo')
if mode not in {'demo','live'}:
    st.error('CI_DASHBOARD_MODE harus demo atau live.')
    st.stop()
o,uid,demo=demo_context() if mode=='demo' else live_context()
if demo:
    st.warning('DEMO SINTETIK — agen berbasis aturan dan database terpisah. Hasil bukan data atau karakter mahasiswa nyata.')
else:
    st.caption('DATA KELAS · akses sesuai identitas OIDC yang dipetakan server')
if not o.chats:
    st.info('Operator perlu mengisi CI_CHAT_IDS.')
    st.stop()
chat=st.sidebar.selectbox('Forum',sorted(o.chats),key='ci_forum')
sessions=o.lab.sessions(uid,chat)
options=[s['id'] for s in sessions]
sid=st.sidebar.selectbox('Sesi',options,format_func=lambda value:next(f"S{r['id']} · {r['title']}" for r in sessions if r['id']==value),key='ci_session') if options else None
if st.sidebar.button('Muat ulang data'):
    st.cache_data.clear()
st.session_state.ci_context={'observer':o,'uid':uid,'chat':chat,'sid':sid,'demo':demo}
facilitator=o.is_facilitator(uid,chat)
pages=[st.Page('ci_app_pages/overview.py',title='Ikhtisar',icon=':material/home:'),
       st.Page('ci_app_pages/intelligence.py',title='Perkembangan CI',icon=':material/trending_up:'),
       st.Page('ci_app_pages/conversation.py',title='Penjelajah percakapan',icon=':material/forum:'),
       st.Page('ci_app_pages/assessment.py',title='Refleksi dan survei',icon=':material/person:'),
       st.Page('ci_app_pages/charter.py',title='Project Charter UAS',icon=':material/description:')]
if facilitator:
    pages.append(st.Page('ci_app_pages/cockpit.py',title='Kokpit fasilitator',icon=':material/groups:'))
if demo or uid in o.instructors:
    pages.append(st.Page('ci_app_pages/simulation.py',title='Simulasi multi-agen',icon=':material/science:'))
if uid in o.instructors:
    pages.append(st.Page('ci_app_pages/settings.py',title='Konfigurasi',icon=':material/settings:'))
st.navigation(pages,position='sidebar').run()
