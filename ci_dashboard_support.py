"""Server-side dashboard context, identity resolution, and bounded caching."""
import os
import tempfile
from pathlib import Path

import streamlit as st
from ci_observer import Observer
from ci_lab_simulator import run_experiment

ROOT=Path(__file__).resolve().parent
COMPONENT_LABELS={'participation':'Partisipasi','balance':'Pemerataan kontribusi','knowledge':'Kontribusi pengetahuan','deliberation':'Deliberasi','action':'Keputusan dan tindakan','reciprocity':'Timbal balik'}


def configured_ids(name):
    return {int(x.strip()) for x in os.environ.get(name,'').split(',') if x.strip()}


def resolve_identity(claims, mappings):
    issuer,subject=claims.get('iss'),claims.get('sub')
    if not isinstance(issuer,str) or not isinstance(subject,str):
        raise PermissionError('Identitas OIDC tidak memiliki issuer dan subject.')
    value=mappings.get(issuer+'|'+subject)
    if value is None or isinstance(value,bool):
        raise PermissionError('Identitas login belum dipetakan ke ID Telegram oleh operator.')
    return int(value)


def demo_context():
    if 'ci_demo_path' not in st.session_state:
        directory=Path(tempfile.mkdtemp(prefix='kipp-ci-v3-demo-'))
        observer,sid=run_experiment(directory/'demo.sqlite3',42,'inclusive',80)
        st.session_state.ci_demo_path=str(observer.path)
    path=Path(st.session_state.ci_demo_path)
    role=st.sidebar.selectbox('Peran simulasi',['Dosen','Fasilitator','Mahasiswa'],key='ci_demo_role')
    uid={'Dosen':9999,'Fasilitator':1000,'Mahasiswa':1001}[role]
    observer=Observer(path,path.with_suffix('.participants.csv'),chats={-999},staff={1000},instructors={9999})
    return observer,uid,True


def live_context():
    try:
        configured=bool(st.secrets.get('auth'))
    except FileNotFoundError:
        configured=False
    if not configured:
        st.info('Mode kelas memerlukan OIDC dan pemetaan issuer|subject ke ID Telegram pada .streamlit/secrets.toml. Lihat panduan v3.')
        st.stop()
    if not st.user.is_logged_in:
        st.info('Masuk dengan akun yang dipetakan operator untuk membuka data kelas.')
        if st.button('Masuk',type='primary'):
            st.login()
        st.stop()
    try:
        uid=resolve_identity(dict(st.user),dict(st.secrets.get('ci_users',{})))
    except (PermissionError,ValueError) as exc:
        st.error(str(exc))
        st.stop()
    if st.sidebar.button('Keluar'):
        st.logout()
        st.stop()
    def location(name,default):
        p=Path(os.environ.get(name,default))
        return p if p.is_absolute() else ROOT/p
    observer=Observer(location('CI_DATABASE','ci.sqlite3'),location('PESERTA_CSV','peserta.csv'),
                      chats=configured_ids('CI_CHAT_IDS'),staff=configured_ids('CI_FACILITATOR_IDS'),
                      instructors=configured_ids('CI_INSTRUCTOR_IDS'))
    if observer.identity(uid) is None:
        st.error('ID Telegram tidak lagi terdaftar atau tidak memiliki peran staf.')
        st.stop()
    return observer,uid,False


def context():
    return st.session_state.ci_context


def require_session():
    c=context()
    if c['sid'] is None:
        st.info('Belum ada sesi. Fasilitator dapat memulai sesi melalui halaman Ikhtisar atau /sesi mulai JUDUL di Telegram.')
        st.stop()
    return c


def can_facilitate(c):
    return c['observer'].is_facilitator(c['uid'],c['chat'])


def execute(action):
    try:
        result=action()
        st.success('Tersimpan.' if result is None else str(result))
        st.cache_data.clear()
        return result
    except (PermissionError,ValueError) as exc:
        st.error(str(exc))
        return None


@st.cache_data(ttl=10,max_entries=64,show_spinner=False)
def collective_data(path,roster,uid,chat,sid,staff,instructors,revision):
    observer=Observer(Path(path),Path(roster),chats={chat},staff=staff,instructors=instructors)
    observer.lab.authorize(uid,chat)
    if observer.lab.session(sid)['chat_id']!=chat:
        raise PermissionError('Sesi tidak berada pada forum terpilih.')
    return {'metrics':observer.lab.metrics(sid),'timeline':observer.lab.timeline(uid,sid),
            'messages':observer.lab.conversations(uid,sid),'surveys':observer.lab.survey_summary(sid)}


def bundle(c):
    o=c['observer']
    o.lab.authorize(c['uid'],c['chat'])
    # Current authorization runs before any cached data is returned.
    revision=(o.path.stat().st_mtime_ns,o.participants.stat().st_mtime_ns)
    return collective_data(str(o.path),str(o.participants),c['uid'],c['chat'],c['sid'],
                           tuple(sorted(o.staff)),tuple(sorted(o.instructors)),revision)
