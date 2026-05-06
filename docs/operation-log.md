# 鎿嶄綔鏃ュ織

鏈枃浠惰褰?Codex 瀵规湰浠撳簱鎵ц鐨勬枃妗ｅ鏌ュ拰椤圭洰瑙勫垝鎿嶄綔銆?

## 2026-04-27

### 1. 璇诲彇鍘熷鏂囨。

杈撳叆鏂囦欢锛?

```text
D:\liulanqixiazai\github-weekly-agent-architecture.md
```

澶勭悊缁撴灉锛?

1. 棣栨璇诲彇鏃剁粓绔腑鏂囨樉绀轰负涔辩爜銆?
2. 浣跨敤鏄惧紡 UTF-8 閲嶆柊璇诲彇鍚庯紝纭鏂囨。鍐呭瀹屾暣鍙銆?
3. 宸插畬鎴愬椤圭洰鐩爣銆佺敤鎴烽渶姹傘€佹ā鍧楄璁°€佹妧鏈€夊瀷銆丮VP 鍜岄獙鏀舵爣鍑嗙殑瀹℃煡銆?

### 2. 瀹℃煡鏋舵瀯

缁撹锛?

1. 鍘熸灦鏋勬€讳綋娓呮櫚锛屼笉闇€瑕佹帹缈婚噸寤恒€?
2. 闇€瑕佽ˉ寮虹儹鐐瑰畾涔夈€丟itHub Actions 鑷彁浜ゃ€侀槻寰幆銆乀elegram 鍒嗘銆佽繍琛屾憳瑕佸拰妯″潡杈圭晫銆?
3. 鎺ㄨ崘閲囩敤鈥滃師濮嬫灦鏋?+ 宸ョ▼鍖栧寮衡€濈殑鏋舵瀯銆?

杈撳嚭鏂囦欢锛?

```text
docs/architecture-review.md
```

### 3. 鐢熸垚浼樺寲鍚庣殑椤圭洰鏂囨。

鏂板瀹屾暣鏋舵瀯鏂囨。锛岃鐩栵細

1. 椤圭洰瀹氫綅銆?
2. 鎺ㄨ崘鏋舵瀯銆?
3. 鏁版嵁娴併€?
4. MVP 鑼冨洿銆?
5. 鎺ㄨ崘鐩綍缁撴瀯銆?
6. 妯″潡鑱岃矗銆?
7. 鎼滅储绛栫暐銆?
8. 鎺ㄨ崘璇勫垎銆?
9. 鍛ㄦ姤鏍煎紡銆?
10. Telegram 鎺ㄩ€佺瓥鐣ャ€?
11. 杩愯褰掓。銆?
12. GitHub Actions 瑕佹眰銆?
13. 瀹夊叏瑕佹眰銆?
14. 杩唬璺嚎銆?

杈撳嚭鏂囦欢锛?

```text
docs/project-architecture.md
```

### 4. 寤虹珛浠撳簱鍏ュ彛鏂囨。

鏂板 `README.md`锛岀敤浜庤鏄庡綋鍓嶄粨搴撶姸鎬併€佹枃妗ｇ储寮曘€侀」鐩洰鏍囥€佹妧鏈矾绾垮拰绗竴闃舵鑼冨洿銆?

### 5. 褰撳墠闃舵鏈墽琛岀殑浜嬮」

鎸夌収鐢ㄦ埛瑕佹眰锛屾湰闃舵鏆備笉寮€鍙戦」鐩唬鐮侊紝鍥犳娌℃湁鍒涘缓 Python 婧愮爜銆丟itHub Actions workflow銆佷緷璧栨枃浠舵垨杩愯鑴氭湰銆?

鍚庣画濡傛灉杩涘叆寮€鍙戦樁娈碉紝鍐嶆寜 `docs/project-architecture.md` 涓殑寮€鍙戦『搴忓疄鏂姐€?

---

## 2026-04-27 杩藉姞锛氬熀浜?pi-mono 鐨勯噸鏂版灦鏋勫鏌?

### 1. 瀛︿範鍙傝€冮」鐩?

鍙傝€冮摼鎺ワ細

```text
https://github.com/badlogic/pi-mono
```

閲嶇偣瀛︿範鍐呭锛?

1. `pi-mono` 鏄洿缁?AI Agent 鏋勫缓鐨?monorepo锛屽寘鍚粺涓€ LLM API銆丄gent runtime銆乧oding agent銆乀UI銆乄eb UI銆丼lack bot 鍜?vLLM pods 绠＄悊宸ュ叿銆?
2. `pi-coding-agent` 鐨勬牳蹇冩€濇兂鏄渶灏忔牳蹇冦€佸伐鍏锋墿灞曘€丳rompt Templates銆丼kills銆丄GENTS.md銆丼essions 鍜?Extensions銆?
3. 瀵规湰椤圭洰鏈€鏈変环鍊肩殑鏄」鐩骇 Agent 瑙勫垯銆佹彁绀鸿瘝妯℃澘澶栫疆銆佽繍琛屽巻鍙茶褰曘€佸彲鎵╁睍浣嗕笉杩囧害澶嶆潅鐨勬ā鍧楄竟鐣屻€?

### 2. 瀹℃煡鏂扮増鏋舵瀯鏂囨。

杈撳叆鏂囦欢锛?

```text
D:\liulanqixiazai\github-weekly-agent-rearchitecture-from-pi-mono.md
```

缁撹锛?

1. 鏂扮増鏋舵瀯鏂瑰悜姝ｇ‘锛岄€傚悎浣滀负鍘熸灦鏋勭殑鍗囩骇鐗堛€?
2. `AGENTS.md` 鍜?`prompts/weekly_report.md` 搴旂撼鍏ョ涓€闃舵銆?
3. `data/` 鍘嗗彶璁板綍璁捐搴斾繚鐣欙紝浣嗚鍖哄垎涓嶅彲鍙樿繍琛屾憳瑕佸拰鍙彉鍘婚噸鐘舵€併€?
4. `skills/` 鐩綍鍙簲浣滀负鍚庣画棰勭暀璇存槑锛孧VP 闃舵涓嶅缓璁垱寤虹┖ Skill 鏂囦欢锛岄伩鍏嶅鍔犳棤瀹為檯鐢ㄩ€旂殑缁存姢闈€?
5. GitHub Actions 鑷姩鎻愪氦蹇呴』鍔犲叆闃插惊鐜€佸苟鍙戞帶鍒跺拰鍙樻洿妫€娴嬨€?

### 3. 鏈鏂板鏂囨。

杈撳嚭鏂囦欢锛?

```text
docs/pi-mono-rearchitecture-review.md
```

璇ユ枃妗ｈ褰曪細

1. 浠?`pi-mono` 瀛﹀埌鐨勫彲閲囩撼璁捐銆?
2. 鏂扮増鏋舵瀯涓缓璁繚鐣欑殑閮ㄥ垎銆?
3. 闇€瑕佹敹鏁涙垨寤跺悗鐨勯儴鍒嗐€?
4. 闈㈠悜鈥滀唬鐮佺畝娲佸畬鏁粹€濈殑鏈€缁堝紑鍙戝缓璁€?

---

## 2026-04-27 杩藉姞锛氱涓€闃舵 MVP 寮€鍙?

### 1. 寮€鍙戣寖鍥?

涓ユ牸鎸夌収鏀舵暃鍚庣殑 MVP 鏋舵瀯寮€鍙戯紝鏈垱寤烘殏缂撶殑 `skills/`銆乄eb Dashboard銆丼QLite 鎴栧鏉傛彃浠剁郴缁熴€?

鏈瀹炵幇鍐呭锛?

1. `AGENTS.md` 椤圭洰绾?Agent 寮€鍙戣鍒欍€?
2. `prompts/weekly_report.md` 鐙珛鍛ㄦ姤鎻愮ず璇嶃€?
3. `main.py` 涓绘祦绋嬬紪鎺掋€?
4. `src/collector.py` GitHub Search API 閲囬泦銆?
5. `src/processor.py` 鍘婚噸銆佽繃婊ゃ€佽瘎鍒嗗拰鎺掑簭銆?
6. `src/reporter.py` Kimi 鐢熸垚鍜?fallback 鍩虹鎶ュ憡銆?
7. `src/sender.py` Telegram 鍒嗘鎺ㄩ€併€?
8. `src/archive.py` Markdown銆佸師濮嬫暟鎹拰杩愯鎽樿褰掓。銆?
9. `src/settings.py` 鐜鍙橀噺鍜屽叴瓒ｉ厤缃鍙栥€?
10. `src/utils.py` 鏃ユ湡銆佸垎娈靛拰閫氱敤杈呭姪鍑芥暟銆?
11. `.github/workflows/weekly.yml` 瀹氭椂鍜屾墜鍔ㄨЕ鍙戝伐浣滄祦銆?
12. `tests/` 鏈€灏忓崟鍏冩祴璇曘€?

### 2. 绠€娲佹€у鐞?

1. 鏆備笉澧炲姞澶栭儴渚濊禆锛宍requirements.txt` 淇濇寔鏍囧噯搴撳疄鐜般€?
2. 鏆備笉鎷嗗垎 HTTP clients锛岄伩鍏?MVP 杩囧害鎶借薄銆?
3. 鏆備笉鍒涘缓 Skill 鐩綍锛岀瓑宸ヤ綔娴佺ǔ瀹氬悗鍐嶄骇鍝佸寲銆?
4. 姣忎釜妯″潡鍙礋璐ｄ竴涓富瑕佽亴璐ｃ€?

### 3. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py -m unittest discover -v
py -m compileall main.py src tests
py main.py
```

楠岃瘉缁撴灉锛?

1. 3 涓崟鍏冩祴璇曢€氳繃銆?
2. Python 缂栬瘧妫€鏌ラ€氳繃銆?
3. 绔埌绔繍琛屾垚鍔熺敓鎴愭姤鍛娿€?
4. 鏈湴鏈厤缃?Telegram锛岀▼搴忔寜璁捐杈撳嚭 `Telegram is not configured`锛屾湭闃绘柇褰掓。娴佺▼銆?

鏈湴楠岃瘉鐢熸垚鐨勪复鏃舵姤鍛婂拰杩愯鏁版嵁涓嶄綔涓烘簮鐮佹彁浜ゃ€?

---

## 2026-04-27 杩藉姞锛氭枃妗ｄ腑鏂囧寲

### 1. 鐢ㄦ埛瑕佹眰

鐢ㄦ埛瑕佹眰椤圭洰涓墍鏈夋枃妗ｄ娇鐢ㄤ腑鏂囦功鍐欙紝灏嗚嫳鏂囧啓鎴愮殑閮ㄥ垎閲嶆柊鐢ㄤ腑鏂囪〃杈俱€?

### 2. 鏈澶勭悊鑼冨洿

鏈宸插皢浠ヤ笅鏂囨。鎬ф枃浠朵腑鐨勮嫳鏂囪鏄庢敼鍐欎负涓枃锛?

1. `AGENTS.md`
2. `docs/architecture.md`
3. `docs/setup.md`
4. `docs/roadmap.md`
5. `prompts/weekly_report.md`
6. `.env.example`
7. `requirements.txt`
8. `.github/workflows/weekly.yml` 涓潰鍚戠敤鎴锋樉绀虹殑宸ヤ綔娴佸悕绉板拰姝ラ鍚嶇О

### 3. 淇濈暀鍐呭

浠ヤ笅鍐呭灞炰簬鎶€鏈悕璇嶃€佸懡浠ゃ€佽矾寰勩€佺幆澧冨彉閲忓悕鎴?GitHub Actions 璇硶锛屼繚鎸佸師鏍凤細

1. `GitHub Weekly Agent`
2. `GitHub Actions`
3. `Telegram`
4. `Kimi API`
5. `python main.py`
6. `GH_SEARCH_TOKEN` 绛夌幆澧冨彉閲忓悕
7. `.github/workflows/weekly.yml` 涓殑宸ヤ綔娴佸叧閿瓧

---

## 2026-04-27 杩藉姞锛欸itHub Secrets 閰嶇疆娴嬭瘯

### 1. 娴嬭瘯鏂瑰紡

鏂板妫€鏌ュ伐浣滄祦锛?

```text
.github/workflows/secrets-check.yml
```

璇ュ伐浣滄祦閫氳繃 GitHub Actions 璇诲彇浠撳簱 Secrets锛屽苟楠岃瘉锛?

1. `GH_SEARCH_TOKEN` 鏄惁瀛樺湪骞跺彲璁块棶 GitHub API銆?
2. `KIMI_API_KEY`銆乣KIMI_BASE_URL`銆乣KIMI_MODEL` 鏄惁瀛樺湪骞跺彲璋冪敤 Kimi API銆?
3. `TELEGRAM_BOT_TOKEN`銆乣TELEGRAM_CHAT_ID` 鏄惁瀛樺湪骞跺彲鍙戦€?Telegram 娴嬭瘯娑堟伅銆?

### 2. 鍒濆娴嬭瘯缁撴灉

杩愯缁撹锛氬け璐ャ€?

宸茬‘璁わ細

1. 鎵€鏈夊繀瑕?Secrets 閮借兘琚?GitHub Actions 璇诲彇鍒般€?
2. `GH_SEARCH_TOKEN` 楠岃瘉閫氳繃锛孏itHub API 鍓╀綑棰濆害姝ｅ父銆?

澶辫触鐐癸細

```text
Kimi API 杩斿洖 HTTP 400銆?
```

### 3. 澶辫触鍘熷洜

GitHub Actions 鏃ュ織鏄剧ず锛?

```text
invalid temperature: only 1 is allowed for this model
```

璇存槑褰撳墠閰嶇疆鐨?Kimi 妯″瀷鍙厑璁?`temperature=1`銆?

### 4. 淇鍔ㄤ綔

宸插皢浠ヤ笅浣嶇疆鐨?`temperature` 鏀逛负 `1`锛?

1. `src/reporter.py`
2. `.github/workflows/secrets-check.yml`

### 5. 鏈€缁堟祴璇曠粨鏋?

鏈€缁堣繍琛岀粨鏋滐細鎴愬姛銆?

宸茬‘璁わ細

1. `GH_SEARCH_TOKEN` 宸查厤缃紝骞堕€氳繃 GitHub API 楠岃瘉銆?
2. `KIMI_API_KEY` 宸查厤缃€?
3. `KIMI_BASE_URL` 宸查厤缃€?
4. `KIMI_MODEL` 宸查厤缃€?
5. Kimi API 鍙互杩為€氬苟杩斿洖 `choices`銆?
6. `TELEGRAM_BOT_TOKEN` 宸查厤缃€?
7. `TELEGRAM_CHAT_ID` 宸查厤缃€?
8. Telegram 娴嬭瘯娑堟伅鍙戦€佹垚鍔熴€?

GitHub Actions 鎴愬姛杩愯閾炬帴锛?

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/24992511910
```

璇存槑锛氭湰娆?Kimi 杞婚噺娴嬭瘯璇锋眰杩斿洖鍐呭涓虹┖锛屼絾 HTTP 璋冪敤鎴愬姛骞惰繑鍥炰簡鏈夋晥 `choices` 瀛楁锛屽洜姝ゅ垽鏂负 API 閰嶇疆鍙敤銆傛寮忓懆鎶ョ敓鎴愭祦绋嬩細浣跨敤瀹屾暣鎻愮ず璇嶅拰椤圭洰鏁版嵁璋冪敤 Kimi銆?

---

## 2026-04-28 杩藉姞锛氬畬鏁村懆鎶ュ伐浣滄祦楠岃瘉

### 1. 楠岃瘉鐩殑

鍦ㄧ敤鎴峰畬鎴?GitHub Secrets 閰嶇疆鍚庯紝瀵瑰畬鏁磋嚜鍔ㄥ寲閾捐矾杩涜楠岃瘉锛岀‘璁や粠 GitHub Actions 鍒板懆鎶ュ綊妗ｃ€並imi 鐢熸垚鍜?Telegram 鎺ㄩ€佺殑娴佺▼鍙互姝ｅ父杩愯銆?

楠岃瘉閾捐矾锛?

```text
GitHub Actions
-> python -m unittest
-> python main.py
-> GitHub 椤圭洰閲囬泦
-> Kimi 涓枃鍛ㄦ姤鐢熸垚
-> reports/ 涓?data/ 褰掓。
-> Telegram 鎺ㄩ€?
-> Actions 鑷姩鎻愪氦褰掓。鏂囦欢
```

### 2. 涓存椂瑙﹀彂鏂瑰紡

涓洪伩鍏嶇瓑寰呮瘡鍛ㄥ畾鏃朵换鍔★紝涓存椂缁?`.github/workflows/weekly.yml` 澧炲姞浜嗕粎鐢ㄤ簬娴嬭瘯鐨?`push` 瑙﹀彂鍣ㄣ€?

娴嬭瘯瀹屾垚鍚庡凡绉婚櫎璇ヤ复鏃惰Е鍙戝櫒锛屾寮忓伐浣滄祦淇濈暀锛?

1. `workflow_dispatch` 鎵嬪姩瑙﹀彂銆?
2. 姣忓懆涓€ UTC 00:00 鐨勫畾鏃惰Е鍙戙€?

### 3. 绗竴娆″畬鏁存祦绋嬫祴璇?

杩愯閾炬帴锛?

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25031865017
```

杩愯缁撹锛氭垚鍔熴€?

褰掓。缁撴灉锛?

1. `reports/2026-04-28.md`
2. `data/raw/2026-04-28.json`
3. `data/runs/2026-04-28.json`

鏈缁撴灉鏄剧ず Telegram 鎺ㄩ€佹垚鍔燂紝浣?Kimi 鍛ㄦ姤鐢熸垚浣跨敤浜嗛檷绾ф姤鍛娿€備负渚夸簬鍚庣画瀹氫綅锛岄殢鍚庡湪杩愯鎽樿涓鍔犱簡 `report_error` 瀛楁锛屽苟澧炲己浜?Kimi 鍝嶅簲鍐呭鎻愬彇閫昏緫銆?

### 4. 绗簩娆″畬鏁存祦绋嬫祴璇?

杩愯閾炬帴锛?

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25031996992
```

杩愯缁撹锛氭垚鍔熴€?

鍏抽敭缁撴灉锛?

1. `collected_count`: 165
2. `selected_count`: 10
3. `kimi_used`: true
4. `fallback_used`: false
5. `telegram_sent`: true
6. `report_path`: `reports/2026-04-28.md`
7. `run_summary_path`: `data/runs/2026-04-28.json`

璇存槑锛氱浜屾瀹屾暣娴佺▼宸茬粡纭 Kimi 姝ｅ父鐢熸垚涓枃鍛ㄦ姤锛孴elegram 姝ｅ父鎺ㄩ€侊紝Actions 鑷姩褰掓。鎻愪氦姝ｅ父鎵ц銆?

### 5. 鏈浠ｇ爜涓庢枃妗ｈ皟鏁?

1. `src/models.py`锛氫负杩愯鎽樿澧炲姞 `report_error` 瀛楁銆?
2. `src/reporter.py`锛氳 Kimi 鐢熸垚澶辫触鏃惰繑鍥炴槑纭敊璇師鍥狅紝骞跺吋瀹规洿澶氬搷搴斿唴瀹圭粨鏋勩€?
3. `main.py`锛氬啓鍏?`report_error`锛屼究浜庝粠 `data/runs/` 杩借釜妯″瀷鐢熸垚闂銆?
4. `tests/test_reporter.py`锛氬鍔?Kimi 鍝嶅簲鍐呭鎻愬彇娴嬭瘯銆?
5. `.github/workflows/weekly.yml`锛氱Щ闄ゆ祴璇曠敤 `push` 瑙﹀彂鍣ㄣ€?
6. `docs/operation-log.md`锛氳褰曞畬鏁村伐浣滄祦楠岃瘉杩囩▼鍜岀粨鏋溿€?

### 6. 褰撳墠缁撹

Secrets 閰嶇疆宸茬粡閫氳繃瀹屾暣閾捐矾楠岃瘉銆傚綋鍓嶉」鐩凡鍏峰鎸夊懆鑷姩鎶撳彇 GitHub 鐑偣椤圭洰銆佺敓鎴愪腑鏂囧懆鎶ャ€佹帹閫佸埌 Telegram銆佸綊妗ｈ繍琛岀粨鏋滃苟鑷姩鎻愪氦鍒?GitHub 鐨勫熀纭€鑳藉姏銆?

---

## 2026-04-28 杩藉姞锛氱浜岄樁娈靛凡鎺ㄩ€佷粨搴撶姸鎬佽褰?

### 1. 寮€鍙戠洰鐨?

杩涘叆绗簩闃舵鏁版嵁璐ㄩ噺澧炲己鍚庯紝浼樺厛瀹炵幇鏈€灏忎笖蹇呰鐨勫巻鍙茬姸鎬佽兘鍔涳紝閬垮厤鍚屼竴浠撳簱鍦ㄥ悗缁懆鎶ヤ腑琚噸澶嶆帹閫併€?

### 2. 鏈瀹炵幇

鏂板妯″潡锛?

```text
src/state.py
```

璇ユā鍧楄礋璐ｏ細

1. 璇诲彇 `data/state/sent_repos.json`銆?
2. 杩囨护宸茬粡鎴愬姛鎺ㄩ€佽繃鐨勪粨搴撱€?
3. Telegram 鎺ㄩ€佹垚鍔熷悗鍐欏叆鏂扮殑宸叉帹閫佷粨搴撱€?
4. 鍏煎鏃х殑瀛楃涓叉暟缁勬牸寮忓拰鏂扮殑瀵硅薄鏁扮粍鏍煎紡銆?

### 3. 涓绘祦绋嬪彉鍖?

鏂扮殑澶勭悊椤哄簭锛?

```text
collect_repositories
-> load_sent_repository_names
-> filter_unsent_repositories
-> process_repositories
-> generate_report
-> send_report
-> write_sent_repositories
```

鐘舵€佸啓鍏ユ潯浠讹細

1. Telegram 鎺ㄩ€佹垚鍔熴€?
2. 鏈绛涢€夊嚭鐨勬柊浠撳簱鍒楄〃涓嶄负绌恒€?

濡傛灉 Kimi 涓嶅彲鐢紝浠嶅彲浣跨敤闄嶇骇鐗堝懆鎶ワ紱濡傛灉 Telegram 涓嶅彲鐢ㄦ垨鍙戦€佸け璐ワ紝鍒欎笉浼氬啓鍏ュ凡鎺ㄩ€佺姸鎬侊紝閬垮厤閬楁紡鍚庣画鐪熷疄鎺ㄩ€併€?

### 4. 杩愯鎽樿鍙樺寲

`data/runs/YYYY-MM-DD.json` 鏂板瀛楁锛?

1. `skipped_sent_count`锛氭湰娆￠噰闆嗙粨鏋滀腑琚巻鍙叉帹閫佺姸鎬佽烦杩囩殑浠撳簱鏁般€?
2. `state_path`锛氭湰娆℃垚鍔熷啓鍏ョ殑鐘舵€佹枃浠惰矾寰勩€?

### 5. 宸ヤ綔娴佸彉鍖?

`.github/workflows/weekly.yml` 鐨勮嚜鍔ㄦ彁浜よ寖鍥村鍔狅細

```text
data/state
```

杩欐牱 GitHub Actions 鐢熸垚鐨勫凡鎺ㄩ€佺姸鎬佷細鍜屽懆鎶ャ€佸師濮嬫暟鎹€佽繍琛屾憳瑕佷竴璧锋彁浜ゅ洖浠撳簱銆?

### 6. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py -m unittest
py -m compileall main.py src tests
```

楠岃瘉缁撴灉锛氶€氳繃銆?

### 7. 鍒濆鐘舵€佸啓鍏?

鐢变簬 `2026-04-28` 鐨勫畬鏁村伐浣滄祦宸茬粡纭 Telegram 鎺ㄩ€佹垚鍔燂紝鏈鍚屾鍒涘缓锛?

```text
data/state/sent_repos.json
```

璇ユ枃浠朵娇鐢?`data/raw/2026-04-28.json` 涓殑 10 涓凡鎺ㄩ€佷粨搴撳垵濮嬪寲锛岄伩鍏嶄笅涓€娆¤繍琛岄噸澶嶆帹閫佸悓涓€鎵归」鐩€?

---

## 2026-04-28 杩藉姞锛氱浜岄樁娈?README 鎽樿鎶撳彇

### 1. 寮€鍙戠洰鐨?

鎻愬崌鍛ㄦ姤鍐呭璐ㄩ噺銆備粎渚濊禆浠撳簱鍚嶇О鍜岀畝浠嬫椂锛孠imi 瀵归」鐩畾浣嶅鏄撹繃浜庣矖鐣ワ紱鍔犲叆 README 鎽樿鍚庯紝鍙互璁╁懆鎶ユ洿鍑嗙‘鍦拌鏄庨」鐩敤閫斻€佺壒鎬у拰瀛︿範浠峰€笺€?

### 2. 瀹炵幇鑼冨洿

鏈瀹炵幇淇濇寔绠€娲侊紝涓嶅鍔犳柊渚濊禆锛屼笉寮曞叆澶嶆潅缂撳瓨鎴栨暟鎹簱銆?

鏂板鑳藉姏锛?

1. 瀵规渶缁堝叆閫夊懆鎶ョ殑浠撳簱鎶撳彇 README銆?
2. 娓呮礂 README 涓殑澶氫綑绌虹櫧銆?
3. 姣忎釜浠撳簱鍙繚鐣欏墠 2000 涓瓧绗︿綔涓烘憳瑕併€?
4. 鍗曚釜 README 鑾峰彇澶辫触鏃惰烦杩囷紝涓嶅奖鍝嶆暣浣撹繍琛屻€?
5. Kimi 鎻愮ず璇嶈姹備紭鍏堝弬鑰?README 鎽樿銆?
6. 闄嶇骇鐗堝懆鎶ヤ篃浼氬睍绀?README 鎽樿銆?

### 3. 涓绘祦绋嬪彉鍖?

鏂扮殑澶勭悊椤哄簭锛?

```text
collect_repositories
-> load_sent_repository_names
-> filter_unsent_repositories
-> process_repositories
-> enrich_repositories_with_readmes
-> generate_report
-> send_report
-> write_sent_repositories
```

### 4. 杩愯鎽樿鍙樺寲

`data/runs/YYYY-MM-DD.json` 鏂板瀛楁锛?

```text
readme_fetched_count
```

璇ュ瓧娈佃褰曟湰娆℃垚鍔熻幏鍙?README 鎽樿鐨勫叆閫変粨搴撴暟閲忋€?

### 5. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py -m unittest
py -m compileall main.py src tests
```

