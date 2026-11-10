import pandas as pd
import streamlit as st
from ci_dashboard_support import require_session,bundle

c=require_session(); data=bundle(c)['messages']
st.header('Penjelajah percakapan')
st.caption('Pseudonim bukan anonimitas penuh; isi pesan dapat mengungkap identitas. Asesmen pribadi tidak dimuat di tabel kolektif.')
if data:
    df=pd.DataFrame(data)
    df['Waktu UTC']=pd.to_datetime(df['Waktu UTC'],unit='s',utc=True)
    people=st.multiselect('Peserta (pseudonim)',sorted(df['Peserta'].unique()))
    categories=st.multiselect('Kategori kontribusi',sorted({a.strip() for value in df['Kategori'] for a in value.split(',')}))
    phrase=st.text_input('Cari teks')
    dates=st.date_input('Rentang tanggal UTC',(df['Waktu UTC'].min().date(),df['Waktu UTC'].max().date()))
    if people: df=df[df['Peserta'].isin(people)]
    if categories: df=df[df['Kategori'].apply(lambda value:any(a in [x.strip() for x in value.split(',')] for a in categories))]
    if phrase: df=df[df['Teks'].str.contains(phrase,case=False,regex=False)]
    if isinstance(dates,(list,tuple)) and len(dates)==2:
        df=df[(df['Waktu UTC'].dt.date>=dates[0])&(df['Waktu UTC'].dt.date<=dates[1])]
    st.dataframe(df,hide_index=True,alt='Pesan forum yang difilter dengan ID bukti, waktu, pseudonim, kategori, dan relasi balasan')
    st.download_button('Unduh percakapan terfilter (CSV)',df.to_csv(index=False),file_name='percakapan-ci.csv',mime='text/csv')
else:
    st.info('Belum ada percakapan pada sesi ini.')
