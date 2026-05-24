from __future__ import annotations

import re
from typing import List


CHUNK_RULES = { #字典，文件后缀 -> 切分参数
    ".md": (500, 80),
    ".txt": (500, 80),
    ".pdf": (700, 120),
    ".docx": (600, 100),
    ".xlsx": (400, 50),
    ".xls": (400, 50),
    ".csv": (400, 50),
}


def get_chunk_params(file_ext: str | None = None) -> tuple[int, int]: #输入文件后缀，返回对应的 chunk 参数
    return CHUNK_RULES.get((file_ext or "").lower(), (600, 100))
    #(file_ext or "").lower()：第一，如果 file_ext 是 None 或空字符串，就用 "" 代替。第二，把文件后缀转成小写。
    #CHUNK_RULES.get(..., (600, 100)) 是什么意思？   字典.get(key, 默认值) 如果字典里有这个 key，就返回对应值；如果没有，就返回默认值。


def normalize_text(text: str) -> str:
    if not text:
        return ""
    #把文本里的换行符统一，把连续空格压缩成一个，把过多空行压缩成段落间隔，最后去掉首尾空白，让文本更干净。
    text = text.replace("\r\n", "\n").replace("\r", "\n") #把不同系统里的换行符统一成 \n
    text = re.sub(r"[ \t]+", " ", text) #把连续的空格和 Tab，替换成一个普通空格。 r"[ \t]+" 一个或多个空格/tab 统一变成一个空格
    text = re.sub(r"\n{3,}", "\n\n", text) #压缩过多空行，如果连续出现 3 个或更多换行，就压缩成 2 个换行。
    return text.strip()


def split_by_paragraph(text: str) -> List[str]: #按照段落切分文本。
    paragraphs = re.split(r"\n\s*\n", text) #空行切段落
    return [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]#第一，去掉每个段落首尾空格。第二，过滤掉空段落。


def split_long_text_by_sentence(text: str, max_size: int) -> List[str]:
    #把一段过长的文本，尽量按照句子切成多个不超过 max_size 的 chunk。
    if len(text) <= max_size:
        return [text]

    sentences = re.split(r"(?<=[。！？!?；;])", text) #按句子结束符切分文本。
    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current) + len(sentence) <= max_size:
            current += sentence
        else:
            if current:
                chunks.append(current.strip())
            current = sentence

    if current:
        chunks.append(current.strip())

    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_size:
            final_chunks.append(chunk)
        else:
            final_chunks.extend(hard_split(chunk, max_size=max_size, overlap=0))

    return final_chunks


def hard_split(text: str, max_size: int, overlap: int) -> List[str]:
    #把一段长文本按固定长度强制切成多个 chunk，并且相邻 chunk 之间可以有一部分重叠内容
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + max_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = max(end - overlap, 0)

    return chunks


def add_overlap(chunks: List[str], overlap: int) -> List[str]:
    #给已经切好的 chunk 再补上 overlap 上下文。
    #不是在切分的时候制造重叠，而是切完以后，把上一个 chunk 的末尾一小段，拼到当前 chunk 的开头。
    if not chunks or overlap <= 0:
        return chunks

    results = [] #这个 results 用来存放加了 overlap 之后的新 chunk。
    for index, chunk in enumerate(chunks): #遍历每个 chunk ，拿到当前chunk编号，当前chunk内容
        if index == 0:
            results.append(chunk)
            continue

        previous = chunks[index - 1] #找到上一个 chunk
        prefix = previous[-overlap:] #取上一个 chunk 的最后 overlap 个字符
        results.append(f"{prefix}\n{chunk}".strip()) #把 prefix 拼到当前 chunk 前面,
        # 新的chunk = 上一个chunk的尾部 + 换行 + 当前chunk,再去掉首尾多余空格和换行

    return results


def split_text( #
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
    file_ext: str | None = None, #文件扩展名，文件类型
) -> List[str]:
    default_chunk_size, default_overlap = get_chunk_params(file_ext)#根据文件类型决定默认 chunk_size 和 overlap. 最后输出一个字符串列表
    chunk_size = chunk_size or default_chunk_size
    overlap = default_overlap if overlap is None else overlap

    text = normalize_text(text) #清洗文本
    if not text:
        return []

    paragraphs = split_by_paragraph(text) #按照段落切分
    small_units = []

    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size: #段落不超过 chunk_size，直接加入small_units
            small_units.append(paragraph)
        else: #超过chunk_size。把长段落按句子继续切。
            small_units.extend(split_long_text_by_sentence(paragraph, max_size=chunk_size))

    #开始组装chunk
    chunks = [] #最终切好的 chunk 列表
    current = "" #当前正在拼接的 chunk

    for unit in small_units:
        unit = unit.strip() #这里先去掉每个小单元首尾空白。
        if not unit: #如果清理后是空字符串，就跳过。
            continue

        if not current: #如果 current 为空，就初始化 current
            current = unit
            continue

        if len(current) + len(unit) + 2 <= chunk_size: #判断当前 chunk 能不能继续拼接 unit。 + 2？：因为拼接时用了：\n\n两个换行符
            current = f"{current}\n\n{unit}" #如果没超过 chunk_size，就合并
        else:
            chunks.append(current.strip()) #如果超过 chunk_size，就保存当前 chunk。
            current = unit #然后用新的 unit 开始一个新的 chunk：

    #把最后一个 current 放进 chunks
    if current:
        chunks.append(current.strip())

    return add_overlap(chunks, overlap=overlap) #给 chunk 添加 overlap
