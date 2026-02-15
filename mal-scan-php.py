import streamlit as st
import re
import io
import zipfile
from pathlib import Path
from datetime import datetime
import hashlib

st.set_page_config(
    page_title="PHP Malware Scanner",
    page_icon="🛡️",
    layout="wide"
)

# ========== Malicious Patterns Database ==========
DANGEROUS_FUNCTIONS = {
    'critical': [
        'eval', 'exec', 'system', 'shell_exec', 'passthru', 
        'popen', 'proc_open', 'pcntl_exec', 'assert',
        'create_function', 'preg_replace.*\/e'
    ],
    'high': [
        'base64_decode', 'gzinflate', 'gzuncompress', 'str_rot13',
        'file_get_contents', 'file_put_contents', 'fwrite', 'fputs',
        'curl_exec', 'curl_multi_exec', 'parse_str', 'extract',
        'move_uploaded_file', 'copy', 'rename'
    ],
    'medium': [
        'include', 'require', 'include_once', 'require_once',
        'readfile', 'fopen', 'file', 'glob', 'opendir',
        'chmod', 'chown', 'chgrp', 'unlink', 'rmdir', 'mkdir'
    ]
}

SUSPICIOUS_PATTERNS = {
    'backdoor': [
        r'\$_(?:GET|POST|REQUEST|COOKIE|SERVER)\s*\[.*?\]\s*\(',
        r'@?eval\s*\(\s*(?:base64_decode|gzinflate|str_rot13)',
        r'assert\s*\(\s*[\'"]?\$',
        r'preg_replace\s*\(.*?\/e',
        r'system\s*\(\s*\$',
        r'shell_exec\s*\(\s*\$',
    ],
    'obfuscation': [
        r'base64_decode\s*\(\s*[\'"][A-Za-z0-9+/=]{50,}',
        r'gzinflate\s*\(\s*base64_decode',
        r'str_rot13\s*\(\s*[\'"]',
        r'eval\s*\(\s*gzinflate',
        r'\$[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*\s*=\s*[\'"][^\'"]{100,}',
    ],
    'webshell': [
        r'c99shell|r57shell|wso|b374k|indoxploit',
        r'FilesMan|Filestools|Backconnect',
        r'Safe[_\s]?Mode[_\s]?Bypass',
        r'\$auth_pass\s*=',
        r'passthru|shell_exec.*?cmd',
    ],
    'sql_injection': [
        r'(select|union|insert|update|delete).*from.*where',
        r'(union|select).*\-\-',
        r'benchmark\s*\(\s*\d+',
        r'sleep\s*\(\s*\d+',
        r'(and|or)\s+1\s*=\s*1',
    ],
    'xss': [
        r'<script[^>]*>.*?</script>',
        r'on(load|error|click|mouse)\s*=',
        r'javascript\s*:',
        r'<iframe[^>]*>',
        r'document\.cookie',
    ],
    'file_upload': [
        r'move_uploaded_file\s*\(',
        r'\$_FILES\[',
        r'is_uploaded_file\s*\(',
        r'copy\s*\(\s*\$_FILES',
    ],
    'remote_code': [
        r'file_get_contents\s*\(\s*[\'"]https?://',
        r'curl_exec\s*\(',
        r'fsockopen\s*\(',
        r'stream_socket_client\s*\(',
    ]
}

COMMON_BACKDOOR_NAMES = [
    'shell.php', 'c99.php', 'r57.php', 'backdoor.php',
    'wso.php', 'b374k.php', 'adminer.php', 'webshell.php',
    '1.php', '404.php', 'xx.php', 'a.php', 'test.php'
]

# ========== Scanning Functions ==========

def calculate_file_hash(content):
    """คำนวณ MD5 hash ของไฟล์"""
    return hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()

def scan_dangerous_functions(content, filename):
    """สแกนหา dangerous functions"""
    results = []
    lines = content.split('\n')
    
    for severity, functions in DANGEROUS_FUNCTIONS.items():
        for func in functions:
            pattern = rf'\b{func}\s*\('
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    results.append({
                        'type': 'dangerous_function',
                        'severity': severity,
                        'line': i,
                        'code': line.strip(),
                        'function': func,
                        'description': f'Dangerous function: {func}()'
                    })
    
    return results

