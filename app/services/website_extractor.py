from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.utils.validators import validate_public_url


MAX_REDIRECTS = 4
USER_AGENT = "LinkAnalysisBot/1.0 (+website content analysis)"


async def extract_website(url: str, timeout: float, max_bytes: int) -> dict[str, str]:
    current = validate_public_url(url)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        for redirect in range(MAX_REDIRECTS + 1):
            current = validate_public_url(current)
            try:
                async with client.stream("GET", current) as response:
                    if response.is_redirect:
                        if redirect == MAX_REDIRECTS:
                            raise HTTPException(status_code=502, detail="Website redirected too many times")
                        location = response.headers.get("location")
                        if not location:
                            raise HTTPException(status_code=502, detail="Website returned an invalid redirect")
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise HTTPException(status_code=502, detail=f"Website returned HTTP {response.status_code}")
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        raise HTTPException(status_code=422, detail="The URL did not return an HTML page")
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise HTTPException(status_code=413, detail="Website page exceeds the configured size limit")
                        chunks.append(chunk)
                    return _parse_page(b"".join(chunks), current)
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Timed out while fetching the website")
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail=f"Could not fetch website: {exc.__class__.__name__}")
    raise HTTPException(status_code=502, detail="Could not fetch website")


def _parse_page(html: bytes, final_url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""
    headings = "\n".join(h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"]))
    text = "\n".join(soup.stripped_strings)
    return {"url": final_url, "title": title[:500], "description": description[:1000], "headings": headings[:6000], "text": text[:24000]}
