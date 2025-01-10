from PIL import Image
import numpy as np

# This code
# * takes in a frame of bad apple
# * shrinks it 4x (to display in vim) and turns it into an array of 1s and 0s representing black and white
# * naively converts that into rectangles, trying to make big rectangles
# * converts those rectangles into vim search queries
# 
# BEWARE I AM A HUGE DUMBASS AND I CONFUSED ROWS AND COLUMNS WHEN WRITING THIS CODE
# I AM TOO LAZY TO FIX IT BECUASE IT OTHERWISE WORKS FINE
# SO INSTEAD WE JUST SWAP ROW WITH COLUMN IN THE VIM QUERY LOL
# SORRY I MADE THIS IN ONE DAY

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

    def to_vim_pattern(self):
        # vim is 1-indexed and exclusive in both directions
        row_start = self.row_start
        row_end = self.row_end + 1
        col_start = self.col_start
        col_end = self.col_end + 1
        #return fr"\%>{row_start}l\%<{row_end}l\%>{col_start}c\%<{col_end}c"
        # I AM AN ABSOLUTE DUMBASS AND I CONFUSED ROWS AND COLUMNS WHEN WRITING THIS CODE LMAO
        return fr"\%>{row_start}c\%<{row_end}c\%>{col_start}l\%<{col_end}l"
        
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
    elif best > run_length: return (best_idx, best_merge_result)
    else: return (None, None)

def to_rectangle_representation(binary_pixels):
    completed_rects = []
    mergeable_rects = []

    for col_idx, row in enumerate(binary_pixels):
        next_mergeable_rects = []
        runs = find_runs_for_this_row(row)

        for (run_start, run_end) in runs:
            res = try_merge_with_prev_row(mergeable_rects, run_start, run_end, col_idx)
            best_merge_idx, best_merge_result = res
            #best_merge_idx, best_merge_result = try_merge_with_prev_row(mergeable_rects, run_start, run_end, col_idx)
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
    #binary_pixels = process_image("test.png")
    #rects = to_rectangle_representation(binary_pixels)
    #print(r"\|".join(rect.to_vim_pattern() for rect in rects))
    with open("frames-list.txt") as frames:
        with open("search-queries.txt", "w") as search_queries:
            for i, frame in enumerate(frames):
                frame = frame.strip()
                binary_pixels = process_image(f"frames/{frame}")
                rects = to_rectangle_representation(binary_pixels)
                query = r"\|".join(rect.to_vim_pattern() for rect in rects)
                if query:
                    search_queries.write(query + "\n")

                if i % 100 == 0:
                    print(i)
