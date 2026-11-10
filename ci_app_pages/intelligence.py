import pandas as pd
import streamlit as st
from ci_dashboard_support import require_session,bundle,execute,can_facilitate,COMPONENT_LABELS

c=require_session(); o=c['observer']; b=bundle(c); m=b['metrics']
st.header('Perkembangan kecerdasan kolektif')
st.info(m['limitation'])
st.caption(f"Cakupan komponen yang tersedia: {m['coverage']:.0%}. Sedikitnya 6 pesan mahasiswa diperlukan untuk indeks.")
if can_facilitate(c) and st.button('Simpan snapshot pengamatan'):
    execute(lambda:o.lab.capture(c['sid']))
    b=bundle(c)
rows=[{'Waktu':pd.to_datetime(r['captured'],unit='s',utc=True),'Indeks':r['index'],
       'Partisipasi (%)':100*r['components']['participation'] if r['components']['participation'] is not None else None,
       'Cakupan (%)':100*r['coverage']} for r in b['timeline'] if r['evidence_valid']]
if any(not r['evidence_valid'] for r in b['timeline']):
    st.caption('Snapshot dengan sumber yang berubah/hilang tidak dimasukkan ke grafik.')
if rows:
    st.line_chart(pd.DataFrame(rows),x='Waktu',y=['Indeks','Partisipasi (%)','Cakupan (%)'],alt='Riwayat indeks eksploratif, partisipasi, dan cakupan data')
    valid=[r for r in b['timeline'] if r['evidence_valid']]
    first,last=valid[0],valid[-1]
    if first['index'] is not None and last['index'] is not None:
        st.metric('Perubahan deskriptif awal–akhir',f"{last['index']-first['index']:+.1f} poin")
        st.caption('Perbedaan waktu, bobot, sampel, dan aktivitas dapat menjelaskan perubahan; bukan bukti sebab-akibat.')
st.dataframe([{'Komponen':COMPONENT_LABELS[k],'Nilai 0–1':v,'Bobot':m['weights'][k]} for k,v in m['components'].items()],hide_index=True,alt='Komponen dan bobot indeks eksploratif')
st.subheader('Modal sosial observasional')
st.dataframe([{'Indikator':k,'Nilai':str(v) if v is not None else 'Tidak tersedia'} for k,v in m['social'].items()],hide_index=True,alt='Indikator balasan timbal balik, bonding, bridging, linking, dan cakupan kelompok')
st.caption('Bonding/bridging memerlukan pemetaan kelompok eksplisit. Linking merujuk balasan mahasiswa–staf konfigurasi. Angka ini bukan pengukuran trust.')
st.subheader('Survei persepsi sukarela')
survey_rows=[]
for stage in ['pra','pasca']:
    survey=b['surveys'][stage]
    row={'Tahap':stage,'Responden':survey['n']}
    row.update({label:survey['means'][key] if survey['means'] else None for key,label in [('trust','Trust'),('heard','Rasa didengar'),('safety','Rasa aman'),('willingness','Kesediaan bekerja sama')]})
    survey_rows.append(row)
st.dataframe(survey_rows,hide_index=True,alt='Rata-rata survei persepsi pra dan pasca dengan jumlah responden dan perlindungan minimum lima orang')
paired=b['surveys']['paired']
if paired['delta']:
    st.caption(f"Perubahan berpasangan ({paired['n']} peserta yang sama): "+', '.join(f"{label} {paired['delta'][key]:+.2f}" for key,label in [('trust','trust'),('heard','didengar'),('safety','aman'),('willingness','kerja sama')]))
else:
    st.caption('Belum ada lima pasangan respons pra–pasca untuk menampilkan perubahan persepsi.')
st.caption('Rata-rata dan perubahan berpasangan hanya ditampilkan untuk sedikitnya 5 responden. Tidak mencampur persepsi dengan indikator teks.')
