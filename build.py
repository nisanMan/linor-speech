"""Builds the site from content.json + pages/*.md into dist/.

Usage:
    python build.py          # build into dist/
    python build.py serve    # local preview at http://localhost:8000,
                             # rebuilds automatically when content.json, pages/ or assets/ change
"""
import datetime
import hashlib
import html
import http.server
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content.json"
PAGES = ROOT / "pages"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
PORT = 8000

IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp")
def svg_icon(body):
    return '<svg class="ci" viewBox="0 0 24 24" aria-hidden="true">{}</svg>'.format(body)


ICON_WHATSAPP = svg_icon(
    '<path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>')
ICON_FACEBOOK = svg_icon(
    '<path fill="#0866FF" d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/>')
ICON_WAZE = svg_icon(
    '<path fill="#33CCFF" stroke="#1D1D1B" stroke-width="1.2" stroke-linejoin="round" '
    'd="M12 2.8c-4.8 0-8.6 3.4-8.6 7.8 0 1.6.5 3 1.4 4.1-.3 1-1 1.8-1.9 2.3 1.5.5 3 .3 4.2-.4 1.4.8 3.1 1.2 4.9 1.2 4.8 0 8.6-3.4 8.6-7.6S16.8 2.8 12 2.8Z"/>'
    '<circle cx="9.4" cy="9.4" r="1" fill="#1D1D1B"/><circle cx="14.8" cy="9.4" r="1" fill="#1D1D1B"/>'
    '<path d="M9.2 12.3c1.6 1.5 4.2 1.5 5.8 0" fill="none" stroke="#1D1D1B" stroke-width="1.2" stroke-linecap="round"/>'
    '<circle cx="8.6" cy="19.8" r="2" fill="#1D1D1B"/><circle cx="15.4" cy="19.8" r="2" fill="#1D1D1B"/>')

# contact fields, in display order: (key, icon, label)
ICON_PHONE = svg_icon(  # Material Icons "call"
    '<path fill="#5D7A5E" d="M20.01 15.38c-1.23 0-2.42-.2-3.53-.56-.35-.12-.74-.03-1.01.24l-1.57 1.97c-2.83-1.35-5.48-3.9-6.89-6.83l1.95-1.66c.27-.28.35-.67.24-1.02-.37-1.11-.56-2.3-.56-3.53 0-.54-.45-.99-.99-.99H4.19C3.65 3 3 3.24 3 3.99 3 13.28 10.73 21 20.01 21c.71 0 .99-.63.99-1.18v-3.45c0-.54-.45-.99-.99-.99z"/>')

CONTACT_FIELDS = [("phone", ICON_PHONE, "טלפון"),
                  ("whatsapp", ICON_WHATSAPP, "וואטסאפ"),
                  ("email", '<span class="ci">✉️</span>', "דוא״ל"),
                  ("address", ICON_WAZE, "כתובת"),
                  ("facebook", ICON_FACEBOOK, "פייסבוק")]


# ---------- text helpers ----------

def versioned(path):
    """Append a content hash (?v=...) so browsers fetch the new file as soon as it changes."""
    f = ROOT / path
    if not f.is_file():
        return path
    return "{}?v={}".format(path, hashlib.md5(f.read_bytes()).hexdigest()[:8])


def esc(text):
    return html.escape(str(text), quote=True)


