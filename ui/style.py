"""The app's CSS -- injected once per run. Ported from the design mockups (dark, rounded, rings)."""

import streamlit as st

_CSS = """
<style>
:root{
  --bg:#0e1117;--surface:#191c24;--surface2:#20242e;--inset:#12151c;--border:#2a2f3a;
  --text:#e8e8ea;--muted:#9aa0ac;--faint:#6b7280;--purple:#8b6dff;
  --cash:#34d399;--invest:#f5b642;--debt:#ef4444;
  --disp:"Inter",system-ui,sans-serif;--body:"Inter",system-ui,sans-serif;
}
/* Streamlit chrome */
[data-testid="stToolbar"],footer{display:none}
.stApp{background:radial-gradient(1000px 500px at 80% -10%,rgba(139,109,255,.10),transparent 60%),#0e1117}
.block-container{padding-top:1.4rem;max-width:1180px}
html,body,[class*="css"]{font-family:var(--body)}
.stButton>button{border-radius:12px;font-family:var(--disp);font-weight:600;border:1px solid var(--border)}
.stButton>button:hover{border-color:var(--purple)}
h1,h2,h3{font-family:var(--disp);letter-spacing:-.02em}

.apphead{font-family:var(--disp);font-weight:600;font-size:15px;color:var(--muted);margin-bottom:14px}
.apphead b{color:var(--text)}
.amsg{font-size:13px;color:var(--muted);margin:6px 0 10px}
.amsg b{color:var(--cash);font-family:var(--disp)}

/* action dialogs (modals) */
.dlgcash{font-size:12.5px;color:var(--muted);margin-bottom:12px}
.dlgcash b{color:var(--cash);font-family:var(--disp)}
.hpreview{display:flex;align-items:center;gap:10px;margin:14px 0 2px;background:var(--inset);
  border:1px solid var(--border);border-radius:12px;padding:11px 13px;font-size:13px;color:var(--muted)}
.hpreview b{margin-left:auto;font-family:var(--disp);font-weight:700;font-size:18px;color:#38bdf8}

/* rings rail */
.rail{background:#0b0d12;border:1px solid #20242e;border-radius:16px;padding:16px 12px;display:flex;flex-direction:column;gap:4px}
.railcap{font-family:var(--disp);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);text-align:center;margin-bottom:6px}
.ringitem{position:relative;display:flex;align-items:center;gap:12px;padding:8px 6px;border-radius:12px}
.ringitem:hover{background:#12151c}
.ring{position:relative;width:70px;height:70px;flex:none}
.ring svg{transform:rotate(-90deg)}
.ring .rc{position:absolute;inset:0;display:grid;place-content:center;text-align:center}
.ring .rv{font-family:var(--disp);font-weight:700;font-size:13px}
.rmeta .rn{font-size:13px;font-weight:600}
.tip{position:absolute;right:calc(100% + 8px);top:50%;transform:translateY(-50%) translateX(6px);width:210px;
  background:#0f1218;border:1px solid #333a47;border-radius:12px;padding:11px 12px;box-shadow:0 18px 40px -18px rgba(0,0,0,.9);
  opacity:0;visibility:hidden;transition:.14s ease;z-index:20;pointer-events:none}
.ringitem:hover .tip{opacity:1;visibility:visible;transform:translateY(-50%) translateX(0)}
.tip .tt{font-family:var(--disp);font-weight:600;font-size:12.5px;margin-bottom:3px}
.tip p{margin:0;font-size:12px;color:var(--muted);line-height:1.45}
.nwrail{margin-top:8px;border-top:1px solid #20242e;padding-top:12px;text-align:center}
.nwrail .k{font-size:11px;color:var(--muted)}
.nwrail .v{font-family:var(--disp);font-weight:700;font-size:18px}

/* paycheck */
.pay{background:linear-gradient(180deg,#1b1e27,#15181f);border:1px solid var(--border);border-radius:16px;padding:18px 20px;margin-bottom:14px}
.pay .cap{font-family:var(--disp);font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--purple);font-weight:600}
.pay .flow{display:flex;align-items:center;gap:22px;flex-wrap:wrap;margin-top:10px}
.pay .blk .k{font-size:12px;color:var(--muted)}
.pay .blk .g{font-family:var(--disp);font-weight:700;font-size:24px;color:var(--muted);font-variant-numeric:tabular-nums}
.pay .blk .n{font-family:var(--disp);font-weight:700;font-size:34px;color:var(--cash);font-variant-numeric:tabular-nums}
.pay .arrow{color:var(--faint);font-size:20px}
.pay .cuts{margin-left:auto;text-align:right;font-size:12.5px;color:var(--muted);min-width:140px}
.pay .cuts .r{display:flex;justify-content:space-between;gap:16px;padding:2px 0}
.pay .cuts .vd{color:var(--debt);font-variant-numeric:tabular-nums}

/* events */
.event{border-radius:13px;padding:12px 15px;margin-bottom:10px}
.event .lab{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;font-weight:600}
.event .etitle{font-family:var(--disp);font-weight:600;font-size:15px;margin-top:4px}
.ev-neg{background:linear-gradient(180deg,#241a1c,#1a1418);border:1px solid #4a2f36}
.ev-neg .lab{color:#fb7185}
.ev-pos{background:linear-gradient(180deg,#16221c,#141a17);border:1px solid #2f4a3a}
.ev-pos .lab{color:#34d399}
.shortfall{background:#241416;border:1px solid #5a2b2b;border-radius:12px;padding:11px 14px;margin-bottom:10px;color:#f3b0b0;font-size:13px}
.taxline{color:var(--muted);font-size:12.5px;margin-bottom:10px}

/* milestone reached (achievement) */
.milestone{display:flex;align-items:center;gap:14px;margin-bottom:10px;padding:12px 15px;border-radius:13px;
  background:linear-gradient(180deg,#251f10,#1a160c);border:1px solid #5a4a1a}
.milestone .mlab{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;color:#f5b642}
.milestone .mtitle{font-family:var(--disp);font-weight:600;font-size:15px;color:#fce8b8;margin-top:3px}
.milestone .mbonus{margin-left:auto;font-family:var(--disp);font-weight:700;font-size:15px;color:#f5b642;white-space:nowrap}

/* title screen */
.title-wrap{text-align:center;padding:46px 20px 30px}
.title-mark{width:104px;height:auto;vertical-align:middle;filter:drop-shadow(0 10px 30px rgba(242,197,61,.30))}
.title-word{height:56px;width:auto;vertical-align:middle;margin-left:6px;filter:drop-shadow(0 3px 12px rgba(242,197,61,.20))}
.title-brand{font-family:var(--disp);font-weight:700;font-size:44px;letter-spacing:-.03em;margin-top:6px}
.title-brand .p{color:var(--purple)}
.title-hook{font-family:var(--disp);font-size:16px;margin-top:8px}
.title-tag{color:var(--muted);font-size:13.5px;margin-top:4px}

/* choose */
.pcard{border:1px solid var(--border);border-radius:16px;background:var(--surface);padding:20px;height:100%}
.pcard .pn{font-family:var(--disp);font-weight:700;font-size:18px}
.pcard .pd{color:var(--muted);font-size:13px;margin:6px 0 14px;min-height:40px}
.pstats{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:6px}
.pstat{background:var(--inset);border:1px solid var(--border);border-radius:11px;padding:8px 10px}
.pstat .sl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.pstat .sv{font-family:var(--disp);font-weight:600;font-size:15px;margin-top:2px;font-variant-numeric:tabular-nums}

/* money quiz */
.qopt{border:1px solid var(--border);border-radius:10px;padding:9px 12px;margin:5px 0;font-size:13.5px}
.qopt.qgood{border-color:#2f6f4f;background:#0f1f19;color:#34d399;font-weight:600}
.qopt.qbad{border-color:#5a2b2b;background:#241416;color:#fb7185;font-weight:600}
.qexpl{margin-top:12px;font-size:13px;color:var(--muted);background:var(--inset);
  border:1px solid var(--border);border-radius:10px;padding:11px 13px;line-height:1.5}

/* how to play */
.steps{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:6px}
@media(max-width:640px){.steps{grid-template-columns:1fr}}
.step{display:flex;gap:13px;border:1px solid var(--border);border-radius:14px;padding:15px;background:var(--surface)}
.step .no{width:30px;height:30px;flex:none;border-radius:9px;display:grid;place-items:center;font-family:var(--disp);
  font-weight:700;background:#241f45;border:1px solid #4a3f8a;color:#c7b8ff;font-size:14px}
.step .st{font-family:var(--disp);font-weight:600;font-size:14px}
.step .sd{font-size:12.5px;color:var(--muted);margin-top:2px}
.legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:18px;padding-top:16px;border-top:1px solid var(--border);
  font-size:12.5px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:7px}
.legend i{width:10px;height:10px;border-radius:50%}

/* titles collection */
.tprog{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}
.tprog .pv{font-family:var(--disp);font-size:13px;color:var(--muted);white-space:nowrap}
.tbarwrap{height:7px;border-radius:999px;background:var(--inset);overflow:hidden;margin:0 0 20px}
.tbarwrap>i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#8b6dff,#34d399)}
.tgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:760px){.tgrid{grid-template-columns:1fr 1fr}}
.ttile{position:relative;border:1px solid var(--border);border-radius:14px;padding:14px;background:var(--surface)}
.ttile .ic{font-size:22px}
.ttile .tn{font-family:var(--disp);font-weight:600;font-size:14px;margin-top:8px}
.ttile .tc{font-size:11.5px;color:var(--muted);margin-top:3px;line-height:1.4}
.ttile.earned{border-color:#3a3170;background:linear-gradient(180deg,#1d1a2e,#161420)}
.ttile.earned .tn{color:#fff}
.ttile.win{border-color:#205040;background:linear-gradient(180deg,#0f1f19,#141a18)}
.ttile.win .tn{color:var(--cash)}
.ttile.locked{opacity:.5}
.ttile.locked .ic{filter:grayscale(1)}
.ttile .bdg{position:absolute;top:12px;right:13px;font-size:10px;font-family:var(--disp);color:var(--faint);letter-spacing:.08em}
.tchips{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:16px 0 2px;font-size:12.5px;color:var(--muted)}
.tchip{display:inline-flex;gap:6px;background:linear-gradient(180deg,#1d1a2e,#161420);border:1px solid #3a3170;
  border-radius:999px;padding:5px 11px;color:#fff;font-family:var(--disp);font-weight:600;font-size:12px}

/* results */
.rbanner{text-align:center;margin:6px 0 18px}
.rbadge{display:inline-block;font-family:var(--disp);font-weight:700;font-size:12px;letter-spacing:.1em;text-transform:uppercase;
  border-radius:999px;padding:6px 14px}
.chartwrap{background:var(--inset);border:1px solid var(--border);border-radius:16px;padding:16px 14px 8px;margin:6px 0 18px}
.chartwrap svg{width:100%;height:auto;display:block}
.rstats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px}
.rstat{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px;text-align:center}
.rstat .rl{font-size:11px;color:var(--muted)}
.rstat .rv{font-family:var(--disp);font-weight:700;font-size:19px;margin-top:3px;font-variant-numeric:tabular-nums}
.rbanner h2{font-size:30px;margin:12px 0 4px}
.rbanner .p{color:var(--purple)}
.rbanner .rs{color:var(--muted);font-size:14px}
.coach{display:flex;gap:12px;background:linear-gradient(180deg,#1d1a2e,#16141d);border:1px solid #3a3170;border-radius:14px;padding:15px;margin-top:6px}
.coach .face{width:44px;height:44px;flex:none;border-radius:12px;display:grid;place-items:center;font-size:23px;background:radial-gradient(circle at 40% 30%,#3a3170,#241f45);border:1px solid #4a3f8a}
.coach .ct{font-family:var(--disp);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--purple);font-weight:600}
.coach p{margin:4px 0 0;font-size:13.5px;line-height:1.5}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)
