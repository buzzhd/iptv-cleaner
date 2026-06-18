import os
import requests
import concurrent.futures
import time

# --- CONFIGURATION ---

OUTPUT_DIR = "/var/www/html/iptv"

PLAYLIST_PROFILES = {
    "us": "https://iptv-org.github.io/iptv/countries/us.m3u",
    "cn": "https://iptv-org.github.io/iptv/countries/cn.m3u",
    "sports": "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "news": "https://iptv-org.github.io/iptv/categories/news.m3u",
    "zho": "https://iptv-org.github.io/iptv/languages/zho.m3u"
}

EPG_SOURCES = {
    "guide_us": "https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml",
    "guide_cn": "https://epg.112114.xyz/pp.xml"
}

TIMEOUT = 5            
# Reduced to 20 to prevent overwhelming smaller systems/VMs
MAX_WORKERS = 20       

# --- FUNCTIONS ---

def check_stream(extinf_line, stream_url):
    """Pings the stream URL and closes the socket immediately to prevent memory leaks."""
    try:
        # The 'with' context manager automatically closes the hanging video stream connection
        with requests.get(stream_url, timeout=TIMEOUT, stream=True) as response:
            if response.status_code == 200:
                return f"{extinf_line}\n{stream_url}\n"
    except requests.RequestException:
        pass 
    return None

def clean_single_playlist(name, url):
    print(f"[{name.upper()}] Fetching source playlist...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[{name.upper()}] Error downloading: {e}")
        return

    lines = response.text.splitlines()
    channels = []

    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            if i + 1 < len(lines) and lines[i+1].startswith("http"):
                channels.append((lines[i], lines[i+1]))

    working_m3u = "#EXTM3U\n"
    
    print(f"[{name.upper()}] Testing {len(channels)} channels...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_stream, extinf, stream) for extinf, stream in channels]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                working_m3u += result

    output_path = os.path.join(OUTPUT_DIR, f"{name}.m3u")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(working_m3u)
    print(f"[{name.upper()}] Cleaned playlist saved to {output_path}")

def fetch_epg(name, url):
    print(f"[{name.upper()}] Downloading EPG database...")
    try:
        response = requests.get(url, timeout=20) 
        response.raise_for_status()
        
        output_path = os.path.join(OUTPUT_DIR, f"{name}.xml")
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"[{name.upper()}] EPG successfully saved to {output_path}")
    except requests.RequestException as e:
        print(f"[{name.upper()}] EPG Download failed: {e}")

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start_time = time.time()
    
    print("\n=== STARTING IPTV AGGREGATOR ===")
    
    for name, url in PLAYLIST_PROFILES.items():
        clean_single_playlist(name, url)
        print("-" * 30)
        
    for name, url in EPG_SOURCES.items():
        fetch_epg(name, url)
        
    print("================================")
    print(f"All updates completed in {round(time.time() - start_time, 2)} seconds.\n")
