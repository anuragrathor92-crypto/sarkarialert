"""Build a reviewed batch into the existing static site. No source scraping at publication."""
import argparse, datetime as dt, html, json, re
from pathlib import Path
from zoneinfo import ZoneInfo
from discover import official,article_url

ROOT=Path(__file__).resolve().parents[2]
CATS={"latest-jobs":"Latest Jobs","results":"Results","admit-card":"Admit Cards","answer-key":"Answer Key","admission":"Admission","documents":"Documents","10th-iti":"10th / ITI Jobs","outsourcing":"Outsourcing Jobs","syllabus":"Syllabus","yojana":"Sarkari Yojana","scholarship":"Scholarship","exam-date":"Exam Dates"}
JOB={"latest-jobs","10th-iti","outsourcing"}
BASE="https://anuragrathor92-crypto.github.io/sarkarialert/"
def e(v):return html.escape(str(v or ""),quote=True)
def read(path):return (ROOT/path).read_text(encoding="utf-8")
def normalize(t):return re.sub(r"[\W_]+","",t.casefold())
def validate(p,now):
    for key in ("id","title","category","department","noticeId","notificationUrl","officialUrl","summary","reviewedBy","reviewedOn"):
        if not isinstance(p.get(key),str) or not p[key].strip():raise ValueError("missing "+key)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}",p["id"]):raise ValueError("invalid ID")
    if p["category"] not in CATS:raise ValueError("invalid category")
    if p.get("approved") is not True or p.get("officialFactsChecked") is not True:raise ValueError("approval and source review required")
    review=dt.date.fromisoformat(p["reviewedOn"])
    if review>now.date() or (now.date()-review).days>7:raise ValueError("review date must be within 7 days")
    for key in ("officialUrl","notificationUrl"):
        if not official(p[key]):raise ValueError("unapproved official domain: "+key)
    if not isinstance(p.get("rows"),list) or not p["rows"] or any(not isinstance(r,list) or len(r)!=2 for r in p["rows"]):raise ValueError("reviewed facts rows required")
    if p.get("discoveryUrl") and article_url(p["discoveryUrl"])!=p["discoveryUrl"]:raise ValueError("invalid discovery URL")
    if p["category"]=="yojana":
        if p.get("applyUrl") or p.get("actionUrl"):raise ValueError("scheme application links prohibited")
    if p["category"] in JOB:
        if not p.get("applyUrl") or not official(p["applyUrl"]) or p.get("applyLinkChecked") is not True:raise ValueError("reviewed official application link required")
        if p.get("applicationStatus")!="OPEN":raise ValueError("job not marked open")
        if not p.get("deadline"):raise ValueError("deadline required")
    if p.get("deadline"):
        deadline=dt.datetime.fromisoformat(p["deadline"])
        if deadline.tzinfo is None or deadline<=now:raise ValueError("expired/invalid deadline")
    return p

def a(url,label,cls=""):
    return '<a'+(' class="'+cls+'"' if cls else '')+' href="'+e(url)+'" target="_blank" rel="noopener noreferrer">'+e(label)+'</a>'

def render(p,template):
    cat=p["category"];title=p["title"];rows=p["rows"]
    buttons=""
    links=[("Official notice",p["notificationUrl"]),("Official website",p["officialUrl"])]
    if cat in JOB:
        buttons='<div class="apply-box" data-apply-box data-deadline="'+e(p["deadline"])+'">'+a(p["applyUrl"],"Apply Online – Official Portal","apply-btn")+' '+a(p["notificationUrl"],"Notification","notice-btn")+'</div>'
        links.insert(0,("Apply Online",p["applyUrl"]))
    # Schemes intentionally have no external application links or buttons.
    link_table="" if cat=="yojana" else '<h2 class="detail-bar">Important Links</h2><table class="important-links"><tbody>'+''.join('<tr><th scope="row">'+e(k)+'</th><td>'+a(v,k)+'</td></tr>' for k,v in links)+'</tbody></table>'
    body='<article class="article detail"><a href="../../">Home</a> › <a href="../../category/'+cat+'/">'+CATS[cat]+'</a><h1>'+e(title)+'</h1>'+buttons+'<p>Official source reviewed: '+e(p["reviewedOn"])+'</p><p>'+e(p["summary"])+'</p><div class="detail-box"><h2 class="detail-bar">Important Information</h2><table><tbody>'+''.join('<tr><th scope="row">'+e(k)+'</th><td>'+e(v)+'</td></tr>' for k,v in rows)+'</tbody></table>'+link_table+'</div><p class="warning">Check the issuing department for current rules and revised dates.</p></article>'
    s=re.sub(r"<title>.*?</title>",lambda _: "<title>"+e(title)+" | Sarkari Alert</title>",template,count=1)
    s=re.sub(r'<meta name="description" content="[^"]*">',lambda _:'<meta name="description" content="'+e(p["summary"][:160])+'">',s,count=1)
    s=re.sub(r'<link rel="canonical" href="[^"]*">',lambda _:'<link rel="canonical" href="'+BASE+'posts/'+p["id"]+'/">',s,count=1)
    return re.sub(r"<main>[\s\S]*?</main>",lambda _:"<main>"+body+"</main>",s,count=1)

