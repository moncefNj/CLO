#!/usr/bin/env python3
"""
record_demo_video.py -- record the CLO Studio walkthrough video (silent, captioned).

Drives examples/demo/clo_studio.html with Playwright (headless Chromium), overlays captions
and a pointer, records the session and converts it to MP4 with ffmpeg.

  pip install playwright && playwright install chromium     # once
  python3 tools/record_demo_video.py --out demo/clo_studio_demo.mp4
"""
import argparse
import os
import shutil
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "examples", "demo", "clo_studio.html")
W, H = 1366, 820

OVERLAY = r"""
(() => {
  const s = document.createElement('style');
  s.textContent = `
  #vcap{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);max-width:1050px;z-index:99999;
        background:rgba(12,20,24,.92);color:#fff;font:500 19px/1.45 system-ui,sans-serif;padding:12px 20px;
        border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.25);transition:opacity .25s}
  #vcap b{color:#7fe0d6}
  #vptr{position:fixed;left:0;top:0;width:22px;height:22px;border-radius:50%;z-index:99998;pointer-events:none;
        background:rgba(194,65,12,.85);border:2px solid #fff;box-shadow:0 0 0 3px rgba(194,65,12,.35);
        transition:transform .7s cubic-bezier(.3,.7,.3,1)}
  .vhl{outline:3px solid #C2410C !important;outline-offset:3px;border-radius:6px}
  #vcard{position:fixed;inset:0;z-index:100000;background:#0E1417;color:#E4ECE9;display:flex;flex-direction:column;
         align-items:center;justify-content:center;gap:14px;font:500 22px/1.5 system-ui,sans-serif;text-align:center;padding:40px}
  #vcard h1{font:600 46px/1.15 system-ui,sans-serif;margin:0;color:#fff}
  #vcard .m{color:#4CC0B5;font:500 18px ui-monospace,monospace}`;
  document.head.appendChild(s);
  const c = document.createElement('div'); c.id='vcap'; c.style.opacity=0; document.body.appendChild(c);
  const p = document.createElement('div'); p.id='vptr'; p.style.transform='translate(680px,420px)'; document.body.appendChild(p);
})();
"""


