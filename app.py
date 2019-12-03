from flask import Flask, render_template, request, send_from_directory
import pandas as pd
import altair as alt
import requests as r
from flask_paginate import Pagination, get_page_parameter, get_page_args

app = Flask(__name__)

#request API
url = "http://api.jakarta.go.id/v1/rumahsakitumum/"
url2 = "http://api.jakarta.go.id/v1/rumahsakitkhusus/"
url3 = "http://api.jakarta.go.id/v1/puskesmas/"
url4 = "http://api.jakarta.go.id/v1/kecamatan/?format=geojson"
key = "YMrdDYSy+NVIO+pyrf2I5yemyJFLKYIUqBX6b27Umjr3b76C/R38vgucK4cMAdhU"

response = r.get(url,
                headers={
                    "Authorization": key
                })
response2 = r.get(url2,
                headers={
                    "Authorization": key
                })
response3 = r.get(url3,
                headers={
                    "Authorization": key
                })
response4 = r.get(url4,
                headers={
                    "Authorization": key
                })

data = response.json()
data2 = response2.json()
data3 = response3.json()
data4 = response4.json()

tabel_kec = pd.io.json.json_normalize(data4['features']).filter(regex='properties')
rs_umum = pd.io.json.json_normalize(data['data'])
rs_khusus = pd.io.json.json_normalize(data2['data'])
puskesmas = pd.io.json.json_normalize(data3['data'])
rs_umum_merge = pd.merge(rs_umum, 
                     tabel_kec, 
                     how='left', 
                     left_on='kode_kecamatan',
                     right_on='properties.kode_kecamatan')
rs_khusus_merge = pd.merge(rs_khusus, 
                     tabel_kec, 
                     how='left', 
                     left_on='kode_kecamatan',
                     right_on='properties.kode_kecamatan')
rs_umum_merge.rename(columns={'jenis_rsu':'jenis_rs',
                    'nama_rsu':'nama_rs'},
                    inplace=True)
rs_khusus_merge.rename(columns={'jenis_rsk':'jenis_rs',
                    'nama_rsk':'nama_rs'},
                    inplace=True)
rs_jakarta = rs_umum_merge.append(rs_khusus_merge, ignore_index = True)
counties = alt.topo_feature('https://raw.githubusercontent.com/hariesramdhani/indonesia-cities-topojson/master/Jakarta%20Raya.json','IDN_adm_2_kabkota')
@app.route("/")
# This fuction for rendering the table
def index():
    df = rs_jakarta.copy()
    total = {
        'umum':rs_umum_merge.shape[0],
        'khusus':rs_khusus_merge.shape[0],
        'puskes':puskesmas.shape[0]
    }
    fasilitas = sum(total.values())
    return render_template('index.html', total=total, fasilitas=fasilitas)
  
# def total():
    
#     return total

@app.route('/map')
def map():
    return render_template('map.html')

@app.route("/kesehatan")
def kesehatan():
    imun = pd.read_csv('data/imunisasi1617.csv')
    return render_template("kesehatan.html")

@app.route("/keluarga")
def keluarga():
    imun = pd.read_csv('data/imunisasi1617.csv')
    return render_template("keluarga.html")

@app.route("/overview")
def overview():
    df = rs_jakarta.copy()

    
    imun = pd.read_csv('data/imunisasi1617.csv')
      #adding the data frame
    df.index +=1 #adding index in table
    PER_PAGE = 5 #limit data per page
    cols = ["jenis_rs","nama_rs","properties.nama_kecamatan",'properties.nama_kota','telepon','email','website']
    
    search = False
    q = request.args.get('q')
    if q:
        search = True
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    pagination = Pagination(page=page, total=len(df), search=search, record_name='records',per_page=PER_PAGE, show_single_page=True,css_framework='bootstrap4')
    return render_template('overview.html',new_tables=df[(page-1)*PER_PAGE:page*PER_PAGE][cols].to_html(classes='niceTable'),pagination=pagination)
    # return render_template('overview.html', rs=rs ,pagination=pagination, facility=fac)

