
from typing import Any, Dict

class ChaptersFormatter: 
    """Formating Utility for Table of Contents"""

    @staticmethod
    def format_chapters_output(
        video_URL: str, 
        video_cu_result: Dict[str, Any], 
        dynamic: bool = False
    ) -> str:
        """Formats the chapters output for the video."""
        
        toc_html = "<div style='width:100%;'>"
        toc_html += "<b>Table of Contents</b><br><ul style='list-style-type:none;padding-left:0;'>"
        if dynamic:
            # Try to use chapters/scenes if present, else fallback to Segments
            chapters = video_cu_result.get("chapters")
            scenes = video_cu_result.get("scenes")
            if chapters and scenes:
                scene_lookup = {scene.get("scene_id"): scene for scene in scenes}
                for chapter in chapters:
                    title = chapter.get("title", "Unknown Chapter")
                    toc_html += f"<li style='margin-top:10px;'><b>{title}</b><ul>"
                    for scene_id in chapter.get("scene_ids", []):
                        scene = scene_lookup.get(scene_id, {})
                        desc = scene.get("description", "No description")
                        start = scene.get("start_timestamp", "N/A")
                        h, m, s = [float(x) if '.' in x else int(x) for x in start.split(':')]
                        seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        toc_html += (
                            f"<li style='margin-bottom:4px;'>"
                            f"<button type='button' class='seek-btn' data-seconds='{seconds}' "
                            f"style='background:none;border:none;color:#007acc;cursor:pointer;text-align:left;padding:0;'>"
                            f"{desc} <span style=\"color:#888;\">({start})</span></button></li>"
                        )
                    toc_html += "</ul></li>"
            else:
                # Fallback to Segments structure
                segments = (
                    video_cu_result
                    .get("result", {})
                    .get("contents", [])[0]
                    .get("fields", {})
                    .get("Segments", {})
                    .get("valueArray", [])
                )
                for idx, segment in enumerate(segments):
                    seg_obj = segment.get("valueObject", {})
                    seg_type = seg_obj.get("SegmentType", {}).get("valueString", "Unknown")
                    toc_html += f"<li style='margin-top:10px;'><b>{seg_type}</b><ul>"
                    scenes = seg_obj.get("Scenes", {}).get("valueArray", [])
                    for sidx, scene in enumerate(scenes):
                        scene_obj = scene.get("valueObject", {})
                        desc = scene_obj.get("Description", {}).get("valueString", "No description")
                        start = scene_obj.get("StartTimestamp", {}).get("valueString", "N/A")
                        h, m, s = [float(x) if '.' in x else int(x) for x in start.split(':')]
                        seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        toc_html += (
                            f"<li style='margin-bottom:4px;'>"
                            f"<button type='button' class='seek-btn' data-seconds='{seconds}' "
                            f"style='background:none;border:none;color:#007acc;cursor:pointer;text-align:left;padding:0;'>"
                            f"{desc} <span style=\"color:#888;\">({start})</span></button></li>"
                        )
                    toc_html += "</ul></li>"
        else:
            segments = (
                video_cu_result
                .get("result", {})
                .get("contents", [])[0]
                .get("fields", {})
                .get("Segments", {})
                .get("valueArray", [])
            )
            for idx, segment in enumerate(segments):
                seg_obj = segment.get("valueObject", {})
                seg_type = seg_obj.get("SegmentType", {}).get("valueString", "Unknown")
                toc_html += f"<li style='margin-top:10px;'><b>{seg_type}</b><ul>"
                scenes = seg_obj.get("Scenes", {}).get("valueArray", [])
                for sidx, scene in enumerate(scenes):
                    scene_obj = scene.get("valueObject", {})
                    desc = scene_obj.get("Description", {}).get("valueString", "No description")
                    start = scene_obj.get("StartTimestamp", {}).get("valueString", "N/A")
                    h, m, s = [float(x) if '.' in x else int(x) for x in start.split(':')]
                    seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    toc_html += (
                        f"<li style='margin-bottom:4px;'>"
                        f"<button type='button' class='seek-btn' data-seconds='{seconds}' "
                        f"style='background:none;border:none;color:#007acc;cursor:pointer;text-align:left;padding:0;'>"
                        f"{desc} <span style=\"color:#888;\">({start})</span></button></li>"
                    )
                toc_html += "</ul></li>"
        toc_html += "</ul></div>"

        full_html = f"""
        <div style="display:flex;gap:5px;">
        <div style="flex:2;min-width:0;">{toc_html}</div>
        <div style="flex:1;min-width:0;display:flex;align-items:center;margin-left:-100px;">
            <video id="analyzed_video" style="width:100%;max-width:100%;height:auto;aspect-ratio:9/16;" controls>
            <source src="{video_URL}" type="video/mp4">
            Your browser does not support this video format.
            </video>
        </div>
        </div>
        <script>
        (function() {{
        document.querySelectorAll('.seek-btn').forEach(function(btn) {{
            btn.addEventListener('click', function() {{
            var v = document.getElementById('analyzed_video');
            v.currentTime = parseFloat(this.getAttribute('data-seconds'));
            v.scrollIntoView({{behavior:'smooth',block:'center'}});
            }});
        }});
        }})();
        </script>
        """

        return full_html