def item(p,prefix):
    extras=""
    if p["category"] in JOB:extras='<div class="job-actions">'+a(p["applyUrl"],"Apply Online","apply-btn")+' '+a(p["notificationUrl"],"Notification","notice-btn")+'</div>'
    date=p.get("lastDate") or (p.get("deadline") or "")[:10]
    return '<li data-post data-deadline="'+e(p.get("deadline"))+'" data-department="'+e(p["department"])+'" data-qualification="'+e(p.get("qualification"))+'"><a href="'+prefix+'posts/'+p["id"]+'/">'+e(p["title"])+'</a>'+(' <span class="date-tag">'+e(date)+'</span>' if date else '')+extras+'</li>'

def inject(s,items):
    if "<ul>" in s:return s.replace("<ul>","<ul>"+items,1)
    s,n=re.subn(r'<p class="empty"[^>]*>[\s\S]*?</p>',lambda _:"<ul>"+items+"</ul>",s,count=1)
    if n!=1:raise ValueError("No listing insertion point")
    return s

def build(approved,now):
    db=json.loads(read("data/posts.json"));directory=json.loads(read("data/schemes_directory.json"))["records"]
    old=db["posts"]+directory;ids={p["id"] for p in old};titles={normalize(p["title"]) for p in old}
    notices={(p.get("department","").casefold(),p.get("noticeId")) for p in old if p.get("noticeId")}
    sourceids={p.get("discoveryUrl") for p in old if p.get("discoveryUrl")}
    accepted=[];rejected=[]
    for row in approved:
        try:
            p=dict(validate(row,now))
            nk=(p["department"].casefold(),p["noticeId"]);nt=normalize(p["title"])
            if p["id"] in ids or nt in titles or nk in notices or p.get("discoveryUrl") in sourceids:raise ValueError("duplicate or already published")
            if (ROOT/"posts"/p["id"]/"index.html").exists():raise ValueError("post path exists")
            ids.add(p["id"]);titles.add(nt);notices.add(nk)
            if p.get("discoveryUrl"):sourceids.add(p["discoveryUrl"])
            p.update(verified=True,verifiedOn=p["reviewedOn"],publishedDate=now.date().isoformat())
            accepted.append(p)
        except (ValueError,TypeError,KeyError) as ex:rejected.append({"id":row.get("id") if isinstance(row,dict) else None,"reason":str(ex)})
    if not accepted:return {},rejected
    files={};home=read("index.html");template=read("category/admission/index.html");sitemap=read("sitemap.xml")
    for cat in {p["category"] for p in accepted}:
        batch=[p for p in accepted if p["category"]==cat]
        pattern=r'<section class="panel" data-category="'+re.escape(cat)+r'">[\s\S]*?</section>'
        home,n=re.subn(pattern,lambda m:inject(m.group(),''.join(item(p,"./") for p in batch)),home,count=1)
        if n!=1:raise ValueError("Missing homepage panel "+cat)
        path="category/"+cat+"/index.html"
        files[path]=inject(read(path),''.join(item(p,"../../") for p in batch))
    for p in accepted:
        files["posts/"+p["id"]+"/index.html"]=render(p,template)
    db["posts"].extend(accepted)
    home=re.sub(r'<p class="launch">[\s\S]*?</p>',lambda _:'<p class="launch">'+str(len(db["posts"]))+' reviewed posts and service guides + '+str(len(directory))+' preliminary scheme entries · Updated '+now.date().isoformat()+'</p>',home,count=1)
    for key in ("department","qualification"):
        vals=sorted({p.get(key) for p in db["posts"]+directory if isinstance(p.get(key),str) and p[key]})
        home=re.sub(r'(<select id="'+key+r'"[^>]*>)[\s\S]*?</select>',lambda m:m[1]+'<option value="">All '+("departments" if key=="department" else "qualifications")+'</option>'+''.join('<option>'+e(v)+'</option>' for v in vals)+'</select>',home,count=1)
    if not all("posts/"+p["id"]+"/" in home and "posts/"+p["id"]+"/" in files["category/"+p["category"]+"/index.html"] for p in accepted):raise ValueError("Incomplete listings")
    if "</urlset>" not in sitemap:raise ValueError("Invalid sitemap")
    sitemap=sitemap.replace("</urlset>",''.join("<url><loc>"+BASE+"posts/"+p["id"]+"/</loc></url>" for p in accepted)+"</urlset>")
    files.update({"index.html":home,"sitemap.xml":sitemap,"data/posts.json":json.dumps(db,ensure_ascii=False,indent=2)+"\n"})
    return files,rejected

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--approved",default="data/import_approved.json");ap.add_argument("--output",default="import-output/publish-report.json");ap.add_argument("--write",action="store_true");args=ap.parse_args()
    rows=json.loads(Path(args.approved).read_text(encoding="utf-8"))["posts"]
    files,rejected=build(rows,dt.datetime.now(ZoneInfo("Asia/Kolkata")))
    if args.write:
        for path,content in files.items():
            dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content,encoding="utf-8")
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({"changedFiles":sorted(files),"rejected":rejected,"written":args.write},indent=2)+"\n",encoding="utf-8")
    print("Changed files:",len(files),"Skipped/rejected:",len(rejected))
