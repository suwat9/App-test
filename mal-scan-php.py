import streamlit as st
import re
import io
import zipfile
from pathlib import Path
from datetime import datetime
import hashlib
import requests
from urllib.parse import urlparse, urljoin, quote
import time
from bs4 import BeautifulSoup
import json
import pandas as pd
from collections import defaultdict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title="PHP Site Scanner",
    page_icon="🌐",
    layout="wide"
)

# ========== Malicious Patterns Database (เหมือนเดิม) ==========
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
}

COMMON_BACKDOOR_NAMES = [
    'shell.php', 'c99.php', 'r57.php', 'backdoor.php',
    'wso.php', 'b374k.php', 'adminer.php', 'webshell.php',
    '1.php', '404.php', 'xx.php', 'a.php', 'test.php'
]

# ========== Site Crawler ==========

class WebsiteCrawler:
    def __init__(self, base_url, max_depth=3, max_pages=100, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout
        self.visited_urls = set()
        self.php_files = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def is_same_domain(self, url):
        """ตรวจสอบว่า URL อยู่ใน domain เดียวกัน"""
        return urlparse(url).netloc == self.domain
    
    def is_php_file(self, url):
        """ตรวจสอบว่าเป็นไฟล์ PHP"""
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in ['.php', '.phtml', '.php3', '.php4', '.php5'])
    
    def normalize_url(self, url):
        """ทำให้ URL เป็นมาตรฐาน"""
        parsed = urlparse(url)
        # ลบ fragment (#)
        url = url.split('#')[0]
        # ลบ trailing slash ถ้าไม่ใช่ root
        if parsed.path != '/' and url.endswith('/'):
            url = url[:-1]
        return url
    
    def get_links_from_page(self, url):
        """ดึงลิงก์ทั้งหมดจากหน้าเว็บ"""
        try:
            response = self.session.get(url, timeout=self.timeout, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            # หา links จาก <a> tags
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                normalized_url = self.normalize_url(absolute_url)
                
                if self.is_same_domain(normalized_url):
                    links.append(normalized_url)
            
            return links
        except Exception as e:
            return []
    
    def crawl(self, url=None, depth=0, progress_callback=None):
        """Crawl เว็บไซต์"""
        if url is None:
            url = self.base_url
        
        url = self.normalize_url(url)
        
        # ตรวจสอบเงื่อนไข
        if (depth > self.max_depth or 
            url in self.visited_urls or 
            len(self.visited_urls) >= self.max_pages or
            not self.is_same_domain(url)):
            return
        
        self.visited_urls.add(url)
        
        if progress_callback:
            progress_callback(url, len(self.visited_urls), len(self.php_files))
        
        # ถ้าเป็นไฟล์ PHP เก็บไว้
        if self.is_php_file(url):
            self.php_files.append(url)
        
        # ดึงลิงก์จากหน้านี้
        links = self.get_links_from_page(url)
        
        # Crawl ลิงก์ที่เจอ
        for link in links:
            if len(self.visited_urls) < self.max_pages:
                self.crawl(link, depth + 1, progress_callback)
            else:
                break
    
    def try_common_paths(self):
        """ลองเข้า path ที่พบบ่อย"""
        common_paths = [
            '/wp-admin/', '/wp-content/', '/wp-includes/',
            '/admin/', '/administrator/', '/manager/',
            '/includes/', '/inc/', '/lib/', '/libs/',
            '/plugins/', '/modules/', '/themes/',
            '/uploads/', '/upload/', '/files/',
            '/api/', '/ajax/', '/cron/',
            '/index.php', '/admin.php', '/login.php',
            '/config.php', '/settings.php'
        ]
        
        found_urls = []
        
        for path in common_paths:
            url = self.base_url + path
            try:
                response = self.session.head(url, timeout=5, verify=False, allow_redirects=True)
                if response.status_code == 200:
                    normalized_url = self.normalize_url(url)
                    if normalized_url not in self.visited_urls:
                        found_urls.append(normalized_url)
                        if self.is_php_file(normalized_url):
                            self.php_files.append(normalized_url)
            except:
                pass
        
        return found_urls
    
    def try_sitemap(self):
        """ลองดึงข้อมูลจาก sitemap.xml"""
        sitemap_urls = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap1.xml',
            '/wp-sitemap.xml'
        ]
        
        php_urls = []
        
        for sitemap_path in sitemap_urls:
            try:
                url = self.base_url + sitemap_path
                response = self.session.get(url, timeout=self.timeout, verify=False)
                response.raise_for_status()
                
                # Parse sitemap
                urls = re.findall(r'<loc>(.*?)</loc>', response.text)
                
                for found_url in urls:
                    if self.is_same_domain(found_url):
                        normalized_url = self.normalize_url(found_url)
                        if normalized_url not in self.visited_urls:
                            self.visited_urls.add(normalized_url)
                            if self.is_php_file(normalized_url):
                                php_urls.append(normalized_url)
                
                break  # ถ้าเจอ sitemap แล้วไม่ต้องลองอันอื่น
                
            except:
                continue
        
        return php_urls

