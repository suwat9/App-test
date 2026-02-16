import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import json
import io

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
            'manual_lat': 13.7563,
            'manual_lng': 100.5018,
            'location_method': 'simulation'
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
        """ดึงตำแหน่งปัจจุบัน"""
        if st.session_state.location_method == 'manual':
            return (st.session_state.manual_lat, st.session_state.manual_lng)
        
        # Simulation mode - สุ่มตำแหน่งรอบพื้นที่ทำงาน
        if (st.session_state.current_location is None or 
            (datetime.now() - getattr(st.session_state, 'last_update', datetime.now())).seconds > 30):
            
            # สุ่มตำแหน่งรอบพื้นที่ทำงาน
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
        
        return True

    def end_work_session(self):
        """หยุดบันทึกเวลาทำงาน"""
        active_sessions = [s for s in st.session_state.work_sessions if s['status'] == 'active']
        
        if not active_sessions:
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
        return True

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

    def render_header(self):
        """แสดง header"""
        st.title("🏢 ระบบบันทึกเวลาปฏิบัติงานด้วย GPS")
        st.markdown("---")
        
        # สถานะปัจจุบัน
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.is_tracking:
                st.success("🟢 **กำลังบันทึกเวลา**")
                # คำนวณเวลาที่ผ่านไป
                active_session = next((s for s in st.session_state.work_sessions if s['status'] == 'active'), None)
                if active_session:
                    elapsed = datetime.now() - active_session['start_time']
                    hours = elapsed.total_seconds() / 3600
                    st.write(f"⏱️ เวลาที่ผ่านไป: **{hours:.2f} ชม.**")
            else:
                st.info("🔴 **ไม่ได้บันทึกเวลา**")
        
        with col2:
            location = self.get_current_location()
            if location:
                lat, lng = location
                in_area, distance = self.is_in_work_area(lat, lng)
                
                status_emoji = "✅" if in_area else "⚠️"
                status_text = "อยู่ในพื้นที่" if in_area else "นอกพื้นที่"
                st.write(f"{status_emoji} **สถานะพื้นที่:** {status_text}")
                st.write(f"📏 **ระยะทาง:** {distance:.0f} เมตร")
        
        with col3:
            if location:
                st.write("📍 **ตำแหน่งปัจจุบัน:**")
                st.write(f"ละติจูด: {lat:.6f}")
                st.write(f"ลองจิจูด: {lng:.6f}")

    def render_sidebar(self):
        """แสดง sidebar"""
        with st.sidebar:
            st.header("⚙️ การตั้งค่า")
            
            # การตั้งค่าตำแหน่ง
            st.subheader("📍 วิธีการกำหนดตำแหน่ง")
            location_method = st.radio(
                "เลือกวิธีการ:",
                ["ตำแหน่งจำลอง", "ป้อนตำแหน่งเอง"],
                index=0 if st.session_state.location_method == 'simulation' else 1
            )
            
            st.session_state.location_method = 'simulation' if location_method == "ตำแหน่งจำลอง" else 'manual'
            
            if location_method == "ป้อนตำแหน่งเอง":
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
                
                if st.button("🔄 ใช้ตำแหน่งนี้"):
                    st.session_state.current_location = (st.session_state.manual_lat, st.session_state.manual_lng)
                    st.success("อัพเดทตำแหน่งเรียบร้อย!")
            
            st.subheader("🏢 ตั้งค่าพื้นที่ทำงาน")
            
            col1, col2 = st.columns(2)
            with col1:
                work_lat = st.number_input(
                    "ละติจูด", 
                    value=st.session_state.work_location['lat'],
                    format="%.6f",
                    key="work_lat"
                )
            with col2:
                work_lng = st.number_input(
                    "ลองจิจูด",
                    value=st.session_state.work_location['lng'],
                    format="%.6f",
                    key="work_lng"
                )
            
            work_radius = st.slider(
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
                    'lat': work_lat,
                    'lng': work_lng,
                    'radius': work_radius,
                    'name': work_name
                })
                st.success("บันทึกการตั้งค่าเรียบร้อย!")
            
            st.markdown("---")
            
            # การควบคุม
            st.subheader("🎮 การควบคุม")
            
            col1, col2 = st.columns(2)
            with col1:
                if not st.session_state.is_tracking:
                    if st.button("🚀 เริ่มทำงาน", type="primary", use_container_width=True):
                        if self.start_work_session():
                            st.success("เริ่มบันทึกเวลาทำงานแล้ว!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.button("🚀 เริ่มทำงาน", disabled=True, use_container_width=True)
            
            with col2:
                if st.session_state.is_tracking:
                    if st.button("⏹️ หยุดทำงาน", type="secondary", use_container_width=True):
                        if self.end_work_session():
                            st.success("หยุดบันทึกเวลาทำงานแล้ว!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.button("⏹️ หยุดทำงาน", disabled=True, use_container_width=True)
            
            if st.button("🔄 อัพเดทตำแหน่ง", use_container_width=True):
                if st.session_state.location_method == 'simulation':
                    st.session_state.current_location = None
                st.rerun()
            
            st.markdown("---")
            
            # สถิติ
            st.subheader("📊 สถิติ")
            stats = self.get_statistics()
            
            st.metric("⏱️ เวลาวันนี้", f"{stats['today_hours']:.2f} ชม.")
            st.metric("📈 เวลารวม", f"{stats['total_hours']:.2f} ชม.")
            st.metric("🔢 จำนวนครั้ง", stats['total_sessions'])

    def render_location_map(self):
        """แสดงข้อมูลตำแหน่งแบบง่าย (ไม่ใช้แผนที่)"""
        st.subheader("🗺️ ข้อมูลตำแหน่ง")
        
        location = self.get_current_location()
        if not location:
            st.warning("ไม่สามารถดึงตำแหน่งได้")
            return
            
        lat, lng = location
        work_lat = st.session_state.work_location['lat']
        work_lng = st.session_state.work_location['lng']
        in_area, distance = self.is_in_work_area(lat, lng)
        
        # สร้าง visualization แบบง่ายด้วย text
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### 📍 ตำแหน่งปัจจุบัน")
            st.write(f"**ละติจูด:** {lat:.6f}")
            st.write(f"**ลองจิจูด:** {lng:.6f}")
            st.write(f"**สถานะ:** {'✅ อยู่ในพื้นที่ทำงาน' if in_area else '⚠️ นอกพื้นที่ทำงาน'}")
            st.write(f"**ระยะทาง:** {distance:.0f} เมตร")
        
        with col2:
            st.write("### 🏢 พื้นที่ทำงาน")
            st.write(f"**ชื่อ:** {st.session_state.work_location['name']}")
            st.write(f"**ศูนย์กลาง:** {work_lat:.6f}, {work_lng:.6f}")
            st.write(f"**รัศมี:** {st.session_state.work_location['radius']} เมตร")
            
            # แสดงระยะทางแบบกราฟิกง่ายๆ
            max_distance = max(distance, st.session_state.work_location['radius'])
            progress = min(distance / st.session_state.work_location['radius'], 2.0)
            
            if in_area:
                st.progress(progress, text=f"อยู่ในพื้นที่ ({distance:.0f}m / {st.session_state.work_location['radius']}m)")
            else:
                st.progress(1.0, text=f"นอกพื้นที่ (+{distance - st.session_state.work_location['radius']:.0f}m)")
        
        # Visualization แบบง่ายด้วย HTML
        st.markdown("""
        <style>
        .location-visualization {
            background: #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 10px 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        status_color = "#28a745" if in_area else "#dc3545"
        st.markdown(f"""
        <div class="location-visualization">
            <h3>🎯 สถานะตำแหน่ง</h3>
            <p style="font-size: 24px; color: {status_color}; font-weight: bold;">
                {'✅ อยู่ในพื้นที่ทำงาน' if in_area else '⚠️ นอกพื้นที่ทำงาน'}
            </p>
            <p>ระยะทางจากศูนย์กลาง: <strong>{distance:.0f} เมตร</strong></p>
            <p>รัศมีที่อนุญาต: <strong>{st.session_state.work_location['radius']} เมตร</strong></p>
        </div>
        """, unsafe_allow_html=True)

    def render_work_sessions(self):
        """แสดงประวัติการทำงาน"""
        st.subheader("📋 ประวัติการทำงาน")
        
        if not st.session_state.work_sessions:
            st.info("ยังไม่มีประวัติการทำงาน")
            return
        
        # สร้างข้อมูลสำหรับตาราง
        sessions_data = []
        for session in reversed(st.session_state.work_sessions[-15:]):  # 15 รายการล่าสุด
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
            # แสดงเป็นตารางแบบง่าย
            for session in sessions_data:
                with st.expander(f"Session #{session['ลำดับ']} - {session['วันที่']} {session['เวลาเริ่ม']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**เริ่ม:** {session['เวลาเริ่ม']}")
                        st.write(f"**สิ้นสุด:** {session['เวลาสิ้นสุด']}")
                    with col2:
                        st.write(f"**ระยะเวลา:** {session['ระยะเวลา']}")
                        st.write(f"**สถานะ:** {session['สถานะ']}")
                    with col3:
                        st.write(f"**ระยะทาง:** {session['ระยะทาง (ม.)']}")
            
            # สรุปข้อมูล
            st.markdown("---")
            self.render_session_summary()
        else:
            st.info("ไม่มี session ที่เสร็จสมบูรณ์")

    def render_session_summary(self):
        """แสดงสรุป session"""
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed:
            return
        
        st.write("### 📊 สรุปข้อมูล")
        cols = st.columns(4)
        
        stats = self.get_statistics()
        
        with cols[0]:
            st.metric("รวมเวลาทำงาน", f"{stats['total_hours']:.2f} ชม.")
        
        with cols[1]:
            st.metric("เวลาวันนี้", f"{stats['today_hours']:.2f} ชม.")
        
        with cols[2]:
            in_area_count = len([s for s in completed if s['in_work_area']])
            percentage = (in_area_count / len(completed)) * 100
            st.metric("ทำงานในพื้นที่", f"{percentage:.1f}%")
        
        with cols[3]:
            avg_hours = stats['total_hours'] / len(completed) if completed else 0
            st.metric("เฉลี่ยต่อครั้ง", f"{avg_hours:.2f} ชม.")
        
        # ปุ่มจัดการข้อมูล
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 ส่งออกข้อมูล CSV", use_container_width=True):
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

    def export_data(self):
        """ส่งออกข้อมูลเป็น CSV"""
        completed = [s for s in st.session_state.work_sessions if s['status'] == 'completed']
        
        if not completed:
            st.warning("ไม่มีข้อมูลที่จะส่งออก")
            return
        
        data_list = []
        for session in completed:
            data_list.append({
                'ลำดับ': session['id'],
                'วันที่': session['start_time'].strftime('%Y-%m-%d'),
                'เวลาเริ่ม': session['start_time'].strftime('%H:%M:%S'),
                'เวลาสิ้นสุด': session['end_time'].strftime('%H:%M:%S'),
                'ระยะเวลา (ชม.)': round(session['duration'].total_seconds() / 3600, 2),
                'ในพื้นที่ทำงาน': 'ใช่' if session['in_work_area'] else 'ไม่',
                'ระยะทาง (ม.)': round(session['distance'], 1),
                'ละติจูด': session['location'][0],
                'ลองจิจูด': session['location'][1]
            })
        
        df = pd.DataFrame(data_list)
        
        # สร้าง CSV ใน memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_string = csv_buffer.getvalue()
        
        # ปุ่มดาวน์โหลด
        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ CSV",
            data=csv_string,
            file_name=f"work_time_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # แสดงตัวอย่างข้อมูล
        st.write("### ตัวอย่างข้อมูลที่จะส่งออก:")
        st.dataframe(df.head(), use_container_width=True)

    def main(self):
        """ฟังก์ชันหลัก"""
        try:
            # Render หน้าเว็บ
            self.render_header()
            self.render_sidebar()
            
            # เนื้อหาหลัก
            tab1, tab2 = st.tabs(["📍 สถานะตำแหน่ง", "📋 ประวัติการทำงาน"])
            
            with tab1:
                self.render_location_map()
            
            with tab2:
                self.render_work_sessions()
            
            # Auto-refresh ถ้ากำลังทำงาน
            if st.session_state.is_tracking:
                time.sleep(5)
                st.rerun()
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            st.info("โปรดรีเฟรชหน้าเว็บ")

# รันแอพพลิเคชัน
if __name__ == "__main__":
    app = WorkTimeTracker()
    app.main()
