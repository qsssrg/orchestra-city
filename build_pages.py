#!/usr/bin/env python3
# LIVE collector+builder: stock=直近3日の区画タグ付き完了(+公開下限3), 往来=直近3hの非プロジェクト完了
import base64, io, json, sys, datetime as dt
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path.home()/'claudecode'))
ROOT = Path.home()/"orchestra-city"
S = ROOT/"sprites_raw"
DOCS = ROOT/"docs"
SPRITES_OUT = DOCS/"sprites"
SPRITES_OUT.mkdir(parents=True, exist_ok=True)
OUT = DOCS/"index.html"

# ===== collector =====
STOCK_DAYS=3; TRAFFIC_HOURS=3
PROJ_ID={"atlas":2,"vagante":3,"naruhodo":4,"career":5,"v-recomm":6,"gundam-null":7,"bgm":8,"司令塔":9}
RELEASED={"atlas":True,"vagante":True,"naruhodo":True,"bgm":True,"司令塔":True,"career":False,"v-recomm":False,"gundam-null":False}
# district-id (REVEAL id) -> project name / heartbeat worker
DID2PROJ={"atlas":"atlas","vagante":"vagante","naruhodo":"naruhodo","career":"career","orchestra":"司令塔","gundam":"gundam-null","bgm":"bgm","vrecomm":"v-recomm"}
HB_WORKER={"atlas":"saas-atlas-worker","vagante":"vagante-worker","naruhodo":"seo-machine-worker","career":"ai-career-worker","orchestra":"orchestra-manager","gundam":"gundam-null-worker","bgm":"bgm-yt-worker","vrecomm":"ai-art-sales-worker"}
def collect():
    try:
        import task_api as T
        tok=T.login()
        r=T.api_request('/api/tasks?filter=completed&order=desc&limit=300','GET',token=tok)
        tasks=r.get('data',[])
    except Exception as e:
        print("collector: API失敗、暫定0で継続:",str(e)[:100]); tasks=[]
    now=dt.datetime.now(dt.timezone.utc)
    def age_h(t):
        ca=t.get('completedAt') or t.get('updatedAt')
        if not ca: return 1e9
        return (now-dt.datetime.fromisoformat(ca.replace('Z','+00:00'))).total_seconds()/3600
    from collections import Counter
    d3=Counter()
    for t in tasks:
        pid=t.get('projectId')
        if pid and age_h(t)<=STOCK_DAYS*24:
            for nm,i in PROJ_ID.items():
                if i==pid: d3[nm]+=1
    traffic=sum(1 for t in tasks if not t.get('projectId') and age_h(t)<=TRAFFIC_HOURS)
    # stock per project name = max(floor, 3day count)
    stock={nm:max(3 if RELEASED.get(nm) else 0, d3.get(nm,0)) for nm in PROJ_ID}
    # alive from heartbeat freshness (<30min)
    alive={}
    hbdir=Path.home()/".claude"/"heartbeat"
    for did,w in HB_WORKER.items():
        f=hbdir/f"{w}.json"; ok=False
        try:
            j=json.loads(f.read_text()); upd=dt.datetime.fromisoformat(j['updated_at']).astimezone(dt.timezone.utc)
            ok=(now-upd).total_seconds()<1800
        except Exception: ok=False
        alive[did]=ok
    return stock, traffic, alive, d3
STOCK_BY_PROJ, TRAFFIC, ALIVE_BY_DID, D3 = collect()
print("LIVE stock:", STOCK_BY_PROJ, "traffic3h:", TRAFFIC, "alive:", {k:v for k,v in ALIVE_BY_DID.items() if v})

def prep(name, size=210):
    im=Image.open(S/f"{name}.png").convert("RGBA");px=im.load()
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a=px[x,y]
            if a<60: px[x,y]=(r,g,b,0)
    bb=im.getbbox()
    if bb: im=im.crop(bb)
    im.thumbnail((size,size),Image.LANCZOS)
    ar=round(im.size[1]/im.size[0],3)
    outp=SPRITES_OUT/f"{name}.png"
    if not outp.exists():  # sprites are static: write once
        im.save(outp,"PNG",optimize=True)
    return f"sprites/{name}.png", ar   # relative URL (Pages same-origin)

