# -*- coding: utf-8 -*-
"""
调用高德地图 POI 搜索 API（仿照 api_request_example.py 的写法）

使用前：
  1. 到高德开放平台 https://lbs.amap.com 注册并创建「Web服务」类型的 Key
  2. 把下面的 API_KEY 替换成你自己的 Key
  3. 修改下方的搜索关键词和城市

依赖：
  pip install requests pandas
  （可选可视化）pip install geopandas folium matplotlib
"""

import os
import sys
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from pprint import pprint

# 让 Windows 控制台能正确输出 ✓/✗/中文（避免 GBK 编码报错）
sys.stdout.reconfigure(encoding="utf-8")

# 设置中文字体（避免图表中文乱码）
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ============ 1. 配置区（按需修改） ============

API_KEY = "e076780c454b0c98d57a27ff820707e0"      # ← 改成你自己的 Key
BASE_URL = "https://restapi.amap.com/v5/place/text"

KEYWORDS = ["大学", "地铁站", "博物馆", "电影院"]   # 要搜索的 POI 类型
CITY = "南京"                                      # 搜索城市
DISTRICT = "栖霞区"                                 # 区县专项搜索（第 9 节）

# 颜色映射：按 KEYWORDS 顺序自动分配，改关键词不用改颜色
COLOR_PALETTE = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "darkgreen"]
COLORS = {kw: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, kw in enumerate(KEYWORDS)}

# 重点分析对象（第 4.3 节分页搜索 + 第 7 节深入分析）
FOCUS_POI = KEYWORDS[0]


# ============ 2. 核心：封装 POI 搜索函数 ============

def search_poi(keywords, city=CITY, api_key=API_KEY, page_size=20):
    """
    搜索 POI

    参数:
        keywords:  搜索关键词（如 '大学'、'医院'）
        city:      城市名称
        api_key:   高德 API 密钥
        page_size: 每页返回数量（最大 50）

    返回:
        pandas.DataFrame，含 名称/地址/经度/纬度/类型/行政区划 等列
    """
    params = {
        "key": api_key,
        "keywords": keywords,
        "city": city,
        "output": "json",
        "page_size": page_size,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)

        if response.status_code != 200:
            print(f"✗ HTTP 请求失败: {response.status_code}")
            return pd.DataFrame()

        data = response.json()

        # 高德返回的 status 为 "1" 表示成功
        if data.get("status") != "1" or "pois" not in data:
            print(f"✗ API 返回错误: {data.get('info', '未知错误')}")
            return pd.DataFrame()

        # 逐条提取有用字段
        rows = []
        for poi in data["pois"]:
            location = poi.get("location", "")
            lon, lat = (location.split(",") + [None, None])[:2] if location else (None, None)

            rows.append({
                "名称": poi.get("name"),
                "地址": poi.get("address"),
                "经度": lon,
                "纬度": lat,
                "类型": poi.get("type"),
                "行政区划": poi.get("adname"),
            })

        df = pd.DataFrame(rows)
        print(f"✓ 搜索「{keywords}」成功，找到 {len(df)} 个 POI")
        return df

    except requests.exceptions.Timeout:
        print("✗ 请求超时")
        return pd.DataFrame()
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        return pd.DataFrame()


# ============ 3. 分页搜索（获取更多数据） ============

def search_poi_with_pagination(keywords, city=CITY, api_key=API_KEY, max_count=100):
    """分页获取更多 POI（高德默认每页 20 条，单次最多 50 条）"""
    all_pois = []
    page, page_size = 1, 50

    while len(all_pois) < max_count:
        params = {
            "key": api_key,
            "keywords": keywords,
            "city": city,
            "output": "json",
            "page_size": page_size,
            "page": page,
        }
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            if response.status_code != 200:
                break
            data = response.json()
            if data.get("status") != "1" or "pois" not in data:
                break

            pois = data["pois"]
            if not pois:
                break
            all_pois.extend(pois)

            if len(pois) < page_size:
                break
            page += 1
            time.sleep(0.2)   # 控制请求频率
        except Exception as e:
            print(f"✗ 错误: {e}")
            break

    rows = []
    for poi in all_pois[:max_count]:
        location = poi.get("location", "")
        lon, lat = (location.split(",") + [None, None])[:2] if location else (None, None)
        rows.append({
            "名称": poi.get("name"),
            "地址": poi.get("address"),
            "经度": lon,
            "纬度": lat,
            "类型": poi.get("type"),
            "行政区划": poi.get("adname"),
        })
    return pd.DataFrame(rows)


