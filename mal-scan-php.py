import streamlit as st
import re
import io
import zipfile
from pathlib import Path
from datetime import datetime
import hashlib
import requests
from urllib.parse import urlparse, urljoin
import time

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

# ========== URL Fetching Functions ==========

def fetch_url_content(url, timeout=10):
    """ดึงเนื้อหาจาก URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        response.raise_for_status()
        return response.text, response.status_code
    except requests.exceptions.Timeout:
        raise Exception(f"Timeout: URL took longer than {timeout}s to respond")
    except requests.exceptions.ConnectionError:
        raise Exception("Connection error: Could not connect to URL")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP Error {response.status_code}: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching URL: {str(e)}")

def is_php_file(url, content=None):
    """ตรวจสอบว่าเป็นไฟล์ PHP หรือไม่"""
    # ตรวจจาก URL
    if url.endswith(('.php', '.phtml', '.php3', '.php4', '.php5')):
        return True
    
    # ตรวจจาก content
    if content:
        if content.strip().startswith('<?php') or '<?php' in content[:200]:
            return True
    
    return False

def extract_php_urls_from_sitemap(sitemap_url):
    """ดึง PHP URLs จาก sitemap"""
    try:
        content, _ = fetch_url_content(sitemap_url)
        
        # หา URLs ใน sitemap
        urls = re.findall(r'<loc>(.*?)</loc>', content)
        
        # กรองเฉพาะไฟล์ PHP
        php_urls = [url for url in urls if url.endswith(('.php', '.phtml'))]
        
        return php_urls
    except Exception as e:
        st.warning(f"⚠️ Could not parse sitemap: {str(e)}")
        return []

def scan_github_repo(repo_url):
    """สแกน GitHub repository"""
    try:
        # แปลง URL ให้เป็น API URL
        # https://github.com/user/repo -> https://api.github.com/repos/user/repo/contents
        
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 5:
            raise Exception("Invalid GitHub URL")
        
        owner = parts[-2]
        repo = parts[-1]
        
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        files = response.json()
        php_files = []
        
        def get_files_recursive(url, path=""):
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return
            
            items = response.json()
            for item in items:
                if item['type'] == 'file' and item['name'].endswith(('.php', '.phtml')):
                    php_files.append({
                        'name': item['path'],
                        'download_url': item['download_url']
                    })
                elif item['type'] == 'dir':
                    get_files_recursive(item['url'], item['path'])
        
        get_files_recursive(api_url)
        
        return php_files
        
    except Exception as e:
        raise Exception(f"Error scanning GitHub repo: {str(e)}")

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
    
    if any(bad_name in filename.lower() for bad_name in COMMON_BACKDOOR_NAMES):
        results.append({
            'type': 'suspicious_filename',
            'severity': 'high',
            'line': 0,
            'code': filename,
            'category': 'backdoor',
            'description': f'Suspicious filename: {filename}'
        })
    
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
    
    if not (filename.endswith('.php') or filename.endswith('.phtml') or 
            content.strip().startswith('<?php') or '<?php' in content[:100]):
        return results
    
    results.extend(check_filename(filename))
    results.extend(scan_dangerous_functions(content, filename))
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

def display_findings(findings, filename, url=None):
    """แสดงผลการค้นพบ"""
    if not findings:
        st.success(f"✅ **{filename}** - No threats detected!")
        if url:
            st.caption(f"🔗 Source: {url}")
        return
    
    score = calculate_risk_score(findings)
    risk_level, emoji = get_risk_level(score)
    
    st.error(f"{emoji} **{filename}** - Risk Level: {risk_level} (Score: {score}/100)")
    if url:
        st.caption(f"🔗 Source: {url}")
    
    severity_groups = {'critical': [], 'high': [], 'medium': []}
    for finding in findings:
        severity = finding.get('severity', 'medium')
        if severity in severity_groups:
            severity_groups[severity].append(finding)
    
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
    ตรวจสอบโค้ด PHP เพื่อหา Malicious Code, Backdoors, Webshells และช่องโหว่ด้าน Security
    """)
    
    # Sidebar
    st.sidebar.header("⚙️ Scanner Settings")
    
    scan_mode = st.sidebar.radio(
        "Select Scan Mode:",
        ["📁 Upload Files", "🌐 Scan from URL", "📋 Multiple URLs", "🐙 GitHub Repository", "📦 ZIP Archive"]
    )
    
    st.sidebar.divider()
    
    show_clean = st.sidebar.checkbox("Show clean files", value=False)
    show_code = st.sidebar.checkbox("Show full code preview", value=False)
    
    st.sidebar.divider()
    
    st.sidebar.subheader("📊 Threat Levels")
    st.sidebar.markdown("""
    - 🔴 **CRITICAL**: ต้องแก้ไขทันที
    - 🟠 **HIGH**: มีความเสี่ยงสูง
    - 🟡 **MEDIUM**: มีความเสี่ยงปานกลาง
    - 🟢 **LOW**: ควรตรวจสอบ
    - ✅ **CLEAN**: ปลอดภัย
    """)
    
    # Main content
    if scan_mode == "📁 Upload Files":
        uploaded_files = st.file_uploader(
            "Upload PHP files",
            type=['php', 'phtml', 'php3', 'php4', 'php5'],
            accept_multiple_files=True,
            help="Upload one or more PHP files to scan"
        )
        
        if uploaded_files:
            total_files = len(uploaded_files)
            total_issues = 0
            total_score = 0
            
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
                    'content': content,
                    'url': None
                })
                
                total_issues += len(findings)
                total_score += score
                
                progress_bar.progress((i + 1) / total_files)
            
            status_text.empty()
            progress_bar.empty()
            
            # สรุปผล
            st.success(f"✅ Scan completed! Scanned {total_files} files")
            
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
            
            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
            
            for result in results_sorted:
                if result['risk_level'] != 'CLEAN' or show_clean:
                    display_findings(result['findings'], result['filename'], result['url'])
                    st.divider()
    
    elif scan_mode == "🌐 Scan from URL":
        st.subheader("🌐 Scan PHP File from URL")
        
        url_input = st.text_input(
            "Enter PHP file URL:",
            placeholder="https://example.com/file.php",
            help="Enter direct URL to a PHP file"
        )
        
        if url_input and st.button("🔍 Scan URL", type="primary"):
            try:
                with st.spinner(f"Fetching {url_input}..."):
                    content, status_code = fetch_url_content(url_input)
                    
                    st.info(f"✅ Fetched successfully (HTTP {status_code})")
                    
                    # ตรวจสอบว่าเป็นไฟล์ PHP
                    if not is_php_file(url_input, content):
                        st.warning("⚠️ This doesn't appear to be a PHP file. Scanning anyway...")
                    
                    # สแกนไฟล์
                    filename = urlparse(url_input).path.split('/')[-1] or 'index.php'
                    findings = scan_file(content, filename)
                    
                    # แสดงสถิติ
                    score = calculate_risk_score(findings)
                    risk_level, emoji = get_risk_level(score)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Risk Score", f"{score}/100")
                    with col2:
                        st.metric("Risk Level", risk_level)
                    with col3:
                        st.metric("Total Issues", len(findings))
                    with col4:
                        file_hash = calculate_file_hash(content)
                        st.metric("File Hash", file_hash[:8] + "...")
                    
                    st.divider()
                    
                    # แสดงผล
                    display_findings(findings, filename, url_input)
                    
                    # แสดง code
                    if show_code:
                        with st.expander("📄 Full Code Preview"):
                            st.code(content, language='php', line_numbers=True)
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    elif scan_mode == "📋 Multiple URLs":
        st.subheader("📋 Scan Multiple URLs")
        
        url_list = st.text_area(
            "Enter URLs (one per line):",
            placeholder="https://example.com/file1.php\nhttps://example.com/file2.php\nhttps://example.com/file3.php",
            height=150,
            help="Enter one URL per line"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            delay = st.slider("Delay between requests (seconds):", 0, 5, 1, help="Prevent rate limiting")
        with col2:
            timeout = st.slider("Request timeout (seconds):", 5, 30, 10)
        
        if url_list and st.button("🚀 Scan All URLs", type="primary"):
            urls = [url.strip() for url in url_list.split('\n') if url.strip()]
            
            if not urls:
                st.warning("⚠️ Please enter at least one URL")
                return
            
            total_files = len(urls)
            st.info(f"📊 Found {total_files} URLs to scan")
            
            total_issues = 0
            total_score = 0
            results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, url in enumerate(urls):
                status_text.text(f"Scanning {url}... ({i+1}/{total_files})")
                
                try:
                    content, status_code = fetch_url_content(url, timeout=timeout)
                    filename = urlparse(url).path.split('/')[-1] or 'index.php'
                    
                    findings = scan_file(content, filename)
                    score = calculate_risk_score(findings)
                    risk_level, emoji = get_risk_level(score)
                    
                    results.append({
                        'filename': filename,
                        'findings': findings,
                        'score': score,
                        'risk_level': risk_level,
                        'url': url,
                        'status': 'success'
                    })
                    
                    total_issues += len(findings)
                    total_score += score
                    
                except Exception as e:
                    results.append({
                        'filename': urlparse(url).path.split('/')[-1] or 'unknown',
                        'findings': [],
                        'score': 0,
                        'risk_level': 'ERROR',
                        'url': url,
                        'status': 'failed',
                        'error': str(e)
                    })
                
                progress_bar.progress((i + 1) / total_files)
                
                # Delay ระหว่าง requests
                if delay > 0 and i < total_files - 1:
                    time.sleep(delay)
            
            status_text.empty()
            progress_bar.empty()
            
            # สรุปผล
            success_count = sum(1 for r in results if r['status'] == 'success')
            failed_count = sum(1 for r in results if r['status'] == 'failed')
            
            st.success(f"✅ Scan completed! {success_count} successful, {failed_count} failed")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total URLs", total_files)
            with col2:
                critical_count = sum(1 for r in results if r['risk_level'] == 'CRITICAL')
                st.metric("Critical Files", critical_count)
            with col3:
                st.metric("Total Issues", total_issues)
            with col4:
                avg_score = total_score / success_count if success_count > 0 else 0
                st.metric("Avg Risk Score", f"{avg_score:.1f}/100")
            
            st.divider()
            
            # แสดงผล
            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
            
            for result in results_sorted:
                if result['status'] == 'failed':
                    st.warning(f"⚠️ **{result['filename']}** - Failed to fetch")
                    st.caption(f"🔗 URL: {result['url']}")
                    st.caption(f"❌ Error: {result.get('error', 'Unknown error')}")
                    st.divider()
                elif result['risk_level'] != 'CLEAN' or show_clean:
                    display_findings(result['findings'], result['filename'], result['url'])
                    st.divider()
    
    elif scan_mode == "🐙 GitHub Repository":
        st.subheader("🐙 Scan GitHub Repository")
        
        repo_url = st.text_input(
            "Enter GitHub repository URL:",
            placeholder="https://github.com/username/repository",
            help="Enter GitHub repository URL (must be public)"
        )
        
        if repo_url and st.button("🔍 Scan Repository", type="primary"):
            try:
                with st.spinner("Fetching repository files..."):
                    php_files = scan_github_repo(repo_url)
                    
                    if not php_files:
                        st.warning("⚠️ No PHP files found in repository")
                        return
                    
                    st.info(f"📦 Found {len(php_files)} PHP files")
                    
                    if st.button("🚀 Start Scanning", type="primary"):
                        total_files = len(php_files)
                        total_issues = 0
                        total_score = 0
                        results = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, file_info in enumerate(php_files):
                            status_text.text(f"Scanning {file_info['name']}... ({i+1}/{total_files})")
                            
                            try:
                                content, _ = fetch_url_content(file_info['download_url'])
                                findings = scan_file(content, file_info['name'])
                                score = calculate_risk_score(findings)
                                risk_level, emoji = get_risk_level(score)
                                
                                results.append({
                                    'filename': file_info['name'],
                                    'findings': findings,
                                    'score': score,
                                    'risk_level': risk_level,
                                    'url': file_info['download_url']
                                })
                                
                                total_issues += len(findings)
                                total_score += score
                                
                            except Exception as e:
                                st.warning(f"⚠️ Could not scan {file_info['name']}: {str(e)}")
                            
                            progress_bar.progress((i + 1) / total_files)
                            time.sleep(0.1)  # Prevent API rate limiting
                        
                        status_text.empty()
                        progress_bar.empty()
                        
                        # สรุปผล
                        st.success(f"✅ Repository scan completed!")
                        
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
                                display_findings(result['findings'], result['filename'], result['url'])
                                st.divider()
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    elif scan_mode == "📦 ZIP Archive":
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
        
        **Scan Modes:**
        - 📁 **Upload Files**: Upload PHP files from your computer
        - 🌐 **Scan from URL**: Scan a single PHP file from URL
        - 📋 **Multiple URLs**: Scan multiple files at once
        - 🐙 **GitHub Repository**: Scan entire GitHub repository
        - 📦 **ZIP Archive**: Upload and scan compressed files
        
        **Detection Capabilities:**
        - 🔴 Dangerous Functions (eval, exec, system, etc.)
        - 🟠 Backdoors & Webshells
        - 🟡 Obfuscated Code
        - 🔵 SQL Injection Patterns
        - 🟣 XSS Vulnerabilities
        - 🟤 Remote Code Execution
        - ⚫ Suspicious Filenames
        
        **Important Notes:**
        - ⚠️ This tool may produce false positives
        - ⚠️ Cannot detect all sophisticated malware
        - ⚠️ Always verify findings manually
        - ⚠️ Use responsibly and legally
        
        **Best Practices:**
        - ✅ Backup before removing files
        - ✅ Keep PHP and plugins updated
        - ✅ Use strong passwords
        - ✅ Limit file permissions
        - ✅ Regular security audits
        """)

if __name__ == "__main__":
    main()
