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
        if overlap_start > self.row_start:
            left_rects.append(Rect(self.col_start, self.col_end, self.row_start, overlap_start))
        if overlap_end < self.row_end:
            left_rects.append(Rect(self.col_start, self.col_end, overlap_end, self.row_end))

        right_rects = []
        if overlap_start > run_start:
            right_rects.append(Rect(run_col, run_col+1, run_start, overlap_start))
        if overlap_end < run_end:
            right_rects.append(Rect(run_col, run_col+1, overlap_end, run_end))

        return [True, overlap_rect, left_rects, right_rects]


# runs are [inclusive, exclusive)
def find_runs(row):
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

def try_merge_with_prev_col(mergeable_rects, run_start, run_end, run_col):
    candidate_merges = []
    for i, rect in enumerate(mergeable_rects):
        merge_result = rect.test_merge_vertical(run_start, run_end, run_col)
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
        runs = find_runs(row)

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
    return r"\|".join(rect.to_vim_pattern() for rect in completed_rects)

def to_vertical_merge_rect_representation(binary_pixels):
    completed_rects = []
    mergeable_rects = []
    # this is such a dumb trick (rotate rows / cols)
    binary_pixels = zip(*binary_pixels)

    for col_idx, col in enumerate(binary_pixels):
        next_mergeable_rects = []
        runs = find_runs(col)

        for (run_start, run_end) in runs:
            best_merge_idx, best_merge_result = try_merge_with_prev_col(mergeable_rects, run_start, run_end, col_idx)
            if best_merge_idx is None:
                r = Rect(col_idx, col_idx+1, run_start, run_end)
                next_mergeable_rects.append(r)
            else:
                mergeable_rects.pop(best_merge_idx)
                overlap_rect, left_rects, right_rects = best_merge_result
                mergeable_rects.extend(left_rects)
                next_mergeable_rects.append(overlap_rect)
                next_mergeable_rects.extend(right_rects)

        completed_rects.extend(mergeable_rects)
        mergeable_rects = next_mergeable_rects

    completed_rects.extend(mergeable_rects)
    return r"\|".join(rect.to_vim_pattern() for rect in completed_rects)

def to_single_line_rle_representation(binary_pixels):
    rects = []
    for row_idx, row in enumerate(binary_pixels):
        runs = find_runs(row)
        for (run_start, run_end) in runs:
            rects.append(Rect(run_start, run_end, row_idx, row_idx+1))
    return r"\|".join(rect.to_vim_pattern() for rect in rects)

def main():
    horizontal_winners = 0
    vertical_winners = 0
    rle_winners = 0
    with open("frames-list.txt") as frames:
        with open("search-queries-combined.txt", "w") as search_queries:
            for i, frame in enumerate(frames):
                if i % 100 == 0: print(i)

                frame = frame.strip()
                binary_pixels = process_image(f"frames/{frame}")
                horizontal_query = to_horizontal_merge_rect_representation(binary_pixels)
                vertical_query = to_vertical_merge_rect_representation(binary_pixels)
                rle_query = to_single_line_rle_representation(binary_pixels)

                lengths = [len(horizontal_query), len(vertical_query), len(rle_query)]
                lengths = [l for l in lengths if l != 0]
                min_length = 0
                if lengths: min_length = min(lengths)

                # avoid double write for equal queries
                written = False
                if len(horizontal_query) == min_length and horizontal_query:
                    horizontal_winners += 1
                    if not written:
                        written = True
                        search_queries.write(horizontal_query + "\n")
                if len(vertical_query) == min_length and vertical_query:
                    vertical_winners += 1
                    if not written:
                        written = True
                        search_queries.write(vertical_query + "\n")
                if len(rle_query) == min_length and rle_query:
                    rle_winners +=1 
                    if not written:
                        written = True
                        search_queries.write(rle_query + "\n")

    print(f"horizontal winners: {horizontal_winners}")
    print(f"vertical winners: {vertical_winners}")
    print(f"rle winners: {rle_winners}")

if __name__ == "__main__":
    main()
























