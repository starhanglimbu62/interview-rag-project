import pymupdf

def extract_text(filename: str, content:bytes) -> dict:
    
    extension = filename.lower().rsplit(".",1)[-1]
    
    
    if extension == "txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("TXT file must use UTF-8 encoding")
        
        page_count = None
    elif extension == "pdf":
        try:
            pdf = pymupdf.open(stream=content, filetype="pdf")
            
            if pdf.is_encrypted:
                pdf.close()
                raise ValueError("Encrypted PDF file are not supported")
            page_count = pdf.page_count
            
            text = "\n".join(
                page.get_text() for page in pdf
            )
            pdf.close()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Unable to read PDF File" ) from exc
    else:
        raise ValueError("Only PDF and TXT files are supported")
    
    if not text.strip():
        raise ValueError("Document contain no extraction text")
    return {
        "filename" : filename,
        "file_type" :  extension,
        "character_count" : len(text),
        "page_count": page_count,
        "extracted_text" : text
    }