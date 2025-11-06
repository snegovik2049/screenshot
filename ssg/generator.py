import os
import pathlib
from pathlib import Path
import shutil
import html
import re
from datetime import datetime
import json
from collections import Counter


LANGS = ["en","ru"]


def human_date(date_str, lang='en'):
    date = datetime.strptime(date_str, "%Y-%m-%d")
    months_en = [
        'January', 'February', 'March', 'April', 'May', 'June', 
        'July', 'August', 'September', 'October', 'November', 'December'
    ]    
    months_ru = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    
    if lang == 'ru':
        return f"{date.day} {months_ru[date.month-1]} {date.year}"
    elif lang == 'en':
        return f"{months_en[date.month-1]} {date.day}, {date.year}"
    else:
        raise ValueError("supported languages are 'ru' and 'en'")



def torsf(rsf):
    if rsf == "/":
        return "/"
    else:
        return f'/{rsf}/'



def parse_fmd(file_path, keystr='###'):
    escaped_keystr = re.escape(keystr)
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    content = re.sub(r'<!--(?:[^-]|-(?!->))*-->', '', content)    
    pattern = fr'{escaped_keystr}\s*([^\n]+)\n(.*?)(?=\n{escaped_keystr}|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    res = { key.strip(): value.strip() for key, value in matches }
    for x in res:
        res[x] = html.escape(res[x])
    return res


def parse_dir(directory, extension):
    results = {} 
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                full_path = os.path.join(root, file)
                try:
                    file_result = parse_fmd(full_path)                    
                    if 'id' in file_result:
                        results[file_result['id']] = file_result
                except Exception as e:
                    print(f"parse_dir error {full_path}: {e}")

    return results



def autolink(text):
    URL_RE = re.compile(r'(https?://[^\s\]\)]+)', re.IGNORECASE)    
    return URL_RE.sub(lambda m: f'<a class="o" href="{html.escape(m.group(1))}" target="_blank" rel="noopener">{html.escape(m.group(1))}</a>', html.escape(text))


def status_color(status):
	d = {
		"awaiting":"g",
		"completely":"p",
		"almost":"p",
		"didnot":"r",
		"unverifiable":"g",
	}
	return d[status]


def suplang(orig,rlang):
    return '' if orig == rlang else f'<sup>{orig} → {rlang}</sup>'


def rate_post(p):
    res = {
        "awaiting,complex,confident":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "awaiting,complex,careful":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "awaiting,regular,confident":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "awaiting,regular,careful":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "unverifiable,complex,confident":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "unverifiable,complex,careful":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "unverifiable,regular,confident":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},
        "unverifiable,regular,careful":{"status":"", "complexity":"", "confidence":"", "total":"", "r":None},  

        "completely,complex,confident":{"status":" (+7)", "complexity":" (+2)", "confidence":" (+1)", "total":"10 (7+2+1)", "r":10},
        "completely,complex,careful":{"status":" (+7)", "complexity":" (+2)", "confidence":" (+0)", "total":"9 (7+2+0)", "r":9},
        "completely,regular,confident":{"status":" (+7)", "complexity":" (+0)", "confidence":" (+1)", "total":"8 (7+0+1)", "r":8},
        "completely,regular,careful":{"status":" (+7)", "complexity":" (+0)", "confidence":" (+0)", "total":"7 (7+0+0)", "r":7},

        "almost,complex,confident":{"status":" (+5)", "complexity":" (+2)", "confidence":" (+0)", "total":"7 (5+2+0)", "r":7},
        "almost,complex,careful":{"status":" (+5)", "complexity":" (+2)", "confidence":" (+0)", "total":"7 (5+2+0)", "r":7},
        "almost,regular,confident":{"status":" (+5)", "complexity":" (+0)", "confidence":" (+0)", "total":"5 (5+0+0)", "r":5},
        "almost,regular,careful":{"status":" (+5)", "complexity":" (+0)", "confidence":" (+0)", "total":"5 (5+0+0)", "r":5},

        "didnot,complex,confident":{"status":" (+2)", "complexity":" (+0)", "confidence":" (-1)", "total":"1 (2+0-1)", "r":1},
        "didnot,complex,careful":{"status":" (+2)", "complexity":" (+0)", "confidence":" (+0)", "total":"2 (2+0+0)", "r":2},
        "didnot,regular,confident":{"status":" (+2)", "complexity":" (+0)", "confidence":" (-1)", "total":"1 (2+0-1)", "r":1},
        "didnot,regular,careful":{"status":" (+2)", "complexity":" (+0)", "confidence":" (+0)", "total":"2 (2+0+0)", "r":2},                       
    }
    return res[f'{p["status"]},{p["complexity"]},{p["confidence"]}']