def overview2():
    imun = pd.read_csv('data/imunisasi1617.csv') #adding the data frame
    imun.index +=1 #adding index in table
    PER_PAGE = 10 #limit data per page
    cols = ["tahun ","antigen","wilayah","jumlah_bayi"]
    
    search = False
    q = request.args.get('q')
    if q:
        search = True
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    pagination1 = Pagination(page=page, total=len(imun), search=search, record_name='records',per_page=PER_PAGE, show_single_page=True, css_framework='bootstrap4')

    return render_template('overview.html',tables=imun[(page-1)*PER_PAGE:page*PER_PAGE][cols].to_html(classes='niceTable'),pagination=pagination)

@app.route("/charts")
# This fuction for rendering the plot
def charts():
    #using altair library
    df = rs_jakarta.copy()
    prov = counties.copy()
    background = alt.Chart(prov).mark_geoshape(
        fill='lightgray',
        stroke='white'
    ).properties(
        width=900,
        height=500
    )
    points = alt.Chart(df).mark_circle(
        size=10,
        color='steelblue'
    ).encode(
        longitude='longitude:Q',
        latitude='latitude:Q',
        tooltip=['jenis_rs', 'nama_rs']
    )
    chart = alt.layer(background,points).configure_view(
        strokeWidth=0
    )
    return chart.to_json() 

@app.route("/ch_totrs")
# This fuction for rendering the plot
def ch_totrs():
    df = rs_jakarta.copy()
    df.drop(['id','kode_kecamatan','kode_kelurahan','kode_kota','kode_pos','location.latitude','location.longitude','properties.kode_kecamatan','properties.kode_kota','properties.kode_provinsi'],axis=1, inplace=True)
    df = df.rename(columns={"properties.nama_kecamatan": "nama_kecamatan", "properties.nama_kota": "nama_kota", "properties.nama_provinsi": "nama_provinsi", 'location.alamat':'alamat'})
    df[['nama_kota', 'nama_kecamatan']] = df[['nama_kota', 'nama_kecamatan']].fillna('Kepulauan Seribu')
    chart = alt.Chart(df).mark_bar().encode(
    y = alt.X('nama_kota',title='Nama Kota'),
    x = alt.Y('count()',title='Jumlah RS'),
    tooltip=['nama_kota','count()']
    )
    return chart.to_json()

@app.route("/ch_kelasrs")
# This fuction for rendering the plot
def ch_kelasrs():
    hos = pd.read_csv('data/fasilitasRS-2017.csv', encoding='latin')
    hos.drop(['kelurahan','kecamatan','kode_pos','no_telepon','no_faximile','alamat_website','alamat_email','nama_direktur/kepala_rs'], axis=1, inplace=True)
    hos = hos.fillna(0)
    hos = pd.concat([
        hos.select_dtypes(exclude='float64'),
        hos.select_dtypes(include='float64').apply(
            pd.Series.astype, dtype='int64'
        )
    ], axis=1)
    tes = hos.iloc[ : , [3,5,6,7,8,9,10]].groupby('kota_administrasi').sum().rename(
        columns= {
            'jml_tempat_tidur_per_kelas_vvip' : 'VVIP',
            'jml_tempat_tidur_per_kelas_vip' : 'VIP',
            'jml_tempat_tidur_per_kelas_eksekutif/utama' : 'Utama',
            'jml_tempat_tidur_per_kelas_kelas_i' : 'KelasI',
            'jml_tempat_tidur_per_kelas_kelas_ii' : 'KelasII',
            'jml_tempat_tidur_per_kelas_kelas_iii' : 'KelasIII'
        }
    )
    tes=tes.reset_index(level='kota_administrasi', col_level=0)

    df_adm_new = pd.melt(tes,id_vars=['kota_administrasi'], value_vars = ['VVIP','VIP','Utama','KelasI','KelasII','KelasIII'], var_name='Kelas',value_name='Total_Kamar')

    kelas = list(df_adm_new.Kelas.unique())
    input_dropdown = alt.binding_select(options=kelas)
    select_kelas = alt.selection_single(name='Select', fields=['Kelas'],
                                   bind=input_dropdown, init={'kelas': 'VIP'})
    chart = alt.Chart(df_adm_new).mark_bar().encode(
        y = 'kota_administrasi:O',
        x = 'Total_Kamar:Q',
        tooltip=['Kelas','Total_Kamar']
        ).add_selection(select_kelas
        ).transform_filter(select_kelas
    )
    return chart.to_json()