楠岃瘉缁撴灉锛氶€氳繃銆?

---

## 2026-04-28 杩藉姞锛氱浜岄樁娈?Star 澧為噺璇勫垎

### 1. 寮€鍙戠洰鐨?

琛ラ綈绗簩闃舵鏁版嵁璐ㄩ噺澧炲己涓殑鍘嗗彶鐑害鑳藉姏銆傚崟绾寜鎬?Star 鎺掑簭瀹规槗闀挎湡鍋忓悜澶у瀷鑰侀」鐩紱鍔犲叆 Star 澧為噺鍚庯紝鍙互鏇村ソ鍙戠幇杩戞湡澧為暱鏄庢樉鐨勯」鐩€?

### 2. 鏈瀹炵幇

鏂板鐘舵€佹枃浠讹細

```text
data/state/star_history.json
```

璇ユ枃浠惰褰曪細

1. 浠撳簱瀹屾暣鍚嶇О銆?
2. 浠撳簱閾炬帴銆?
3. 鏈€杩戜竴娆￠噰闆嗗埌鐨?Star 鏁般€?
4. 鏈€杩戜竴娆￠噰闆嗘棩鏈熴€?

### 3. 璇勫垎鍙樺寲

`Repository` 鏂板瀛楁锛?

```text
star_growth
```

璁＄畻鏂瑰紡锛?

```text
star_growth = 褰撳墠 Star - 鍘嗗彶 Star
```

濡傛灉娌℃湁鍘嗗彶璁板綍锛屽垯澧為暱鍊间负 0銆?

褰撳墠璇勫垎鏉冮噸锛?

1. 鎬?Star锛?5%
2. Fork锛?5%
3. 鍏磋叮涓婚鍖归厤锛?5%
4. Star 澧為噺锛?5%
5. 鍒涘缓鏃堕棿鏂伴矞搴︼細10%

### 4. 涓绘祦绋嬪彉鍖?

涓绘祦绋嬩細鍦ㄥ鐞嗕粨搴撳墠璇诲彇 Star 鍘嗗彶锛屽湪瀹屾垚鏈褰掓。鏃跺啓鍏ユ渶鏂?Star 鍘嗗彶銆?

杩愯鎽樿鏂板瀛楁锛?

1. `star_history_updated_count`
2. `star_history_path`

### 5. 鍒濆鐘舵€佸啓鍏?

鐢变簬 `2026-04-28` 宸茬粡鏈変竴娆℃垚鍔熷畬鏁磋繍琛岋紝鏈浣跨敤 `data/raw/2026-04-28.json` 鍒濆鍖?`data/state/star_history.json`锛屼负涓嬩竴娆¤繍琛屾彁渚涘閲忓熀绾裤€?

### 6. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py -m unittest
py -m compileall main.py src tests
```

楠岃瘉缁撴灉锛氶€氳繃銆?

---

## 2026-04-28 杩藉姞锛氱涓夐樁娈?GitHub Pages 鍛ㄦ姤褰掓。椤甸潰

### 1. 寮€鍙戠洰鐨?

杩涘叆绗笁闃舵浜у搧鍖栬緭鍑哄悗锛屼紭鍏堝疄鐜拌交閲忕殑鍛ㄦ姤褰掓。椤甸潰锛岃鐢熸垚鐨勫懆鎶ュ彲浠ラ€氳繃 GitHub Pages 鐩存帴娴忚銆?

### 2. 鏈瀹炵幇

鏂板鑴氭湰锛?

```text
scripts/build_pages.py
```

璇ヨ剼鏈礋璐ｏ細

1. 璇诲彇 `reports/` 涓嬬殑鍛ㄦ姤銆?
2. 璇诲彇 `data/runs/` 涓嬬殑杩愯鎽樿銆?
3. 鐢熸垚 `docs/index.md` 鍛ㄦ姤褰掓。棣栭〉銆?
4. 灏嗗懆鎶ュ悓姝ュ埌 `docs/weekly/YYYY-MM-DD.md`銆?

### 3. 宸ヤ綔娴佸彉鍖?

`.github/workflows/weekly.yml` 鏂板姝ラ锛?

```text
python scripts/build_pages.py
```

鑷姩鎻愪氦鑼冨洿鏂板锛?

```text
docs/index.md
docs/weekly
```

### 4. 鏈鐢熸垚鏂囦欢

```text
docs/index.md
docs/weekly/2026-04-28.md
```

### 5. GitHub Pages 鍚敤鏂瑰紡

鍦?GitHub 浠撳簱涓繘鍏ワ細

```text
Settings -> Pages
```

璁剧疆锛?

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

### 6. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py scripts/build_pages.py
py -m unittest
py -m compileall main.py src tests scripts
```

楠岃瘉缁撴灉锛氶€氳繃銆?

---

## 2026-04-28 杩藉姞锛氬懆鎶ラ〉闈㈠唴瀹逛笌閾炬帴鏍煎紡淇

### 1. 鐢ㄦ埛鍙嶉

鐢ㄦ埛鍙嶉 GitHub Pages 涓敓鎴愮殑鍛ㄦ姤椤甸潰瀛樺湪浠ヤ笅闂锛?

1. 闇€瑕佺‘淇濋〉闈㈠唴瀹瑰睘浜庢湰鍛ㄨ寖鍥淬€?
2. 鈥滀富瑕佽瑷€鈥濅腑涓嶈兘鍑虹幇鈥滆煉铔団€濊繖绫讳腑鏂囩洿璇戯紝搴斾繚鐣?`Python` 绛夋妧鏈瑷€鑻辨枃鍚嶇О銆?
3. 鐑棬椤圭洰鎬昏涓殑 GitHub 閾炬帴搴斾负鍙偣鍑昏秴閾炬帴銆?
4. 淇敼鍚庨渶瑕佹鏌ヤ唬鐮佹槸鍚﹀瓨鍦ㄥ啑浣欐垨鏄庢樉闂銆?

### 2. 鏈淇

閲囬泦鑼冨洿淇锛?

1. 绉婚櫎 `pushed:>=...` 鏌ヨ锛岄伩鍏嶅巻鍙茶€侀」鐩粎鍥犳湰鍛ㄦ洿鏂拌€岃繘鍏モ€滄湰鍛ㄥ垱寤洪」鐩€濆懆鎶ャ€?
2. 鍦ㄥ鐞嗛樁娈靛鍔?`created_at >= since_date` 浜屾鏍￠獙锛屽嵆浣?GitHub Search 鏌ヨ鍙樺寲锛屼篃涓嶄細璁╅潪鏈懆鍒涘缓椤圭洰杩涘叆鍛ㄦ姤銆?

鎶ュ憡鏍煎紡淇锛?

1. Kimi 杈撳嚭鍜岄檷绾ф姤鍛婇兘浼氱粡杩?`normalize_report_markdown` 娓呮礂銆?
2. 灏嗏€滆煉铔団€濈粺涓€鏇挎崲涓?`Python`銆?
3. 灏?GitHub 鍘熷 URL 杞负 Markdown 瓒呴摼鎺ャ€?
4. 宸茬粡鏄?Markdown 鏍煎紡鐨勯摼鎺ヤ笉浼氶噸澶嶅寘瑁呫€?
5. 闄嶇骇鐗堝懆鎶ヤ腑鐨?README 鎽樿鎴柇灞曠ず锛岄伩鍏嶉〉闈㈣繃闀垮奖鍝嶉槄璇汇€?

鎻愮ず璇嶄慨姝ｏ細

1. 瑕佹眰鎶€鏈瑷€鍚嶇О淇濈暀瀹樻柟鑻辨枃鍚嶇О銆?
2. 瑕佹眰鍙垎鏋愮敤鎴锋暟鎹彁渚涚殑鏈懆鍒涘缓椤圭洰銆?
3. 瑕佹眰鐑偣椤圭洰鎬昏涓殑閾炬帴鍒椾娇鐢?Markdown 瓒呴摼鎺ユ牸寮忋€?

### 3. 褰撳墠椤甸潰閲嶆柊鐢熸垚

宸查噸鏂版墽琛岋細

```text
py main.py
py scripts/build_pages.py
```

璇存槑锛氭湰鍦扮幆澧冩病鏈?Kimi 鍜?Telegram 瀵嗛挜锛屽洜姝ゆ湰娆￠噸鏂扮敓鎴愮殑 `2026-04-28` 椤甸潰涓洪檷绾х増鍛ㄦ姤锛屼笖涓嶄細鍐欏叆宸叉帹閫佺姸鎬併€侴itHub Actions 鍚庣画姝ｅ紡杩愯鏃朵粛浼氳鍙栦粨搴?Secrets 骞朵娇鐢?Kimi 涓?Telegram銆?

### 4. 鏍￠獙缁撴灉

宸茬‘璁わ細

1. `reports/2026-04-28.md` 鍜?`docs/weekly/2026-04-28.md` 涓病鏈夆€滆煉铔団€濄€?
2. 鐑棬椤圭洰鎬昏涓殑 GitHub 閾炬帴宸蹭负 `[GitHub](...)` Markdown 瓒呴摼鎺ャ€?
3. `data/raw/2026-04-28.json` 涓墍鏈夊叆閫夐」鐩殑 `created_at` 閮戒笉鏃╀簬 `2026-04-21`銆?