def inline(text):
    """Escape text, then allow **bold** and [links](url)."""
    out = esc(text)
    out = re.sub(r"\[(.+?)\]\((.+?)\)", lambda m: link_html(m.group(2), m.group(1)), out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return out.replace("\n", "<br>")


def link_html(url, text, cls=""):
    extra = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
    cls_attr = ' class="{}"'.format(cls) if cls else ""
    return '<a href="{}"{}{}>{}</a>'.format(url, cls_attr, extra, text)


def markdown(text):
    """Minimal Markdown: ## headings, paragraphs, - lists, > quotes."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.rstrip() for l in block.strip().splitlines()]
        m = re.match(r"(#{1,4})\s+(.*)", lines[0])
        if m and len(lines) == 1:
            level = min(len(m.group(1)) + 1, 4)  # '#' becomes h2: the page title is the h1
            out.append("<h{0}>{1}</h{0}>".format(level, inline(m.group(2))))
        elif all(re.match(r"[-*]\s+", l) for l in lines):
            out.append("<ul>{}</ul>".format("".join("<li>{}</li>".format(inline(l[2:].strip())) for l in lines)))
        elif all(l.startswith(">") for l in lines):
            out.append("<blockquote><p>{}</p></blockquote>".format(inline(" ".join(l[1:].strip() for l in lines))))
        else:
            out.append("<p>{}</p>".format(inline(" ".join(lines))))
    return "\n".join(out)


# ---------- contact links ----------

def href(link, contact):
    """Resolve a contact keyword (phone/whatsapp/email/address/facebook) or pass a URL through.
    Returns "" when the keyword's contact field is empty."""
    value = contact.get(link, "")
    if link == "phone":
        return "tel:" + re.sub(r"[^\d+]", "", value) if value else ""
    if link == "whatsapp":
        if not value:
            return ""
        url = "https://wa.me/" + re.sub(r"\D", "", value)
        if contact.get("whatsapp_message"):
            url += "?text=" + quote(contact["whatsapp_message"])
        return url
    if link == "email":
        return "mailto:" + value if value else ""
    if link == "address":
        return "https://waze.com/ul?navigate=yes&q=" + quote(value) if value else ""
    if link == "facebook":
        return value
    return link


def contact_list(contact):
    rows = []
    for key, icon, label in CONTACT_FIELDS:
        value = contact.get(key)
        if value:
            label = icon + label
            text = esc(value)
            if key == "facebook":
                text = esc(contact.get("facebook_label") or value)
            elif key == "whatsapp":
                text = "שליחת הודעה"
            rows.append("<div><dt>{}</dt><dd>{}</dd></div>".format(label, link_html(esc(href(key, contact)), text)))
    return '<dl class="contact">{}</dl>'.format("".join(rows))


# ---------- content loading ----------

def load_pages():
    pages = []
    for path in PAGES.glob("*.md"):
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", raw, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            body = m.group(2)
        pages.append({
            "file": "index.html" if path.stem == "index" else path.stem + ".html",
            "nav": meta.get("nav", path.stem),
            "title": meta.get("title", ""),
            "description": meta.get("description", ""),
            "order": int(meta.get("order", 99)),
            "layout": meta.get("layout", "page"),
            "image": meta.get("image", ""),
            "image_alt": meta.get("image_alt", ""),
            "certificates": meta.get("certificates", "").lower() == "true",
            "body": body,
        })
    pages.sort(key=lambda p: p["order"])
    return pages


def find_photo(content):
    """The configured photo, or else the first image found in assets/ or the project folder."""
    configured = content.get("photo")
    if configured and (ROOT / configured).is_file():
        return ROOT / configured
    for folder in (ASSETS, ROOT):
        images = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_TYPES)
        if images:
            return images[0]
    return None


# ---------- page bodies ----------

def body_home(page, c, photo_src):
    brand = c["brand"]
    photo = ""
    if photo_src:
        photo = '<div class="photo-wrap {}"><img class="photo" src="{}" alt="{}"></div>'.format(
            esc(c.get("photo_shape", "circle")), esc(photo_src), esc(brand["name"]))
    buttons = "".join(link_html(esc(href(b["link"], c["contact"])), inline(b["text"]), "btn btn-" + b.get("style", "primary"))
                      for b in c.get("home_buttons", []) if href(b["link"], c["contact"]))
    return """
<section class="home wrap{no_photo}">
  {photo}
  <div class="home-text">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{name}</h1>
    <p class="role">{role}</p>
    <span class="rule" aria-hidden="true"></span>
    <div class="prose">{text}</div>
    <div class="actions">{buttons}</div>
  </div>
</section>""".format(no_photo="" if photo else " no-photo", photo=photo, eyebrow=inline(brand.get("eyebrow", "")),
                     name=esc(brand["name"]), role=esc(brand["role"]), text=markdown(page["body"]), buttons=buttons)


