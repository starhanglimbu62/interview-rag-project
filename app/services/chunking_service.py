def fixed_size_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> list[str]:
    """
    Split text into fixed-size chunks with overlapping characters.
    """

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be between 0 and chunk_size")

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def recursive_character_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> list[str]:
    """
    Split text recursively, preferring meaningful boundaries.
    """

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be between 0 and chunk_size")

    text = text.strip()

    if not text:
        return []

    separators = ["\n\n", "\n", ". ", " ", ""]

    def split_recursively(
        content: str,
        separator_index: int = 0
    ) -> list[str]:

        if len(content) <= chunk_size:
            return [content] if content.strip() else []

        if separator_index >= len(separators):
            return [
                content[i:i + chunk_size]
                for i in range(0, len(content), chunk_size)
            ]

        separator = separators[separator_index]

        if not separator:
            return [
                content[i:i + chunk_size]
                for i in range(0, len(content), chunk_size)
            ]

        parts = content.split(separator)

        if len(parts) == 1:
            return split_recursively(
                content,
                separator_index + 1
            )

        result = []

        for index, part in enumerate(parts):
            if index < len(parts) - 1:
                part += separator

            if not part:
                continue

            if len(part) > chunk_size:
                result.extend(
                    split_recursively(
                        part,
                        separator_index + 1
                    )
                )
            else:
                result.append(part)

        return result

    pieces = split_recursively(text)

    chunks = []
    current = ""

    for piece in pieces:

        candidate = current + piece

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current.strip():
            chunks.append(current.strip())

        # Retain trailing context from the previous chunk.
        prefix = current[-overlap:] if overlap else ""

        # If a piece itself is large, split it further.
        if len(prefix + piece) > chunk_size:
            current = prefix

            for subpiece in split_recursively(piece):
                if len(current + subpiece) <= chunk_size:
                    current += subpiece
                else:
                    if current.strip():
                        chunks.append(current.strip())

                    current = current[-overlap:] + subpiece if overlap else subpiece
        else:
            current = prefix + piece

    if current.strip():
        chunks.append(current.strip())

    return chunks