@app.route("/ch_imun")
    # This fuction for rendering the plot
def ch_imun():
    imun = pd.read_csv('data/imunisasi1617.csv')
    imun['tahun '] = imun['tahun '].astype('category')
    ant = list(imun.antigen.unique())
    input_dropdown = alt.binding_select(options=ant)
    select_ant = alt.selection_single(name='Select', fields=['antigen'],
                                     bind=input_dropdown, init={'antigen': 'BCG'})
    chart = alt.Chart(imun).mark_bar().encode(
        x='tahun ',
        y='jumlah_bayi:Q',
        color='tahun :N',
        column='wilayah:N',
        tooltip=['wilayah','jumlah_bayi']
    ).add_selection(select_ant
    ).transform_filter(select_ant
    )
    return chart.to_json()

@app.route('/ch_persenbayi')
def layanan_bayi():
    bayi = pd.read_csv('data/persen_layanan_bayi.csv')
    bayi = bayi.rename(columns={'kota_administrasi':'administrasi'})
    bayi.administrasi.unique().tolist()
    input_dropdown = alt.binding_select(options=bayi.administrasi.unique().tolist())
    selection = alt.selection_single(fields=['administrasi'], bind=input_dropdown, name='Kota', init={'administrasi': 'Jakarta Pusat'})
    color = alt.condition(selection,
                        alt.Color('administrasi:N', legend=None),
                        alt.value('lightgray'))
    base = alt.Chart(bayi).encode(
        x='tahun:O',
        y='persentase_pelayanan_kesehatan_bayi',
        color=color,
        tooltip = ['tahun','persentase_pelayanan_kesehatan_bayi']
    )
    line = base.mark_line().add_selection(
        selection
    )
    point = base.mark_point()
    chart = (line + point).properties(width=500, height=200)
    return chart.to_json()

