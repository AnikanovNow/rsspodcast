#!/usr/bin/env python3
# coding: utf-8
"""
generate_rss.py
Usage:
  export YT_API_KEY="ВАШ_КЛЮЧ"
  python scripts/generate_rss.py --playlist PLSiLlNvYaVdUVIuzS5wL_s8izfq24jPrw --output youtube_podcast_rss.xml
"""

import os
import sys
import argparse
import requests
import xml.etree.ElementTree as ET
from email.utils import formatdate
from datetime import datetime
from time import mktime

YT_API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

def rfc2822_from_iso(isodate):
    try:
        dt = datetime.fromisoformat(isodate.replace("Z","+00:00"))
        ts = mktime(dt.timetuple())
        return formatdate(ts, usegmt=True)
    except Exception:
        return formatdate(usegmt=True)

def fetch_all_playlist_items(api_key, playlist_id):
    items = []
    params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": api_key
    }
    while True:
        r = requests.get(YT_API_URL, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        for it in j.get("items", []):
            sn = it.get("snippet", {})
            if not sn or sn.get("title") == "Deleted video" or sn.get("title") == "Private video":
                continue
            vid = sn.get("resourceId", {}).get("videoId")
            if not vid:
                continue
            items.append({
                "videoId": vid,
                "title": sn.get("title",""),
                "description": sn.get("description",""),
                "publishedAt": sn.get("publishedAt", "")
            })
        token = j.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token
    return items

def safe_text(text):
    if text is None:
        return ""
    return text

def build_rss(channel_info, episodes):
    itunes_ns = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    ET.register_namespace('itunes', itunes_ns)
    rss = ET.Element("rss", version="2.0", attrib={"xmlns:itunes": itunes_ns})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = channel_info.get("title","")
    ET.SubElement(channel, "link").text = channel_info.get("link","")
    ET.SubElement(channel, "description").text = channel_info.get("description","")
    ET.SubElement(channel, "language").text = channel_info.get("language","ru")
    ET.SubElement(channel, "{%s}author" % itunes_ns).text = channel_info.get("author","")
    ET.SubElement(channel, "{%s}explicit" % itunes_ns).text = "false"
    ET.SubElement(channel, "{%s}category" % itunes_ns, attrib={"text": channel_info.get("category","Religion & Spirituality")})

    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep["title"]
        ET.SubElement(item, "link").text = f"https://www.youtube.com/watch?v={ep['videoId']}"
        guid = ET.SubElement(item, "guid", isPermaLink="true")
        guid.text = f"https://www.youtube.com/watch?v={ep['videoId']}"
        pubdate = rfc2822_from_iso(ep.get("publishedAt",""))
        ET.SubElement(item, "pubDate").text = pubdate
        desc = ET.SubElement(item, "description")
        desc.text = ep.get("description","")
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", f"https://www.youtube.com/watch?v={ep['videoId']}")
        enclosure.set("type", "video/mp4")
        enclosure.set("length", "1000000")
    return ET.ElementTree(rss)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", required=True, help="YouTube playlist ID")
    parser.add_argument("--output", default="youtube_podcast_rss.xml", help="Output RSS filename")
    args = parser.parse_args()

    api_key = os.environ.get("YT_API_KEY")
    if not api_key:
        print("ERROR: set environment variable YT_API_KEY with your API key", file=sys.stderr)
        sys.exit(1)

    print("Fetching playlist items...")
    episodes = fetch_all_playlist_items(api_key, args.playlist)
    print(f"Found {len(episodes)} episodes")

    channel_info = {
        "title": "Подкаст Югадхармы",
        "link": f"https://www.youtube.com/playlist?list={args.playlist}",
        "description": "Вайшнавские беседы и тренинги.",
        "language": "ru",
        "author": "Югадхарма дас",
        "category": "Religion & Spirituality"
    }

    tree = build_rss(channel_info, episodes)
    print(f"Writing to {args.output} ...")
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print("Done. Validate the file with an RSS validator (castfeedvalidator.com) and then upload to your host.")

if __name__ == "__main__":
    main()
