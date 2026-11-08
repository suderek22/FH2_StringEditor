"""FH2 LSB2 (0x200) tables. Ancillary sections are preserved like FH2 Mod Platform."""
import struct


class StrTable:
    def __init__(self):
        self.strings = {}
        self.sections = [b"", b"", b"", b""]
        self.header = struct.pack("<4s4I4I", b"LSB2", 0, 0x200, 36, 4, 0, 0, 0, 0)
        self.original = None
        self.original_strings = {}

    @classmethod
    def read(cls, data):
        if len(data) < 20 or data[:4] != b"LSB2":
            raise ValueError("Not an FH2 LSB2 string table.")
        _, version, header_size, count = struct.unpack_from("<4I", data, 4)
        if version != 0x200:
            raise ValueError(f"Unsupported LSB2 version 0x{version:X}; expected FH2 0x200.")
        if count != 4 or header_size < 36 or header_size > len(data):
            raise ValueError("Invalid FH2 section directory.")
        offsets = struct.unpack_from("<4I", data, 20)
        result = cls()
        result.header = data[:header_size]
        spans = []
        for i, offset in enumerate(offsets):
            if not offset:
                continue
            if offset < header_size or offset + 8 > len(data):
                raise ValueError("Section offset is outside the file.")
            size = struct.unpack_from("<I", data, offset)[0]
            if size < 8 or offset + size > len(data):
                raise ValueError("Invalid section length.")
            spans.append((offset, offset + size))
            result.sections[i] = data[offset:offset + size]
        spans.sort()
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise ValueError("Overlapping sections.")
        section = result.sections[0]
        if not section:
            raise ValueError("Missing text section.")
        n = struct.unpack_from("<I", section, 4)[0]
        base = 8 + 6 * (n + 1)
        if n > 65536 or base > len(section):
            raise ValueError("Invalid text entry count.")
        sentinel, units = struct.unpack_from("<HI", section, 8 + 6 * n)
        end_of_text = base + units * 2
        if (sentinel != 0xFFFF or end_of_text > len(section)
                or section[end_of_text:] not in (b"", b"\0\0")):
            raise ValueError("Invalid text sentinel or string-data length.")
        for i in range(n):
            key, offset = struct.unpack_from("<HI", section, 8 + 6 * i)
            if key in result.strings or offset >= units:
                raise ValueError("Duplicate key or invalid text offset.")
            start = base + offset * 2
            end = start
            while end + 2 <= end_of_text and section[end:end + 2] != b"\0\0":
                end += 2
            if end + 2 > end_of_text:
                raise ValueError("Unterminated UTF-16 string.")
            result.strings[key] = section[start:end].decode("utf-16le")
        result.original = data
        result.original_strings = result.strings.copy()
        return result

    def write(self):
        if self.original is not None and self.strings == self.original_strings:
            return self.original
        entries = bytearray()
        text = bytearray()
        for key, value in sorted(self.strings.items()):
            if not isinstance(key, int) or not 0 <= key <= 0xFFFF:
                raise ValueError("IDs must be between 0 and 65535 (0xFFFF).")
            if "\0" in value:
                raise ValueError("Text cannot contain NUL characters.")
            entries.extend(struct.pack("<HI", key, len(text) // 2))
            text.extend(value.encode("utf-16le") + b"\0\0")
        entries.extend(struct.pack("<HI", 0xFFFF, len(text) // 2))
        text.extend(b"\0\0")
        section = struct.pack("<II", 8 + len(entries) + len(text), len(self.strings))
        sections = [section + entries + text, *self.sections[1:]]
        output = bytearray(self.header)
        for i, block in enumerate(sections):
            struct.pack_into("<I", output, 20 + 4 * i, len(output) if block else 0)
            output.extend(block)
        return bytes(output)