# ========== Scanning Functions (เหมือนเดิม) ==========

def calculate_file_hash(content):
    return hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()

def scan_dangerous_functions(content, filename):
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
    
    return results

def scan_file(content, filename):
    results = []
    
    if not (filename.endswith('.php') or filename.endswith('.phtml') or 
            content.strip().startswith('<?php') or '<?php' in content[:100]):
        return results
    
    results.extend(check_filename(filename))
    results.extend(scan_dangerous_functions(content, filename))
    results.extend(scan_suspicious_patterns(content, filename))
    
    return results

def calculate_risk_score(findings):
    score = 0
    severity_weights = {'critical': 10, 'high': 5, 'medium': 2}
    
    for finding in findings:
        severity = finding.get('severity', 'medium')
        score += severity_weights.get(severity, 1)
    
    return min(score, 100)

def get_risk_level(score):
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

def fetch_url_content(url, timeout=10):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        response.raise_for_status()
        return response.text, response.status_code
    except Exception as e:
        raise Exception(f"Error fetching URL: {str(e)}")

# ========== Report Generation ==========

def generate_summary_stats(results):
    """สร้างสถิติสรุป"""
    total_files = len(results)
    total_issues = sum(len(r['findings']) for r in results)
    
    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    
    for result in results:
        for finding in result['findings']:
            severity_counts[finding['severity']] += 1
            if 'category' in finding:
                category_counts[finding['category']] += 1
    
    risk_levels = defaultdict(int)
    for result in results:
        risk_levels[result['risk_level']] += 1
    
    return {
        'total_files': total_files,
        'total_issues': total_issues,
        'severity_counts': dict(severity_counts),
        'category_counts': dict(category_counts),
        'risk_levels': dict(risk_levels),
        'clean_files': risk_levels.get('CLEAN', 0),
        'infected_files': total_files - risk_levels.get('CLEAN', 0)
    }

def export_to_csv(results):
    """Export ผลเป็น CSV"""
    data = []
    
    for result in results:
        data.append({
            'URL': result['url'],
            'Filename': result['filename'],
            'Risk Level': result['risk_level'],
            'Risk Score': result['score'],
            'Total Issues': len(result['findings']),
            'Critical': sum(1 for f in result['findings'] if f['severity'] == 'critical'),
            'High': sum(1 for f in result['findings'] if f['severity'] == 'high'),
            'Medium': sum(1 for f in result['findings'] if f['severity'] == 'medium'),
        })
    
    df = pd.DataFrame(data)
    return df

def export_detailed_json(results):
    """Export รายละเอียดเป็น JSON"""
    return json.dumps(results, indent=2, ensure_ascii=False)

# ========== UI ==========

def display_finding_summary(result):
    """แสดงสรุปแต่ละไฟล์"""
    score = result['score']
    risk_level, emoji = get_risk_level(score)
    
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.markdown(f"**{result['filename']}**")
        st.caption(f"🔗 {result['url']}")
    with col2:
        if risk_level == 'CRITICAL':
            st.error(f"{emoji} {risk_level}")
        elif risk_level == 'HIGH':
            st.warning(f"{emoji} {risk_level}")
        elif risk_level == 'MEDIUM':
            st.info(f"{emoji} {risk_level}")
        else:
            st.success(f"{emoji} {risk_level}")
    with col3:
        st.metric("Score", f"{score}/100")
    with col4:
        st.metric("Issues", len(result['findings']))

