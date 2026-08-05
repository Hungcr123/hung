import os
import re
import shutil

# ============= CONFIG =============
DICT_PATH = r"H:\QMHome\Lap trinh tam\QmDict.txt"
MAX_WORDS_PER_FILE = 10
EXCEPT_FOLDER = "Except"
# ==================================

# --- Hàm hỗ trợ ---
def to_upper(s: str) -> str:
    return s.upper()

def capitalize_first(word: str) -> str:
    if not word:
        return word
    return word[0].upper() + word[1:].lower()

def load_dictionary(path: str):
    dictionary = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("!")
            if len(parts) >= 1:
                key = to_upper(capitalize_first(parts[0]))
                dictionary[key] = line
    return dictionary

def normalize_text(text: str):
    text = re.sub(r"[^a-zA-Z]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_valid_word(word, dictionary, number_mode):
    valid_lines = []

    def add_if_valid_key(raw):
        key = to_upper(capitalize_first(raw))
        if key in dictionary:
            line = dictionary[key].replace("!", "\t")
            if line not in valid_lines:
                valid_lines.append(line)
            return True
        return False

    def try_root_only(root):
        return add_if_valid_key(root)

    def try_root_plus_e(root):
        return add_if_valid_key(root) or add_if_valid_key(root + "e")

    def try_double_consonant_fix(root):
        if len(root) >= 2 and root[-1] == root[-2]:
            return try_root_plus_e(root[:-1])
        return False

    w_low = word.lower()
    length = len(w_low)

    if length <= 3:
        try_root_only(w_low)
        return valid_lines

    found_self = try_root_plus_e(w_low)

    if w_low.endswith("ied") and length > 3:
        try_root_plus_e(w_low[:-3] + "y")
    if w_low.endswith("ies") and length > 3:
        try_root_plus_e(w_low[:-3] + "y")
    if w_low.endswith("ying") and length > 4:
        try_root_plus_e(w_low[:-4] + "ie")

    if w_low.endswith("ing") and length > 3:
        root = w_low[:-3]
        try_double_consonant_fix(root)
        try_root_plus_e(root)

    if w_low.endswith("ed") and length > 2:
        root = w_low[:-2]
        try_double_consonant_fix(root)
        try_root_plus_e(root)

    if found_self and not (w_low.endswith("ing") or w_low.endswith("ed")):
        for suf in ("ies", "ied", "es", "s", "er", "est", "ly"):
            if w_low.endswith(suf) and length > len(suf):
                base = w_low[:-len(suf)]
                if suf in ("ies", "ied"):
                    try_root_plus_e(base + "y")
                else:
                    try_root_plus_e(base)
                    try_double_consonant_fix(base)

    if not found_self:
        for suf in ("ing", "ed", "er", "est", "es", "s", "ly"):
            if w_low.endswith(suf) and length > len(suf):
                base = w_low[:-len(suf)]
                if try_root_plus_e(base):
                    return valid_lines
                if try_double_consonant_fix(base):
                    return valid_lines

    return valid_lines


def process_txt_file(file_path, dictionary, seen_words, number_mode, page_num, word_sources):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    text = normalize_text(text)
    words = text.split()
    unit_lines = []

    for w in words:
        valid = is_valid_word(w, dictionary, number_mode)
        for line in valid:
            word = line.split("\t")[0]
            if word not in seen_words:
                # 🟢 Chỉ khi từ chưa từng xuất hiện thì mới lưu page nguồn
                seen_words.add(word)
                unit_lines.append(line)
                word_sources[word] = {page_num}   # ghi lại trang đầu tiên
            # ❌ Không thêm page_num nữa nếu từ đã tồn tại rồi

    return unit_lines



def save_unit_output(unit_name, lines, word_sources, output_root, file_index_start):
    unit_dir = os.path.join(output_root, unit_name)
    os.makedirs(unit_dir, exist_ok=True)

    file_count = 0
    word_count = 0
    count = 0
    file_index = file_index_start
    buffer = []
    pages_in_file = set()

    total_files_estimate = (len(lines) + MAX_WORDS_PER_FILE - 1) // MAX_WORDS_PER_FILE
    width = len(str(total_files_estimate + file_index_start - 1))  # để giữ padding cho đủ chữ số

    for line in lines:
        buffer.append(line)
        word_count += 1
        count += 1

        word = line.split("\t")[0]
        if word in word_sources:
            pages_in_file.update(word_sources[word])

        if count == MAX_WORDS_PER_FILE:
            pages_str = ",".join(str(p) for p in sorted(pages_in_file))
            file_name = f"File {str(file_index).zfill(width)} - {{{pages_str}}}.QMV"
            file_path = os.path.join(unit_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(buffer))
            file_index += 1
            file_count += 1
            buffer = []
            count = 0
            pages_in_file = set()

    if buffer:
        pages_str = ",".join(str(p) for p in sorted(pages_in_file))
        file_name = f"File {str(file_index).zfill(width)} - {{{pages_str}}}.QMV"
        file_path = os.path.join(unit_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(buffer))
        file_index += 1
        file_count += 1

    return file_count, word_count, file_index



def load_except_words(base_dir):
    except_dir = os.path.join(base_dir, EXCEPT_FOLDER)
    seen_words = set()

    if not os.path.exists(except_dir):
        os.makedirs(except_dir)
        return seen_words

    for file in os.listdir(except_dir):
        if file.lower().endswith(".txt"):
            path = os.path.join(except_dir, file)
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip().split("\t")[0]
                    if word:
                        seen_words.add(word)
    return seen_words


# --- MAIN ---
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_name = os.path.basename(base_dir)

    # Xóa output cũ
    pattern = re.compile(rf"^{re.escape(parent_name)}\b")
    for folder in os.listdir(base_dir):
        full_path = os.path.join(base_dir, folder)
        if os.path.isdir(full_path) and pattern.match(folder):
            shutil.rmtree(full_path)

    seen_words = load_except_words(base_dir)
    dictionary = load_dictionary(DICT_PATH)

    temp_output_root = os.path.join(base_dir, parent_name)
    os.makedirs(temp_output_root, exist_ok=True)

    total_files = 0
    total_words = 0
    unit_info = []
    all_words = []
    global_file_index = 1   # 🔑 bộ đếm file toàn cục

    for folder in sorted(os.listdir(base_dir)):
        full_path = os.path.join(base_dir, folder)
        if not os.path.isdir(full_path) or folder.lower() == EXCEPT_FOLDER.lower():
            continue

        txt_files = [f for f in os.listdir(full_path) if re.fullmatch(r"\d+\.txt", f)]
        if not txt_files:
            continue

        txt_files.sort(key=lambda x: int(os.path.splitext(x)[0]))

        unit_lines = []
        word_sources = {}

        for txt_file in txt_files:
            page_num = int(os.path.splitext(txt_file)[0])
            file_path = os.path.join(full_path, txt_file)
            unit_lines.extend(
                process_txt_file(file_path, dictionary, seen_words, number_mode="1",
                                 page_num=page_num, word_sources=word_sources)
            )

        file_count, word_count, global_file_index = save_unit_output(
            folder, unit_lines, word_sources, temp_output_root, global_file_index
        )
        total_files += file_count
        total_words += word_count
        unit_info.append((folder, file_count, word_count))
        all_words.extend(unit_lines)


    # Đổi tên thư mục cha
    final_output_root = os.path.join(base_dir, f"{parent_name} - [{total_files} Files] - {{{total_words} words}}")
    os.rename(temp_output_root, final_output_root)

    # Đổi tên các Unit con
    for folder, file_count, word_count in unit_info:
        old_path = os.path.join(final_output_root, folder)
        new_path = os.path.join(final_output_root, f"{folder} - [{file_count} Files] - {{{word_count} words}}")
        os.rename(old_path, new_path)

    # Ghi file tổng hợp
    final_txt_path = os.path.join(base_dir, f"{parent_name}.txt")
    with open(final_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_words))


if __name__ == "__main__":
    main()
