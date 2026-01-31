#!/usr/bin/env python3
"""
Script to analyze video runtimes in combined_modules_withLocalURL.json
Adds runtime_seconds field to each video and reports total runtime.
"""

import json
import subprocess
import os
from pathlib import Path


def get_video_duration(video_path: str) -> float | None:
    """
    Get video duration in seconds using ffprobe.
    Returns None if the file doesn't exist or can't be analyzed.
    """
    if not os.path.exists(video_path):
        print(f"  [MISSING] File not found: {video_path}")
        return None
    
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        else:
            print(f"  [ERROR] Could not get duration for: {video_path}")
            print(f"          stderr: {result.stderr.strip()}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Timed out analyzing: {video_path}")
        return None
    except Exception as e:
        print(f"  [ERROR] Exception for {video_path}: {e}")
        return None


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def main():
    # Paths
    script_dir = Path(__file__).parent
    json_path = script_dir.parent / "templates" / "combined_modules_withLocalURL.json"
    
    print(f"Loading JSON from: {json_path}")
    
    # Load the JSON
    with open(json_path, "r") as f:
        modules = json.load(f)
    
    total_runtime = 0.0
    total_videos = 0
    missing_videos = 0
    
    print("\n" + "=" * 80)
    print("VIDEO RUNTIME ANALYSIS")
    print("=" * 80)
    
    for module in modules:
        module_name = module.get("module_name", "Unknown Module")
        module_runtime = 0.0
        
        print(f"\n📁 Module: {module_name}")
        print("-" * 60)
        
        for video in module.get("videos", []):
            title = video.get("title", "Unknown")
            local_path = video.get("local_path", "")
            
            duration = get_video_duration(local_path)
            
            if duration is not None:
                video["runtime_seconds"] = round(duration, 2)
                video["runtime_formatted"] = format_duration(duration)
                module_runtime += duration
                total_runtime += duration
                total_videos += 1
                print(f"  ✓ {title}: {format_duration(duration)}")
            else:
                video["runtime_seconds"] = None
                video["runtime_formatted"] = "N/A"
                missing_videos += 1
                print(f"  ✗ {title}: MISSING/ERROR")
        
        print(f"  Module Total: {format_duration(module_runtime)}")
    
    # Save the updated JSON
    with open(json_path, "w") as f:
        json.dump(modules, f, indent=2)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total videos analyzed: {total_videos}")
    print(f"Missing/errored videos: {missing_videos}")
    print(f"Total runtime: {format_duration(total_runtime)}")
    print(f"Total runtime (seconds): {round(total_runtime, 2)}")
    print(f"\nUpdated JSON saved to: {json_path}")


if __name__ == "__main__":
    main()