LAND=1.62; BLD=1.0; PROP=0.6; PLAZA=1.35
# layout: place[0]=landmark(back-center), place[1]=plaza(center, always from stage1), then ring buildings, then props(front)
# reveal idx→pos: 0=stage2(back-right), 1=stage3(back-left), 2=stage4(front-left・広場の"前"に置き高さを合わせる), 3+=sides
RING=[(1.25,-0.45),(-1.25,-0.45),(-0.75,1.02),(1.62,0.18),(0.8,1.0),(-1.62,0.18)]
PROPP=[(0,1.15),(-0.55,1.28),(0.55,1.3)]
OVR={"bgm":{"land_dy":-1.55,"plaza_dy":0.6},
     "gundam":{"ring":[(1.7,0.05),(-1.55,0.15),(1.15,0.85)],"props":[(-1.25,0.95),(0.15,1.35),(1.35,1.05)]}}
# (id, nm, gx, gy, stock, alive, active, land, plaza, ring[], props[], theme)
REVEAL=[
 ("atlas","atlas",0,0,5,False,False,"atlas_senate","atlas_plaza",["atlas_towerB","atlas_spire","atlas_bridge"],["atlas_falcon"],"コルサント（洗練未来都市）"),
 ("naruhodo","naruhodo",7,0,2,True,False,"naruhodo_holotower","naruhodo_plaza",["naruhodo_towerB","naruhodo_alley","naruhodo_rooftop","naruhodo_ramen"],["naruhodo_tachikoma"],"サイバーパンク（攻殻）"),
 ("career","career",14,0,2,False,False,"career_castle","career_fountain",["career_tavern","career_guild","career_stable","career_training"],[],"中世ファンタジー"),
 ("vagante","vagante",0,7,3,True,False,"hall","vagante_plaza",["stage","neon","record"],[],"ミュージックタウン"),
 ("orchestra","司令塔",7,7,3,True,True,"shireitou_mountain","orchestra_plaza",["shireitou_cabin","shireitou_forest","shireitou_forest"],[],"シンボルの山・大自然"),
 ("gundam","gundam-null",14,7,1,False,False,"gundam_dock","gundam_plaza",["gundam_hangar","gundam_gantry"],["gundam_guncannon","gundam_guntank","gundam_corebooster"],"スペースコロニー ドック"),
 ("bgm","bgm",0,14,1,False,False,"bgm_keep","bgm_plaza",["bgm_teahouse","bgm_torii"],[],"和風（天守閣・庭園）"),
 ("vrecomm","v-recomm",7,14,0,False,False,"vrecomm_stage","vrecomm_plaza",["vrecomm_booth","vrecomm_merch","vrecomm_ministage"],["vrecomm_idol"],"アイドルイベント会場"),
]
DIST=[]; need=set()
for id_,nm,gx,gy,stock,alive,active,land,plaza,ring,props,theme in REVEAL:
    o=OVR.get(id_,{})
    place=[[land,0,o.get("land_dy",-1.15),LAND],[plaza,0,o.get("plaza_dy",0.15),PLAZA]]; need.add(land); need.add(plaza)
    rpos=o.get("ring",RING)
    for i,b in enumerate(ring):
        dx,dy=rpos[i%len(rpos)]; place.append([b,dx,dy,BLD]); need.add(b)
    ppos=o.get("props",PROPP)
    for i,p in enumerate(props):
        dx,dy=ppos[i%len(ppos)]; place.append([p,dx,dy,PROP]); need.add(p)
    # ---- LIVE override ----
    projname=DID2PROJ[id_]
    cap=len(place)-1
    live_stock=min(STOCK_BY_PROJ.get(projname,0), cap)
    live_alive=ALIVE_BY_DID.get(id_, False)
    DIST.append({"id":id_,"nm":nm,"theme":theme,"gx":gx,"gy":gy,"stock":live_stock,"alive":live_alive,"active":False,"place":place,"released":RELEASED.get(projname,False)})
SPR={};AR={}
for k in sorted(need):
    d,ar=prep(k);SPR[k]=d;AR[k]=ar
CFG={"SPR":SPR,"AR":AR,"DIST":DIST,"traffic":TRAFFIC,"gen":dt.datetime.now().astimezone().strftime("%m/%d %H:%M")}

