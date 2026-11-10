import streamlit as st
from ci_dashboard_support import context,bundle,execute,can_facilitate
from ci_lab import PHASES

c=context(); o=c['observer']
st.header('Ikhtisar laboratorium')
if can_facilitate(c):
    with st.form('new_session'):
        title=st.text_input('Judul sesi',value='Laboratorium spesifikasi UAS')
        if st.form_submit_button('Mulai sesi baru'):
            execute(lambda:o.lab.start(c['uid'],c['chat'],title,synthetic=c['demo']))
            st.info('Muat ulang halaman untuk memilih sesi baru.')
if c['sid'] is not None:
    s=o.lab.session(c['sid']); data=bundle(c); m=data['metrics']
    st.subheader(s['title'])
    st.text(s['objective'])
    st.caption(f"Fase {s['phase']} · {'Selesai' if s['ended'] else 'Aktif'} · kohort {m['students']} mahasiswa")
    with st.container(horizontal=True):
        st.metric('Pesan tercatat',m['messages'],border=True)
        st.metric('Peserta teramati',f"{m['active']}/{m['students']}",border=True)
        st.metric('Keputusan dikonfirmasi',len(m['decisions']['confirmed']),border=True)
        st.metric('Indeks eksploratif','Belum cukup data' if m['index'] is None else f"{m['index']:.1f}/100",border=True)
    if can_facilitate(c) and not s['ended']:
        with st.form('phase'):
            phase=st.selectbox('Fase TAIDA',PHASES,index=PHASES.index(s['phase']))
            if st.form_submit_button('Simpan fase'):
                execute(lambda:o.lab.phase(c['uid'],c['sid'],phase))
        if st.button('Tutup sesi dan simpan snapshot'):
            execute(lambda:o.lab.close(c['uid'],c['sid']))
    st.subheader('Keputusan dan alternatif')
    with o.db() as db:
        st.text(o.facilitator.rounds_text(db,c['chat']))
    st.subheader('Cuplikan percakapan sesi')
    for row in data['messages'][-5:]:
        st.text(f"{row['Bukti']} · {row['Peserta']}: {row['Teks'][:280]}")
    st.info(m['limitation'])
else:
    st.info('Mulai sesi dengan peran fasilitator. Bot dan forum tetap dapat berjalan sebelum ada sesi laboratorium.')
