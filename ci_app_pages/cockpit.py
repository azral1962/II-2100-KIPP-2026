import streamlit as st
from ci_dashboard_support import require_session,can_facilitate,execute

c=require_session(); o=c['observer']
if not can_facilitate(c):
    st.error('Peran fasilitator tidak lagi aktif.'); st.stop()
st.header('Kokpit fasilitator')
st.text(o.facilitator.report(c['chat']))
st.caption('Indikator versi 2 memakai 200 pesan forum terbaru; metrik sesi laboratorium memakai periode sesi yang dipilih.')
st.subheader('Peserta belum teramati pada sesi')
st.dataframe(o.lab.unheard(c['uid'],c['sid']),hide_index=True,alt='Daftar peserta yang belum memiliki pesan tercatat dalam periode sesi, khusus fasilitator')
st.caption('Gunakan untuk undangan yang memberi pilihan; bukan bukti ketidakaktifan atau dasar nilai.')
if st.button('Analisis dan simpan perkembangan sesi'):
    execute(lambda:o.command(c['uid'],o.identity(c['uid']),{'id':c['chat'],'type':'supergroup'},'/analisis',''))
st.subheader('Intervensi dengan persetujuan manusia')
user=o.identity(c['uid']); chat={'id':c['uid'],'type':'private'}
st.text(o.facilitator.command(c['uid'],user,chat,c['chat'],'/intervensi',''))
with st.form('intervention'):
    number=st.number_input('ID intervensi',min_value=1,step=1)
    action=st.selectbox('Tindakan',['terapkan','alternatif','abaikan'])
    body=st.text_area('Teks pengganti (opsional saat menerapkan)')
    if st.form_submit_button('Jalankan tindakan fasilitator'):
        execute(lambda:o.facilitator.command(c['uid'],user,chat,c['chat'],'/'+action,str(number)+(' '+body if body and action=='terapkan' else '')))
st.caption('Pengiriman ke Telegram dilakukan proses ci.py pada polling berikutnya; dashboard tidak mengirim langsung.')
