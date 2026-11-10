import json
import streamlit as st
from ci_dashboard_support import require_session,execute,can_facilitate
from ci_lab import CHARTER_FIELDS

c=require_session(); o=c['observer']
st.header('Project Charter UAS')
charters=o.lab.charters(c['uid'],c['sid'])
if can_facilitate(c):
    sources=o.lab.confirmed_sources(c['sid'])
    st.caption(f'{len(sources)} keputusan dikonfirmasi tersedia pada sesi ini. Bagian editorial tetap rancangan, terpisah dari kebutuhan yang disepakati.')
    with st.form('charter_form'):
        title=st.text_input('Judul charter',value=charters[0]['title'] if charters else 'Aplikasi AI fasilitator Collective Intelligence')
        previous=json.loads(charters[0]['body'])['editorial'] if charters else {}
        labels=['Rumusan masalah','Pengguna sasaran','Kebutuhan nonfungsional','Fitur AI','Model data','Kriteria penerimaan','Paket pekerjaan','Roadmap implementasi']
        fields={key:st.text_area(label,value=previous.get(key,'')) for key,label in zip(CHARTER_FIELDS,labels)}
        version=charters[0]['version'] if charters else 0
        if st.form_submit_button('Simpan versi draf baru'):
            execute(lambda:o.lab.charter(c['uid'],c['sid'],title,fields,expected_version=version))
            charters=o.lab.charters(c['uid'],c['sid'])
if charters:
    chosen=st.selectbox('Versi charter',[r['id'] for r in charters],format_func=lambda i:next(f"C{i} · versi {r['version']} · {r['status']}" for r in charters if r['id']==i))
    text=o.lab.export_charter(c['uid'],chosen)
    st.text(text)
    st.download_button('Unduh Project Charter (Markdown)',text,file_name=f'charter-C{chosen}.md',mime='text/markdown')
    if c['uid'] in o.instructors and st.button('Setujui dokumen sebagai dosen'):
        execute(lambda:o.lab.approve_charter(c['uid'],chosen))
else:
    st.info('Belum ada charter. Konfirmasikan keputusan melalui Telegram sebelum menyusun draf.')