def bayesian_average(v):
    m = 5.5
    C = 10
    return (C*m + sum(v))/(C + len(v))

def calc_stat(posts):
    status_counts = Counter(item['status'] for item in posts)
    complexity_counts = Counter(item['complexity'] for item in posts)
    confidence_counts = Counter(item['confidence'] for item in posts)
    # r_counts = Counter(item['params']['r'] for item in posts)
    b  = bayesian_average([item['params']['r'] for item in posts if item['params']['r']])
    
    stat = {}
    stat["total_authors"] = len(set([item["author-id"] for item in posts]))
    stat["total_posts"] = len(posts)
    stat["total_verified"] = status_counts["completely"] + status_counts["almost"] + status_counts["didnot"]
    stat["success"] = status_counts["completely"] + status_counts["almost"]
    stat["success_pct"] = str(round(stat["success"]*100 / stat["total_verified"]))+"%" if stat["total_verified"] != 0 else "*"
    stat["complex_pct"] =  str(round(complexity_counts["complex"]*100 / stat["total_posts"]))+"%" if stat["total_posts"] != 0 else "*"
    stat["confident_pct"] = str(round(confidence_counts["confident"]*100 / stat["total_posts"]))+"%" if stat["total_posts"] != 0 else "*"
    stat["rating"] = f'{round(b,2):.2f}' if stat["total_verified"] >= 1 else "*";
    stat["ratingf"] = round(b,2)
    return stat


def calc_ranking(authors):
    return sorted([item for item in authors if item['stat']['total_verified'] >= 10], key=lambda x: (x['stat']['ratingf'], x['stat']['total_verified']), reverse=True)

def calc_ranking_posts(authors):
    return sorted([item for item in authors], key=lambda x: (x['stat']['total_posts']), reverse=True)

def calc_ranking_verified(authors):
    return sorted([item for item in authors], key=lambda x: (x['stat']['total_verified']), reverse=True)




def render_stat(stat, items, locales, rlang, linkflag=False, boldflag=""):
    parts = []
    parts.append('<div class="stat">')
    for x in items:
        tblock = f'{locales["stat"][x][rlang]}'
        sblock = f'{stat[x]}'
        if x == "total_authors" and linkflag and False:
            tblock = f'<a class="u {"bold" if boldflag==x else ""}" href="/{rlang}/authors">{locales["stat"][x][rlang]}</a>'
            sblock = f'<a class="" href="/{rlang}/authors">{stat[x]}</a>'
        if x == "total_posts" and linkflag and False:
            tblock = f'<a class="u {"bold" if boldflag==x else ""}" href="/{rlang}/new">{locales["stat"][x][rlang]}</a>'  
            sblock = f'<a class="" href="/{rlang}/new">{stat[x]}</a>'          
        if x == "rating" and stat["total_verified"] < 10:
            sblock = f'<span class="g2">{stat[x]}</span>'
        parts.append(f'<div class="itm"><div class="hstat">{tblock}</div><div class="nstat bold">{sblock}</div></div>')
    parts.append('</div>')
    return "\n".join(parts)


def render_heatmap(posts, locales, rlang):
    ps = sorted(posts, key=lambda x: (x['time-statement'] if x['time-statement'] else "9999-12-31", x['id']), reverse=False)

    parts = []
    parts.append('<div class="heatmap">')
    for x in ps:
        color = ""
        if x["status"] in ['completely', 'almost']:
            color = "p"
        if x["status"] in ['didnot']:
            color = "rh"
        if x["status"] in ['awaiting','unverifiable']:
            color = "g"
        # data-tooltip="{human_date(x["time-statement"],rlang)}"    
        parts.append(f'<a class="hmc {color}" href="/{rlang}/{x["author-id"]}/{x["id"]}"></a>')            
    parts.append('</div>')
    return "\n".join(parts)


