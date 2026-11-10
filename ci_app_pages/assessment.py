import json
import pandas as pd
import streamlit as st
from ci_dashboard_support import require_session,execute

c=require_session(); o=c['observer']; target=c['uid']
st.header('Refleksi pribadi dan survei')
if c['uid'] in o.instructors:
    ids={int(r['ID']):r['Nama'] for r in o.roster() if (r.get('ID') or '').isdigit()}
    ids[c['uid']]='Akun dosen'
    target=st.selectbox('Bukti peserta (akses dosen)',list(ids),format_func=lambda i:ids[i])
rows=o.lab.personal(c['uid'],c['sid'],target)
st.metric('Kontribusi pada sesi',len(rows))
if rows:
    timeline=pd.DataFrame([{'Waktu UTC':pd.to_datetime(r['timestamp'],unit='s',utc=True),'Pesan':1} for r in rows])
    activity=timeline.set_index('Waktu UTC').resample('10min').sum().reset_index()
    st.bar_chart(activity,x='Waktu UTC',y='Pesan',alt='Jumlah kontribusi milik peserta pada setiap interval sepuluh menit')
    st.caption('Grafik aktivitas deskriptif; frekuensi pesan tidak menunjukkan kualitas kompetensi.')
for row in rows[-15:]:
    with st.expander(f"M{row['id']} · {row['text'][:90]}"):
        st.text(row['text'])
        if row['result']: st.json(json.loads(row['result']))
        else: st.caption('Belum dianalisis; fasilitator dapat menjalankan /analisis.')
st.caption('Tidak ada rata-rata nilai pesan atau kesimpulan karakter. Gunakan /tinjau melalui Telegram untuk meminta koreksi dosen.')
st.subheader('Survei diri sukarela')
st.caption('Urutan: persepsi trust, rasa didengar, rasa aman menyampaikan pendapat, dan kesediaan bekerja sama. Ini persepsi diri, bukan penilaian dosen.')
if st.button('Saya setuju pada penggunaan data lokal sesuai pengantar bot'):
    execute(lambda:o.command(c['uid'],o.identity(c['uid']),{'id':c['uid'],'type':'private'},'/setuju',''))
with st.form('survey'):
    stage=st.selectbox('Waktu survei',['pra','pasca'])
    values=[st.slider(label,1,5,3) for label in ['Trust','Rasa didengar','Rasa aman','Kesediaan bekerja sama']]
    if st.form_submit_button('Simpan survei saya'):
        execute(lambda:o.lab.survey(c['uid'],c['sid'],stage,values))
