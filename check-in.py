import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import plotly.express as px
import plotly.graph_objects as go

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
            'use_gps': False,
            'manual_lat': 13.7563,
            'manual_lng': 100.5018
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """คำนวณระยะทางระหว่างสองจุด (Haversine formula)"""
        # แปลงองศาเป็นเรเดียน
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lon1_rad = math.radians(lon1)
        lon2_rad = math.radians(lon2)
        
        # ความแตกต่าง
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # ระยะทางในเมตร (รัศมีโลกประมาณ 6371 กม.)
        distance = 6371000 * c
        return distance

    def get_current_location(self):
        """ดึงตำแหน่งปัจจุบัน - ใช้ manual input หรือ simulation"""
        if st.session_state.use_gps:
            # พยายามใช้ GPS จริง (ถ้ามี)
            try:
                # วิธีนี้จะทำงานเมื่อผู้ใช้อนุญาต GPS
                # สำหรับตอนนี้ให้ใช้ manual input เป็นหลัก
                if st.session_state.current_location:
                    return st.session_state.current_location
            except:
                st.session_state.use_gps = False
                st.warning("GPS ไม่พร้อมใช้งาน ใช้ตำแหน่งจำลองแทน")
        
        # ใช้ตำแหน่งจำลองหรือ manual input
        if (st.session_state.current_location is None or 
            (datetime.now() - st.session_state.last_update).seconds > 30):
            
            # สุ่มตำแหน่งรอบพื้นที่ทำงานสำหรับ simulation
            variation = 0.002  # ~200 เมตร
            lat = st.session_state.work_location['lat'] + np.random.uniform(-variation, variation)
            lng = st.session_state.work_location['lng'] + np.random.uniform(-variation, variation)
            
            st.session_state.current_location = (lat, lng)
            st.session_state.last_update = datetime.now()
        
        return st.session_state.current_location

    def is_in_work_area(self, current_lat, current_lng):
        """ตรวจสอบว่าอยู่ในพื้นที่ทำงานหรือไม่"""
        work_lat = st.session_state.work_location['lat']
        work_lng = st.session_state.work_location['lng']
        radius = st.session_state.work_location['radius']
        
        distance = self.haversine_distance(work_lat, work_lng, current_lat, current_lng)
        return distance <= radius, distance

    def start_work_session(self):
        """เริ่มบันทึกเวลาทำงาน"""
        location = self.get_current_location()
        
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
        
        # แสดงสถานะ
        if in_area:
            st.success("✅ เริ่มบันทึกเวลาทำงานแล้ว - อยู่ในพื้นที่ทำงาน")
        else:
            st.warning("⚠️ เริ่มบันทึกเวลาทำงานแล้ว - นอกพื้นที่ทำงาน")
        
        return True

    def end_work_session(self):
        """หยุดบันทึกเวลาทำงาน"""
        active_sessions = [s for s in st.session_state.work_sessions if s['status'] == 'active']
        
        if not active_sessions:
            st.warning("ไม่มี session การทำงานที่กำลังดำเนินอยู่")
            return False
            
        # หยุด session ล่าสุดที่ active
        for session in reversed(st.session_state.work_sessions):
            if session['status'] == 'active':
                session['end_time'] = datetime.now()
                session['status'] = 'completed'
                
                # คำนวณระยะเวลา
                duration = session['end_time'] - session['start_time']
                session['duration'] = duration
                break
        
        st.session_state.is_tracking = False
        st.success("⏹️ หยุดบันทึกเวลาทำงานแล้ว")
        return True

    def render_sidebar(self):
        """แสดง sidebar"""
        with st.sidebar:
            st.title("⚙️ การตั้งค่า")
            
            # การตั้งค่าตำแหน่ง
            st.subheader("📍 การตั้งค่าตำแหน่ง")
            
            # ตัวเลือกการได้มาซึ่งตำแหน่ง
            gps_option = st.radio(
                "วิธีการได้ตำแหน่ง:",
                ["ตำแหน่งจำลอง", "ป้อนตำแหน่งเอง"],
                index=0
            )
            
            if gps_option == "ป้อนตำแหน่งเอง":
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state.manual_lat = st.number_input(
                        "ละติจูด", 
                        value=st.session_state.manual_lat,
                        format="%.6f"
                    )
                with col2:
                    st.session_state.manual_lng = st.number_input(
                        "ลองจิจูด",
                        value=st.session_state.manual_lng,
                        format="%.6f"
                    )
                
                if st.button("ใช้ตำแหน่งนี้"):
                    st.session_state.current_location = (st.session_state.manual_lat, st.session_state.manual_lng)
                    st.session_state.last_update = datetime.now()
                    st.success("อัพเดทตำแหน่งเรียบร้อย!")
            
            # ตั้งค่าพื้นที่ทำงาน
            st.subheader("🏢 ตั้งค่าพื้นที่ทำงาน")
            
            col1, col2 = st.columns(2)
            with col1:
                new_lat = st.number_input(
                    "ละติจูดพื้นที่ทำงาน", 
                    value=st.session_state.work_location['lat'],
                    format="%.6f",
                    key="work_lat"
                )
            with col2:
                new_lng = st.number_input(
                    "ลองจิจูดพื้นที่ทำงาน",
                    value=st.session_state.work_location['lng'],
                    format="%.6f",
                    key="work_lng"
                )
            
            new_radius = st.slider(
                "รัศมีพื้นที่ทำงาน (เมตร)",
                min_value=10,
                max_value=500,
                value=st.session_state.work_location['radius']
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
            
            st.divider()
            
            # การควบคุม
            st.subheader("🎮 การควบคุม")
            
            col1, col2 = st.columns(2)
            with col1:
                if not st.session_state.is_tracking:
                    if st.button("🚀 เริ่มทำงาน", type="primary", use_container_width=True):
                        self.start_work_session()
                        st.rerun()
                else:
                    st.button("🚀 เริ่มทำงาน", disabled=True, use_container_width=True)
            
            with col2:
                if st.session_state.is_tracking:
                    if st.button("⏹️ หยุดทำงาน", type="secondary", use_container_width=True):
                        self.end_work_session()
                        st.rerun()
                else:
                    st.button("⏹️ หยุดทำงาน", disabled=True, use_container_width=True)
            
            if st.button("🔄 อัพเดทตำแหน่ง", use_container_width=True):
                st.session_state.current_location = None
                st.rerun()
            
            st.divider()
            
            # สถิติ
            st.subheader("📊 สถิติ")
            stats = self.get_statistics()
            st.metric("เวลาวันนี้", f"{stats['today_hours']:.2f} ชม.")
            st.metric("เวลารวม", f"{stats['total_hours']:.2f} ชม.")
            st.metric("จำนวนครั้ง", stats['total_sessions'])

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

    def render_main_content(self):
        """แสดงเนื้อหาหลัก"""
        st.title("🏢 ระบบบันทึกเวลาปฏิบัติงาน")
        st.markdown("---")
        
        # สถานะปัจจุบัน
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.is_tracking:
                st.success("🟢 กำลังบันทึกเวลา")
                # คำนวณเวลาที่ผ่านไป
                active_session = next((s for s in st.session_state.work_sessions if s['status'] == 'active'), None)
                if active_session:
                    elapsed = datetime.now() - active_session['start_time']
                    hours = elapsed.total_seconds() / 3600
                    st.metric("เวลาที่ผ่านไป", f"{hours:.2f} ชม.")
            else:
                st.info("🔴 ไม่ได้บันทึกเวลา")
        
        with col2:
            location = self.get_current_location()
            if location:
                lat, lng = location
                in_area, distance = self.is_in_work_area(lat, lng)
                
                status = "✅ ในพื้นที่" if in_area else "⚠️ นอกพื้นที่"
                st.metric("สถานะพื้นที่", status)
                st.metric("ระยะทาง", f"{distance:.0f} เมตร")
        
        with col3:
            if location:
                st.metric("ตำแหน่งปัจจุบัน", f"{lat:.6f}, {lng:.6f}")
        
        # แสดงแผนที่
        self.render_map()
        
        # แสดงประวัติการทำงาน
        st.subheader("📋 ประวัติการทำงาน")
        self.render_sessions_table()
        
        # การวิเคราะห์ข้อมูล
        st.subheader("📈 การวิเคราะห์")
        self.render_analytics()

    def render_map(self):
        """แสดงแผนที่แบบง่าย"""
        if not st.session_state.current_location:
            return
            
        user_lat, user_lng = st.session_state.current_location
        work_lat = st.session_state.work_location['lat']
        work_lng = st.session_state.work_location['lng']
        in_area, distance = self.is_in_work_area(user_lat, user_lng)
        
        # สร้างข้อมูลสำหรับแผนที่
        df = pd.DataFrame({
            'lat': [work_lat, user_lat],
            'lon': [work_lng, user_lng],
            'type': ['พื้นที่ทำงาน', 'ตำแหน่งคุณ'],
            'size': [20, 15],
            'color': ['blue', 'green' if in_area else 'red']
        })
        
        # สร้างแผนที่แบบง่าย
        try:
            fig = px.scatter_mapbox(
                df,
                lat="lat",
                lon="lon",
                color="type",
                size="size",
                color_discrete_map={
                    'พื้นที่ทำงาน': 'blue',
                    'ตำแหน่งคุณ': 'green' if in_area else 'red'
                },
                zoom=14,
                height=300
            )
            
            fig.update_layout(
                mapbox_style="open-street-map",
                margin={"r":0,"t":0,"l":0,"b":0},
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.warning(f"ไม่สามารถแสดงแผนที่ได้: {e}")
            # แสดงข้อมูลตำแหน่งแบบตารางแทน
            st.info(f"""
            **ข้อมูลตำแหน่ง:**
            - พื้นที่ทำงาน: {work_lat:.6f}, {work_lng:.6f}
            - ตำแหน่งคุณ: {user_lat:.6f}, {user_lng:.6f}
            - ระยะทาง: {distance:.0f} เมตร
            - สถานะ: {'อยู่ในพื้นที่' if in_area else 'นอกพื้นที่'}
            """)

    def render_sessions_table(self):
        """แสดงตารางประวัติการทำงาน"""
        if not st.session_state.work_sessions:
            st.info("ยังไม่มีประวัติการทำงาน")
            return
        
        # สร้างข้อมูลสำหรับตาราง
        sessions_data = []
        for session in reversed(st.session_state.work_sessions[-10:]):  # 10 รายการล่าสุด
            if session['status'] == 'completed':
                sessions_data.append({
                    'ลำดับ': session['id'],
                    'วันที่': session['start_time'].strftime('%d/%m/%Y'),
                    'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                    'เวลาสิ้นสุด': session['end_time'].strftime('%H:%M:%S'),
                    'ระยะเวลา': str(session['duration']).split('.')[0],
                    'สถานะ': '✅' if session['in_work_area'] else '⚠️',
                    'ระยะทาง (ม.)': f"{session['distance']:.0f}"
                })
            else:
                elapsed = datetime.now() - session['start_time']
                hours = elapsed.total_seconds() / 3600
                sessions_data.append({
                    'ลำดับ': session['id'],
                    'วันที่': session['start_time'].strftime('%d/%m/%Y'),
                    'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                    'เวลาสิ้นสุด': 'กำลังทำงาน...',
                    'ระยะเวลา': f"{hours:.2f} ชม.",
                    'สถานะ': '🟢 กำลังทำงาน',
                    'ระยะทาง (ม.)': f"{session['distance']:.0f}"
                })
        
        if sessions_data:
            df = pd.DataFrame(sessions_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # ปุ่มจัดการข้อมูล
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 ส่งออกข้อมูล CSV"):
                    self.export_data()
            with col2:
                if st.button("🗑️ ล้างข้อมูลทั้งหมด", type="secondary"):
                    if not st.session_state.is_tracking:
                        st.session_state.work_sessions = []
                        st.success("ล้างข้อมูลเรียบร้อย!")
                        st.rerun()
                    else:
                        st.warning("กรุณาหยุดการทำงานก่อนล้างข้อมูล")

    def render_analytics(self):
        """แสดงการวิเคราะห์ข้อมูล"""
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if len(completed) < 2:
            st.info("ต้องการข้อมูลอย่างน้อย 2 session เพื่อแสดงการวิเคราะห์")
            return
        
        # สร้างกราฟแท่งเวลาทำงานรายวัน
        daily_data = []
        for session in completed:
            date = session['start_time'].date()
            hours = session['duration'].total_seconds() / 3600
            daily_data.append({'วันที่': date, 'ชั่วโมง': hours})
        
        if daily_data:
            df_daily = pd.DataFrame(daily_data)
            df_daily = df_daily.groupby('วันที่')['ชั่วโมง'].sum().reset_index()
            
            # แสดงกราฟ
            fig = px.bar(
                df_daily.tail(7),  # 7 วันล่าสุด
                x='วันที่',
                y='ชั่วโมง',
                title='เวลาทำงานรายวัน',
                color='ชั่วโมง'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # สถิติเพิ่มเติม
        col1, col2, col3 = st.columns(3)
        stats = self.get_statistics()
        
        with col1:
            in_area_count = len([s for s in completed if s['in_work_area']])
            total_count = len(completed)
            percentage = (in_area_count / total_count * 100) if total_count > 0 else 0
            st.metric("ทำงานในพื้นที่", f"{percentage:.1f}%")
        
        with col2:
            avg_hours = stats['total_hours'] / total_count if total_count > 0 else 0
            st.metric("เฉลี่ยต่อครั้ง", f"{avg_hours:.2f} ชม.")
        
        with col3:
            today_target = 8.0
            today_progress = min((stats['today_hours'] / today_target * 100), 100)
            st.metric("ความคืบหน้าวันนี้", f"{today_progress:.1f}%")

    def export_data(self):
        """ส่งออกข้อมูลเป็น CSV"""
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed:
            st.warning("ไม่มีข้อมูลที่จะส่งออก")
            return
        
        data_list = []
        for session in completed:
            data_list.append({
                'วันที่': session['start_time'].strftime('%Y-%m-%d'),
                'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                'เวลาสิ้นสุด': session['end_time'].strftime('%H:%M:%S'),
                'ระยะเวลา (ชม.)': round(session['duration'].total_seconds() / 3600, 2),
                'ในพื้นที่ทำงาน': 'ใช่' if session['in_work_area'] else 'ไม่',
                'ระยะทาง (ม.)': round(session['distance'], 1),
                'ตำแหน่ง': f"{session['location'][0]:.6f}, {session['location'][1]:.6f}"
            })
        
        df = pd.DataFrame(data_list)
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 ดาวน์โหลด CSV",
            data=csv,
            file_name=f"work_time_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    def main(self):
        """ฟังก์ชันหลัก"""
        try:
            self.render_sidebar()
            self.render_main_content()
            
            # Auto-refresh ถ้ากำลังทำงาน
            if st.session_state.is_tracking:
                time.sleep(5)
                st.rerun()
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            st.info("โปรดรีเฟรชหน้าเว็บหรือตรวจสอบการเชื่อมต่อ")

# รันแอพพลิเคชัน
if __name__ == "__main__":
    app = WorkTimeTracker()
    app.main()
