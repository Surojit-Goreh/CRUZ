import re
from typing import AsyncIterator, List, Tuple

# Common abbreviations that should not trigger premature sentence boundaries
HONORIFICS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.",
    "rev.", "gen.", "sen.", "rep.", "st.", "capt.", "col.", "sgt.",
}

ABBREVIATIONS = HONORIFICS | {
    "vs.", "e.g.", "i.e.", "etc.", "inc.", "ltd.", "co.", "corp.",
    "jan.", "feb.", "mar.", "apr.", "jun.", "jul.", "aug.", "sep.", "oct.", "nov.", "dec.",
    "a.m.", "p.m.", "am.", "pm.", "u.s.", "u.k.", "ai.", "no.", "approx.", "dept.",
}


class SentenceChunker:
    """
    Buffers streaming LLM tokens and yields complete sentences as soon as
    a sentence-ending character ('.', '!', '?', or newline '\\n') is encountered.
    """

    def __init__(self):
        self.buffer = ""

    def add_token(self, token: str) -> List[str]:
        """
        Appends a token to the buffer and extracts any completed sentences.
        Returns a list of complete sentences (if any).
        """
        self.buffer += token
        sentences, self.buffer = extract_completed_sentences(self.buffer)
        return sentences

    def flush(self) -> List[str]:
        """
        Flushes any remaining text in the buffer when the stream ends.
        Returns the remaining sentence if non-empty.
        """
        remaining = self.buffer.strip()
        self.buffer = ""
        if remaining:
            return [remaining]
        return []


def _is_abbreviation(word: str) -> bool:
    """Checks if a word ending with a dot is a known abbreviation or honorific."""
    clean = word.lower().strip()
    return clean in ABBREVIATIONS


def extract_completed_sentences(text: str) -> Tuple[List[str], str]:
    """
    Scans `text` for sentence terminators ('.', '!', '?', or '\\n').
    Splits out completed sentences while guarding against:
    - Decimal numbers (e.g. 3.14)
    - Common abbreviations and honorifics (e.g. Dr., Mr., etc.)
    - Consecutive punctuation marks (e.g. ..., ?!, !!)

    Returns:
        (completed_sentences: List[str], remaining_buffer: str)
    """
    sentences = []
    i = 0
    start = 0
    n = len(text)

    while i < n:
        char = text[i]

        # Case 1: Newline is always a natural sentence boundary
        if char == "\n":
            sentence = text[start:i].strip()
            if sentence:
                sentences.append(sentence)
            while i < n and text[i] in "\r\n":
                i += 1
            start = i
            continue

        # Case 2: Sentence-ending punctuation ('.', '!', '?')
        if char in ".!?":
            # Consume repeated punctuation (e.g. '...', '?!', '!!!')
            punct_end = i
            while punct_end < n and text[punct_end] in ".!?":
                punct_end += 1

            # Check if this dot is part of a decimal number (e.g. 3.14)
            if char == "." and (punct_end - i) == 1:
                has_prev_digit = i > 0 and text[i - 1].isdigit()
                has_next_digit = punct_end < n and text[punct_end].isdigit()
                if has_prev_digit and has_next_digit:
                    i = punct_end
                    continue

            # Check candidate sentence so far
            candidate_sentence = text[start:punct_end].strip()
            words = candidate_sentence.split()
            last_word = words[-1] if words else ""
            clean_last_word = last_word.rstrip(".!?").lower()

            # Check if it's an abbreviation or honorific (e.g. Dr., Mr., vs., etc.)
            if char == "." and (punct_end - i) == 1 and _is_abbreviation(last_word):
                i = punct_end
                continue

            # Check if it's a list marker (e.g. '1.', '2.', 'a.', 'b.', 'i.', 'ii.')
            # List markers should not be split as isolated sentences
            if char == "." and (punct_end - i) == 1:
                if clean_last_word.isdigit() or clean_last_word in ("a", "b", "c", "d", "e", "f", "i", "ii", "iii", "iv", "v"):
                    # If this is the start of the current sentence segment, don't split here
                    if len(words) <= 1:
                        i = punct_end
                        continue

            # Determine if this sentence boundary is complete:
            # - Followed by whitespace, closing quote, parenthesis, or end of buffer with terminator
            is_at_end = punct_end >= n
            followed_by_space = punct_end < n and text[punct_end] in " \t\r\n\"')]}"

            if is_at_end:
                # If punctuation is at the end of the current buffer and not an abbreviation/number marker,
                # trigger as a completed sentence.
                if len(candidate_sentence) > 0 and not _is_abbreviation(last_word):
                    if not (clean_last_word.isdigit() and len(words) <= 1):
                        sentences.append(candidate_sentence)
                        start = punct_end
                        i = punct_end
                        break
                break

            if followed_by_space:
                end_pos = punct_end
                while end_pos < n and text[end_pos] in "\"')]}":
                    end_pos += 1

                sentence = text[start:end_pos].strip()
                if sentence:
                    sentences.append(sentence)

                while end_pos < n and text[end_pos] in " \t\r\n":
                    end_pos += 1

                start = end_pos
                i = end_pos
                continue

            i = punct_end
            continue

        i += 1

    remaining = text[start:]
    return sentences, remaining




async def stream_sentences(token_stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """
    Consumes an async generator of text tokens, buffers them into sentences,
    and yields each complete sentence as soon as it is formed.
    Flushes remaining text when the token stream finishes.
    """
    chunker = SentenceChunker()
    async for token in token_stream:
        if not token:
            continue
        sentences = chunker.add_token(token)
        for sentence in sentences:
            if sentence:
                yield sentence

    for sentence in chunker.flush():
        if sentence:
            yield sentence
