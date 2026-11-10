import streamlit as st
from ci_dashboard_support import require_session,execute,bundle,COMPONENT_LABELS

c=require_session(); o=c['observer']
if c['uid'] not in o.instructors:
    st.error('Konfigurasi khusus dosen.'); st.stop()
st.header('Konfigurasi laboratorium')
st.caption('Rahasia API dan konfigurasi login tidak ditampilkan atau disunting melalui dashboard.')
m=bundle(c)['metrics']
with st.form('weights'):
    st.subheader('Bobot indeks eksploratif')
    weights={k:st.number_input(COMPONENT_LABELS[k],min_value=0.0,max_value=100.0,value=float(v*100)) for k,v in m['weights'].items()}
    if st.form_submit_button('Simpan bobot untuk forum ini'):
        execute(lambda:o.lab.set_weights(c['uid'],c['chat'],weights))
st.caption('Bobot dinormalisasi. Membandingkan snapshot dengan bobot berbeda memerlukan kehati-hatian; komponen dan bobot disimpan pada setiap snapshot.')
with st.form('groups'):
    st.subheader('Kelompok yang ditetapkan manusia')
    nims=[r['NIM'] for r in o.roster()]
    nim=st.selectbox('NIM',nims)
    team=st.text_input('Nama kelompok')
    if st.form_submit_button('Simpan kelompok peserta'):
        execute(lambda:o.lab.set_group(c['uid'],c['chat'],nim,team))
st.text('Analisis: aturan lokal; tidak ada pengiriman ke LLM. Survei agregat minimum 5 responden. Retensi mengikuti CI_RETENTION_DAYS pada bot.')
