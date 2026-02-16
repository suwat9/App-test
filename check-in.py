import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
from geopy.distance import geodesic
import requests
import plotly.express as px
import plotly.graph_objects as go

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ระบบบันทึกเวลาปฏิบัติงานด้วยGPS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WorkTimeTracker:
    def __init__(self):
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """เริ่มต้นสถานะ session"""
        if 'work_location' not in st.session_state:
            st.session_state.work_location = {
                'lat': 13.7563,  # กรุงเทพฯ
                'lng': 100.5018,
                'radius': 100,
                'name': 'สถานที่ทำงานหลัก'
            }
        
        if 'work_sessions' not in st.session_state:
            st.session_state.work_sessions = []
            
        if 'is_tracking' not in st.session_state:
            st.session_state.is_tracking = False
            
        if 'current_location' not in st.session_state:
            st.session_state.current_location = None
            
        if 'last_update' not in st.session_state:
            st.session_state.last_update = None

    def get_current_location(self):
        """ดึงตำแหน่งปัจจุบัน (จำลองสำหรับ Streamlit)"""
        try:
            # ในสภาพแวดล้อมจริงควรใช้บริการ geolocation
            # นี่เป็นตัวอย่างการจำลอง
            if st.session_state.current_location is None:
                # สุ่มตำแหน่งรอบๆ พื้นที่ทำงานสำหรับการสาธิต
                lat = st.session_state.work_location['lat'] + np.random.uniform(-0.01, 0.01)
                lng = st.session_state.work_location['lng'] + np.random.uniform(-0.01, 0.01)
                st.session_state.current_location = (lat, lng)
                st.session_state.last_update = datetime.now()
            
            # อัพเดทตำแหน่งเป็นระยะๆ
            elif (datetime.now() - st.session_state.last_update).seconds > 30:
                lat = st.session_state.work_location['lat'] + np.random.uniform(-0.01, 0.01)
                lng = st.session_state.work_location['lng'] + np.random.uniform(-0.01, 0.01)
                st.session_state.current_location = (lat, lng)
                st.session_state.last_update = datetime.now()
                
            return st.session_state.current_location
        except Exception as e:
            st.error(f"ข้อผิดพลาดในการดึงตำแหน่ง: {e}")
            return None

    def is_in_work_area(self, current_lat, current_lng):
        """ตรวจสอบว่าอยู่ในพื้นที่ทำงานหรือไม่"""
        work_coords = (st.session_state.work_location['lat'], 
                      st.session_state.work_location['lng'])
        current_coords = (current_lat, current_lng)
        
        distance = geodesic(work_coords, current_coords).meters
        return distance <= st.session_state.work_location['radius'], distance

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
        st.success("✅ เริ่มบันทึกเวลาทำงานแล้ว")
        return True

    def end_work_session(self):
        """หยุดบันทึกเวลาทำงาน"""
        if not st.session_state.work_sessions or st.session_state.work_sessions[-1]['end_time'] is not None:
            st.warning("ไม่มี session การทำงานที่กำลังดำเนินอยู่")
            return False
            
        st.session_state.work_sessions[-1]['end_time'] = datetime.now()
        st.session_state.work_sessions[-1]['status'] = 'completed'
        
        # คำนวณระยะเวลา
        start_time = st.session_state.work_sessions[-1]['start_time']
        end_time = st.session_state.work_sessions[-1]['end_time']
        duration = end_time - start_time
        st.session_state.work_sessions[-1]['duration'] = duration
        
        st.session_state.is_tracking = False
        st.success("⏹️ หยุดบันทึกเวลาทำงานแล้ว")
        return True

    def get_work_statistics(self):
        """คำนวณสถิติการทำงาน"""
        completed_sessions = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed_sessions:
            return {'total_hours': 0, 'today_hours': 0, 'total_sessions': 0}
        
        total_seconds = sum(
            session['duration'].total_seconds() for session in completed_sessions
        )
        
        today_sessions = [
            s for s in completed_sessions 
            if s['start_time'].date() == datetime.now().date()
        ]
        
        today_seconds = sum(
            session['duration'].total_seconds() for session in today_sessions
        )
        
        return {
            'total_hours': total_seconds / 3600,
            'today_hours': today_seconds / 3600,
            'total_sessions': len(completed_sessions)
        }

    def render_sidebar(self):
        """แสดง sidebar"""
        with st.sidebar:
            st.title("⚙️ การตั้งค่า")
            
            # ตั้งค่าพื้นที่ทำงาน
            st.subheader("ตั้งค่าพื้นที่ทำงาน")
            
            col1, col2 = st.columns(2)
            with col1:
                new_lat = st.number_input(
                    "ละติจูด", 
                    value=st.session_state.work_location['lat'],
                    format="%.6f"
                )
            with col2:
                new_lng = st.number_input(
                    "ลองจิจูด",
                    value=st.session_state.work_location['lng'],
                    format="%.6f"
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
            
            if st.button("💾 บันทึกการตั้งค่า"):
                st.session_state.work_location.update({
                    'lat': new_lat,
                    'lng': new_lng,
                    'radius': new_radius,
                    'name': work_name
                })
                st.success("บันทึกการตั้งค่าเรียบร้อย!")
                
            st.divider()
            
            # การจัดการข้อมูล
            st.subheader("การจัดการข้อมูล")
            if st.button("🗑️ ล้างข้อมูลทั้งหมด"):
                if st.session_state.is_tracking:
                    st.warning("กรุณาหยุดการทำงานก่อนล้างข้อมูล")
                else:
                    st.session_state.work_sessions = []
                    st.success("ล้างข้อมูลเรียบร้อย!")
                    
            # สถิติแบบสรุป
            stats = self.get_work_statistics()
            st.divider()
            st.subheader("📊 สถิติแบบสรุป")
            st.metric("รวมเวลาทำงาน", f"{stats['total_hours']:.2f} ชั่วโมง")
            st.metric("เวลาทำงานวันนี้", f"{stats['today_hours']:.2f} ชั่วโมง")
            st.metric("จำนวน session", stats['total_sessions'])

    def render_location_status(self):
        """แสดงสถานะตำแหน่งปัจจุบัน"""
        st.header("📍 สถานะตำแหน่งปัจจุบัน")
        
        col1, col2, col3 = st.columns(3)
        
        location = self.get_current_location()
        if location:
            lat, lng = location
            in_area, distance = self.is_in_work_area(lat, lng)
            
            with col1:
                status_color = "🟢" if in_area else "🔴"
                status_text = "อยู่ในพื้นที่ทำงาน" if in_area else "นอกพื้นที่ทำงาน"
                st.metric("สถานะ", f"{status_color} {status_text}")
                
            with col2:
                st.metric("ระยะทาง", f"{distance:.2f} เมตร")
                
            with col3:
                st.metric("ตำแหน่ง", f"{lat:.6f}, {lng:.6f}")
                
            # แสดงแผนที่
            self.render_map(lat, lng, in_area, distance)
        else:
            st.error("ไม่สามารถดึงข้อมูลตำแหน่งได้")

    def render_map(self, lat, lng, in_area, distance):
        """แสดงแผนที่"""
        # สร้างข้อมูลสำหรับแผนที่
        work_lat = st.session_state.work_location['lat']
        work_lng = st.session_state.work_location['lng']
        
        df = pd.DataFrame({
            'lat': [work_lat, lat],
            'lng': [work_lng, lng],
            'type': ['พื้นที่ทำงาน', 'ตำแหน่งปัจจุบัน'],
            'size': [20, 10]
        })
        
        fig = px.scatter_mapbox(
            df,
            lat="lat",
            lon="lng",
            color="type",
            size="size",
            hover_data={"type": True, "size": False},
            zoom=15,
            height=300
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":0,"l":0,"b":0},
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def render_control_panel(self):
        """แสดงแผงควบคุม"""
        st.header("🎛️ แผงควบคุมการทำงาน")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if not st.session_state.is_tracking:
                if st.button("🚀 เริ่มทำงาน", type="primary", use_container_width=True):
                    self.start_work_session()
            else:
                st.info("🟢 กำลังบันทึกเวลาทำงาน...")
                
        with col2:
            if st.session_state.is_tracking:
                if st.button("⏹️ หยุดทำงาน", type="secondary", use_container_width=True):
                    self.end_work_session()
            else:
                st.button("⏹️ หยุดทำงาน", disabled=True, use_container_width=True)
                
        with col3:
            if st.button("🔄 อัพเดทตำแหน่ง", use_container_width=True):
                st.session_state.current_location = None
                st.rerun()

    def render_work_sessions(self):
        """แสดงประวัติการทำงาน"""
        st.header("📋 ประวัติการทำงาน")
        
        if not st.session_state.work_sessions:
            st.info("ยังไม่มีประวัติการทำงาน")
            return
            
        # สร้าง DataFrame สำหรับแสดงผล
        sessions_data = []
        for session in reversed(st.session_state.work_sessions[-20:]):  # แสดง 20 รายการล่าสุด
            if session['status'] == 'completed':
                sessions_data.append({
                    'ลำดับ': session['id'],
                    'วันที่': session['start_time'].strftime('%Y-%m-%d'),
                    'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                    'เวลาหยุด': session['end_time'].strftime('%H:%M:%S'),
                    'ระยะเวลา': str(session['duration']).split('.')[0],
                    'สถานะ': '✅' if session['in_work_area'] else '⚠️',
                    'ระยะทาง (ม.)': f"{session['distance']:.1f}"
                })
            else:  # session กำลังดำเนินอยู่
                sessions_data.append({
                    'ลำดับ': session['id'],
                    'วันที่': session['start_time'].strftime('%Y-%m-%d'),
                    'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                    'เวลาหยุด': 'กำลังทำงาน...',
                    'ระยะเวลา': 'กำลังคำนวณ...',
                    'สถานะ': '🟢 กำลังทำงาน',
                    'ระยะทาง (ม.)': f"{session['distance']:.1f}"
                })
        
        if sessions_data:
            df = pd.DataFrame(sessions_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการทำงานที่เสร็จสมบูรณ์")

    def render_analytics(self):
        """แสดงการวิเคราะห์ข้อมูล"""
        st.header("📈 การวิเคราะห์ข้อมูล")
        
        completed_sessions = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        if not completed_sessions:
            st.info("ไม่มีข้อมูลเพียงพอสำหรับการวิเคราะห์")
            return
            
        # แผนภูมิเวลาทำงานรายวัน
        df_daily = pd.DataFrame([
            {
                'date': session['start_time'].date(),
                'hours': session['duration'].total_seconds() / 3600
            }
            for session in completed_sessions
        ])
        
        if not df_daily.empty:
            daily_summary = df_daily.groupby('date')['hours'].sum().reset_index()
            
            fig_daily = px.bar(
                daily_summary.tail(7),  # 7 วันล่าสุด
                x='date',
                y='hours',
                title='เวลาทำงานรายวัน (7 วันล่าสุด)',
                labels={'hours': 'ชั่วโมง', 'date': 'วันที่'}
            )
            st.plotly_chart(fig_daily, use_container_width=True)
            
        # สถิติเพิ่มเติม
        col1, col2, col3 = st.columns(3)
        stats = self.get_work_statistics()
        
        with col1:
            avg_duration = stats['total_hours'] / max(stats['total_sessions'], 1)
            st.metric("⏱️ เฉลี่ยต่อ session", f"{avg_duration:.2f} ชั่วโมง")
            
        with col2:
            in_area_sessions = len([s for s in completed_sessions if s['in_work_area']])
            in_area_percent = (in_area_sessions / max(len(completed_sessions), 1)) * 100
            st.metric("✅ ทำงานในพื้นที่", f"{in_area_percent:.1f}%")
            
        with col3:
            today_target = 8.0  # 8 ชั่วโมงต่อวัน
            progress = min(stats['today_hours'] / today_target * 100, 100)
            st.metric("🎯 ความคืบหน้าวันนี้", f"{progress:.1f}%")

    def main(self):
        """ฟังก์ชันหลัก"""
        # Header
        st.title("🏢 ระบบบันทึกเวลาปฏิบัติงานด้วยGPS")
        st.markdown("---")
        
        # Auto-refresh สำหรับการอัพเดทตำแหน่ง
        if st.session_state.is_tracking:
            st_auto_refresh = st.checkbox("อัพเดทตำแหน่งอัตโนมัติ", value=True)
            if st_auto_refresh:
                time.sleep(2)  # รอ 2 วินาที
                st.rerun()
        
        # เรนเดอร์คอมโพเนนต์ต่างๆ
        self.render_sidebar()
        self.render_location_status()
        self.render_control_panel()
        self.render_work_sessions()
        self.render_analytics()

# รันแอพพลิเคชัน
if __name__ == "__main__":
    app = WorkTimeTracker()
    app.main()
