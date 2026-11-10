"""Run: streamlit run uts_review.py --server.address 127.0.0.1"""
import os
from pathlib import Path
import streamlit as st
from llm import load_env_file, resolve_project_path
from uts_manual import (COMPONENTS, read_csv, latest, history, portfolio_links,
                        save_review, export_csv, ai_suggestions)

st.set_page_config(page_title='Penilaian manual UTS', layout='wide')
st.title('Penilaian manual UTS')
st.caption('Nilai dosen untuk pra-UTS dan lima sesi • skala 0–100')
ROOT = Path(__file__).resolve().parent
load_env_file(ROOT / '.env')
participant_path = resolve_project_path(ROOT, os.environ.get('PESERTA_CSV', 'peserta.csv'))
queue_path = resolve_project_path(ROOT, os.environ.get('ANTRIAN_CSV', 'antrian.csv'))
input_dir = resolve_project_path(ROOT, os.environ.get('LLM_INPUT_DIR', 'assessment-inputs'))
report_dir = resolve_project_path(ROOT, os.environ.get('LLM_REPORT_DIR', 'assessment-results'))
store = resolve_project_path(ROOT, os.environ.get('UTS_MANUAL_FILE', 'uts-manual-reviews.json'))
try:
    participants = sorted(read_csv(participant_path), key=lambda p: p['NIM'])
    queue = read_csv(queue_path) if queue_path.exists() else []
    reviews = latest(store)
except (OSError, ValueError, KeyError) as exc:
    st.error(f'Data tidak dapat dibaca: {exc}')
    st.stop()
if not participants:
    st.info('Belum ada peserta.')
    st.stop()
if st.sidebar.button('Muat ulang data'):
    for key in list(st.session_state):
        if str(key).startswith('review_'):
            del st.session_state[key]
    st.rerun()
st.sidebar.caption('Muat ulang membuang perubahan formulir yang belum disimpan.')
labels = {p['NIM']: f"{p['NIM']} — {p['Nama']}" for p in participants}
selected_student = st.sidebar.selectbox('Mahasiswa', list(labels.values()), key='student_selector')
nim = selected_student.split(' — ', 1)[0]
p = next(p for p in participants if p['NIM'] == nim)
tickets = sorted([r for r in queue if r['nim'] == nim and r['week'].upper() == 'W08'],
                 key=lambda r: int(r['tiket']), reverse=True)
ticket_id = st.selectbox('Tiket UTS', [r['tiket'] for r in tickets], key='ticket_'+nim) if tickets else ''
ticket = next((r for r in tickets if r['tiket'] == ticket_id), None)
if not tickets:
    st.info('Belum ada tiket W08. Penilaian tetap dapat disimpan untuk mahasiswa ini.')
index_url, links = portfolio_links(p, ticket, input_dir)
if index_url:
    st.link_button('Buka indeks portfolio W08', index_url)
else:
    st.warning('Repo belum terdaftar atau URL tidak valid. Periksa peserta.csv.')
if ticket:
    st.caption(f"Status antrean: {ticket['status']}")
previous = reviews.get(nim, {})
revision = previous.get('revision', 0)
key = f'review_{nim}_{ticket_id}_{revision}'
st.info('Pra-UTS berbobot 10%; setiap sesi 18%. Kosong berarti belum dinilai. '
        'Hasil manual disimpan terpisah dari hasil AI dan status antrean.')
if previous:
    st.caption(f"Tersimpan: {previous['status']} • revisi {revision} • "
               f"{previous['assessor']} • tiket {previous['ticket'] or '—'}")
suggestions, ai_message = ai_suggestions(report_dir, ticket_id, nim)
if ai_message:
    st.caption(ai_message)
st.caption('Adopsi AI hanya mengisi nilai sesi; klik Simpan draf atau Finalisasi untuk menyimpan.')
with st.form(key):
    assessor = st.text_input('Nama dosen', value=previous.get('assessor', ''), key=key+'_assessor')
    scores, notes = {}, {}
    for component, label in COMPONENTS.items():
        with st.container(border=True):
            st.subheader(label)
            for caption, url in links.get(component, []):
                st.link_button(caption, url)
            suggestion = suggestions.get(component)
            if component == 'paper':
                st.caption('Pra-UTS dinilai manual oleh dosen; tidak ada usulan nilai AI.')
            elif suggestion:
                ai_score = suggestion['score']
                st.metric('Usulan AI /100', f'{ai_score:.2f}' if ai_score is not None else 'BT')
                st.caption('Evidence: ' + suggestion['evidence_status'])
                st.write(suggestion['summary'])
                st.caption('Prioritas perbaikan: ' + suggestion['improvement_priority'])
                adopt = st.form_submit_button('Adopsi nilai AI — ' + label,
                    key=key+'_adopt_'+component, disabled=ai_score is None)
                if adopt and ai_score is not None:
                    st.session_state[key+'_'+component] = ai_score
                if ai_score is None:
                    st.caption('BT belum dapat diadopsi sebagai nilai angka.')
            else:
                st.caption('Usulan AI sesi ini belum tersedia.')
            old = previous.get('scores', {}).get(component)
            st.session_state.setdefault(key+'_'+component, float(old) if old is not None else None)
            scores[component] = st.number_input('Nilai '+label, min_value=0.0, max_value=100.0,
                value=None, step=1.0,
                placeholder='Belum dinilai', key=key+'_'+component)
            notes[component] = st.text_area('Catatan '+label,
                value=previous.get('notes', {}).get(component, ''), key=key+'_note_'+component)
    draft = st.form_submit_button('Simpan draf')
    final = st.form_submit_button('Finalisasi nilai manual', type='primary')
if draft or final:
    try:
        saved = save_review(store, nim=nim, name=p['Nama'], ticket=ticket_id, scores=scores,
                            notes=notes, assessor=assessor, final=final, expected_revision=revision)
        st.session_state['saved_notice'] = f"Nilai {nim} disimpan sebagai {saved['status']}."
        st.rerun()
    except (ValueError, OSError) as exc:
        st.error(str(exc))
if 'saved_notice' in st.session_state:
    st.success(st.session_state.pop('saved_notice'))
if previous:
    st.metric('Total berbobot /100', previous['total'] if previous['total'] is not None else 'Belum lengkap')
    with st.expander('Riwayat penilaian mahasiswa'):
        st.dataframe([dict(Revisi=r['revision'], Status=r['status'], Dosen=r['assessor'],
                           Total=r['total'], Waktu=r['updated_at'])
                      for r in history(store) if r['nim'] == nim], hide_index=True)
st.divider()
st.subheader('Rekap penilaian manual')
st.caption('Draf dan final dibedakan pada kolom Status. Finalisasi tidak mengubah antrean atau nilai mingguan.')
st.dataframe([{'NIM': r['nim'], 'Nama': r['name'], **r['scores'],
               'Total': r['total'], 'Status': r['status'], 'Dosen': r['assessor']}
              for r in reviews.values()], hide_index=True)
st.download_button('Unduh rekap CSV', export_csv(reviews), 'uts-manual.csv', 'text/csv')
