#!/usr/bin/env bash
# 用法: shots.sh <base_url> <out_dir> —— 六种页面状态的截图，用于重构前后逐像素对比
set -e
U=$1; O=$2; mkdir -p "$O"; D=$(dirname "$0")
L="document.documentElement.setAttribute('data-theme','light'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));"
node $D/cdp_debug.mjs "$U" "shotjs:$L scrollTo(0,0)" "$O/1_top.json" >/dev/null
node $D/cdp_debug.mjs "$U" "shotjs:$L document.documentElement.setAttribute('data-theme','dark'); scrollTo(0,3000)" "$O/2_dark.json" >/dev/null
node $D/cdp_debug.mjs "$U" "shotjs:$L scrollTo(0,2000); document.querySelector('#reader-bar [data-role=toc]').click(); await sleep(300)" "$O/3_toc.json" >/dev/null
node $D/cdp_debug.mjs "$U" "shotjs:$L const a=[...document.querySelectorAll('main a.xref')].find(x=>/式/.test(x.textContent)); a.scrollIntoView({block:'center'}); await sleep(200); a.dispatchEvent(new PointerEvent('pointerover',{bubbles:true,pointerType:'mouse'})); await sleep(700)" "$O/4_preview.json" >/dev/null
node $D/cdp_debug.mjs "$U" "shotjs:$L const e=document.querySelector('div.thm'); scrollTo(0, e.getBoundingClientRect().top+scrollY-60)" "$O/5_thm.json" >/dev/null
node $D/cdp_debug.mjs "$U" "shotjs:$L const b=[...document.querySelectorAll('#reader-bar button')].find(x=>/双栏/.test(x.textContent)); if(b){b.click(); await sleep(1800);}" "$O/6_split.json" >/dev/null
sha256sum "$O"/*.png | sed 's|  .*/|  |'