def scan_suspicious_patterns(content, filename):
    """สแกนหา suspicious patterns"""
    results = []
    lines = content.split('\n')
    
    for category, patterns in SUSPICIOUS_PATTERNS.items():
        for pattern in patterns:
            for i, line in enumerate(lines, 1):
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    results.append({
                        'type': 'suspicious_pattern',
                        'severity': 'high' if category in ['backdoor', 'webshell'] else 'medium',
                        'line': i,
                        'code': line.strip(),
                        'category': category,
                        'description': f'Suspicious {category} pattern detected'
                    })
    
    return results

def check_filename(filename):
    """ตรวจสอบชื่อไฟล์ที่น่าสงสัย"""
    results = []
    
    # ตรวจสอบชื่อไฟล์ที่เป็น backdoor ทั่วไป
    if any(bad_name in filename.lower() for bad_name in COMMON_BACKDOOR_NAMES):
        results.append({
            'type': 'suspicious_filename',
            'severity': 'high',
            'line': 0,
            'code': filename,
            'category': 'backdoor',
            'description': f'Suspicious filename: {filename}'
        })
    
    # ตรวจสอบไฟล์ที่มีชื่อสั้นผิดปกติ
    if len(Path(filename).stem) <= 2 and filename.endswith('.php'):
        results.append({
            'type': 'suspicious_filename',
            'severity': 'medium',
            'line': 0,
            'code': filename,
            'category': 'unusual',
            'description': f'Unusually short filename: {filename}'
        })
    
    return results

def scan_file(content, filename):
    """สแกนไฟล์ทั้งหมด"""
    results = []
    
    # ตรวจสอบว่าเป็นไฟล์ PHP หรือไม่
    if not (filename.endswith('.php') or filename.endswith('.phtml') or 
            content.strip().startswith('<?php') or '<?php' in content[:100]):
        return results
    
    # สแกนชื่อไฟล์
    results.extend(check_filename(filename))
    
    # สแกน dangerous functions
    results.extend(scan_dangerous_functions(content, filename))
    
    # สแกน suspicious patterns
    results.extend(scan_suspicious_patterns(content, filename))
    
    return results

def calculate_risk_score(findings):
    """คำนวณคะแนนความเสี่ยง"""
    score = 0
    severity_weights = {'critical': 10, 'high': 5, 'medium': 2}
    
    for finding in findings:
        severity = finding.get('severity', 'medium')
        score += severity_weights.get(severity, 1)
    
    return min(score, 100)

def get_risk_level(score):
    """กำหนดระดับความเสี่ยง"""
    if score >= 50:
        return 'CRITICAL', '🔴'
    elif score >= 30:
        return 'HIGH', '🟠'
    elif score >= 10:
        return 'MEDIUM', '🟡'
    elif score > 0:
        return 'LOW', '🟢'
    else:
        return 'CLEAN', '✅'

# ========== UI Functions ==========

def display_findings(findings, filename):
    """แสดงผลการค้นพบ"""
    if not findings:
        st.success(f"✅ **{filename}** - No threats detected!")
        return
    
    # คำนวณคะแนน
    score = calculate_risk_score(findings)
    risk_level, emoji = get_risk_level(score)
    
    # แสดงหัวข้อพร้อมความเสี่ยง
    st.error(f"{emoji} **{filename}** - Risk Level: {risk_level} (Score: {score}/100)")
    
    # จัดกลุ่มตาม severity
    severity_groups = {'critical': [], 'high': [], 'medium': []}
    for finding in findings:
        severity = finding.get('severity', 'medium')
        if severity in severity_groups:
            severity_groups[severity].append(finding)
    
    # แสดงผลแต่ละกลุ่ม
    for severity in ['critical', 'high', 'medium']:
        if severity_groups[severity]:
            color = {'critical': '🔴', 'high': '🟠', 'medium': '🟡'}[severity]
            
            with st.expander(f"{color} {severity.upper()} - {len(severity_groups[severity])} issues", expanded=(severity == 'critical')):
                for i, finding in enumerate(severity_groups[severity], 1):
                    st.markdown(f"""
                    **#{i}** Line {finding['line']}: {finding['description']}
                    ```php
                    {finding['code']}
                    ```
                    """)