### 5. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py -m unittest
py -m compileall main.py src tests scripts
```

楠岃瘉缁撴灉锛氶€氳繃銆?

---

## 2026-04-28 杩藉姞锛氫慨姝ｂ€滄湰鍛ㄦ渶鐏垎鈥濆畾涔変笌 Kimi 闄嶇骇鍘熷洜

### 1. 鐢ㄦ埛绾犳

鐢ㄦ埛鎸囧嚭锛氶」鐩簲褰撴槸涓€鍛ㄥ唴鏈€鐏垎鐨勯」鐩紝鑰屼笉鏄敓鎴愭椂闂存垨鍒涘缓鏃堕棿鍦ㄤ竴鍛ㄤ箣鍐呯殑椤圭洰銆?

杩欐槸姝ｇ‘鐨勩€傛湰椤圭洰鐨勯噰闆嗛€昏緫搴斾互鈥滄渶杩戜竴鍛ㄦ椿璺冧笖鐑害楂樷€濅负涓伙紝涓嶈兘鍙湅 `created_at`銆?

### 2. 閲囬泦閫昏緫淇

宸插皢涓绘煡璇粠 `created:>=...` 鏀逛负 `pushed:>=...`锛?

```text
pushed:>=YYYY-MM-DD stars:>N
topic:ai pushed:>=YYYY-MM-DD stars:>N
topic:agent pushed:>=YYYY-MM-DD stars:>10
topic:llm pushed:>=YYYY-MM-DD stars:>10
topic:automation pushed:>=YYYY-MM-DD stars:>10
language:Python pushed:>=YYYY-MM-DD stars:>N
language:TypeScript pushed:>=YYYY-MM-DD stars:>N
created:>=YYYY-MM-DD stars:>10
```

鍏朵腑 `created` 鏌ヨ鍙綔涓鸿ˉ鍏咃紝鐢ㄤ簬鎹曟崏鏈懆鏂板嚭鐜颁笖澧為暱杈冨揩鐨勯」鐩€?

### 3. 杩囨护閫昏緫淇

`Repository` 鏂板瀛楁锛?

```text
pushed_at
```

澶勭悊闃舵涓嶅啀瑕佹眰 `created_at >= since_date`锛屾敼涓鸿姹傦細

```text
pushed_at 鎴?updated_at >= since_date
```

杩欐牱鑰侀」鐩彧瑕佹湰鍛ㄤ粛鐒舵椿璺冧笖鐑害楂橈紝涔熷彲浠ヨ繘鍏ュ懆鎶ャ€?

### 4. Kimi 闄嶇骇鍘熷洜鍒ゆ柇

鏈椤甸潰鏄剧ず鈥?Kimi API 鏈惎鐢ㄦ垨璋冪敤澶辫触鈥濈殑鐩存帴鍘熷洜鏄細涓轰簡淇椤甸潰锛屾垜鍦ㄦ湰鍦版墽琛屼簡锛?

```text
py main.py
```

褰撳墠鏈湴鐜娌℃湁閰嶇疆锛?

```text
KIMI_API_KEY
KIMI_MODEL
```

鍥犳绋嬪簭鎸夎璁＄敓鎴愰檷绾х増 Markdown 鍛ㄦ姤锛屽苟鍦?`data/runs/2026-04-28.json` 涓褰曪細

```text
"kimi_used": false
"fallback_used": true
"report_error": "Kimi API 鏈厤缃?
```

杩欎笉鏄?GitHub Actions Secrets 澶辨晥銆備箣鍓?GitHub Actions 鑷姩褰掓。鎻愪氦 `3767552` 涓殑杩愯鎽樿鏄剧ず锛?

```text
"kimi_used": true
"fallback_used": false
"telegram_sent": true
```

璇存槑鍦?GitHub Actions 鐜涓紝Kimi Secrets 鏇剧粡姝ｅ父鐢熸晥銆?

### 5. 褰撳墠椤甸潰閲嶆柊鐢熸垚

宸查噸鏂版墽琛岋細

```text
py main.py
py scripts/build_pages.py
```

褰撳墠 `2026-04-28` 椤甸潰宸茬粡鎸夋渶杩戜竴鍛ㄦ椿璺冮」鐩噸鏂扮敓鎴愩€傜敱浜庢湰鍦版湭閰嶇疆 Kimi 鍜?Telegram锛屾湰娆￠〉闈负闄嶇骇鐗堬紝涓斾笉浼氬啓鍏ュ凡鎺ㄩ€佺姸鎬併€?

### 6. 鏍￠獙缁撴灉

宸茬‘璁わ細

1. `data/raw/2026-04-28.json` 涓墍鏈夊叆閫夐」鐩殑 `pushed_at` 鎴?`updated_at` 閮戒笉鏃╀簬 `2026-04-21`銆?
2. 鎶ュ憡涓病鏈夆€滆煉铔団€濄€?
3. 鐑棬椤圭洰鎬昏涓殑 GitHub 閾炬帴涓?Markdown 瓒呴摼鎺ャ€?

### 7. 鏈湴楠岃瘉

宸叉墽琛岋細

```text
py -m unittest
py -m compileall main.py src tests scripts
```

楠岃瘉缁撴灉锛氶€氳繃銆?

---

## 2026-04-28 杩藉姞锛氭彁楂樻柊澧?Star 鏉冮噸涓庡畬鏁撮摼鎺ユ樉绀?

### 1. 鐢ㄦ埛瑕佹眰

鐢ㄦ埛瑕佹眰锛?

1. 灏嗘柊澧?Star 浣滀负閲嶈绛涢€変緷鎹€?
2. 閾炬帴閮ㄥ垎搴旀樉绀哄畬鏁撮摼鎺ワ紝鑰屼笉鏄彧鏄剧ず `GitHub`銆?

### 2. 璇勫垎璋冩暣

宸插皢缁煎悎璇勫垎鏉冮噸璋冩暣涓猴細

1. Star 澧為噺锛?0%
2. 鎬?Star锛?5%
3. 鍏磋叮涓婚鍖归厤锛?0%
4. 娲昏穬鏃堕棿鏂伴矞搴︼細10%
5. Fork锛?%

鍚屾椂鎺掑簭鏃跺鍔犳槑纭殑鍏滃簳椤哄簭锛?

```text
score -> star_growth -> stargazers_count
```

杩欐牱鏂板 Star 浼氭垚涓哄垽鏂€滄湰鍛ㄦ渶鐏垎鈥濈殑涓昏渚濇嵁銆?

### 3. 閾炬帴鏄剧ず璋冩暣

鍛ㄦ姤涓殑 GitHub 閾炬帴缁熶竴鏄剧ず涓哄畬鏁?URL锛屽苟淇濇寔鍙偣鍑伙細

```text
[https://github.com/owner/repo](https://github.com/owner/repo)
```

鎶ュ憡娓呮礂閫昏緫涔熶細鎶婃ā鍨嬬敓鎴愮殑鐭枃鏈摼鎺ワ細

```text
[GitHub](https://github.com/owner/repo)
```

杞崲涓哄畬鏁?URL 鏂囨湰閾炬帴銆?

### 4. 鏈湴楠岃瘉

宸茶ˉ鍏呮祴璇曪紝瑕嗙洊锛?

1. 鏂板 Star 瀵规帓搴忕殑浼樺厛褰卞搷銆?
2. 鍘熷 GitHub URL 杞崲涓哄畬鏁?URL 鏂囨湰閾炬帴銆?
3. `[GitHub](...)` 閾炬帴杞崲涓哄畬鏁?URL 鏂囨湰閾炬帴銆?

宸叉墽琛岋細

```text
py -m unittest
py -m compileall main.py src tests scripts
```

楠岃瘉缁撴灉锛氶€氳繃銆?

### 5. 褰撳墠椤甸潰閲嶆柊鐢熸垚

宸查噸鏂版墽琛岋細

```text
py main.py
py scripts/build_pages.py
```

褰撳墠 `2026-04-28` 鍛ㄦ姤宸叉寜鏂板 Star 楂樻潈閲嶉噸鏂版帓搴忥紝鍓嶄袱椤逛负锛?

1. `NousResearch/hermes-agent`锛屾柊澧?Star 25銆?
2. `affaan-m/everything-claude-code`锛屾柊澧?Star 10銆?

鎶ュ憡鍜?Pages 椤甸潰涓殑閾炬帴鍧囨樉绀哄畬鏁?URL銆?

---

## 2026-04-28 杩藉姞锛氱涓夐樁娈佃秼鍔挎€荤粨

### 1. 寮€鍙戠洰鐨?

缁х画绗笁闃舵浜у搧鍖栬緭鍑猴紝澧炲姞鏁版嵁椹卞姩鐨勮秼鍔挎€荤粨锛屽噺灏戝懆鎶ヨ秼鍔块儴鍒嗕緷璧栨ā鍨嬭嚜鐢卞彂鎸ャ€?

### 2. 鏈瀹炵幇

鏂板妯″潡锛?

```text
src/trends.py
```

璇ユā鍧楁牴鎹湰鏈熷叆閫変粨搴撶敓鎴愶細

1. 鍏ラ€夐」鐩€绘暟銆?
2. 绱鏂板 Star銆?
3. 涓昏璇█鍒嗗竷銆?
4. 椤圭洰鏂瑰悜鍒嗗竷銆?
5. 鏂板 Star 鏈€楂樼殑椤圭洰鍒楄〃銆?
6. 鍙洿鎺ュ啓鍏ュ懆鎶ョ殑瓒嬪娍瑕佺偣銆?

### 3. 褰掓。鏂囦欢

鏂板褰掓。璺緞锛?

```text
data/trends/YYYY-MM-DD.json
```

杩愯鎽樿鏂板瀛楁锛?

```text
trend_summary_path
```

### 4. 鎶ュ憡鐢熸垚鍙樺寲

Kimi 鐢熸垚鍛ㄦ姤鏃朵細鏀跺埌 `trend_summary`銆傚鏋滄湰鍦版湭閰嶇疆 Kimi锛岄檷绾х増鍛ㄦ姤涔熶細鍦ㄢ€滄湰鍛ㄨ秼鍔库€濋儴鍒嗗睍绀鸿秼鍔胯鐐广€?

### 5. 宸ヤ綔娴佸彉鍖?

`.github/workflows/weekly.yml` 鑷姩鎻愪氦鑼冨洿澧炲姞锛?

```text
data/trends
```

### 6. 鏈湴楠岃瘉

宸茶ˉ鍏呮祴璇曪細

1. `tests/test_trends.py`
2. `tests/test_reporter.py` 涓殑瓒嬪娍瑕佺偣灞曠ず鏂█

---

## 2026-04-29 杩藉姞锛氶樁娈垫€т唬鐮佸鏌ヨ褰?

### 1. 瀹℃煡鐩殑

鍦ㄨ秼鍔挎€荤粨鍔熻兘鎻愪氦鍚庯紝瀵瑰綋鍓嶄唬鐮佽繘琛岄樁娈垫€у鏌ワ紝纭宸茬粡瀹炵幇鐨勮兘鍔涖€佷粛瀛樺湪鐨勯闄╃偣锛屼互鍙婁笅涓€姝ュ紑鍙戜紭鍏堢骇銆?

鏈瀹℃煡鑼冨洿鍖呮嫭锛?

1. `main.py`
2. `src/collector.py`
3. `src/processor.py`
4. `src/reporter.py`
5. `src/settings.py`
6. `src/state.py`
7. `src/trends.py`
8. `.github/workflows/weekly.yml`
9. 鐜版湁娴嬭瘯鏂囦欢

### 2. 宸茬‘璁ゅ疄鐜扮殑鑳藉姏

褰撳墠椤圭洰宸茬粡瀹炵幇锛?

1. GitHub 杩戞湡娲昏穬浠撳簱閲囬泦銆?
2. 浠撳簱鍘婚噸銆佽繃婊ゃ€佽瘎鍒嗗拰鎺掑簭銆?
3. 鏂板 Star 鍘嗗彶璁板綍涓庤瘎鍒嗗姞鏉冦€?
4. README 鎽樿鎶撳彇銆?
5. Kimi 涓枃鍛ㄦ姤鐢熸垚銆?
6. Kimi 涓嶅彲鐢ㄦ椂鐢熸垚闄嶇骇鐗?Markdown 鍛ㄦ姤銆?
7. Telegram 鎵嬫満鎺ㄩ€併€?
8. Telegram 涓嶅彲鐢ㄦ椂淇濈暀褰掓。銆?
9. 鍛ㄦ姤銆佸師濮嬫暟鎹€佽繍琛屾憳瑕佸拰瓒嬪娍鎬荤粨褰掓。銆?
10. GitHub Actions 瀹氭椂杩愯銆佹墜鍔ㄨЕ鍙戝拰鑷姩鎻愪氦褰掓。銆?
11. GitHub Pages 鍛ㄦ姤褰掓。椤甸潰銆?
12. 鍗曞厓娴嬭瘯瑕嗙洊鏍稿績閲囬泦銆佸鐞嗐€佹姤鍛娿€佺姸鎬佸拰瓒嬪娍閫昏緫銆?

鏈湴楠岃瘉缁撴灉锛?

```text
py -m unittest
```

缁撴灉锛?0 涓祴璇曞叏閮ㄩ€氳繃銆?

### 3. 鏈瀹℃煡鍙戠幇

#### 闂 1锛氫粛淇濈暀 `created` 鏌ヨ锛屽彲鑳界户缁亸鍚戔€滄柊寤洪」鐩€?

浣嶇疆锛?

```text
src/collector.py:27
```

璇存槑锛?

鐢ㄦ埛宸茬粡鏄庣‘瑕佹眰鍏虫敞鈥滀竴鍛ㄥ唴鏈€鐏垎鐨勯」鐩€濓紝鑰屼笉鏄€滆繖涓€鍛ㄦ柊鍒涘缓鐨勯」鐩€濄€傚綋鍓嶄粛淇濈暀锛?

```text
created:>=... stars:>10
```

璇ユ煡璇細棰濆寮曞叆鏂板缓椤圭洰銆傝櫧鐒跺悗缁細缁忚繃娲昏穬鏃堕棿杩囨护锛屼絾瀹冧粛鍙兘褰卞搷鍊欓€夋睜鏉ユ簮銆?

寤鸿锛?

1. 涓嬩竴姝ョЩ闄よ鏌ヨ锛涙垨
2. 灏嗗叾浣滀负浣庢潈閲嶈ˉ鍏呮潵婧愶紝骞跺湪杩愯鎽樿涓爣鏄庛€?

#### 闂 2锛氶儴鍒?GitHub 鏌ヨ澶辫触涓嶄細杩涘叆杩愯鎽樿

浣嶇疆锛?

```text
src/collector.py:83-90
```

璇存槑锛?

褰撳墠閫昏緫鍙湁鍦ㄦ墍鏈夋煡璇㈤兘澶辫触鏃舵墠鎶涘嚭閿欒銆傚鏋滈儴鍒嗘煡璇㈠け璐ャ€侀儴鍒嗘垚鍔燂紝閿欒浼氳鍐呴儴鏀堕泦浣嗕笉浼氬啓鍏?`data/runs/YYYY-MM-DD.json`銆?

褰卞搷锛?

1. 鍛ㄦ姤鍙兘姝ｅ父鐢熸垚锛屼絾閲囬泦缁撴灉涓嶅畬鏁淬€?
2. 鍚庣画鏃犳硶浠庤繍琛屾憳瑕佷腑鍒ゆ柇鏄惁鍙戠敓 GitHub API 闄愭祦銆佺綉缁滃紓甯告垨鏌ヨ璇硶闂銆?

寤鸿锛?

灏嗛儴鍒嗘煡璇㈠け璐ヨ褰曞啓鍏?`RunSummary`锛屼緥濡傛柊澧烇細

```text
collector_errors
```

#### 闂 3锛氬彧璇诲彇 example 閰嶇疆锛屼笉鍒╀簬鑷畾涔夊叴瓒ｉ厤缃?

浣嶇疆锛?

```text
src/settings.py:49
```

璇存槑锛?

褰撳墠 `load_settings` 鍥哄畾璇诲彇锛?

```text
config/interests.example.json
```

杩欎細璁╃ず渚嬮厤缃壙鎷呯湡瀹為厤缃亴璐ｏ紝涓嶅埄浜庣敤鎴烽暱鏈熺淮鎶よ嚜宸辩殑鍏磋叮鍋忓ソ銆?

寤鸿锛?

浼樺厛璇诲彇锛?

```text
config/interests.json
```

濡傛灉涓嶅瓨鍦紝鍐嶅洖閫€鍒帮細

```text
config/interests.example.json
```

#### 闂 4锛歚data/raw` 瀹為檯鍐欏叆鐨勬槸绛涢€夊悗椤圭洰

浣嶇疆锛?

```text
main.py:41
```

璇存槑锛?

褰撳墠璋冪敤锛?

```text
write_raw_repositories(selected, settings)
```

鍐欏叆鐨勬槸鏈€缁堝叆閫夐」鐩紝鑰屼笉鏄師濮嬮噰闆嗙粨鏋溿€俙raw` 鍛藉悕瀹规槗璇鍚庣画璋冭瘯銆?

寤鸿锛?

浜岄€変竴澶勭悊锛?

1. 濡傛灉瑕佷繚鐣欑湡姝ｅ師濮嬮噰闆嗙粨鏋滐紝搴斿啓鍏?`collected`銆?
2. 濡傛灉鍙兂淇濈暀鍏ラ€夐」鐩紝搴斿皢鍑芥暟鎴栫洰褰曞懡鍚嶈皟鏁翠负 `selected`銆?

### 4. 涓嬩竴姝ュ缓璁?

涓嬩竴姝ヤ紭鍏堝鐞嗭細

1. 淇閲囬泦鏌ヨ锛岀Щ闄ゆ垨寮卞寲 `created` 鏌ヨ銆?
2. 澧炲己杩愯鎽樿锛岃褰曢儴鍒嗛噰闆嗗け璐ャ€?
3. 澧炲姞 `config/interests.json` 鐢ㄦ埛閰嶇疆浼樺厛绾с€?
4. 鏄庣‘ `data/raw` 涓庡叆閫夐」鐩綊妗ｇ殑鍛藉悕鍜岃亴璐ｃ€?

杩欎簺鏀瑰姩灞炰簬鏁版嵁璐ㄩ噺鍜屽彲瑙傛祴鎬у寮猴紝涓嶉渶瑕佹帹缈荤幇鏈夋灦鏋勩€?

---

## 2026-04-29 杩藉姞锛氫唬鐮佸鏌ラ棶棰樹慨澶?

### 1. 淇鑼冨洿

鏍规嵁闃舵鎬т唬鐮佸鏌ョ殑涓嬩竴姝ュ缓璁紝鏈缁х画澶勭悊鏁版嵁璐ㄩ噺鍜屽彲瑙傛祴鎬ч棶棰樸€?

### 2. 閲囬泦鏌ヨ淇

宸蹭粠 `src/collector.py` 涓Щ闄わ細

```text
created:>=... stars:>10
```

褰撳墠閲囬泦鏌ヨ鍙洿缁曟渶杩戜竴鍛?`pushed` 娲昏穬椤圭洰灞曞紑锛岄伩鍏嶅€欓€夋睜缁х画鍋忓悜鈥滄湰鍛ㄦ柊鍒涘缓椤圭洰鈥濄€?

### 3. 閮ㄥ垎閲囬泦澶辫触璁板綍

`collect_repositories` 鐜板湪浼氳繑鍥烇細

```text
repositories
queries
errors
```

濡傛灉閮ㄥ垎 GitHub 鏌ヨ澶辫触浣嗕粛鏈夊叾浠栨煡璇㈡垚鍔燂紝绋嬪簭浼氱户缁敓鎴愬懆鎶ワ紝鍚屾椂鎶婇敊璇啓鍏ヨ繍琛屾憳瑕侊細

```text
collector_errors
```

杩欐牱鍚庣画鍙互浠?`data/runs/YYYY-MM-DD.json` 鍒ゆ柇閲囬泦鏄惁瀹屾暣銆?

### 4. 鑷畾涔夊叴瓒ｉ厤缃?

`src/settings.py` 鏂板鐢ㄦ埛閰嶇疆浼樺厛绾э細

1. 浼樺厛璇诲彇 `config/interests.json`銆?
2. 濡傛灉涓嶅瓨鍦紝鍐嶈鍙?`config/interests.example.json`銆?

杩欐牱鐢ㄦ埛鍙互缁存姢鑷繁鐨勫叴瓒ｉ厤缃紝涓嶉渶瑕佺洿鎺ヤ慨鏀圭ず渚嬫枃浠躲€?

### 5. 褰掓。鑱岃矗鏄庣‘

鏈灏嗗師濮嬪€欓€夋暟鎹拰鏈€缁堝叆閫夋暟鎹媶寮€锛?

1. `data/raw/YYYY-MM-DD.json`锛氫繚瀛樻湰娆?GitHub API 閲囬泦鍒扮殑鍘熷鍊欓€変粨搴撱€?
2. `data/selected/YYYY-MM-DD.json`锛氫繚瀛樻渶缁堝叆閫夊懆鎶ョ殑浠撳簱銆?

`.github/workflows/weekly.yml` 鐨勮嚜鍔ㄦ彁浜よ寖鍥翠篃宸插姞鍏ワ細

```text
data/selected
```

### 6. 娴嬭瘯琛ュ厖

鏂板鍜屾洿鏂版祴璇曪細

1. 閲囬泦鏌ヨ涓嶅啀鍖呭惈 `created` 鏉′欢銆?
2. 閮ㄥ垎閲囬泦澶辫触浼氳繑鍥為敊璇垪琛ㄣ€?
3. `config/interests.json` 浼樺厛浜庣ず渚嬮厤缃€?
4. `data/raw` 鍜?`data/selected` 鍐欏叆涓嶅悓璺緞銆?

---

## 2026-04-29 杩藉姞锛氶厤缃鏄庤ˉ鍏?

### 1. 琛ュ厖鍘熷洜

浠ｇ爜宸茬粡鏀寔浼樺厛璇诲彇 `config/interests.json`锛屼絾閰嶇疆鏂囨。涓繕娌℃湁璇存槑璇ユ枃浠剁殑鐢ㄩ€斿拰鎻愪氦鏂瑰紡銆?

### 2. 鏈鏇存柊

宸叉洿鏂帮細

```text
docs/setup.md
```

鏂板鍐呭锛?

1. `config/interests.json` 鐨勮鍙栦紭鍏堢骇銆?
2. `preferred_topics`銆乣preferred_languages`銆乣exclude_keywords`銆乣max_projects`銆乣min_stars` 鐨勭敤閫斻€?
3. 濡傛灉甯屾湜 GitHub Actions 浣跨敤鑷畾涔夊叴瓒ｉ厤缃紝闇€瑕佸皢 `config/interests.json` 鎻愪氦鍒颁粨搴撱€?
4. `config/interests.json` 涓嶅簲鍖呭惈浠讳綍 API Key銆乀oken 鎴?Chat ID銆?

### 3. 澶勭悊缁撹

鏈涓嶆妸 `config/interests.json` 鍔犲叆 `.gitignore`銆傚師鍥犳槸璇ユ枃浠朵笉鏄瘑閽ユ枃浠讹紝骞朵笖 GitHub Actions 闇€瑕佷粠浠撳簱璇诲彇瀹冩墠鑳戒娇鐢ㄨ嚜瀹氫箟鍋忓ソ銆?

---

## 2026-04-29 杩藉姞锛欸itHub Actions 鐪熷疄杩愯澶嶆祴

### 1. 澶嶆祴缁撴灉

宸查€氳繃 GitHub CLI 鎵嬪姩瑙﹀彂姣忓懆鍛ㄦ姤宸ヤ綔娴侊細

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25087537033
```

杩愯缁撹锛氭垚鍔熴€?

鍏抽敭缁撴灉锛?

1. `collected_count`: 210
2. `selected_count`: 10
3. `collector_errors`: []
4. `readme_fetched_count`: 10
5. `telegram_sent`: true
6. `raw_repositories_path`: `data/raw/2026-04-29.json`
7. `selected_repositories_path`: `data/selected/2026-04-29.json`
8. `trend_summary_path`: `data/trends/2026-04-29.json`

### 2. 鍙戠幇鐨勯棶棰?

鏈 Kimi 璋冪敤瓒呮椂锛岃繍琛屾憳瑕佽褰曪細

```text
"report_error": "The read operation timed out"
```

鍥犳鏈鍛ㄦ姤浣跨敤闄嶇骇妯℃澘鐢熸垚锛屼絾涓绘祦绋嬨€乀elegram 鎺ㄩ€佸拰褰掓。鍧囨垚鍔熴€?

### 3. 淇鍔ㄤ綔

宸插皢 Kimi 璇锋眰瓒呮椂鏃堕棿浠庡浐瀹?60 绉掕皟鏁翠负鍙厤缃」锛?

```text
KIMI_TIMEOUT_SECONDS
```

榛樿鍊间负锛?

```text
120
```

鍚屾椂鏇存柊 `.env.example` 鍜?`docs/setup.md`銆?

---

## 2026-04-29 杩藉姞锛欸itHub Actions Node 24 鍏煎鏇存柊

### 1. 瑙﹀彂鍘熷洜

GitHub Actions 杩愯鏃舵彁绀?`actions/checkout@v4` 鍜?`actions/setup-python@v5` 浠嶈繍琛屽湪 Node.js 20銆侴itHub 宸叉彁绀?Node.js 20 actions 灏嗚寮冪敤銆?

### 2. 瀹樻柟鐗堟湰纭

宸茬‘璁ゅ畼鏂?action 鏂扮増鏈細

1. `actions/checkout@v6`锛氭敮鎸?Node 24銆?
2. `actions/setup-python@v6`锛氭敮鎸?Node 24銆?

### 3. 鏈璋冩暣

宸叉洿鏂帮細

```text
.github/workflows/weekly.yml
```

璋冩暣鍐呭锛?

```text
actions/checkout@v4 -> actions/checkout@v6
actions/setup-python@v5 -> actions/setup-python@v6
```

### 4. 棰勬湡鏁堟灉

鍚庣画姣忓懆鍛ㄦ姤宸ヤ綔娴佷笉鍐嶈Е鍙?Node.js 20 action 寮冪敤璀﹀憡銆?

---

## 2026-04-29 杩藉姞锛欿imi 鍐呭杩囨护闄嶇骇淇

### 1. 闂鐜拌薄

鐢ㄦ埛鍦?GitHub 缃戦〉鎵嬪姩瑙﹀彂宸ヤ綔娴佸悗锛屽伐浣滄祦鏈韩杩愯鎴愬姛锛屼絾鐢熸垚鐨勬槸闄嶇骇鐗堝懆鎶ャ€?

杩愯鎽樿鏄剧ず锛?

```text
"kimi_used": false
"fallback_used": true
"report_error": "Kimi API error 400: ... high risk ... content_filter"
```

### 2. 鍘熷洜鍒ゆ柇

杩欐涓嶆槸瓒呮椂锛屼篃涓嶆槸 Secrets 鏈厤缃€侹imi API 杩斿洖浜嗗唴瀹硅繃婊ら敊璇紝璇存槑璇锋眰涓殑鎻愮ず璇嶆垨椤圭洰鏁版嵁琚垽瀹氫负楂橀闄┿€?

鏈€鍙兘鐨勮Е鍙戞簮鏄煇涓叆閫変粨搴撶殑 README 鎽樿鍖呭惈妯″瀷瀹夊叏绛栫暐涓嶆帴鍙楃殑鍘熸枃鍐呭銆?

### 3. 淇鍔ㄤ綔

宸插湪 `src/reporter.py` 涓鍔犲畨鍏ㄩ噸璇曪細

1. 绗竴娆′粛浣跨敤瀹屾暣椤圭洰鏁版嵁锛屽寘鎷?README 鎽樿銆?
2. 濡傛灉 Kimi 杩斿洖 `content_filter` 鎴?`high risk`锛岃嚜鍔ㄩ噸璇曚竴娆°€?
3. 閲嶈瘯鏃剁Щ闄?`readme_excerpt`锛屽彧淇濈暀浠撳簱鍚嶇О銆佺畝浠嬨€佽瑷€銆丼tar銆丗ork銆侀摼鎺ャ€佸垎绫汇€佽秼鍔挎憳瑕佺瓑缁撴瀯鍖栦俊鎭€?
4. 濡傛灉閲嶈瘯鎴愬姛锛屽垯涓嶅啀鐢熸垚闄嶇骇鐗堝懆鎶ャ€?
5. 濡傛灉閲嶈瘯浠嶅け璐ワ紝鎵嶄繚鐣欏師鏈夐檷绾ч€昏緫锛岄伩鍏嶆暣涓伐浣滄祦涓柇銆?

### 4. 璇存槑

澶栭儴妯″瀷 API 浠嶅彲鑳藉洜涓烘湇鍔′笉鍙敤銆侀檺娴佹垨鏇翠弗鏍肩殑瀹夊叏绛栫暐澶辫触锛屽洜姝ゆ棤娉曠粷瀵逛繚璇佹案杩滀笉鍑虹幇闄嶇骇鐗堛€備絾鏈淇宸茬粡閽堝褰撳墠鐪熷疄澶辫触鍘熷洜鍋氫簡鍏滃簳锛岃兘鏄捐憲闄嶄綆鍥?README 鍘熸枃瑙﹀彂鍐呭杩囨护鑰岄檷绾х殑姒傜巼銆?

### 5. 娴嬭瘯琛ュ厖

宸插鍔犳祴璇曪細褰撶涓€娆?Kimi 璋冪敤杩斿洖 `content_filter high risk` 鏃讹紝绋嬪簭浼氳嚜鍔ㄤ互涓嶅寘鍚?README 鎽樿鐨?payload 閲嶈瘯锛屽苟鍦ㄩ噸璇曟垚鍔熸椂杩斿洖 Kimi 鍛ㄦ姤銆?

---

## 2026-04-29 杩藉姞锛欳odex 鎶€鑳藉皝瑁?

### 1. 寮€鍙戠洰鐨?

璺嚎鍥剧涓夐樁娈垫渶鍚庝竴椤规槸鈥滃湪椤圭洰娴佺▼绋冲畾鍚庯紝鍐嶅皝瑁呯湡姝ｅ彲鐢ㄧ殑 Codex 鎶€鑳解€濄€傚綋鍓嶉噰闆嗐€佺瓫閫夈€並imi 鍛ㄦ姤銆乀elegram 鎺ㄩ€併€佸綊妗ｅ拰 GitHub Actions 宸插畬鎴愬娆＄湡瀹炶繍琛岄獙璇侊紝鍥犳寮€濮嬪皝瑁呮妧鑳姐€?

### 2. 鏈瀹炵幇

鏂板鎶€鑳界洰褰曪細

```text
skills/github-weekly-agent/
```

鏍稿績鏂囦欢锛?

```text
skills/github-weekly-agent/SKILL.md
```

鎶€鑳藉唴瀹硅鐩栵細

1. 椤圭洰缁存姢绾︽潫銆?
2. 涓绘祦绋嬨€?
3. 鐩綍鑱岃矗銆?
4. 閲囬泦涓庢帓搴忎慨鏀硅鑼冦€?
5. 鍛ㄦ姤鐢熸垚淇敼瑙勮寖銆?
6. 褰掓。鍜?GitHub Pages 淇敼瑙勮寖銆?
7. GitHub Actions 淇敼瑙勮寖銆?
8. 鏈湴楠岃瘉鍜岀湡瀹為摼璺獙璇佹柟寮忋€?

### 3. 绠€娲佹€у鐞?

鏈鍙垱寤哄繀瑕佺殑鎶€鑳借鏄庯紝涓嶅鍔犺剼鏈€佹ā鏉挎垨璧勪骇锛岄伩鍏嶉噸澶嶇淮鎶ゅ凡鏈夐」鐩唬鐮併€?

### 4. 璺嚎鍥炬洿鏂?

`docs/roadmap.md` 涓涓夐樁娈?Codex 鎶€鑳藉皝瑁呮爣璁颁负宸插畬鎴愩€?

---

## 2026-04-29 杩藉姞锛氭湭鏉ユ洿鏂拌鍒?

### 1. 瑙勫垝鐩殑

褰撳墠鍓嶄笁闃舵宸茬粡瀹屾垚锛岄」鐩叿澶囩ǔ瀹氱殑閲囬泦銆佺瓫閫夈€並imi 鍛ㄦ姤銆乀elegram 鎺ㄩ€併€佸綊妗ｃ€丟itHub Pages 鍜?Codex 鎶€鑳借兘鍔涖€?

涓轰簡閬垮厤鍚庣画寮€鍙戠洿鎺ュ爢鍒颁富娴佺▼涓紝鏈琛ュ厖闀挎湡鏇存柊璺嚎鍜屾灦鏋勮竟鐣屻€?

### 2. 鏂板鏂囨。

鏂板锛?

```text
docs/future-plan.md
```

璇ユ枃妗ｈ鍒掞細

1. 鏁版嵁璐ㄩ噺澧炲己銆?
2. 澶氭暟鎹簮閲囬泦銆?
3. 鎶ュ憡璐ㄩ噺澧炲己銆?
4. 鎺ㄩ€佹笭閬撴墿灞曘€?
5. 灞曠ず椤甸潰澧炲己銆?
6. 闀挎湡鐘舵€佸拰 SQLite 璇勪及銆?
7. 鐭湡銆佷腑鏈熴€侀暱鏈熶紭鍏堢骇銆?
8. 鏆備笉寤鸿鍋氱殑浜嬮」銆?

### 3. 鍚屾鏇存柊

宸叉洿鏂帮細

1. `docs/roadmap.md`锛氬鍔犵鍥涢樁娈靛拰绗簲闃舵銆?
2. `docs/architecture.md`锛氬鍔犲悗缁墿灞曡竟鐣屻€?
3. `docs/index.md`锛氬鍔犳湭鏉ユ洿鏂拌鍒掑叆鍙ｃ€?

### 4. 璁捐缁撹

鍚庣画涓嶅簲鎻愬墠閲嶆瀯涓哄鏉傛鏋躲€傚綋鍓嶄富娴佺▼淇濇寔绋冲畾锛屽彧鏈夊綋鏌愮被鑳藉姏寮€濮嬪寘鍚涓疄鐜版垨鏄庢樉鍙樺鏉傛椂锛屽啀鎷嗗嚭 `sources`銆乣quality`銆乣report_checks`銆乣channels`銆乣storage` 绛夋ā鍧椼€?

---

## 2026-04-29 杩藉姞锛氬畨鍏ㄦ鏌ュ熀纭€鐗堟湰

### 1. 鐢ㄦ埛瑕佹眰

鐢ㄦ埛瑕佹眰鍦ㄦ湭鏉ヨ鍒掍腑鍔犲叆瀹夊叏鎬ф鏌ュ姛鑳斤紝鐢ㄤ簬妫€鏌ラ」鐩槸鍚﹀瓨鍦ㄥ畨鍏ㄩ闄╋紝鍚屾椂瀵瑰綋鍓嶅伐浣滄柟寮忓仛瀹夊叏淇濇姢銆?

### 2. 褰撳墠瀹夊叏鐘舵€佹鏌?

宸叉鏌ワ細

1. GitHub CLI 褰撳墠鏈櫥褰曪紝鏈満娌℃湁缁х画淇濈暀 CLI 鐧诲綍鎬併€?
2. 褰撳墠杩涚▼鐜涓湭鍙戠幇 `TOKEN`銆乣KEY`銆乣SECRET`銆乣CHAT_ID` 绛夊瘑閽ョ被鐜鍙橀噺鍚嶃€?
3. 鏈鎿嶄綔涓嶈鍙栥€佷笉杈撳嚭浠讳綍鐪熷疄瀵嗛挜鍊笺€?

### 3. 鏈瀹炵幇

鏂板锛?

```text
scripts/security_check.py
tests/test_security_check.py
```

鑳藉姏锛?

1. 鎵弿婧愮爜銆侀厤缃€亀orkflow銆佹枃妗ｅ拰鎻愮ず璇嶄腑鐨勭枒浼肩‖缂栫爜瀵嗛挜銆?
2. 妫€娴?GitHub token銆乀elegram Bot Token銆侀€氱敤 key/token/secret/password/chat_id 璧嬪€笺€?
3. 鍏佽 GitHub Actions Secrets 寮曠敤鍜?`os.getenv` 杩欑被瀹夊叏璇诲彇鏂瑰紡銆?
4. 鎺掗櫎 `data/` 鍜?`reports/`锛岄伩鍏嶆妸绗笁鏂?README 鎴栫敓鎴愭姤鍛婅鍒や负椤圭洰鑷韩瀵嗛挜銆?

### 4. 宸ヤ綔娴佹帴鍏?

`.github/workflows/weekly.yml` 鏂板姝ラ锛?

```text
python scripts/security_check.py
```

璇ユ楠ゅ湪鍗曞厓娴嬭瘯鍓嶈繍琛屻€傚鏋滃彂鐜扮枒浼肩‖缂栫爜瀵嗛挜锛屽伐浣滄祦浼氬け璐ワ紝闃绘缁х画鐢熸垚鍜屾彁浜ゅ綊妗ｃ€?

### 5. 鏈潵瑙勫垝鏇存柊

`docs/future-plan.md` 鏂板鈥滃畨鍏ㄩ闄╂鏌モ€濋樁娈碉紝鍚庣画浼氭墿灞曞埌鍏ラ€変粨搴撻闄╂彁绀猴紝渚嬪鍙枒鍏抽敭璇嶃€佸紓甯?Star 澧為暱銆佽鍙瘉缂哄け鍜岀淮鎶ら闄┿€?

---

## 2026-04-29 杩藉姞锛氬叆閫変粨搴撳畨鍏ㄩ闄╂彁绀?

### 1. 寮€鍙戠洰鐨?

鍦ㄩ」鐩嚜韬瘑閽ユ壂鎻忎箣鍚庯紝缁х画澧炲姞鍏ラ€変粨搴撶殑瀹夊叏椋庨櫓鎻愮ず鑳藉姏銆傝鑳藉姏鐢ㄤ簬鎻愰啋鐢ㄦ埛鍏虫敞娼滃湪椋庨櫓锛屼笉瀵圭涓夋柟椤圭洰鍋氬畨鍏ㄨ儗涔︺€?

### 2. 鏈瀹炵幇

鏂板锛?

```text
src/security.py
tests/test_security.py
```

`Repository` 鏂板瀛楁锛?

```text
security_flags
```

涓绘祦绋嬪湪鎶撳彇 README 鍚庯紝瀵规渶缁堝叆閫変粨搴撴墽琛岋細

```text
apply_security_flags(selected)
```

### 3. 褰撳墠妫€鏌ヨ寖鍥?

褰撳墠鍙仛鍏冩暟鎹骇妫€鏌ワ細

1. 缂哄皯璁稿彲璇併€?
2. 浠撳簱宸插綊妗ｃ€?
3. 浠撳簱鏄?fork銆?
4. 鍚嶇О銆佺畝浠嬨€佷富棰樻垨 README 鎽樿涓寘鍚槑鏄鹃闄╁叧閿瘝锛屼緥濡傜┖鎶曘€佽禒閫併€佺牬瑙ｃ€佺獌鍙栥€佹伓鎰忚蒋浠躲€侀挀楸笺€?

### 4. 鎶ュ憡鍙樺寲

闄嶇骇鐗堝懆鎶ョ殑閲嶇偣椤圭洰鍒嗘瀽涓柊澧烇細

```text
椋庨櫓鎻愮ず
```

Kimi 鍛ㄦ姤鐢熸垚涔熶細鏀跺埌 `security_flags` 瀛楁锛屽彲鐢ㄤ簬鐢熸垚鏇磋皑鎱庣殑椤圭洰璇存槑銆?

### 5. 瀹夊叏杈圭晫

鏈姛鑳戒笉浼氭墽琛岀涓夋柟浠撳簱浠ｇ爜锛屼笉浼氫笅杞芥垨杩愯椤圭洰渚濊禆锛屼篃涓嶄細鎶婇」鐩垽瀹氫负瀹夊叏銆傞闄╂彁绀哄彧浣滀负浜哄伐澶嶆牳绾跨储銆?

---

## 2026-04-29 杩藉姞锛氬叆閫夊師鍥犺褰?

### 1. 寮€鍙戠洰鐨?

缁х画绗洓闃舵璐ㄩ噺涓庡彲瑙傛祴鎬у寮猴紝澧炲姞姣忎釜鍏ラ€夐」鐩殑瑙ｉ噴瀛楁锛岃鐢ㄦ埛鐭ラ亾椤圭洰涓轰粈涔堣繘鍏ュ懆鎶ャ€?

### 2. 鏈瀹炵幇

`Repository` 鏂板瀛楁锛?

```text
selection_reasons
```

`src/processor.py` 浼氭牴鎹互涓嬩俊鍙风敓鎴愬叆閫夊師鍥狅細

1. 鏂板 Star銆?
2. 褰撳墠绱 Star銆?
3. 涓婚銆佽瑷€鎴栧悕绉颁笌鍏虫敞鏂瑰悜鍖归厤銆?
4. 鏈€杩戜竴鍛ㄤ粛鏈夋洿鏂版垨缁存姢娲诲姩銆?

### 3. 鎶ュ憡鍙樺寲

闄嶇骇鐗堝懆鎶ュ湪閲嶇偣椤圭洰鍒嗘瀽涓柊澧烇細

```text
鍏ラ€夊師鍥?
```

Kimi 鎻愮ず璇嶄篃宸叉洿鏂帮紝瑕佹眰浼樺厛浣跨敤 `selection_reasons` 瑙ｉ噴椤圭洰涓轰粈涔堝€煎緱鍏虫敞锛屽苟缁撳悎 `security_flags` 淇濇寔璋ㄦ厧琛ㄨ堪銆?

### 4. 褰掓。鍙樺寲

`data/selected/YYYY-MM-DD.json` 浼氫繚瀛樻瘡涓」鐩殑 `selection_reasons` 瀛楁锛屼负鍚庣画鎶ュ憡璐ㄩ噺妫€鏌ュ拰椤甸潰灞曠ず鎻愪緵鍩虹鏁版嵁銆?

---

## 2026-04-29 杩藉姞锛氭姤鍛婅川閲忔鏌?

### 1. 寮€鍙戠洰鐨?

缁х画绗洓闃舵璐ㄩ噺涓庡彲瑙傛祴鎬у寮猴紝闄嶄綆 Kimi 杈撳嚭缂洪」銆侀摼鎺ユ牸寮忛敊璇垨璇█缈昏瘧涓嶅綋鐨勬鐜囥€?

### 2. 鏈瀹炵幇

鏂板锛?

```text
src/report_checks.py
tests/test_report_checks.py
```

褰撳墠妫€鏌ヨ寖鍥达細

1. 鎶ュ憡涓笉鑳藉嚭鐜扳€滆煉铔団€濊繖绫讳笉鍚堥€傜殑鎶€鏈瑷€缈昏瘧銆?
2. 姣忎釜鍏ラ€夐」鐩殑瀹屾暣浠撳簱鍚嶅繀椤诲嚭鐜板湪鎶ュ憡涓€?
3. 姣忎釜鍏ラ€夐」鐩殑 GitHub 閾炬帴蹇呴』浠ュ畬鏁?URL 鐨?Markdown 閾炬帴褰㈠紡鍑虹幇銆?

### 3. 涓绘祦绋嬪彉鍖?

Kimi 杈撳嚭浼氬厛缁忚繃锛?

```text
normalize_report_markdown
check_report_quality
```

濡傛灉璐ㄩ噺妫€鏌ュけ璐ワ紝绋嬪簭浼氳褰?`report_error`锛屽苟鍥為€€鍒拌鍒欏懆鎶ワ紝閬垮厤鎶婄粨鏋勪笉瀹屾暣鐨勬ā鍨嬭緭鍑烘帹閫佺粰鐢ㄦ埛銆?

### 4. 鍚庣画绌洪棿

鍚庣画鍙互缁х画澧炲己锛?

1. 妫€鏌ユ姤鍛婃槸鍚﹀寘鍚潪鍏ラ€夐」鐩€?
2. 瀵圭粨鏋勯棶棰樺鍔?Kimi 鑷姩閲嶈瘯锛岃€屼笉鏄洿鎺ュ洖閫€銆?
3. 妫€鏌ユ瘡涓」鐩槸鍚﹀寘鍚叆閫夊師鍥犲拰椋庨櫓鎻愮ず銆?

---

## 2026-04-29 杩藉姞锛氶噰闆嗗垎椤圭粺璁?

### 1. 寮€鍙戠洰鐨?

缁х画绗洓闃舵璐ㄩ噺涓庡彲瑙傛祴鎬у寮恒€傛鍓嶈繍琛屾憳瑕佸彧璁板綍 `collector_errors`锛屾棤娉曟竻妤氱湅鍒版瘡鏉?GitHub Search 鏌ヨ鐨勬垚鍔熴€佸け璐ュ拰杩斿洖鏁伴噺銆?

### 2. 鏈瀹炵幇

`collect_repositories` 鐜板湪杩斿洖锛?

```text
repositories
queries
errors
stats
```

杩愯鎽樿鏂板瀛楁锛?

```text
collector_stats
```

姣忔潯缁熻鍖呭惈锛?

1. `query`锛氭煡璇㈡潯浠躲€?
2. `status`锛歚success` 鎴?`failed`銆?
3. `count`锛氳繑鍥炰粨搴撴暟閲忋€?
4. `error`锛氬け璐ュ師鍥犮€?

### 3. 浠峰€?

鍚庣画鍙互浠?`data/runs/YYYY-MM-DD.json` 鐩存帴鍒ゆ柇锛?

1. 鍝簺鏌ヨ鎴愬姛銆?
2. 鍝簺鏌ヨ澶辫触銆?
3. 姣忔潯鏌ヨ璐＄尞浜嗗灏戝€欓€変粨搴撱€?
4. 鏄惁瀛樺湪 GitHub API 闄愭祦銆佺綉缁滃紓甯告垨鏌ヨ璇硶闂銆?

璇ョ粨鏋勪篃涓哄悗缁?GitHub Trending銆丟raphQL API 绛夊鏁版嵁婧愭墿灞曢鐣欎簡缁熻鍏ュ彛銆?

---

## 2026-04-29 杩藉姞锛欸itHub Pages 棣栭〉鎽樿澧炲己

### 1. 寮€鍙戠洰鐨?

缁х画绗洓闃舵璐ㄩ噺涓庡彲瑙傛祴鎬у寮猴紝璁?GitHub Pages 棣栭〉涓嶅彧鏄剧ず鍛ㄦ姤鍒楄〃锛屼篃鑳藉揩閫熺湅鍒版渶鏂拌繍琛岀姸鎬佸拰瓒嬪娍瑕佺偣銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/build_pages.py
tests/test_build_pages.py
```

棣栭〉鏂板锛?

1. 鏈€鏂拌繍琛屾憳瑕併€?
2. 鍏ラ€夐」鐩暟銆?
3. 閲囬泦鍊欓€夋暟銆?
4. 鐢熸垚鏂瑰紡銆?
5. Telegram 鎺ㄩ€佺姸鎬併€?
6. 閲囬泦閿欒鏁伴噺銆?
7. 鏈€鏂拌秼鍔胯鐐广€?

### 3. 鏁版嵁鏉ユ簮

棣栭〉璇诲彇锛?

```text
data/runs/YYYY-MM-DD.json
data/trends/YYYY-MM-DD.json
```

### 4. 璁捐杈圭晫

鏈浠嶄繚鎸?GitHub Pages 涓鸿交閲?Markdown锛屼笉寮曞叆鍓嶇妗嗘灦銆傚悗缁綋鍘嗗彶鍛ㄦ姤鏁伴噺澧炲姞鍚庯紝鍐嶈€冭檻绛涢€夈€侀」鐩崱鐗囧拰瓒嬪娍鍙鍖栥€?

---

## 2026-04-29 杩藉姞锛氬巻鍙插懆鎶ヨ秼鍔挎憳瑕?

### 1. 寮€鍙戠洰鐨?

缁х画澧炲己 GitHub Pages 鐨勬祻瑙堟晥鐜囷紝璁┾€滃叏閮ㄥ懆鎶モ€濆垪琛ㄤ笉浠呮樉绀烘棩鏈熷拰鎺ㄩ€佺姸鎬侊紝涔熻兘蹇€熺湅鍑烘瘡鏈熺殑涓昏璇█銆佷富瑕佹柟鍚戝拰鏂板 Star銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/build_pages.py
tests/test_build_pages.py
```

`docs/index.md` 鐨勬瘡鏉″巻鍙插懆鎶ヨ褰曚細鍦ㄥ瓨鍦ㄨ秼鍔挎暟鎹椂杩藉姞锛?

1. 涓昏瑷€銆?
2. 涓绘柟鍚戙€?
3. 绱鏂板 Star銆?

### 3. 鏁版嵁鏉ユ簮

璇ヤ俊鎭潵鑷細

```text
data/trends/YYYY-MM-DD.json
```

濡傛灉鍘嗗彶鍛ㄦ姤娌℃湁瓒嬪娍鏁版嵁锛屽垯淇濇寔鍘熸湁绠€娲佹牸寮忋€?

---

## 2026-04-29 杩藉姞锛氬巻鍙查」鐩储寮?

### 1. 寮€鍙戠洰鐨?

缁х画澧炲己 GitHub Pages 娴忚鑳藉姏锛岃鐢ㄦ埛涓嶅彧鎸夊懆鎶ユ棩鏈熷洖鐪嬶紝涔熻兘鍦ㄤ竴涓〉闈腑鏌ョ湅鍘嗘鍏ラ€夐」鐩€?

### 2. 鏈瀹炵幇

`scripts/build_pages.py` 鏂板鐢熸垚锛?

```text
docs/projects.md
```

璇ラ〉闈粠浠ヤ笅鐩綍璇诲彇鏁版嵁锛?

```text
data/selected/
```

骞剁敓鎴愬巻鍙查」鐩〃鏍硷紝鍖呭惈锛?

1. 鏃ユ湡銆?
2. 椤圭洰鍚嶇О銆?
3. 鏂瑰悜銆?
4. 璇█銆?
5. Star銆?
6. 鏂板 Star銆?
7. 椋庨櫓鎻愮ず鏁伴噺銆?
8. 瀹屾暣 GitHub 閾炬帴銆?

### 3. 棣栭〉鍏ュ彛

`docs/index.md` 鐨勯」鐩枃妗ｅ尯鍩熸柊澧烇細

```text
鍘嗗彶椤圭洰绱㈠紩
```

### 4. 璁捐杈圭晫

鏈浠嶄繚鎸?Markdown 椤甸潰锛屼笉寮曞叆鍓嶇妗嗘灦銆傚悗缁鏋滃巻鍙查」鐩槑鏄惧澶氾紝鍐嶈€冭檻鎸夎瑷€銆佹柟鍚戙€佹棩鏈熺敓鎴愭洿缁嗙殑鍒嗙粍椤甸潰銆?

---

## 2026-04-29 杩藉姞锛欸itHub Trending 绗竴浼樺厛绾ч噰闆?

### 1. 鐢ㄦ埛瑕佹眰

鐢ㄦ埛鏄庣‘甯屾湜浠?GitHub Trending 浣滀负鐑偣鑰冩牳鐨勭涓€鎸囨爣锛屽叾浣欎俊鍙蜂綔涓鸿緟鍔╋紝鍚屾椂淇濈暀鍨傜洿鏂瑰悜閰嶇疆锛屾柟渚垮悗缁仛涓€у寲璋冩暣銆?

### 2. 鏋舵瀯鍒ゆ柇

鏈娌℃湁鎻愬墠鎷嗗嚭鏂扮殑 `src/sources/` 鐩綍锛岃€屾槸鍦ㄧ幇鏈?`src/collector.py` 涓帴鍏?Trending銆傚師鍥犳槸褰撳墠鍙湁涓や釜鏉ユ簮锛欸itHub Trending 鍜?GitHub Search API锛岀洿鎺ュ湪閲囬泦灞傛墿灞曟洿绠€娲侊紱绛夊悗缁帴鍏?GraphQL銆佽嚜瀹氫箟浠撳簱鍒楄〃鎴栨洿澶氭潵婧愭椂锛屽啀鎷嗗垎鏉ユ簮妯″潡銆?

褰撳墠鏁版嵁婧愬畾浣嶏細

1. GitHub Trending 鍛ㄦ锛氱涓€浼樺厛绾у€欓€夋潵婧愩€?
2. GitHub Search API锛氳緟鍔╁€欓€夋潵婧愶紝涓昏鐢ㄤ簬琛ュ厖鍨傜洿鏂瑰悜鍜?Trending 閬楁紡椤圭洰銆?
3. 鍚庣画棰勭暀锛欸raphQL 缁嗙矑搴︾儹搴︺€佺敤鎴疯嚜瀹氫箟鍏虫敞浠撳簱銆?

### 3. 鏈瀹炵幇

鏇存柊锛?

```text
src/models.py
src/collector.py
src/processor.py
config/interests.example.json
tests/test_collector.py
tests/test_processor.py
docs/architecture.md
docs/future-plan.md
docs/setup.md
```

鏂板浠撳簱瀛楁锛?

1. `sources`锛氳褰曢」鐩潵鑷?`github_trending`銆乣github_search` 鎴栧涓潵婧愩€?
2. `trending_rank`锛氳褰曢」鐩湪 GitHub Trending 鍛ㄦ涓殑鎺掑悕銆?
3. `trending_period`锛氬綋鍓嶄负 `weekly`銆?
4. `source_priority`锛氱敤浜庝繚鐣欐潵婧愪紭鍏堢骇锛孴rending 楂樹簬 Search銆?

閲囬泦娴佺▼璋冩暣涓猴細

```text
GitHub Trending weekly
-> GitHub Search API 杈呭姪鏌ヨ
-> 鍘婚噸骞跺悎骞舵潵婧愪俊鍙?
-> 杩囨护鏈€杩戜竴鍛ㄦ椿璺冮」鐩?
-> 缁煎悎璇勫垎鎺掑簭
```

### 4. 璇勫垎璋冩暣

褰撳墠榛樿璇勫垎鏉冮噸锛?

1. `trending`锛?5%銆?
2. `star_growth`锛?5%銆?
3. `topic`锛?5%銆?
4. `freshness`锛?0%銆?
5. `community`锛?%銆?

鍏朵腑 `community` 鐢辨€?Star 鍜?Fork 鍏卞悓鏋勬垚銆傝璁捐鎶?Trending 浣滀负绗竴鎸囨爣锛屽悓鏃朵繚鐣欐柊澧?Star銆佸瀭鐩存柟鍚戝尮閰嶃€佽繎鏈熸椿璺冨拰绀惧尯鍩虹淇″彿銆?

### 5. 涓€у寲棰勭暀

`config/interests.example.json` 鏂板锛?

1. `enable_github_trending`锛氭槸鍚﹀惎鐢?Trending銆?
2. `trending_languages`锛氶澶栭噰闆嗘寚瀹氳瑷€鐨?Trending 姒溿€?
3. `trending_max_repositories`锛氶檺鍒舵瘡涓?Trending 姒滆ˉ榻愯鎯呯殑椤圭洰鏁般€?
4. `search_topics`锛歋earch API 鐨?topic 琛ュ厖鏂瑰悜銆?
5. `search_languages`锛歋earch API 鐨勮瑷€琛ュ厖鏂瑰悜銆?
6. `score_weights`锛氱患鍚堣瘎鍒嗘潈閲嶃€?

鍚庣画鐢ㄦ埛鍙互閫氳繃 `config/interests.json` 璋冩暣杩欎簺瀛楁锛屼笉闇€瑕佹敼涓绘祦绋嬩唬鐮併€?

---

## 2026-04-29 杩藉姞锛歍rending 淇″彿灞曠ず澧炲己

### 1. 寮€鍙戠洰鐨?

涓婁竴杞凡缁忔妸 GitHub Trending 鍛ㄦ浣滀负绗竴浼樺厛绾у€欓€夋潵婧愩€傛湰杞户缁ˉ榻愬彲瑙佹€э細璁╁懆鎶ャ€佽秼鍔挎憳瑕佸拰 GitHub Pages 鍘嗗彶椤圭洰绱㈠紩閮借兘鐩存帴鐪嬪埌椤圭洰鏉ユ簮涓?Trending 鎺掑悕锛屾柟渚垮垽鏂帓搴忔槸鍚︾鍚堚€淭rending 浼樺厛鈥濈殑璁捐銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
prompts/weekly_report.md
src/reporter.py
src/trends.py
scripts/build_pages.py
tests/test_reporter.py
tests/test_trends.py
tests/test_build_pages.py
```

鍏蜂綋鍙樺寲锛?

1. Kimi 鎻愮ず璇嶈姹備紭鍏堣В閲?`trending_rank`锛屽苟璇存槑 `sources` 鏉ユ簮銆?
2. 闄嶇骇鍛ㄦ姤鐨勯」鐩€昏鏂板鈥滄潵婧愨€濆拰鈥淭rending 鎺掑悕鈥濄€?
3. 閲嶇偣椤圭洰鍒嗘瀽鏂板鈥滅儹搴︽潵婧愨€濄€?
4. 瓒嬪娍鎽樿鏂板 `trending_project_count` 鍜?`top_trending`銆?
5. GitHub Pages 鍘嗗彶椤圭洰绱㈠紩鏂板鈥滄潵婧愨€濆拰鈥淭rending 鎺掑悕鈥濆垪銆?

### 3. 璁捐杈圭晫

鏈鍙寮哄睍绀轰笌鎽樿锛屼笉鏀瑰彉閲囬泦鎺掑簭閫昏緫銆傛帓搴忛€昏緫浠嶇敱涓婁竴杞殑 `score_weights` 鎺у埗锛屽悗缁彲浠ラ€氳繃 `config/interests.json` 璋冩暣鏉冮噸銆?

---

## 2026-04-29 杩藉姞锛歍rending 椤甸潰闈炰粨搴撻摼鎺ヨ繃婊?

### 1. 闂鏉ユ簮

妫€鏌?GitHub Actions 鑷姩褰掓。鍥炴潵鐨?`data/runs/2026-04-29.json` 鍚庡彂鐜帮紝GitHub Trending 閲囬泦宸茬粡鐢熸晥锛屼絾椤甸潰瑙ｆ瀽鍣ㄦ妸閮ㄥ垎闈炰粨搴撻摼鎺ヤ篃褰撴垚浠撳簱锛屼緥濡傦細

```text
sponsors/explore
apps/dependabot
apps/github-actions
```

杩欎簺璺緞涓嶆槸鏅€氫粨搴擄紝璋冪敤 GitHub 浠撳簱璇︽儏 API 鏃朵細杩斿洖 404锛屽鑷磋繍琛屾憳瑕佷腑鍑虹幇涓嶅繀瑕佺殑 `collector_errors`銆?

### 2. 鏈淇

鏇存柊锛?

```text
src/collector.py
tests/test_collector.py
```

淇鏂瑰紡锛?

1. 鍦?Trending 閾炬帴瑙ｆ瀽闃舵杩囨护 `sponsors`銆乣apps`銆乣users`銆乣settings` 绛夐潪浠撳簱璺緞鍓嶇紑銆?
2. 淇濈暀鐪熷疄浠撳簱璺緞瑙ｆ瀽閫昏緫锛屼笉鏀瑰彉 Trending 浼樺厛绾у拰璇勫垎閫昏緫銆?
3. 澧炲姞鍗曞厓娴嬭瘯锛岀‘淇?`sponsors/explore` 鍜?`apps/dependabot` 涓嶄細杩涘叆 Trending 浠撳簱鍊欓€夊垪琛ㄣ€?

### 3. 棰勬湡鏁堟灉

涓嬩竴娆?GitHub Actions 杩愯鏃讹紝Trending 鏉ユ簮鐨?404 鍣０搴旀槑鏄惧噺灏戙€傝嫢 GitHub 椤甸潰缁撴瀯缁х画鍙樺寲锛屽悗缁啀鑰冭檻鎶婅В鏋愯鍒欐敹绱у埌 Trending 椤圭洰鍗＄墖鍖哄煙銆?

---

## 2026-04-29 杩藉姞锛歍rending 鏍囬鍖哄煙瑙ｆ瀽鏀剁揣

### 1. 寮€鍙戠洰鐨?

涓婁竴杞€氳繃杩囨护闈炰粨搴撹矾寰勫噺灏戜簡 Trending 閲囬泦鍣０銆傛湰杞户缁敹绱цВ鏋愯竟鐣岋紝閬垮厤鏈潵 GitHub Trending 椤甸潰鏂板鍏朵粬涓ゆ寮忛摼鎺ユ椂鍐嶆琚鍒や负浠撳簱銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/collector.py
tests/test_collector.py
```

瑙ｆ瀽瑙勫垯浠庘€滆鍙栭〉闈腑鎵€鏈夊舰濡?`/owner/repo` 鐨勯摼鎺モ€濊皟鏁翠负锛?

```text
鍙鍙?article 鍐?h2 鏍囬鍖哄煙涓殑浠撳簱閾炬帴
```

杩欐牱鍙互鏇磋创杩?GitHub Trending 椤圭洰鍗＄墖缁撴瀯锛岄伩鍏嶉〉闈㈠鑸€佽禐鍔╁叆鍙ｃ€佸簲鐢ㄥ叆鍙ｆ垨椤圭洰鍗＄墖鍐呴儴鐨勮緟鍔╅摼鎺ヨ繘鍏ュ€欓€夋睜銆?

### 3. 娴嬭瘯琛ュ厖

娴嬭瘯涓柊澧炰簡浠ヤ笅鍣０閾炬帴锛?

```text
/outside/not-repository
/inside/not-repository
```

纭瀹冧滑涓嶄細琚В鏋愪负 Trending 鍊欓€変粨搴撱€?

---

## 2026-04-29 杩藉姞锛氭灦鏋勩€佸畨鍏ㄤ笌鍐椾綑瀹℃煡

### 1. 瀹℃煡鑼冨洿

鏈瀹℃煡浜嗗綋鍓嶄富娴佺▼鍜屾牳蹇冩ā鍧楋細

```text
main.py
src/collector.py
src/processor.py
src/reporter.py
src/archive.py
src/security.py
src/state.py
scripts/security_check.py
```

### 2. 鏋舵瀯缁撹

褰撳墠鏋舵瀯浠嶇劧娓呮櫚锛屼富娴佺▼淇濇寔涓猴細

```text
collector -> processor -> reporter -> archive -> sender
```

GitHub Trending 宸茬粡浣滀负绗竴浼樺厛绾у€欓€夋潵婧愭帴鍏ワ紝GitHub Search API 浣滀负杈呭姪鏉ユ簮銆傚綋鍓嶈繕涓嶉渶瑕佺珛鍒绘媶鍒?`src/sources/`锛屽洜涓烘暟鎹簮鏁伴噺鍜屽鏉傚害浠嶅彲鐢?`collector.py` 鎵胯浇銆傚悗缁帴鍏?GraphQL銆佽嚜瀹氫箟浠撳簱鍒楄〃鎴?OSSInsight 鏃讹紝鍐嶆媶鍒嗘潵婧愭ā鍧楁洿鍚堥€傘€?

### 3. 瀹夊叏缁撹

褰撳墠鏈彂鐜扮‖缂栫爜瀵嗛挜椋庨櫓锛?

1. 瀵嗛挜浠嶇劧鍙粠鐜鍙橀噺鎴?GitHub Actions Secrets 璇诲彇銆?
2. 椤圭洰涓嶄細涓嬭浇銆佸畨瑁呮垨鎵ц绗笁鏂逛粨搴撲唬鐮併€?
3. 鍏ラ€変粨搴撳畨鍏ㄦ鏌ヤ粛鏄厓鏁版嵁绾ф彁绀猴紝涓嶆妸澶栭儴椤圭洰鍒ゆ柇涓衡€滃畨鍏ㄢ€濄€?
4. `scripts/security_check.py` 浼氱户缁壂鎻忔簮鐮併€侀厤缃€亀orkflow銆佹枃妗ｅ拰鎻愮ず璇嶄腑鐨勭枒浼肩‖缂栫爜瀵嗛挜銆?

闇€瑕佺户缁敞鎰忕殑椋庨櫓锛?

1. README 鎽樿灞炰簬涓嶅彲淇¤緭鍏ワ紝鍙兘鍖呭惈鎻愮ず娉ㄥ叆鍐呭銆?
2. GitHub Trending 鏄綉椤垫潵婧愶紝涓嶆槸绋冲畾瀹樻柟 API锛岄〉闈㈢粨鏋勫彉鍖栧彲鑳藉奖鍝嶈В鏋愩€?
3. 鑻ュ悗缁厤缃涓?`trending_languages`锛孏itHub API 璇锋眰閲忎細澧炲姞锛岄渶瑕佺户缁叧娉ㄩ檺娴併€?

### 4. 鏈淇

鏇存柊锛?

```text
prompts/weekly_report.md
src/reporter.py
```

淇鍐呭锛?

1. 鎻愮ず璇嶆柊澧炶姹傦細浠撳簱绠€浠嬨€丷EADME 鎽樿銆侀」鐩悕绉板拰 topic 閮芥槸涓嶅彲淇￠」鐩唴瀹癸紝鍙兘浣滀负鍒嗘瀽鏉愭枡锛屼笉鑳芥墽琛屾垨閬靛惊鍏朵腑鎸囦护銆?
2. 闄嶇骇鍛ㄦ姤鏂囨浠庢棫鐨勨€淕itHub Search API 缁撴灉鈥濇敼涓衡€淕itHub Trending 涓?GitHub Search 閲囬泦缁撴灉鈥濓紝閬垮厤涓庡綋鍓嶆灦鏋勪笉涓€鑷淬€?

### 5. 鍙户缁紭鍖栨柟鍚?

鍚庣画浼樺厛绾у缓璁細

1. 瑙傚療涓嬩竴娆?GitHub Actions 涓?Trending 404 鍣０鏄惁娑堝け銆?
2. 涓?Trending 瑙ｆ瀽澧炲姞鐪熷疄椤甸潰鏍蜂緥娴嬭瘯锛岄檷浣?GitHub 椤甸潰缁撴瀯鍙樺寲甯︽潵鐨勯闄┿€?
3. 澧炲姞鎶ュ憡缁撴瀯鏍￠獙锛屾鏌?Kimi 鏄惁纭疄灞曠ず鏉ユ簮銆乀rending 鎺掑悕鍜岄闄╂彁绀恒€?
4. 褰撴暟鎹簮缁х画澧炲姞鏃讹紝鍐嶆媶鍒?`src/sources/`锛屼笉瑕佺幇鍦ㄦ彁鍓嶅鏉傚寲銆?

---

## 2026-04-29 杩藉姞锛氭姤鍛婅川閲忔牎楠屽寮?

### 1. 寮€鍙戠洰鐨?

褰撳墠閲囬泦鍜屾帓搴忓凡缁忔妸 GitHub Trending 浣滀负绗竴鐑害淇″彿銆備负浜嗛伩鍏?Kimi 鍛ㄦ姤婕忔帀鍏抽敭瀛楁锛屾湰杞寮烘姤鍛婅川閲忔牎楠岋紝璁╂ā鍨嬭緭鍑哄繀椤讳綋鐜伴」鐩潵婧愩€乀rending 鎺掑悕鍜岄闄╂彁绀恒€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/report_checks.py
src/reporter.py
tests/test_report_checks.py
```

鏍￠獙瑙勫垯锛?

1. 濡傛灉椤圭洰鍖呭惈 `sources`锛屾姤鍛婁腑闇€瑕佸嚭鐜板搴旀潵婧愶紝渚嬪 `GitHub Trending` 鎴?`GitHub Search`銆?
2. 濡傛灉椤圭洰鍖呭惈澶т簬 0 鐨?`trending_rank`锛屾姤鍛婁腑闇€瑕佸嚭鐜?`Trending` 鍜屽搴旀帓鍚嶆暟瀛椼€?
3. 濡傛灉椤圭洰鍖呭惈 `security_flags`锛屾姤鍛婁腑闇€瑕佸嚭鐜伴闄╂彁绀虹浉鍏冲唴瀹广€?

杩欎簺瑙勫垯鍙湪瀵瑰簲鏁版嵁瀛樺湪鏃惰Е鍙戯紝涓嶄細瑕佹眰鏅€?Search 椤圭洰寮鸿灞曠ず Trending 鎺掑悕銆?

### 3. 鍐椾綑鏂囨淇

闄嶇骇鍛ㄦ姤缁撹鏂囨涓粛鎻愬埌鈥滃悗缁姞鍏?README 娣卞害鍒嗘瀽鍜屽巻鍙插幓閲嶁€濓紝浣嗚繖涓ょ被鑳藉姏宸茬粡閮ㄥ垎瀹炵幇銆傛湰杞敼涓烘彁閱掔敤鎴蜂紭鍏堟煡鐪?Trending 鎺掑悕闈犲墠銆佽繎鏈熷闀挎槑鏄句笖鍖归厤鍏磋叮鐨勯」鐩紝骞跺己璋冨鐢ㄥ墠浠嶉渶浜哄伐瀹℃煡浠ｇ爜銆佷緷璧栧拰璁稿彲璇併€?

---

## 2026-04-29 杩藉姞锛歍elegram 鏀逛负鎺ㄩ€佸懆鎶ラ摼鎺?

### 1. 鐢ㄦ埛瑕佹眰

鐢ㄦ埛甯屾湜 Telegram 涓洿鎺ユ帹閫?GitHub Actions 杩愯鍚庣敱 Kimi 鐢熸垚骞跺綊妗ｅ埌 GitHub Pages 鐨勫懆鎶ラ摼鎺ワ紝鑰屼笉鏄帹閫佸畬鏁?Markdown 姝ｆ枃锛屾柟渚垮湪鎵嬫満涓婇槄璇汇€傚悓鏃堕渶瑕佷负鍚庣画鎺ュ叆寰俊銆侀涔︾瓑娓犻亾棰勭暀鍏ュ彛銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/sender.py
src/settings.py
tests/test_sender.py
.env.example
docs/setup.md
docs/future-plan.md
```

鍏蜂綋鍙樺寲锛?

1. `send_report` 涓嶅啀鎶婂畬鏁?Markdown 鎷嗗垎鍙戦€佸埌 Telegram銆?
2. 鏂板 `build_report_message`锛岀粺涓€鏋勫缓鐭増鎺ㄩ€佹秷鎭€?
3. 鏂板 `report_url`锛岀敤浜庣敓鎴愬懆鎶ュ叕寮€璁块棶閾炬帴銆?
4. 鏂板 `REPORT_BASE_URL` 閰嶇疆锛岄€傞厤鑷畾涔夊煙鍚嶃€佽嚜瀹氫箟 Pages 璺緞鎴栨湭鏉ュ叾浠栧睍绀哄叆鍙ｃ€?
5. 濡傛灉鏈厤缃?`REPORT_BASE_URL`锛孏itHub Actions 涓細鏍规嵁 `GITHUB_REPOSITORY` 鑷姩鎺ㄥ GitHub Pages 閾炬帴銆?

榛樿閾炬帴鏍煎紡锛?

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.md
```

### 3. 鍚庣画娓犻亾棰勭暀

褰撳墠浠嶄繚鎸?Telegram 鍗曟笭閬擄紝涓嶆彁鍓嶅垱寤哄鏉傜殑 `channels` 妗嗘灦銆傚悗缁帴鍏ュ井淇°€侀涔︽椂锛屽彲浠ュ鐢?`build_report_message` 鍜?`report_url`锛屽彧鏂板瀵瑰簲娓犻亾鐨勫彂閫佸嚱鏁板嵆鍙€?

---

## 2026-04-29 杩藉姞锛歍rending 鍏ラ€変繚搴曚笌 Telegram 瓒呴摼鎺ヤ慨澶?

### 1. 闂鐜拌薄

鐢ㄦ埛鍙嶉鐪熷疄杩愯鍚庝粛鐒舵病鏈夋妸 GitHub Trending 鏀惧湪瓒冲閲嶈鐨勪綅缃紝甯屾湜 Trending 鍛ㄦ鍓?10 鐨勯」鐩嚦灏戞湁 7 涓繘鍏ョ儹鐐归」鐩懆鎶ャ€傚悓鏃?Telegram 鎺ㄩ€佷腑鐨勫懆鎶ュ湴鍧€涓嶈兘鐩存帴鐐瑰嚮锛岄渶瑕佷互瓒呴摼鎺ュ舰寮忓彂閫併€?

### 2. 鍘熷洜鍒ゆ柇

浠呬緷璧栬瘎鍒嗘潈閲嶄粛鍙兘璁╅珮 Star銆侀珮澧為暱鐨?Search API 椤圭洰鎸ゆ帀 Trending Top 10 椤圭洰銆傚彟涓€涓殣钘忓師鍥犳槸鍘嗗彶鍘婚噸浼氬湪鎺掑簭鍓嶈繃婊ゅ凡鎺ㄩ€侀」鐩紝濡傛灉鏌愪釜 Trending Top 10 椤圭洰涔嬪墠鍙戣繃锛屽畠浼氳鎸″湪鍛ㄦ姤澶栥€?

Telegram 渚х殑闂鏄綋鍓嶆秷鎭彧鍙戦€佺函鏂囨湰鍦板潃锛岃€屼笖榛樿鐢熸垚鐨勬槸 `.md` 鍦板潃锛汫itHub Pages 鏇撮€傚悎浣跨敤 `.html` 椤甸潰鍦板潃銆?

### 3. 鏈瀹炵幇

鏇存柊锛?

```text
src/processor.py
src/state.py
src/sender.py
config/interests.example.json
tests/test_processor.py
tests/test_state.py
tests/test_sender.py
docs/setup.md
docs/future-plan.md
```

鍏蜂綋鍙樺寲锛?

1. `process_repositories` 鏂板 Trending Top 10 淇濆簳閫夋嫨閫昏緫銆?
2. 榛樿 `min_trending_top10_projects` 涓?`7`锛屽嵆 Trending 鍓?10 涓嚦灏?7 涓繘鍏ュ懆鎶ワ紱濡傛灉鍙敤椤圭洰涓嶈冻 7 涓紝鍒欎繚鐣欏疄闄呭彲鐢ㄦ暟閲忋€?
3. `filter_unsent_repositories` 瀵?Trending Top 10 椤圭洰鏀捐锛岄伩鍏嶅巻鍙插幓閲嶆尅鎺夋湰鍛ㄧ湡姝ｇ儹闂ㄩ」鐩€?
4. Telegram 娑堟伅鏀逛负 HTML 瓒呴摼鎺ワ細`鎵撳紑鏈懆鍛ㄦ姤`銆?
5. 鍛ㄦ姤閾炬帴浠?GitHub Pages 鐨?`.md` 鍦板潃鏀逛负 `.html` 鍦板潃锛屾洿閫傚悎娴忚鍣ㄧ洿鎺ユ墦寮€銆?

### 4. 璁捐杈圭晫

璇ヨ鍒欏彧淇濇姢 Trending 鍛ㄦ鍓?10锛屼笉鍙栨秷鍏朵粬 Search API 杈呭姪椤圭洰銆傚懆鎶ュ墿浣欏悕棰濅粛鎸夌患鍚堣瘎鍒嗚ˉ榻愶紝缁х画淇濈暀鍨傜洿鏂瑰悜鍜屼釜鎬у寲璋冩暣绌洪棿銆?

---

## 2026-04-29 杩藉姞锛歅ages 鍘嗗彶椤圭洰绱㈠紩鎻愪氦鑼冨洿淇

### 1. 闂鏉ユ簮

澶嶆牳 workflow 鏃跺彂鐜帮紝`scripts/build_pages.py` 浼氱敓鎴愶細

```text
docs/projects.md
```

浣?`.github/workflows/weekly.yml` 鐨勮嚜鍔ㄦ彁浜よ寖鍥村彧鍖呭惈 `docs/index.md` 鍜?`docs/weekly`锛屾病鏈夊寘鍚?`docs/projects.md`銆傝繖浼氬鑷?GitHub Actions 杩愯鍚庯紝鍘嗗彶椤圭洰绱㈠紩鍙兘娌℃湁闅忔渶鏂版暟鎹竴璧锋彁浜ゃ€?

### 2. 鏈淇

鏇存柊锛?

```text
.github/workflows/weekly.yml
```

灏?`docs/projects.md` 鍔犲叆鑷姩鎻愪氦鑼冨洿锛岀‘淇濇瘡娆″懆鎶ョ敓鎴愬悗锛孏itHub Pages 棣栭〉銆佸懆鎶ラ〉闈㈠拰鍘嗗彶椤圭洰绱㈠紩閮借兘鍚屾鍒锋柊銆?

---

## 2026-04-29 杩藉姞锛歍elegram 閾炬帴鍙戦€侀『搴忚皟鏁?

### 1. 闂鏉ユ簮

Telegram 宸茬粡鏀逛负鎺ㄩ€?GitHub Pages 鍛ㄦ姤閾炬帴锛屼絾鍘熸祦绋嬫槸鍦?`main.py` 鍐呯敓鎴愭姤鍛婂悗绔嬪嵆鍙戦€?Telegram銆傛鏃?`scripts/build_pages.py` 杩樻病鏈夌敓鎴?`docs/weekly/YYYY-MM-DD.md`锛孏itHub Actions 涔熻繕娌℃湁鎶婇〉闈㈡彁浜ゅ埌浠撳簱锛屽洜姝ょ敤鎴风偣鍑婚摼鎺ユ椂鍙兘閬囧埌椤甸潰灏氭湭鍙戝竷鐨勯棶棰樸€?

### 2. 鏈璋冩暣

鏇存柊锛?

```text
main.py
scripts/send_report_link.py
.github/workflows/weekly.yml
tests/test_send_report_link.py
```

鏂扮殑 Actions 椤哄簭锛?

```text
python main.py锛堣烦杩?Telegram锛?
python scripts/build_pages.py
鎻愪氦 reports/data/docs 褰掓。
python scripts/send_report_link.py锛堝彂閫?Pages 閾炬帴锛?
鎻愪氦 data/runs 鍜?data/state 涓殑鎺ㄩ€佺姸鎬?
```

### 3. 璁捐杈圭晫

1. 鏈湴杩愯 `python main.py` 榛樿浠嶅彲鐩存帴灏濊瘯鍙戦€?Telegram锛屼繚鎸佸吋瀹广€?
2. GitHub Actions 涓€氳繃 `SKIP_TELEGRAM_SEND=true` 璺宠繃涓绘祦绋嬪唴鍙戦€侊紝鏀圭敱褰掓。鎻愪氦鍚庣殑鐙珛鑴氭湰鍙戦€併€?
3. 濡傛灉 Telegram 鏈厤缃垨鍙戦€佸け璐ワ紝鑴氭湰浼氳褰曠姸鎬侊紝浣嗕笉闃绘柇宸茬粡瀹屾垚鐨勫懆鎶ュ綊妗ｃ€?

---

## 2026-04-30 杩藉姞锛氳繍琛屾憳瑕佽褰?Telegram 鍛ㄦ姤閾炬帴

### 1. 寮€鍙戠洰鐨?

Telegram 鏀逛负鎺ㄩ€?GitHub Pages 鍛ㄦ姤閾炬帴鍚庯紝闇€瑕佸湪杩愯鎽樿涓褰曞疄闄呭彂閫佺殑閾炬帴锛屾柟渚夸粠 GitHub 浠撳簱鐩存帴鎺掓煡鏈鎺ㄩ€佹槸鍚︽寚鍚戞纭〉闈€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/models.py
main.py
scripts/send_report_link.py
tests/test_send_report_link.py
```

鏂板杩愯鎽樿瀛楁锛?

```text
telegram_report_url
```

璇ュ瓧娈佃褰曟湰娆″彂閫佸埌 Telegram 鐨?GitHub Pages 鍛ㄦ姤椤甸潰鍦板潃锛屼緥濡傦細

```text
https://windsky922.github.io/githubzhuaqu/weekly/YYYY-MM-DD.html
```

### 3. 浣跨敤浠峰€?

鍚庣画鎺掓煡 Telegram 鎺ㄩ€佹椂锛屽彲浠ョ洿鎺ユ墦寮€ `data/runs/YYYY-MM-DD.json`锛岀‘璁わ細

1. `telegram_sent` 鏄惁涓?`true`銆?
2. `telegram_error` 鏄惁涓虹┖銆?
3. `telegram_report_url` 鏄惁鏄鏈熺殑鍛ㄦ姤椤甸潰銆?

---

## 2026-04-30 杩藉姞锛欸itHub Pages 鍐呴儴閾炬帴淇

### 1. 寮€鍙戠洰鐨?

Telegram 宸叉敼涓烘帹閫?GitHub Pages 鐨?`.html` 鍛ㄦ姤椤甸潰锛屼絾褰掓。棣栭〉涓粛浣跨敤 `weekly/YYYY-MM-DD.md` 浣滀负鍛ㄦ姤鍏ュ彛銆備负浜嗚鎵嬫満绔拰 Pages 椤甸潰鍐呯殑璺宠浆璺緞淇濇寔涓€鑷达紝鏈灏嗛〉闈㈠鑸摼鎺ョ粺涓€鏀逛负鏈€缁堢綉椤靛湴鍧€銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/build_pages.py
tests/test_build_pages.py
```

璋冩暣鍐呭锛?

1. 鍛ㄦ姤褰掓。棣栭〉涓殑鏈€鏂板懆鎶ラ摼鎺ユ敼涓?`weekly/YYYY-MM-DD.html`銆?
2. 鍏ㄩ儴鍛ㄦ姤鍒楄〃涓殑鍘嗗彶鍛ㄦ姤閾炬帴鏀逛负 `weekly/YYYY-MM-DD.html`銆?
3. 棣栭〉涓殑椤圭洰鏂囨。瀵艰埅鏀逛负 `.html` 閾炬帴锛岄€傞厤 GitHub Pages 鏈€缁堟覆鏌撻〉闈€?
4. 鍘嗗彶椤圭洰绱㈠紩鐨勮繑鍥為摼鎺ユ敼涓?`index.html`銆?
5. 淇鍘嗗彶椤圭洰绱㈠紩鍦ㄦ殏鏃犻」鐩椂鐨勮〃鏍煎垪鏁帮紝閬垮厤琛ㄦ牸缁撴瀯涓嶅畬鏁淬€?

### 3. 楠岃瘉鏂瑰紡

鏂板鍗曞厓娴嬭瘯瑕嗙洊锛?

1. 棣栭〉鏄惁杈撳嚭 `.html` 鍛ㄦ姤閾炬帴銆?
2. 鏂囨。瀵艰埅鏄惁杈撳嚭 `.html` 閾炬帴銆?
3. 鏆傛棤椤圭洰鏃讹紝鍘嗗彶椤圭洰绱㈠紩琛ㄦ牸鏄惁浠嶄繚鎸佸畬鏁村垪鏁般€?

---

## 2026-04-30 杩藉姞锛氭帹閫佺煭娑堟伅缁撴瀯棰勭暀

### 1. 寮€鍙戠洰鐨?

褰撳墠鍙渶瑕?Telegram 鎺ㄩ€侊紝浣嗗悗缁彲鑳芥帴鍏ュ井淇°€侀涔︽垨閭欢銆備负浜嗛伩鍏嶄互鍚庢妸 Telegram 鐨?HTML 鏂囨澶嶅埗鍒板叾浠栨笭閬擄紝鏈鍦ㄤ笉鍒涘缓澶嶆潅 `channels/` 妗嗘灦鐨勫墠鎻愪笅锛屽厛鎶藉嚭缁熶竴鐨勭煭娑堟伅缁撴瀯銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/sender.py
tests/test_sender.py
```

鏂板锛?

```text
DeliveryMessage
build_delivery_message
```

瀛楁璇存槑锛?

1. `title`锛氬懆鎶ユ爣棰樸€?
2. `url`锛欸itHub Pages 鍛ㄦ姤閾炬帴銆?
3. `text`锛氱函鏂囨湰娑堟伅锛岄€傚悎鍚庣画寰俊銆侀涔︽垨閭欢澶嶇敤銆?
4. `html_text`锛欻TML 娑堟伅锛屽綋鍓?Telegram 浣跨敤瀹冩潵鍙戦€佸彲鐐瑰嚮瓒呴摼鎺ャ€?

### 3. 鏋舵瀯杈圭晫

鏈娌℃湁鎻愬墠鍒涘缓 `src/channels/` 鐩綍锛屼篃娌℃湁鍔犲叆寰俊銆侀涔︽垨閭欢渚濊禆銆傚彧鏈夊綋绗簩涓湡瀹炴帹閫佹笭閬撴帴鍏ユ椂锛屽啀鎶婂悇娓犻亾鍙戦€佸嚱鏁版媶鍑虹嫭绔嬫ā鍧椼€?

---

## 2026-04-30 杩藉姞锛氬畨鍏ㄦ鏌?allowlist 鏀剁揣

### 1. 寮€鍙戠洰鐨?

椤圭洰瑕佹眰涓嶈兘鍦ㄤ唬鐮佷腑纭紪鐮?API Key銆乀oken銆丆hat ID 鎴栦换浣曞瘑閽ャ€傚師瀹夊叏妫€鏌ヤ細瀵瑰寘鍚?`os.getenv(` 鐨勬暣琛岀洿鎺ユ斁琛岋紝杩欏湪姝ｅ父璇诲彇鐜鍙橀噺鏃舵病鏈夐棶棰橈紝浣嗗鏋滄湁浜哄啓鍏ュ甫鐪熷疄瀵嗛挜鐨勯粯璁ゅ€硷紝渚嬪 `os.getenv("TOKEN", "鐪熷疄 token")`锛屽氨鍙兘琚紡妫€銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/security_check.py
tests/test_security_check.py
```

璋冩暣鍐呭锛?

1. allowlist 涓嶅啀鏁磋璺宠繃鎵€鏈夎鍒欍€?
2. 瀵?GitHub token 鍜?Telegram bot token 杩欑被鍏锋湁鏄庣‘鏍煎紡鐨勫瘑閽ワ紝濮嬬粓鎵ц妫€娴嬨€?
3. 浠嶇劧鍏佽 GitHub Actions Secrets 寮曠敤鍜岀幆澧冨彉閲忕ず渚嬮€氳繃閫氱敤閰嶇疆妫€鏌ワ紝閬垮厤璇姤姝ｅ父閰嶇疆銆?
4. 鏂板娴嬭瘯瑕嗙洊 `os.getenv` 榛樿鍊间腑钘忓叆 GitHub token 鐨勬儏鍐点€?

### 3. 瀹夊叏杈圭晫

璇ユ鏌ュ彧鑳藉彂鐜板父瑙佹牸寮忓拰鏄庢樉纭紪鐮佺殑瀵嗛挜锛屼笉鑳芥浛浠?GitHub Secret Scanning 鎴栦汉宸ュ鏌ャ€傚悗缁鏋滄帴鍏ユ洿澶氬閮ㄦ湇鍔★紝闇€瑕佺户缁ˉ鍏呭搴?token 鏍煎紡瑙勫垯銆?

---

## 2026-04-30 杩藉姞锛氭帓闄ょ敓鎴愬懆鎶ョ洰褰曠殑瀵嗛挜璇姤

### 1. 寮€鍙戠洰鐨?

`docs/weekly/` 鏄敱 `reports/` 鍚屾鐢熸垚鐨?GitHub Pages 鍛ㄦ姤鐩綍锛岄噷闈㈠彲鑳藉寘鍚涓夋柟浠撳簱 README 鎽樿銆傚畨鍏ㄦ鏌ョ殑鐩爣鏄繚鎶ゆ湰椤圭洰婧愮爜銆侀厤缃拰鎵嬪啓鏂囨。涓笉瑕佺‖缂栫爜瀵嗛挜锛屼笉搴旀妸绗笁鏂圭敓鎴愬唴瀹硅鍒や负鏈」鐩嚜韬硠婕忋€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/security_check.py
tests/test_security_check.py
```

璋冩暣鍐呭锛?

1. 鏂板 `EXCLUDED_PATH_PREFIXES`锛屽綋鍓嶅彧鎺掗櫎 `docs/weekly/`銆?
2. 淇濈暀 `docs/setup.md`銆乣docs/operation-log.md` 绛夋墜鍐欐枃妗ｆ壂鎻忋€?
3. 鏂板娴嬭瘯纭 `docs/weekly/` 涓殑鐤戜技 token 浼氳璺宠繃銆?
4. 鏂板娴嬭瘯纭鏅€?`docs/` 鏂囨。浠嶄細琚壂鎻忋€?

### 3. 瀹夊叏杈圭晫

璇ヨ皟鏁村彧澶勭悊璇姤鏉ユ簮锛屼笉闄嶄綆瀵归」鐩簮鐮併€亀orkflow銆侀厤缃€佹彁绀鸿瘝鍜屾墜鍐欐枃妗ｇ殑妫€鏌ュ己搴︺€傜敓鎴愬懆鎶ヤ粛鐒朵細闀挎湡褰掓。锛屽洜姝ゅ悗缁彲浠ヨ€冭檻鍦ㄦ姤鍛婄敓鎴愰樁娈靛 README 鎽樿鍋氭洿淇濆畧鐨勮劚鏁忓鐞嗐€?

---

## 2026-04-30 杩藉姞锛氱涓夋柟鍐呭鍏ュ簱鍓嶈劚鏁?

### 1. 寮€鍙戠洰鐨?

鍛ㄦ姤浼氫繚瀛樼涓夋柟浠撳簱绠€浠嬪拰 README 鎽樿銆傚嵆浣胯繖浜涘唴瀹逛笉鏄湰椤圭洰鑷繁鐨勫瘑閽ワ紝涔熶笉搴旇鎶婄枒浼?token 鍘熸牱鍐欏叆 `reports/`銆乣data/selected/` 鎴?GitHub Pages 鍛ㄦ姤涓€傛湰娆″湪閲囬泦杈圭晫澧炲姞鑴辨晱锛岄檷浣庡綊妗ｇ涓夋柟鏁忔劅瀛楃涓茬殑椋庨櫓銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/security.py
src/collector.py
tests/test_security.py
tests/test_collector.py
```

鏂板锛?

```text
redact_sensitive_text
```

澶勭悊鑼冨洿锛?

1. GitHub token 褰㈡€佸瓧绗︿覆銆?
2. Telegram bot token 褰㈡€佸瓧绗︿覆銆?
3. GitHub 浠撳簱绠€浠嬭繘鍏ョ郴缁熸椂鑴辨晱銆?
4. README 鎽樿杩涘叆绯荤粺鏃惰劚鏁忋€?

### 3. 璁捐杈圭晫

璇ヨ兘鍔涚敤浜庡噺灏戠涓夋柟鍐呭褰掓。椋庨櫓锛屼笉鏀瑰彉瀹夊叏鎵弿鑴氭湰鐨勮亴璐ｃ€傚悗缁鏋滄帴鍏ユ洿澶氭湇鍔★紝鍙互缁х画鎵╁睍 `redact_sensitive_text` 鐨勬ā寮忓垪琛ㄣ€?

---

## 2026-04-30 杩藉姞锛氭姤鍛婄敓鎴愬眰鏈€缁堣劚鏁?

### 1. 寮€鍙戠洰鐨?

閲囬泦灞傚凡缁忎細瀵圭涓夋柟浠撳簱绠€浠嬪拰 README 鎽樿鍋氳劚鏁忥紝浣嗘姤鍛婄敓鎴愬眰浠嶉渶瑕佹渶鍚庝竴閬撲繚鎶わ紝闃叉鎵嬪伐鏋勯€犵殑鏁版嵁銆佹祴璇曟暟鎹垨妯″瀷杈撳嚭缁曡繃閲囬泦杈圭晫锛屾妸鐤戜技瀵嗛挜鍐欏叆 Markdown 鍛ㄦ姤銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/reporter.py
tests/test_reporter.py
```

璋冩暣鍐呭锛?

1. `normalize_report_markdown` 浼氬厛鎵ц `redact_sensitive_text`锛屽啀鍋氶摼鎺ュ拰璇█瑙勮寖鍖栥€?
2. `fallback_report` 杩斿洖鍓嶄細鍋氭渶缁堣劚鏁忋€?
3. `_repository_payload` 浼氬湪鍙戠粰 Kimi 鍓嶅 `description` 鍜?`readme_excerpt` 鍐嶆鑴辨晱銆?
4. 鏂板娴嬭瘯瑕嗙洊鎶ュ憡褰掍竴鍖栬劚鏁忓拰 Kimi payload 鑴辨晱銆?

### 3. 瀹夊叏杈圭晫

璇ヤ繚鎶ゆ槸鈥滄渶鍚庡厹搴曗€濓紝涓嶈兘鏇夸唬閲囬泦灞傝劚鏁忓拰浠撳簱瀵嗛挜鎵弿銆傛湭鏉ュ鏋滄姤鍛婁腑澧炲姞鏇村鏉ヨ嚜绗笁鏂圭殑鏂囨湰瀛楁锛屽簲缁х画澶嶇敤 `redact_sensitive_text`銆?

---

## 2026-04-30 杩藉姞锛氶€氱敤瀵嗛挜璧嬪€艰劚鏁?

### 1. 寮€鍙戠洰鐨?

姝ゅ墠杩愯鏃惰劚鏁忓凡缁忚鐩?GitHub token 鍜?Telegram bot token 鐨勬槑纭牸寮忥紝浣嗙涓夋柟 README 涓繕鍙兘鍑虹幇 `api_key=...`銆乣password: ...`銆乣chat_id=...` 杩欑被閫氱敤瀵嗛挜璧嬪€笺€備负浜嗗拰 `scripts/security_check.py` 鐨勬壂鎻忕瓥鐣ヤ繚鎸佷竴鑷达紝鏈鎵╁睍杩愯鏃惰劚鏁忚鍒欍€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/security.py
tests/test_security.py
```

鏂板鑴辨晱鍖归厤鑼冨洿锛?

1. `api_key` 鎴?`api-key`
2. `token`
3. `secret`
4. `password`
5. `chat_id` 鎴?`chat-id`

### 3. 璁捐杈圭晫

閫氱敤璧嬪€艰鍒欏彧鏇挎崲鐤戜技瀵嗛挜鍊硷紝涓嶉樆姝㈠懆鎶ョ敓鎴愩€傚畠鐢ㄤ簬鍑忓皯绗笁鏂瑰唴瀹瑰綊妗ｉ闄╋紝椤圭洰鑷韩婧愮爜鍜屾墜鍐欐枃妗ｄ粛鐢?`scripts/security_check.py` 闃绘柇纭紪鐮佸瘑閽ャ€?

---

## 2026-04-30 杩藉姞锛氫繚鐣欒劚鏁忓瓧娈靛悕

### 1. 寮€鍙戠洰鐨?

閫氱敤瀵嗛挜璧嬪€艰劚鏁忓簲璇ヤ繚鐣?`api_key=`銆乣password:` 绛夊瓧娈靛悕锛屽彧鏇挎崲鍚庨潰鐨勭枒浼煎瘑閽ュ€笺€傝繖鏍锋棦鑳介伩鍏嶆晱鎰熷瓧绗︿覆杩涘叆褰掓。锛屼篃鑳借鎶ュ憡璇昏€呯煡閬撳師鏂囦綅缃瓨鍦ㄤ竴涓鑴辨晱鐨勯厤缃瓧娈点€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/security.py
tests/test_security.py
```

璋冩暣鍐呭锛?

1. 灏嗘槑纭?token 褰㈡€佸拰閫氱敤璧嬪€煎舰鎬佸垎寮€澶勭悊銆?
2. GitHub token銆乀elegram bot token 浠嶆暣浣撴浛鎹负 `[宸茶劚鏁忕枒浼煎瘑閽`銆?
3. `api_key=...`銆乣password: ...` 绛夎祴鍊煎舰鎬佷繚鐣欓敭鍚嶅拰鍒嗛殧绗︼紝鍙浛鎹㈠€笺€?
4. 娴嬭瘯澧炲姞瀵瑰瓧娈靛悕淇濈暀琛屼负鐨勬柇瑷€銆?

### 3. 浣跨敤鏁堟灉

绀轰緥锛?

```text
api_key=[宸茶劚鏁忕枒浼煎瘑閽
password: [宸茶劚鏁忕枒浼煎瘑閽
```

---

## 2026-04-30 杩藉姞锛歄pen Issue 椋庨櫓鎻愮ず

### 1. 寮€鍙戠洰鐨?

鏈潵璁″垝涓彁鍒伴渶瑕佷负鍏ラ€変粨搴撳鍔?Issue 椋庨櫓鎻愮ず銆傚綋鍓?GitHub 浠撳簱璇︽儏宸茬粡鍖呭惈 `open_issues_count`锛屽彲浠ュ厛鍋氫竴鏉′繚瀹堣鍒欙細褰?Open Issue 鏁伴噺鏄庢樉鍋忛珮鏃讹紝鍦ㄥ懆鎶ラ闄╂彁绀轰腑鏍囪鈥滈渶瑕佷汉宸ユ鏌ョ淮鎶ゅ搷搴斺€濄€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/security.py
tests/test_security.py
```

鏂板瑙勫垯锛?

```text
open_issues_count >= 100
骞朵笖 open_issues_count / stargazers_count >= 0.2
```

婊¤冻鏉′欢鏃讹紝`security_flags` 浼氬姞鍏ワ細

```text
Open Issue 鏁伴噺鐩稿杈冮珮锛屽缓璁鐢ㄥ墠浜哄伐妫€鏌ョ淮鎶ゅ搷搴斿拰闂璐ㄩ噺銆?
```

### 3. 璁捐杈圭晫

璇ヨ鍒欏彧鍋氶闄╂彁绀猴紝涓嶆妸椤圭洰鍒ゅ畾涓轰笉鍙敤锛屼篃涓嶅奖鍝嶅綋鍓嶆帓搴忋€侷ssue 澶氬彲鑳戒唬琛ㄩ」鐩椿璺冿紝涔熷彲鑳戒唬琛ㄧ淮鎶ゅ帇鍔涜緝澶э紝鍥犳鍛ㄦ姤涓彧鎻愮ず浜哄伐澶嶆牳銆?

---

## 2026-04-30 杩藉姞锛氭姤鍛婇潪鍏ラ€夐」鐩摼鎺ユ鏌?

### 1. 寮€鍙戠洰鐨?

鏈潵璁″垝涓彁鍒伴渶瑕佹鏌ュ懆鎶ユ槸鍚﹀寘鍚潪鍏ラ€夐」鐩€侹imi 鐢熸垚鍛ㄦ姤鏃跺彲鑳介澶栨帹鑽愭湭杩涘叆鏈湡绛涢€夌粨鏋滅殑 GitHub 浠撳簱锛岃繖浼氬墛寮?Trending 浼樺厛鍜屼釜鎬у寲绛涢€夌殑绾︽潫銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/report_checks.py
tests/test_report_checks.py
```

鏂板妫€鏌ワ細

1. 浠庡懆鎶ヤ腑鎻愬彇 `https://github.com/owner/repo` 褰㈠紡鐨勪粨搴撻摼鎺ャ€?
2. 涓庢湰鏈熷叆閫変粨搴?`full_name` 瀵规瘮銆?
3. 濡傛灉鍑虹幇闈炲叆閫変粨搴撻摼鎺ワ紝杩斿洖璐ㄩ噺閿欒銆?
4. Kimi 鍛ㄦ姤璐ㄩ噺妫€鏌ュけ璐ユ椂锛屼富娴佺▼浼氬洖閫€鍒拌鍒欏懆鎶ャ€?

### 3. 璁捐杈圭晫

璇ユ鏌ュ彧閽堝 GitHub 浠撳簱閾炬帴锛屼笉闄愬埗鏅€氱綉椤点€佹枃妗ｉ摼鎺ユ垨 GitHub Pages 鍛ㄦ姤閾炬帴銆傚畠鐢ㄤ簬淇濊瘉鏈湡鍛ㄦ姤涓ユ牸鍥寸粫绛涢€夊悗鐨勯」鐩泦鍚堝睍寮€銆?

---

## 2026-04-30 杩藉姞锛氬懆鎶ュ浐瀹氱粨鏋勬鏌?

### 1. 寮€鍙戠洰鐨?

鏈潵璁″垝涓彁鍒伴渶瑕佹妸鍛ㄦ姤鎷嗘垚鍥哄畾缁撴瀯锛屽噺灏戞ā鍨嬭嚜鐢卞彂鎸ャ€傛彁绀鸿瘝宸茬粡瑕佹眰 Kimi 杈撳嚭浜斾釜鏍稿績閮ㄥ垎锛屼絾浠ｇ爜灞傝繕娌℃湁楠岃瘉杩欎簺绔犺妭鏄惁鐪熺殑瀛樺湪銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/report_checks.py
tests/test_report_checks.py
```

鏂板妫€鏌ワ細

1. 鏈懆鎬讳綋瓒嬪娍銆?
2. 鐑偣椤圭洰鎬昏銆?
3. 閲嶇偣椤圭洰鍒嗘瀽銆?
4. 鏈€閫傚悎鐢ㄦ埛瀛︿範鐨勯」鐩€?
5. 鏈懆缁撹銆?

涓轰簡鍏煎宸叉湁琛ㄨ揪锛岄儴鍒嗙珷鑺傚厑璁歌繎涔夋爣棰橈紝渚嬪鈥滄湰鍛ㄨ秼鍔库€濃€滅儹闂ㄩ」鐩€昏鈥濃€滄渶閫傚悎鍏虫敞鐨勯」鐩€濄€?

### 3. 璁捐杈圭晫

璇ユ鏌ュ彧鐢ㄤ簬 Kimi 鍛ㄦ姤璐ㄩ噺鏍￠獙銆傝嫢 Kimi 杈撳嚭缂哄皯鏍稿績缁撴瀯锛屼富娴佺▼浼氬洖閫€鍒拌鍒欏懆鎶ワ紝閬垮厤鐢熸垚缁撴瀯娣蜂贡鐨勬姤鍛娿€?

---

## 2026-04-30 杩藉姞锛欿imi 璐ㄩ噺澶辫触鑷姩閲嶈瘯

### 1. 寮€鍙戠洰鐨?

姝ゅ墠 Kimi 鐢熸垚鐨勫懆鎶ュ彧瑕佹湭閫氳繃璐ㄩ噺妫€鏌ワ紝灏变細鐩存帴鍥為€€鍒拌鍒欏懆鎶ャ€傝繖鏍疯櫧鐒剁ǔ瀹氾紝浣嗕細璁╀竴浜涘彲淇鐨勯棶棰樹篃鍙樻垚闄嶇骇鐗堟湰銆傛湰娆″鍔犱竴娆¤嚜鍔ㄩ噸璇曟満浼氾紝鍑忓皯鍙伩鍏嶇殑闄嶇骇鍛ㄦ姤銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/reporter.py
tests/test_reporter.py
```

璋冩暣鍐呭锛?

1. 棣栨 Kimi 杈撳嚭鏈€氳繃璐ㄩ噺妫€鏌ユ椂锛岃褰曡川閲忛敊璇€?
2. 绗簩娆¤姹?Kimi 鏃讹紝鎶婅川閲忛敊璇綔涓?`quality_retry_feedback` 浼犲叆銆?
3. 閲嶈瘯鎸囦护瑕佹眰 Kimi 鍙娇鐢ㄦ湰娆¤緭鍏ラ」鐩紝骞朵慨澶嶈川閲忔鏌ラ棶棰樸€?
4. 濡傛灉绗簩娆′粛涓嶅悎鏍硷紝鎵嶅洖閫€鍒拌鍒欏懆鎶ャ€?
5. 鍐呭瀹夊叏杩囨护澶辫触浠嶄繚鐣欏師鏈夐€昏緫锛氬繀瑕佹椂鍘绘帀 README 鎽樿鍚庡啀璇曘€?

### 3. 璁捐杈圭晫

璇ラ噸璇曞彧鎵ц涓€娆★紝閬垮厤澶栭儴 API 涓嶇ǔ瀹氭椂鏃犻檺閲嶈瘯銆傛墍鏈夊け璐ュ師鍥犱粛浼氬啓鍏ヨ繍琛屾憳瑕佺殑 `report_error`锛屼究浜庡悗缁帓鏌ャ€?

---

## 2026-04-30 杩藉姞锛氬墠绔€佹暟鎹簱涓庝釜鎬у寲鍒嗘瀽瑙勫垝鎻愬墠

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛甯屾湜鍚庢湡椤圭洰鍙互鏋勫缓鍓嶇鍜屾暟鎹簱锛屽悓鏃跺笇鏈涗釜鎬у寲鍒嗘瀽鎻愪笂鏃ョ▼銆傛湰娆″厛涓嶇洿鎺ュ紑宸ュ鏉傚伐绋嬶紝鑰屾槸鎶婃垚鐔熷害鍒ゆ柇銆佽Е鍙戞潯浠躲€侀鐣欑洰褰曘€佸垎鏀瓥鐣ュ拰鏈€缁堟垚鍝佸睍鏈涘啓鍏ユ湭鏉ヨ鍒掋€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
docs/future-plan.md
```

鏂板瑙勫垝锛?

1. 鍓嶇寤鸿璁″垝銆?
2. 鏁版嵁搴撳缓璁捐鍒掋€?
3. 涓€у寲鍒嗘瀽璁″垝銆?
4. 澶氬垎鏀紑鍙戠瓥鐣ャ€?
5. 鏈€缁堟垚鍝佸睍鏈涖€?
6. 缁х画鎺ㄨ繘鍓嶉渶瑕佽В鍐崇殑闂銆?

### 3. 鍒ゆ柇缁撹

褰撳墠鍓嶇鍜屾暟鎹簱杩樹笉閫傚悎绔嬪嵆瀹屾暣寮€鍙戙€傛洿鍚堢悊鐨勮矾寰勬槸鍏堢ǔ瀹氭暟鎹粨鏋勫拰鍛ㄦ姤璐ㄩ噺锛屽啀鍋?GitHub Pages 杞婚噺绛涢€夛紝绛夊巻鍙叉暟鎹冻澶熷悗鍐嶅紩鍏?SQLite 鍜屾洿瀹屾暣鐨勫墠绔€備釜鎬у寲鍒嗘瀽宸茬粡鏈?`config/interests.json` 鍩虹锛屽彲浠ヤ紭鍏堟帹杩?profile 閰嶇疆璁捐銆?

---

## 2026-04-30 杩藉姞锛氫釜鎬у寲 profile 鏈€灏忕増鏈?

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛甯屾湜鍚庣画鍙互閫氳繃閫夋嫨 Java銆丳ython銆丄gent 寮€鍙戠瓑閫夐」锛岀簿鍑嗘帹閫佺鍚堝綋鍓嶉渶姹傜殑椤圭洰銆傛湰娆″厛瀹炵幇閰嶇疆灞傜殑鏈€灏忕増鏈紝閬垮厤鎻愬墠寮曞叆澶嶆潅鍓嶇鎴栨暟鎹簱銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
config/profiles.example.json
src/personalization.py
src/settings.py
tests/test_personalization.py
tests/test_settings.py
README.md
docs/setup.md
.github/workflows/weekly.yml
```

璋冩暣鍐呭锛?

1. 鏂板 `config/profiles.example.json`锛屾彁渚?`java`銆乣python`銆乣agent_development`銆乣learning`銆乣developer_tools` 浜旂被绀轰緥鏂瑰悜銆?
2. 鏂板 `src/personalization.py`锛屾敮鎸佹妸澶氫釜 profile 鍙犲姞鍒板熀纭€鍏磋叮閰嶇疆涓€?
3. 鏀寔 `INTEREST_PROFILE=java,agent_development` 杩欑澶氶€夊舰寮忥紝涓哄悗缁墠绔€夋嫨鍣ㄩ鐣欏叆鍙ｃ€?
4. `src/settings.py` 鍦ㄥ姞杞?`config/interests.json` 鎴?example 鍚庤嚜鍔ㄥ簲鐢?profile銆?
5. GitHub Actions 鏀寔浠庝粨搴撳彉閲忚鍙?`INTEREST_PROFILE`銆?
6. README 鏇存柊涓哄綋鍓嶇湡瀹為」鐩兘鍔涜鏄庛€?

### 3. 璁捐杈圭晫

鏈鍙仛涓€у寲閰嶇疆鍏ュ彛锛屼笉鏂板鏁版嵁搴撱€佷笉鏂板鐧诲綍绯荤粺銆佷笉鏂板澶嶆潅鍓嶇銆俻rofile 涓彧鍏佽淇濆瓨鍏磋叮鏂瑰悜銆佽瑷€銆佷富棰樸€佹悳绱㈣ˉ鍏呴」鍜岃瘎鍒嗘潈閲嶏紝涓嶅簲鍐欏叆浠讳綍瀵嗛挜銆?

---

## 2026-04-30 杩藉姞锛氫釜鎬у寲鍖归厤鍘熷洜

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛甯屾湜鍚庣画涓嶄粎鑳介€夋嫨 Java銆丳ython銆丄gent 寮€鍙戠瓑鏂瑰悜锛岃繕鑳界簿鍑嗘帹閫佺鍚堝綋鍓嶉渶姹傜殑椤圭洰銆傛湰娆″湪宸叉湁 profile 閫夋嫨鑳藉姏涓婂鍔犫€滃尮閰嶅師鍥犫€濓紝璁╂帹鑽愮粨鏋滃彲浠ヨВ閲婁负浠€涔堟煇涓」鐩€傚悎褰撳墠閫夋嫨銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/personalization.py
src/processor.py
tests/test_personalization.py
tests/test_processor.py
README.md
docs/setup.md
```

璋冩暣鍐呭锛?

1. profile 搴旂敤鍚庝細鐢熸垚杞婚噺鐨?`profile_match_rules`銆?
2. 璇勫垎闃舵鏍规嵁浠撳簱璇█銆乼opic銆佸悕绉板拰绠€浠嬪垽鏂懡涓摢浜涗釜鎬у寲鏂瑰悜銆?
3. 鍏ラ€夐」鐩殑 `selection_reasons` 浼氳拷鍔犵被浼尖€滃尮閰嶅綋鍓嶄釜鎬у寲鏂瑰悜锛欽ava 鍚庣涓庡伐绋嬪疄璺点€丄gent 寮€鍙戙€傗€濈殑璇存槑銆?
4. 璇ュ瓧娈典細杩涘叆 `data/selected/YYYY-MM-DD.json`锛屽彲渚?Kimi 鍛ㄦ姤銆佽鍒欑増鍛ㄦ姤鍜屽悗缁墠绔瓫閫夊鐢ㄣ€?

### 3. 璁捐杈圭晫

鏈浠嶄笉鏂板鍓嶇鎴栨暟鎹簱銆傚尮閰嶉€昏緫淇濇寔杞婚噺锛屽厛浠?profile 鐨勮瑷€鍜屼富棰樺叧閿瘝涓轰緷鎹紝鍚庣画濡傛灉鐪熷疄鍛ㄦ姤涓鍒よ緝澶氾紝鍐嶆墿灞曟洿缁嗙殑瑙勫垯銆?

### 4. 杩藉姞淇

杩愯鐪熷疄鍛ㄦ姤鍚庡彂鐜帮紝瀛愪覆鍖归厤鍙兘璁?`java` 璇懡涓?`JavaScript`銆傚凡灏?profile 涓婚鍖归厤璋冩暣涓鸿瘝椤瑰尮閰嶏紝骞舵柊澧炴祴璇曡鐩栵紝閬垮厤璇█鍜屼富棰樺嚭鐜版槑鏄捐鍒ゃ€?
---

## 2026-04-30 杩藉姞锛欿imi 杩囪浇閲嶈瘯涓庨檷绾у師鍥犱慨姝?

### 1. 闂鍘熷洜

鐪熷疄杩愯鏃?Kimi 杩斿洖 `429 engine_overloaded_error`锛岃〃绀烘ā鍨嬫湇鍔¤繃杞姐€傛棫浠ｇ爜娌℃湁閽堝杩欑被涓存椂閿欒绛夊緟閲嶈瘯锛岃€屾槸绗竴娆¤姹傚け璐ュ悗鐩存帴鍥為€€鍒拌鍒欑増鍛ㄦ姤銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/reporter.py
tests/test_reporter.py
README.md
docs/setup.md
```

璋冩暣鍐呭锛?

1. Telegram 鍏佽缁х画鎺ㄩ€佽鍒欑増鍛ㄦ姤閾炬帴锛屼繚璇佺敤鎴疯兘鏀跺埌鍏滃簳缁撴灉銆?
2. Kimi 杩斿洖 `429`銆乣500`銆乣502`銆乣503`銆乣504`銆乣engine_overloaded` 鎴栫綉缁滀复鏃堕敊璇椂锛屼細鍏堣嚜鍔ㄩ噸璇曘€?
3. 鏂板 `KIMI_MAX_RETRIES`锛岄粯璁ら噸璇?`2` 娆°€?
4. 鏂板 `KIMI_RETRY_SECONDS`锛岄粯璁ゆ瘡娆＄瓑寰?`20` 绉掋€?
5. 澶氭閲嶈瘯浠嶅け璐ユ椂锛屾墠浼氱敓鎴愯鍒欑増鍛ㄦ姤锛屽苟鍦ㄨ繍琛屾憳瑕佺殑 `report_error` 涓褰曞畬鏁村け璐ュ師鍥犮€?

### 3. 璁捐缁撹

鏈闂鐨勭洿鎺ュ師鍥犱笉鏄厤缃敊璇紝鑰屾槸 Kimi 鏈嶅姟绔繃杞姐€傚悗缁€氳繃鑷姩閲嶈瘯鍑忓皯鍋跺彂杩囪浇瀵艰嚧鐨勯檷绾э紱濡傛灉澶氭閲嶈瘯鍚庝粛澶辫触锛岃鏄庡閮ㄦā鍨嬫湇鍔℃寔缁笉鍙敤锛岀郴缁熶粛浼氫繚鐣欒鍒欑増鍛ㄦ姤浣滀负鍏滃簳銆?

---

## 2026-04-30 杩藉姞锛氬閮ㄩ」鐩?README 绮剧偧鎽樿

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛璇存槑闇€瑕佷繚鐣欐湰浠撳簱 README 鐨勫畬鏁寸姸鎬侊紝鐪熸闇€瑕佺簿绠€鐨勬槸鍛ㄦ姤涓潵鑷閮ㄩ」鐩殑 README 鍐呭銆傛鍓嶇郴缁熶細鎴彇澶栭儴椤圭洰 README 鍓嶆鏂囨湰锛屽鏄撴妸杩囬暱璇存槑澶嶅埗杩涘懆鎶ラ〉闈€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
src/collector.py
tests/test_collector.py
README.md
```

璋冩暣鍐呭锛?

1. 鎭㈠鏈粨搴?README 鐨勫畬鏁寸増鏈€?
2. 澶栭儴椤圭洰 README 杩涘叆鍛ㄦ姤鍓嶅厛娓呯悊寰界珷銆佸浘鐗囥€佷唬鐮佸潡銆佽〃鏍笺€佸畨瑁呭懡浠ゅ拰鐩綍鍣０銆?
3. `readme_excerpt` 鏀逛负淇濆瓨 2-3 鍙ャ€佺害 300 瀛椾互鍐呯殑绮剧偧鎽樿銆?
4. 瑙勫垯鐗堝懆鎶ヤ腑鍘熸潵鐨勨€淩EADME 鎽樿鈥濅綅缃細鐩存帴浣跨敤璇ョ簿鐐兼憳瑕侊紝涓嶅啀灞曠ず闀跨瘒 README 鍘熸枃銆?

### 3. 璁捐杈圭晫

褰撳墠鎽樿鏄鍒欏瀷鎻愬彇锛屼笉璋冪敤棰濆妯″瀷锛岄伩鍏嶅鍔犳垚鏈拰澶辫触鐐广€傚悗缁鏋?Kimi 绋冲畾锛屽彲鍐嶈妯″瀷鍩轰簬璇ョ簿鐐兼憳瑕佸仛鏇磋嚜鐒剁殑涓枃鏀瑰啓銆?

---

## 2026-04-30 杩藉姞锛氫唬鐮佸鏌ラ棶棰樹慨澶?

### 1. 寮€鍙戠洰鐨?

鏍规嵁鏈€鏂颁唬鐮佸鏌ョ粨鏋滐紝淇鍥涚被闂锛氬凡鎺ㄩ€佺姸鎬佸奖鍝嶇儹鐐瑰畬鏁存€с€並imi 鏍煎紡灏忛敊璇鑷存暣浠介檷绾с€丷EADME 鎽樿瀛楁涓嶆竻鏅般€佹棫鏋舵瀯鏂囨。浠嶄繚鐣?`created` 鏌ヨ绀轰緥銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
main.py
src/models.py
src/collector.py
src/reporter.py
tests/test_collector.py
tests/test_reporter.py
docs/project-architecture.md
```

璋冩暣鍐呭锛?

1. 鍛ㄦ姤鍊欓€夋睜涓嶅啀鍥?`sent_repos.json` 杩囨护鍘嗗彶宸叉帹閫侀」鐩紝閬垮厤閬楁紡鎸佺画鐑棬椤圭洰銆?
2. 杩愯鎽樿鏂板 `previously_sent_selected_count`锛岃褰曟湰鏈熷叆閫夐」鐩腑鏈夊灏戞浘缁忔帹閫佽繃銆?
3. 鍒犻櫎涓嶅啀浣跨敤鐨?`filter_unsent_repositories`锛岄伩鍏嶅悗缁浠ヤ负涓绘祦绋嬩粛浼氳繃婊ゅ凡鎺ㄩ€佷粨搴撱€?
4. Kimi 杈撳嚭杩涘叆璐ㄩ噺妫€鏌ュ墠锛屼細鑷姩琛ラ綈椤圭洰瀹屾暣閾炬帴銆佹潵婧愩€乀rending 鎺掑悕鍜岄闄╂彁绀猴紝鍑忓皯鍙慨澶嶆牸寮忛棶棰樺鑷寸殑闄嶇骇銆?
5. `Repository` 鏂板 `readme_summary` 瀛楁锛岀户缁繚鐣?`readme_excerpt` 鍏煎鍘嗗彶鏁版嵁銆?
6. README 瑙勫垯鎽樿澧炲姞 bullet-only README 鐨勫厹搴曟彁鍙栥€?
7. `docs/project-architecture.md` 灏嗘棫 `created:>=...` 绀轰緥鏀逛负褰撳墠 `Trending + pushed` 绛栫暐銆?

### 3. 璁捐杈圭晫

鏈娌℃湁寮曞叆鏁版嵁搴撴垨鏂版鏋躲€俙sent_repos.json` 浠嶇敤浜庤褰曟帹閫佺姸鎬侊紝浣嗕笉鍐嶅奖鍝嶅懆鎶ュ€欓€夋睜锛汯imi 淇鍣ㄥ彧鍋氱粨鏋勫寲鍏冩暟鎹ˉ榻愶紝涓嶆敼鍐欐ā鍨嬫鏂囥€?

---

## 2026-05-03 杩藉姞锛氬惛鏀剁爺绌舵姤鍛婂苟淇鍙戝竷鐘舵€佷竴鑷存€?

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛鎻愪緵 `deep-research-report.md` 鍚庯紝纭鍚庣画鏂瑰悜搴斾粠鈥滄洿澶嶆潅鐨勬姄鍙栧櫒鈥濊浆鍚戔€滃彲澶嶇洏銆佸彲璁㈤槄銆佸彲涓€у寲鐨勫紑婧愭儏鎶ョ郴缁熲€濄€傛湰娆″厛鍚告敹鍏朵腑閫傚悎褰撳墠闃舵鐨勮矾绾垮缓璁紝骞朵慨澶?Pages 椤甸潰鍙兘鏄剧ず鏃?Telegram 鐘舵€佺殑闂銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
.github/workflows/weekly.yml
scripts/send_report_link.py
tests/test_send_report_link.py
docs/roadmap.md
docs/future-plan.md
```

璋冩暣鍐呭锛?

1. `scripts/send_report_link.py` 鍦ㄥ啓鍥?`data/runs/YYYY-MM-DD.json` 鐨?Telegram 鐘舵€佸悗锛屼細閲嶆柊鏋勫缓 GitHub Pages 椤甸潰銆?
2. workflow 鐨勨€滄彁浜ゆ帹閫佺姸鎬佲€濇楠ゅ悓鏃舵彁浜?`docs/index.md`銆乣docs/projects.md` 鍜?`docs/weekly`锛岄伩鍏嶉〉闈㈢姸鎬佸仠鐣欏湪鎺ㄩ€佸墠銆?
3. 鏂板娴嬭瘯锛岄獙璇?Telegram 鐘舵€佸啓鍥炲悗閲嶅缓椤甸潰鏃讹紝棣栭〉浼氬睍绀衡€滃凡鎺ㄩ€佲€濄€?
4. 閲嶅啓 `docs/roadmap.md`锛屽皢璺嚎鏄庣‘涓衡€滄ā鍧楀寲鍗曚綋 + SQLite 鍙屽啓 + 鍏叡 JSON + 涓湡杞婚噺鍓嶇 + 涓€у寲鍙嶉鈥濄€?
5. 鏇存柊 `docs/future-plan.md` 鐨勪紭鍏堢骇锛屾妸 Pages 鐘舵€佷竴鑷存€с€侀噸澶嶅叆閫夋柊棰栧害銆丼QLite 鍙屽啓鍜屽叕鍏?JSON 鎻愬埌鏇撮潬鍓嶇殑浣嶇疆銆?

### 3. 璁捐杈圭晫

鏈娌℃湁鐩存帴寮曞叆鏁版嵁搴撱€佸墠绔鏋舵垨鏂板閮ㄦ湇鍔°€係QLite銆丟raphQL銆佸叕鍏?JSON 鍜屽墠绔寮哄彧杩涘叆璺嚎鍥撅紝鍚庣画鎸夊皬姝ユ彁浜ら€愰」瀹炵幇銆?

---

## 2026-05-03 杩藉姞锛氶噸澶嶅叆閫夐」鐩殑鏂伴搴︾瓥鐣?

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛瑕佹眰鍛ㄦ姤蹇呴』淇濇寔鈥滄瘡鍛ㄦ渶鐏垎椤圭洰鈥濈殑瀹屾暣鎬э紝鍥犳涓嶈兘绠€鍗曡繃婊ゅ凡缁忔帹閫佽繃鐨勪粨搴撱€備絾濡傛灉鍚屼竴鎵归」鐩繛缁鍛ㄥ叆閫夛紝鍛ㄦ姤浼氶檷浣庢柊椴滄劅銆傛湰娆″疄鐜拌交閲忕殑鏂伴搴︽儵缃氬拰璇存槑鏈哄埗銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
main.py
src/processor.py
config/interests.example.json
tests/test_processor.py
README.md
docs/roadmap.md
docs/future-plan.md
```

璋冩暣鍐呭锛?

1. `process_repositories` 鏂板鍙€夊弬鏁?`previously_sent_names`锛屾棫璋冪敤淇濇寔鍏煎銆?
2. 涓绘祦绋嬫妸 `sent_repos.json` 涓殑宸叉帹閫佷粨搴撻泦鍚堜紶鍏ユ帓搴忛樁娈点€?
3. 鏂板 `novelty_penalty_weight` 閰嶇疆锛岄粯璁?`0.08`锛岀敤浜庤交寰檷浣庨潪 Trending 鍓嶅崄鐨勯噸澶嶉」鐩垎鏁般€?
4. GitHub Trending 鍓嶅崄椤圭洰涓嶅彈璇ユ儵缃氾紝閬垮厤鐮村潖 Trending 浼樺厛绾у拰鍓嶅崄淇濇姢绛栫暐銆?
5. 閲嶅鍏ラ€夐」鐩細澧炲姞鎺ㄨ崘鐞嗙敱锛氣€滄鍓嶅凡缁忔帹閫佽繃锛屾湰娆″洜浠嶇劧鍏峰鐑偣淇″彿缁х画淇濈暀瑙傚療銆傗€?
6. 鏂板娴嬭瘯瑕嗙洊閲嶅椤圭洰涓嶈杩囨护銆侀潪 Trending 閲嶅椤圭洰琚交閲忛檷鏉冦€乀rending 鍓嶅崄閲嶅椤圭洰浠嶄繚鎸佷紭鍏堛€?

### 3. 璁捐杈圭晫

鏈娌℃湁寮曞叆鎸夋棩鏈熺獥鍙ｇ殑澶嶆潅鍘婚噸锛屼篃涓嶅垹闄ゅ巻鍙叉帹閫佺姸鎬併€傚悗缁鏋滈渶瑕佹洿绮剧粏鐨勯暱鏈熶綋楠岋紝鍙熀浜?`first_sent_at`銆佹渶杩戞帹閫佹棩鏈熷拰鍙嶉鏁版嵁鍋氬姩鎬佹儵缃氥€?

---

## 2026-05-03 杩藉姞锛氬叕鍏?JSON 瀵煎嚭

### 1. 寮€鍙戠洰鐨?

鏍规嵁璺嚎鍥撅紝鍚庣画鍓嶇銆丷SS銆佸井淇°€侀涔﹀拰澶栭儴璁㈤槄閮介渶瑕佺ǔ瀹氱殑鏁版嵁鍏ュ彛銆傚鏋滅洿鎺ヨ鍙?Markdown 椤甸潰锛屽悗缁細澧炲姞瑙ｆ瀽鎴愭湰銆傚洜姝ゆ湰娆″厛鍦ㄧ幇鏈?Pages 鏋勫缓娴佺▼涓鍑哄叕寮€ JSON銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
.github/workflows/weekly.yml
scripts/build_pages.py
tests/test_build_pages.py
README.md
docs/roadmap.md
docs/future-plan.md
```

鏂板浜х墿锛?

```text
docs/projects.json
docs/runs.json
```

璋冩暣鍐呭锛?

1. `scripts/build_pages.py` 浼氬湪鐢熸垚 `docs/index.md` 鍜?`docs/projects.md` 鐨勫悓鏃剁敓鎴愬叕鍏?JSON銆?
2. `projects.json` 姹囨€诲巻娆″叆閫夐」鐩殑鍏紑鎽樿瀛楁锛屽寘鎷」鐩悕銆侀摼鎺ャ€佽瑷€銆佹柟鍚戙€佹潵婧愩€乀rending 鎺掑悕銆佹柊澧?Star銆佹帹鑽愮悊鐢卞拰椋庨櫓鎻愮ず銆?
3. `runs.json` 姹囨€诲巻娆¤繍琛屾憳瑕佺殑鍏紑瀛楁锛屽寘鎷繍琛屾棩鏈熴€佸叆閫夋暟閲忋€侀噰闆嗘暟閲忋€並imi/闄嶇骇鐘舵€併€乀elegram 鐘舵€佸拰瓒嬪娍瑕佺偣銆?
4. workflow 鐨勪袱澶勫綊妗ｆ彁浜ら兘鍔犲叆 `docs/projects.json` 鍜?`docs/runs.json`銆?
5. 鏂板娴嬭瘯楠岃瘉鍏叡 JSON 鐨?schema 鐗堟湰銆佹暟閲忋€侀」鐩摼鎺ャ€佽繍琛岀姸鎬佸拰绌烘暟鎹厹搴曘€?

### 3. 璁捐杈圭晫

鍏叡 JSON 鍙鍑洪€傚悎鍏紑灞曠ず鐨勬憳瑕佸瓧娈碉紝涓嶅鍑哄瘑閽ャ€佺敤鎴烽殣绉併€佸師濮嬮敊璇爢鏍堟垨鏈劚鏁忛厤缃€係QLite 浠嶆湭寮曞叆锛屽悗缁暟鎹簱鍙互浠庤繖浜涘叕寮€ JSON 鍜屽師濮?`data/` 宸ヤ欢缁х画婕旇繘銆?

---

## 2026-05-03 杩藉姞锛歋QLite 娲剧敓绱㈠紩鍩虹鐗堟湰

### 1. 寮€鍙戠洰鐨?

鍚庣画鍓嶇绛涢€夈€佸巻鍙茶秼鍔挎煡璇㈠拰涓€у寲鍙嶉閮介渶瑕佹洿绋冲畾鐨勬暟鎹簳搴с€傚綋鍓?JSON 褰掓。浠嶇劧閫傚悎浣滀负鍙浜嬪疄鏉ユ簮锛屼絾璺ㄥ懆鏌ヨ鍜屼竴鑷存€ф牎楠屼細閫愭鍙樺鏉傘€傚洜姝ゆ湰娆″厛寤虹珛 SQLite 娲剧敓绱㈠紩鐨勬渶灏忓熀纭€锛屼笉鏀瑰彉涓绘祦绋嬭鍙栬矾寰勩€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
.gitignore
README.md
docs/roadmap.md
docs/future-plan.md
src/storage/schema.sql
src/storage/sqlite_store.py
scripts/migrate_json_to_sqlite.py
scripts/verify_migration.py
tests/test_storage_sqlite.py
```

鏂板琛細

```text
runs
repositories
selections
trend_summaries
sent_repositories
star_history
migration_meta
```

璋冩暣鍐呭锛?

1. 鏂板 SQLite schema锛岃鐩栬繍琛屾憳瑕併€佷粨搴撱€佸叆閫夎褰曘€佽秼鍔挎憳瑕併€佸凡鎺ㄩ€佺姸鎬佸拰 Star 鍘嗗彶銆?
2. 鏂板 `scripts/migrate_json_to_sqlite.py`锛屽彲灏嗙幇鏈?`data/` JSON 褰掓。瀵煎叆 `data/github_weekly.sqlite`銆?
3. 鏂板 `scripts/verify_migration.py`锛屾牎楠?SQLite 琛ㄨ鏁板拰 JSON 褰掓。鍩虹璁℃暟鏄惁涓€鑷淬€?
4. 鏂板娴嬭瘯楠岃瘉瀵煎叆銆佸箓绛夋€с€佽鏁颁竴鑷存€у拰琛ㄥ悕淇濇姢銆?
5. `.gitignore` 鎺掗櫎 `data/*.sqlite`銆乣data/*.sqlite-shm`銆乣data/*.sqlite-wal`锛岄伩鍏嶆彁浜ゆ淳鐢熸暟鎹簱銆?

### 3. 璁捐杈圭晫

SQLite 褰撳墠鍙槸鍙噸寤虹殑娲剧敓绱㈠紩锛孞SON 浠嶇劧鏄簨瀹炴潵婧愩€備富娴佺▼灏氭湭鎺ュ叆鍙屽啓锛屼篃娌℃湁浠?SQLite 璇诲彇鏁版嵁銆傚悗缁彲浠ュ湪鏈熀纭€涓婂皬姝ュ姞鍏ヤ富娴佺▼鍙屽啓锛屽啀閫愭璁╁墠绔垨鍒嗘瀽鑴氭湰娑堣垂 SQLite銆?

---

## 2026-05-03 杩藉姞锛氫富娴佺▼ SQLite 鍚屾

### 1. 寮€鍙戠洰鐨?

涓婁竴闃舵宸茬粡寤虹珛 SQLite schema銆佽縼绉昏剼鏈拰鏍￠獙鑴氭湰銆傛湰娆＄户缁妸 SQLite 浣滀负娲剧敓绱㈠紩鎺ュ叆涓绘祦绋嬶紝璁╂瘡娆¤繍琛屽湪鍐欏叆 JSON 褰掓。鍚庤嚜鍔ㄦ洿鏂版暟鎹簱锛屽悓鏃朵粛淇濇寔 JSON 涓轰簨瀹炴潵婧愩€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
main.py
scripts/send_report_link.py
src/archive.py
src/models.py
tests/test_archive.py
tests/test_send_report_link.py
README.md
docs/roadmap.md
docs/future-plan.md
```

璋冩暣鍐呭锛?

1. `RunSummary` 鏂板 `sqlite_index_path` 鍜?`sqlite_error` 瀛楁銆?
2. `src/archive.py` 鏂板 `sync_sqlite_index`锛屼細浠庣幇鏈?JSON 褰掓。鍚屾鍒?SQLite銆?
3. 涓绘祦绋嬪湪 `write_run_summary` 鍚庤嚜鍔ㄥ悓姝?SQLite锛涘悓姝ュけ璐ヤ笉浼氶樆鏂懆鎶ョ敓鎴愩€?
4. `scripts/send_report_link.py` 鍦?Telegram 鐘舵€佸啓鍥炲悗鍐嶆鍚屾 SQLite锛屼繚璇佹暟鎹簱涓殑鍙戦€佺姸鎬佸拰鏈€缁?JSON 涓€鑷淬€?
5. 鏂板 `SQLITE_INDEX_PATH` 鐜鍙橀噺锛岀敤浜庤嚜瀹氫箟 SQLite 璺緞銆?
6. 鏂板 `SKIP_SQLITE_INDEX` 鐜鍙橀噺锛岀敤浜庤烦杩?SQLite 鍚屾銆?
7. 鏂板娴嬭瘯瑕嗙洊褰掓。鍚屾鍜屽彂閫佽剼鏈啓鍥?SQLite 鐘舵€佸瓧娈点€?

### 3. 璁捐杈圭晫

SQLite 浠嶆槸鍙噸寤烘淳鐢熺储寮曪紝涓嶆槸鍞竴浜嬪疄鏉ユ簮銆備富娴佺▼涓嶄粠 SQLite 璇诲彇鏁版嵁锛涘嵆浣?SQLite 鍚屾澶辫触锛屾姤鍛娿€佸綊妗ｃ€丳ages 鍜?Telegram 閾捐矾浠嶇户缁伐浣溿€?

---

## 2026-05-03 杩藉姞锛氬叕鍏辨暟鎹绾︽祴璇?

### 1. 寮€鍙戠洰鐨?

鍏叡 JSON 鍜?SQLite 宸茬粡鎴愪负鍚庣画鍓嶇銆佸娓犻亾鎺ㄩ€併€佽闃呭拰瓒嬪娍鍒嗘瀽鐨勫熀纭€銆傚鏋滃瓧娈佃鏃犳剰鍒犻櫎鎴栭噸鍛藉悕锛屼笅娓稿姛鑳戒細鍑虹幇闅愯斀闂銆傛湰娆¤ˉ鍏呮暟鎹绾︽祴璇曞拰涓枃璇存槑鏂囨。銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
docs/data-contracts.md
docs/roadmap.md
docs/future-plan.md
```

璋冩暣鍐呭锛?

1. 鏂板 `tests/test_data_contracts.py`锛屽浐瀹?`docs/projects.json` 鐨勯」鐩瓧娈甸泦鍚堛€?
2. 鍥哄畾 `docs/runs.json` 鐨勮繍琛屾憳瑕佸瓧娈甸泦鍚堛€?
3. 鍥哄畾 SQLite 鍏抽敭琛ㄥ瓧娈甸泦鍚堛€?
4. 鏂板 `docs/data-contracts.md`锛岀敤涓枃璇存槑鍏叡 JSON銆丼QLite 琛ㄥ拰淇敼瀛楁鏃剁殑瑕佹眰銆?
5. GitHub Pages 棣栭〉鏂囨。鍏ュ彛鏂板鈥滄暟鎹绾﹁鏄庘€濄€?

### 3. 璁捐杈圭晫

濂戠害娴嬭瘯鍙攣瀹氬綋鍓嶅澶栫ǔ瀹氬瓧娈碉紝涓嶉樆姝㈠悗缁柊澧炶兘鍔涖€傛湭鏉ュ鏋滅‘瀹炶鏂板銆佸垹闄ゆ垨閲嶅懡鍚嶅瓧娈碉紝搴斿悓姝ユ洿鏂板绾︽祴璇曘€佷腑鏂囨枃妗ｅ拰鎵€鏈変笅娓告秷璐归€昏緫銆?

---

## 2026-05-03 杩藉姞锛氳交閲忛」鐩瓫閫夐〉

### 1. 寮€鍙戠洰鐨?

鍏叡 JSON 宸茬粡鍏峰绋冲畾瀛楁锛屼笅涓€姝ラ渶瑕佺粰鏈潵鍓嶇鍜岀敤鎴锋祻瑙堟彁渚涗竴涓渶灏忓彲鐢ㄥ叆鍙ｃ€傛湰娆′笉寮曞叆鍓嶇妗嗘灦锛屽彧鍦ㄧ幇鏈?GitHub Pages 鏋勫缓娴佺▼涓敓鎴愰潤鎬?HTML 椤甸潰銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/build_pages.py
tests/test_build_pages.py
.github/workflows/weekly.yml
README.md
docs/data-contracts.md
docs/roadmap.md
docs/future-plan.md
```

鏂板浜х墿锛?

```text
docs/explorer.html
```

璋冩暣鍐呭锛?

1. `scripts/build_pages.py` 鏂板 `docs/explorer.html` 鐢熸垚閫昏緫銆?
2. 绛涢€夐〉鐩存帴璇诲彇 `docs/projects.json`銆?
3. 鏀寔鍏抽敭璇嶃€佽瑷€銆佹柟鍚戙€佹潵婧愩€侀闄╂彁绀虹瓫閫夈€?
4. 鏀寔鎸夋渶鏂板叆閫夈€佹柊澧?Star銆乀rending 鎺掑悕銆佺患鍚堝垎鍜岀疮璁?Star 鎺掑簭銆?
5. GitHub Pages 棣栭〉鏂板鈥滈」鐩瓫閫夐〉鈥濆叆鍙ｃ€?
6. workflow 褰掓。鎻愪氦鑼冨洿鍔犲叆 `docs/explorer.html`銆?
7. 娴嬭瘯楠岃瘉绛涢€夐〉浼氱敓鎴愶紝骞跺寘鍚牳蹇冩帶浠跺拰 `projects.json` 鏁版嵁鍏ュ彛銆?

### 3. 璁捐杈圭晫

鏈娌℃湁寮曞叆 Astro銆丷eact銆乂ue 鎴?SSR銆傞〉闈㈠彧鏄渶灏忓彲鐢ㄧ殑闈欐€佺瓫閫夊叆鍙ｏ紝鍚庣画濡傛灉浜や簰闇€姹傜户缁鍔狅紝鍐嶅熀浜庡叕鍏?JSON 鍜屾暟鎹绾﹁瘎浼板墠绔伐绋嬪寲銆?

---

## 2026-05-06 杩藉姞锛氬彲鍒嗕韩绛涢€夎鍥?

### 1. 寮€鍙戠洰鐨?

椤圭洰绛涢€夐〉宸茬粡鍙互璇诲彇 `projects.json` 鍋氬熀纭€绛涢€夛紝浣嗙瓫閫夌姸鎬佷笉鑳藉鐜般€備负浜嗚鍚庣画 Telegram銆佸井淇°€侀涔﹀拰娴忚鍣ㄤ功绛捐兘澶熸寚鍚戝悓涓€涓瓫閫夎鍥撅紝鏈琛ュ厖 URL 鐘舵€佸悓姝ュ拰缁撴灉姒傝銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
scripts/build_pages.py
tests/test_build_pages.py
README.md
docs/data-contracts.md
docs/operation-log.md
```

璋冩暣鍐呭锛?

1. `docs/explorer.html` 鏂板鏃ユ湡绛涢€夈€?
2. 鏂板绛涢€夌粨鏋滄瑙堬紝灞曠ず鏂板 Star銆乀rending 椤圭洰鏁般€侀闄╂彁绀烘暟鍜屼富璇█/鏂瑰悜銆?
3. 绛涢€夋潯浠朵細鍚屾鍒?URL 鏌ヨ鍙傛暟銆?
4. 鎵撳紑甯︽煡璇㈠弬鏁扮殑閾炬帴鏃朵細鑷姩鎭㈠绛涢€夌姸鎬併€?
5. 鏂板鈥滃鍒堕摼鎺モ€濇寜閽紝鏂逛究鍒嗕韩褰撳墠绛涢€夎鍥俱€?
6. 娴嬭瘯瑕嗙洊鏃ユ湡鎺т欢銆佸垎浜寜閽€乁RL 鐘舵€佹仮澶嶃€乁RL 鏇存柊鍜岀粨鏋滄瑙堝嚱鏁板瓨鍦ㄦ€с€?

### 3. 璁捐杈圭晫

鏈浠嶄繚鎸佹棤妗嗘灦闈欐€侀〉闈€俇RL 鍙傛暟鍙繚瀛樺叕寮€绛涢€夋潯浠讹紝涓嶅啓鍏ラ殣绉佷俊鎭垨瀵嗛挜銆?

---

## 2026-05-06 杩藉姞锛歊SS 璁㈤槄杈撳嚭

### 1. 寮€鍙戠洰鐨?

椤圭洰宸茬粡鏀寔 Telegram 鎺ㄩ€佸拰 GitHub Pages 闃呰锛屼絾杩樼己灏戦潰鍚戦槄璇诲櫒鍜岃嚜鍔ㄥ寲宸ュ叿鐨勮闃呭叆鍙ｃ€傛湰娆℃柊澧?RSS 杈撳嚭锛岃鐢ㄦ埛鍙互璁㈤槄姣忓懆鍛ㄦ姤鏇存柊锛屼篃涓哄悗缁井淇°€侀涔︺€侀偖浠剁瓑娓犻亾鎻愪緵杞婚噺鐩戝惉鏉ユ簮銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
.github/workflows/weekly.yml
scripts/build_pages.py
tests/test_build_pages.py
README.md
docs/data-contracts.md
docs/operation-log.md
```

鏂板浜х墿锛?

```text
docs/feed.xml
```

璋冩暣鍐呭锛?

1. `scripts/build_pages.py` 鍦ㄧ敓鎴?Pages 鏃跺悓姝ョ敓鎴?RSS 2.0 鏂囦欢銆?
2. RSS 鏉＄洰鎸夊懆鎶ユ棩鏈熷€掑簭鐢熸垚锛屾渶澶氫繚鐣欐渶杩?20 绡囥€?
3. 鏉＄洰閾炬帴浼樺厛浣跨敤杩愯鎽樿涓殑鍏紑 Pages 鍩虹鍦板潃銆?
4. RSS 鎻忚堪鍖呭惈鍏ラ€夋暟閲忋€侀噰闆嗘暟閲忋€佺敓鎴愭柟寮忋€乀elegram 鐘舵€佸拰瓒嬪娍鎽樿銆?
5. workflow 褰掓。鎻愪氦鑼冨洿鍔犲叆 `docs/feed.xml`銆?
6. 娴嬭瘯楠岃瘉 RSS 鏂囦欢鐢熸垚銆佹爣棰樸€佸懆鎶ラ摼鎺ュ拰鎽樿鍐呭銆?

### 3. 璁捐杈圭晫

RSS 鍙彂甯冨叕寮€鎽樿锛屼笉鍖呭惈瀵嗛挜銆佺敤鎴烽殣绉併€佸師濮嬮敊璇爢鏍堟垨鏈劚鏁忛厤缃€傚畠鏄闃呭叆鍙ｏ紝涓嶆浛浠?Telegram 鎺ㄩ€佸拰 GitHub Pages 闃呰椤点€?

---

## 2026-05-06 杩藉姞锛氬鎺ㄩ€侀€氶亾鍏ュ彛

### 1. 寮€鍙戠洰鐨?

褰撳墠瀹為檯鎺ㄩ€侀€氶亾鏄?Telegram銆備负浜嗗悗缁帴鍏ュ井淇°€侀涔︽垨閭欢锛屾湰娆″厛鎶婃帹閫佺粨鏋滄娊璞′负閫氶亾鐘舵€佸垪琛紝淇濇寔鐜版湁 Telegram 琛屼负涓嶅彉锛屽悓鏃惰杩愯鎽樿鍜屽叕鍏?JSON 鑳借褰曞閫氶亾鐘舵€併€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
main.py
src/models.py
src/sender.py
scripts/send_report_link.py
scripts/build_pages.py
tests/test_sender.py
tests/test_send_report_link.py
tests/test_build_pages.py
tests/test_data_contracts.py
.env.example
README.md
docs/data-contracts.md
docs/operation-log.md
```

璋冩暣鍐呭锛?

1. 鏂板 `DeliveryResult`锛岃褰曢€氶亾鍚嶇О銆佸彂閫佺姸鎬併€侀敊璇憳瑕佸拰鏄惁璺宠繃銆?
2. 鏂板 `DELIVERY_CHANNELS` 閰嶇疆鍏ュ彛锛岄粯璁?`telegram`銆?
3. 褰撳墠浠?Telegram 浼氱湡瀹炲彂閫侊紱`feishu`銆乣wechat` 浼氳褰曚负棰勭暀閫氶亾鏈疄鐜帮紝涓嶄細鍙戦€佽姹傘€?
4. 杩愯鎽樿鏂板 `delivery_results` 瀛楁銆?
5. `docs/runs.json` 鍏紑杈撳嚭 `delivery_results`锛屾柟渚垮悗缁墠绔拰澶栭儴鑷姩鍖栬鍙栥€?
6. 淇濈暀 `telegram_sent`銆乣telegram_error`銆乣telegram_report_url` 鏃у瓧娈碉紝閬垮厤鐮村潖鐜版湁 workflow 鍜岄〉闈㈤€昏緫銆?

### 3. 璁捐杈圭晫

鏈涓嶆彁鍓嶅疄鐜板井淇°€侀涔﹀叿浣?API锛屼篃涓嶆柊澧炲瘑閽ュ瓧娈点€傚悗缁帴鍏ユ椂鍐嶆寜瀹為檯骞冲彴瑕佹眰澧炲姞鐜鍙橀噺鍜屽彂閫佸嚱鏁帮紝浠嶇劧涓嶈兘鎶?Webhook銆乀oken 鎴?Chat ID 鍐欏叆浠ｇ爜鍜屾枃妗ｇず渚嬨€?

---

## 2026-05-06 杩藉姞锛氶涔︿笌浼佷笟寰俊 Webhook 鎺ㄩ€?

### 1. 寮€鍙戠洰鐨?

涓婁竴闃舵宸茬粡鎶婃帹閫佺姸鎬佹娊璞′负澶氶€氶亾缁撴灉銆傛湰娆＄户缁ˉ榻愰涔﹀拰浼佷笟寰俊 Webhook 鍙戦€佽兘鍔涳紝璁╁懆鎶ラ摼鎺ュ彲浠ョ洿鎺ユ帹閫佸埌鏇村绉诲姩绔崗浣滃伐鍏枫€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
.env.example
.github/workflows/weekly.yml
README.md
docs/data-contracts.md
docs/operation-log.md
docs/setup.md
src/sender.py
tests/test_sender.py
```

璋冩暣鍐呭锛?

1. `DELIVERY_CHANNELS` 鏀寔 `telegram`銆乣feishu`銆乣wechat`銆?
2. `lark` 浼氬綊涓€涓?`feishu`锛宍wecom`銆乣weixin` 浼氬綊涓€涓?`wechat`銆?
3. 鏂板 `FEISHU_WEBHOOK_URL`锛岀敤浜庨涔︽満鍣ㄤ汉 Webhook銆?
4. 鏂板 `WECHAT_WEBHOOK_URL` 鍜?`WECOM_WEBHOOK_URL`锛岀敤浜庝紒涓氬井淇℃満鍣ㄤ汉 Webhook銆?
5. 椋炰功鍙戦€佷氦浜掑崱鐗囷紝浼佷笟寰俊鍙戦€?Markdown 娑堟伅锛屽唴瀹归兘鍙寘鍚懆鎶ユ爣棰樺拰 GitHub Pages 闃呰閾炬帴銆?
6. 鏈厤缃?Webhook 鐨勯€氶亾浼氳褰曚负璺宠繃锛屼笉褰卞搷鍛ㄦ姤鐢熸垚銆佸綊妗ｅ拰鍏朵粬閫氶亾鍙戦€併€?

### 3. 瀹夊叏杈圭晫

Webhook 鍦板潃鍙粠鐜鍙橀噺鎴?GitHub Actions Secrets 璇诲彇锛屼笉鍐欏叆浠ｇ爜鍜岀ず渚嬪€笺€傞敊璇憳瑕佷細鍋氬瓧娈垫敹鏁涳紝鍙褰曞钩鍙拌繑鍥炵殑鐘舵€佺爜鍜岀畝鐭秷鎭紝涓嶈褰曞畬鏁?Webhook 鍦板潃銆?

---

## 2026-05-06 杩藉姞锛氭帹閫侀€氶亾閰嶇疆妫€鏌?

### 1. 寮€鍙戠洰鐨?

椋炰功鍜屼紒涓氬井淇?Webhook 宸茬粡鏀寔鐪熷疄鍙戦€侊紝浣嗗鏋?`DELIVERY_CHANNELS` 鍚敤浜嗛€氶亾鍗存病鏈夐厤缃搴?Secret锛岀敤鎴峰彧鑳藉湪杩愯鍚庝粠鏃ュ織閲屽彂鐜拌烦杩囥€傛湰娆℃柊澧炵嫭绔嬫鏌ヨ剼鏈紝璁╅厤缃棶棰樺彲浠ユ彁鍓嶆毚闇层€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
.github/workflows/secrets-check.yml
README.md
docs/operation-log.md
docs/setup.md
scripts/check_delivery_channels.py
tests/test_delivery_channel_check.py
```

璋冩暣鍐呭锛?

1. 鏂板 `scripts/check_delivery_channels.py`銆?
2. 榛樿妯″紡鍙墦鍗?Telegram銆侀涔︺€佷紒涓氬井淇￠€氶亾閰嶇疆鐘舵€侊紝涓嶅彂閫佺湡瀹炴秷鎭€?
3. `--strict` 妯″紡浼氬湪鍚敤閫氶亾缂哄皯閰嶇疆鎴栧嚭鐜颁笉鏀寔閫氶亾鏃惰繑鍥炲け璐ャ€?
4. Secrets 閰嶇疆妫€鏌?workflow 鏂板鎺ㄩ€侀€氶亾閰嶇疆妫€鏌ユ楠ゃ€?
5. 娴嬭瘯瑕嗙洊 Telegram 瀹屾暣閰嶇疆銆侀涔︾己澶?Webhook銆佷紒涓氬井淇″弻鍙橀噺鍚嶅拰涓嶆敮鎸侀€氶亾銆?

### 3. 瀹夊叏杈圭晫

妫€鏌ヨ剼鏈彧鍒ゆ柇鐜鍙橀噺鏄惁瀛樺湪锛屼笉鎵撳嵃鍙橀噺鍊硷紝涓嶅彂閫佹秷鎭紝涔熶笉璁块棶澶栭儴 Webhook銆傜湡瀹炶繛閫氭€т粛鐢卞悗缁彂閫佹祦绋嬭礋璐ｃ€?

---

## 2026-05-06 杩藉姞锛氬叕寮€涓€у寲鏂瑰悜鏁版嵁

### 1. 寮€鍙戠洰鐨?

鐢ㄦ埛甯屾湜鍚庣画鍙互閫氳繃 Java銆丳ython銆丄gent 寮€鍙戠瓑閫夐」绮惧噯鎺ㄩ€侀」鐩€傚綋鍓?profile 宸茬粡鑳藉奖鍝嶉噰闆嗗拰璇勫垎锛屼絾鍓嶇缂哄皯绋冲畾鍏紑鏁版嵁鍏ュ彛銆傛湰娆℃柊澧?`profiles.json`锛岃 GitHub Pages 鍜屽悗缁墠绔彲浠ョ洿鎺ヨ鍙栦釜鎬у寲鏂瑰悜銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/data-contracts.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
```

璋冩暣鍐呭锛?

1. `scripts/build_pages.py` 鐢熸垚 `docs/profiles.json`銆?
2. GitHub Pages 棣栭〉鏂板 `profiles.json` 鍏ュ彛銆?
3. `docs/explorer.html` 鏂板鈥滀釜鎬у寲鏂瑰悜鈥濈瓫閫夐」銆?
4. 绛涢€夐〉浼氳鍙?`profiles.json`锛屾寜 profile 鐨勫亸濂借瑷€鍜屼富棰樺叧閿瘝杩囨护鍘嗗彶椤圭洰銆?
5. URL 鍙傛暟鏂板 `profile`锛屾柟渚垮垎浜煇涓釜鎬у寲鏂瑰悜瑙嗗浘銆?
6. 濂戠害娴嬭瘯瑕嗙洊 `profiles.json` 鐨勫叕寮€瀛楁闆嗗悎銆?

### 3. 瀹夊叏杈圭晫

`profiles.json` 鍙叕寮€ profile 鍚嶇О銆佹樉绀烘爣绛俱€佸涔犵洰鏍囥€佸亸濂借瑷€鍜屼富棰樺叧閿瘝锛屼笉鍏紑璇勫垎鏉冮噸銆佺鏈夐厤缃€佸瘑閽ユ垨鐢ㄦ埛韬唤淇℃伅銆?

---

## 2026-05-06 杩藉姞锛氬畨鍏ㄥ垎涓庨闄╃瓑绾?

### 1. 寮€鍙戠洰鐨?

姝ゅ墠椤圭洰鍙繚瀛橀闄╂彁绀烘枃鏈紝鍓嶇鍜屽悗缁釜鎬у寲鎺ㄨ崘闅句互鎺掑簭鎴栫瓫閫夐闄╁己寮便€傛湰娆℃柊澧炲熀纭€瀹夊叏鍒嗗拰椋庨櫓绛夌骇锛屼负鍚庣画瀹夊叏妫€鏌ュ姛鑳姐€佸墠绔瓫閫夊拰鎺ㄩ€佹憳瑕佹彁渚涚粨鏋勫寲瀛楁銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/data-contracts.md
docs/operation-log.md
scripts/build_pages.py
src/models.py
src/security.py
tests/test_build_pages.py
tests/test_data_contracts.py
tests/test_security.py
```

璋冩暣鍐呭锛?

1. `Repository` 鏂板 `security_score` 鍜?`security_level`銆?
2. `apply_security_flags` 浼氬悓姝ヨ绠楀畨鍏ㄥ垎鍜岄闄╃瓑绾с€?
3. 椋庨櫓绛夌骇鍒嗕负 `low`銆乣medium`銆乣high`銆?
4. 涓嶅悓椋庨櫓鎻愮ず鎸変弗閲嶇▼搴︽墸鍒嗭紝渚嬪鎭舵剰杞欢銆侀挀楸笺€佺獌鍙栫被椋庨櫓鎵ｅ垎鏇撮珮銆?
5. `docs/projects.json` 杈撳嚭瀹夊叏鍒嗗拰椋庨櫓绛夌骇銆?
6. `docs/explorer.html` 鍦ㄩ闄╁垪灞曠ず椋庨櫓绛夌骇鍜屽畨鍏ㄥ垎銆?

### 3. 璁捐杈圭晫

璇ヨ瘎鍒嗘槸鍚彂寮忓熀纭€妫€鏌ワ紝涓嶄唬琛ㄥ畬鏁村畨鍏ㄥ璁°€傚畠鐢ㄤ簬鎺掑簭銆佹彁閱掑拰鍚庣画绛涢€夛紝涓嶅簲浣滀负鏄惁鍙互鐩存帴杩愯澶栭儴椤圭洰鐨勫敮涓€渚濇嵁銆?

---

## 2026-05-06 杩藉姞锛氬巻鍙查」鐩鎯呭睍寮€

### 1. 寮€鍙戠洰鐨?

褰撳墠鍘嗗彶椤圭洰绛涢€夐〉宸茬粡鑳芥寜璇█銆乸rofile銆佹潵婧愬拰椋庨櫓绛涢€夛紝浣嗙敤鎴蜂粛闇€瑕佹墦寮€鍛ㄦ姤鎴栦粨搴撴墠鑳界悊瑙ｉ」鐩环鍊笺€傛湰娆″湪闈欐€佺瓫閫夐〉涓姞鍏ヨ鎯呭睍寮€鑳藉姏锛屾彁鍗囨祻瑙堟晥鐜囷紝鍚屾椂缁х画淇濈暀鏈潵鍗囩骇澶嶆潅鍓嶇妗嗘灦鐨勭┖闂淬€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/data-contracts.md
docs/future-plan.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
```

璋冩暣鍐呭锛?

1. `docs/projects.json` 鏂板 `readme_summary` 瀛楁銆?
2. `docs/explorer.html` 姣忎釜椤圭洰鏂板鈥滆鎯呪€濇寜閽€?
3. 灞曞紑璇︽儏鍚庡睍绀?README 绮剧畝鎽樿銆佹帹鑽愮悊鐢便€侀闄╂彁绀恒€侀」鐩寚鏍囥€佹潵婧愬拰瀹屾暣閾炬帴銆?
4. `docs/future-plan.md` 鏂板鍓嶇鎵╁睍杈圭晫锛屾槑纭湭鏉ュ彲鍗囩骇鍒板鏉傛鏋讹紝浣嗗綋鍓嶄粛浠ュ叕鍏?JSON 濂戠害涓烘牳蹇冦€?

### 3. 璁捐杈圭晫

鏈娌℃湁寮曞叆鍓嶇鏋勫缓宸ュ叿銆傛墍鏈変氦浜掍粛鍦ㄩ潤鎬侀〉闈㈠唴瀹屾垚锛屾暟鎹户缁潵鑷?`projects.json`銆乣profiles.json` 鍜?`runs.json`锛屼负鍚庣画妗嗘灦鍖栬縼绉讳繚鐣欐竻鏅版帴鍙ｃ€?

---

## 2026-05-06 杩藉姞锛氫釜鎬у寲鏂瑰悜蹇嵎瑙嗗浘

### 1. 寮€鍙戠洰鐨?

绛涢€夐〉宸叉湁 profile 涓嬫媺妗嗭紝浣嗙Щ鍔ㄧ鍜岄绻佸垏鎹㈠満鏅笅涓嶅鐩磋銆傛湰娆″鍔犲揩鎹疯鍥炬寜閽紝璁╃敤鎴峰彲浠ヤ竴閿垏鎹?Java銆丳ython銆丄gent 寮€鍙戠瓑鏂瑰悜锛屽悓鏃剁户缁鐢ㄥ叕寮€ `profiles.json`銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

璋冩暣鍐呭锛?

1. `docs/explorer.html` 鏂板 `profileShortcuts` 鍖哄煙銆?
2. 椤甸潰鏍规嵁 `profiles.json` 鑷姩鐢熸垚鈥滃叏閮ㄦ柟鍚戔€濆拰鍚?profile 蹇嵎鎸夐挳銆?
3. 鐐瑰嚮蹇嵎鎸夐挳浼氬悓姝ユ洿鏂?profile 绛涢€夋潯浠躲€佽〃鏍肩粨鏋滃拰 URL 鏌ヨ鍙傛暟銆?
4. 褰撳墠浠嶄负闈欐€侀〉闈㈠疄鐜帮紝涓嶆柊澧炲墠绔瀯寤烘楠ゃ€?

### 3. 璁捐杈圭晫

蹇嵎鎸夐挳鍙秷璐瑰叕寮€ profile 鏁版嵁锛屼笉纭紪鐮佷笟鍔℃柟鍚戙€傛湭鏉ュ崌绾у埌澶嶆潅鍓嶇妗嗘灦鏃讹紝鍙互鐩存帴澶嶇敤 `profiles.json` 鍜屽綋鍓?URL 鍙傛暟绾﹀畾銆?

---

## 2026-05-06 杩藉姞锛氭帰绱㈤〉鐩镐技椤圭洰鎺ㄨ崘

### 1. 寮€鍙戠洰鐨?

椤圭洰璇︽儏宸茬粡鑳藉睍绀?README 鎽樿鍜屾帹鑽愮悊鐢憋紝浣嗙敤鎴疯繕闇€瑕佸湪鍚屼竴鏂瑰悜鍐呮í鍚戞瘮杈冪被浼间粨搴撱€傛湰娆″湪闈欐€佹帰绱㈤〉涓姞鍏ョ浉浼煎巻鍙查」鐩帹鑽愶紝涓哄悗缁釜鎬у寲鎺ㄨ崘銆佹暟鎹簱鏌ヨ鍜屽鏉傚墠绔鏋惰縼绉婚鐣欏叆鍙ｃ€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/explorer.html
docs/operation-log.md
tests/test_build_pages.py
```

璋冩暣鍐呭锛?

1. `docs/explorer.html` 鐨勯」鐩鎯呮柊澧炩€滅浉浼奸」鐩€濆尯鍩熴€?
2. 鐩镐技搴︽殏鎸夎瑷€銆佹柟鍚戙€佹潵婧愬拰椤圭洰鍏抽敭璇嶉噸鍚堝害璁＄畻锛屼笉渚濊禆鏂版帴鍙ｆ垨鏂版暟鎹簱銆?
3. 姣忎釜椤圭洰鏈€澶氬睍绀?3 涓浉浼煎巻鍙查」鐩紝骞舵樉绀洪」鐩摼鎺ャ€佽瑷€銆佹柟鍚戝拰鏂板 Star銆?
4. 椤甸潰浠嶇劧鍙秷璐?`projects.json`锛屽悗缁彲鎶婂綋鍓嶇浉浼煎害鍑芥暟杩佺Щ鍒板墠绔鏋躲€丼QLite 鏌ヨ鎴栨湇鍔＄鎺ㄨ崘妯″潡銆?

### 3. 璁捐杈圭晫

褰撳墠鐩镐技椤圭洰鎺ㄨ崘鏄交閲忓惎鍙戝紡鍖归厤锛岀敤浜庢彁鍗囨祻瑙堟晥鐜囷紝涓嶄綔涓烘渶缁堟帹鑽愭ā鍨嬨€傛湭鏉ユ帴鍏ユ暟鎹簱鍚庯紝鍙互鎶婂悓璇█銆佸悓涓婚銆佸悓 profile 鍜岀敤鎴风偣鍑诲弽棣堢撼鍏ユ洿绋冲畾鐨勭浉浼煎害璁＄畻銆?

---

## 2026-05-06 杩藉姞锛氬巻鍙插綊妗ｆ煡璇㈣剼鏈?

### 1. 寮€鍙戠洰鐨?

鍓嶇鍜屾暟鎹簱宸茬粡杩涘叆瑙勫垝闃舵锛屼絾褰撳墠涓嶉€傚悎绔嬪埢寮曞叆瀹屾暣鍚庡彴鏈嶅姟銆傛湰娆″厛琛ラ綈鍛戒护琛屽巻鍙叉煡璇㈠叆鍙ｏ紝璁?SQLite 娲剧敓绱㈠紩鐪熸鍙敤锛屼负鍚庣画鍚庡彴 API銆佸鏉傚墠绔瓫閫夊拰涓€у寲璁㈤槄鎵撳熀纭€銆?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/data-contracts.md
docs/operation-log.md
scripts/query_archive.py
tests/test_query_archive.py
```

璋冩暣鍐呭锛?

1. 鏂板 `scripts/query_archive.py`銆?
2. 鏀寔鎸夎瑷€銆佹柟鍚戙€乸rofile銆佹潵婧愩€侀闄╂彁绀哄拰鍏抽敭璇嶆煡璇㈠巻鍙查」鐩€?
3. 鏀寔 `--refresh` 鍦ㄦ煡璇㈠墠浠?JSON 褰掓。鍚屾 SQLite銆?
4. 鏀寔 `table` 鍜?`json` 涓ょ杈撳嚭鏍煎紡銆?
5. 鏂板娴嬭瘯瑕嗙洊璇█銆佹潵婧愩€佸叧閿瘝銆乸rofile銆侀闄╁拰琛ㄦ牸杈撳嚭銆?

### 3. 璁捐杈圭晫

璇ヨ剼鏈彧璇诲彇 JSON 褰掓。銆丼QLite 娲剧敓绱㈠紩鍜屽叕寮€ profile 閰嶇疆锛屼笉璇诲彇瀵嗛挜锛屼笉鍙戦€佸閮ㄨ姹傦紝涔熶笉鏀瑰彉涓绘祦绋嬨€傛湭鏉ュ鏋滃缓璁惧悗绔?API锛屽彲浠ョ洿鎺ュ鐢ㄥ叾涓殑绛涢€夋潯浠跺拰杈撳嚭瀛楁銆?

---

## 2026-05-06 杩藉姞锛氬巻鍙插綊妗ｆ煡璇㈣鏄庨〉

### 1. 寮€鍙戠洰鐨?

鍘嗗彶鏌ヨ CLI 宸茬粡鍙敤锛屼絾鍏ュ彛涓昏闈㈠悜寮€鍙戣€呫€備负浜嗚鍚庣画鍓嶇銆佹暟鎹簱鍜屼釜鎬у寲鑳藉姏鏈夋洿娓呮鐨勬枃妗ｅ叆鍙ｏ紝鏈琛ュ厖 GitHub Pages 鍙闂殑鏌ヨ璇存槑椤点€?

### 2. 鏈瀹炵幇

鏇存柊锛?

```text
README.md
docs/archive-query.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

璋冩暣鍐呭锛?

1. 鏂板 `docs/archive-query.md`銆?
2. 璇存槑鍘嗗彶鏌ヨ鐨勪娇鐢ㄥ満鏅€佸父鐢ㄥ懡浠ゃ€佸畨鍏ㄨ竟鐣屽拰鍚庣画鎵╁睍鏂瑰悜銆?
3. GitHub Pages 棣栭〉澧炲姞鈥滃巻鍙插綊妗ｆ煡璇㈣鏄庘€濆叆鍙ｃ€?
4. README 鐨?SQLite 娲剧敓绱㈠紩閮ㄥ垎琛ュ厖璇存槑椤靛紩鐢ㄣ€?
5. 椤甸潰鏋勫缓娴嬭瘯瑕嗙洊鏂板鍏ュ彛銆?

### 3. 璁捐杈圭晫

璇ラ〉闈㈡槸闈欐€佽鏄庢枃妗ｏ紝涓嶅紩鍏ユ柊鐨勮繍琛屼緷璧栥€傚悗缁鏋滃缓璁炬暟鎹簱椤甸潰鎴栧墠绔悗鍙帮紝鍙互鎶婅繖閲岀殑鍛戒护绀轰緥婕旇繘涓洪〉闈㈢瓫閫夐」鍜?API 鏌ヨ鍙傛暟銆?