def search_poi_in_district(keywords, district=DISTRICT, city=CITY, api_key=API_KEY):
    """
    在指定区县搜索 POI（例如「北京东城区」的博物馆）

    返回:
        pandas.DataFrame
    """
    params = {
        "key": api_key,
        "keywords": keywords,
        "city": f"{city}{district}",
        "output": "json",
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        if response.status_code != 200:
            return pd.DataFrame()
        data = response.json()
        if data.get("status") != "1" or "pois" not in data:
            print(f"✗ 未找到结果: {data.get('info', '')}")
            return pd.DataFrame()

        rows = []
        for poi in data["pois"]:
            location = poi.get("location", "")
            lon, lat = (location.split(",") + [None, None])[:2] if location else (None, None)
            rows.append({
                "名称": poi.get("name"),
                "地址": poi.get("address"),
                "经度": lon,
                "纬度": lat,
                "类型": poi.get("type"),
                "行政区划": poi.get("adname"),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"✗ 错误: {e}")
        return pd.DataFrame()


# ============ 4. 主流程 ============

if __name__ == "__main__":
    # 先验证 Key 是否已配置
    if API_KEY == "你的高德地图Key":
        print("⚠️  请先在脚本顶部把 API_KEY 替换成你自己的高德 Key")
        exit(1)

    # 确保 data 目录存在（用于保存 CSV / 图片）
    os.makedirs("data", exist_ok=True)

    # 4.1 搜索多种类型
    results = {}
    for kw in KEYWORDS:
        df = search_poi(kw)
        results[kw] = df
        time.sleep(0.5)   # 避免请求过快

    print("\n===== 搜索结果汇总 =====")
    for kw, df in results.items():
        print(f"{kw}: {len(df)} 条")

    # 4.2 保存为 CSV
    for kw, df in results.items():
        if not df.empty:
            path = f"data/{kw}_{CITY}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"✓ 已保存: {path}")

    # 4.3 分页示例：获取更多数据（对重点分析对象）
    focus = search_poi_with_pagination(FOCUS_POI, max_count=150)
    if not focus.empty:
        print(f"\n分页获取{FOCUS_POI}: {len(focus)} 条")
        focus.to_csv(f"data/{FOCUS_POI}_{CITY}_分页.csv", index=False, encoding="utf-8-sig")

    # 4.4 预览
    first = next((df for df in results.values() if not df.empty), None)
    if first is not None:
        print("\n前 5 条结果预览:")
        print(first.head())

    # ============ 5. 地图可视化（folium 交互地图） ============

    def plot_poi_map(results, center=None, zoom_start=12):
        """把多种 POI 画到一张 folium 交互地图上（中心点默认按数据自动计算）"""
        import folium

        if center is None:
            lats, lons = [], []
            for df in results.values():
                if df.empty:
                    continue
                lats.extend(pd.to_numeric(df["纬度"], errors="coerce").dropna())
                lons.extend(pd.to_numeric(df["经度"], errors="coerce").dropna())
            center = [sum(lats) / len(lats), sum(lons) / len(lons)] if lats else [35.0, 105.0]

        base_map = folium.Map(
            location=list(center),
            zoom_start=zoom_start,
            tiles="OpenStreetMap",
        )

        colors = COLORS

        for poi_type, df in results.items():
            if df.empty:
                continue
            color = colors.get(poi_type, "gray")
            for _, row in df.iterrows():
                try:
                    lat, lon = float(row["纬度"]), float(row["经度"])
                except (TypeError, ValueError):
                    continue
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    color=color,
                    fillColor=color,
                    fillOpacity=0.6,
                    popup=f"{poi_type}: {row['名称']}",
                    tooltip=poi_type,
                ).add_to(base_map)

        # 图例
        items = "".join(
            f'<p><i class="fa fa-circle" style="color:{c}"></i> {t}</p>'
            for t, c in colors.items() if t in results
        )
        legend = (
            '<div style="position:fixed;top:10px;right:10px;width:150px;'
            'background-color:white;border:2px solid grey;z-index:9999;'
            'font-size:14px;padding:10px"><p><strong>POI类型</strong></p>'
            f"{items}</div>"
        )
        base_map.get_root().html.add_child(folium.Element(legend))
        return base_map

    if any(not df.empty for df in results.values()):
        m = plot_poi_map(results)
        m.save("data/poi_map.html")
        print("\n✓ 交互式地图已生成: data/poi_map.html（用浏览器打开查看）")

    # ============ 6. 统计图表（matplotlib 柱状图） ============

    poi_counts = {kw: len(df) for kw, df in results.items() if not df.empty}
    if poi_counts:
        color_map = COLORS
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(
            poi_counts.keys(),
            poi_counts.values(),
            color=[color_map.get(k, "gray") for k in poi_counts],
        )
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h, f"{int(h)}",
                    ha="center", va="bottom", fontsize=12)
        ax.set_xlabel("POI类型", fontsize=12)
        ax.set_ylabel("数量", fontsize=12)
        ax.set_title(f"{CITY}市不同类型POI数量对比", fontsize=14, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig("data/poi_type_comparison.png", dpi=300, bbox_inches="tight")
        print("✓ 统计图表已保存: data/poi_type_comparison.png")
        plt.show()

    # ============ 7. 重点对象深入分析（geopandas + matplotlib） ============

    def to_gdf(df):
        """把含 经度/纬度 的 DataFrame 转成 GeoDataFrame，自动剔除无效坐标"""
        d = df.copy()
        d["经度"] = pd.to_numeric(d["经度"], errors="coerce")
        d["纬度"] = pd.to_numeric(d["纬度"], errors="coerce")
        d = d.dropna(subset=["经度", "纬度"])
        return gpd.GeoDataFrame(
            d,
            geometry=[Point(x, y) for x, y in zip(d["经度"], d["纬度"])],
            crs="EPSG:4326",
        )

    focus_gdf = to_gdf(focus) if not focus.empty else gpd.GeoDataFrame()
    focus_color = COLORS.get(FOCUS_POI, "gray")

    if not focus_gdf.empty:
        # 7.1 重点对象探索地图
        m_focus = focus_gdf.explore(
            marker_type="circle_marker",
            marker_kwds={"radius": 5, "color": focus_color, "fillColor": focus_color, "fillOpacity": 0.6},
            tooltip=["名称", "地址", "行政区划"],
            tiles="OpenStreetMap",
        )
        m_focus.save(f"data/{FOCUS_POI}_map.html")
        print(f"\n✓ {FOCUS_POI}探索地图已生成: data/{FOCUS_POI}_map.html")

        # 7.2 各行政区数量（横向柱状图）
        district_counts = focus["行政区划"].value_counts()
        fig, ax = plt.subplots(figsize=(10, 8))
        cmap = plt.cm.YlOrBr(range(len(district_counts)))
        bars = ax.barh(district_counts.index, district_counts.values, color=cmap)
        for bar in bars:
            w = bar.get_width()
            ax.text(w, bar.get_y() + bar.get_height() / 2, f"{int(w)}",
                    ha="left", va="center", fontsize=11)
        ax.set_xlabel(f"{FOCUS_POI}数量", fontsize=12)
        ax.set_ylabel("行政区划", fontsize=12)
        ax.set_title(f"{CITY}市各行政区{FOCUS_POI}数量分布", fontsize=14, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"data/{FOCUS_POI}_by_district.png", dpi=300, bbox_inches="tight")
        print(f"✓ 行政区分布图已保存: data/{FOCUS_POI}_by_district.png")
        plt.show()

        print(f"\n各区{FOCUS_POI}数量:")
        for district, count in district_counts.items():
            print(f"  {district}: {count} 家 ({count / len(focus) * 100:.1f}%)")

        # 7.3 密度热力图
        fig, ax = plt.subplots(figsize=(12, 10))
        h = ax.hist2d(focus_gdf.geometry.x, focus_gdf.geometry.y, bins=30, cmap="YlOrRd", cmin=1)
        cbar = plt.colorbar(h[3], ax=ax)
        cbar.set_label(f"{FOCUS_POI}数量", fontsize=11)
        ax.set_xlabel("经度", fontsize=12)
        ax.set_ylabel("纬度", fontsize=12)
        ax.set_title(f"{CITY}市{FOCUS_POI}密度热力图", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"data/{FOCUS_POI}_density_heatmap.png", dpi=300, bbox_inches="tight")
        print(f"✓ 密度热力图已保存: data/{FOCUS_POI}_density_heatmap.png")
        plt.show()

    # ============ 8. 空间分布特征对比 ============

    def analyze_distribution(df, name):
        """计算 POI 的空间分布特征（中心点 / 离散度 / 范围）"""
        if df.empty:
            return None
        lons = pd.to_numeric(df["经度"], errors="coerce").dropna()
        lats = pd.to_numeric(df["纬度"], errors="coerce").dropna()
        if lons.empty:
            return None
        return {
            "名称": name,
            "数量": len(df),
            "中心经度": round(lons.mean(), 4),
            "中心纬度": round(lats.mean(), 4),
            "经度离散度": round(lons.std(), 4),
            "纬度离散度": round(lats.std(), 4),
            "经度范围": round(lons.max() - lons.min(), 4),
            "纬度范围": round(lats.max() - lats.min(), 4),
        }

    spatial_stats = []
    for poi_type, df in results.items():
        s = analyze_distribution(df, poi_type)
        if s:
            spatial_stats.append(s)

    if spatial_stats:
        stats_df = pd.DataFrame(spatial_stats)
        print("\n空间分布特征对比:")
        print(stats_df.to_string(index=False))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        ax1.bar(stats_df["名称"], stats_df["经度离散度"], color="skyblue", edgecolor="black")
        ax1.set_xlabel("POI类型", fontsize=12)
        ax1.set_ylabel("经度离散度", fontsize=12)
        ax1.set_title("东西方向分布离散度", fontsize=13, fontweight="bold")
        ax1.grid(axis="y", alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

        ax2.bar(stats_df["名称"], stats_df["纬度离散度"], color="lightcoral", edgecolor="black")
        ax2.set_xlabel("POI类型", fontsize=12)
        ax2.set_ylabel("纬度离散度", fontsize=12)
        ax2.set_title("南北方向分布离散度", fontsize=13, fontweight="bold")
        ax2.grid(axis="y", alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()
        plt.savefig("data/poi_spatial_distribution_comparison.png", dpi=300, bbox_inches="tight")
        print("✓ 空间分布对比图已保存: data/poi_spatial_distribution_comparison.png")
        plt.show()

    # ============ 9. 区县专项搜索：某区县博物馆 ============

    museums = search_poi_in_district("博物馆", district=DISTRICT)
    if not museums.empty:
        print(f"\n{DISTRICT}博物馆: {len(museums)} 个")
        museums_gdf = to_gdf(museums)
        m_museums = museums_gdf.explore(
            marker_type="circle_marker",
            marker_kwds={"radius": 8, "color": "red", "fillColor": "red", "fillOpacity": 0.7},
            tooltip=["名称", "地址"],
            popup=True,
            tiles="OpenStreetMap",
        )
        m_museums.save(f"data/{DISTRICT}_museums_map.html")
        print(f"✓ {DISTRICT}博物馆地图已生成: data/{DISTRICT}_museums_map.html")

    # ============ 10. 投影坐标系转换（EPSG:3857 Web墨卡托） ============

    print("\n【投影坐标系转换】WGS84 → EPSG:3857 (Web墨卡托)")
    print("-" * 50)

    # 把所有类型的 POI 合成一个 GeoDataFrame，再转投影
    parts = []
    for poi_type, df in results.items():
        if df.empty:
            continue
        g = to_gdf(df)
        g["POI类型"] = poi_type
        parts.append(g)

    if parts:
        all_gdf = pd.concat(parts, ignore_index=True)      # 原始：WGS84 经纬度（单位：度）
        all_3857 = all_gdf.to_crs(epsg=3857)               # 投影后：Web墨卡托（单位：米）

        # 展示转换前后坐标对比
        print("转换前后坐标对比（以第一个点为例）:")
        print(f"  WGS84 经纬度 : ({all_gdf.geometry.x.iloc[0]:.6f}, {all_gdf.geometry.y.iloc[0]:.6f}) 度")
        print(f"  EPSG:3857  : ({all_3857.geometry.x.iloc[0]:.0f}, {all_3857.geometry.y.iloc[0]:.0f}) 米")

        # 保存投影后的数据
        out = all_3857[["名称", "地址", "行政区划", "POI类型"]].copy()
        out["X(米)"] = all_3857.geometry.x.round(2)
        out["Y(米)"] = all_3857.geometry.y.round(2)
        out.to_csv("data/POI_EPSG3857投影.csv", index=False, encoding="utf-8-sig")
        print("✓ 投影后数据已保存: data/POI_EPSG3857投影.csv")

        # 用投影坐标绘制地图（x/y 单位为米，不再是经纬度）
        color_map = COLORS
        fig, ax = plt.subplots(figsize=(11, 9))
        for poi_type, g in all_3857.groupby("POI类型"):
            ax.scatter(g.geometry.x, g.geometry.y,
                       c=color_map.get(poi_type, "gray"), s=30, alpha=0.6,
                       edgecolors="white", linewidths=0.4, label=poi_type)
        ax.set_xlabel("X (米)", fontsize=12)
        ax.set_ylabel("Y (米)", fontsize=12)
        ax.set_title(f"{CITY}市 POI 分布（EPSG:3857 投影坐标，单位米）", fontsize=14, fontweight="bold")
        ax.ticklabel_format(style="plain", axis="both")   # 避免科学计数法
        ax.grid(True, alpha=0.3)
        ax.legend(title="POI类型")
        plt.tight_layout()
        plt.savefig("data/poi_epsg3857_map.png", dpi=300, bbox_inches="tight")
        print("✓ 投影坐标地图已保存: data/poi_epsg3857_map.png")
        plt.show()