def run(out, repo, authors):
    tmp = tempfile.mkdtemp()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=tmp,
                            record_video_size={"width": W, "height": H})
        pg = ctx.new_page()
        pg.goto("file://" + PAGE)
        pg.wait_for_timeout(400)
        pg.evaluate(OVERLAY)

        def card(title, lines, ms):
            pg.evaluate("""([t,l])=>{let c=document.getElementById('vcard'); if(!c){c=document.createElement('div');c.id='vcard';document.body.appendChild(c);}
                c.innerHTML='<h1>'+t+'</h1>'+l.map(x=>'<div>'+x+'</div>').join(''); c.style.display='flex';}""", [title, lines])
            pg.wait_for_timeout(ms)
            pg.evaluate("()=>{const c=document.getElementById('vcard'); if(c) c.style.display='none';}")

        def cap(text, ms=0):
            pg.evaluate("t=>{const c=document.getElementById('vcap'); c.innerHTML=t; c.style.opacity=t?1:0;}", text)
            if ms:
                pg.wait_for_timeout(ms)

        def point(sel, click=True, hl=True, ms=900):
            el = pg.locator(sel).first
            el.scroll_into_view_if_needed()
            bb = el.bounding_box()
            if bb:
                pg.evaluate("([x,y])=>{document.getElementById('vptr').style.transform=`translate(${x}px,${y}px)`}",
                            [bb["x"] + min(bb["width"] / 2, 60) - 11, bb["y"] + bb["height"] / 2 - 11])
            pg.wait_for_timeout(ms)
            if hl:
                pg.evaluate("()=>document.querySelectorAll('.vhl').forEach(e=>e.classList.remove('vhl'))")
                el.evaluate("e=>e.classList.add('vhl')")
            if click:
                el.click()
                pg.wait_for_timeout(350)
                pg.evaluate("()=>{const p=document.getElementById('vptr');p.style.boxShadow='0 0 0 12px rgba(194,65,12,.15)';"
                            "setTimeout(()=>p.style.boxShadow='0 0 0 3px rgba(194,65,12,.35)',300)}")

        def unhl():
            pg.evaluate("()=>document.querySelectorAll('.vhl').forEach(e=>e.classList.remove('vhl'))")

        def scroll_to(sel, block="start"):
            pg.locator(sel).first.evaluate("(e,b)=>e.scrollIntoView({behavior:'smooth',block:b})", block)
            pg.wait_for_timeout(900)

        sub = "ICSOC 2026 · Demonstrations and Resources" + (f" · {authors}" if authors else "")
        card("CLO Studio", ["Explaining and repairing multi-cloud tag governance findings",
                            f"<span class='m'>{sub}</span>"], 5000)
        cap("Cloud tags are written by one team and read by others: FinOps needs a <b>cost-center</b>, Security a "
            "<b>data-classification</b>, Operations an <b>owner</b> and an <b>environment</b>.", 6000)
        cap("Existing tools report <i>that</i> a key is missing. CLO Studio answers four questions: why is it required "
            "and for whom, is it really missing, may it be filled in, and with what?", 7000)
        # inputs
        point("#t-inputs")
        cap("The page is generated from two plain files: an <b>organisation file</b> (roles, the keys they need, "
            "policies, teams, value sources) and an <b>inventory</b> (one row per resource).", 7500)
        scroll_to("#p-inputs .pipe", "center")
        cap("Each component's input and output: the ontology reasoner derives what each resource requires, the "
            "audit reports findings, the planner proposes repairs, the compiler emits provider policies.", 8000)
        scroll_to("#incode", "center")
        point("#p-inputs .chip[data-f='inventory.csv']", ms=500)
        cap("Ten resources on AWS, Azure and GCP, four teams. With your own two files, one command rebuilds the page.", 6500)
        unhl()
        pg.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pg.wait_for_timeout(600)
        point("#t-audit", hl=False)
        # guided scenario
        cap("A guided scenario: <b>a FinOps analyst</b> preparing the monthly chargeback report.", 4500)
        steps = [
            ("#step-1", "<b>1 · Your backlog.</b> View the estate as FinOps: only resources with a FinOps finding stay "
                        "highlighted; 3 of the 8 governed resources carry cost-center.", 7000),
            ("#step-2", "<b>2 · Why is cost-center required?</b> The shared standard reaches the bucket through its "
                        "account and the company (chain C-4); FinOps needs the key (chain C-9).", 8000),
            ("#step-3", "<b>3 · Is it really missing?</b> vol-scratch came from a listing that never returns tags: "
                        "CLO concludes nothing and re-reads it.", 7000),
            ("#step-4", "<b>4 · Can it be filled in?</b> cost-center declares the team's value as a source and Payments "
                        "writes CC-1001: a proposal with a dry-run command. data-classification is never guessed.", 8500),
            ("#step-5", "<b>5 · What if values were guessed?</b> Team-majority repairs fill 11 values instead of 1, "
                        "including a data-classification copied from the team's habit.", 8000),
            ("#step-6", "<b>6 · Enforce.</b> The derived standard compiled into AWS Config, Azure Policy and Cloud "
                        "Custodian; the team policy stays in CLO's audit.", 7000),
        ]
        for sel, text, ms in steps:
            pg.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pg.wait_for_timeout(400)
            point(sel, ms=600)
            cap(text)
            if sel in ("#step-2", "#step-4", "#step-5"):
                pg.wait_for_timeout(1200)
                pg.evaluate("()=>{const e=document.querySelector('.finding.focus'); if(e) e.scrollIntoView({behavior:'smooth',block:'center'})}")
            elif sel == "#step-3":
                scroll_to("#detail")
            pg.wait_for_timeout(ms)
        unhl()
        # free exploration
        pg.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pg.wait_for_timeout(600)
        point("#t-audit", hl=False)
        point("#sw-role", ms=600)
        cap("Beyond the tour: what if a <b>Sustainability</b> role joins? Error findings go from 17 to 23 and "
            "<b>carbon-scope</b> joins the derived standard: one line in the organisation file, no rule edited.", 8000)
        point("#sw-role", hl=False)
        point("#sw-closure", ms=600)
        cap("<b>Close the world everywhere</b>, as an export-based check does: vol-scratch becomes 'unlabelled', a "
            "finding the provider response gives no evidence for.", 7500)
        point("#sw-closure", hl=False)
        unhl()
        point("#t-loop")
        cap("<b>Closed loop</b> over 8 simulated cycles: team-majority repairs close as many findings but write "
            "<b>778</b> silently wrong values, against <b>16</b>.", 7500)
        point("#t-corpus")
        cap("<b>Open corpus</b>: 1,686 resources recorded from AWS, Azure and GCP; completeness is derived from the shape "
            "of each response.", 7000)
        cap("", 0)
        unhl()
        card("Try it", ["One self-contained HTML file: no server, no cloud credentials.",
                        "<span class='m'>python3 tools/clo_demo.py --org organisation.yaml --inventory inventory.csv</span>",
                        f"<span class='m'>{repo}</span>"], 6500)
        pg.close()
        ctx.close()
        b.close()
    webm = next(os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".webm"))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if out.endswith(".webm"):
        shutil.copy(webm, out)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", webm, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-preset", "slow", "-crf", "22", "-movflags", "+faststart", out], check=True)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "demo", "clo_studio_demo.mp4"))
    ap.add_argument("--repo", default="Code, data and this page: the artefact repository (see the paper)")
    ap.add_argument("--authors", default="", help="shown on the title card")
    a = ap.parse_args()
    run(a.out, a.repo, a.authors)