def main():
    st.title("🛡️ PHP Malware Scanner")
    st.markdown("""
    ตรวจสอบโค้ด PHP เพื่อหา:
    - 🔴 Dangerous Functions (eval, exec, system, etc.)
    - 🟠 Backdoors & Webshells
    - 🟡 Obfuscated Code
    - 🔵 SQL Injection Patterns
    - 🟣 XSS Vulnerabilities
    - 🟤 Remote Code Execution
    """)
    
    # Sidebar
    st.sidebar.header("⚙️ Scanner Settings")
    
    scan_mode = st.sidebar.radio(
        "Select Scan Mode:",
        ["Single File", "Multiple Files", "ZIP Archive"]
    )
    
    st.sidebar.divider()
    
    show_clean = st.sidebar.checkbox("Show clean files", value=False)
    show_code = st.sidebar.checkbox("Show full code preview", value=False)
    
    st.sidebar.divider()
    
    st.sidebar.subheader("📊 Threat Categories")
    st.sidebar.markdown("""
    - **CRITICAL** 🔴: Immediate action required
    - **HIGH** 🟠: Serious security risk
    - **MEDIUM** 🟡: Potential vulnerability
    - **LOW** 🟢: Minor concern
    - **CLEAN** ✅: No threats detected
    """)
    
    # Main content
    if scan_mode == "Single File":
        uploaded_file = st.file_uploader(
            "Upload PHP file",
            type=['php', 'phtml', 'php3', 'php4', 'php5'],
            help="Upload a single PHP file to scan"
        )
        
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            filename = uploaded_file.name
            
            with st.spinner(f"Scanning {filename}..."):
                findings = scan_file(content, filename)
                
                # แสดงสถิติ
                col1, col2, col3, col4 = st.columns(4)
                score = calculate_risk_score(findings)
                risk_level, emoji = get_risk_level(score)
                
                with col1:
                    st.metric("Risk Score", f"{score}/100")
                with col2:
                    st.metric("Risk Level", risk_level, delta=None)
                with col3:
                    st.metric("Total Issues", len(findings))
                with col4:
                    file_hash = calculate_file_hash(content)
                    st.metric("File Hash", file_hash[:8] + "...")
                
                st.divider()
                
                # แสดงผลการสแกน
                display_findings(findings, filename)
                
                # แสดง code ทั้งหมด
                if show_code:
                    with st.expander("📄 Full Code Preview"):
                        st.code(content, language='php', line_numbers=True)
    
    elif scan_mode == "Multiple Files":
        uploaded_files = st.file_uploader(
            "Upload multiple PHP files",
            type=['php', 'phtml', 'php3', 'php4', 'php5'],
            accept_multiple_files=True,
            help="Upload multiple PHP files to scan"
        )
        
        if uploaded_files:
            total_files = len(uploaded_files)
            total_issues = 0
            total_score = 0
            critical_files = []
            high_risk_files = []
            clean_files = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Scanning {uploaded_file.name}... ({i+1}/{total_files})")
                
                content = uploaded_file.read().decode('utf-8', errors='ignore')
                filename = uploaded_file.name
                findings = scan_file(content, filename)
                
                score = calculate_risk_score(findings)
                risk_level, emoji = get_risk_level(score)
                
                results.append({
                    'filename': filename,
                    'findings': findings,
                    'score': score,
                    'risk_level': risk_level,
                    'content': content
                })
                
                total_issues += len(findings)
                total_score += score
                
                if risk_level == 'CRITICAL':
                    critical_files.append(filename)
                elif risk_level == 'HIGH':
                    high_risk_files.append(filename)
                elif risk_level == 'CLEAN':
                    clean_files.append(filename)
                
                progress_bar.progress((i + 1) / total_files)
            
            status_text.empty()
            progress_bar.empty()
            
            # สรุปผลการสแกน
            st.success(f"✅ Scan completed! Scanned {total_files} files")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Files", total_files)
            with col2:
                st.metric("Critical Files", len(critical_files))
            with col3:
                st.metric("Total Issues", total_issues)
            with col4:
                avg_score = total_score / total_files if total_files > 0 else 0
                st.metric("Avg Risk Score", f"{avg_score:.1f}/100")
            
            st.divider()
            
            # แสดงไฟล์ที่มีปัญหาก่อน
            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
            
            for result in results_sorted:
                if result['risk_level'] != 'CLEAN' or show_clean:
                    display_findings(result['findings'], result['filename'])
                    st.divider()
    
    elif scan_mode == "ZIP Archive":
        uploaded_zip = st.file_uploader(
            "Upload ZIP archive",
            type=['zip'],
            help="Upload a ZIP file containing PHP files"
        )
        
        if uploaded_zip:
            try:
                with zipfile.ZipFile(io.BytesIO(uploaded_zip.read())) as z:
                    php_files = [f for f in z.namelist() if f.endswith(('.php', '.phtml'))]
                    
                    if not php_files:
                        st.warning("⚠️ No PHP files found in ZIP archive")
                        return
                    
                    total_files = len(php_files)
                    st.info(f"📦 Found {total_files} PHP files in archive")
                    
                    if st.button("🚀 Start Scanning", type="primary"):
                        total_issues = 0
                        total_score = 0
                        results = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, filename in enumerate(php_files):
                            status_text.text(f"Scanning {filename}... ({i+1}/{total_files})")
                            
                            try:
                                content = z.read(filename).decode('utf-8', errors='ignore')
                                findings = scan_file(content, filename)
                                score = calculate_risk_score(findings)
                                risk_level, emoji = get_risk_level(score)
                                
                                results.append({
                                    'filename': filename,
                                    'findings': findings,
                                    'score': score,
                                    'risk_level': risk_level
                                })
                                
                                total_issues += len(findings)
                                total_score += score
                                
                            except Exception as e:
                                st.warning(f"⚠️ Could not read {filename}: {str(e)}")
                            
                            progress_bar.progress((i + 1) / total_files)
                        
                        status_text.empty()
                        progress_bar.empty()
                        
                        # สรุปผล
                        st.success(f"✅ Scan completed!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Files", total_files)
                        with col2:
                            critical_count = sum(1 for r in results if r['risk_level'] == 'CRITICAL')
                            st.metric("Critical Files", critical_count)
                        with col3:
                            st.metric("Total Issues", total_issues)
                        with col4:
                            avg_score = total_score / total_files if total_files > 0 else 0
                            st.metric("Avg Risk Score", f"{avg_score:.1f}/100")
                        
                        st.divider()
                        
                        # แสดงผล
                        results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
                        
                        for result in results_sorted:
                            if result['risk_level'] != 'CLEAN' or show_clean:
                                display_findings(result['findings'], result['filename'])
                                st.divider()
                        
            except Exception as e:
                st.error(f"❌ Error reading ZIP file: {str(e)}")
    
    # Footer
    st.divider()
    with st.expander("ℹ️ About This Scanner"):
        st.markdown("""
        ### 🛡️ PHP Malware Scanner
        
        เครื่องมือสแกนหา malicious code ในไฟล์ PHP
        
        #### ตรวจจับได้:
        - **Dangerous Functions**: eval(), exec(), system(), shell_exec(), etc.
        - **Backdoors**: Common webshell patterns
        - **Obfuscation**: base64_decode, gzinflate, etc.
        - **SQL Injection**: Suspicious SQL patterns
        - **XSS**: Cross-site scripting patterns
        - **Remote Code Execution**: file_get_contents from URLs, curl, etc.
        - **Suspicious Filenames**: Common backdoor names
        
        #### ข้อจำกัด:
        - ไม่สามารถตรวจจับ malware ที่ซับซ้อนมากทั้งหมด
        - อาจมี false positives (โค้ดปกติถูกตรวจพบว่าน่าสงสัย)
        - ควรใช้ร่วมกับเครื่องมืออื่นๆ
        
        #### คำแนะนำ:
        - ตรวจสอบโค้ดที่พบด้วยตัวเองเสมอ
        - สำรองข้อมูลก่อนลบไฟล์
        - อัพเดท PHP และ plugins เป็นประจำ
        - ใช้ strong passwords
        - จำกัดสิทธิ์การเข้าถึงไฟล์
        """)

if __name__ == "__main__":
    main()
