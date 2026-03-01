import glob
import os

import cv2
import numpy as np


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
INPUT_GLOB = os.path.join(PROJECT_ROOT, "avatars", "*", "avatar_image.png")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "avatars_cropped_test")

CROP_WIDTH = 96
CROP_HEIGHT = 96


def crop_with_character_center(image_path: str) -> np.ndarray | None:
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None

    h, w, c = img.shape
    if c < 4:
        return None

    alpha = img[:, :, 3]
    _, binary = cv2.threshold(alpha, 254, 1, cv2.THRESH_BINARY)
    if np.max(binary) == 0:
        return None

    win_w, win_h = 50, 70
    head_h = 30
    body_w = 20

    kernel = np.zeros((win_h, win_w), dtype=np.float32)
    kernel[0:head_h, :] = 1.0
    body_start_x = (win_w - body_w) // 2
    kernel[head_h:win_h, body_start_x : body_start_x + body_w] = 2.5

    density_map = cv2.filter2D(binary.astype(float), -1, kernel)

    y_indices, x_indices = np.indices((h, w))
    center_y_img, center_x_img = h / 2, w / 2
    dist_from_center = np.sqrt(
        (x_indices - center_x_img) ** 2 + (y_indices - center_y_img) ** 2
    )
    max_dist = np.sqrt(center_x_img**2 + center_y_img**2)
    center_weight = 1.0 - 0.3 * (dist_from_center / max_dist)
    bottom_weight = 1.0 + 0.15 * (y_indices / h)

    weight_map = center_weight * bottom_weight
    weighted_density = density_map * weight_map

    max_val = np.max(weighted_density)
    best_y, best_x = np.where(weighted_density >= max_val * 0.999)
    if len(best_x) == 0:
        return None

    rough_x = int(np.mean(best_x))
    spine_half_width = body_w // 2
    col_start = max(0, rough_x - spine_half_width)
    col_end = min(w, rough_x + spine_half_width)

    body_column = binary[:, col_start:col_end]
    y_coords_in_spine, x_coords_in_spine = np.where(body_column == 1)

    if len(y_coords_in_spine) > 0:
        center_x = col_start + int(np.median(x_coords_in_spine))

        y_proj = np.sum(body_column, axis=1)
        rough_y = int(np.mean(best_y))

        foot_y = rough_y
        while foot_y < h and y_proj[foot_y] > 0:
            foot_y += 1

        true_foot_y = foot_y - 1
        center_y = true_foot_y - (win_h // 2)
    else:
        center_x = rough_x
        center_y = int(np.mean(best_y))

    start_x = center_x - CROP_WIDTH // 2
    end_x = start_x + CROP_WIDTH
    start_y = center_y - CROP_HEIGHT // 2
    end_y = start_y + CROP_HEIGHT

    src_start_x = max(0, start_x)
    src_start_y = max(0, start_y)
    src_end_x = min(w, end_x)
    src_end_y = min(h, end_y)

    dst_start_x = max(0, -start_x)
    dst_start_y = max(0, -start_y)
    dst_end_x = dst_start_x + (src_end_x - src_start_x)
    dst_end_y = dst_start_y + (src_end_y - src_start_y)

    cropped_img = np.zeros((CROP_HEIGHT, CROP_WIDTH, 4), dtype=np.uint8)
    if src_end_x > src_start_x and src_end_y > src_start_y:
        cropped_img[dst_start_y:dst_end_y, dst_start_x:dst_end_x] = img[
            src_start_y:src_end_y, src_start_x:src_end_x
        ]

    return cropped_img


def process_avatar_images() -> tuple[int, int]:
    image_files = sorted(glob.glob(INPUT_GLOB))
    if not image_files:
        print("no avatar files found")
        return 0, 0

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    processed = 0
    failed = 0

    for src in image_files:
        cropped = crop_with_character_center(src)
        if cropped is None:
            failed += 1
            continue

        char_id = os.path.basename(os.path.dirname(src))
        dst_dir = os.path.join(OUTPUT_ROOT, char_id)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "avatar_image.png")
        cv2.imwrite(dst, cropped)
        processed += 1

    return processed, failed


if __name__ == "__main__":
    ok, fail = process_avatar_images()
    print(f"processed={ok}, failed={fail}, output='{OUTPUT_ROOT}'")
