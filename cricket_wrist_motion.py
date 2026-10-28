#!/usr/bin/env python3
"""Cricket wrist-motion prototype. Measures image-plane motion, not calibrated bat speed."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--outdir", default="results")
    parser.add_argument("--model", default="yolov8n-pose.pt")
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()

    video = Path(args.video)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    if not video.is_file():
        raise SystemExit(f"Video not found: {video}")

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {video}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        fps = 25.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    stem = video.stem
    csv_path = out / f"{stem}_tracks.csv"
    plot_path = out / f"{stem}_velocity.png"
    video_path = out / f"{stem}_annotated.mp4"
    summary_path = out / f"{stem}_summary.json"

    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"mp4v"),
        fps, (width, height)
    )
    if not writer.isOpened():
        cap.release()
        raise SystemExit("Could not create output video.")

    model = YOLO(args.model)
    rows = []
    frame_no = 0
    previous_gray = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cut_score = 0.0
        if previous_gray is not None:
            a = cv2.resize(previous_gray, (160, 90))
            b = cv2.resize(gray, (160, 90))
            cut_score = float(np.mean(cv2.absdiff(a, b)))
        is_cut = cut_score > 35

        result = model.predict(frame, conf=args.conf, verbose=False)[0]
        bbox = None
        person_conf = np.nan
        left = right = None

        if result.boxes is not None and len(result.boxes) and result.keypoints is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            keypoints = result.keypoints.data.cpu().numpy()
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            idx = int(np.argmax(areas * (0.5 + 0.5 * scores)))
            bbox = boxes[idx]
            person_conf = float(scores[idx])
            left = keypoints[idx, 9]   # left wrist: x, y, confidence
            right = keypoints[idx, 10] # right wrist

        if left is not None:
            lx, ly, lc = map(float, left)
            rx, ry, rc = map(float, right)
        else:
            lx = ly = lc = rx = ry = rc = np.nan

        if np.isfinite(lc) and np.isfinite(rc):
            if lc >= rc:
                wx, wy, wc, side = lx, ly, lc, "left"
            else:
                wx, wy, wc, side = rx, ry, rc, "right"
        elif np.isfinite(lc):
            wx, wy, wc, side = lx, ly, lc, "left"
        elif np.isfinite(rc):
            wx, wy, wc, side = rx, ry, rc, "right"
        else:
            wx = wy = wc = np.nan
            side = "none"

        rows.append({
            "frame": frame_no,
            "time_s": frame_no / fps,
            "person_confidence": person_conf,
            "left_wrist_x_px": lx, "left_wrist_y_px": ly,
            "left_wrist_confidence": lc,
            "right_wrist_x_px": rx, "right_wrist_y_px": ry,
            "right_wrist_confidence": rc,
            "selected_wrist": side,
            "wrist_x_px": wx, "wrist_y_px": wy,
            "wrist_confidence": wc,
            "cut_score": cut_score,
            "suspected_scene_cut": is_cut
        })

        annotated = frame.copy()
        if bbox is not None:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 255), 2)
            for x, y, c, label in [
                (lx, ly, lc, "L"), (rx, ry, rc, "R")
            ]:
                if np.isfinite(c) and c > 0.05:
                    cv2.circle(annotated, (int(x), int(y)), 6, (0, 255, 0), -1)
                    cv2.putText(
                        annotated, f"{label}:{c:.2f}", (int(x) + 5, int(y) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                    )
        if is_cut:
            cv2.putText(
                annotated, "POSSIBLE SCENE CUT", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
            )

        writer.write(annotated)
        previous_gray = gray
        frame_no += 1

    cap.release()
    writer.release()

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No frames processed.")

    x = df["wrist_x_px"].to_numpy(float)
    y = df["wrist_y_px"].to_numpy(float)
    confidence = df["wrist_confidence"].to_numpy(float)
    cuts = df["suspected_scene_cut"].to_numpy(bool)

    valid = np.isfinite(x) & np.isfinite(y) & (confidence >= 0.35) & ~cuts
    raw_speed = np.full(len(df), np.nan)

    for i in range(1, len(df)):
        if valid[i] and valid[i - 1] and not cuts[i - 1]:
            raw_speed[i] = np.hypot(x[i] - x[i - 1], y[i] - y[i - 1]) * fps

    finite_speeds = raw_speed[np.isfinite(raw_speed)]
    if len(finite_speeds):
        threshold = max(1200.0, float(np.percentile(finite_speeds, 95) * 2.5))
        bad = np.isfinite(raw_speed) & (raw_speed > threshold)
        valid[bad] = False
        valid[np.maximum(np.where(bad)[0] - 1, 0)] = False

    df["tracking_valid"] = valid
    df["raw_wrist_speed_px_s"] = raw_speed

    sx = pd.Series(np.where(valid, x, np.nan)).interpolate(limit=2, limit_area="inside")
    sy = pd.Series(np.where(valid, y, np.nan)).interpolate(limit=2, limit_area="inside")

    window = min(11, len(df) if len(df) % 2 else len(df) - 1)
    if window >= 5:
        xs = savgol_filter(sx.interpolate(limit_direction="both"), window, 2)
        ys = savgol_filter(sy.interpolate(limit_direction="both"), window, 2)
        smooth = np.hypot(np.gradient(xs) * fps, np.gradient(ys) * fps)
        df["smoothed_wrist_speed_px_s"] = np.where(valid, smooth, np.nan)
    else:
        df["smoothed_wrist_speed_px_s"] = raw_speed

    df.to_csv(csv_path, index=False)

    plt.figure(figsize=(12, 5))
    plt.plot(
        df["time_s"], df["smoothed_wrist_speed_px_s"],
        label="Smoothed wrist speed (px/s)"
    )
    plt.xlabel("Time (seconds)")
    plt.ylabel("Image-plane speed (pixels/second)")
    plt.title(f"{video.name}: wrist-motion proxy, not bat speed")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_path, dpi=160)
    plt.close()

    summary = {
        "video": str(video),
        "width": width,
        "height": height,
        "fps": fps,
        "frames_processed": len(df),
        "valid_frames": int(valid.sum()),
        "valid_fraction": float(valid.mean()),
        "suspected_scene_cuts": int(cuts.sum()),
        "peak_smoothed_wrist_speed_px_s": (
            float(df["smoothed_wrist_speed_px_s"].max())
            if df["smoothed_wrist_speed_px_s"].notna().any() else None
        ),
        "warning": (
            "This prototype estimates wrist image-plane motion in px/s, "
            "not calibrated bat speed in m/s. It does not compensate for "
            "camera motion and may switch player identity."
        )
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nSaved outputs:")
    for path in [csv_path, plot_path, video_path, summary_path]:
        print(path)


if __name__ == "__main__":
    main()
