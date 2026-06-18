import os
import requests
import concurrent.futures
import time

# --- CONFIGURATION ---

OUTPUT_DIR = "./public"

PLAYLIST_PROFILES = {
    "us": "https://iptv-org.github.io/iptv/countries/us.m3u",
    "cn": "https://iptv-org.github.io/iptv/countries/cn.m3u",
    "sports": "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "news": "https://iptv-org.github.io/iptv/categories/news.m3u",
    "zho": "https://iptv-org.github.io/iptv/languages/zho.m3u"
}

# The keys represent the exact filename that will be saved
EPG_SOURCES = {
    "guide_us.xml.gz": "https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/US_guide.xml.gz",
    "guide_cn.xml": "https://epg.112114.xyz/pp.xml"
}

TIMEOUT = 5
MAX_WORKERS = 15

# --- FUNCTIONS ---

def check_stream(extinf_line, stream_url):
    try:
        with requests.get(stream_url, timeout=TIMEOUT, stream=True) as response:
            if response.status_code == 200:
                return f"{extinf_line}\n{stream_url}\n"
    except requests.RequestException:
        pass
    return None

def clean_single_playlist(name, url):
    print(f"[{name.upper()}] Fetching source playlist...")
    try:
        with requests.get(url) as response:
            response.raise_for_status()
            lines = response.text.splitlines()
    except requests.RequestException as e:
        print(f"[{name.upper()}] Error: {e}")
        return

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
    print(f"[{name.upper()}] Saved to {output_path}")

def fetch_epg(filename, url):
    print(f"[{filename.upper()}] Downloading EPG database...")
    try:
        with requests.get(url, timeout=20) as response:
            response.raise_for_status()
            
            # Save the file exactly as named in the dictionary (keeps .gz extension)
            output_path = os.path.join(OUTPUT_DIR, filename)
            with open(output_path, "wb") as f:
                f.write(response.content)
                
            print(f"[{filename.upper()}] EPG successfully saved to {output_path}")
    except Exception as e:
        print(f"[{filename.upper()}] EPG Download failed: {e}")

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start_time = time.time()
    
    for name, url in PLAYLIST_PROFILES.items():
        clean_single_playlist(name, url)
        
    for filename, url in EPG_SOURCES.items():
        fetch_epg(filename, url)
        
    print(f"Completed in {round(time.time() - start_time, 2)}s.")
