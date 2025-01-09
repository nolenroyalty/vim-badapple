from PIL import Image
import numpy as np

def process_image(path, target_width=120, target_height=90):
    img = Image.open(path)
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    if img.mode != "L": img = img.convert("L")

    pixels = np.array(img)
    binary_pixels = (pixels < 10).astype(int) # 1 for dark, 0 for light
    return binary_pixels

def text_preview(binary_pixels):
    chars = {0: ".", 1: "#"}

    return "\n".join("".join(chars[px] for px in row) for row in binary_pixels)

class Rect:
    def __init__(self, col_start, col_end, row_start, row_end):
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

    def to_vim_pattern(self):
        # vim is 1-indexed and exclusive in both directions
        row_start = self.row_start
        row_end = self.row_end + 1
        col_start = self.col_start
        col_end = self.col_end + 1
        #return fr"\%>{row_start}l\%<{row_end}l\%>{col_start}c\%<{col_end}c"
        return fr"\%>{col_start}c\%<{col_end}c\%>{row_start}l\%<{row_end}l"

    def __repr__(self):
        width = self.width()
        height = self.height()
        return f"R: ({width}x{height}) {self.row_start}:{self.row_end}, {self.col_start}:{self.col_end}"

    def test_merge_horizontal(self, run_start, run_end, run_row):
        if run_end <= self.col_start: return [False, None, None, None]
        if run_start >= self.col_end: return [False, None, None, None]

        overlap_start = max(run_start, self.col_start)
        overlap_end = min(run_end, self.col_end)
        overlap_rect = Rect(overlap_start, overlap_end, self.row_start, run_row+1)

        # rects that are no longer eligible for merging
        top_rects = []
        if overlap_start > self.col_start:
            top_rects.append(Rect(self.col_start, overlap_start, self.row_start, self.row_end))
        if overlap_end < self.col_end:
            top_rects.append(Rect(overlap_end, self.col_end, self.row_start, self.row_end))

        # rects that are split from the current run but eligible for merging
        # with stuff below
        bot_rects = []
        if overlap_start > run_start:
            bot_rects.append(Rect(run_start, overlap_start, run_row, run_row+1))
        if overlap_end < run_end:
            bot_rects.append(Rect(overlap_end, run_end, run_row, run_row+1))

        return [True, overlap_rect, top_rects, bot_rects]

    def test_merge_vertical(self, run_start, run_end, run_col):
        if run_end <= self.row_start: return [False, None, None, None]
        if run_start >= self.row_end: return [False, None, None, None]

        overlap_start = max(run_start, self.row_start)
        overlap_end = min(run_end, self.row_end)
        overlap_rect = Rect(self.col_start, run_col+1, overlap_start, overlap_end)

        left_rects = []
        #if overlap_start > 

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

def try_merge_with_prev_row(mergeable_rects, run_start, run_end, run_row):
    candidate_merges = []
    for i, rect in enumerate(mergeable_rects):
        merge_result = rect.test_merge_horizontal(run_start, run_end, run_row)
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
    elif best > run_length: return (best_idx, best_merge_result)
    else: return (None, None)

def to_horizontal_merge_rect_representation(binary_pixels):
    completed_rects = []
    mergeable_rects = []

    for row_idx, row in enumerate(binary_pixels):
        next_mergeable_rects = []
        runs = find_runs_for_this_row(row)

        for (run_start, run_end) in runs:
            best_merge_idx, best_merge_result = try_merge_with_prev_row(mergeable_rects, run_start, run_end, row_idx)
            if best_merge_idx is None:
                r = Rect(run_start, run_end, row_idx, row_idx+1)
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
    with open("frames-list.txt") as frames:
        with open("search-queries-2.txt", "w") as search_queries:
            for i, frame in enumerate(frames):
                if i % 100 == 0: print(i)

                frame = frame.strip()
                binary_pixels = process_image(f"frames/{frame}")
                rects = to_horizontal_merge_rect_representation(binary_pixels)
                query = r"\|".join(rect.to_vim_pattern() for rect in rects)

                if query: search_queries.write(query + "\n")

if __name__ == "__main__":
    main()
























