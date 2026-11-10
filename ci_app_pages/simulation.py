import json
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from ci_dashboard_support import context,execute
from ci_lab_simulator import run_experiment,ASSUMPTIONS
from ci_observer import Observer

c=context()
if not c['demo'] and c['uid'] not in c['observer'].instructors:
    st.error('Eksperimen kelas hanya untuk dosen.'); st.stop()
st.header('Simulasi multi-agen dan eksperimen')
st.info(ASSUMPTIONS)
with st.form('experiment'):
    seed=st.number_input('Seed',value=42,min_value=0,step=1)
    steps=st.slider('Langkah percakapan',40,200,80,step=20)
    policies=st.multiselect('Kebijakan yang dibandingkan',['none','inclusive','bridge'],default=['none','inclusive','bridge'])
    submitted=st.form_submit_button('Jalankan eksperimen lokal')
if submitted:
    results=[]
    with st.spinner('Menjalankan agen, replay, dan evaluasi pada database sintetik terpisah…'):
        for policy in policies:
            folder=Path(tempfile.mkdtemp(prefix='kipp-ci-experiment-'))
            observer,sid=run_experiment(folder/'experiment.sqlite3',int(seed),policy,int(steps))
            results.append({'path':str(observer.path),'session':sid,'policy':policy,'seed':int(seed)})
    st.session_state.ci_experiments=results
results=st.session_state.get('ci_experiments',[])
if results:
    summaries=[]
    for entry in results:
        path=Path(entry['path']); o=Observer(path,path.with_suffix('.participants.csv'),chats={-999},instructors={9999})
        m=o.lab.metrics(entry['session'])
        summaries.append({'Kebijakan':entry['policy'],'Seed':entry['seed'],'Peserta teramati':m['active'],'Indeks eksploratif':m['index'],
                          'Bridging':m['social']['bridging_edges'],'Pasangan timbal balik':m['social']['mutual_dyads'],'Keputusan dikonfirmasi':len(m['decisions']['confirmed'])})
    st.dataframe(summaries,hide_index=True,alt='Perbandingan hasil sintetik kebijakan tanpa intervensi, inklusif, dan lintas kelompok')
    chosen=st.selectbox('Replay eksperimen',range(len(results)),format_func=lambda i:results[i]['policy'])
    entry=results[chosen]; path=Path(entry['path']); o=Observer(path,path.with_suffix('.participants.csv'),chats={-999},instructors={9999})
    with o.db() as db:
        record=dict(db.execute('SELECT * FROM ci_v3_simulations WHERE session_id=?',(entry['session'],)).fetchone())
    events=json.loads(record['events'])
    step=st.slider('Langkah replay (langkah terakhir memuat keputusan)',0,len(events)+1,len(events)+1)
    session=o.lab.session(entry['session'])
    until=session['ended'] if step>len(events) else session['started']+(events[step-1]['offset'] if step else 0)
    replay=o.lab.metrics(entry['session'],until)
    with st.container(horizontal=True):
        st.metric('Pesan pada langkah',replay['messages'],border=True)
        st.metric('Peserta teramati',replay['active'],border=True)
        st.metric('Keputusan dikonfirmasi',len(replay['decisions']['confirmed']),border=True)
    st.dataframe(pd.DataFrame([{'Fase':e['phase'],'Kelompok':e['group'],'Agen sintetik':e['uid'],'Teks':e['text']} for e in events[:min(step,len(events))]]),hide_index=True,alt='Replay pesan agen sintetik sesuai langkah terpilih')
    st.download_button('Unduh eksperimen sintetik (JSON)',json.dumps(record,ensure_ascii=False,indent=2),file_name='eksperimen-sintetik.json',mime='application/json')
else:
    st.caption('Jalankan eksperimen untuk membandingkan kebijakan dan memutar ulang percakapan. Tidak ada pesan dikirim ke Telegram.')
