import statistics
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.config import YOUTUBE_API_KEY, SEARCH_QUERIES

def discover_youtube_influencers(target_count: int = 65) -> list[dict]:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    discovered_channel_ids = set()

    print(f"[Discovery] Searching YouTube across {len(SEARCH_QUERIES)} niche queries (Target: {target_count} profiles)...")
    for query in SEARCH_QUERIES:
        if len(discovered_channel_ids) >= target_count:
            break
        page_token = None
        # Supports pagination up to 500+ channels when target_count is increased
        for _ in range(3):
            if len(discovered_channel_ids) >= target_count:
                break
            try:
                req = youtube.search().list(
                    q=query,
                    part="snippet",
                    type="video",
                    maxResults=50,
                    pageToken=page_token,
                    order="relevance",
                    relevanceLanguage="en"
                )
                res = req.execute()
                for item in res.get("items", []):
                    discovered_channel_ids.add(item["snippet"]["channelId"])
                page_token = res.get("nextPageToken")
                if not page_token:
                    break
            except HttpError as e:
                print(f"[Discovery Warning] YouTube Search API limit/error: {e}")
                break

    channel_id_list = list(discovered_channel_ids)[:target_count]
    print(f"[Discovery] Found {len(channel_id_list)} unique channels. Fetching metrics...")

    profiles = []
    for i in range(0, len(channel_id_list), 50):
        batch_ids = channel_id_list[i:i+50]
        try:
            ch_req = youtube.channels().list(
                id=",".join(batch_ids),
                part="snippet,statistics,contentDetails"
            )
            ch_res = ch_req.execute()
        except Exception as e:
            print(f"[Discovery Warning] Channel batch fetch error: {e}")
            continue

        for ch in ch_res.get("items", []):
            cid = ch["id"]
            snippet = ch["snippet"]
            stats = ch["statistics"]
            
            if stats.get("hiddenSubscriberCount", False):
                continue
                
            subs = int(stats.get("subscriberCount", 0))
            total_views = int(stats.get("viewCount", 0))
            video_count = max(int(stats.get("videoCount", 1)), 1)
            custom_url = snippet.get("customUrl", f"channel/{cid}")
            profile_url = f"https://www.youtube.com/{custom_url}" if custom_url.startswith("@") else f"https://www.youtube.com/channel/{cid}"

            # Early Gate: If outside 5k-100k micro-influencer window, estimate baseline ER from channel stats to save API quota
            if subs < 5000 or subs > 100000:
                avg_views_per_vid = total_views / video_count
                est_er = round(min((avg_views_per_vid / max(subs, 1)) * 3.5, 25.0), 2)
                profiles.append({
                    "channel_id": cid,
                    "name": snippet.get("title", "Unknown").strip(),
                    "platform": "YouTube",
                    "profile_url": profile_url,
                    "followers": subs,
                    "engagement_rate": est_er,
                    "raw_description": snippet.get("description", ""),
                    "country": snippet.get("country", "Global"),
                    "recent_videos": "Channel outside 5k-100k micro-influencer subscriber bounds"
                })
                continue

            uploads_playlist = ch["contentDetails"]["relatedPlaylists"].get("uploads")
            video_context = _fetch_recent_video_engagement(youtube, uploads_playlist, subs)
            if not video_context["titles"]:
                continue

            combined_description = snippet.get("description", "") + "\n" + "\n".join(video_context["descs"])
            rich_video_summary = (
                f"LATEST VIDEO: '{video_context['latest_title']}' ({video_context['latest_views']:,} views) - Context: {video_context['latest_snippet']} || "
                f"MOST POPULAR RECENT VIDEO: '{video_context['popular_title']}' ({video_context['popular_views']:,} views, {video_context['popular_likes']:,} likes) - Context: {video_context['popular_snippet']} || "
                f"OTHER VIDEOS: {' | '.join(video_context['titles'][:4])}"
            )

            profiles.append({
                "channel_id": cid,
                "name": snippet.get("title", "Unknown").strip(),
                "platform": "YouTube",
                "profile_url": profile_url,
                "followers": subs,
                "engagement_rate": round(video_context["median_er"], 2),
                "raw_description": combined_description,
                "country": snippet.get("country", "Global"),
                "recent_videos": rich_video_summary
            })

    print(f"[Discovery] Successfully extracted {len(profiles)} complete influencer profiles.")
    return profiles

def _fetch_recent_video_engagement(youtube, playlist_id: str, followers: int) -> dict:
    empty_res = {"titles": [], "median_er": 0.0, "descs": []}
    if not playlist_id or followers == 0:
        return empty_res
    try:
        pl_req = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="contentDetails",
            maxResults=6
        )
        pl_res = pl_req.execute()
        video_ids = [item["contentDetails"]["videoId"] for item in pl_res.get("items", [])]
        if not video_ids:
            return empty_res

        v_req = youtube.videos().list(
            id=",".join(video_ids),
            part="snippet,statistics"
        )
        v_res = v_req.execute()

        video_records = []
        er_list = []
        for v in v_res.get("items", []):
            title = v["snippet"]["title"]
            desc = v["snippet"].get("description", "")
            clean_desc = " ".join(desc.split())[:180]
            
            v_stats = v.get("statistics", {})
            views = int(v_stats.get("viewCount", 0))
            likes = int(v_stats.get("likeCount", 0))
            comments = int(v_stats.get("commentCount", 0))
            
            # Guard against brand-new/unreleased premieres with <25 views skewing ER
            denom = max(views, followers if views < 25 else views, 1)
            er = min(((likes + comments) / denom) * 100.0, 100.0)
            er_list.append(er)

            video_records.append({
                "title": title,
                "desc": desc,
                "clean_desc": clean_desc,
                "views": views,
                "likes": likes
            })

        if not video_records:
            return empty_res

        latest = video_records[0]
        most_popular = max(video_records, key=lambda x: x["views"])

        return {
            "titles": [r["title"] for r in video_records],
            "descs": [r["desc"] for r in video_records],
            "median_er": statistics.median(er_list) if er_list else 0.0,
            "latest_title": latest["title"],
            "latest_views": latest["views"],
            "latest_snippet": latest["clean_desc"],
            "popular_title": most_popular["title"],
            "popular_views": most_popular["views"],
            "popular_likes": most_popular["likes"],
            "popular_snippet": most_popular["clean_desc"]
        }
    except Exception:
        return empty_res