def body_faq(page):
    items = []
    for chunk in re.split(r"^##\s+", page["body"].strip(), flags=re.M):
        if not chunk.strip():
            continue
        question, _, answer = chunk.partition("\n")
        items.append("<details><summary>{}</summary>{}</details>".format(inline(question.strip()), markdown(answer)))
    return '<div class="faq">{}</div>'.format("".join(items))


SEAL_ICON = ('<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M17 30l-5 14 7-3 4 6 4-12" fill="#C4876A"/>'
             '<path d="M31 30l5 14-7-3-4 6-4-12" fill="#C4876A"/><circle cx="24" cy="20" r="14" fill="#5D7A5E"/>'
             '<circle cx="24" cy="20" r="10" fill="none" stroke="#EAF0E7" stroke-width="1.5" stroke-dasharray="2 2.5"/>'
             '<path d="M19 20.5l3.5 3.5 7-7.5" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def body_certificates(c):
    certs = c.get("certificates") or {}
    cards = []
    for item in certs.get("items", []):
        img = item.get("image")
        if img and (ROOT / img).is_file():
            visual = '<a class="cert-img zoom" href="{0}"><img src="{0}" alt="{1}" loading="lazy"></a>'.format(esc(versioned(img)), esc(item["title"]))
        else:
            visual = '<div class="cert-img cert-seal">{}</div>'.format(SEAL_ICON)
        meta = " · ".join(esc(x) for x in (item.get("issuer"), item.get("year")) if x)
        cards.append('<figure class="cert">{}<figcaption><strong>{}</strong><span>{}</span></figcaption></figure>'.format(
            visual, inline(item["title"]), meta))
    if not cards:
        return ""
    return """
<section class="certs">
  <div class="wrap">
    <h2>{title}</h2><span class="rule" aria-hidden="true"></span>
    <div class="cert-grid">{cards}</div>
  </div>
</section>""".format(title=inline(certs.get("title", "")), cards="".join(cards))


def plain(text):
    """Markdown-ish text to plain text (for structured data)."""
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", text)
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def json_ld(data):
    return '\n  <script type="application/ld+json">{}</script>'.format(
        json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


def international_phone(phone):
    digits = re.sub(r"\D", "", phone)
    return "+972" + digits[1:] if digits.startswith("0") else "+" + digits


def head_seo_and_analytics(page, c):
    """Google Search Console verification, Google Analytics and schema.org structured data."""
    site, brand, contact = c["site"], c["brand"], c["contact"]
    google = c.get("google", {})
    out = ""
    if google.get("site_verification"):
        out += '\n  <meta name="google-site-verification" content="{}">'.format(esc(google["site_verification"]))
    ga = google.get("analytics_id")
    if ga:
        out += ('\n  <script async src="https://www.googletagmanager.com/gtag/js?id={0}"></script>'
                '\n  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}'
                'gtag("js",new Date());gtag("config","{0}");</script>').format(esc(ga))

    base = site.get("url", "").rstrip("/") + "/"
    if page["layout"] == "home" and site.get("url"):
        business = {
            "@context": "https://schema.org",
            "@type": "MedicalBusiness",
            "name": "{} – {}".format(brand["name"], brand["role"]),
            "description": site["description"],
            "url": base,
            "medicalSpecialty": "SpeechPathology",
            "employee": {"@type": "Person", "name": brand["name"], "jobTitle": brand["role"]},
        }
        if site.get("image"):
            business["image"] = base + site["image"]
        if contact.get("phone"):
            business["telephone"] = international_phone(contact["phone"])
        if contact.get("street") or contact.get("city"):
            business["address"] = {"@type": "PostalAddress", "streetAddress": contact.get("street", ""),
                                   "addressLocality": contact.get("city", ""), "addressCountry": "IL"}
        if contact.get("facebook"):
            business["sameAs"] = [contact["facebook"]]
        out += json_ld(business)
    if page["layout"] == "faq":
        questions = []
        for chunk in re.split(r"^##\s+", page["body"].strip(), flags=re.M):
            if chunk.strip():
                q, _, a = chunk.partition("\n")
                questions.append({"@type": "Question", "name": plain(q),
                                  "acceptedAnswer": {"@type": "Answer", "text": plain(a)}})
        out += json_ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": questions})
    return out


def render(page, pages, c, photo_src):
    if page["layout"] == "home":
        main = body_home(page, c, photo_src)
    else:
        if page["layout"] == "faq":
            inner = body_faq(page)
        elif page["layout"] == "contact":
            inner = '<div class="prose">{}</div>{}'.format(markdown(page["body"]), contact_list(c["contact"]))
        else:
            inner = '<div class="prose">{}</div>'.format(markdown(page["body"]))
        title = inline(page["title"] or page["nav"])
        certs = body_certificates(c) if page["certificates"] else ""
        if page["image"] and (ROOT / page["image"]).is_file():
            # split layout: title + text beside an arch-framed photo
            main = """
<section class="page-head split">
  <div class="wrap split-grid">
    <div class="split-text"><h1>{title}</h1><span class="rule" aria-hidden="true"></span>{inner}</div>
    <figure class="arch"><img src="{src}" alt="{alt}"></figure>
  </div>
</section>{certs}""".format(title=title, inner=inner, src=esc(versioned(page["image"])), alt=esc(page["image_alt"]), certs=certs)
        else:
            main = """
<section class="page-head">
  <div class="wrap"><h1>{title}</h1><span class="rule" aria-hidden="true"></span></div>
</section>
<section class="page-body wrap narrow">{inner}</section>{certs}""".format(title=title, inner=inner, certs=certs)

    nav = "".join('<a href="{}"{}>{}</a>'.format(p["file"], ' aria-current="page"' if p is page else "", esc(p["nav"]))
                  for p in pages)
    site, brand, contact = c["site"], c["brand"], c["contact"]
    title = site["title"] if page["layout"] == "home" else "{} | {}".format(page["title"] or page["nav"], brand["name"])
    canonical = ""
    if site.get("url"):
        base = site["url"].rstrip("/") + "/"
        page_url = base if page["file"] == "index.html" else base + page["file"]
        canonical = '\n  <link rel="canonical" href="{0}">\n  <meta property="og:url" content="{0}">'.format(esc(page_url))
        if site.get("image"):  # link-preview image (WhatsApp, Facebook) – must be an absolute URL
            canonical += ('\n  <meta property="og:image" content="{0}">\n  <meta property="og:image:width" content="1200">'
                          '\n  <meta property="og:image:height" content="630">\n  <meta property="og:image:alt" content="{1}">'
                          '\n  <meta name="twitter:card" content="summary_large_image">').format(
                esc(base + versioned(site["image"])), esc(brand["name"] + " – " + brand["role"]))
    head_extra = head_seo_and_analytics(page, c)
    footer_bits = [esc(brand["name"]), esc(brand["role"])]
    if contact.get("phone"):
        footer_bits.append(link_html(esc(href("phone", contact)), esc(contact["phone"])))
    float_wa = ""
    if contact.get("whatsapp"):
        float_wa = '<a class="float-wa" href="{}" target="_blank" rel="noopener" aria-label="וואטסאפ">{}</a>'.format(
            esc(href("whatsapp", contact)), ICON_WHATSAPP.replace("#25D366", "#FFFFFF"))
    return """<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{name}">
  <meta property="og:locale" content="he_IL">{canonical}
  <meta name="theme-color" content="#5D7A5E">
  <link rel="icon" type="image/png" sizes="32x32" href="{favicon32}">
  <link rel="icon" type="image/png" sizes="96x96" href="{favicon96}">
  <link rel="apple-touch-icon" href="{touch_icon}">
  <link rel="stylesheet" href="{style_css}">{head_extra}
</head>
<body>
<header class="site-header">
  <div class="wrap bar">
    <a class="brand" href="index.html"><span class="brand-name">{name}</span><span class="brand-role">{role}</span></a>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu" aria-label="תפריט">
      <span></span><span></span><span></span>
    </button>
    <nav id="menu" class="menu" aria-label="ניווט ראשי">{nav}</nav>
  </div>
</header>
<main>{main}
</main>
<footer class="site-footer"><div class="wrap">{footer} · © {year}</div></footer>
{float_wa}
<dialog class="lightbox" aria-label="תצוגה מוגדלת"><img alt=""></dialog>
<script src="{site_js}"></script>
</body>
</html>
""".format(title=esc(title), description=esc(page["description"] or site["description"]), canonical=canonical,
           name=esc(brand["name"]), role=esc(brand["role"]), nav=nav, main=main, footer=" · ".join(footer_bits),
           year=datetime.date.today().year, float_wa=float_wa, head_extra=head_extra,
           style_css=versioned("assets/style.css"), site_js=versioned("assets/site.js"),
           favicon32=versioned("assets/favicon-32.png"), favicon96=versioned("assets/favicon-96.png"),
           touch_icon=versioned("assets/apple-touch-icon.png"))


def build():
    with CONTENT.open(encoding="utf-8") as f:
        content = json.load(f)
    pages = load_pages()
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ASSETS, DIST / "assets")

    photo = find_photo(content)
    photo_src = None
    if photo:
        if photo.parent != ASSETS:
            shutil.copy2(photo, DIST / "assets" / photo.name)
        photo_src = "assets/{}?v={}".format(photo.name, hashlib.md5(photo.read_bytes()).hexdigest()[:8])

    for page in pages:
        (DIST / page["file"]).write_text(render(page, pages, content, photo_src), encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    # sitemap + robots for search engines
    if content["site"].get("url"):
        base = content["site"]["url"].rstrip("/") + "/"
        urls = "".join("\n  <url><loc>{}</loc></url>".format(esc(base if p["file"] == "index.html" else base + p["file"]))
                       for p in pages)
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "{}\n</urlset>\n".format(urls), encoding="utf-8")
        (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: {}sitemap.xml\n".format(base), encoding="utf-8")


# ---------- local dev server ----------

def source_mtime():
    files = [CONTENT] + [p for d in (ASSETS, PAGES) for p in d.rglob("*") if p.is_file()]
    files += [p for p in ROOT.iterdir() if p.suffix.lower() in IMAGE_TYPES]
    return max(p.stat().st_mtime for p in files)


def serve():
    state = {"mtime": None}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DIST), **kwargs)

        def do_GET(self):
            mtime = source_mtime()
            if mtime != state["mtime"]:
                try:
                    build()
                    state["mtime"] = mtime
                    print("✓ האתר נבנה מחדש")
                except Exception as e:  # show the error in the browser instead of crashing
                    msg = "שגיאה בבניית האתר (כנראה פסיק או מירכאה חסרים ב-content.json):\n\n{}".format(e)
                    print("✗", msg)
                    data = msg.encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            super().do_GET()

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *args):
            pass

    DIST.mkdir(exist_ok=True)
    print("האתר רץ בכתובת http://localhost:{}  (Ctrl+C לעצירה)".format(PORT))
    http.server.ThreadingHTTPServer(("", PORT), Handler).serve_forever()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
    else:
        build()
        print("✓ האתר נבנה בתיקייה dist/")
