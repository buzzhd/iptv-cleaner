import os
import requests
import concurrent.futures
import time

# --- CONFIGURATION ---

# GitHub Actions output directory
OUTPUT_DIR = "./public"

# Dictionary of all M3U playlists you want to track and clean
PLAYLIST_PROFILES = {
    "us": "https://iptv-org.github.io/iptv/countries/us.m3u",
    "cn": "https://iptv-org.github.io/iptv/countries/cn.m3u",
    "sports": "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "news": "https://iptv-org.github.io/iptv/categories/news.m3u",
    "zho": "https://iptv-org.github.io/iptv/languages/zho.m3u"
}

# Dictionary of EPG (TV Guide) files to download
# Keys include the file extension so they save correctly locally
EPG_SOURCES = {
    "guide_us.xml.gz": "https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/US_guide.xml.gz",
    "guide_cn.xml": "https://epg.112114.xyz/pp.xml"
}

# Connection settings
TIMEOUT = 5            # Seconds to wait before assuming a stream is dead
MAX_WORKERS = 15       # Limit concurrent threads to prevent resource exhaustion

# --- FUNCTIONS ---

def check_stream(extinf_line, stream_url):
    """Pings the stream URL and immediately severs the connection to save sockets."""
    try:
        # The 'with' statement ensures the connection is explicitly closed immediately
        with requests.get(stream_url, timeout=TIMEOUT, stream=True) as response:
            if response.status_code == 200:
                return f"{extinf_line}\n{stream_url}\n"
    except requests.RequestException:
        pass # Ignore timeouts and connection errors
    return None

def clean_single_playlist(name, url):
    """Downloads a master playlist, tests all links, and saves the working ones."""
    print(f"[{name.upper()}] Fetching source playlist...")
    try:
        # Safely download the master list
        with requests.get(url) as response:
            response.raise_for_status()
            lines = response.text.splitlines()
    except requests.RequestException as e:
        print(f"[{name.upper()}] Error downloading: {e}")
        return

    channels = []

    # Extract EXTINF metadata and the corresponding stream URL
    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            if i + 1 < len(lines) and lines[i+1].startswith("http"):
                channels.append((lines[i], lines[i+1]))

    working_m3u = "#EXTM3U\n"
    
    # Test channels concurrently to save time
    print(f"[{name.upper()}] Testing {len(channels)} channels...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_stream, extinf, stream) for extinf, stream in channels]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                working_m3u += result

    # Save the clean playlist locally
    output_path = os.path.join(OUTPUT_DIR, f"{name}.m3u")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(working_m3u)
    print(f"[{name.upper()}] Cleaned playlist saved to {output_path}")

def fetch_epg(name, url):
    """Downloads EPG files directly to the web directory safely."""
    print(f"[{name.upper()}] Downloading EPG database...")
    try:
        with requests.get(url, timeout=20) as response:
            response.raise_for_status()
            
            # 'name' already contains the correct extension (.xml or .xml.gz)
            output_path = os.path.join(OUTPUT_DIR, name)
            
            # Save as binary to prevent text encoding corruption
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[{name.upper()}] EPG successfully saved to {output_path}")
    except requests.RequestException as e:
        print(f"[{name.upper()}] EPG Download failed: {e}")

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    start_time = time.time()
    
    print("\n=== STARTING IPTV AGGREGATOR ===")
    
    # 1. Process all M3U playlists
    for name, url in PLAYLIST_PROFILES.items():
        clean_single_playlist(name, url)
        print("-" * 30)
        
    # 2. Download all EPG files
    for name, url in EPG_SOURCES.items():
        fetch_epg(name, url)
        
    print("================================")
    print(f"All updates completed in {round(time.time() - start_time, 2)} seconds.\n")
