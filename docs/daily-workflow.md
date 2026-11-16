# 4作業をまとめて監視

2026-11-17。複数作業CLIと、所有確認付きの本体接続。4job/期限切れ/終了を実機で自動照合した。長時間・再接続の結果は別記録。

```sh
uv run --locked python -m arcade_agent_desk watch \
  --key secrets/pairing.json --jobs examples/jobs.json --linger 3
```

サンプルはunit試験・2秒待機・意図したexit7・意図した期限切れの4本。
失敗を含むため終了コードは1。全成功だけ0、入力不正は2。
実作業へ使う場合はGit対象外の`secrets/jobs.json`へコピーし、実行するargvと期限を設定する。
シェル展開は使わず、1〜4の重複しないtask IDへ固定する。最大4並行、各期限1時間以内。

| イベント | 表示 |
|---|---|
| 実行中 | WORK |
| exit0 | DONE |
| 非0 / 起動失敗 / 期限 | FAIL |
| 取消 | CANCEL |
| 送信が止まりTTL経過 | LOST |

全jobを検査してから起動。WORKの送信後も実exitを待ち、失敗を完了と誤表示しない。
Ctrl-Cは所有するjob groupだけを終了する。通知内容はtask番号/状態/経過時間等で、
command・stdout・資格情報はUDPへ含めない。子コマンドの出力はローカルの端末へ出る。
WAITは既存libraryの明示イベントのみで、watchがAIの承認待ちを推測することはない。

Bridgeへの書き込みは1スレッドにまとめる。頻繁なdirty更新を250ms単位でまとめ、
1回最大4通知、heartbeatは500ms。認証済みHELLOには既存の即時応答を維持する。
この上限は実機の欠落0/遅延の保証ではなく、連続試験で別に測定する。

実機は同じ鍵でbuildしたapp、RAM Wi-FiとUDP route、明示したLAN bindが必要。
watch単独では実機へinstall/接続しない。先に次の明示コマンドで接続する。

## 本体の接続と終了

対応OSが導入済みの本体でHOMEに戻り、全キーを離す。SSID/passwordは非公開の
`secrets/network.json`へ保存し、`chmod 600 secrets/network.json`を適用する。
`PORT`は検出したシリアルポート、`MAC_LAN_IP`は本体から到達できるMacのLAN IPv4。

```sh
uv run --locked python -m arcade_agent_desk install \
  --sdk ../scratch-arcade-os --port "$PORT" --package build/paired/app.labapp
uv run --locked python -m arcade_agent_desk connect \
  --sdk ../scratch-arcade-os --port "$PORT" --package build/paired/app.labapp \
  --network secrets/network.json --peer "$MAC_LAN_IP"
uv run --locked python -m arcade_agent_desk watch \
  --key secrets/pairing.json --jobs examples/jobs.json --bind "$MAC_LAN_IP" --linger 3
uv run --locked python -m arcade_agent_desk disconnect \
  --sdk ../scratch-arcade-os --port "$PORT" --package build/paired/app.labapp
```

初回だけinstallし、既存版を更新する場合は正確な旧hashを`--previous-sha`へ指定する。
connectは選んだpackageと本体hashの一致を確認して、RAM Wi-Fi/UDP設定後に専用appを起動する。
UDPはguest起動後、catalog照合はHOMEのみ。disconnectは所有appだけ終了し、HOME・無線/socket停止・catalogを確認する。
FW・共有設定・他appを書き換えない。Wi-Fiエラーや所有不明時は操作を繰り返さず確認する。

## 新CLIの実機結果

4本の実プロセスでexit0/7/124/0を取得し、4タブの描画命令CRCが同一WASMの参照と一致。
送信停止後のLOST、HOME復帰、radio停止、15appの全版/hash保持も確認した。
[匿名結果](device/daily-v1.json)。LCD・物理キー・音の聴取を確認済みとは扱わない。
初回の追加試験は管理sessionを無通信で放置したためstatus6となり失敗。観測中も状態を照会して再実行した。失敗を成功記録で上書きしていない。

## 画面素材

[実WASMのGIF](media/replay.gif)と6状態のPNGは、公開demo専用鍵と合成通知で作成した。
本体撮影・実ジョブの録画ではない。`uv run --locked python -m arcade_agent_desk.media --sdk <SDK> --output <new-directory>`で再生成できる。production鍵やpaired binaryは公開しない。

## 再接続と連続更新

同じ15app/FWで接続→実更新→終了を2周し、稼働中のUSB再openも2回成功した。
合計317.654秒、3秒間隔の40更新を本体の描画命令CRCで照合し、3秒の照合期限超過は0。
PCのupdate呼出しから最初の一致まで中央値262.716ms、最大462.976ms。
物理LCDの遅延・UDP全packetの欠落率を測った値ではない。長期の無故障保証でもない。
終了ごとにHOME/radio停止/15app版hashを確認し、再起動したappの世代増加を確認した。
[匿名結果](device/soak-v1.json)。新FW・本体の電源再投入は実施していない。