def render_ranking(ranking, rlang, locales):
    parts = []
    parts.append('<table>')
    parts.append('<tbody>')
    for i,x in enumerate(ranking):
        rtg_color = "p" if x["stat"]["ratingf"] >= 5.5 else "r"
        parts.append(f'<tr> <td width="1rem"><b>{i+1}.<b></td> <td><a class="d" href="/{rlang}/{x["id"]}"><b>{x["name."+rlang]}</b><br><small>{x["description."+rlang]}</small><a/></td> <td width="1rem"><a class="d" href="/{rlang}/{x["id"]}"><span class="badge rtg {rtg_color}"><small><b>{x["stat"]["rating"]}</b></small></span></a></td> </tr>')
    parts.append('</tbody>')
    parts.append('</table>')
    return "\n".join(parts)


def render_authors(authors, rlang, locales):
    parts = []
    parts.append('<table>')
    parts.append('<tbody>')
    for i,x in enumerate(authors):
        parts.append(f'<tr> <td><a class="d" href="/{rlang}/{x["id"]}"><b>{x["name."+rlang]}</b> ({x["stat"]["total_posts"]}/{x["stat"]["total_verified"]})<br><small>{x["description."+rlang]}</small><a/></td></tr>')
    parts.append('</tbody>')
    parts.append('</table>')
    return "\n".join(parts)


def render_post_item(post, author, rlang, rsf, locales):
    parts = []
    parts.append("<hgroup>")
    parts.append(f"<h4><a href='/{rlang}/{author["id"]}'>{author["name."+rlang]}</a></h4>")
    parts.append(f"<p><time datetime='{post["time-statement"]}'>{human_date(post["time-statement"],rlang)}</time> {suplang(post["original-language"],rlang)}</p>")
    parts.append("</hgroup>")
    parts.append(f"<p>{post["statement."+rlang].replace('\n', '<br>').rstrip('.')}")
    if post["context."+rlang].strip() != "":
        parts.append(f"<span class='g2'>({post["context."+rlang].rstrip('.')})</span>")
    parts.append(f"</p>")
    parts.append(f"<small class='badge {status_color(post["status"])}'>{locales[post["status"]][rlang]}</small>")
    
    if post["status"] == "awaiting" and post["time-awaiting"] != "" and rsf == "awaiting":
        parts.append(f"<small class='badge {status_color(post["status"])}'>{human_date(post["time-awaiting"],rlang)}</small>")
    elif post["status"] != "awaiting" and post["time-verified"] != "" and rsf == "verified":
        parts.append(f"<small class='badge {status_color(post["status"])}'>{human_date(post["time-verified"],rlang)}</small>") 
    
    parts.append(f"<a class='linka' href='/{rlang}/{author["id"]}/{post["id"]}'></a>")
    return "<article>" + "\n".join(parts) + "</article>"


def render_post(post, author, rlang, locales):
    parts = []
    parts.append("<hgroup>")
    parts.append(f"<h4><a href='/{rlang}/{author["id"]}'>{author["name."+rlang]}</a></h4>")
    parts.append(f"<p><time datetime='{post["time-statement"]}'>{human_date(post["time-statement"],rlang)}</time> {suplang(post["original-language"],rlang)}</p>")
    parts.append("</hgroup>")
    parts.append(f"<p>{post["statement."+rlang].replace('\n', '<br>').rstrip('.')}")
    if post["context."+rlang].strip() != "":
        parts.append(f"<span class='g2'>({post["context."+rlang].rstrip('.')})</span>")
    parts.append(f"</p>")    


    parts.append(f"<small class='badge {status_color(post["status"])}'>{locales[post["status"]][rlang]}</small>")
    if post["status"] == "awaiting" and post["time-awaiting"] != "":
        parts.append(f"<small class='badge {status_color(post["status"])}'>{human_date(post["time-awaiting"],rlang)}</small>")
    elif post["status"] != "awaiting" and post["time-verified"] != "":
        parts.append(f"<small class='badge {status_color(post["status"])}'>{human_date(post["time-verified"],rlang)}</small>")     

    parts.append(f"<hr><small><p><b>{locales["notes_refs"][rlang]}</b><br>{autolink(post["notes."+rlang]).replace('\n', '<br>')}</p></small>")
    parts.append(f"<small><p>{locales["params"][rlang]}: {locales[post["status"]][rlang].lower()}{post["params"]["status"]}, {locales[post["complexity"]][rlang].lower()}{post["params"]["complexity"]}, {locales[post["confidence"]][rlang].lower()}{post["params"]["confidence"]} {"<br>"+locales["post_total"][rlang] + " " + str(post["params"]["r"]) if post["params"]["r"] else ""}</p></small>")
    return "<article>" + "\n".join(parts) + "</article>"

	



