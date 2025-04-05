import folium
import polars as pl
import math
import psycopg2
import json
# DB接続設定
with open('./environment/local.json') as f:
    config = json.load(f)
conn = psycopg2.connect(
    host=config['postgres']['host'],
    user=config['postgres']['user'], 
    password=config['postgres']['password'],
    database=config['postgres']['dbname'],
    port=config['postgres']['port']
)

# SQLからデータを読み込む
start_date = '2025-04-05 00:00:00'
end_date = '2025-04-05 23:59:59'
query = f"""
SELECT latitude, longitude, wind_direction, wind_speed FROM weather.wind
WHERE measured_at >= '{start_date}' AND measured_at <= '{end_date}'
"""
with conn.cursor() as cursor:
    cursor.execute(query)
    result = cursor.fetchall()

conn.close()

# PolarsのDataFrameに変換
df = pl.DataFrame(result, schema=['latitude', 'longitude', 'wind_direction', 'wind_speed'])

# 地図の中心を設定
map_center = [df['latitude'].mean(), df['longitude'].mean()]

# Folium地図作成
m = folium.Map(location=map_center, zoom_start=14)

# 矢印を地図上に描画する関数
def add_wind_arrow(map_obj, lat, lon, direction_deg, speed):
    # 表示用スケール（必要に応じて調整）
    length_scale = 0.001
    rad = math.radians(direction_deg - 90)
    end_lat = lat + speed * length_scale * math.sin(rad)
    end_lon = lon + speed * length_scale * math.cos(rad)

    # 風向矢印を地図に追加
    folium.PolyLine(
        locations=[(lat, lon), (end_lat, end_lon)],
        color="blue",
        weight=3,
        opacity=0.8,
        tooltip=f'風向: {direction_deg}°, 風速: {speed} m/s'
    ).add_to(map_obj)

    # 測定点マーカーを追加
    folium.CircleMarker(
        location=(lat, lon),
        radius=3,
        color='red',
        fill=True,
        fill_opacity=0.8
    ).add_to(map_obj)

# 各測定データを地図に表示
for row in df.iter_rows(named=True):
    add_wind_arrow(m, row['latitude'], row['longitude'], row['wind_direction'], row['wind_speed'])

# 凡例を追加するためのHTMLを作成
legend_html = '''
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 150px; height: 90px; 
    background-color: white; z-index:9999; font-size:14px;
    border:2px solid grey; border-radius:5px;
    ">
    <h4 style="margin:10px;">凡例</h4>
    <p style="margin:10px;"> 
        <i style="background:blue; width:10px; height:10px; float:left; margin-right:5px;"></i> 風向矢印<br>
        <i style="background:red; width:10px; height:10px; float:left; margin-right:5px;"></i> 測定点
    </p>
</div>
'''

# 地図に凡例を追加
m.get_root().html.add_child(folium.Element(legend_html))

# 地図をHTML形式で保存
m.save('wind_map.html')
