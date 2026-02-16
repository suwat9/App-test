import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import plotly.express as px
import plotly.graph_objects as go
from streamlit_js_eval import streamlit_js_eval

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ระบบบันทึกเวลาปฏิบัติงานด้วยGPS",
    page_icon="🏢",
    layout="wide"
)

class WorkTimeTracker:
    def __init__(self):
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """เริ่มต้นสถานะ session"""
        defaults = {
            'work_location': {
                'lat': 13.7563,
                'lng': 100.5018,
                'radius': 100,
                'name': 'สถานที่ทำงานหลัก'
            },
            'work_sessions': [],
            'is_tracking': False,
            'current_location': None,
            'last_update': None,
            'simulation_mode': True
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """คำนวณระยะทางระหว่างสองจุด (Haversine formula)"""
        R = 6371000  # รัศมีของโลกในหน่วยเมตร
        
        # แปลงองศาเป็นเรเดียน
        phi_1 = math.radians(lat1)
        phi_2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = math.sin(delta_phi/2.0)**2 + \
            math.cos(phi_1) * math.cos(phi_2) * \
            math.sin(delta_lambda/2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def get_browser_location(self):
        """ดึงตำแหน่งจากเบราว์เซอร์"""
        try:
            # พยายามดึงตำแหน่งจากเบราว์เซอร์
            result = streamlit_js_eval(
                js_expressions="""
                new Promise((resolve, reject) => {
                    if ("geolocation" in navigator) {
                        navigator.geolocation.getCurrentPosition(
                            position => resolve({
                                lat: position.coords.latitude,
                                lng: position.coords.longitude
                            }),
                            error => reject(new Error(error.message))
                        );
                    } else {
                        reject(new Error("Geolocation not available"));
                    }
                })
                """,
                key='get_location'
            )
            
            st.session_state.current_location = (result['lat'], result['lng'])
            st.session_state.last_update = datetime.now()
            st.session_state.simulation_mode = False
            
            return st.session_state.current_location
            
        except Exception as e:
            st.warning(f"ใช้ตำแหน่งจำลอง: {e}")
            return self.get_simulated_location()

    def get_simulated_location(self):
        """สร้างตำแหน่งจำลอง"""
        if (st.session_state.current_location is None or 
            (st.session_state.last_update and 
             (datetime.now() - st.session_state.last_update).seconds > 30)):
            
            # สุ่มตำแหน่งรอบพื้นที่ทำงาน
            lat = st.session_state.work_location['lat'] + np.random.uniform(-0.005, 0.005)
            lng = st.session_state.work_location['lng'] + np.random.uniform(-0.005, 0.005)
            
            st.session_state.current_location = (lat, lng)
            st.session_state.last_update = datetime.now()
            st.session_state.simulation_mode = True
        
        return st.session_state.current_location

    def is_in_work_area(self, current_lat, current_lng):
        """ตรวจสอบว่าอยู่ในพื้นที่ทำงานหรือไม่"""
        work_lat = st.session_state.work_location['lat']
        work_lng = st.session_state.work_location['lng']
        radius = st.session_state.work_location['radius']
        
        distance = self.haversine_distance(
            work_lat, work_lng,
            current_lat, current_lng
        )
        
        return distance <= radius, distance

    def start_work_session(self):
        """เริ่มบันทึกเวลาทำงาน"""
        with st.spinner("กำลังตรวจสอบตำแหน่ง..."):
            location = self.get_browser_location()
        
        if not location:
            st.error("ไม่สามารถดึงตำแหน่งได้")
            return False
            
        lat, lng = location
        in_area, distance = self.is_in_work_area(lat, lng)
        
        new_session = {
            'id': len(st.session_state.work_sessions) + 1,
            'start_time': datetime.now(),
            'end_time': None,
            'location': location,
            'in_work_area': in_area,
            'distance': distance,
            'status': 'active'
        }
        
        st.session_state.work_sessions.append(new_session)
        st.session_state.is_tracking = True
        
        status_msg = "✅ เริ่มบันทึกเวลาทำงานแล้ว"
        if not in_area:
            status_msg += " ⚠️ (อยู่นอกพื้นที่ทำงาน)"
        
        st.success(status_msg)
        time.sleep(1)
        st.rerun()
        return True

    def end_work_session(self):
        """หยุดบันทึกเวลาทำงาน"""
        if not st.session_state.work_sessions or st.session_state.work_sessions[-1]['end_time'] is not None:
            st.warning("ไม่มี session การทำงานที่กำลังดำเนินอยู่")
            return False
            
        # อัพเดทตำแหน่งสุดท้าย
        location = self.get_browser_location()
        if location:
            lat, lng = location
            in_area, distance = self.is_in_work_area(lat, lng)
            st.session_state.work_sessions[-1].update({
                'end_location': location,
                'end_in_area': in_area,
                'end_distance': distance
            })
        
        st.session_state.work_sessions[-1]['end_time'] = datetime.now()
        st.session_state.work_sessions[-1]['status'] = 'completed'
        
        # คำนวณระยะเวลา
        start_time = st.session_state.work_sessions[-1]['start_time']
        end_time = st.session_state.work_sessions[-1]['end_time']
        duration = end_time - start_time
        st.session_state.work_sessions[-1]['duration'] = duration
        
        st.session_state.is_tracking = False
        
        # แสดงสรุป
        total_hours = duration.total_seconds() / 3600
        st.success(f"⏹️ บันทึกเวลาทำงานเสร็จสิ้น: {total_hours:.2f} ชั่วโมง")
        time.sleep(1)
        st.rerun()
        return True

    def render_header(self):
        """แสดง header"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.title("🏢 ระบบบันทึกเวลาปฏิบัติงานด้วย GPS")
            st.markdown("---")
        
        with col2:
            if st.session_state.is_tracking:
                st.markdown("### 🟢 กำลังบันทึกเวลา")
                current_session = st.session_state.work_sessions[-1]
                start_time = current_session['start_time']
                elapsed = datetime.now() - start_time
                hours = elapsed.total_seconds() / 3600
                st.markdown(f"**⏱️ ผ่านไปแล้ว:** {hours:.2f} ชั่วโมง")
            else:
                st.markdown("### 🔴 หยุดบันทึก")

    def render_sidebar(self):
        """แสดง sidebar"""
        with st.sidebar:
            st.title("⚙️ การตั้งค่า")
            
            # สถานะตำแหน่ง
            if st.session_state.current_location:
                lat, lng = st.session_state.current_location
                sim_status = "(จำลอง)" if st.session_state.simulation_mode else "(GPS จริง)"
                st.info(f"**ตำแหน่งปัจจุบัน:**\n{lat:.6f}, {lng:.6f}\n{sim_status}")
            
            # ตั้งค่าพื้นที่ทำงาน
            st.subheader("📍 กำหนดพื้นที่ทำงาน")
            
            col1, col2 = st.columns(2)
            with col1:
                new_lat = st.number_input(
                    "ละติจูด", 
                    value=st.session_state.work_location['lat'],
                    format="%.6f",
                    key="lat_input"
                )
            with col2:
                new_lng = st.number_input(
                    "ลองจิจูด",
                    value=st.session_state.work_location['lng'],
                    format="%.6f",
                    key="lng_input"
                )
            
            new_radius = st.slider(
                "รัศมีพื้นที่ทำงาน (เมตร)",
                min_value=10,
                max_value=1000,
                value=st.session_state.work_location['radius'],
                step=10
            )
            
            work_name = st.text_input(
                "ชื่อสถานที่ทำงาน",
                value=st.session_state.work_location['name']
            )
            
            if st.button("💾 บันทึกการตั้งค่า", use_container_width=True):
                st.session_state.work_location.update({
                    'lat': new_lat,
                    'lng': new_lng,
                    'radius': new_radius,
                    'name': work_name
                })
                st.success("บันทึกการตั้งค่าเรียบร้อย!")
                time.sleep(1)
                st.rerun()
            
            st.divider()
            
            # การควบคุม
            st.subheader("🎮 การควบคุม")
            
            col1, col2 = st.columns(2)
            with col1:
                if not st.session_state.is_tracking:
                    if st.button("🚀 เริ่มทำงาน", type="primary", use_container_width=True):
                        self.start_work_session()
                else:
                    st.button("🚀 เริ่มทำงาน", disabled=True, use_container_width=True)
            
            with col2:
                if st.session_state.is_tracking:
                    if st.button("⏹️ หยุดทำงาน", type="secondary", use_container_width=True):
                        self.end_work_session()
                else:
                    st.button("⏹️ หยุดทำงาน", disabled=True, use_container_width=True)
            
            st.divider()
            
            # สถิติ
            stats = self.get_statistics()
            st.subheader("📊 สถิติ")
            st.metric("เวลาวันนี้", f"{stats['today_hours']:.2f} ชม.")
            st.metric("เวลารวม", f"{stats['total_hours']:.2f} ชม.")
            st.metric("จำนวนครั้ง", stats['total_sessions'])
            
            if st.button("🔄 อัพเดทตำแหน่ง", use_container_width=True):
                self.get_browser_location()
                st.rerun()

    def get_statistics(self):
        """คำนวณสถิติ"""
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed:
            return {'total_hours': 0, 'today_hours': 0, 'total_sessions': 0}
        
        total_seconds = sum(s['duration'].total_seconds() for s in completed)
        today_seconds = sum(
            s['duration'].total_seconds() 
            for s in completed 
            if s['start_time'].date() == datetime.now().date()
        )
        
        return {
            'total_hours': total_seconds / 3600,
            'today_hours': today_seconds / 3600,
            'total_sessions': len(completed)
        }

    def render_location_info(self):
        """แสดงข้อมูลตำแหน่ง"""
        st.header("📍 สถานะตำแหน่ง")
        
        location = st.session_state.current_location or self.get_simulated_location()
        
        if location:
            lat, lng = location
            in_area, distance = self.is_in_work_area(lat, lng)
            
            cols = st.columns(4)
            
            with cols[0]:
                if in_area:
                    st.metric("สถานะ", "✅ อยู่ในพื้นที่", delta="ในพื้นที่")
                else:
                    st.metric("สถานะ", "⚠️ นอกพื้นที่", delta="นอกพื้นที่", delta_color="inverse")
            
            with cols[1]:
                st.metric("ระยะทาง", f"{distance:.0f} m")
            
            with cols[2]:
                st.metric("ละติจูด", f"{lat:.6f}")
            
            with cols[3]:
                st.metric("ลองจิจูด", f"{lng:.6f}")
            
            # แสดงแผนที่
            self.render_map(lat, lng, in_area, distance)

    def render_map(self, user_lat, user_lng, in_area, distance):
        """แสดงแผนที่"""
        work_lat = st.session_state.work_location['lat']
        work_lng = st.session_state.work_location['lng']
        
        # สร้างวงกลมรอบพื้นที่ทำงาน
        radius_m = st.session_state.work_location['radius']
        radius_deg = radius_m / 111000  # ประมาณ 1 องศา = 111 กม.
        
        theta = np.linspace(0, 2*np.pi, 100)
        circle_lat = work_lat + radius_deg * np.sin(theta)
        circle_lng = work_lng + radius_deg * np.cos(theta)
        
        fig = go.Figure()
        
        # เพิ่มวงกลมพื้นที่ทำงาน
        fig.add_trace(go.Scattermapbox(
            lat=circle_lat.tolist(),
            lon=circle_lng.tolist(),
            mode='lines',
            line=dict(width=2, color='blue'),
            fill='toself',
            fillcolor='rgba(0, 0, 255, 0.1)',
            name='พื้นที่ทำงาน'
        ))
        
        # เพิ่มจุดพื้นที่ทำงาน
        fig.add_trace(go.Scattermapbox(
            lat=[work_lat],
            lon=[work_lng],
            mode='markers+text',
            marker=dict(size=20, color='blue'),
            text=[st.session_state.work_location['name']],
            textposition="top center",
            name='ศูนย์กลาง'
        ))
        
        # เพิ่มจุดผู้ใช้
        user_color = 'green' if in_area else 'red'
        fig.add_trace(go.Scattermapbox(
            lat=[user_lat],
            lon=[user_lng],
            mode='markers+text',
            marker=dict(size=15, color=user_color),
            text=['คุณ'],
            textposition="bottom center",
            name='ตำแหน่งคุณ'
        ))
        
        # อัพเดท layout
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=work_lat, lon=work_lng),
                zoom=15
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def render_sessions_table(self):
        """แสดงตารางประวัติการทำงาน"""
        st.header("📋 ประวัติการทำงาน")
        
        if not st.session_state.work_sessions:
            st.info("ยังไม่มีประวัติการทำงาน")
            return
        
        # สร้าง DataFrame
        sessions_list = []
        for session in reversed(st.session_state.work_sessions[-10:]):  # 10 รายการล่าสุด
            if session['status'] == 'completed':
                row = {
                    'ลำดับ': session['id'],
                    'วันที่': session['start_time'].strftime('%d/%m/%Y'),
                    'เริ่ม': session['start_time'].strftime('%H:%M'),
                    'สิ้นสุด': session['end_time'].strftime('%H:%M'),
                    'ระยะเวลา': str(session['duration']).split('.')[0],
                    'สถานะ': '✅' if session['in_work_area'] else '⚠️',
                    'ระยะทาง (ม.)': f"{session['distance']:.0f}"
                }
            else:  # กำลังทำงาน
                elapsed = datetime.now() - session['start_time']
                hours = elapsed.total_seconds() / 3600
                row = {
                    'ลำดับ': session['id'],
                    'วันที่': session['start_time'].strftime('%d/%m/%Y'),
                    'เริ่ม': session['start_time'].strftime('%H:%M'),
                    'สิ้นสุด': 'กำลังทำงาน...',
                    'ระยะเวลา': f"{hours:.2f} ชม.",
                    'สถานะ': '🟢 ทำงานอยู่',
                    'ระยะทาง (ม.)': f"{session['distance']:.0f}"
                }
            sessions_list.append(row)
        
        if sessions_list:
            df = pd.DataFrame(sessions_list)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("ไม่มี session ที่เสร็จสมบูรณ์")

    def render_analytics(self):
        """แสดงการวิเคราะห์"""
        st.header("📈 การวิเคราะห์ข้อมูล")
        
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed:
            st.info("ไม่มีข้อมูลเพียงพอสำหรับการวิเคราะห์")
            return
        
        # แบ่งเป็น 2 columns
        col1, col2 = st.columns(2)
        
        with col1:
            # สร้างกราฟแท่งเวลาทำงานรายวัน
            daily_data = []
            for session in completed:
                date = session['start_time'].date()
                hours = session['duration'].total_seconds() / 3600
                daily_data.append({'วันที่': date, 'ชั่วโมง': hours})
            
            if daily_data:
                df_daily = pd.DataFrame(daily_data)
                df_daily = df_daily.groupby('วันที่')['ชั่วโมง'].sum().reset_index()
                df_daily = df_daily.tail(7)  # 7 วันล่าสุด
                
                fig_daily = px.bar(
                    df_daily,
                    x='วันที่',
                    y='ชั่วโมง',
                    title='เวลาทำงานรายวัน',
                    color='ชั่วโมง',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_daily, use_container_width=True)
        
        with col2:
            # แสดงสถิติเพิ่มเติม
            in_area_count = len([s for s in completed if s['in_work_area']])
            total_count = len(completed)
            in_area_percent = (in_area_count / total_count * 100) if total_count > 0 else 0
            
            stats_data = {
                'ในพื้นที่': in_area_count,
                'นอกพื้นที่': total_count - in_area_count
            }
            
            fig_pie = px.pie(
                values=list(stats_data.values()),
                names=list(stats_data.keys()),
                title='อัตราการทำงานในพื้นที่',
                color=list(stats_data.keys()),
                color_discrete_map={'ในพื้นที่': 'green', 'นอกพื้นที่': 'red'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    def render_footer(self):
        """แสดง footer"""
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: gray;'>
        <p>ระบบบันทึกเวลาปฏิบัติงานด้วย GPS | พัฒนาด้วย Streamlit</p>
        <p>⚠️ หมายเหตุ: สำหรับการใช้งานจริง อนุญาตการเข้าถึงตำแหน่งในเบราว์เซอร์</p>
        </div>
        """, unsafe_allow_html=True)

    def main(self):
        """ฟังก์ชันหลัก"""
        self.render_header()
        self.render_sidebar()
        
        # แสดงเนื้อหาหลัก
        tab1, tab2, tab3 = st.tabs(["📍 สถานะตำแหน่ง", "📋 ประวัติการทำงาน", "📈 การวิเคราะห์"])
        
        with tab1:
            self.render_location_info()
        
        with tab2:
            self.render_sessions_table()
            
            # ปุ่มจัดการข้อมูล
            if st.session_state.work_sessions:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 ดาวน์โหลดข้อมูล", use_container_width=True):
                        self.export_data()
                with col2:
                    if st.button("🗑️ ล้างข้อมูลทั้งหมด", type="secondary", use_container_width=True):
                        if not st.session_state.is_tracking:
                            st.session_state.work_sessions = []
                            st.success("ล้างข้อมูลเรียบร้อย!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("กรุณาหยุดการทำงานก่อนล้างข้อมูล")
        
        with tab3:
            self.render_analytics()
        
        self.render_footer()
        
        # Auto-refresh ถ้ากำลังทำงาน
        if st.session_state.is_tracking:
            time.sleep(5)  # รีเฟรชทุก 5 วินาที
            st.rerun()

    def export_data(self):
        """ส่งออกข้อมูล"""
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed:
            st.warning("ไม่มีข้อมูลที่จะส่งออก")
            return
        
        data_list = []
        for session in completed:
            data_list.append({
                'ID': session['id'],
                'วันที่': session['start_time'].strftime('%Y-%m-%d'),
                'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                'เวลาสิ้นสุด': session['end_time'].strftime('%H:%M:%S'),
                'ระยะเวลา (ชั่วโมง)': session['duration'].total_seconds() / 3600,
                'ในพื้นที่ทำงาน': 'ใช่' if session['in_work_area'] else 'ไม่',
                'ระยะทางจากศูนย์กลาง (ม.)': session['distance'],
                'ตำแหน่งเริ่มต้น': f"{session['location'][0]:.6f},{session['location'][1]:.6f}"
            })
        
        df = pd.DataFrame(data_list)
        
        # แสดงข้อมูล
        st.dataframe(df, use_container_width=True)
        
        # สร้าง CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลด CSV",
            data=csv,
            file_name=f"work_time_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# รันแอพพลิเคชัน
if __name__ == "__main__":
    try:
        app = WorkTimeTracker()
        app.main()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
        st.info("โปรดรีเฟรชหน้าเว็บหรือลองใหม่อีกครั้ง")
