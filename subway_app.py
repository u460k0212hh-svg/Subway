import csv
import os

import folium
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LINE_COLOR = {"1": "blue", "2": "green", "3": "orange", "4": "cyan"}


# 다익스트라 최단 경로
class Dijkstra:
    def __init__(self, nodes):
        self.nodes = set(nodes)
        self.graph = []

    def setEdge(self, a, b, w):
        self.graph.append((a, b, w))

    def _neighbor(self, curNode):
        # curNode에 연결된 역과 소요시간
        neighbor = {}
        for node in self.graph:
            if node[0] == curNode:
                neighbor[node[1]] = node[2]
            elif node[1] == curNode:
                neighbor[node[0]] = node[2]
        return neighbor

    def _dicFilter(self, cost, nodes):
        # 아직 방문하지 않은 역 중 cost가 가장 작은 역
        mini = float("inf")
        curNode = None
        for key, value in cost.items():
            if key in nodes and value[0] < mini:
                mini = value[0]
                curNode = key
        return curNode

    def getPath(self, start, end):
        nodes = set(self.nodes)          # 검색할 때마다 새로 시작
        cost = {node: [float("inf"), None] for node in nodes}
        cost[start][0] = 0
        curNode = start

        while curNode is not None:
            nodes.remove(curNode)
            for node, w in self._neighbor(curNode).items():
                if cost[curNode][0] + w < cost[node][0]:
                    cost[node][0] = cost[curNode][0] + w
                    cost[node][1] = curNode
            if curNode == end:
                break
            curNode = self._dicFilter(cost, nodes)

        total = cost[end][0]
        path = [end]
        while end != start:
            end = cost[end][1]
            path.append(end)
        path.reverse()
        times = [cost[p][0] for p in path]
        return path, times, total


# csv 읽기
@st.cache_data
def load_data():
    subwayLoc = {}
    with open(os.path.join(BASE_DIR, "subwayLocation.csv"), encoding="utf-8-sig") as f:
        for line in csv.reader(f):
            if line and line[0] not in subwayLoc:
                subwayLoc[line[0]] = [float(line[1]), float(line[2])]

    edges = []
    with open(os.path.join(BASE_DIR, "subway.csv"), encoding="utf-8-sig") as f:
        for line in csv.reader(f):
            if line:
                edges.append((line[0], line[1], int(line[2])))
    return subwayLoc, edges


@st.cache_resource
def make_dijkstra(edges):
    nodes = set()
    for a, b, w in edges:
        nodes.add(a)
        nodes.add(b)
    d = Dijkstra(nodes)
    for a, b, w in edges:
        d.setEdge(a, b, w)
    return d


def station_name(node):
    return node[:-3]          # '서울역(1)' -> '서울역'


def line_no(node):
    return node[-2]           # '서울역(1)' -> '1'


def base_map(subwayLoc, edges, faded=False):
    m = folium.Map(location=[37.54, 127.0], zoom_start=12, tiles="OpenStreetMap")
    opacity = 0.25 if faded else 0.8
    # 노선 그리기 (같은 노선끼리만, 환승 연결선은 제외)
    for a, b, w in edges:
        if line_no(a) == line_no(b):
            folium.PolyLine([subwayLoc[station_name(a)], subwayLoc[station_name(b)]],
                            color=LINE_COLOR[line_no(a)], weight=4, opacity=opacity).add_to(m)
    return m


st.set_page_config(page_title="지하철 노선도", page_icon="🚇", layout="wide")
st.title("🚇 지하철 최단 경로 찾기")

subwayLoc, edges = load_data()
d = make_dijkstra(edges)
stations = sorted(d.nodes)

# 사이드바
with st.sidebar:
    st.header("경로 검색")
    start = st.selectbox("출발역", stations, index=stations.index("남태령(4)"))
    end = st.selectbox("도착역", stations, index=stations.index("종각(1)"))
    run = st.button("최단 경로 찾기", type="primary", use_container_width=True)
    st.divider()
    st.caption("노선 색상")
    for no, color in LINE_COLOR.items():
        st.markdown(f"<span style='color:{color};font-size:1.3rem'>●</span> {no}호선",
                    unsafe_allow_html=True)

if run:
    st.session_state.result = (start, end)

left, right = st.columns([3, 1], gap="large")

if "result" not in st.session_state:
    # 처음 화면: 전체 노선도
    with left:
        components.html(base_map(subwayLoc, edges).get_root().render(), height=650)
    with right:
        st.subheader("사용 방법")
        st.write("왼쪽에서 출발역과 도착역을 고르고 **최단 경로 찾기**를 누르세요.")
        st.metric("전체 역 수", f"{len(stations)}개")
else:
    start, end = st.session_state.result
    if start == end:
        st.warning("출발역과 도착역이 같습니다.")
        st.stop()

    path, times, total = d.getPath(start, end)
    transfers = sum(1 for i in range(1, len(path))
                    if station_name(path[i]) == station_name(path[i - 1]))

    # 지도에 경로 표시
    m = base_map(subwayLoc, edges, faded=True)
    points = []
    for node in path:
        loc = subwayLoc[station_name(node)]
        color = LINE_COLOR[line_no(node)]
        folium.CircleMarker(loc, radius=6, color=color, fill=True, fill_color=color,
                            fill_opacity=1, tooltip=node).add_to(m)
        points.append(loc)
    folium.PolyLine(points, color="red", weight=5, opacity=1).add_to(m)
    folium.Marker(points[0], tooltip="출발: " + start,
                  icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(points[-1], tooltip="도착: " + end,
                  icon=folium.Icon(color="red", icon="flag")).add_to(m)
    m.fit_bounds(points, padding=(30, 30))

    with left:
        components.html(m.get_root().render(), height=650)

    with right:
        st.subheader(f"{station_name(start)} → {station_name(end)}")
        c1, c2 = st.columns(2)
        c1.metric("소요시간", f"{total}분")
        c2.metric("환승", f"{transfers}회")
        st.metric("지나는 역", f"{len(path) - 1 - transfers}개 역")

        rows = []
        for i, node in enumerate(path):
            note = ""
            if i > 0 and station_name(node) == station_name(path[i - 1]):
                note = f"{line_no(path[i - 1])}호선 → {line_no(node)}호선 환승"
            rows.append({"역": node, "누적 시간(분)": times[i], "비고": note})
        st.dataframe(rows, hide_index=True, use_container_width=True, height=400)