@app.route('/ch_popbayi')
def populasi_bayi():
    alt.data_transformers.disable_max_rows()
    kelahiran_bayi = pd.read_csv('data/data_kelahiran_bayi.csv')
    pd.options.display.float_format = '{:,.0f}'.format
    kelahiran_bayi['jenis_kelamin'] = kelahiran_bayi['jenis_kelamin'].replace({'Laki-Laki': 'Laki-laki'})
    kelahiran_bayi.dropna(inplace=True)
    cross_bayi = pd.crosstab(index=kelahiran_bayi.jenis_kelamin,
                            columns=kelahiran_bayi.bulan,
                            values=kelahiran_bayi.jumlah,
                            aggfunc='sum')
    cross_bayi=cross_bayi.stack().reset_index().rename(columns={0:'jumlah'})

    slider = alt.binding_range(min=1, max=12, step=1)
    select_bulan = alt.selection_single(name='kelahiran', fields=['bulan'],
                                    bind=slider, init={'bulan': 1})

    base = alt.Chart(kelahiran_bayi).add_selection(
        select_bulan
    ).transform_filter(
        select_bulan
    ).transform_calculate(
        jk=alt.expr.if_(alt.datum.jenis_kelamin == 'Laki-laki', 'Laki-laki', 'Perempuan')
    ).properties(
        width=250
    )

    color_scale = alt.Scale(domain=['Laki-laki', 'Perempuan'],
                            range=['#1f77b4', '#e377c2'])

    left = base.transform_filter(
        alt.datum.jk == 'Perempuan'
    ).encode(
        y=alt.Y('nama_kabupaten:N', axis=None),
        x=alt.X('sum(jumlah):Q',
                sort=alt.SortOrder('descending'),title=None),
        tooltip=['sum(jumlah)'],
        color=alt.Color('jenis_kelamin:N', scale=color_scale, legend=None)
    ).mark_bar().properties(title='Perempuan')

    middle = base.encode(
        y=alt.Y('nama_kabupaten:N', axis=None),
        text=alt.Text('nama_kabupaten:N'),
    ).mark_text().properties(width=20)

    right = base.transform_filter(
        alt.datum.jk == 'Laki-laki'
    ).encode(
        y=alt.Y('nama_kabupaten:N', axis=None),
        x=alt.X('sum(jumlah):Q',title=None),
        tooltip=['sum(jumlah)'],
        color=alt.Color('jenis_kelamin:N', scale=color_scale, legend=None)
    ).mark_bar().properties(title='Laki-laki')

    cross_jum = alt.Chart(cross_bayi).mark_bar().encode(
        y=alt.Y('jenis_kelamin', title=None),
        x=alt.X('sum(jumlah):Q', title='Total Kelahiran'),
        tooltip=['sum(jumlah)'],
        color=alt.Color('jenis_kelamin:N', scale=color_scale, legend=None)
        ).add_selection(
        select_bulan
    ).transform_filter(
        select_bulan).properties(
        width=630
    )

    con=alt.concat(left, middle, right, spacing=5)
    chart= con & cross_jum
    return chart.to_json()

@app.route('/ch_kbaktif')
def ch_kbaktif():
    aktif_kb = pd.read_csv('data/data_peserta_aktif_kb.csv')
    chart = alt.Chart(aktif_kb).mark_point().encode(
        x=alt.X('jumlah:Q', title='Jumlah'),
        y=alt.Y('metode_kontrasepsi:N', title='Metode Kontrasepsi'),
        color='jenis_fasilitasi_kesehatan:N',
        tooltip=['jenis_fasilitasi_kesehatan','jumlah','bulan '],
        facet='wilayah:O'
    ).properties(
        columns=3
    )
    return chart.to_json()

@app.route('/ch_faskes_kb')
def ch_faskes_kb():
    faskes = pd.read_csv('data/faskes-kb.csv')
    faskes=pd.melt(faskes,id_vars=['wilayah','jenis_fasilitas_kesehatan_kb'],value_vars=['jumlah_yang_ada','jumlah_yang_dilaporkan']).rename(columns={'variable':'status','value':'jumlah','jenis_fasilitas_kesehatan_kb':'jenis_faskes'}).replace({'jumlah_yang_ada': 'Tersedia','jumlah_yang_dilaporkan':'Dilaporkan'})
    faskes.columns
    jenis_faskes = list(faskes.jenis_faskes.unique())
    input_dropdown = alt.binding_select(options=jenis_faskes)
    select_faskes = alt.selection_single(name='Select', fields=['jenis_faskes'],
                                        bind=input_dropdown, init={'jenis_faskes': 'Fasilitas Kesehatan KB Pemerintah'})

    chart = alt.Chart(faskes).mark_bar().encode(
            x='jumlah:Q',
            y=alt.Y('status:N', title=None),
            color=alt.condition(select_faskes,
                            alt.Color('status:N', legend = None),
                           alt.value('lightgray')),
            row='wilayah:N',
            tooltip=['wilayah','jumlah']
        ).add_selection(select_faskes
        ).transform_filter(select_faskes
        ).configure_header(labelPadding = 3
        ).configure_facet(spacing=35
    )
    return chart.to_json()

if __name__ == '__main__':
    app.run(threaded=True, port=5000)