HTML=r"""<title>Orchestra City — themepark（全8区画）</title>
<style>
 :root{--ink:#1C2431;--muted:#57647A;--faint:#8A96AA;--gold:#C77F1A;--line:#D4DCE7;--bg:#CFE0F0;}
 :root[data-theme="dark"]{--ink:#E7ECF3;--muted:#93A0B4;--faint:#66738A;--gold:#E8B23A;--line:#232C3A;--bg:#0D131C;}
 @media(prefers-color-scheme:dark){:root{--ink:#E7ECF3;--muted:#93A0B4;--faint:#66738A;--gold:#E8B23A;--line:#232C3A;--bg:#0D131C;}}
 :root[data-theme="light"]{--ink:#1C2431;--muted:#57647A;--faint:#8A96AA;--gold:#C77F1A;--line:#D4DCE7;--bg:#CFE0F0;}
 *{box-sizing:border-box}html,body{margin:0}
 body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Yu Gothic",system-ui,sans-serif}
 .wrap{max-width:1360px;margin:0 auto;padding:20px 16px 46px}
 .eyebrow{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);font-weight:700;display:flex;gap:8px;align-items:center}
 .eyebrow::before{content:"";width:20px;height:1.5px;background:var(--gold)}
 h1{font-size:clamp(21px,5vw,31px);margin:7px 0 3px;letter-spacing:-.02em;font-weight:800}
 .sub{color:var(--muted);font-size:13px;margin-bottom:14px;max-width:72ch}
 .stage{position:relative;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 12px 44px rgba(20,40,70,.2)}
 canvas{display:block;width:100%;height:auto;image-rendering:pixelated}
 .hud{position:absolute;left:12px;top:11px;display:flex;gap:15px;background:rgba(255,255,255,.72);backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,.6);border-radius:12px;padding:8px 13px;pointer-events:none}
 :root[data-theme="dark"] .hud{background:rgba(15,20,30,.62);border-color:rgba(255,255,255,.08)}
 .hud .v{font-size:20px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}.hud .k{font-size:10px;color:var(--muted);margin-top:3px}
 .live{position:absolute;right:12px;top:12px;display:flex;align-items:center;gap:7px;background:rgba(199,127,26,.15);border:1px solid rgba(199,127,26,.42);color:var(--gold);font-size:11px;font-weight:700;padding:5px 10px;border-radius:999px}
 .live .b{width:8px;height:8px;border-radius:50%;background:var(--gold);animation:bl 1.6s infinite}@keyframes bl{0%,100%{opacity:1}50%{opacity:.25}}
 @media(prefers-reduced-motion:reduce){.live .b{animation:none}}
 .panel{margin-top:14px;background:rgba(255,255,255,.5);border:1px solid var(--line);border-radius:12px;padding:12px 15px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
 :root[data-theme="dark"] .panel{background:rgba(20,26,36,.5)}
 .panel label{font-size:12.5px;font-weight:700}
 input[type=range]{flex:1;min-width:200px;accent-color:var(--gold)}
 .btn{border:1px solid var(--line);background:var(--bg);color:var(--muted);font:inherit;font-size:12px;font-weight:700;padding:6px 11px;border-radius:8px;cursor:pointer}
 .cap{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;min-width:88px}
 .legend{display:flex;gap:13px;flex-wrap:wrap;margin-top:12px;font-size:11.5px;color:var(--muted)}
 .tip{position:fixed;z-index:20;background:#0A0E14;color:#EAEDF3;border:1px solid #28303c;font-size:12px;padding:8px 11px;border-radius:9px;pointer-events:none;opacity:0;transition:opacity .12s;max-width:240px;box-shadow:0 8px 26px rgba(0,0,0,.4)}
 .tip .r{color:#E8B23A;font-weight:700}
 footer{margin-top:18px;color:var(--faint);font-size:12px;text-align:center;line-height:1.7}footer b{color:var(--muted)}
</style>
<div class="wrap">
 <div class="eyebrow">Orchestra Observability · themepark city · API sprites</div>
 <h1>オーケストラ・シティ 🎡</h1>
 <p class="sub">実データ駆動。<b>段階</b>＝直近3日の区画タグ付き完了タスク（＋公開済みは下限3）、<b>往来(車/人)</b>＝直近3時間の非プロジェクト完了タスク数。放置すると段階も往来も減る。灯り＝ワーカー稼働。</p>
 <div class="stage"><canvas id="c"></canvas>
   <div class="hud"><div><div class="v" id="hB">0</div><div class="k">累積成果</div></div><div><div class="v" id="hL">0</div><div class="k">灯る区画</div></div><div><div class="v" id="hT">0</div><div class="k">往来(3h)</div></div></div>
   <div class="live"><span class="b"></span><span id="lt">建設中 1</span></div>
 </div>
 <div class="panel"><label>🏗 成長プレビュー</label><input type="range" id="grow" min="0" max="6" value="0"><span class="cap" id="growcap">実データ</span><button class="btn" id="real">実データに戻す</button></div>
 <div class="legend"><span>🎵vagante ♦ 🏯bgm ♦ 🌆atlas ♦ 🌃naruhodo ♦ ⚔career ♦ 💡v-recomm ♦ 🚀gundam ♦ 🏔司令塔</span></div>
 <footer id="ft"><b>実データ駆動プロトタイプ。</b>タスクを各区画projectにタグ付けするほど街が育ちます。</footer>
</div>
<div class="tip" id="tip"></div>
<script>
const CFG=__CFG__;const {SPR,AR,DIST}=CFG;
const imgs={};Object.keys(SPR).forEach(k=>{const im=new Image();im.src=SPR[k];imgs[k]=im;});
const cv=document.getElementById("c"),ctx=cv.getContext("2d"),tip=document.getElementById("tip");
const RM=matchMedia("(prefers-reduced-motion:reduce)").matches;
const isDark=()=>{const t=document.documentElement.getAttribute("data-theme");if(t)return t==="dark";return matchMedia("(prefers-color-scheme:dark)").matches;};
let W,H,TW,TH,OX,OY,SC;
function resize(){const cssW=Math.min(cv.parentElement.clientWidth,1328),cssH=Math.round(cssW*0.66);
 const DPR=Math.min(devicePixelRatio||1,2);cv.width=cssW*DPR;cv.height=cssH*DPR;cv.style.height=cssH+"px";ctx.setTransform(DPR,0,0,DPR,0,0);
 W=cssW;H=cssH;SC=cssW/1328;TW=76*SC;TH=38*SC;OX=W/2;OY=H*0.26;}
const iso=(gx,gy)=>[OX+(gx-gy)*TW/2,OY+(gx+gy)*TH/2];
let GROW=0;function dcount(d){const base=d.stock===0?0:Math.min(d.stock+1,d.place.length);return GROW>0?Math.min(GROW+1,d.place.length):base;}
document.getElementById("hL").textContent=DIST.filter(d=>d.alive).length+"/"+DIST.length;
document.getElementById("hT").textContent=(CFG.traffic||0);
document.getElementById("ft").innerHTML+=" ｜ 生成 "+(CFG.gen||"");
document.getElementById("lt").textContent="建設中 "+DIST.filter(d=>d.active).length;
function updHUD(){document.getElementById("hB").textContent=DIST.reduce((a,d)=>a+dcount(d),0);}
const loop=[[3.5,-3],[10.5,-3],[10.5,17.5],[3.5,17.5]];
function llen(p){let L=0;for(let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%p.length];L+=Math.hypot(b[0]-a[0],b[1]-a[1]);}return L;}
const LP=llen(loop);const carC=["#E24A3A","#3E7BC4","#2FA36B","#E8B23A","#8A5AD0"];
const TRAF=CFG.traffic||0;
const NCAR=Math.max(1,Math.min(TRAF+1,16));       // 直近3hの非プロジェクト処理数で往来量
const NPPL=Math.max(2,Math.min(TRAF*2+2,28));
const cars=[];for(let i=0;i<NCAR;i++)cars.push({s:LP/NCAR*i,sp:0.4+0.12*(i%3),bus:i%5===0,col:carC[i%5]});
const ppl=[];for(let i=0;i<NPPL;i++)ppl.push({s:LP/NPPL*i,sp:0.16+0.05*(i%3),lane:(i%2?1:-1),col:["#333","#E24A3A","#3E7BC4","#7A5230","#8A5AD0"][i%5]});
function onloop(s){let ss=((s%LP)+LP)%LP;for(let i=0;i<loop.length;i++){const a=loop[i],b=loop[(i+1)%loop.length];const d=Math.hypot(b[0]-a[0],b[1]-a[1]);if(ss<=d){const u=ss/d;return[a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u];}ss-=d;}return loop[0];}
let trainX=-4;
function pgon(pts,fill,st){ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0],pts[i][1]);ctx.closePath();ctx.fillStyle=fill;ctx.fill();if(st){ctx.strokeStyle=st;ctx.lineWidth=1;ctx.stroke();}}
function ground(dark){const LO=-3,HI=18;
 pgon([iso(LO,LO),iso(HI,LO),iso(HI,HI),iso(LO,HI)],dark?"#141b12":"#8FBF6A");
 const road=dark?"#333b47":"#727C89",HW=0.42;
 [3.5,10.5].forEach(x=>pgon([iso(x-HW,LO),iso(x+HW,LO),iso(x+HW,HI),iso(x-HW,HI)],road));
 [3.5,10.5].forEach(y=>pgon([iso(LO,y-HW),iso(HI,y-HW),iso(HI,y+HW),iso(LO,y+HW)],road));
 ctx.strokeStyle=dark?"#5a6472":"#E7C558";ctx.lineWidth=1.3*SC;ctx.setLineDash([8*SC,10*SC]);
 [3.5,10.5].forEach(x=>{const s=iso(x,LO),e=iso(x,HI);ctx.beginPath();ctx.moveTo(s[0],s[1]);ctx.lineTo(e[0],e[1]);ctx.stroke();});
 [3.5,10.5].forEach(y=>{const s=iso(LO,y),e=iso(HI,y);ctx.beginPath();ctx.moveTo(s[0],s[1]);ctx.lineTo(e[0],e[1]);ctx.stroke();});
 ctx.setLineDash([]);
 pgon([iso(LO,17.2-.16),iso(HI,17.2-.16),iso(HI,17.2+.16),iso(LO,17.2+.16)],dark?"#463d33":"#8A7B6E");}
function pad(d,dark){const R=2.4;pgon([iso(d.gx-R,d.gy-R),iso(d.gx+R,d.gy-R),iso(d.gx+R,d.gy+R),iso(d.gx-R,d.gy+R)],dark?"rgba(255,255,255,.03)":"rgba(255,255,255,.12)",dark?"rgba(255,255,255,.05)":"rgba(80,100,120,.12)");}
function sprite(key,gx,gy,scale){const im=imgs[key];if(!im||!im.complete)return;const w=TW*scale*1.15,h=w*(AR[key]||1);const[cx,cy]=iso(gx,gy);ctx.drawImage(im,cx-w/2,cy-h+TH*0.34,w,h);}
function car(v,dark){const[gx,gy]=onloop(v.s);const[x,y]=iso(gx,gy);const w=(v.bus?9:6)*SC,h=(v.bus?5:4)*SC;
 ctx.fillStyle="rgba(0,0,0,.16)";ctx.beginPath();ctx.ellipse(x,y+2*SC,w*.9,h*.5,0,0,7);ctx.fill();
 ctx.fillStyle=v.bus?"#F2B21E":v.col;ctx.fillRect(x-w/2,y-h,w,h);ctx.fillStyle="rgba(255,255,255,.5)";ctx.fillRect(x-w/2,y-h,w,h*.4);}
function person(p){const[gx,gy]=onloop(p.s);const[x,y]=iso(gx+p.lane*0.18,gy-p.lane*0.18);
 ctx.fillStyle="rgba(0,0,0,.14)";ctx.beginPath();ctx.ellipse(x,y,2.2*SC,1.1*SC,0,0,7);ctx.fill();
 ctx.fillStyle=p.col;ctx.fillRect(x-1.3*SC,y-6*SC,2.6*SC,6*SC);ctx.beginPath();ctx.arc(x,y-7.2*SC,1.6*SC,0,7);ctx.fill();}
let t0=performance.now(),last=t0;
function frame(now){const t=(now-t0)/1000,dt=Math.min(.05,(now-last)/1000);last=now;const dark=isDark();
 ctx.imageSmoothingEnabled=false;ctx.clearRect(0,0,W,H);
 const sky=ctx.createLinearGradient(0,0,0,H*.55);if(dark){sky.addColorStop(0,"#0D131C");sky.addColorStop(1,"#1b2636");}else{sky.addColorStop(0,"#AFD6F2");sky.addColorStop(1,"#DCEBDA");}
 ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);
 ground(dark);DIST.forEach(d=>pad(d,dark));
 cars.forEach(c=>c.s+=c.sp*dt*(RM?0:1));
 ppl.forEach(p=>p.s+=p.sp*dt*(RM?0:1));
 const obj=[];
 DIST.forEach(d=>{const n=dcount(d);
   if(d.active){const[gx,gy]=iso(d.gx,d.gy);const pulse=RM?.5:.5+.5*Math.sin(t*2);const rad=ctx.createRadialGradient(gx,gy,0,gx,gy,TW*2.1);rad.addColorStop(0,`rgba(232,178,58,${.15+.1*pulse})`);rad.addColorStop(1,"rgba(232,178,58,0)");ctx.fillStyle=rad;ctx.beginPath();ctx.ellipse(gx,gy,TW*2.1,TH*2.1,0,0,7);ctx.fill();}
   if(n===0){const[gx,gy]=iso(d.gx,d.gy);ctx.setLineDash([7*SC,6*SC]);ctx.strokeStyle=dark?"#5a6472":"#6f7d8b";ctx.lineWidth=1.8;const s=1.9;pgon([iso(d.gx-s,d.gy-s),iso(d.gx+s,d.gy-s),iso(d.gx+s,d.gy+s),iso(d.gx-s,d.gy+s)],"rgba(0,0,0,0)",dark?"#5a6472":"#6f7d8b");ctx.setLineDash([]);return;}
   for(let i=0;i<n&&i<d.place.length;i++){const[key,dx,dy,sc]=d.place[i];obj.push({k:(d.gx+dx)+(d.gy+dy),f:()=>sprite(key,d.gx+dx,d.gy+dy,sc)});}
 });
 cars.forEach(c=>{const[gx,gy]=onloop(c.s);obj.push({k:gx+gy+0.01,f:()=>car(c,dark)});});
 ppl.forEach(p=>{const[gx,gy]=onloop(p.s);obj.push({k:gx+gy+0.02,f:()=>person(p)});});
 obj.sort((a,b)=>a.k-b.k);obj.forEach(o=>o.f());
 trainX+=RM?0:0.032;if(trainX>19)trainX=-5;
 for(let k=0;k<4;k++){const gx=trainX-k*0.9;if(gx<-4||gx>18.5)continue;const[x,y]=iso(gx,17.2);ctx.fillStyle=k===0?"#D8503A":"#C64536";ctx.fillRect(x-9*SC,y-9*SC,18*SC,9*SC);ctx.fillStyle="rgba(180,220,255,.85)";ctx.fillRect(x-7*SC,y-7*SC,14*SC,3.4*SC);}
 DIST.forEach(d=>{const[lx,ly]=iso(d.gx,d.gy);const yy=ly+TH*2.3;
   ctx.font=`${12*SC|0}px -apple-system,system-ui,sans-serif`;ctx.textAlign="center";
   ctx.strokeStyle=dark?"rgba(0,0,0,.55)":"rgba(255,255,255,.85)";ctx.lineWidth=3.4*SC;ctx.strokeText(d.nm,lx,yy);
   ctx.fillStyle=dark?"#E7ECF3":"#1C2431";ctx.fillText(d.nm,lx,yy);
   if(!d.alive&&dcount(d)>0){ctx.fillStyle=dark?"#E0674E":"#C2452F";ctx.fillText("●停止",lx,yy+13*SC);}});
 updHUD();requestAnimationFrame(frame);}
addEventListener("resize",resize);resize();requestAnimationFrame(frame);
const grow=document.getElementById("grow"),growcap=document.getElementById("growcap");
grow.oninput=()=>{GROW=+grow.value;growcap.textContent=GROW===0?"実データ":("全区画 "+GROW+" 段階");};
document.getElementById("real").onclick=()=>{GROW=0;grow.value=0;growcap.textContent="実データ";};
cv.addEventListener("mousemove",e=>{const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let best=null,bd=1e9;
 DIST.forEach(d=>{const[cx,cy]=iso(d.gx,d.gy);const dd=Math.hypot(cx-mx,cy-my);if(dd<bd){bd=dd;best=d;}});
 if(best&&bd<TW*1.4){tip.style.opacity=1;tip.innerHTML=`<b style="color:#fff">${best.nm}</b> <span class="r">${best.active?"建設中●":best.alive?"稼働":dcount(best)===0?"更地":"停止"}</span><br>${best.theme}<br>${dcount(best)===0?"更地":"建物 "+Math.max(0,dcount(best)-1)+" 棟＋広場"}`;tip.style.left=Math.min(e.clientX+12,innerWidth-250)+"px";tip.style.top=(e.clientY+14)+"px";}else tip.style.opacity=0;});
cv.addEventListener("mouseleave",()=>tip.style.opacity=0);
</script>"""
HTML=HTML.replace("__CFG__", json.dumps(CFG, ensure_ascii=False))
OUT.write_text(HTML);print("wrote",OUT,len(HTML)//1024,"KB")
