"""Discover notice URLs and possible official links; never publish third-party articles."""
import argparse, datetime as dt, json, re, time, urllib.request, urllib.parse, urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE="https://sarkariresult.com.cm/"
UA="SarkariAlertDiscovery/1.0"
HOST="sarkariresult.com.cm"
PAGES={"latest-jobs":"latest-jobs/","results":"result/","admit-card":"admit-card/","answer-key":"answer-key/","admission":"admission/","documents":"document-verification/","10th-iti":"10th-iti-job/","outsourcing":"outsoursing-sewa-yojana-job/","syllabus":"syllabus/"}
EXCLUDED=set(PAGES.values())|{"","contact/","contact-us/","privacy-policy/","disclaimer/","about-us/","about/","more/","feed/","sarkari-result/","wp-login.php"}
ALLOWED={"www.ibps.in","ibps.in","www.rrbapply.gov.in","www.joinindiannavy.gov.in","www.joinindianarmy.nic.in","www.aees.gov.in","www.sidbi.in","sidbi.in","sbi.co.in","www.sbi.co.in","bank.sbi","www.bank.sbi","www.joinindiancoastguard.gov.in","www.clat2027.consortiumofnlus.ac.in","clat2027.consortiumofnlus.ac.in","exams.nta.ac.in","www.nielit.gov.in","www.nielit.in","student.nielit.gov.in","eshram.gov.in","pmuy.gov.in","pmsuryaghar.gov.in","www.pmuy.gov.in"}
def official(url):
    try:
        u=urllib.parse.urlsplit(url)
        h=(u.hostname or "").lower()
        return u.scheme=="https" and u.username is None and u.password is None and u.port in (None,443) and (h in ALLOWED or h.endswith((".gov.in",".nic.in",".ac.in"))) and h not in {"gov.in","nic.in","ac.in"}
    except ValueError:return False

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.links=[];self.current=None;self.depth=0
    def handle_starttag(self,tag,attrs):
        if tag=="li":self.depth+=1
        if tag=="a":
            self.current=(dict(attrs).get("href",""),self.depth>0)
    def handle_endtag(self,tag):
        if tag=="li":self.depth=max(0,self.depth-1)
        if tag=="a" and self.current:
            self.links.append(self.current);self.current=None

class SameHost(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urllib.parse.urlsplit(newurl).hostname!=HOST or urllib.parse.urlsplit(newurl).scheme!="https":
            raise ValueError("External or non-HTTPS redirect")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url):
    request=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,text/plain"})
    with urllib.request.build_opener(SameHost()).open(request,timeout=20) as r:
        raw=r.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("Page too large")
        return raw.decode(r.headers.get_content_charset() or "utf-8",errors="replace")

def article_url(href,base=BASE):
    u=urllib.parse.urlsplit(urllib.parse.urljoin(base,href))
    path=u.path.strip("/")+"/"
    if u.hostname!=HOST or u.scheme!="https" or path in EXCLUDED or not re.fullmatch(r"[a-z0-9][a-z0-9-]{5,}/",path):return None
    if not re.search(r"20(?:2[0-9]|3[0-9])|recruitment|result|admit|answer|yojana|scholarship|apprentice|online-form",path):return None
    return BASE+path

def discover(limit):
    rp=urllib.robotparser.RobotFileParser()
    rp.set_url(BASE+"robots.txt")
    rp.parse(fetch(BASE+"robots.txt").splitlines())
    found={}; errors=[]
    for cat,path in PAGES.items():
        url=BASE+path
        if not rp.can_fetch(UA,url):errors.append({"url":url,"error":"robots disallowed"});continue
        try:
            a=Anchors();a.feed(fetch(url))
            for href,in_list in a.links:
                if not in_list:continue
                link=article_url(href,url)
                if link:
                    row=found.setdefault(link,{"sourceUrl":link,"sourceSlug":link.rstrip("/").split("/")[-1],"categories":[],"officialLinkCandidates":[],"status":"pending_review"})
                    if cat not in row["categories"]:row["categories"].append(cat)
        except Exception as e:errors.append({"url":url,"error":str(e)})
        time.sleep(1.2)
    # Only inspect a bounded number of pages for outgoing official link candidates.
    # No third-party article body, title or description is retained.
    for row in list(found.values())[:limit]:
        url=row["sourceUrl"]
        if not rp.can_fetch(UA,url):continue
        try:
            a=Anchors();a.feed(fetch(url))
            row["officialLinkCandidates"]=sorted({urllib.parse.urljoin(url,h) for h,_ in a.links if official(urllib.parse.urljoin(url,h))})[:30]
        except Exception as e:row["inspectionError"]=str(e)
        time.sleep(1.2)
    existing=json.loads((ROOT/"data/posts.json").read_text(encoding="utf-8"))["posts"]
    imported={p.get("discoveryUrl") for p in existing if p.get("discoveryUrl")}
    return {"checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),"source":BASE,"candidates":[r for u,r in found.items() if u not in imported],"errors":errors,"sourcePages":PAGES,"publishedCount":len(existing)}

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--output",default="import-output/discovery.json");ap.add_argument("--inspect",type=int,default=20);args=ap.parse_args()
    result=discover(max(0,min(40,args.inspect)))
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Discovered",len(result["candidates"]),"candidate URLs;",len(result["errors"]),"source errors")
    if not result["candidates"]:raise SystemExit("No candidates: check source access or parser; do not assume no updates.")