def main():
    st.title("🌐 PHP Website Malware Scanner")
    st.markdown("""
    สแกนเว็บไซต์ทั้งหมดเพื่อหา Malicious Code ในไฟล์ PHP
    """)
    
    # Sidebar
    st.sidebar.header("⚙️ Scanner Settings")
    
    # Website URL
    website_url = st.sidebar.text_input(
        "🌐 Website URL:",
        placeholder="https://example.com",
        help="Enter the website URL to scan"
    )
    
    st.sidebar.divider()
    
    st.sidebar.subheader("🔍 Crawling Options")
    
    crawler_method = st.sidebar.radio(
        "Scanning Method:",
        ["Auto Crawl", "Sitemap Only", "Common Paths", "Full Scan (All Methods)"]
    )
    
    if crawler_method in ["Auto Crawl", "Full Scan (All Methods)"]:
        max_depth = st.sidebar.slider("Max Crawl Depth:", 1, 5, 3)
        max_pages = st.sidebar.slider("Max Pages to Visit:", 10, 500, 100)
    else:
        max_depth = 2
        max_pages = 50
    
    st.sidebar.divider()
    
    st.sidebar.subheader("⚡ Performance")
    timeout = st.sidebar.slider("Request Timeout (sec):", 5, 30, 10)
    delay = st.sidebar.slider("Delay Between Requests (sec):", 0.0, 2.0, 0.5, 0.1)
    
    st.sidebar.divider()
    
    show_clean = st.sidebar.checkbox("Show clean files", value=False)
    
    # Main Content
    if website_url:
        if st.button("🚀 Start Website Scan", type="primary", use_container_width=True):
            
            # Phase 1: Crawling
            st.subheader("🕷️ Phase 1: Website Crawling")
            
            crawler = WebsiteCrawler(
                website_url, 
                max_depth=max_depth, 
                max_pages=max_pages,
                timeout=timeout
            )
            
            crawl_status = st.empty()
            crawl_progress = st.progress(0)
            
            php_files_found = set()
            
            def update_progress(url, visited, php_count):
                crawl_status.info(f"🔍 Crawling: {url[:60]}... | Visited: {visited} | PHP files: {php_count}")
            
            # Crawl ตาม method ที่เลือก
            if crawler_method in ["Auto Crawl", "Full Scan (All Methods)"]:
                st.info("🕷️ Auto crawling website...")
                crawler.crawl(progress_callback=update_progress)
                php_files_found.update(crawler.php_files)
            
            if crawler_method in ["Sitemap Only", "Full Scan (All Methods)"]:
                st.info("🗺️ Checking sitemap...")
                sitemap_files = crawler.try_sitemap()
                php_files_found.update(sitemap_files)
                st.success(f"✅ Found {len(sitemap_files)} PHP files from sitemap")
            
            if crawler_method in ["Common Paths", "Full Scan (All Methods)"]:
                st.info("📁 Checking common paths...")
                common_files = crawler.try_common_paths()
                php_files_found.update(common_files)
                st.success(f"✅ Found {len(common_files)} files from common paths")
            
            crawl_status.empty()
            crawl_progress.empty()
            
            php_files_list = list(php_files_found)
            
            if not php_files_list:
                st.warning("⚠️ No PHP files found on this website!")
                st.info("""
                **Possible reasons:**
                - Website doesn't use PHP
                - PHP files are protected/hidden
                - Crawler couldn't access them
                - Try different scanning method
                """)
                return
            
            st.success(f"✅ Crawling completed! Found **{len(php_files_list)}** PHP files")
            
            # แสดงรายการไฟล์ที่เจอ
            with st.expander(f"📄 View {len(php_files_list)} PHP Files Found"):
                for i, url in enumerate(php_files_list, 1):
                    st.text(f"{i}. {url}")
            
            st.divider()
            
            # Phase 2: Scanning
            st.subheader("🔍 Phase 2: Malware Scanning")
            
            total_files = len(php_files_list)
            results = []
            
            scan_progress = st.progress(0)
            scan_status = st.empty()
            
            for i, url in enumerate(php_files_list):
                scan_status.info(f"🔍 Scanning: {url[:60]}... ({i+1}/{total_files})")
                
                try:
                    content, status_code = fetch_url_content(url, timeout=timeout)
                    filename = urlparse(url).path.split('/')[-1] or 'index.php'
                    
                    findings = scan_file(content, filename)
                    score = calculate_risk_score(findings)
                    risk_level, emoji = get_risk_level(score)
                    
                    results.append({
                        'url': url,
                        'filename': filename,
                        'findings': findings,
                        'score': score,
                        'risk_level': risk_level,
                        'status': 'success',
                        'hash': calculate_file_hash(content)
                    })
                    
                except Exception as e:
                    results.append({
                        'url': url,
                        'filename': urlparse(url).path.split('/')[-1] or 'unknown',
                        'findings': [],
                        'score': 0,
                        'risk_level': 'ERROR',
                        'status': 'failed',
                        'error': str(e)
                    })
                
                scan_progress.progress((i + 1) / total_files)
                
                if delay > 0 and i < total_files - 1:
                    time.sleep(delay)
            
            scan_status.empty()
            scan_progress.empty()
            
            # Phase 3: Results
            st.divider()
            st.subheader("📊 Scan Results")
            
            # สถิติ
            stats = generate_summary_stats(results)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Files", stats['total_files'])
            with col2:
                st.metric("Clean Files", stats['clean_files'], delta="Good" if stats['clean_files'] > 0 else None)
            with col3:
                st.metric("Infected Files", stats['infected_files'], delta="Bad" if stats['infected_files'] > 0 else None)
            with col4:
                st.metric("Total Issues", stats['total_issues'])
            with col5:
                infection_rate = (stats['infected_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
                st.metric("Infection Rate", f"{infection_rate:.1f}%")
            
            # Severity breakdown
            st.divider()
            st.subheader("⚠️ Severity Breakdown")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                critical = stats['severity_counts'].get('critical', 0)
                st.metric("🔴 Critical", critical)
            with col2:
                high = stats['severity_counts'].get('high', 0)
                st.metric("🟠 High", high)
            with col3:
                medium = stats['severity_counts'].get('medium', 0)
                st.metric("🟡 Medium", medium)
            
            # Category breakdown
            if stats['category_counts']:
                st.divider()
                st.subheader("📈 Threat Categories")
                
                category_data = pd.DataFrame(
                    list(stats['category_counts'].items()),
                    columns=['Category', 'Count']
                ).sort_values('Count', ascending=False)
                
                st.bar_chart(category_data.set_index('Category'))
            
            # Export
            st.divider()
            st.subheader("💾 Export Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV Export
                csv_df = export_to_csv(results)
                csv = csv_df.to_csv(index=False)
                
                st.download_button(
                    "📥 Download CSV Report",
                    data=csv,
                    file_name=f"malware_scan_{urlparse(website_url).netloc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # JSON Export
                json_data = export_detailed_json(results)
                
                st.download_button(
                    "📥 Download JSON Report",
                    data=json_data,
                    file_name=f"malware_scan_{urlparse(website_url).netloc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            # Detailed Results
            st.divider()
            st.subheader("📋 Detailed Scan Results")
            
            # แสดงผลเรียงตาม risk score
            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
            
            # แยกตาม risk level
            critical_files = [r for r in results_sorted if r['risk_level'] == 'CRITICAL']
            high_files = [r for r in results_sorted if r['risk_level'] == 'HIGH']
            medium_files = [r for r in results_sorted if r['risk_level'] == 'MEDIUM']
            low_files = [r for r in results_sorted if r['risk_level'] == 'LOW']
            clean_files = [r for r in results_sorted if r['risk_level'] == 'CLEAN']
            error_files = [r for r in results_sorted if r['status'] == 'failed']
            
            # Critical Files
            if critical_files:
                st.error(f"🔴 CRITICAL RISK FILES ({len(critical_files)})")
                for result in critical_files:
                    with st.expander(f"🔴 {result['filename']} - Score: {result['score']}/100"):
                        st.caption(f"🔗 {result['url']}")
                        st.caption(f"🔑 Hash: {result.get('hash', 'N/A')}")
                        
                        for finding in result['findings']:
                            st.markdown(f"""
                            **Line {finding['line']}**: {finding['description']}
                            ```php
                            {finding['code']}
                            ```
                            """)
            
            # High Risk Files
            if high_files:
                st.warning(f"🟠 HIGH RISK FILES ({len(high_files)})")
                for result in high_files:
                    with st.expander(f"🟠 {result['filename']} - Score: {result['score']}/100"):
                        st.caption(f"🔗 {result['url']}")
                        st.caption(f"🔑 Hash: {result.get('hash', 'N/A')}")
                        
                        for finding in result['findings']:
                            st.markdown(f"""
                            **Line {finding['line']}**: {finding['description']}
                            ```php
                            {finding['code']}
                            ```
                            """)
            
            # Medium Risk Files
            if medium_files:
                with st.expander(f"🟡 MEDIUM RISK FILES ({len(medium_files)})"):
                    for result in medium_files:
                        display_finding_summary(result)
                        st.divider()
            
            # Low Risk Files
            if low_files:
                with st.expander(f"🟢 LOW RISK FILES ({len(low_files)})"):
                    for result in low_files:
                        display_finding_summary(result)
                        st.divider()
            
            # Clean Files
            if show_clean and clean_files:
                with st.expander(f"✅ CLEAN FILES ({len(clean_files)})"):
                    for result in clean_files:
                        st.success(f"✅ {result['filename']}")
                        st.caption(f"🔗 {result['url']}")
                        st.divider()
            
            # Error Files
            if error_files:
                with st.expander(f"❌ ERROR FILES ({len(error_files)})"):
                    for result in error_files:
                        st.error(f"❌ {result['filename']}")
                        st.caption(f"🔗 {result['url']}")
                        st.caption(f"Error: {result.get('error', 'Unknown error')}")
                        st.divider()
    
    else:
        st.info("👈 Enter a website URL in the sidebar to start scanning")
        
        st.markdown("""
        ### 🚀 How to Use:
        
        1. **Enter Website URL** - Input the website you want to scan
        2. **Choose Scanning Method**:
           - **Auto Crawl**: Automatically find PHP files by crawling
           - **Sitemap Only**: Use sitemap.xml to find files
           - **Common Paths**: Check common directories
           - **Full Scan**: Use all methods combined
        3. **Configure Settings** - Adjust depth, limits, and delays
        4. **Start Scan** - Click the scan button
        5. **Review Results** - Check findings and export reports
        
        ### ⚠️ Important Notes:
        
        - Only scan websites you have permission to scan
        - Respect robots.txt and terms of service
        - Use appropriate delays to avoid overwhelming servers
        - Results may include false positives
        - Always verify findings manually
        
        ### 📊 What Gets Scanned:
        
        - ✅ All PHP files on the website
        - ✅ Dangerous functions (eval, exec, system, etc.)
        - ✅ Backdoor patterns
        - ✅ Webshell signatures
        - ✅ Obfuscated code
        - ✅ SQL injection patterns
        - ✅ XSS vulnerabilities
        - ✅ Suspicious filenames
        """)
    
    # Footer
    st.divider()
    with st.expander("ℹ️ About This Scanner"):
        st.markdown("""
        ### 🌐 PHP Website Malware Scanner
        
        **Scanning Methods:**
        - 🕷️ **Auto Crawl**: Follows links to discover PHP files
        - 🗺️ **Sitemap**: Parses sitemap.xml for URLs
        - 📁 **Common Paths**: Checks frequently used directories
        - 🔍 **Full Scan**: Combines all methods for comprehensive coverage
        
        **Detection Capabilities:**
        - Dangerous PHP functions
        - Backdoor code patterns
        - Webshell signatures (c99, r57, wso, etc.)
        - Obfuscated/encoded code
        - SQL injection attempts
        - XSS vulnerabilities
        - Remote code execution
        - Suspicious file naming
        
        **Features:**
        - Site-wide scanning
        - Automatic file discovery
        - Risk scoring (0-100)
        - Severity classification
        - CSV/JSON export
        - Detailed reports
        - Progress tracking
        
        **Best Practices:**
        - Get permission before scanning
        - Use appropriate delays
        - Start with small limits
        - Review all findings manually
        - Export reports for documentation
        
        **Limitations:**
        - Cannot detect all malware types
        - May produce false positives
        - Requires internet access
        - Limited by site structure
        - Respects rate limiting
        """)

if __name__ == "__main__":
    main()