def create_post_page(post, author, rlang, locales):    
    html_block = render_post(post,author,rlang, locales)
    
    rout = f"/{post['author-id']}/{post['id']}/"
    title = author["name."+rlang]
    if post["title."+rlang] != '':
        title = post["title."+rlang] + " | " + title
    else:
        if len(post["statement."+rlang]) + len(post["context."+rlang]) <= 120:
            title = post["statement."+rlang].rstrip('.') + (" | " + post["context."+rlang].rstrip('.') if post["context."+rlang] != '' else "") + " | " + title  
        else:
            title = title + " | " + post["time-statement"]
    meta = {
        "rlang":rlang,
        "title":title,
        "canonical":f"{rlang}{rout}"
    }
    html_doc = create_base(html_block, meta, rlang, locales, rout)

    output_file = Path(f"./public/{rlang}/{post['author-id']}/{post['id']}/index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_doc, encoding="utf-8")




def create_author_page(author, posts, rlang, rsf, locales):
    parts = []

    parts.append("<article>")
    parts.append("<hgroup>")
    parts.append(f"<h4>{author["name."+rlang]}</h4>")
    parts.append(f"<p>{author["description."+rlang]}</p>")
    parts.append("</hgroup>")
    parts.append("<hr>")
    parts.append(render_stat(author["stat"],["total_posts","total_verified","success_pct","rating"],locales,rlang,linkflag=False, boldflag=""))
    parts.append(render_heatmap(author["posts"],locales, rlang))
    parts.append("</article>")


    # 
    parts.append('<p class="fnav" style="padding-left: 1em">')
    parts.append(f"<a class='badge sec {"p" if rsf == "/" else "w"}' href='/{rlang}/{author["id"]}/'>{locales["sf"]["new"][rlang]}</a> ")
    parts.append(f"<a class='badge sec {"p" if rsf == "awaiting" else "w"}' href='/{rlang}/{author["id"]}/awaiting'>{locales["sf"]["awaiting"][rlang]}</a> ")
    parts.append(f"<a class='badge sec {"p" if rsf == "verified" else "w"}' href='/{rlang}/{author["id"]}/verified'>{locales["sf"]["verified"][rlang]}</a> ")
    parts.append('</p>')

    for x in posts:
        parts.append(render_post_item(x,author, rlang, rsf, locales))

    html_block = "\n".join(parts)

    rout = f"/{author["id"]}{torsf(rsf)}"
    meta = {
        "rlang":rlang,
        "title":author["name."+rlang] + " | "  + (locales["titles"]["prpr"][rlang] if rsf == "/" else locales["titles"][rsf][rlang]),
        "canonical":f"{rlang}/{author["id"]}/"
    }

    html_doc = create_base(html_block, meta, rlang, locales, rout)

    output_file = Path(f"./public/{rlang}/{author["id"]}{torsf(rsf)}index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_doc, encoding="utf-8")    


def create_ranking_page(stat, ranking, rlang, rsf, locales):
    parts = []
    # stat
    parts.append("<article>")
    parts.append(render_stat(stat,["total_authors", "total_posts","total_verified","success_pct"],locales,rlang,True,""))
    parts.append("</article>")

    # ranking
    parts.append("<article>")
    parts.append(render_ranking(ranking, rlang, locales))
    parts.append(f"<p>{locales["about_notes"]["rtg_note"][rlang]}</p>")
    parts.append(f"<p><a class='u' href='/{rlang}/about'>{locales["about_notes"]["how_rating"][rlang]}</a></p>")
    parts.append("</article>")

    html_block = "\n".join(parts)

    rout = f"{torsf(rsf)}"
    meta = {
        "rlang":rlang,
        "title":locales["titles"]["ranking"][rlang],
        "canonical":f"{rlang}"
    }

    html_doc = create_base(html_block, meta, rlang, locales, rout)

    output_file = Path(f"./public/{rlang}{torsf(rsf)}index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_doc, encoding="utf-8")  

    if rlang == "en" and rsf == "/":
        output_file = Path(f"./public/{torsf(rsf)}index.html")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_doc, encoding="utf-8")  


def create_authors_page(stat, authors, rlang, locales):
    parts = []
    # stat
    parts.append("<article>")
    parts.append(render_stat(stat,["total_authors", "total_posts","total_verified","success_pct"],locales,rlang,True,"total_authors"))
    parts.append("</article>")

    # authors
    parts.append("<article>")
    parts.append(render_authors(authors, rlang, locales))
    parts.append("</article>")

    html_block = "\n".join(parts)
    
    rout = f"/authors/"
    meta = {
        "rlang":rlang,
        "title":locales["titles"]["authors"][rlang],
        "canonical":f"{rlang}{rout}"
    }

    html_doc = create_base(html_block, meta, rlang, locales, rout)

    output_file = Path(f"./public/{rlang}/authors/index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_doc, encoding="utf-8")     


def create_mainfeed_page(authors, posts, stat, rlang, rsf, locales):
    nb = 100
    pages = [posts[i:i+nb] for i in range(0, len(posts), nb)]
    page1 = pages[0]

    parts = []
    # stat
    parts.append("<article>")
    parts.append(render_stat(stat,["total_authors", "total_posts","total_verified","success_pct"],locales,rlang, True,"total_posts"))
    parts.append("</article>")

    #
    parts.append('<p class="fnav" style="padding-left: 1em">')
    parts.append(f"<a class='badge sec {"p" if rsf == "new" else "w"}' href='/{rlang}/new'>{locales["sf"]["new"][rlang]}</a>")
    parts.append(f"<a class='badge sec {"p" if rsf == "awaiting" else "w"}' href='/{rlang}/awaiting'>{locales["sf"]["awaiting"][rlang]}</a> ")
    parts.append(f"<a class='badge sec {"p" if rsf == "verified" else "w"}' href='/{rlang}/verified'>{locales["sf"]["verified"][rlang]}</a> ")
    parts.append('</p>')

    for x in page1:
        parts.append(render_post_item(x,authors[x["author-id"]], rlang, rsf, locales))

    html_block = f"""
    <script>
    document.addEventListener('DOMContentLoaded', () => {{
        let currentPage = 1;
        let flag = true;

        window.addEventListener('scroll', () => {{
            if (window.innerHeight*3.0 + window.scrollY >= document.documentElement.scrollHeight && currentPage < {len(pages)} && flag) {{
                flag = false
                fetch(`${{currentPage + 1}}.html`)
                    .then(response => {{
                        if (!response.ok) throw new Error('404');
                        return response.text();
                    }})
                    .then(html => {{
                        document.getElementById('abc').insertAdjacentHTML('beforeend', html);
                        currentPage++;
                        flag = true;
                    }})
                    .catch(error => {{
                        console.log(error);
                        flag = true;
                    }});                    
            }}
        }});
    }});
    </script>    
    """

    html_block = html_block + "\n".join(parts)
    
    rout = f"{torsf(rsf)}"
    meta = {
        "rlang":rlang,
        "title":locales["titles"][f"{rsf}"][rlang],
        "canonical":f"{rlang}{rout}"
    }

    html_doc = create_base(html_block, meta, rlang, locales, rout)

    output_file = Path(f"./public/{rlang}{torsf(rsf)}index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_doc, encoding="utf-8")

    page_parts = []
    i = 2
    for p in pages[1:]:
        page_parts = []
        for x in p:
            page_parts.append(render_post_item(x,authors[x["author-id"]], rlang, rsf, locales))
        page_block = "\n".join(page_parts)
        output_file = Path(f"./public/{rlang}{torsf(rsf)}{i}.html")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(page_block, encoding="utf-8") 
        i = i + 1       


def create_about_page(rlang, locales):
    parts = []
    
    with open(f'./ssg/aux/about/about.{rlang}.html', 'r', encoding='utf-8') as file:
        about_page = file.read()
    
    parts.append("<article>")
    parts.append(about_page)
    parts.append("</article>")

    html_block = "\n".join(parts)
    
    rout = f"/about/"
    meta = {
        "rlang":rlang,
        "title":locales["titles"]["about"][rlang],
        "canonical":f"{rlang}{rout}"
    }

    html_doc = create_base(html_block, meta, rlang, locales, rout)

    output_file = Path(f"./public/{rlang}/about/index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_doc, encoding="utf-8")


def create_base(html_block, meta, rlang, locales, rout):
    html_doc = f"""
    <!doctype html>
    <html lang="{rlang}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        
        <title>{meta['title']}</title>
        <link rel="canonical" href="https://screenshot.report/{meta["canonical"]}">
        <link rel="alternate" hreflang="ru" href="https://screenshot.report/ru{rout}" />
        <link rel="alternate" hreflang="en" href="https://screenshot.report/en{rout}" />        

        <link rel="icon" href="/favicon.ico?v=16" sizes="32x32">
        <link rel="icon" href="/icon.svg?v=16" type="image/svg+xml">
        <link rel="apple-touch-icon" href="/apple-touch-icon.png?v=16">
        <link rel="manifest" href="/manifest.webmanifest?v=16"> 

        <link rel="stylesheet" href="/assets/pico.min.css">
        <link rel="stylesheet" href="/assets/my.css">
    </head>
    <body class="bgc">
        <header class="container">
            <article style="position: relative;">
                <h1 style="margin-bottom:0;"><a href="/{rlang}">screenshot</a></h1>
                <p class="fnav" style="margin-bottom:0; margin-top:0;">{locales["ppm"][rlang]} <span class="no-break">| <a class=" {"bold" if rlang=="ru" else ""}" href="/ru{rout}">ru</a> | <a class=" {"bold" if rlang=="en" else ""}" href="/en{rout}">en</a></span></p>
                <p class="fnav" style="margin-bottom:0; margin-top:8px;">
                <span><a class="badge sec {"p "if rout=='/' else "w"}" href="/{rlang}/">{locales["rating"][rlang]}</a></span>
                <span><a class="badge sec {"p" if rout in ['/new/','/awaiting/','/verified/'] else "w"}" href="/{rlang}/new">{locales["predictions"][rlang]}</a></span>
                <span><a class="badge sec {"p "if rout=='/authors/' else "w"}" href="/{rlang}/authors">{locales["authors"][rlang]}</a></span>
                </p>

                <a class="gh" rel="noopener noreferrer" class="contrast" aria-label="GitHub repository" href="https://github.com/snegovik2049/screenshot" target="_blank">
                <svg width="24.25" height="24" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z" fill="#24292f"/></svg>                
                </a>
            </article>
        </header>
        <main class="container">
            <section class="grid">
                <div id="abc">
                    {html_block}
                </div>
            </section>
        </main>
    {"""<a class="to-top" onclick='window.scrollTo({top: 0})' aria-label="up">↑</a>""" if rout not in ['/','/about/'] else ''}
    </body>
    </html>
    """ 
    return html_doc   




def _create_url_entry(base_url, ru_path, en_path, x_default_path):
    ru_url = f"{base_url}{ru_path}"
    en_url = f"{base_url}{en_path}"
    x_default_url = f"{base_url}{x_default_path}"

    hreflangs = (
        f'    <xhtml:link rel="alternate" hreflang="ru" href="{ru_url}" />\n'
        f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}" />\n'
        f'    <xhtml:link rel="alternate" hreflang="x-default" href="{x_default_url}" />\n'
    )

    ru_entry = (
        f'  <url>\n'
        f'    <loc>{ru_url}</loc>\n'
        f'{hreflangs}'
        f'  </url>\n'
    )

    en_entry = (
        f'  <url>\n'
        f'    <loc>{en_url}</loc>\n'
        f'{hreflangs}'
        f'  </url>\n'
    )
    
    return ru_entry + en_entry

def generate_sitemap_string(authors_list, base_url="https://screenshot.report"):    
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" ',
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    ]

    #
    xml_parts.append(_create_url_entry(base_url, "/ru/", "/en/", "/en/"))

    #
    static_pages = ["about", "authors", "new", "awaiting", "verified"]
    for page_slug in static_pages:
        xml_parts.append(_create_url_entry(base_url, f"/ru/{page_slug}", f"/en/{page_slug}", f"/en/{page_slug}"))

    #
    for author in authors_list:
        author_id = author['id']
        
        xml_parts.append(_create_url_entry(base_url, f"/ru/{author_id}", f"/en/{author_id}", f"/en/{author_id}"))
        xml_parts.append(_create_url_entry(base_url, f"/ru/{author_id}/awaiting", f"/en/{author_id}/awaiting", f"/en/{author_id}/awaiting"))
        xml_parts.append(_create_url_entry(base_url, f"/ru/{author_id}/verified", f"/en/{author_id}/verified", f"/en/{author_id}/verified"))

        if 'posts' in author and author['posts']:
            for post in author['posts']:
                xml_parts.append(_create_url_entry(base_url,f"/ru/{author_id}/{post["id"]}",f"/en/{author_id}/{post["id"]}",f"/en/{author_id}/{post["id"]}"))

    #
    xml_parts.append('</urlset>')
    
    return "".join(xml_parts)


def create_sitemap(authors):
    xml_doc = generate_sitemap_string(authors, "https://screenshot.report")
    output_file = Path(f"./public/sitemap.xml")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(xml_doc, encoding="utf-8")


def create_site():
    public_path = './public'
    if os.path.exists(public_path):
        shutil.rmtree(public_path)
    shutil.copytree("./ssg/aux/assets", './public/assets')
    shutil.copytree("./ssg/aux/favicon/", './public/', dirs_exist_ok=True)
    shutil.copy("./ssg/aux/robots.txt", "./public/")
    shutil.copy("./ssg/aux/CNAME", "./public/")


    with open('./ssg/aux/locales.json', 'r', encoding='utf-8') as f:
        locales = json.load(f)

    authors = parse_dir(directory="./data/authors", extension=".md")
    posts = parse_dir(directory="./data/posts", extension=".md")
    
    [a.setdefault('posts', []) for a in authors.values()]


    # posts pages
    for p in posts.values():
        p["params"] = rate_post(p)
        authors[str(p["author-id"])]["posts"].append(p)
        [create_post_page(p,authors[p["author-id"]],rlang, locales) for rlang in LANGS]

    # authors pages
    for a in authors.values():
        a["stat"] = calc_stat(a["posts"])
        rsfposts = {
            "/":sorted(a["posts"], key=lambda x: (x['time-statement'] if x['time-statement'] else "9999-12-31", x['id']), reverse=True),
            "awaiting":sorted([item for item in a["posts"] if item['status'] == 'awaiting'], key=lambda x: (x['time-awaiting'] if x['time-awaiting'] else '9999-12-31', x['id'])),
            "verified":sorted([item for item in a["posts"] if item['status'] != 'awaiting'], key=lambda x: (x['time-verified'] if x['time-verified'] else "9999-12-31", x['id']), reverse=True),
        }
        [create_author_page(a,v,rlang,k,locales) for rlang in LANGS for k,v in rsfposts.items()]

    # mainfeed pages
    main_stat = calc_stat(posts.values())
    main_ranking = calc_ranking(authors.values())
    posts_ranking = calc_ranking_posts(authors.values())

    rsfposts = {
        "new":sorted(posts.values(), key=lambda x: (x['time-statement'] if x['time-statement'] else "9999-12-31", x['id']), reverse=True),
        "awaiting":sorted([item for item in posts.values() if item['status'] == 'awaiting'], key=lambda x: (x['time-awaiting'] if x['time-awaiting'] else '9999-12-31', x['id'])),
        "verified":sorted([item for item in posts.values() if item['status'] != 'awaiting'], key=lambda x: (x['time-verified'] if x['time-verified'] else "9999-12-31", x['id']), reverse=True),
    }
    [create_mainfeed_page(authors,v, main_stat, rlang,k,locales) for rlang in LANGS for k,v in rsfposts.items()]

    # ranking index page
    rsfs = ["/"]
    [create_ranking_page(main_stat, main_ranking, rlang, rsf, locales) for rlang in LANGS for rsf in rsfs]

    # authors list
    [create_authors_page(main_stat, posts_ranking, rlang, locales) for rlang in LANGS]

    # about page
    [create_about_page(rlang, locales) for rlang in LANGS]

    # sitemap
    create_sitemap(authors.values())

create_site()


#



