from PIL import Image
import numpy as np

def process_image(path, target_width=120, target_height=90):
    img = Image.open(path)
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    if img.mode != "L": img = img.convert("L")

    pixels = np.array(img)
    binary_pixels = (pixels < 128).astype(int) # 1 for dark, 0 for light
    return binary_pixels

def text_preview(binary_pixels):
    chars = {0: ".", 1: "#"}

    return "\n".join("".join(chars[px] for px in row) for row in binary_pixels)

class Rect:
    def __init__(self, row_start, row_end, col_start, col_end):
        self.row_start = row_start
        self.row_end = row_end
        self.col_start = col_start
        self.col_end = col_end

    def height(self):
        return self.row_end - self.row_start

    def width(self):
        return self.col_end - self.col_start

    def area(self):
        return self.height() * self.width()

    def incr_col(self):
        return Rect(self.row_start, self.row_end, self.col_start, self.col_end + 1)

    def __repr__(self):
        width = self.width()
        height = self.height()
        return f"R: ({width}x{height}) {self.row_start}:{self.row_end}, {self.col_start}:{self.col_end}"

    def test_merge(self, run_start, run_end, run_col):
        # run ends before we start (remember end is exclusive)
        if run_end <= self.row_start: return [False, None, None, None]
        # run starts after we end (remember end is exclusive)
        if run_start >= self.row_end: return [False, None, None, None]

        overlap_start = max(run_start, self.row_start)
        overlap_end = min(run_end, self.row_end)
        overlap_rect = Rect(overlap_start, overlap_end, self.col_start, run_col+1)

        top_rects = []
        if overlap_start > self.row_start:
            top_rects.append(Rect(self.row_start, overlap_start, self.col_start, self.col_end))
        if overlap_end < self.row_end:
            top_rects.append(Rect(overlap_end, self.row_end, self.col_start, self.col_end))

        bot_rects = []
        if overlap_start > run_start:
            bot_rects.append(Rect(run_start, overlap_start, run_col, run_col+1))
        if overlap_end < run_end:
            bot_rects.append(Rect(overlap_end, run_end, run_col, run_col+1))

        return [True, overlap_rect, top_rects, bot_rects]


# runs are [inclusive, exclusive)
def find_runs_for_this_row(row):
    runs = []
    start = None

    for i, val in enumerate(row):
        if val == 1 and start is None:
            start = i
        elif val == 0 and start is not None:
            runs.append((start, i))
            start = None

    if start is not None:
        runs.append((start, len(row)))
    return runs

def try_merge_with_prev_row(mergeable_rects, run_start, run_end, run_col):
    candidate_merges = []
    for i, rect in enumerate(mergeable_rects):
        merge_result = rect.test_merge(run_start, run_end, run_col)
        if merge_result[0]: candidate_merges.append((merge_result, i))

    best = None
    best_idx = None
    best_merge_result = None
    run_length = run_end - run_start

    for (candidate, candidate_idx) in candidate_merges:
        _, overlap_rect, top_rects, bot_rects = candidate
        overlap_area = overlap_rect.area()
        if best is None or overlap_area > best:
            best = overlap_area
            best_idx = candidate_idx
            best_merge_result = (overlap_rect, top_rects, bot_rects)

    if best is None: return (None, None)
    if best > run_length: return (best_idx, best_merge_result)

def to_rectangle_representation(binary_pixels):
    completed_rects = []
    mergeable_rects = []

    for col_idx, row in enumerate(binary_pixels):
        next_mergeable_rects = []
        runs = find_runs_for_this_row(row)

        for (run_start, run_end) in runs:
            best_merge_idx, best_merge_result = try_merge_with_prev_row(mergeable_rects, run_start, run_end, col_idx)
            if best_merge_idx is None:
                r = Rect(run_start, run_end, col_idx, col_idx + 1)
                next_mergeable_rects.append(r)
            else:
                mergeable_rects.pop(best_merge_idx)
                overlap_rect, top_rects, bot_rects = best_merge_result
                mergeable_rects.extend(top_rects)
                next_mergeable_rects.append(overlap_rect)
                next_mergeable_rects.extend(bot_rects)

        completed_rects.extend(mergeable_rects)
        mergeable_rects = next_mergeable_rects

    completed_rects.extend(mergeable_rects)
    return completed_rects


def main():
    binary_pixels = process_image("test.png")
    preview = text_preview(binary_pixels)
    print(preview)

    with open("test.pixels", "w") as f:
        f.write(preview)

if __name__ == "__main__":
    test_grid = [
            [1, 1, 1, 0, 0],  # Simple run
            [0, 1, 1, 1, 0],  # Partially overlapping run
            [0, 1, 1, 0, 0],  # Contained run
            ]
    print(to_rectangle_representation(test_grid))

